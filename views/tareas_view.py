"""
views/tareas_view.py
Diálogo global de tareas del local — accesible desde la AppBar (Ctrl+T).

Cada tarea: {"id": "...", "texto": "...", "completada": False, "fecha": "YYYY-MM-DD"}
Al completar → se tacha + se mueve al fondo.
Editable inline haciendo clic en el botón lápiz.
"""
import uuid
from datetime import datetime

import flet as ft


def mostrar_dialogo_tareas(page: ft.Page, repo) -> None:
    """Abre el diálogo de tareas del local."""
    tareas: list = repo.get_tareas()

    tf_nueva = ft.TextField(
        hint_text="Nueva tarea... (Enter para agregar)",
        expand=True,
        dense=True,
        text_size=13,
        border_color=ft.Colors.TRANSPARENT,
        focused_border_color=ft.Colors.AMBER_400,
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
        border_radius=8,
        autofocus=True,
    )

    lista = ft.ListView(expand=True, spacing=2, padding=ft.padding.only(right=6))

    def guardar_y_refrescar():
        repo.save_tareas(tareas)
        _render_lista()

    def agregar(e=None):
        texto = tf_nueva.value.strip()
        if not texto:
            return
        tareas.append({
            "id": str(uuid.uuid4()),
            "texto": texto,
            "completada": False,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
        })
        tf_nueva.value = ""
        try:
            tf_nueva.update()
        except Exception:
            pass
        guardar_y_refrescar()
        try:
            page.run_task(tf_nueva.focus)
        except Exception:
            pass

    def eliminar(tarea_id: str):
        nonlocal tareas
        tareas = [t for t in tareas if t["id"] != tarea_id]
        guardar_y_refrescar()

    def completar(tarea_id: str):
        for t in tareas:
            if t["id"] == tarea_id:
                t["completada"] = not t["completada"]
                break
        # Reordenar: pendientes primero, completadas al fondo
        tareas.sort(key=lambda t: t.get("completada", False))
        guardar_y_refrescar()

    def editar_texto(tarea_id: str, nuevo_texto: str):
        for t in tareas:
            if t["id"] == tarea_id:
                t["texto"] = nuevo_texto.strip() or t["texto"]
                break
        guardar_y_refrescar()

    def _render_lista():
        lista.controls.clear()
        if not tareas:
            lista.controls.append(ft.Container(
                content=ft.Text("No hay tareas pendientes. ¡Todo al día! 🎉",
                                color=ft.Colors.GREY_500, size=13, italic=True),
                alignment=ft.Alignment(0, 0), padding=20,
            ))
        else:
            for tarea in tareas:
                lista.controls.append(_build_fila_tarea(tarea))
        try:
            lista.update()
        except Exception:
            pass

    def _build_fila_tarea(tarea: dict) -> ft.Container:
        completada = tarea.get("completada", False)
        tarea_id   = tarea["id"]

        # Texto con tachado si está completada
        texto_ctrl = ft.Text(
            tarea["texto"],
            size=13,
            expand=True,
            color=ft.Colors.GREY_600 if completada else ft.Colors.WHITE,
            style=ft.TextStyle(
                decoration=ft.TextDecoration.LINE_THROUGH if completada else None,
            ),
        )

        # TextField oculto para edición inline
        tf_edit = ft.TextField(
            value=tarea["texto"],
            dense=True,
            text_size=13,
            expand=True,
            border_color=ft.Colors.AMBER_400,
            focused_border_color=ft.Colors.AMBER_400,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            border_radius=6,
            height=36,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=2),
            visible=False,
        )

        def _toggle_edicion(e):
            modo_edicion = not tf_edit.visible
            tf_edit.visible   = modo_edicion
            texto_ctrl.visible = not modo_edicion
            btn_edit.icon = ft.Icons.CHECK if modo_edicion else ft.Icons.EDIT_NOTE
            btn_edit.icon_color = ft.Colors.GREEN_400 if modo_edicion else ft.Colors.INDIGO_300
            try:
                fila_row.update()
            except Exception:
                pass
            if modo_edicion:
                try:
                    page.run_task(tf_edit.focus)
                except Exception:
                    pass

        def _guardar_edicion(e=None):
            nuevo = tf_edit.value.strip()
            if nuevo:
                editar_texto(tarea_id, nuevo)
            else:
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

        btn_edit = ft.IconButton(
            icon=ft.Icons.EDIT_NOTE,
            icon_size=16, icon_color=ft.Colors.INDIGO_300,
            tooltip="Editar tarea",
            on_click=_toggle_edicion,
            width=30, height=30, padding=0,
        )

        checkbox = ft.Checkbox(
            value=completada,
            on_change=lambda e, tid=tarea_id: completar(tid),
            active_color=ft.Colors.GREEN_400,
        )

        fecha_lbl = ft.Text(
            tarea.get("fecha", ""),
            size=10, color=ft.Colors.GREY_700, width=80,
        )

        btn_eliminar = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_size=16, icon_color=ft.Colors.RED_400,
            tooltip="Eliminar tarea",
            on_click=lambda e, tid=tarea_id: eliminar(tid),
            width=30, height=30, padding=0,
        )

        fila_row = ft.Row(
            [
                checkbox,
                ft.Stack([texto_ctrl, tf_edit], expand=True),
                fecha_lbl,
                btn_edit,
                btn_eliminar,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        )

        return ft.Container(
            content=fila_row,
            bgcolor=(
                ft.Colors.with_opacity(0.04, ft.Colors.GREEN_400)
                if completada
                else ft.Colors.with_opacity(0.05, ft.Colors.INDIGO_400)
            ),
            border=ft.border.all(1, ft.Colors.with_opacity(
                0.1, ft.Colors.GREEN_400 if completada else ft.Colors.INDIGO_700
            )),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
        )

    tf_nueva.on_submit = agregar

    n_pending = sum(1 for t in tareas if not t.get("completada", False))
    titulo_badge = f" ({n_pending} pendiente{'s' if n_pending != 1 else ''})" if n_pending else ""

    dlg = ft.AlertDialog(
        modal=False,
        title=ft.Row([
            ft.Icon(ft.Icons.CHECKLIST_OUTLINED, color=ft.Colors.AMBER_400, size=22),
            ft.Text(f"Tareas del Local{titulo_badge}",
                    weight=ft.FontWeight.BOLD, size=16),
        ], spacing=8),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row([tf_nueva,
                            ft.IconButton(
                                icon=ft.Icons.ADD_TASK,
                                icon_color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.INDIGO_600,
                                on_click=agregar,
                                tooltip="Agregar tarea",
                            )], spacing=8),
                    ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
                    ft.Container(content=lista, expand=True),
                    ft.Row(
                        [ft.TextButton("Eliminar completadas",
                                       icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                                       icon_color=ft.Colors.RED_400,
                                       on_click=lambda e: _limpiar_completadas())],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                tight=False, spacing=8,
            ),
            width=480,
            height=520,
        ),
        actions=[
            ft.FilledTonalButton(
                "Cerrar",
                on_click=lambda e: (setattr(dlg, "open", False), page.update()),
            )
        ],
    )

    def _limpiar_completadas():
        nonlocal tareas
        tareas = [t for t in tareas if not t.get("completada", False)]
        guardar_y_refrescar()

    _render_lista()
    page._tareas_dlg = dlg
    if dlg not in page.overlay:
        page.overlay.append(dlg)
    dlg.open = True
    page.update()
