"""
views/helpers.py
Funciones de UI compartidas entre todas las vistas Flet.
Centraliza la lógica de diálogos y notificaciones para evitar duplicación.
"""
import flet as ft


def abrir_dlg(page: ft.Page, dlg: ft.AlertDialog) -> None:
    """Añade el diálogo al overlay y lo abre."""
    page.dialog = dlg
    if dlg not in page.overlay:
        page.overlay.append(dlg)
    dlg.open = True
    page.update()


def cerrar_dlg(page: ft.Page, dlg: ft.AlertDialog) -> None:
    """Cierra el diálogo sin eliminarlo del overlay."""
    dlg.open = False
    page.update()


def snack(page: ft.Page, mensaje: str, color: str) -> None:
    """Muestra un SnackBar temporal con el mensaje y color indicados."""
    print(f"[UI] {mensaje}")
    sb = ft.SnackBar(content=ft.Text(mensaje), bgcolor=color)
    page.snack_bar = sb
    if sb not in page.overlay:
        page.overlay.append(sb)
    sb.open = True
    page.update()
