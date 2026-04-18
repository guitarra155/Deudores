import flet as ft
import asyncio
import ctypes

_teclas_bloqueo = {0x26: False, 0x28: False}  # VK_UP, VK_DOWN

async def _bucle_auto_repetir(vk_code: int, callback, delta: int):
    if _teclas_bloqueo.get(vk_code, False):
        return
    _teclas_bloqueo[vk_code] = True
    try:
        callback(delta) # Acción inicial (inmediata)
        await asyncio.sleep(0.20) # Reducido de 0.35 a 0.20 para sentirlo más rápido
        while (ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000) != 0:
            callback(delta)
            await asyncio.sleep(0.05) # ~20 repeticiones por seg
    finally:
        _teclas_bloqueo[vk_code] = False

def registrar_atajos_teclado(page: ft.Page, clientes_view, deudas_view):
    def _on_keyboard_global(e: ft.KeyboardEvent) -> None:
        if hasattr(page, "_faltantes_on_key") and page._faltantes_on_key(e):
            return

        if e.ctrl and e.key.upper() == "N":
            clientes_view._abrir_dialogo_nuevo()
            return

        if e.ctrl and e.key.upper() == "L":
            from views.faltantes_view import mostrar_dialogo_faltantes
            mostrar_dialogo_faltantes(page, clientes_view._repo, deudas_view._catalogo)
            return

        if e.ctrl and e.key.upper() == "O":
            from views.notas_view import mostrar_dialogo_notas
            mostrar_dialogo_notas(page, clientes_view._repo)
            return

        if e.ctrl and e.key.upper() == "T":
            from views.tareas_view import mostrar_dialogo_tareas
            mostrar_dialogo_tareas(page, clientes_view._repo)
            return

        if e.ctrl and e.key.upper() == "K":
            page.run_task(clientes_view._search_field.focus)
            return

        # Navegación en Clientes (solo si no hay cliente seleccionado o el buscador tiene el foco)
        es_pantalla_seleccion = (deudas_view._cliente is None)
        search_focused = getattr(clientes_view, "_search_focused", False)
        
        if (search_focused or es_pantalla_seleccion) and not e.ctrl:
            if e.key == "Arrow Down":
                page.run_task(_bucle_auto_repetir, 0x28, clientes_view._mover_highlight, 1)
                return
            if e.key == "Arrow Up":
                page.run_task(_bucle_auto_repetir, 0x26, clientes_view._mover_highlight, -1)
                return

        if e.ctrl and deudas_view._cliente is not None:
            k = e.key.upper()
            if k == "A":
                deudas_view._on_abono(None)
                return
            if k == "P":
                deudas_view._exportar_pdf(None)
                return
            if k == "W" and deudas_view._cliente.telefono:
                deudas_view._enviar_whatsapp(None)
                return
            if k == "S":
                deudas_view._on_saldar_deuda(None)
                return

        if e.key == "Escape":
            if clientes_view._busqueda:
                clientes_view._limpiar_busqueda()
                page.run_task(clientes_view._search_field.focus)
                return

            if deudas_view._sug_container is not None and deudas_view._sug_container.visible:
                deudas_view._ocultar_sug()
                return

            cerrado = False
            for ctrl in reversed(page.overlay):
                if hasattr(ctrl, "open") and ctrl.open:
                    ctrl.open = False
                    try:
                        ctrl.update()
                    except Exception:
                        pass
                    cerrado = True
                    break
            if cerrado:
                page.update()
                return

            if deudas_view._cliente is not None:
                deudas_view.cargar_cliente(None)
                clientes_view._cliente_activo = None
                clientes_view._refresh_lista()
                return

        deudas_view._on_key_event(e)

    page.on_keyboard_event = _on_keyboard_global
