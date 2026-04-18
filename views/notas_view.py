"""
views/notas_view.py
Diálogo global de notas del local — accesible desde la AppBar (Ctrl+O).
Funciona como un listado de notas: agregar, editar inline, eliminar.
"""
import flet as ft


def mostrar_dialogo_notas(page: ft.Page, repo) -> None:
    """Abre el diálogo de notas generales del local como un listado editable."""
    notas: list = repo.get_notas()

    tf_nueva = ft.TextField(
        hint_text="Nueva nota... (Enter para agregar)",
        expand=True,
        dense=True,
        text_size=13,
        border_color=ft.Colors.TRANSPARENT,
        focused_border_color=ft.Colors.INDIGO_400,
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
        border_radius=8,
        autofocus=True,
    )

    lista = ft.ListView(expand=True, spacing=3, padding=ft.padding.only(right=6))

    def guardar_y_refrescar():
        repo.save_notas(notas)
        _render_lista()

    def agregar(e=None):
        texto = tf_nueva.value.strip()
        if not texto:
            return
        notas.append(texto)
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

    def eliminar(idx: int):
        notas.pop(idx)
        guardar_y_refrescar()

    def editar(idx: int, nuevo: str):
        if nuevo.strip():
            notas[idx] = nuevo.strip()
        guardar_y_refrescar()

    def _render_lista():
        lista.controls.clear()
        if not notas:
            lista.controls.append(ft.Container(
                content=ft.Text("Sin notas. Agrega recordatorios del negocio.",
                                color=ft.Colors.GREY_500, size=13, italic=True),
                alignment=ft.Alignment(0, 0), padding=20,
            ))
        else:
            for i, nota in enumerate(notas):
                lista.controls.append(_build_fila_nota(i, nota))
        try:
            lista.update()
        except Exception:
            pass

    def _build_fila_nota(i: int, nota: str) -> ft.Container:
        texto_ctrl = ft.Text(
            nota, size=13, expand=True, color=ft.Colors.WHITE,
        )

        tf_edit = ft.TextField(
            value=nota,
            dense=True,
            text_size=13,
            expand=True,
            border_color=ft.Colors.INDIGO_400,
            focused_border_color=ft.Colors.INDIGO_400,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            border_radius=6,
            height=34,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=2),
            visible=False,
        )

        btn_edit = ft.IconButton(
            icon=ft.Icons.EDIT_NOTE,
            icon_size=16, icon_color=ft.Colors.INDIGO_300,
            tooltip="Editar nota",
            width=30, height=30, padding=0,
        )

        def _toggle_edicion(e, idx=i):
            modo = not tf_edit.visible
            tf_edit.visible    = modo
            texto_ctrl.visible = not modo
            btn_edit.icon      = ft.Icons.CHECK if modo else ft.Icons.EDIT_NOTE
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
            if nuevo and nuevo != notas[idx]:
                editar(idx, nuevo)
            else:
                tf_edit.visible    = False
                texto_ctrl.visible = True
                btn_edit.icon      = ft.Icons.EDIT_NOTE
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
                ft.Icon(ft.Icons.NOTES, size=14, color=ft.Colors.INDIGO_300),
                ft.Stack([texto_ctrl, tf_edit], expand=True),
                btn_edit,
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=15, icon_color=ft.Colors.GREY_600,
                    tooltip="Eliminar nota",
                    on_click=lambda e, idx=i: eliminar(idx),
                    width=28, height=28, padding=0,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        )

        return ft.Container(
            content=fila_row,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.INDIGO_400),
            border=ft.border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.INDIGO_300)),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
        )

    tf_nueva.on_submit = agregar

    dlg = ft.AlertDialog(
        modal=False,
        title=ft.Row([
            ft.Icon(ft.Icons.NOTE_ALT_OUTLINED, color=ft.Colors.AMBER_400, size=22),
            ft.Text("Notas del Local", weight=ft.FontWeight.BOLD, size=16),
        ], spacing=8),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row([
                        tf_nueva,
                        ft.IconButton(
                            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                            icon_color=ft.Colors.WHITE,
                            bgcolor=ft.Colors.INDIGO_600,
                            on_click=agregar,
                            tooltip="Agregar nota",
                        ),
                    ], spacing=8),
                    ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
                    ft.Container(content=lista, expand=True),
                    ft.Row(
                        [ft.TextButton(
                            "Borrar todas",
                            icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                            icon_color=ft.Colors.RED_400,
                            on_click=lambda e: (_borrar_todas()),
                        )],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                tight=False, spacing=8,
            ),
            width=460,
            height=480,
        ),
        actions=[
            ft.FilledTonalButton(
                "Cerrar",
                on_click=lambda e: (setattr(dlg, "open", False), page.update()),
            )
        ],
    )

    def _borrar_todas():
        notas.clear()
        guardar_y_refrescar()

    _render_lista()
    page._notas_dlg = dlg
    if dlg not in page.overlay:
        page.overlay.append(dlg)
    dlg.open = True
    page.update()
