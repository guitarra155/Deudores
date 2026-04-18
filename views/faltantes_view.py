import flet as ft
import asyncio

def mostrar_dialogo_faltantes(page: ft.Page, repo, catalogo=None) -> None:
    """Abre el diálogo global interactivo de productos faltantes."""
    
    faltantes = repo.get_faltantes()
    
    # Textfield principal
    tf_nuevo = ft.TextField(
        hint_text="Escriba un producto y pulse Enter...",
        expand=True,
        dense=True,
        text_size=13,
        border_color=ft.Colors.TRANSPARENT,
        focused_border_color=ft.Colors.INDIGO_400,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        border_radius=8,
        autofocus=True,
    )
    
    sug_container = ft.Container(
        content=ft.Column(spacing=0),
        bgcolor="#1e1e2d",
        border_radius=8,
        border=ft.border.all(1, ft.Colors.INDIGO_900),
        padding=4,
        margin=ft.margin.only(top=40),
        visible=False,
    )

    lista = ft.ListView(expand=True, spacing=4, padding=ft.padding.only(right=10))
    
    def guardar_y_refrescar(e=None):
        repo.save_faltantes(faltantes)
        _render_lista()

    def agregar(e=None, val=None):
        texto = val if val else tf_nuevo.value.strip()
        if texto:
            faltantes.append(texto)
            tf_nuevo.value = ""
            estado_sug["items"] = []
            estado_sug["idx"] = -1
            _render_sug()
            guardar_y_refrescar()
            try:
                page.run_task(tf_nuevo.focus)
            except Exception:
                pass
            
    def eliminar(i: int):
        faltantes.pop(i)
        guardar_y_refrescar()

    def vaciar(e):
        faltantes.clear()
        guardar_y_refrescar()

    tf_nuevo.on_submit = agregar

    estado_sug = {"idx": -1, "items": []}

    def _render_sug():
        col = sug_container.content
        col.controls.clear()
        for i, prod in enumerate(estado_sug["items"]):
            es_sel = (i == estado_sug["idx"])
            btn = ft.Container(
                content=ft.Text(prod, color=ft.Colors.WHITE if es_sel else ft.Colors.GREY_300, size=13),
                padding=8,
                border_radius=4,
                bgcolor="#2a2f5a" if es_sel else "transparent",
                ink=True,
                on_click=lambda ev, p=prod: agregar(val=p),
            )
            col.controls.append(btn)
            
        sug_container.visible = len(estado_sug["items"]) > 0
        try:
            sug_container.update()
        except:
            pass

    def _mover_sug(delta: int):
        n = len(estado_sug["items"])
        if not n: return
        if delta > 0:
            estado_sug["idx"] = min(estado_sug["idx"] + 1, n - 1)
        else:
            estado_sug["idx"] = max(estado_sug["idx"] - 1, -1)
        _render_sug()

    def _faltantes_on_key(e: ft.KeyboardEvent) -> bool:
        if not getattr(dlg, "open", False):
            return False
            
        if e.key == "Escape":
            if sug_container.visible:
                estado_sug["items"] = []
                estado_sug["idx"] = -1
                _render_sug()
                return True
            return False # Let global escape handle dialog closure
            
        if e.key == "Arrow Down" and estado_sug["items"]:
            from core.keyboard import _bucle_auto_repetir
            page.run_task(_bucle_auto_repetir, 0x28, _mover_sug, 1)
            return True
        if e.key == "Arrow Up" and estado_sug["items"]:
            from core.keyboard import _bucle_auto_repetir
            page.run_task(_bucle_auto_repetir, 0x26, _mover_sug, -1)
            return True
        if e.key == "Enter" and estado_sug["idx"] >= 0:
            # Selecciona la sugerencia resaltada
            agregar(val=estado_sug["items"][estado_sug["idx"]])
            return True
            
        return False
        
    page._faltantes_on_key = _faltantes_on_key

    def _on_change_texto(e):
        val = tf_nuevo.value.strip()
        cat = catalogo
        if not val or not cat or not cat.disponible:
            estado_sug["items"] = []
            estado_sug["idx"] = -1
            _render_sug()
            return
            
        coincidencias = cat.buscar_nombre(val, limite=5)
        estado_sug["items"] = coincidencias
        estado_sug["idx"] = -1
        _render_sug()

    tf_nuevo.on_change = _on_change_texto

    def _render_lista():
        lista.controls.clear()
        if not faltantes:
            lista.controls.append(
                ft.Container(
                    content=ft.Text("Lista vacía. No faltan productos.", color=ft.Colors.GREY_500, size=13, italic=True),
                    alignment=ft.Alignment(0, 0),
                    padding=20,
                )
            )
        else:
            for i, prod in enumerate(faltantes):
                lista.controls.append(_build_fila_faltante(i, prod))
        page.update()

    def _build_fila_faltante(i: int, prod: str) -> ft.Container:
        texto_ctrl = ft.Text(prod, size=14, expand=True, color=ft.Colors.WHITE)

        tf_edit = ft.TextField(
            value=prod,
            dense=True,
            text_size=13,
            expand=True,
            border_color=ft.Colors.AMBER_400,
            focused_border_color=ft.Colors.AMBER_400,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            border_radius=6,
            height=34,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=2),
            visible=False,
        )

        btn_edit = ft.IconButton(
            icon=ft.Icons.EDIT_NOTE,
            icon_size=16, icon_color=ft.Colors.INDIGO_300,
            tooltip="Editar",
            width=30, height=30, padding=0,
        )

        def _toggle_edicion(e, idx=i):
            modo = not tf_edit.visible
            tf_edit.visible    = modo
            texto_ctrl.visible = not modo
            btn_edit.icon = ft.Icons.CHECK if modo else ft.Icons.EDIT_NOTE
            btn_edit.icon_color = ft.Colors.GREEN_400 if modo else ft.Colors.INDIGO_300
            try:
                fila_row.update()
            except Exception:
                pass
            if modo:
                try:
                    page.run_task(tf_edit.focus)
                except Exception:
                    pass

        def _guardar_edicion(e=None, idx=i):
            nuevo = tf_edit.value.strip()
            if nuevo and nuevo != faltantes[idx]:
                faltantes[idx] = nuevo
                guardar_y_refrescar()
            else:
                # Solo salir del modo edición
                tf_edit.visible    = False
                texto_ctrl.visible = True
                btn_edit.icon = ft.Icons.EDIT_NOTE
                btn_edit.icon_color = ft.Colors.INDIGO_300
                try:
                    fila_row.update()
                except Exception:
                    pass

        tf_edit.on_submit = _guardar_edicion
        tf_edit.on_blur   = _guardar_edicion
        btn_edit.on_click = _toggle_edicion

        fila_row = ft.Row(
            [
                ft.Icon(ft.Icons.CIRCLE, size=8, color=ft.Colors.AMBER_400),
                ft.Stack([texto_ctrl, tf_edit], expand=True),
                btn_edit,
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=16,
                    icon_color=ft.Colors.GREY_500,
                    on_click=lambda e, idx=i: eliminar(idx),
                    tooltip="Quitar",
                    width=30, height=30, padding=0,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=fila_row,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
            padding=ft.padding.symmetric(horizontal=12, vertical=4),
            border_radius=6,
        )


    btn_add = ft.IconButton(
        icon=ft.Icons.ADD_SHOPPING_CART,
        icon_color=ft.Colors.WHITE,
        bgcolor=ft.Colors.INDIGO_600,
        on_click=agregar,
        tooltip="Añadir a la lista"
    )

    dlg = ft.AlertDialog(
        modal=False,
        title=ft.Row([
            ft.Icon(ft.Icons.FORMAT_LIST_BULLETED, color=ft.Colors.AMBER_400),
            ft.Text("Productos Faltantes", weight=ft.FontWeight.BOLD),
        ], spacing=8),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Stack([
                        ft.Row([tf_nuevo, btn_add], spacing=8),
                        sug_container
                    ], clip_behavior="none"),
                    ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
                    ft.Container(content=lista, expand=True),
                    ft.Row(
                        [
                            ft.TextButton(
                                "Vaciar la lista", 
                                icon=ft.Icons.DELETE_SWEEP, 
                                icon_color=ft.Colors.RED_400,
                                on_click=vaciar
                            )
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    )
                ],
                tight=False,
            ),
            width=400,
            height=500,
        ),
        actions=[
            ft.FilledTonalButton("Cerrar", on_click=lambda e: (setattr(dlg, "open", False), page.update()))
        ]
    )

    _render_lista()
    page.overlay.append(dlg)
    dlg.open = True
    page.update()
