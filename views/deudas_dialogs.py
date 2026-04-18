"""
views/deudas_dialogs.py
Diálogos modales para la gestión de ítems de deuda y abonos.

  - dialogo_item        → crear/editar un ítem de deuda
  - dialogo_abono       → registrar un abono nuevo
  - dialogo_ver_abonos  → lista de abonos con nota, eliminar y ajustar monto
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable

import flet as ft

from models.deuda import Deuda, DeudaItem, Abono
from database.repositorio import Repositorio
from views.helpers import abrir_dlg, cerrar_dlg, snack
from views.deudas_tabla import crear_control_cantidad


# ─────────────────────────────────────────────────────────────── #
# Ítem de deuda (crear / editar)                                   #
# ─────────────────────────────────────────────────────────────── #

def dialogo_item(
    page: ft.Page,
    repo: Repositorio,
    deuda: Deuda,
    item: DeudaItem | None,
    on_done: Callable,
) -> None:
    es_nuevo = item is None

    nombre_f = ft.TextField(label="Producto *",       value="" if es_nuevo else item.nombre,     autofocus=True)
    cod_f    = ft.TextField(label="Observaciones",     value="" if es_nuevo else item.codigo_barras)
    precio_f = ft.TextField(label="Precio unitario *", value="" if es_nuevo else str(item.precio), keyboard_type=ft.KeyboardType.NUMBER)
    # ── Campo fecha con selector ─────────────────────────────────── #
    async def on_fecha_change(e):
        if e.control.value:
            fecha_f.value = e.control.value.strftime("%Y-%m-%d")
            fecha_f.update()

    picker = ft.DatePicker(
        on_change=on_fecha_change,
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
    )
    page.overlay.append(picker)

    async def abrir_picker(e):
        try:
            picker.value = datetime.strptime(fecha_f.value, "%Y-%m-%d")
        except Exception:
            picker.value = datetime.now()
        picker.open = True
        picker.update()

    fecha_f  = ft.TextField(
        label="Fecha",
        value=datetime.now().strftime("%Y-%m-%d") if es_nuevo else item.fecha,
        read_only=True, # Evitar edición manual para forzar el uso del calendario o mantener formato
        suffix=ft.IconButton(ft.Icons.CALENDAR_MONTH, on_click=abrir_picker),
    )
    error    = ft.Text("", color=ft.Colors.RED_400, size=12)

    control_ctd, cant_f = crear_control_cantidad(
        valor_inicial="1" if es_nuevo else str(item.cantidad)
    )

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Nuevo Producto" if es_nuevo else "Editar Producto"),
        content=ft.Column(
            [
                nombre_f,
                cod_f,
                ft.Column(
                    [ft.Text("Cantidad", size=12, color=ft.Colors.GREY_400), control_ctd],
                    spacing=4,
                ),
                precio_f,
                fecha_f,
                error,
            ],
            tight=True, spacing=10, width=360, scroll=ft.ScrollMode.AUTO,
        ),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    async def guardar(e) -> None:
        nombre = nombre_f.value.strip()
        if not nombre:
            error.value = "El nombre del producto es obligatorio."
            error.update()
            return
        try:
            precio   = float(precio_f.value.replace(",", "."))
            cantidad = int(cant_f.value or "1")
        except ValueError:
            error.value = "Precio y cantidad deben ser números válidos."
            error.update()
            return

        if es_nuevo:
            deuda.items.append(
                DeudaItem(
                    nombre=nombre,
                    codigo_barras=cod_f.value.strip(),
                    precio=precio,
                    cantidad=cantidad,
                    fecha=fecha_f.value.strip(),
                )
            )
        else:
            item.nombre        = nombre
            item.codigo_barras = cod_f.value.strip()
            item.precio        = precio
            item.cantidad      = cantidad
            item.fecha         = fecha_f.value.strip()

        repo.save_deuda(deuda)
        cerrar_dlg(page, dlg)
        on_done()

    for campo in (nombre_f, cod_f, precio_f, fecha_f, cant_f):
        campo.on_submit = guardar

    dlg.actions = [
        ft.TextButton("Cancelar", on_click=lambda e: cerrar_dlg(page, dlg)),
        ft.FilledButton("Guardar", on_click=guardar),
    ]
    abrir_dlg(page, dlg)


# ─────────────────────────────────────────────────────────────── #
# Registrar abono nuevo                                            #
# ─────────────────────────────────────────────────────────────── #

def dialogo_abono(
    page: ft.Page,
    repo: Repositorio,
    deuda: Deuda,
    on_done: Callable,
) -> None:
    from utils.calculos import calcular_saldo_pendiente, aplicar_abono

    saldo   = calcular_saldo_pendiente(deuda)
    monto_f = ft.TextField(
        label=f"Monto a abonar (saldo: $ {saldo:.2f})",
        autofocus=True,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    nota_f = ft.TextField(label="Nota (opcional)")
    fecha_f = ft.TextField(label="Fecha", value=datetime.now().strftime("%Y-%m-%d"))
    error  = ft.Text("", color=ft.Colors.RED_400, size=12)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.PAYMENTS_OUTLINED, color=ft.Colors.GREEN_400),
            ft.Text("Registrar Abono"),
        ], spacing=8),
        content=ft.Column([monto_f, fecha_f, nota_f, error], tight=True, spacing=10, width=320),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    async def guardar(e) -> None:
        try:
            monto = float(monto_f.value.replace(",", "."))
        except ValueError:
            error.value = "Ingresa un monto válido."
            error.update()
            return
        try:
            aplicar_abono(deuda, monto, nota_f.value.strip(), fecha_f.value.strip())
        except ValueError as ex:
            error.value = str(ex)
            error.update()
            return

        repo.save_deuda(deuda)
        cerrar_dlg(page, dlg)
        on_done()

    monto_f.on_submit = guardar
    nota_f.on_submit  = guardar

    dlg.actions = [
        ft.TextButton("Cancelar", on_click=lambda e: cerrar_dlg(page, dlg)),
        ft.FilledButton(
            "Registrar",
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700),
            on_click=guardar,
            autofocus=True,
        ),
    ]
    abrir_dlg(page, dlg)


# ─────────────────────────────────────────────────────────────── #
# Ver, editar y eliminar abonos                                    #
# ─────────────────────────────────────────────────────────────── #

def dialogo_ver_abonos(
    page: ft.Page,
    repo: Repositorio,
    deuda: Deuda,
    on_done: Callable,
) -> None:
    """
    Lista todos los abonos con su fecha, monto y nota.
    Permite:
      - Expandir cada fila para leer la nota completa
      - Eliminar un abono
      - Ajustar el monto de un abono
    """
    from utils.calculos import calcular_total_abonado, calcular_saldo_pendiente

    lista = ft.Column(tight=True, spacing=4, scroll=ft.ScrollMode.AUTO, height=320, width=440)
    dlg_vista = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.RECEIPT_LONG, color=ft.Colors.GREEN_300),
            ft.Text("Historial de abonos", size=16, weight=ft.FontWeight.BOLD),
        ], spacing=8),
        content=ft.Column(
            [lista],
            tight=True, spacing=8, width=460,
        ),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def _render_lista() -> None:
        """Re-dibuja la lista de abonos."""
        lista.controls.clear()

        if not deuda.abonos:
            lista.controls.append(ft.Text(
                "No hay abonos registrados.",
                size=13, color=ft.Colors.GREY_500, italic=True,
            ))
        else:
            for abono in list(deuda.abonos):
                _agregar_fila(abono)

        # Resumen al pie
        abonado = calcular_total_abonado(deuda)
        saldo   = calcular_saldo_pendiente(deuda)
        lista.controls.append(ft.Divider(color=ft.Colors.INDIGO_900))
        lista.controls.append(ft.Row([
            ft.Text(f"Total abonado: $ {abonado:.2f}", size=12, color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD, expand=True),
            ft.Text(f"Saldo: $ {saldo:.2f}",   size=12,
                    color=ft.Colors.AMBER_400 if saldo > 0 else ft.Colors.GREEN_400,
                    weight=ft.FontWeight.BOLD),
        ]))

        try:
            lista.update()
        except Exception:
            pass

    def _agregar_fila(abono: Abono) -> None:
        """Crea el control visual de un abono con nota expandible y acciones."""
        nota_txt = ft.Text(
            abono.nota if abono.nota else "— sin nota —",
            size=11,
            color=ft.Colors.GREY_400 if abono.nota else ft.Colors.GREY_700,
            italic=not bool(abono.nota),
            visible=False,
        )

        def _toggle_nota(e) -> None:
            nota_txt.visible = not nota_txt.visible
            e.control.icon = (
                ft.Icons.EXPAND_LESS if nota_txt.visible else ft.Icons.EXPAND_MORE
            )
            e.control.update()
            nota_txt.update()

        def _on_eliminar(e, a: Abono = abono) -> None:
            _confirmar_eliminar_abono(a)

        def _on_editar(e, a: Abono = abono) -> None:
            _editar_monto(a)

        fila = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            # Fecha
                            ft.Text(abono.fecha, size=11, color=ft.Colors.GREY_400, width=90),
                            # Monto
                            ft.Text(
                                f"$ {abono.monto:.2f}",
                                size=14, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREEN_400, expand=True,
                            ),
                            # Botón ver nota
                            ft.IconButton(
                                icon=ft.Icons.EXPAND_MORE,
                                icon_size=16, icon_color=ft.Colors.GREY_400,
                                tooltip="Ver nota",
                                on_click=_toggle_nota,
                                width=30, height=30, padding=0,
                            ),
                            # Botón editar monto
                            ft.IconButton(
                                icon=ft.Icons.EDIT_NOTE,
                                icon_size=16, icon_color=ft.Colors.INDIGO_300,
                                tooltip="Ajustar monto",
                                on_click=_on_editar,
                                width=30, height=30, padding=0,
                            ),
                            # Botón eliminar
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=16, icon_color=ft.Colors.RED_400,
                                tooltip="Eliminar abono",
                                on_click=_on_eliminar,
                                width=30, height=30, padding=0,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    nota_txt,
                ],
                spacing=2,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.GREEN_400),
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.GREEN_400)),
        )
        lista.controls.append(fila)

    # ── Confirmación de eliminación ───────────────────────────── #
    def _confirmar_eliminar_abono(abono: Abono) -> None:
        dlg_conf = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar abono"),
            content=ft.Text(
                f"¿Eliminar el abono de $ {abono.monto:.2f} del {abono.fecha}?\n"
                f"Nota: \"{abono.nota or 'sin nota'}\"\n\n"
                "Esta acción no se puede deshacer.",
                size=13,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
        )

        def eliminar(e) -> None:
            deuda.abonos = [a for a in deuda.abonos if a.id != abono.id]
            repo.save_deuda(deuda)
            dlg_conf.open = False
            page.update()
            _render_lista()
            on_done()

        dlg_conf.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: _cerrar_y_actualizar(dlg_conf)),
            ft.FilledButton(
                "Eliminar",
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700),
                on_click=eliminar,
            ),
        ]
        if dlg_conf not in page.overlay:
            page.overlay.append(dlg_conf)
        dlg_conf.open = True
        page.update()

    # ── Ajustar monto de abono ────────────────────────────────── #
    def _editar_monto(abono: Abono) -> None:
        monto_f = ft.TextField(
            label="Nuevo monto",
            value=str(abono.monto),
            autofocus=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        nota_f = ft.TextField(label="Nota", value=abono.nota)
        error  = ft.Text("", color=ft.Colors.RED_400, size=12)

        dlg_ed = ft.AlertDialog(
            modal=True,
            title=ft.Text("Ajustar abono"),
            content=ft.Column([monto_f, nota_f, error], tight=True, spacing=10, width=300),
            actions_alignment=ft.MainAxisAlignment.END,
        )

        async def guardar_edicion(e) -> None:
            try:
                nuevo_monto = float(monto_f.value.replace(",", "."))
                if nuevo_monto <= 0:
                    raise ValueError()
            except ValueError:
                error.value = "Ingresa un monto válido mayor a 0."
                error.update()
                return

            abono.monto = round(nuevo_monto, 2)
            abono.nota  = nota_f.value.strip()
            repo.save_deuda(deuda)
            dlg_ed.open = False
            page.update()
            _render_lista()
            on_done()

        monto_f.on_submit = guardar_edicion
        nota_f.on_submit  = guardar_edicion

        dlg_ed.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: _cerrar_y_actualizar(dlg_ed)),
            ft.FilledButton("Guardar", on_click=guardar_edicion),
        ]
        if dlg_ed not in page.overlay:
            page.overlay.append(dlg_ed)
        dlg_ed.open = True
        page.update()

    def _cerrar_y_actualizar(dlg) -> None:
        dlg.open = False
        page.update()

    def _abrir_nuevo_abono(e) -> None:
        """Abre dialogo_abono. Solo reabre el historial si todavía hay saldo."""
        dlg_vista.open = False
        page.update()

        def _tras_guardar():
            on_done()
            # Si el saldo llegó a 0, NO reabrir → la notificación de cuenta saldada queda visible
            if calcular_saldo_pendiente(deuda) > 0:
                _reabrir()

        dialogo_abono(page, repo, deuda, _tras_guardar)

    dlg_vista.actions = [
        ft.FilledTonalButton(
            "+ Nuevo abono",
            icon=ft.Icons.ADD,
            on_click=_abrir_nuevo_abono,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_800, color=ft.Colors.WHITE),
        ),
        ft.TextButton("Cerrar", on_click=lambda e: cerrar_dlg(page, dlg_vista)),
    ]

    def _reabrir():
        _render_lista()
        dlg_vista.open = True
        page.update()

    _render_lista()
    abrir_dlg(page, dlg_vista)
