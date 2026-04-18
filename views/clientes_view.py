"""
views/clientes_view.py
Panel lateral con la lista de clientes y CRUD en modales.
"""
from __future__ import annotations
from typing import Callable, Optional
import threading

import flet as ft

from models.cliente import Cliente
from database.repositorio import Repositorio
from views.helpers import abrir_dlg, cerrar_dlg

# Máximo de tarjetas renderizadas a la vez.
# Con más de 60 el render se vuelve lento en PCs de bajos recursos.
_MAX_VISIBLE = 60


# Modos de ordenamiento disponibles
_SORT_MODES = [
    ("deuda_desc",      ft.Icons.ARROW_DOWNWARD,     "Mayor deuda primero"),
    ("deuda_asc",       ft.Icons.ARROW_UPWARD,        "Menor deuda primero"),
    ("nombre_asc",      ft.Icons.SORT_BY_ALPHA,       "Nombre A → Z"),
    ("nombre_desc",     ft.Icons.SORT,                "Nombre Z → A"),
    ("ultimo_registro", ft.Icons.HISTORY,             "Último registro ingresado"),
    ("ultimo_cliente",  ft.Icons.PERSON_ADD_OUTLINED, "Último usuario registrado"),
]

# Cache de colores del degradado: ratio (0.0–1.0, 3 decimales) → color hex
# Evita recalcular el mismo color en cada refresco de la lista
_COLOR_CACHE: dict[int, str] = {}


