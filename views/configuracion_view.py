"""
views/configuracion_view.py
Panel de configuración del negocio.

Usa utils.native_dialogs (tkinter) para selección de archivos/carpetas,
evitando completamente ft.FilePicker que da timeout en versiones nuevas de Flet.
"""
from __future__ import annotations
from typing import Callable

import flet as ft

from database.repositorio import DEFAULT_CARPETA_DATOS_CLIENTES, Repositorio
from utils.native_dialogs import pick_json_file, pick_directory, pick_xlsx_file
from views.helpers import snack


class ConfiguracionView(ft.AlertDialog):
    def __init__(
        self,
        repo: Repositorio,
        page: ft.Page,
        on_saved: Callable[[], None] = None,
        catalogo=None,
    ):
        super().__init__(modal=True)
        self._repo     = repo
        self._page     = page
        self._on_saved = on_saved
        self._catalogo = catalogo   # utils.catalogo.Catalogo | None

        config = self._repo.get_config()

        # ── 1. Datos del negocio ─────────────────────────────────────── #
        self._nombre_f = ft.TextField(label="Nombre del negocio", value=config.get("nombre_negocio", ""))
        self._dir_f    = ft.TextField(label="Dirección",           value=config.get("direccion", ""))
        self._tel_f    = ft.TextField(label="Teléfono",            value=config.get("telefono", ""))
        self._slogan_f = ft.TextField(label="Slogan (aparece en el ticket)", value=config.get("slogan", ""))
        self._export_f = ft.TextField(
            label="Ruta de exportación de PDFs",
            value=config.get("ruta_exportacion", "data_storage/exportaciones"),
        )
        self._carpeta_datos_f = ft.TextField(
            label="Carpeta del archivo clientes.json en red (UNC)",
            value=config.get("carpeta_datos_clientes", "") or "",
            hint_text=r"Ej: \\SERVIDOR\carpeta\Respaldo — vacío = data_storage local",
            expand=True,
        )
        btn_datos_red = ft.ElevatedButton(
            "Elegir carpeta…",
            icon=ft.Icons.DRIVE_FILE_MOVE_OUTLINE,
            on_click=self._on_click_carpeta_datos,
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_900, color=ft.Colors.WHITE),
        )
        btn_datos_local = ft.TextButton(
            "Usar solo datos locales",
            on_click=self._usar_solo_datos_locales,
            style=ft.ButtonStyle(color=ft.Colors.GREY_400),
        )
        btn_datos_defecto = ft.TextButton(
            "Usar carpeta por defecto del programa",
            icon=ft.Icons.RESTORE_OUTLINED,
            on_click=self._usar_carpeta_datos_por_defecto,
            tooltip="Rellena la carpeta UNC definida en el instalador / código fuente",
            style=ft.ButtonStyle(color=ft.Colors.INDIGO_300),
        )
        btn_rutas_pdf = ft.ElevatedButton(
            "Elegir carpeta…",
            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
            on_click=self._on_click_ruta_exportacion,
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_900, color=ft.Colors.WHITE),
        )


        # ── 3. Importar JSON ──────────────────────────────────────────  #
        self._lbl_import = ft.Text(
            "Selecciona un archivo JSON con la lista de clientes.",
            size=12, color=ft.Colors.GREY_400,
        )
        btn_importar = ft.ElevatedButton(
            "Seleccionar archivo de clientes...",
            icon=ft.Icons.UPLOAD_FILE,
            on_click=self._on_click_importar,
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_800, color=ft.Colors.WHITE),
        )

        # ── 4. Catálogo de productos ──────────────────────────────── #
        if self._catalogo and self._catalogo.disponible:
            cat_status_text = f"✓ Catálogo activo — {self._catalogo.total:,} productos"
            cat_status_color = ft.Colors.GREEN_400
        else:
            cat_status_text = "Sin catálogo configurado."
            cat_status_color = ft.Colors.GREY_500

        self._lbl_catalogo = ft.Text(
            cat_status_text,
            size=12,
            color=cat_status_color,
            italic=not bool(self._catalogo and self._catalogo.disponible),
        )
        btn_catalogo = ft.ElevatedButton(
            "Seleccionar archivo Excel del catálogo...",
            icon=ft.Icons.TABLE_CHART_OUTLINED,
            on_click=self._on_click_catalogo,
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_900, color=ft.Colors.WHITE),
        )

        # ── 5. Carpeta de respaldo ─────────────────────────────────── #
        carpeta_guardada = config.get("carpeta_respaldo", "") or ""
        self._lbl_carpeta = ft.Text(
            carpeta_guardada if carpeta_guardada else "Sin carpeta de respaldo configurada.",
            size=12,
            color=ft.Colors.GREEN_400 if carpeta_guardada else ft.Colors.GREY_500,
            italic=not bool(carpeta_guardada),
        )
        btn_carpeta = ft.ElevatedButton(
            "Seleccionar carpeta de respaldo...",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._on_click_carpeta,
            style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_800, color=ft.Colors.WHITE),
        )
        btn_limpiar = ft.TextButton(
            "Desactivar respaldo",
            icon=ft.Icons.CANCEL_OUTLINED,
            on_click=self._desactivar_respaldo,
            style=ft.ButtonStyle(color=ft.Colors.RED_400),
        )

        # ── 6. Plantillas de WhatsApp ────────────────────────────── #
        _WA_DEUDA_DEFAULT = (
            "Hola {nombre} 👋\n\n"
            "📝 *Resumen de tu cuenta:*\n"
            "{detalle}\n\n"
            "💰 Total deuda:  *${total}*\n"
            "✅ Abonado:      *${abonado}*\n"
            "⚠️ Saldo pendiente: *${saldo}*\n\n"
            "_Por favor comunicarse para coordinar el pago._"
        )
        _WA_SALDADA_DEFAULT = (
            "Hola {nombre} 🎉\n\n"
            "¡Excelentes noticias! Tu cuenta ha sido *saldada completamente*. "
            "Ya no tienes ningún saldo pendiente con nosotros. 🙌\n\n"
            "¡Gracias por tu pago! Te esperamos pronto. 😊"
        )

        self._wa_deuda_f = ft.TextField(
            label="Plantilla: resumen de deuda",
            value=config.get("wa_template_deuda", _WA_DEUDA_DEFAULT),
            multiline=True, min_lines=4, max_lines=8,
            text_size=12,
            hint_text="Usa {nombre}, {detalle}, {total}, {abonado}, {saldo}",
        )
        self._wa_saldada_f = ft.TextField(
            label="Plantilla: cuenta saldada",
            value=config.get("wa_template_saldada", _WA_SALDADA_DEFAULT),
            multiline=True, min_lines=3, max_lines=6,
            text_size=12,
            hint_text="Usa {nombre}",
        )

        # ── Feedback ─────────────────────────────────────────────────── #
        self._error        = ft.Text("", color=ft.Colors.RED_400,   size=12)
        self._saved_banner = ft.Text("", color=ft.Colors.GREEN_400, size=12)

        # ── Layout ───────────────────────────────────────────────────── #
        self.title = ft.Row(
            [
                ft.Icon(ft.Icons.SETTINGS, color=ft.Colors.INDIGO_300),
                ft.Text("Configuración del Negocio", size=17, weight=ft.FontWeight.BOLD),
            ],
            spacing=10,
        )
        self.content = ft.Column(
            [
                ft.Text("Datos que aparecerán en los tickets PDF", size=12, color=ft.Colors.GREY_400),
                self._nombre_f, self._dir_f, self._tel_f, self._slogan_f,
                ft.Divider(),
                ft.Text("Rutas del sistema", size=12, color=ft.Colors.GREY_400),
                ft.Row([self._export_f, btn_rutas_pdf], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(
                    "Misma base de clientes en varias PCs: ruta UNC donde vive clientes.json.",
                    size=11, color=ft.Colors.GREY_500,
                ),
                ft.Row([self._carpeta_datos_f, btn_datos_red], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([btn_datos_local, btn_datos_defecto], spacing=4, wrap=True),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"• Clientes: {self._repo._clientes_path()}", size=10, color=ft.Colors.INDIGO_300, italic=True),
                        ft.Text(f"• Faltantes: {self._repo._faltantes_path()}", size=10, color=ft.Colors.INDIGO_300, italic=True),
                        ft.Text(f"• Notas: {self._repo._notas_path()}", size=10, color=ft.Colors.INDIGO_300, italic=True),
                        ft.Text(f"• Tareas: {self._repo._tareas_path()}", size=10, color=ft.Colors.INDIGO_300, italic=True),
                    ], spacing=1),
                    padding=ft.padding.only(left=4, top=-4),
                ),
                ft.Divider(),
                ft.Text("Privacidad y Control", size=12, color=ft.Colors.GREY_400, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Importar clientes desde archivo JSON", size=12, color=ft.Colors.GREY_400, weight=ft.FontWeight.BOLD),
                self._lbl_import,
                btn_importar,
                ft.Divider(),
                ft.Text("Catálogo de productos (autocompletado)", size=12, color=ft.Colors.GREY_400, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Selecciona tu archivo .xlsx con columnas PRODUCTO y CÓDIGO_BARRAS.\n"
                    "El archivo se copia localmente — puedes borrar el original.",
                    size=11, color=ft.Colors.GREY_500,
                ),
                self._lbl_catalogo,
                btn_catalogo,
                ft.Divider(),
                ft.Text("Respaldo automático de datos", size=12, color=ft.Colors.GREY_400, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Se copia clientes.json en la carpeta elegida en cada cambio y cada 30 min.",
                    size=11, color=ft.Colors.GREY_500,
                ),
                self._lbl_carpeta,
                ft.Row([btn_carpeta, btn_limpiar], spacing=8),
                ft.Divider(),
                # ── Plantillas WhatsApp ─────────────────────────── #
                ft.Row([
                    ft.Icon(ft.Icons.CHAT_OUTLINED, color="#25D366", size=16),
                    ft.Text("Plantillas de mensajes WhatsApp", size=12,
                            color=ft.Colors.GREY_400, weight=ft.FontWeight.BOLD),
                ], spacing=6),
                self._wa_deuda_f,
                ft.Container(
                    content=ft.Text(
                        "💡 Variables disponibles: {nombre}  {detalle}  {total}  {abonado}  {saldo}",
                        size=10, color="#888", italic=True,
                    ),
                    padding=ft.padding.only(left=4),
                ),
                self._wa_saldada_f,
                ft.Container(
                    content=ft.Text(
                        "💡 Variables disponibles: {nombre}",
                        size=10, color="#888", italic=True,
                    ),
                    padding=ft.padding.only(left=4),
                ),
                self._error,
                self._saved_banner,
            ],
            tight=True, spacing=10, width=460, scroll=ft.ScrollMode.AUTO,
        )
        self.actions = [
            ft.TextButton("Cerrar", on_click=self._cerrar),
            ft.FilledButton("Guardar", on_click=self._guardar),
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    # ─────────────────────────────────────────────────────────── #
    # API pública                                                  #
    # ─────────────────────────────────────────────────────────── #

    def recargar_config(self) -> None:
        """Refresca los campos con los valores actuales en disco antes de abrir."""
        config = self._repo.get_config()
        self._nombre_f.value     = config.get("nombre_negocio", "")
        self._dir_f.value        = config.get("direccion", "")
        self._tel_f.value        = config.get("telefono", "")
        self._slogan_f.value     = config.get("slogan", "")
        self._export_f.value     = config.get("ruta_exportacion", "data_storage/exportaciones")
        self._carpeta_datos_f.value = config.get("carpeta_datos_clientes", "") or ""
        self._wa_deuda_f.value   = config.get("wa_template_deuda",   self._wa_deuda_f.value)
        self._wa_saldada_f.value = config.get("wa_template_saldada", self._wa_saldada_f.value)
        self._error.value        = ""
        self._saved_banner.value = ""

        carpeta = config.get("carpeta_respaldo", "") or ""
        if carpeta:
            self._lbl_carpeta.value  = carpeta
            self._lbl_carpeta.color  = ft.Colors.GREEN_400
            self._lbl_carpeta.italic = False
        else:
            self._lbl_carpeta.value  = "Sin carpeta de respaldo configurada."
            self._lbl_carpeta.color  = ft.Colors.GREY_500
            self._lbl_carpeta.italic = True

    # ─────────────────────────────────────────────────────────── #
    # Acciones básicas                                             #
    # ─────────────────────────────────────────────────────────── #

    def _cerrar(self, e) -> None:
        self.open = False
        self._page.update()

    def _guardar(self, e) -> None:
        self._error.value = ""
        nombre = self._nombre_f.value.strip()
        if not nombre:
            self._error.value = "El nombre del negocio es obligatorio."
            self._error.update()
            return

        carpeta_activa = (
            self._lbl_carpeta.value
            if self._lbl_carpeta.color == ft.Colors.GREEN_400
            else ""
        )
        config = self._repo.get_config()
        config.update({
            "nombre_negocio":            nombre,
            "direccion":                 self._dir_f.value.strip(),
            "telefono":                  self._tel_f.value.strip(),
            "slogan":                    self._slogan_f.value.strip(),
            "ruta_exportacion":          self._export_f.value.strip() or "data_storage/exportaciones",
            "carpeta_respaldo":          carpeta_activa,
            "carpeta_datos_clientes":    self._carpeta_datos_f.value.strip(),
            "wa_template_deuda":         self._wa_deuda_f.value,
            "wa_template_saldada":       self._wa_saldada_f.value,
        })
        self._repo.save_config(config)
        self._saved_banner.value = "✓ Configuración guardada correctamente."
        self._saved_banner.update()
        if self._on_saved:
            self._on_saved()

    # ─────────────────────────────────────────────────────────── #
    # Importar clientes desde JSON (diálogo nativo de Windows)    #
    # ─────────────────────────────────────────────────────────── #

    async def _on_click_importar(self, e) -> None:
        """Abre el diálogo nativo de Windows para seleccionar un archivo JSON."""
        ruta = await pick_json_file("Seleccionar JSON de clientes")
        if not ruta:
            return  # Usuario canceló
        try:
            diferencias = self._repo.importar_clientes_desde_json(ruta)
        except ValueError as ex:
            snack(self._page, str(ex), ft.Colors.RED_800)
            return
        self._mostrar_dialogo_diferencias(ruta, diferencias)

    def _mostrar_dialogo_diferencias(self, ruta: str, dif: dict) -> None:
        """Muestra diferencias y pide confirmación antes de aplicar la importación."""
        nuevos     = dif["nuevos"]
        modif      = dif["modificados"]
        eliminados = dif["eliminados"]
        sin_cambio = dif["sin_cambio"]

        filas: list[ft.Control] = []

        def seccion(titulo, color, items, render_fn):
            if not items:
                return
            filas.append(ft.Text(titulo, size=12, weight=ft.FontWeight.BOLD, color=color))
            for item in items:
                filas.append(render_fn(item))

        seccion(
            f"✚ Nuevos ({len(nuevos)})", ft.Colors.GREEN_400, nuevos,
            lambda c: ft.Text(f"  • {c.nombre}  {c.telefono or ''}", size=12),
        )
        seccion(
            f"✎ Modificados ({len(modif)})", ft.Colors.AMBER_400, modif,
            lambda pair: ft.Column([
                ft.Text(f"  • {pair[0].nombre}", size=12, color=ft.Colors.GREY_400),
                ft.Text(f"    → {pair[1].nombre}  {pair[1].telefono or ''}  {pair[1].direccion or ''}",
                        size=11, color=ft.Colors.AMBER_300),
            ], spacing=1),
        )
        seccion(
            f"✖ Se eliminarían ({len(eliminados)})", ft.Colors.RED_400, eliminados,
            lambda c: ft.Text(f"  • {c.nombre}", size=12),
        )

        if not filas:
            filas.append(ft.Text(
                f"Sin diferencias. {len(sin_cambio)} cliente(s) idénticos.",
                size=13, color=ft.Colors.GREEN_400,
            ))

        nombre_archivo = ruta.replace("\\", "/").split("/")[-1]
        dlg_dif = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.COMPARE_ARROWS, color=ft.Colors.INDIGO_300),
                ft.Text("Diferencias detectadas", size=16, weight=ft.FontWeight.BOLD),
            ], spacing=10),
            content=ft.Column(
                [
                    ft.Text(f"Archivo: {nombre_archivo}", size=11, color=ft.Colors.GREY_500),
                    ft.Column(filas, spacing=6, scroll=ft.ScrollMode.AUTO, height=260),
                    ft.Text("¿Deseas aplicar estos cambios?", size=12, color=ft.Colors.GREY_400, italic=True),
                ],
                tight=True, spacing=8, width=440,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
        )

        def confirmar(e) -> None:
            try:
                self._repo.aplicar_importacion(ruta)
                snack(self._page, "✓ Clientes importados correctamente.", ft.Colors.GREEN_800)
            except Exception as ex:
                snack(self._page, f"Error al importar: {ex}", ft.Colors.RED_800)
            dlg_dif.open = False
            self._page.update()

        def cancelar(e) -> None:
            dlg_dif.open = False
            self._page.update()

        dlg_dif.actions = [
            ft.TextButton("Cancelar", on_click=cancelar),
            ft.FilledButton(
                "Aplicar cambios", icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                on_click=confirmar,
                style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_700),
            ),
        ]
        if dlg_dif not in self._page.overlay:
            self._page.overlay.append(dlg_dif)
        dlg_dif.open = True
        self._page.update()

    # ─────────────────────────────────────────────────────────── #
    # Catálogo de productos                                        #
    # ─────────────────────────────────────────────────────────── #

    async def _on_click_catalogo(self, e) -> None:
        """Abre el selector de Excel, copia localmente y recarga el catálogo."""
        if not self._catalogo:
            snack(self._page, "El módulo de catálogo no está disponible.", ft.Colors.RED_800)
            return

        ruta = await pick_xlsx_file("Seleccionar catálogo de productos (.xlsx)")
        if not ruta:
            return

        snack(self._page, "Cargando catálogo...", ft.Colors.INDIGO_700)
        ok = self._catalogo.importar_xlsx(ruta)
        if ok:
            self._lbl_catalogo.value  = f"✓ Catálogo activo — {self._catalogo.total:,} productos"
            self._lbl_catalogo.color  = ft.Colors.GREEN_400
            self._lbl_catalogo.italic = False
            self._lbl_catalogo.update()
            snack(self._page, f"✓ Catálogo cargado: {self._catalogo.total:,} productos", ft.Colors.GREEN_800)
        else:
            self._lbl_catalogo.value  = "Error al cargar el archivo. Verifica el formato."
            self._lbl_catalogo.color  = ft.Colors.RED_400
            self._lbl_catalogo.italic = True
            self._lbl_catalogo.update()
            snack(self._page, "Error al leer el Excel. ¿Tiene la columna PRODUCTO?", ft.Colors.RED_800)

    # ─────────────────────────────────────────────────────────── #
    # Carpeta de datos clientes (UNC / red)                        #
    # ─────────────────────────────────────────────────────────── #

    async def _on_click_carpeta_datos(self, e) -> None:
        carpeta = await pick_directory("Carpeta donde guardar o leer clientes.json")
        if not carpeta:
            return
        self._carpeta_datos_f.value = carpeta
        self._carpeta_datos_f.update()

    async def _on_click_ruta_exportacion(self, e) -> None:
        carpeta = await pick_directory("Carpeta donde guardar los PDFs exportados")
        if not carpeta:
            return
        self._export_f.value = carpeta
        self._export_f.update()

    def _usar_solo_datos_locales(self, e) -> None:
        self._carpeta_datos_f.value = ""
        self._carpeta_datos_f.update()

    def _usar_carpeta_datos_por_defecto(self, e) -> None:
        self._carpeta_datos_f.value = DEFAULT_CARPETA_DATOS_CLIENTES
        self._carpeta_datos_f.update()
        snack(self._page, "Carpeta por defecto aplicada. Pulsa Guardar para confirmar.", ft.Colors.INDIGO_700)

    # ─────────────────────────────────────────────────────────── #
    # Carpeta de respaldo (diálogo nativo de Windows)             #
    # ─────────────────────────────────────────────────────────── #

    async def _on_click_carpeta(self, e) -> None:
        """Abre el diálogo nativo de Windows para seleccionar una carpeta."""
        carpeta = await pick_directory("Seleccionar carpeta de respaldo automático")
        if not carpeta:
            return  # Usuario canceló

        self._lbl_carpeta.value  = carpeta
        self._lbl_carpeta.color  = ft.Colors.GREEN_400
        self._lbl_carpeta.italic = False
        self._lbl_carpeta.update()

        # Activar BackupManager y persistir
        self._repo.backup_manager.set_carpeta(carpeta)
        config = self._repo.get_config()
        config["carpeta_respaldo"] = carpeta
        self._repo.save_config(config)

        snack(self._page, f"✓ Respaldo activado en: {carpeta}", ft.Colors.TEAL_800)

    def _desactivar_respaldo(self, e) -> None:
        self._repo.backup_manager.set_carpeta(None)
        self._lbl_carpeta.value  = "Sin carpeta de respaldo configurada."
        self._lbl_carpeta.color  = ft.Colors.GREY_500
        self._lbl_carpeta.italic = True
        self._lbl_carpeta.update()

        config = self._repo.get_config()
        config["carpeta_respaldo"] = ""
        self._repo.save_config(config)

        snack(self._page, "Respaldo automático desactivado.", ft.Colors.GREY_700)
