"""
views/deudas_tabla.py
Constructores de widgets para la tabla de productos en DeudasView.

Funciones puras: reciben datos y callbacks, devuelven controles Flet.
No contienen estado propio ni referencias a la vista padre.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import flet as ft

from models.cliente import Cliente
from models.deuda import Deuda, DeudaItem
from utils.calculos import calcular_total, calcular_total_abonado, calcular_saldo_pendiente


_HOY = datetime.now().strftime("%Y-%m-%d")

# ─────────────────────────────────────────────────────────────── #
# Helpers internos                                                 #
# ─────────────────────────────────────────────────────────────── #

def tf_celda(
    value: str,
    hint: str = "",
    width: int = None,
    keyboard_type=ft.KeyboardType.TEXT,
    on_change=None,
    on_blur=None,
) -> ft.TextField:
    """Estilo compartido para celdas editables de la tabla."""
    kwargs = dict(
        value=value,
        hint_text=hint,
        dense=True,
        text_size=13,
        border_color=ft.Colors.TRANSPARENT,
        focused_border_color=ft.Colors.INDIGO_400,
        border_radius=6,
        height=38,
        content_padding=ft.padding.symmetric(horizontal=6, vertical=4),
        keyboard_type=keyboard_type,
        on_change=on_change,
        on_blur=on_blur,
    )
    if width:
        kwargs["width"] = width
    return ft.TextField(**kwargs)


def crear_control_cantidad(
    valor_inicial: str = "1",
    on_submit=None,
    width: int = 120,
) -> tuple[ft.Row, ft.TextField]:
    """
    Control de cantidad con botones + y –.
    Devuelve (Row widget, TextField interno) para que el llamador
    pueda asignar on_submit y leer el valor.
    """
    txt_cantidad = ft.TextField(
        value=valor_inicial,
        width=50,
        height=36,
        dense=True,
        text_size=13,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=ft.Colors.TRANSPARENT,
        focused_border_color=ft.Colors.AMBER_400,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
        content_padding=ft.padding.all(0),
        on_submit=on_submit,
    )

    def modificar(delta: int) -> None:
        try:
            nuevo = max(0, int(txt_cantidad.value or "0") + delta)
            txt_cantidad.value = str(nuevo)
            txt_cantidad.update()
        except ValueError:
            txt_cantidad.value = "1"
            txt_cantidad.update()

    control = ft.Row(
        [
            ft.IconButton(icon=ft.Icons.REMOVE, icon_size=14, icon_color=ft.Colors.RED_400,
                          on_click=lambda _: modificar(-1), width=28, height=28, padding=0),
            txt_cantidad,
            ft.IconButton(icon=ft.Icons.ADD,    icon_size=14, icon_color=ft.Colors.GREEN_400,
                          on_click=lambda _: modificar(1),  width=28, height=28, padding=0),
        ],
        spacing=0,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        width=width,
    )
    return control, txt_cantidad


# ─────────────────────────────────────────────────────────────── #
# Constructores de secciones de la vista                          #
# ─────────────────────────────────────────────────────────────── #

def build_barra_superior(
    cliente: Cliente,
    deuda: Deuda,
    on_abono=None,
) -> ft.Container:
    """Barra superior con nombre del cliente y chips de totales.
    Si se pasa on_abono, el chip ABONADO se vuelve clickable."""
    total   = calcular_total(deuda)
    abonado = calcular_total_abonado(deuda)
    saldo   = calcular_saldo_pendiente(deuda)

    def chip(label: str, valor: float, color, clickable: bool = False, click_cb=None):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(label, size=10, color=ft.Colors.GREY_400),
                    ft.Text(f"$ {valor:.2f}", size=16, weight=ft.FontWeight.BOLD, color=color),
                ],
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            bgcolor=ft.Colors.with_opacity(0.08, color),
            border_radius=10,
            border=ft.border.all(
                1,
                ft.Colors.with_opacity(0.6 if clickable else 0.3, color),
            ),
            ink=clickable,
            on_click=click_cb if clickable else None,
            tooltip="Ver y gestionar abonos" if clickable else None,
        )

    return ft.Container(
        content=ft.ResponsiveRow(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(cliente.nombre, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                            ft.Text(
                                cliente.telefono or cliente.direccion or "Sin datos adicionales",
                                size=12, color=ft.Colors.GREY_400,
                            ),
                        ],
                        spacing=2,
                    ),
                    col={"sm": 12, "md": 6},
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            chip("TOTAL DEUDA", total, ft.Colors.RED_400),
                            *(  # Solo mostrar ABONADO si hay abonos
                                [chip("ABONADO", abonado, ft.Colors.GREEN_400,
                                      clickable=on_abono is not None, click_cb=on_abono)]
                                if abonado > 0 else []
                            ),
                            chip("SALDO", saldo, ft.Colors.AMBER_400 if saldo > 0 else ft.Colors.GREEN_400),
                        ],
                        spacing=12,
                        wrap=True,
                    ),
                    col={"sm": 12, "md": 6},
                    alignment=ft.Alignment(1, 0),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
    )


def build_header_tabla() -> ft.Container:
    """Fila de cabecera de la tabla de productos."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(width=36),  # espacio para indicador + checkbox
                ft.Text("Producto",      weight=ft.FontWeight.BOLD, size=12, expand=3,  color=ft.Colors.INDIGO_200),
                ft.Text("Ctd.",          weight=ft.FontWeight.BOLD, size=12, width=48,  color=ft.Colors.INDIGO_200, text_align=ft.TextAlign.CENTER),
                ft.Text("Precio $",      weight=ft.FontWeight.BOLD, size=12, width=68,  color=ft.Colors.INDIGO_200, text_align=ft.TextAlign.RIGHT),
                ft.Text("Subtotal $",    weight=ft.FontWeight.BOLD, size=12, width=80,  color=ft.Colors.AMBER_300,  text_align=ft.TextAlign.RIGHT),
                ft.Text("Fecha",         weight=ft.FontWeight.BOLD, size=12, width=96,  color=ft.Colors.INDIGO_200, text_align=ft.TextAlign.CENTER),
                ft.Text("Observaciones", weight=ft.FontWeight.BOLD, size=12, expand=2,  color=ft.Colors.INDIGO_200),
                ft.Container(width=70),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.INDIGO_800),
        border_radius=ft.border_radius.only(top_left=10, top_right=10),
    )