class ClientesView(ft.Column):
    def __init__(
        self,
        repo: Repositorio,
        on_cliente_selected: Callable[[Cliente], None],
        page: ft.Page,
    ):
        super().__init__(spacing=0, expand=True)
        self._repo = repo
        self._on_selected = on_cliente_selected
        self._page = page
        self._cliente_activo: Optional[Cliente] = None
        self._busqueda    = ""
        self._sort_mode   = "deuda_desc"   # ordenamiento por defecto
        self._highlight_idx     = -1       # índice resaltado con flechas (-1 = ninguno)
        self._clientes_actuales = []       # lista visible actual [(cliente, saldo)]
        self._search_focused    = False    # True cuando el buscador tiene el foco

        self._clear_btn = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_size=16,
            icon_color=ft.Colors.GREY_400,
            tooltip="Limpiar búsqueda",
            visible=False,
            on_click=self._limpiar_busqueda,
            width=32, height=32, padding=0,
        )
        self._search_field = ft.TextField(
            hint_text="Buscar cliente…",
            prefix_icon=ft.Icons.SEARCH,
            suffix=self._clear_btn,
            border_radius=10,
            height=42,
            text_size=13,
            autofocus=True,
            on_change=self._on_busqueda,
            on_submit=self._on_search_submit,
            on_focus=lambda e: setattr(self, "_search_focused", True),
            on_blur=lambda e: setattr(self, "_search_focused", False),
            border_color=ft.Colors.INDIGO_300,
            focused_border_color=ft.Colors.INDIGO_400,
        )
        self._lista = ft.ListView(expand=True, spacing=4, padding=ft.padding.only(top=8))

        # Ícono de sort — se actualiza en _refresh_lista
        self._sort_icon = ft.Icons.ARROW_DOWNWARD
        self._sort_tooltip = "Mayor deuda primero"

        self._sort_btn = ft.PopupMenuButton(
            icon=ft.Icons.ARROW_DOWNWARD,
            icon_color=ft.Colors.INDIGO_300,
            tooltip="Ordenar lista",
            items=self._build_sort_items(),
        )

        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    "Clientes",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.INDIGO_200,
                                ),
                                ft.Row(
                                    [
                                        self._sort_btn,
                                        ft.IconButton(
                                            icon=ft.Icons.PERSON_ADD_ALT_1,
                                            icon_color=ft.Colors.AMBER_400,
                                            tooltip="Nuevo cliente",
                                            on_click=self._abrir_dialogo_nuevo,
                                        ),
                                    ],
                                    spacing=0,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        self._search_field,
                    ],
                    spacing=8,
                ),
                padding=ft.padding.all(12),
                bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            ),
            ft.Divider(height=1, color=ft.Colors.INDIGO_900),
            self._lista,
        ]

        self._refresh_lista()

    # ------------------------------------------------------------------ #
    # Sort items                                                           #
    # ------------------------------------------------------------------ #
    def _build_sort_items(self) -> list:
        items = []
        for mode, icon, label in _SORT_MODES:
            is_active = mode == self._sort_mode
            items.append(
                ft.PopupMenuItem(
                    content=ft.Row(
                        [
                            ft.Icon(
                                icon,
                                size=18,
                                color=ft.Colors.AMBER_400 if is_active else ft.Colors.GREY_400,
                            ),
                            ft.Text(
                                label,
                                weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                                color=ft.Colors.AMBER_300 if is_active else ft.Colors.WHITE,
                            ),
                            ft.Icon(ft.Icons.CHECK, size=14, color=ft.Colors.AMBER_400) if is_active else ft.Container(),
                        ],
                        spacing=8,
                    ),
                    on_click=lambda e, m=mode: self._set_sort(m),
                )
            )
        return items

    def _set_sort(self, mode: str):
        self._sort_mode = mode
        # Actualizar ícono y tooltip del botón
        for m, icon, label in _SORT_MODES:
            if m == mode:
                self._sort_btn.icon = icon
                self._sort_btn.tooltip = label
                break
        self._sort_btn.items = self._build_sort_items()
        try:
            self._sort_btn.update()
        except RuntimeError:
            pass
        self._refresh_lista()

    def _aplicar_orden(self, datos: list) -> list:
        if self._sort_mode == "deuda_desc":
            return sorted(datos, key=lambda x: x[1], reverse=True)
        elif self._sort_mode == "deuda_asc":
            return sorted(datos, key=lambda x: x[1])
        elif self._sort_mode == "nombre_asc":
            return sorted(datos, key=lambda x: x[0].nombre.lower())
        elif self._sort_mode == "nombre_desc":
            return sorted(datos, key=lambda x: x[0].nombre.lower(), reverse=True)
        elif self._sort_mode == "ultimo_registro":
            # Ordenar por fecha del último ítem registrado (más reciente primero)
            # get_ultimas_fechas_items() lee del cache en RAM — sin disco
            fechas = self._repo.get_ultimas_fechas_items()
            return sorted(datos, key=lambda x: fechas.get(x[0].id, ""), reverse=True)
        elif self._sort_mode == "ultimo_cliente":
            # Ordenar por fecha de creación del cliente (más reciente primero)
            return sorted(datos, key=lambda x: x[0].fecha_creacion, reverse=True)
        return datos

    # ------------------------------------------------------------------ #
    # Lista                                                                #
    # ------------------------------------------------------------------ #
    def _refresh_lista(self, *_):
        datos = self._repo.get_clientes_con_saldos()

        if self._busqueda:
            busq = self._busqueda.lower()
            datos = [(c, s) for c, s in datos if busq in c.nombre.lower()]

        datos = self._aplicar_orden(datos)

        max_saldo = max([s for _, s in datos] + [0.0])
        total     = len(datos)
        datos_visibles = datos[:_MAX_VISIBLE]

        # Guardar lista visible para navegación con flechas
        self._clientes_actuales = datos_visibles
        # Clampar el highlight al rango válido
        if self._clientes_actuales:
            self._highlight_idx = max(-1, min(self._highlight_idx, len(self._clientes_actuales) - 1))
        else:
            self._highlight_idx = -1

        self._lista.controls.clear()
        for idx, (cliente, saldo) in enumerate(datos_visibles):
            highlighted = (idx == self._highlight_idx)
            self._lista.controls.append(self._tarjeta(cliente, saldo, max_saldo, highlighted))

        if total > _MAX_VISIBLE:
            self._lista.controls.append(
                ft.Container(
                    content=ft.Text(
                        f"Mostrando {_MAX_VISIBLE} de {total}. Usa la búsqueda para filtrar.",
                        size=10, color="#555570", text_align=ft.TextAlign.CENTER,
                    ),
                    padding=ft.padding.symmetric(vertical=8),
                )
            )

        try:
            if self._lista.page:
                self._lista.update()
        except RuntimeError:
            pass

    def _get_color_deuda(self, saldo: float, max_saldo: float) -> str:
        """Interpolación verde→rojo con cache para no recalcular en cada refresco."""
        if saldo <= 0 or max_saldo <= 0:
            return "#4CAF50"
        # Reducimos a 256 niveles (1 byte) para que el cache sea efectivo
        nivel = int(min(1.0, saldo / max_saldo) * 255)
        if nivel in _COLOR_CACHE:
            return _COLOR_CACHE[nivel]
        ratio = nivel / 255
        r = int(76 + (244 - 76) * ratio)
        g = int(175 + (67 - 175) * ratio)
        b = int(80 + (54 - 80) * ratio)
        color = f"#{r:02x}{g:02x}{b:02x}"
        _COLOR_CACHE[nivel] = color
        return color

    def _tarjeta(self, cliente: Cliente, saldo: float, max_saldo: float,
                 highlight: bool = False) -> ft.Container:
        activo      = self._cliente_activo and self._cliente_activo.id == cliente.id
        color_deuda = self._get_color_deuda(saldo, max_saldo)

        menu_opciones = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            icon_size=20,
            icon_color=ft.Colors.GREY_400,
            tooltip="Opciones de usuario",
            items=[
                ft.PopupMenuItem(
                    content=ft.Row([ft.Icon(ft.Icons.EDIT_NOTE, size=18), ft.Text("Editar")]),
                    on_click=lambda e, c=cliente: self._abrir_dialogo_editar(c)
                ),
                ft.PopupMenuItem(
                    content=ft.Row([ft.Icon(ft.Icons.DELETE_OUTLINE, size=18, color=ft.Colors.RED_400), ft.Text("Eliminar", color=ft.Colors.RED_400)]),
                    on_click=lambda e, c=cliente: self._confirmar_eliminar(c)
                ),
            ]
        )

        zona_avatar_texto = ft.Row(
            [
                ft.CircleAvatar(
                    content=ft.Text(cliente.nombre[0].upper(), size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    bgcolor=color_deuda,
                    radius=18,
                ),
                ft.Column(
                    [
                        ft.Row([
                            ft.Text(cliente.nombre, size=13, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                            ft.Text(f" (${saldo:.2f})", size=11, color=color_deuda, weight=ft.FontWeight.BOLD) if saldo > 0 else ft.Container()
                        ], spacing=4, wrap=True),
                        ft.Text(cliente.telefono or "Sin teléfono", size=11, color=ft.Colors.GREY_400),
                    ],
                    spacing=1, expand=True,
                ),
            ],
            spacing=8, expand=True,
        )

        # Colores de fondo
        if highlight:
            bg_color = "#0d2137"          # azul-teal oscuro para el highlight de teclado
            borde    = ft.border.all(1, "#00bcd4")  # teal brillante
        elif activo:
            bg_color = "#2a1f3d" if saldo > 0 else "#1a1f3a"
            borde    = ft.border.all(1, color_deuda)
        elif saldo > 0:
            bg_color = "#181a2a"
            borde    = None
        else:
            bg_color = "#14151f"
            borde    = None

        # Almacenar estados originales para restaurarlos al quitar el highlight
        container_data = {
            "activo": activo,
            "color_deuda": color_deuda,
            "bg_normal": bg_color,
            "borde_normal": borde
        }

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=5, height=35,
                        bgcolor="#00bcd4" if highlight else color_deuda,
                        border_radius=3,
                    ),
                    ft.Row(
                        [zona_avatar_texto, menu_opciones],
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True,
                    ),
                ],
                spacing=8,
            ),
            bgcolor=bg_color,
            border_radius=8,
            border=borde,
            padding=ft.padding.only(left=8, top=6, bottom=6, right=2),
            on_click=lambda e, c=cliente: self._seleccionar(c),
            ink=False,
            data=container_data
        )

    def _on_busqueda(self, e):
        self._busqueda      = e.control.value
        self._highlight_idx = -1   # resetear highlight al cambiar la búsqueda
        # Mostrar/ocultar la X según haya texto
        tiene_texto = bool(self._busqueda)
        if self._clear_btn.visible != tiene_texto:
            self._clear_btn.visible = tiene_texto
            try:
                self._clear_btn.update()
            except Exception:
                pass
        # Debounce 200ms para no rebuildar en cada tecla en PCs lentas
        if hasattr(self, '_search_timer') and self._search_timer:
            self._search_timer.cancel()
        self._search_timer = threading.Timer(0.20, self._refresh_lista)
        self._search_timer.start()

    def _mover_highlight(self, delta: int) -> None:
        """Mueve el resaltado de teclado ↑↓ por la lista de clientes a velocidad luz."""
        n = len(self._clientes_actuales)
        if n == 0 or len(self._lista.controls) == 0:
            return
            
        old_idx = self._highlight_idx
        self._highlight_idx = (self._highlight_idx + delta) % n if self._highlight_idx >= 0 else (0 if delta > 0 else n - 1)
        new_idx = self._highlight_idx

        def _update_card(idx, is_highlight):
            if not (0 <= idx < len(self._lista.controls)): return
            card = self._lista.controls[idx]
            if not isinstance(card, ft.Container) or not card.data: return
            
            d = card.data
            if is_highlight:
                card.bgcolor = "#0d2137"
                card.border = ft.border.all(1, "#00bcd4")
                # El indicador lateral es el primer hijo del Row dentro del Container
                card.content.controls[0].bgcolor = "#00bcd4"
            else:
                card.bgcolor = d["bg_normal"]
                card.border = d["borde_normal"]
                card.content.controls[0].bgcolor = d["color_deuda"]
            
            try:
                card.update()
            except:
                pass

        _update_card(old_idx, False)
        _update_card(new_idx, True)

        try:
            self._lista.scroll_to(item_index=self._highlight_idx, duration=50)
        except:
            pass

    def _seleccionar_highlight(self, *_) -> None:
        """Selecciona el cliente resaltado (o el primero si ninguno está resaltado)."""
        if self._clientes_actuales:
            idx = self._highlight_idx if self._highlight_idx >= 0 else 0
            if idx < len(self._clientes_actuales):
                cliente, _ = self._clientes_actuales[idx]
                self._highlight_idx = -1
                self._seleccionar(cliente)

    def _on_search_submit(self, e=None) -> None:
        """Enter en el buscador: selecciona el cliente resaltado o el primero."""
        self._seleccionar_highlight()

    def _limpiar_busqueda(self, e=None):
        """Limpia el campo de búsqueda y oculta la X."""
        self._busqueda = ""
        self._search_field.value = ""
        self._clear_btn.visible = False
        try:
            self._search_field.update()
        except Exception:
            pass
        self._refresh_lista()

    def _seleccionar(self, cliente: Cliente):
        self._cliente_activo = cliente
        self._refresh_lista()
        self._on_selected(cliente)

    def _abrir_dialogo_nuevo(self, e=None):
        self._abrir_dialogo(None)

    def _abrir_dialogo_editar(self, cliente: Cliente):
        self._abrir_dialogo(cliente)

    def _abrir_dialogo(self, cliente: Optional[Cliente]):
        es_nuevo = cliente is None
        nombre_f = ft.TextField(label="Nombre *", value="" if es_nuevo else cliente.nombre, autofocus=True)
        tel_f = ft.TextField(label="Teléfono", value="" if es_nuevo else cliente.telefono)
        dir_f = ft.TextField(label="Dirección", value="" if es_nuevo else cliente.direccion)
        error_txt = ft.Text("", color=ft.Colors.RED_400, size=12)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo Cliente" if es_nuevo else "Editar Cliente"),
            content=ft.Column([nombre_f, tel_f, dir_f, error_txt], tight=True, spacing=12, width=340),
            actions_alignment=ft.MainAxisAlignment.END,
        )

        def guardar(e):
            nombre = nombre_f.value.strip()
            if not nombre:
                error_txt.value = "El nombre es obligatorio."
                error_txt.update()
                return
            if es_nuevo:
                nuevo_cliente = Cliente(nombre=nombre, telefono=tel_f.value.strip(), direccion=dir_f.value.strip())
                self._repo.save_cliente(nuevo_cliente)
                cerrar_dlg(self._page, dlg)
                self._seleccionar(nuevo_cliente)
            else:
                cliente.nombre = nombre
                cliente.telefono = tel_f.value.strip()
                cliente.direccion = dir_f.value.strip()
                self._repo.save_cliente(cliente)
                cerrar_dlg(self._page, dlg)
                self._refresh_lista()

                if self._cliente_activo and self._cliente_activo.id == cliente.id:
                    self._on_selected(cliente)

        nombre_f.on_submit = guardar
        tel_f.on_submit = guardar
        dir_f.on_submit = guardar

        dlg.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: cerrar_dlg(self._page, dlg)),
            ft.FilledButton("Guardar", on_click=guardar),
        ]
        abrir_dlg(self._page, dlg)

    def _confirmar_eliminar(self, cliente: Cliente):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar cliente"),
            content=ft.Text(f"¿Eliminar a {cliente.nombre} y todas sus deudas?\nEsta acción no se puede deshacer."),
            actions_alignment=ft.MainAxisAlignment.END,
        )

        def eliminar(e):
            self._repo.delete_cliente(cliente.id)
            if self._cliente_activo and self._cliente_activo.id == cliente.id:
                self._cliente_activo = None
                self._on_selected(None)
            cerrar_dlg(self._page, dlg)
            self._refresh_lista()

        dlg.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: cerrar_dlg(self._page, dlg)),
            ft.FilledButton(
                "Eliminar",
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700),
                on_click=eliminar,
            ),
        ]
        abrir_dlg(self._page, dlg)
