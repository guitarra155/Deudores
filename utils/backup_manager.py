"""
utils/backup_manager.py
Gestiona el respaldo automático de clientes.json a una carpeta elegida por el usuario.

- Realiza una copia al momento de cada guardado (si la carpeta está configurada).
- Ejecuta un respaldo periódico cada 30 minutos usando un hilo daemon.
- El respaldo siempre reemplaza al anterior (un solo archivo: clientes_backup.json).
- No modifica nunca el archivo original.
"""
from __future__ import annotations

import shutil
import threading
from pathlib import Path


_CLIENTES_BACKUP = "clientes_backup.json"
_FALTANTES_BACKUP = "faltantes_backup.json"
_INTERVAL_SECONDS = 30 * 60  # 30 minutos


class BackupManager:
    """Maneja copias de seguridad de clientes.json en una carpeta elegida por el usuario."""

    def __init__(self, origen: Path):
        """
        Args:
            origen: Ruta absoluta al archivo clientes.json original.
        """
        self._origen = origen
        self._carpeta_destino: Path | None = None
        self._timer: threading.Timer | None = None

    def set_origen(self, origen: Path) -> None:
        """Actualiza el archivo fuente (p. ej. si cambia la carpeta de datos en red)."""
        self._origen = origen

    # ------------------------------------------------------------------ #
    # Configuración                                                        #
    # ------------------------------------------------------------------ #
    def set_carpeta(self, carpeta: str | Path | None) -> None:
        """
        Establece (o elimina) la carpeta de respaldo.
        Si `carpeta` es None o vacío, desactiva el respaldo periódico.
        """
        self._cancelar_timer()

        if carpeta:
            self._carpeta_destino = Path(carpeta)
            self._carpeta_destino.mkdir(parents=True, exist_ok=True)
            # Primer respaldo inmediato al activar
            self._hacer_copia()
            # Programar el periódico
            self._programar_periodico()
        else:
            self._carpeta_destino = None

    @property
    def carpeta(self) -> Path | None:
        return self._carpeta_destino

    # ------------------------------------------------------------------ #
    # Respaldo                                                             #
    # ------------------------------------------------------------------ #
    def respaldar_ahora(self) -> bool:
        """
        Realiza un respaldo inmediato si la carpeta está configurada.
        Retorna True si la copia se realizó, False si no hay carpeta configurada.
        """
        if not self._carpeta_destino:
            return False
        return self._hacer_copia()

    def _hacer_copia(self) -> bool:
        """Copia el archivo origen (y faltantes.json si existe) al destino. 
        Verifica integridad antes de copiar para no pisar un buen respaldo con basura.
        """
        if not self._carpeta_destino:
            return False
            
        success = True
        import json
        
        def _es_valido(p: Path) -> bool:
            if not p.exists() or p.stat().st_size == 0:
                return False
            try:
                with open(p, "r", encoding="utf-8") as f:
                    json.load(f)
                return True
            except Exception:
                return False

        # 1. Respaldar clientes.json
        if self._origen.exists():
            if _es_valido(self._origen):
                try:
                    dest_clientes = self._carpeta_destino / _CLIENTES_BACKUP
                    shutil.copy2(str(self._origen), str(dest_clientes))
                except Exception as e:
                    print(f"[BackupManager] Error clientes: {e}")
                    success = False
            else:
                print(f"[BackupManager] Omitiendo respaldo de clientes: archivo origen parece corrupto.")
                success = False
        
        # 2. Respaldar faltantes.json (si existe en la misma carpeta)
        faltantes_path = self._origen.parent / "faltantes.json"
        if faltantes_path.exists():
            if _es_valido(faltantes_path):
                try:
                    dest_faltantes = self._carpeta_destino / _FALTANTES_BACKUP
                    shutil.copy2(str(faltantes_path), str(dest_faltantes))
                except Exception as e:
                    print(f"[BackupManager] Error faltantes: {e}")
                    success = False
            else:
                print(f"[BackupManager] Omitiendo respaldo de faltantes: archivo origen parece corrupto.")
                success = False
                
        return success

    # ------------------------------------------------------------------ #
    # Timer periódico                                                      #
    # ------------------------------------------------------------------ #
    def _programar_periodico(self) -> None:
        """Programa el siguiente respaldo automático en 30 minutos."""
        self._cancelar_timer()
        self._timer = threading.Timer(_INTERVAL_SECONDS, self._tick_periodico)
        self._timer.daemon = True
        self._timer.start()

    def _tick_periodico(self) -> None:
        """Callback del timer: realiza la copia y reprograma el siguiente ciclo."""
        self._hacer_copia()
        if self._carpeta_destino:           # Si aún hay carpeta activa, vuelve a programar
            self._programar_periodico()

    def _cancelar_timer(self) -> None:
        """Cancela el timer periódico si existe."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