def build_fila_item(
    item: DeudaItem,
    on_edit: Callable,
    on_delete: Callable,
    pago_aplicado: float = 0.0,
    seleccionado: bool = False,
    on_toggle_seleccion: Optional[Callable] = None,
) -> ft.Container:
    """Una fila de producto en la tabla (modo lectura).

    - Se resalta con color llamativo si la fecha es hoy.
    - Muestra checkbox de selección para abono selectivo.
    """
    es_hoy     = item.fecha == _HOY
    tachado    = pago_aplicado >= item.subtotal and item.subtotal > 0
    es_parcial = pago_aplicado > 0 and not tachado

    estilo      = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if tachado else None
    color_texto = ft.Colors.GREY_600 if tachado else None

    texto_nombre = item.nombre
    if es_parcial:
        falta = item.subtotal - pago_aplicado
        texto_nombre = f"{item.nombre}\n└ Abono: ${pago_aplicado:.2f} | Resta: ${falta:.2f}"
        color_texto  = ft.Colors.INDIGO_300

    color_secundario = ft.Colors.GREY_600 if tachado else ft.Colors.GREY_400
    color_destacado  = ft.Colors.GREY_600 if tachado else ft.Colors.AMBER_300

    # ── Fondo de la fila ──────────────────────────────────────────── #
    if seleccionado:
        fondo       = "#1e3a2f"
        borde_color = ft.Colors.GREEN_500
        borde_ancho = 1
    elif es_hoy:
        fondo       = "#162838"   # azul-verde oscuro sutil para hoy
        borde_color = "#2d6a4f"   # verde sutil
        borde_ancho = 1
    elif tachado:
        fondo       = ft.Colors.with_opacity(0.02, ft.Colors.WHITE)
        borde_color = ft.Colors.TRANSPARENT
        borde_ancho = 0
    else:
        fondo       = None
        borde_color = ft.Colors.TRANSPARENT
        borde_ancho = 0

    # Indicador lateral de "hoy" (bolita verde sutil)
    indicador_hoy = ft.Container(
        width=4, height=36,
        bgcolor="#52b788",
        border_radius=4,
    ) if (es_hoy and not seleccionado) else ft.Container(width=4)

    # Checkbox de selección para abono selectivo
    chk = ft.Checkbox(
        value=seleccionado,
        on_change=(lambda e, iid=item.id: on_toggle_seleccion(iid)) if on_toggle_seleccion else None,
        active_color=ft.Colors.GREEN_400,
        width=28,
        height=28,
        disabled=tachado,
    )

    return ft.Container(
        content=ft.Row(
            [
                indicador_hoy,
                chk,
                ft.Text(texto_nombre,              size=13, expand=3, style=estilo, color=color_texto),
                ft.Text(str(item.cantidad),        size=13, width=48, text_align=ft.TextAlign.CENTER, style=estilo, color=color_texto),
                ft.Text(f"$ {item.precio:.2f}",    size=13, width=68, text_align=ft.TextAlign.RIGHT,  style=estilo, color=color_texto),
                ft.Text(
                    f"$ {item.subtotal:.2f}", size=13, width=80,
                    text_align=ft.TextAlign.RIGHT,
                    color=color_destacado,
                    weight=ft.FontWeight.W_500,
                    style=estilo,
                ),
                ft.Text(item.fecha,                size=12, color=color_secundario, width=96, text_align=ft.TextAlign.CENTER, style=estilo),
                ft.Text(item.codigo_barras or "—", size=12, color=color_secundario, expand=2, style=estilo),
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.EDIT_NOTE,
                            icon_size=18,
                            icon_color=ft.Colors.INDIGO_300,
                            tooltip="Editar",
                            on_click=on_edit,
                            disabled=tachado,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_size=18,
                            icon_color=ft.Colors.RED_400,
                            tooltip="Eliminar",
                            on_click=on_delete,
                        ),
                    ],
                    spacing=0, width=70, tight=True, alignment=ft.MainAxisAlignment.END,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=5),
        bgcolor=fondo,
        border=ft.border.all(borde_ancho, borde_color) if borde_ancho > 0 else None,
        border_radius=6 if (es_hoy or seleccionado) else 0,
        ink=not tachado,
        on_click=on_edit if not tachado else None,
    )


