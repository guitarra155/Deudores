from pathlib import Path
import os
import sys
import asyncio
import threading
import ssl
import flet as ft

from core.system import aplicar_parche_ssl, main_exception_handler
from core.watchdog import init_watchdog
from core.keyboard import registrar_atajos_teclado
from core.sync import iniciar_vigilancia_de_red

aplicar_parche_ssl()


if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from database.repositorio import Repositorio
from utils.pdf_generator import PdfGenerator
from utils.catalogo import Catalogo
from views.helpers import snack
from views.clientes_view import ClientesView
from views.deudas_view import DeudasView
from views.configuracion_view import ConfiguracionView
from views.faltantes_view import mostrar_dialogo_faltantes
from views.notas_view import mostrar_dialogo_notas
from views.tareas_view import mostrar_dialogo_tareas


async def main(page: ft.Page):
    asyncio.get_running_loop().set_exception_handler(main_exception_handler)

    page.title = "Sistema de Gestion de Deudores"   # sin tildes para FindWindowW
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0d0f1a"
    page.window.width = 1100
    page.window.height = 720
    page.window.min_width = 500
    page.window.min_height = 560
    page.window.maximized = True
    page.padding = 0
    # Sin font_family externo → usa Segoe UI del sistema (ahorra ~0.5s en arranque)
    page.theme = ft.Theme(color_scheme_seed="indigo", use_material3=True)


    repo = Repositorio(BASE_DIR)

    # Catálogo de productos — carga en hilo de fondo (no bloquea el arranque)
    catalogo = Catalogo(BASE_DIR)
    catalogo.cargar_en_fondo()   # regresa inmediatamente, carga en paralelo

    def get_pdf_generator() -> PdfGenerator:
        config = repo.get_config()
        export_path_str = config.get("ruta_exportacion", "data_storage/exportaciones")
        export_path = Path(export_path_str)
        if not export_path.is_absolute():
            export_path = BASE_DIR / export_path_str
        return PdfGenerator(config=config, export_dir=export_path)

    # Referencia mutable para que el lambda de clientes_view alcance a deudas_view
    # (instanciada después) sin problema de forward-reference.
    _dv_ref: list = []

    clientes_view = ClientesView(
        repo=repo,
        on_cliente_selected=lambda cliente: _dv_ref[0].cargar_cliente(cliente),
        page=page,
    )

    deudas_view = DeudasView(
        repo=repo,
        page=page,
        get_pdf_generator=get_pdf_generator,
        on_add_cliente=clientes_view._abrir_dialogo_nuevo,
        catalogo=catalogo,
        on_deuda_changed=clientes_view._refresh_lista,  # actualiza saldos en tiempo real
    )
    _dv_ref.append(deudas_view)   # resolver la referencia circular

    # ── Diálogo de configuración (singleton) ─────────────────────── #
    _config_dlg: ConfiguracionView | None = None

    async def abrir_config(e):
        nonlocal _config_dlg
        if _config_dlg is None:
            def _on_config_saved():
                # Refrescar lista de clientes (por si se importaron clientes)
                clientes_view._refresh_lista()
                # Cerrar el diálogo automáticamente al guardar
                if _config_dlg:
                    _config_dlg.open = False
                page.update()

            _config_dlg = ConfiguracionView(
                repo=repo,
                page=page,
                catalogo=catalogo,
                on_saved=_on_config_saved,
            )
            page.overlay.append(_config_dlg)
        _config_dlg.recargar_config()
        _config_dlg.open = True
        page.update()

    # ── AppBar ─────────────────────────────────────────────────── #
    page.appbar = ft.AppBar(
        leading=ft.Row(
            [
                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=ft.Colors.AMBER_400, size=26),
                ft.Text("DeudorPro", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        leading_width=160,
        bgcolor="#131627",
        actions=[
            ft.IconButton(
                icon=ft.Icons.NOTE_ALT_OUTLINED,
                icon_color=ft.Colors.INDIGO_300,
                tooltip="Notas del local (Ctrl+O)",
                on_click=lambda e: mostrar_dialogo_notas(page, repo),
            ),
            ft.IconButton(
                icon=ft.Icons.CHECKLIST_OUTLINED,
                icon_color=ft.Colors.GREEN_400,
                tooltip="Tareas del local (Ctrl+T)",
                on_click=lambda e: mostrar_dialogo_tareas(page, repo),
            ),
            ft.IconButton(
                icon=ft.Icons.SHOPPING_BASKET_OUTLINED,
                icon_color=ft.Colors.AMBER_500,
                tooltip="Lista de mercancía faltante (Ctrl+L)",
                on_click=lambda e: mostrar_dialogo_faltantes(page, repo, catalogo),
            ),
            ft.IconButton(
                icon=ft.Icons.SETTINGS_OUTLINED,
                icon_color=ft.Colors.GREY_400,
                tooltip="Configuración del negocio",
                on_click=abrir_config,
            ),
        ],
    )

    panel_lateral = ft.Container(
        content=clientes_view,
        width=260,
        bgcolor="#131627",
        border=ft.Border.only(right=ft.BorderSide(1, ft.Colors.INDIGO_900)),
    )

    zona_deudas = ft.Container(
        content=deudas_view,
        expand=True,
        bgcolor="#0d0f1a",
    )

    # ── Handler de teclado global ───────────────────────────────── #
    registrar_atajos_teclado(page, clientes_view, deudas_view)

    # ── Render principal ────────────────────────────────────────── #
    page.add(ft.Row([panel_lateral, zona_deudas], expand=True, spacing=0))

    # ── clientes.json en red ────────────────────────────────────── #
    iniciar_vigilancia_de_red(page, repo, clientes_view, deudas_view)

    # ── Cierre limpio del proceso ───────────────────────────────── #
    # Estrategia 1: evento de ventana Flet (desktop)
    try:
        async def window_event(e):
            if hasattr(e, "data") and e.data == "close":
                os._exit(0)
        page.window.on_event = window_event
    except Exception:
        pass

    # Estrategia 2: on_disconnect (modo web / fallback)
    page.on_disconnect = lambda e: os._exit(0)

    # Estrategia 3: watchdog nativo de Windows
    init_watchdog()


if __name__ == "__main__":
    ft.run(main)
