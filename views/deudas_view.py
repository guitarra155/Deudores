"""
views/deudas_view.py
Vista principal de deudas. Solo contiene estado y coordinación.

Los constructores de widgets están en deudas_tabla.py.
Los diálogos modales están en deudas_dialogs.py.
"""
from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime
from typing import Optional

import flet as ft

from models.cliente import Cliente
from models.deuda import Deuda, DeudaItem
from database.repositorio import Repositorio
from utils.calculos import calcular_total, calcular_total_abonado, calcular_saldo_pendiente
from views.helpers import snack
from views.deudas_tabla import (
    build_barra_superior,
    build_barra_inferior,
    build_header_tabla,
    build_fila_item,
    build_fila_totales,
    build_panel_abono_selectivo,
    crear_control_cantidad,
)
from core.keyboard import _bucle_auto_repetir
from views.deudas_dialogs import dialogo_item, dialogo_abono, dialogo_ver_abonos
from core.whatsapp import WhatsAppManager


class DeudasView(ft.Column):
    def __init__(self, repo: Repositorio, page: ft.Page, get_pdf_generator,
                 on_add_cliente=None, catalogo=None, on_deuda_changed=None):
        super().__init__(expand=True, spacing=0)
        self._repo             = repo
        self._page             = page
        self._get_pdf          = get_pdf_generator
        self._on_add_cliente   = on_add_cliente
        self._catalogo         = catalogo
        self._on_deuda_changed = on_deuda_changed   # callback → actualiza lista clientes

        self._cliente: Optional[Cliente] = None
        self._deuda:   Optional[Deuda]   = None

        # ── Estado del abono selectivo ───────────────────────────── #
        self._selected_items: set = set()   # IDs de ítems marcados para abono selectivo
        # Mapa {item_id: (container_fila, item)} para actualización sin rebuild
        self._item_containers: dict = {}
        # Referencia al panel de abono selectivo para actualizar sin rebuild
        self._panel_selectivo_ref: Optional[ft.Container] = None

        # ── Estado del autocomplete ──────────────────────────────── #
        self._sug_container: Optional[ft.Container] = None
        self._sug_items:     list[str]              = []
        self._sug_idx:       int                    = -1
        self._nombre_foco:   bool                   = False
        self._nombre_field:  Optional[ft.TextField] = None
        self._ctd_field:     Optional[ft.TextField] = None
        # Evita que on_blur cierre el panel antes del clic en una sugerencia (ratón).
        self._sug_blur_token: int = 0
        # Column con scroll donde están ítems + sugerencias + fila de entrada (autoscroll al escribir).
        self._rows_list_scroll: Optional[ft.Column] = None
        self._sug_last_rebuild_n: int = -1
        self._ignorar_texto: str = "" # previene reapertura accidental del autocompletar al seleccionar
        # Nota: page.on_keyboard_event se asigna en main.py (handler global)

        self._placeholder = self._build_placeholder()
        self.controls = [self._placeholder]

    async def _focus_campo_cantidad(self) -> None:
        if self._ctd_field:
            await self._ctd_field.focus()

    def _schedule_focus_cantidad(self) -> None:
        """Enfoca cantidad desde callbacks sync (p. ej. clic en sugerencia)."""
        try:
            self._page.run_task(self._focus_campo_cantidad)
        except Exception:
            pass

    async def _scroll_entrada_a_vista(self) -> None:
        """Baja el scroll hasta la fila de producto (sugerencias + campos)."""
        col = self._rows_list_scroll
        if col is None:
            return
        try:
            await col.scroll_to(offset=-1, duration=200)
        except Exception:
            pass

    def _schedule_scroll_entrada_a_vista(self) -> None:
        try:
            self._page.run_task(self._scroll_entrada_a_vista)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────── #
    # Pantalla de bienvenida                                       #
    # ─────────────────────────────────────────────────────────── #

    def _build_placeholder(self) -> ft.Container:
        """Pantalla de bienvenida con botón prominente para agregar nuevo cliente."""

        def _on_nuevo(e):
            if self._on_add_cliente:
                self._on_add_cliente()

        btn_nuevo = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.PERSON_ADD_ALT_1, color=ft.Colors.WHITE, size=25),
                    ft.Text(
                        "Agregar nuevo cliente",
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                    ),
                ],
                spacing=5,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            width=300,
            bgcolor=ft.Colors.AMBER_700,
            border_radius=14,
            padding=ft.padding.symmetric(horizontal=10, vertical=20),
            on_click=_on_nuevo,
            ink=True,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=50,    # reducido de 18 → 6 (menos GPU)
                color="#cc7700",  # hex fijo, sin with_opacity
                offset=ft.Offset(0, 5),
            ),
        )

        def _atajo(tecla: str, desc: str):
            return ft.Row(
                [
                    ft.Container(
                        content=ft.Text(
                            tecla, size=11,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.INDIGO_200,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        bgcolor="#1a2040",
                        border_radius=6,
                        border=ft.border.all(1, "#2d3560"),
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        width=110,
                    ),
                    ft.Text(desc, size=11, color="#888899", expand=True),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        import os
        
        def pick_logo(e):
            import tkinter as tk
            from tkinter import filedialog
            import shutil
            
            # Abre el dialogo nativo de windows sin involucrar al cliente de Flet
            root = tk.Tk()
            root.withdraw()
            # Forzamos que la ventana aparezca por encima
            root.attributes('-topmost', True)
            
            ruta_origen = filedialog.askopenfilename(
                title="Selecciona tu logotipo o imagen",
                filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.webp"), ("Todos los archivos", "*.*")]
            )
            root.destroy()
            
            if ruta_origen:
                import time
                assets_dir = os.path.join(os.getcwd(), "assets")
                os.makedirs(assets_dir, exist_ok=True)
                
                config = self._repo.get_config()
                old_logo = config.get("logo_portada")
                if old_logo and os.path.exists(old_logo):
                    try:
                        os.remove(old_logo)
                    except Exception:
                        pass
                
                ext = os.path.splitext(ruta_origen)[1]
                ruta_destino = os.path.join(assets_dir, f"logo_custom_{int(time.time())}{ext}")
                shutil.copy2(ruta_origen, ruta_destino)
                
                config["logo_portada"] = ruta_destino
                self._repo.save_config(config)
                
                # Actualizar el componente visual correcto (pantalla de inicio)
                self._placeholder = self._build_placeholder()
                if self._cliente is None:
                    self.controls = [self._placeholder]
                    self.update()

        config = self._repo.get_config()
        version_str = config.get("version", "2.2.1 (Modular)")
        logo_path = config.get("logo_portada", "")
        if logo_path and os.path.exists(logo_path):
            logo_control = ft.Image(src=logo_path, fit="cover", width=235, height=115, border_radius=20)
        else:
            logo_control = ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, size=44, color=ft.Colors.INDIGO_300)

        col_izq = ft.Column(
            [
                ft.Container(
                    content=logo_control,
                    width=240, height=120,
                    margin=ft.margin.only(top=-20),
                    border_radius=20,
                    bgcolor="#1a1f40",
                    alignment=ft.Alignment(0, 0),
                    on_click=pick_logo,
                    tooltip="Clic para cambiar el logotipo",
                    ink=True,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Bienvenido a DeudorPro", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_200, text_align=ft.TextAlign.CENTER),
                            ft.Text("Gestiona los fiados de tu negocio\nde forma rápida y sencilla", size=13, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    margin=ft.margin.only(top=-20),
                ),
                btn_nuevo,
                ft.Text("— o selecciona un cliente existente a la izquierda —", size=11, color=ft.Colors.GREY_700, italic=True),
                ft.Container(height=10),
                ft.Text(f"Versión {version_str}\nCreado por Guitarra Jhon", size=10, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=22,
        )

        tarjeta_atajos = ft.Container(
            content=ft.Column(
                [
                    ft.Row([ft.Icon(ft.Icons.KEYBOARD_OUTLINED, size=15, color=ft.Colors.INDIGO_300), ft.Text("Atajos de teclado", size=12, color=ft.Colors.INDIGO_300, weight=ft.FontWeight.BOLD)], spacing=6),
                    ft.Divider(height=1, color="#1e2035"),
                    _atajo("Ctrl + N",  "Nuevo cliente"),
                    _atajo("Ctrl + K",  "Enfocar buscador de clientes"),
                    _atajo("Ctrl + L",  "Lista de faltantes / compras"),
                    _atajo("Ctrl + O",  "Notas del local"),
                    _atajo("Ctrl + T",  "Tareas del local"),
                    _atajo("Escape",    "Cerrar diálogo / volver al inicio"),
                    ft.Divider(height=1, color="#1e2035"),
                    ft.Text("Con cliente seleccionado:", size=10, color="#555570", italic=True),
                    _atajo("Ctrl + A",  "Registrar abono"),
                    _atajo("Ctrl + S",  "Liquidar deuda (Saldar)"),
                    _atajo("Ctrl + P",  "Exportar PDF"),
                    _atajo("Ctrl + W",  "Enviar por WhatsApp"),
                    ft.Divider(height=1, color="#1e2035"),
                    ft.Text("En campo de producto:", size=10, color="#555570", italic=True),
                    _atajo("↑ ↓",       "Navegar sugerencias"),
                    _atajo("Tab",        "Seleccionar sugerencia"),
                    _atajo("Enter",      "Guardar producto"),
                ],
                spacing=6,
                tight=True,
            ),
            bgcolor="#0e1020",
            border_radius=12,
            border=ft.border.all(1, "#1e2035"),
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            width=320,
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.ResponsiveRow(
                        [
                            ft.Container(col_izq, col={"sm": 12, "md": 12, "lg": 6, "xl": 6}, alignment=ft.Alignment(0, 0)),
                            ft.Container(tarjeta_atajos, col={"sm": 12, "md": 12, "lg": 6, "xl": 6}, alignment=ft.Alignment(0, 0), padding=ft.padding.only(top=30)),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.Alignment(0, 0),
            padding=ft.padding.all(30),
        )

    # ─────────────────────────────────────────────────────────── #
    # API pública                                                  #
    # ─────────────────────────────────────────────────────────── #

    def cargar_cliente(self, cliente: Optional[Cliente]) -> None:
        self._cliente = cliente
        self._ocultar_sug()
        if cliente is None:
            self.controls = [self._placeholder]
        else:
            self._deuda = self._repo.get_deuda(cliente.id)
            self._render()
        self.update()

    def refrescar_datos_desde_red(self) -> None:
        """Tras recargar clientes.json desde disco (otra PC), repinta esta vista."""
        self._ocultar_sug()
        if self._cliente is None:
            try:
                if self.page:
                    self.update()
            except RuntimeError:
                pass
            return
        c = self._repo.get_cliente(self._cliente.id)
        if c is None:
            self.cargar_cliente(None)
            return
        self._cliente = c
        self._deuda = self._repo.get_deuda(c.id)
        self._render()
        try:
            if self.page:
                self.update()
        except RuntimeError:
            pass

    # ─────────────────────────────────────────────────────────── #
    # Render                                                       #
    # ─────────────────────────────────────────────────────────── #

    def _render(self) -> None:
        _wa = self._enviar_whatsapp if (self._cliente and self._cliente.telefono) else None
        
        contenido = ft.Container(
            content=ft.Column(
                [
                    build_barra_superior(self._cliente, self._deuda, on_abono=self._on_abono),
                    ft.Divider(height=1, color=ft.Colors.INDIGO_900),
                    ft.Container(content=self._tabla_scroll(), expand=True, padding=ft.padding.all(16)),
                    ft.Divider(height=1, color=ft.Colors.INDIGO_900),
                    build_barra_inferior(
                        self._on_abono,
                        self._exportar_pdf,
                        on_whatsapp=_wa,
                        on_saldar=self._on_saldar_deuda,
                        on_reset=self._on_resetear_deuda,
                    ),
                ],
            ),
            expand=True,
        )

        self.controls = [
            contenido
        ]

    def _tabla_scroll(self) -> ft.Column:
        from utils.calculos import calcular_pagos_aplicados
        rows_list = ft.Column(spacing=0, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

        # Usar la nueva función que respeta selectivos > generales
        pagos = calcular_pagos_aplicados(self._deuda)

        # Guardar un map {item_id: container_fila} para actualización directa
        self._item_containers = {}
        
        # Ordenar ítems por fecha (del más antiguo al más nuevo)
        sorted_items = sorted(self._deuda.items, key=lambda x: x.fecha)
        
        for item in sorted_items:
            pago_aplicado = pagos.get(item.id, 0.0)
            seleccionado  = item.id in self._selected_items

            fila = build_fila_item(
                item,
                on_edit=lambda e, i=item: self._on_editar_item(i),
                on_delete=lambda e, i=item: self._on_eliminar_item(i),
                pago_aplicado=pago_aplicado,
                seleccionado=seleccionado,
                on_toggle_seleccion=self._toggle_item_selection,
            )
            self._item_containers[item.id] = (fila, item)
            rows_list.controls.append(fila)
            rows_list.controls.append(
                ft.Divider(height=1, color=ft.Colors.with_opacity(0.05, ft.Colors.WHITE))
            )

        _fila_entrada = self._fila_agregar_rapido()
        rows_list.controls.append(_fila_entrada)

        self._rows_list_scroll = rows_list

        # ── Panel de abono selectivo ─────────────────────────────── #
        items_sel = [i for i in self._deuda.items if i.id in self._selected_items]
        panel_sel = build_panel_abono_selectivo(
            items_seleccionados=items_sel,
            on_confirmar=self._on_confirmar_abono_selectivo,
            on_seleccionar_fecha=self._seleccionar_por_fecha,
            on_limpiar=lambda e: self._limpiar_seleccion(),
            pagos_aplicados=pagos,
        )
        # Guardar referencia para actualización sin rebuild
        self._panel_selectivo_ref = panel_sel

        body_content = ft.Column(
            [rows_list, panel_sel, build_fila_totales(self._deuda)],
            spacing=0, expand=True
        )

        body = ft.Container(
            content=body_content,
            border=ft.border.all(1, ft.Colors.INDIGO_900),
            border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10),
            expand=True,
            clip_behavior=ft.ClipBehavior.NONE, # IMPORTANTE: Evita recorte de sugerencias flotantes
        )
        
        # Stack maestro de la tabla (solo para el contenido, ya no contiene las sugerencias)
        self._tabla_stack_maestro = ft.Stack(
            controls=[
                ft.Column([build_header_tabla(), body], spacing=0, expand=True),
            ],
            expand=True,
        )

        # Inyectar el panel en el Overlay del sistema si no existe
        if self._sug_container and self._sug_container not in self._page.overlay:
            self._page.overlay.append(self._sug_container)

        # Configurar posición inicial del Overlay
        self._actualizar_posicion_sug_global()

        self._tabla_col_container = ft.Container(
            content=self._tabla_stack_maestro,
        )

        self._tabla_col_container = ft.Container(
            content=self._tabla_stack_maestro,
        )

        def _on_resize_table(e=None):
            try:
                w = self._page.window.width
            except Exception:
                w = 1000
                
            new_width = max(1000, w - 320)
            self._tabla_col_container.width = new_width

            # Lógica de Flip Dinámico en el Overlay
            self._actualizar_posicion_sug_global()

            if e is not None:
                try:
                    self._tabla_col_container.update()
                    if self._sug_container and self._sug_container.visible: 
                        self._sug_container.update()
                except Exception:
                    pass

        # Definir tamaño inicial
        _on_resize_table()

        # Inyectar sin pisar otros eventos
        old_resize = getattr(self._page, "on_resized", None)
        def _safe_resize(e):
            if old_resize and old_resize != _safe_resize:
                try:
                    old_resize(e)
                except Exception:
                    pass
            _on_resize_table(e)
            
        self._page.on_resized = _safe_resize
        
        return ft.Row(
            [self._tabla_col_container],
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
        )

    def _actualizar_posicion_sug_global(self) -> None:
        """Calcula la posición absoluta en el Overlay para evitar recortes."""
        if not self._sug_container:
            return
            
        try:
            # page.window_height es más preciso para el área de contenido
            h = self._page.window_height or 800
        except Exception:
            h = 800

        # Sidebar(300) + Padding(16) + Margen buscador(12) + Offset texto(120)
        self._sug_container.left = 448
        # Shadow premium para que resalte sobre el fondo en el overlay
        self._sug_container.shadow = ft.BoxShadow(
            blur_radius=25, spread_radius=3, 
            color=ft.Colors.with_opacity(0.8, ft.Colors.BLACK)
        )

        if h < 700:
            self._sug_container.bottom = 26 # Modo Corto
            self._sug_container.height = 180 # Compacto
            self._sug_container.border_radius = ft.border_radius.only(bottom_left=10, bottom_right=10)
        else:
            self._sug_container.bottom = 138 # Más cerca (antes 150)
            self._sug_container.height = 300 # Muestra más resultados (aprox 10)
            self._sug_container.border_radius = ft.border_radius.all(10)

    # ─────────────────────────────────────────────────────────── #
    # Fila de entrada rápida con autocomplete                      #
    # ─────────────────────────────────────────────────────────── #

    def _fila_agregar_rapido(self) -> ft.Container:
        """Fila inline de entrada rápida. Columnas alineadas con el header."""

        def es(hint: str = "", width: int = None, ta=ft.TextAlign.LEFT) -> dict:
            d = dict(
                hint_text=hint, dense=True, text_size=13,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.AMBER_400,
                border_radius=6, height=36,
                content_padding=ft.padding.symmetric(horizontal=6, vertical=2),
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                text_align=ta,
            )
            if width:
                d["width"] = width
            return d

        # ── Campos ─────────────────────────────────────────────────── #
        n_f   = ft.TextField(**es("Buscar producto o código..."), expand=3, autofocus=True)
        ctd_f = ft.TextField(**es("1", width=48, ta=ft.TextAlign.CENTER),
                             keyboard_type=ft.KeyboardType.NUMBER, value="1")
        p_f   = ft.TextField(**es("0.00", width=68, ta=ft.TextAlign.RIGHT),
                             keyboard_type=ft.KeyboardType.NUMBER)
        sub_lbl = ft.Text("$ 0.00", size=12, color=ft.Colors.GREY_600, width=80,
                          text_align=ft.TextAlign.RIGHT)
        f_f   = ft.TextField(value=datetime.now().strftime("%Y-%m-%d"),
                             read_only=True, **es("", width=96, ta=ft.TextAlign.CENTER))
        c_f   = ft.TextField(**es("Observaciones"), expand=2)

        # Guardar referencias al nivel del view para el teclado
        self._nombre_field = n_f
        self._ctd_field    = ctd_f

        # ── Panel de sugerencias con SLOTS PRE-CREADOS ──────────────────── #
        # Los widgets se crean UNA sola vez y se actualizan in-place.
        # Antes: 8 Container nuevos por tecla → LENTO
        # Ahora: actualizar text/color/visibility de 8 slots fijos → RÁPIDO
        # Slots aumentados a 10; se muestran más o menos según la altura dinámica del contenedor
        _SLOTS = 10
        _slot_nombres: list[str] = []   # nombre actual de cada slot (para on_click)

        def _slot_hover(idx: int):
            """Misma fila resaltada que con ↑↓ al pasar el ratón."""
            def _on_hover(e):
                if e.data is True:
                    self._sug_idx = idx
                    _rebuild_sug_ui()
            return _on_hover

        _slot_texts  = [ft.Text("",  size=12, color="#aaaacc", expand=True, no_wrap=True) for _ in range(_SLOTS)]
        _slot_icons  = [ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=13, color="#7986cb") for _ in range(_SLOTS)]
        _slot_boxes  = [
            ft.Container(
                content=ft.Row([_slot_icons[i], _slot_texts[i]], spacing=8),
                bgcolor="transparent",
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                on_click=lambda e, idx=i: _seleccionar_slot(idx),
                on_hover=_slot_hover(i),
                ink=True,
                visible=False,
            )
            for i in range(_SLOTS)
        ]

        sug_lista = ft.Column(_slot_boxes, spacing=1, scroll=ft.ScrollMode.ADAPTIVE)
        self._sug_container = ft.Container(
            content=sug_lista,
            visible=False,
            bgcolor="#12152b",
            height=180, # Altura inicial (se actualiza dinámicamente)
            border_radius=ft.border_radius.all(10),
            border=ft.border.all(1, ft.Colors.INDIGO_800),
            padding=ft.padding.symmetric(vertical=6, horizontal=4),
            margin=ft.margin.all(0),
        )
        self._sug_items = []
        self._sug_idx   = -1

        # ── Lógica del autocomplete ─────────────────────────────────── #
        def _seleccionar_slot(idx: int) -> None:
            """Click en un slot pre-creado — usa el nombre guardado."""
            if idx < len(_slot_nombres):
                _seleccionar(_slot_nombres[idx])

        def _rebuild_sug_ui() -> None:
            """Actualiza los slots existentes en lugar de recrear widgets — mucho más rápido."""
            items = self._sug_items
            n     = len(items)
            antes_vis = self._sug_container.visible
            prev_n = self._sug_last_rebuild_n
            for i in range(_SLOTS):
                if i < n:
                    nombre  = items[i]
                    es_sel  = i == self._sug_idx
                    # Solo cambiar propiedades, NO crear widgets nuevos
                    _slot_texts[i].value   = nombre
                    _slot_texts[i].color   = "#ffffff" if es_sel else "#aaaacc"
                    _slot_icons[i].color   = "#ffb300" if es_sel else "#7986cb"
                    _slot_boxes[i].bgcolor = "#2a2f5a" if es_sel else "transparent"
                    _slot_boxes[i].visible = True
                    # Actualizar nombre para el on_click
                    if i >= len(_slot_nombres):
                        _slot_nombres.append(nombre)
                    else:
                        _slot_nombres[i] = nombre
                else:
                    _slot_boxes[i].visible = False

            self._sug_container.visible = n > 0
            try:
                self._sug_container.update()
            except Exception:
                pass
            self._sug_last_rebuild_n = n
            # Scroll solo al abrir o al cambiar cantidad de sugerencias — no en cada flecha ↑↓
            if n > 0 and (not antes_vis or n != prev_n):
                self._schedule_scroll_entrada_a_vista()

        def _seleccionar(nombre: str) -> None:
            """Selecciona una sugerencia: rellena el campo y oculta el panel."""
            self._ignorar_texto = nombre
            n_f.value = nombre
            
            # Autocompletado de precio
            if self._catalogo:
                precio = self._catalogo.obtener_precio(nombre)
                if precio is not None:
                    p_f.value = str(precio)
                    actualizar_subtotal()
            
            try:
                n_f.update()
                p_f.update()
            except Exception:
                pass
            self._ocultar_sug()
            self._schedule_focus_cantidad()

        def _mostrar_sugerencias(texto: str) -> None:
            if not self._catalogo or not self._catalogo.disponible:
                return
            self._sug_items = self._catalogo.buscar_nombre(texto)
            self._sug_idx   = -1
            _rebuild_sug_ui()

        def on_nombre_change(e) -> None:
            texto = n_f.value or ""
            if texto == self._ignorar_texto:
                return
            self._ignorar_texto = "" # resetea ante nuevos cambios
            
            if len(texto) < 1:
                self._ocultar_sug()
                return
            # Llamada directa — on_change corre en el event loop de Flet (hilo correcto).
            # Usar threading.Timer introduce cross-thread marshal → 1-2s de latencia extra.
            _mostrar_sugerencias(texto)

        def on_nombre_focus(e) -> None:
            # Cancela cierres diferidos viejos al volver al campo producto
            self._sug_blur_token += 1
            self._nombre_foco = True
            # Si hay texto, volver a mostrar sugerencias
            texto = n_f.value or ""
            if texto == self._ignorar_texto:
                return
                
            if texto and self._catalogo and self._catalogo.disponible:
                _mostrar_sugerencias(texto)

        def on_nombre_blur(e) -> None:
            self._nombre_foco = False
            # Sin demora, el blur gana al clic: el panel desaparece antes del on_click del ítem.
            tok = self._sug_blur_token

            async def _cerrar_sugerencias_luego() -> None:
                await asyncio.sleep(0.28)
                if tok != self._sug_blur_token:
                    return
                self._ocultar_sug()

            try:
                self._page.run_task(_cerrar_sugerencias_luego)
            except Exception:
                self._ocultar_sug()

        n_f.on_change = on_nombre_change
        n_f.on_focus  = on_nombre_focus
        n_f.on_blur   = on_nombre_blur

        # Guardar rebuild_fn para que on_key_event lo pueda llamar
        self._rebuild_sug_ui = _rebuild_sug_ui

        # ── Campo de código de barras (Observaciones) ───────────────── #
        def on_codigo_change(e) -> None:
            codigo = c_f.value.strip()
            if not codigo or not self._catalogo:
                return
            resultado = self._catalogo.buscar_por_codigo(codigo)
            if resultado:
                nombre, precio = resultado
                n_f.value = nombre
                if precio is not None:
                    p_f.value = str(precio)
                    actualizar_subtotal()
                    
                try:
                    n_f.update()
                    p_f.update()
                except Exception:
                    pass
                self._ocultar_sug()
                self._schedule_focus_cantidad()

        c_f.on_change = on_codigo_change

        # ── Subtotal en vivo ────────────────────────────────────────── #
        def actualizar_subtotal(e=None) -> None:
            try:
                precio = float(p_f.value.replace(",", ".") or "0")
                cant   = int(ctd_f.value or "1")
                sub_lbl.value = f"$ {precio * cant:.2f}"
                sub_lbl.color = ft.Colors.AMBER_300
            except Exception:
                sub_lbl.value = "$ 0.00"
                sub_lbl.color = ft.Colors.GREY_600
            try:
                sub_lbl.update()
            except Exception:
                pass

        p_f.on_change   = actualizar_subtotal
        ctd_f.on_change = actualizar_subtotal

        # ── Agregar ítem ────────────────────────────────────────────── #
        async def agregar(e=None) -> None:
            # Si hay sugerencias visibles, Enter selecciona la marcada (o la primera)
            if (self._sug_container and self._sug_container.visible
                    and self._sug_items):
                idx = self._sug_idx if self._sug_idx >= 0 else 0
                if idx < len(self._sug_items):
                    _seleccionar(self._sug_items[idx])
                    return

            nombre     = n_f.value.strip()
            precio_raw = p_f.value.strip()

            if not nombre:
                snack(self._page, "Por favor, ingresa el nombre del producto", ft.Colors.RED_800)
                await n_f.focus()
                return
            if not precio_raw:
                snack(self._page, "Por favor, ingresa el precio", ft.Colors.RED_800)
                await p_f.focus()
                return
            try:
                precio = float(precio_raw.replace(",", "."))
            except ValueError:
                snack(self._page, "El precio debe ser un número válido", ft.Colors.RED_800)
                await p_f.focus()
                return
            try:
                cantidad = int(ctd_f.value or "1")
            except ValueError:
                cantidad = 1

            self._deuda.items.append(
                DeudaItem(
                    nombre=nombre,
                    codigo_barras=c_f.value.strip(),
                    precio=precio,
                    cantidad=cantidad,
                    fecha=f_f.value.strip() or datetime.now().strftime("%Y-%m-%d"),
                )
            )
            self._repo.save_deuda(self._deuda)
            self._after_change()

        for campo in (n_f, ctd_f, p_f, c_f):
            campo.on_submit = agregar

        btn_add = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE, icon_size=24,
            icon_color=ft.Colors.AMBER_400,
            tooltip="Guardar (Enter)", on_click=agregar, width=70,
        )

        # Indicador de catálogo disponible
        cat_icon = None
        if self._catalogo and self._catalogo.disponible:
            cat_icon = ft.Icon(
                ft.Icons.AUTO_AWESOME,
                size=14,
                color=ft.Colors.AMBER_600,
                tooltip=f"Catálogo activo: {self._catalogo.total:,} productos",
            )

        nombre_row = ft.Row(
            [n_f] + ([cat_icon] if cat_icon else []),
            spacing=4, expand=3,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )


        return ft.Container(
            content=ft.Row(
                [nombre_row, ctd_f, p_f, sub_lbl, f_f, c_f,
                 ft.Row([btn_add], alignment=ft.MainAxisAlignment.END, width=70)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.AMBER_400),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            clip_behavior=ft.ClipBehavior.NONE, # IMPORTANTE
        )

    # ─────────────────────────────────────────────────────────── #
    # Autocomplete — navegación por teclado                       #
    # ─────────────────────────────────────────────────────────── #

    def _mover_sug(self, delta: int) -> None:
        n = len(self._sug_items)
        if not n: return
        
        # Nueva lógica circular: de -1 (campo texto) a n-1 (última sugerencia)
        if delta > 0: # Abajo
            self._sug_idx += 1
            if self._sug_idx >= n:
                self._sug_idx = -1
        else: # Arriba
            self._sug_idx -= 1
            if self._sug_idx < -1:
                self._sug_idx = n - 1
                
        self._rebuild_sug_ui()

    def _on_key_event(self, e: ft.KeyboardEvent) -> None:
        """Maneja ↑↓ Tab Esc para navegar las sugerencias."""
        if not self._nombre_foco:
            return
        if self._sug_container is None or not self._sug_container.visible:
            return
        if not self._sug_items:
            return

        key = e.key
        if key == "Arrow Down":
            self._page.run_task(_bucle_auto_repetir, 0x28, self._mover_sug, 1)
        elif key == "Arrow Up":
            self._page.run_task(_bucle_auto_repetir, 0x26, self._mover_sug, -1)
        elif key == "Escape":
            self._ocultar_sug()
        elif key == "Tab":
            # Tab selecciona la sugerencia marcada (o la primera)
            idx = self._sug_idx if self._sug_idx >= 0 else 0
            sel_ok = idx < len(self._sug_items)
            if sel_ok and self._nombre_field:
                self._nombre_field.value = self._sug_items[idx]
                try:
                    self._nombre_field.update()
                except Exception:
                    pass
            self._ocultar_sug()
            if sel_ok:
                self._schedule_focus_cantidad()

    def _ocultar_sug(self) -> None:
        if self._sug_container and self._sug_container.visible:
            self._sug_container.visible = False
            try:
                self._sug_container.update()
            except Exception:
                pass
        self._sug_items = []
        self._sug_idx   = -1
        self._sug_last_rebuild_n = -1

    # ─────────────────────────────────────────────────────────── #
    # Abono Selectivo                                              #
    # ─────────────────────────────────────────────────────────── #

    def _toggle_item_selection(self, item_id: str) -> None:
        """Marca/Desmarca un ítem sin reconstruir la vista (no hace scroll)."""
        if item_id in self._selected_items:
            self._selected_items.discard(item_id)
        else:
            self._selected_items.add(item_id)
        self._actualizar_visuals_seleccion(item_id)

    def _actualizar_visuals_seleccion(self, item_id_cambiado: str) -> None:
        """Actualiza solo el container de la fila cambiada y el panel sumario, sin rebuild."""
        if not self._deuda:
            return

        _HOY = datetime.now().strftime("%Y-%m-%d")

        # 1. Actualizar visualmente solo la fila cambiada
        if item_id_cambiado in self._item_containers:
            contenedor, item = self._item_containers[item_id_cambiado]
            seleccionado = item_id_cambiado in self._selected_items
            es_hoy = item.fecha == _HOY

            if seleccionado:
                contenedor.bgcolor       = "#1e3a2f"
                contenedor.border        = ft.border.all(1, "#22c55e")
                contenedor.border_radius = 6
            elif es_hoy:
                contenedor.bgcolor       = "#162838"
                contenedor.border        = ft.border.all(1, "#2d6a4f")
                contenedor.border_radius = 6
            else:
                contenedor.bgcolor       = None
                contenedor.border        = None
                contenedor.border_radius = 0

            # Actualizar el checkbox dentro de la fila
            try:
                fila_row = contenedor.content
                if hasattr(fila_row, "controls"):
                    for ctrl in fila_row.controls:
                        if isinstance(ctrl, ft.Checkbox):
                            ctrl.value = seleccionado
                            break
            except Exception:
                pass

            try:
                contenedor.update()
            except Exception:
                pass

        # 2. Actualizar el panel de suma sin tocar la lista de filas
        if self._panel_selectivo_ref is not None:
            from utils.calculos import calcular_pagos_aplicados
            pagos = calcular_pagos_aplicados(self._deuda)
            
            items_sel = [i for i in self._deuda.items if i.id in self._selected_items]
            suma = round(sum(max(0, i.subtotal - pagos.get(i.id, 0.0)) for i in items_sel), 2)
            n    = len(items_sel)
            panel = self._panel_selectivo_ref
            panel.visible = n > 0

            try:
                for ctrl in panel.content.controls:
                    if isinstance(ctrl, ft.Column):
                        for txt in ctrl.controls:
                            if hasattr(txt, "value") and txt.value and "$" in str(txt.value):
                                txt.value = f"$ {suma:.2f}"
                            elif hasattr(txt, "value") and txt.value:
                                txt.value = (
                                    f"{n} producto{'s' if n != 1 else ''} "
                                    f"seleccionado{'s' if n != 1 else ''}"
                                )
            except Exception:
                pass

            try:
                panel.update()
            except Exception:
                pass


    def _seleccionar_por_fecha(self, fecha: str) -> None:
        """Selecciona automáticamente todos los ítems de una fecha dada. Sí hace rebuild (es una acción masiva)."""
        if not fecha or not self._deuda:
            return
        self._selected_items = {item.id for item in self._deuda.items if item.fecha == fecha}
        self._after_change()

    def _limpiar_seleccion(self) -> None:
        self._selected_items.clear()
        self._after_change()

    def _on_confirmar_abono_selectivo(self, e=None) -> None:
        """Confirma el abono de los ítems seleccionados."""
        from models.deuda import Abono
        from views.helpers import snack
        import datetime

        if not self._selected_items:
            return

        items_sel = [i for i in self._deuda.items if i.id in self._selected_items]
        if not items_sel:
            return

        from utils.calculos import calcular_pagos_aplicados
        pagos = calcular_pagos_aplicados(self._deuda)
        
        suma = round(sum(max(0, i.subtotal - pagos.get(i.id, 0.0)) for i in items_sel), 2)
        ids  = [i.id for i in items_sel]
        nombres = ", ".join(i.nombre for i in items_sel[:3])
        if len(items_sel) > 3:
            nombres += f" (+{len(items_sel)-3} más)"

        def _confirmar(ev):
            dlg_conf.open = False
            self._page.update()
            nuevo = Abono(
                monto=suma,
                fecha=datetime.datetime.now().strftime("%Y-%m-%d"),
                nota=f"Abono selectivo: {nombres}",
                items_ids=ids,
            )
            self._deuda.abonos.append(nuevo)
            self._repo.save_deuda(self._deuda)
            self._selected_items.clear()
            self._after_change()
            snack(self._page, f"Abono selectivo de ${suma:.2f} registrado.", ft.Colors.GREEN_600)

        dlg_conf = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.PAYMENTS_OUTLINED, color=ft.Colors.GREEN_400),
                ft.Text("Confirmar Abono Selectivo", weight=ft.FontWeight.BOLD),
            ], spacing=8),
            content=ft.Column([
                ft.Text(f"Productos seleccionados: {len(items_sel)}", size=13),
                ft.Text(nombres, size=12, color=ft.Colors.GREY_400),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ATTACH_MONEY, color=ft.Colors.GREEN_400, size=20),
                        ft.Text(f"Total a abonar: ${suma:.2f}", size=16,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                    ], spacing=4),
                    bgcolor="#0e2a1a",
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    margin=ft.margin.only(top=6),
                ),
                ft.Text(
                    "Los productos seleccionados se marcarán como pagados.",
                    size=11, color=ft.Colors.GREY_500, italic=True,
                ),
            ], tight=True, spacing=8, width=360),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg_conf.actions = [
            ft.TextButton("Cancelar", on_click=lambda ev: (
                setattr(dlg_conf, "open", False), self._page.update()
            )),
            ft.FilledButton(
                "Confirmar Abono",
                icon=ft.Icons.CHECK_CIRCLE,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700),
                on_click=_confirmar,
            ),
        ]
        if dlg_conf not in self._page.overlay:
            self._page.overlay.append(dlg_conf)
        dlg_conf.open = True
        self._page.update()

    # ─────────────────────────────────────────────────────────── #
    # Callbacks / Acciones                                         #
    # ─────────────────────────────────────────────────────────── #

    def _on_editar_item(self, item: DeudaItem) -> None:
        dialogo_item(self._page, self._repo, self._deuda, item, on_done=self._after_change)

    def _on_eliminar_item(self, item: DeudaItem) -> None:
        self._deuda.items = [i for i in self._deuda.items if i.id != item.id]
        self._repo.save_deuda(self._deuda)
        self._after_change()

    def _on_resetear_deuda(self, e=None) -> None:
        """Muestra confirmación y borra todos los ítems y abonos del cliente."""
        nombre = self._cliente.nombre if self._cliente else "este cliente"

        def _confirmar_reset(ev):
            dlg_conf.open = False
            self._page.update()
            self._deuda.items  = []
            self._deuda.abonos = []
            self._repo.save_deuda(self._deuda)
            self._after_change()
            snack(self._page, f"Lista de {nombre} reiniciada.", ft.Colors.INDIGO_600)

        dlg_conf = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER_400),
                ft.Text("Reiniciar lista", weight=ft.FontWeight.BOLD),
            ], spacing=8),
            content=ft.Text(
                f"¿Borrar TODOS los productos y abonos de {nombre}?\n\n"
                "Esto eliminará el historial completo y dejará la cuenta en $0.\n"
                "Esta acción no se puede deshacer.",
                size=13,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg_conf.actions = [
            ft.TextButton("Cancelar", on_click=lambda ev: (
                setattr(dlg_conf, "open", False), self._page.update()
            )),
            ft.FilledButton(
                "Sí, borrar todo",
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700),
                on_click=_confirmar_reset,
            ),
        ]
        if dlg_conf not in self._page.overlay:
            self._page.overlay.append(dlg_conf)
        dlg_conf.open = True
        self._page.update()

    def _on_abono(self, e) -> None:
        dialogo_ver_abonos(self._page, self._repo, self._deuda, on_done=self._after_change)

    def _on_saldar_deuda(self, e) -> None:
        from utils.calculos import calcular_saldo_pendiente
        from models.deuda import Abono
        import datetime
        from views.helpers import snack

        saldo = calcular_saldo_pendiente(self._deuda)
        if saldo <= 0:
            snack(self._page, "La cuenta ya está saldada o en ceros.", ft.Colors.RED_400)
            return

        def _confirmar(ev):
            dlg_conf.open = False
            self._page.update()
            nuevo = Abono(
                monto=saldo,
                fecha=datetime.datetime.now().strftime("%Y-%m-%d"),
                nota="Liquidación automática"
            )
            self._deuda.abonos.append(nuevo)
            self._repo.save_deuda(self._deuda)
            self._after_change()
            snack(self._page, f"Cuenta saldada automáticamente por ${saldo:.2f}", ft.Colors.GREEN_600)

        dlg_conf = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.AMBER_400),
                ft.Text("Saldar Deuda Completa", weight=ft.FontWeight.BOLD),
            ], spacing=8),
            content=ft.Text(f"¿Deseas agregar un abono automático por el total restante de ${saldo:.2f} para dejar la cuenta en ceros ahora mismo?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: (setattr(dlg_conf, "open", False), self._page.update())),
                ft.FilledButton("Sí, liquidar de una", style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700), on_click=_confirmar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg_conf)
        dlg_conf.open = True
        self._page.update()

    def _after_change(self) -> None:
        """Re-renderiza la vista completa tras cualquier modificación."""
        self._render()
        self.update()
        self._schedule_scroll_entrada_a_vista()
        # Notificar a la lista de clientes para que actualice el saldo en tiempo real
        if self._on_deuda_changed:
            try:
                self._on_deuda_changed()
            except Exception:
                pass
        # ── Detectar cuenta saldada ────────────────────────────────────
        self._verificar_cuenta_saldada()

    def _verificar_cuenta_saldada(self) -> None:
        """Si el saldo llega a 0 y había deuda real, muestra diálogo de celebración."""
        from utils.calculos import calcular_total, calcular_saldo_pendiente
        if not self._cliente or not self._deuda:
            return
        total = calcular_total(self._deuda)
        saldo = calcular_saldo_pendiente(self._deuda)
        if not (total > 0 and round(saldo, 2) == 0.0):
            return

        nombre    = self._cliente.nombre
        tiene_tel = bool(self._cliente.telefono)

        def _mostrar_dialogo():
            """Ejecutado con pequeño delay para que el dialog de abono termine de cerrar."""

            def _enviar_saldada(e=None) -> None:
                import webbrowser, urllib.parse
                # Cargar plantilla desde config (o usar la por defecto)
                _template = self._repo.get_config().get(
                    "wa_template_saldada",
                    "Hola {nombre} 🎉\n\n"
                    "¡Excelentes noticias! Tu cuenta ha sido *saldada completamente*. "
                    "Ya no tienes ningún saldo pendiente con nosotros. 🙌\n\n"
                    "¡Gracias por tu pago! Te esperamos pronto. 😊",
                )
                try:
                    msg = _template.format(nombre=nombre)
                except KeyError:
                    msg = _template  # si la plantilla tiene errores, enviar tal cual
                tel = self._formatear_telefono_wa(self._cliente.telefono)
                url = f"https://wa.me/{tel}?text={urllib.parse.quote(msg)}"
                try:
                    webbrowser.open(url)
                except Exception:
                    pass
                cerrar(None)

            def cerrar(e):
                dlg_cel.open = False
                try:
                    self._page.update()
                except Exception:
                    pass

            acciones = [ft.TextButton("Cerrar", on_click=cerrar)]
            if tiene_tel:
                acciones.insert(0, ft.FilledButton(
                    "Enviar WhatsApp 🎉",
                    icon=ft.Icons.CHAT_OUTLINED,
                    on_click=_enviar_saldada,
                    style=ft.ButtonStyle(bgcolor="#075E54", color=ft.Colors.WHITE),
                ))

            dlg_cel = ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    [ft.Text("🎉", size=28), ft.Text("¡Cuenta Saldada!", size=18, weight=ft.FontWeight.BOLD, color="#4caf50")],
                    spacing=10,
                ),
                content=ft.Column(
                    [
                        ft.Text(
                            f"¡Felicitaciones! {nombre} ha pagado su deuda completa.",
                            size=14, color=ft.Colors.WHITE,
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.CHECK_CIRCLE, color="#4caf50", size=20),
                                ft.Text("Saldo pendiente: $0.00", size=15, weight=ft.FontWeight.BOLD, color="#4caf50"),
                            ], spacing=8),
                            bgcolor="#1b5e20",
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=14, vertical=10),
                        ),
                    ],
                    tight=True, spacing=12, width=360,
                ),
                actions=acciones,
                actions_alignment=ft.MainAxisAlignment.END,
            )

            if dlg_cel not in self._page.overlay:
                self._page.overlay.append(dlg_cel)
            dlg_cel.open = True
            try:
                self._page.update()
            except Exception:
                pass

        # Pequeño delay para que el dialog de abono termine su animación de cierre
        threading.Timer(0.35, _mostrar_dialogo).start()

    def _exportar_pdf(self, e) -> None:
        try:
            gen  = self._get_pdf()
            ruta = gen.generar_ticket(self._cliente, self._deuda)
            os.startfile(str(ruta))
            snack(self._page, f"PDF generado: {ruta.name}", ft.Colors.GREEN_800)
        except Exception as ex:
            snack(self._page, f"Error al generar PDF: {ex}", ft.Colors.RED_800)

    # ──────────────────────────────────────────────────────────────── #
    # WhatsApp                                                          #
    # ──────────────────────────────────────────────────────────────── #

    @staticmethod
    def _formatear_telefono_wa(telefono: str) -> str:
        """Convierte el teléfono al formato internacional para wa.me.
        Ej: '0987654321' → '593987654321'  |  '+593...' → '593...'
        """
        tel = "".join(c for c in telefono if c.isdigit())
        if tel.startswith("0") and len(tel) == 10:
            # Formato Ecuador: 09XXXXXXXX → 593 9XXXXXXXX
            tel = "593" + tel[1:]
        elif tel.startswith("593"):
            pass   # ya tiene código país
        return tel

    def _enviar_whatsapp(self, e=None) -> None:
        """Usa el motor modular de WhatsApp para enviar el resumen."""
        error = WhatsAppManager.enviar_resumen_deuda(self._cliente, self._deuda, self._repo)
        if error:
            snack(self._page, f"No se pudo abrir WhatsApp: {error}", ft.Colors.RED_800)
        else:
            snack(self._page, f"Abriendo WhatsApp para {self._cliente.nombre}…", ft.Colors.GREEN_700)
