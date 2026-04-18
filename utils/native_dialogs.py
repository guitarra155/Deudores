"""
utils/native_dialogs.py
Diálogos de selección de archivos y carpetas usando tkinter nativo de Windows.

Ventajas sobre ft.FilePicker:
  - Funciona con cualquier versión de Flet
  - Sin timeouts ni problemas de "invoke method listener"
  - Siempre abre el diálogo real de Windows
  - Se ejecuta en un hilo separado para no bloquear la UI de Flet
"""
from __future__ import annotations

import asyncio
import tkinter as tk
from tkinter import filedialog
from typing import Optional


def _make_root() -> tk.Tk:
    """Crea una ventana Tk oculta que queda siempre al frente."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def _pick_file_sync(
    title: str = "Seleccionar archivo",
    filetypes: list[tuple[str, str]] | None = None,
) -> Optional[str]:
    """Sincrónico: abre el diálogo de selección de archivo y retorna la ruta o None."""
    if filetypes is None:
        filetypes = [("Todos los archivos", "*.*")]
    root = _make_root()
    path = filedialog.askopenfilename(title=title, filetypes=filetypes, parent=root)
    root.destroy()
    return path if path else None


def _pick_directory_sync(title: str = "Seleccionar carpeta") -> Optional[str]:
    """Sincrónico: abre el diálogo de selección de carpeta y retorna la ruta o None."""
    root = _make_root()
    path = filedialog.askdirectory(title=title, parent=root)
    root.destroy()
    return path if path else None


# ── API async (para usar con await en handlers de Flet) ─────── #

async def pick_json_file(title: str = "Seleccionar archivo JSON") -> Optional[str]:
    """
    Abre el selector de Windows para archivos JSON.
    Retorna la ruta seleccionada o None si el usuario canceló.
    """
    return await asyncio.to_thread(
        _pick_file_sync,
        title,
        [("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
    )


async def pick_directory(title: str = "Seleccionar carpeta") -> Optional[str]:
    """
    Abre el selector de Windows para carpetas.
    Retorna la ruta seleccionada o None si el usuario canceló.
    """
    return await asyncio.to_thread(_pick_directory_sync, title)


async def pick_xlsx_file(title: str = "Seleccionar archivo Excel") -> Optional[str]:
    """
    Abre el selector de Windows para archivos Excel (.xlsx).
    Retorna la ruta seleccionada o None si el usuario canceló.
    """
    return await asyncio.to_thread(
        _pick_file_sync,
        title,
        [
            ("Archivo Excel", "*.xlsx"),
            ("Todos los archivos", "*.*"),
        ],
    )