def build_panel_abono_selectivo(
    items_seleccionados: list,
    on_confirmar: Callable,
    on_seleccionar_fecha: Callable,
    on_limpiar: Callable,
    pagos_aplicados: dict = None,
) -> ft.Container:
    """
    Panel que aparece cuando hay ítems seleccionados para abono selectivo.
    Muestra la suma restando lo que ya se abonó parcialmente.
    """
    if pagos_aplicados is None:
        pagos_aplicados = {}
        
    suma = sum(max(0, i.subtotal - pagos_aplicados.get(i.id, 0.0)) for i in items_seleccionados)
    suma = round(suma, 2)
    n    = len(items_seleccionados)

    fecha_picker = ft.DatePicker(
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
        on_change=lambda e: on_seleccionar_fecha(
            e.control.value.strftime("%Y-%m-%d") if e.control.value else None
        ),
    )

    def abrir_datepicker(e):
        if fecha_picker not in e.page.overlay:
            e.page.overlay.append(fecha_picker)
        fecha_picker.open = True
        e.page.update()

    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.CHECKLIST, color=ft.Colors.GREEN_400, size=20),
                ft.Column(
                    [
                        ft.Text(
                            f"{n} producto{'s' if n != 1 else ''} seleccionado{'s' if n != 1 else ''}",
                            size=11, color=ft.Colors.GREY_400,
                        ),
                        ft.Text(
                            f"$ {suma:.2f}",
                            size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400,
                        ),
                    ],
                    spacing=1,
                    expand=True,
                ),
                ft.ElevatedButton(
                    "Auto por fecha",
                    icon=ft.Icons.CALENDAR_TODAY_OUTLINED,
                    on_click=abrir_datepicker,
                    style=ft.ButtonStyle(bgcolor="#1a2a52", color=ft.Colors.AMBER_300),
                    height=38,
                ),
                ft.FilledButton(
                    "Confirmar abono",
                    icon=ft.Icons.PAYMENTS_OUTLINED,
                    on_click=on_confirmar,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                    height=38,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLEAR,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Limpiar selección",
                    on_click=on_limpiar,
                    width=36, height=36,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        bgcolor="#0e2a1a",
        border=ft.border.all(1, ft.Colors.GREEN_800),
        border_radius=8,
        margin=ft.margin.only(top=4),
        visible=n > 0,
    )


def build_fila_totales(deuda: Deuda) -> ft.Container:
    """Fila de total al pie de la tabla."""
    total = calcular_total(deuda)
    return ft.Container(
        content=ft.Row(
            [
                ft.Text("TOTAL DEUDA", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400, size=13),
                ft.Container(width=12),
                ft.Text(
                    f"$ {total:.2f}",
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.RED_400,
                    size=15,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.INDIGO_900),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10),
    )


def build_barra_inferior(on_abono: Callable, on_pdf: Callable,
                         on_whatsapp: Callable = None,
                         on_saldar: Callable = None,
                         on_reset: Callable = None) -> ft.Container:
    """Barra de acciones inferior."""
    botones_izq = []
    if on_reset:
        botones_izq.append(
            ft.IconButton(
                icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                icon_color=ft.Colors.RED_300,
                icon_size=20,
                tooltip="Reiniciar lista de productos (borrar todo)",
                on_click=on_reset,
            )
        )

    color_saldar = "#3f51b5"
    color_abono  = "#2e7d32"
    color_pdf    = "#455a64"
    color_wa     = "#25D366"

    def _btn_prop(texto, icon, color, click_fn):
        return ft.FilledButton(
            content=ft.Row(
                [
                    ft.Icon(icon, size=18),
                    ft.Text(texto, size=13, weight=ft.FontWeight.W_500),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            width=165,
            height=44,
            on_click=click_fn,
            style=ft.ButtonStyle(
                bgcolor=color,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.all(0),
            ),
        )

    botones_der = [
        _btn_prop("Liquidar [Ctrl+S]", ft.Icons.CHECK_CIRCLE,   color_saldar, on_saldar),
        _btn_prop("Abonar [Ctrl+A]",   ft.Icons.ADD_CARD,       color_abono,  on_abono),
        _btn_prop("PDF [Ctrl+P]",      ft.Icons.PICTURE_AS_PDF, color_pdf,    on_pdf),
    ]
    if on_whatsapp:
        botones_der.append(
            _btn_prop("WhatsApp [Ctrl+W]", ft.Icons.SEND_ROUNDED, color_wa, on_whatsapp)
        )

    return ft.Container(
        content=ft.ResponsiveRow(
            [
                ft.Container(
                    content=ft.Row(botones_izq, alignment=ft.MainAxisAlignment.START),
                    col={"sm": 12, "md": 1},
                ),
                ft.Container(
                    content=ft.Row(botones_der, spacing=12, wrap=True, alignment=ft.MainAxisAlignment.END),
                    col={"sm": 12, "md": 11},
                    alignment=ft.Alignment(1, 0),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=20, vertical=12),
    )
