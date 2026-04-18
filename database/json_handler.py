"""
database/json_handler.py
Capa de persistencia genérica: lee y escribe archivos JSON
usando rutas relativas a la raíz del proyecto para portabilidad total.
"""
import json
import os
from pathlib import Path


class JsonHandler:
    """Lee y escribe archivos JSON de forma segura."""

    def __init__(self, base_dir: Path):
        """
        Args:
            base_dir: Ruta absoluta a la carpeta raíz del proyecto.
                      Todos los archivos se referirán de forma relativa a ella.
        """
        self.base_dir = base_dir

    def _resolve(self, relative_path: str) -> Path:
        """Convierte una ruta relativa al proyecto en una ruta absoluta."""
        return self.base_dir / relative_path

    def load(self, relative_path: str, default=None):
        """
        Carga un archivo JSON.  Si no existe, devuelve `default`.
        """
        path = self._resolve(relative_path)
        if not path.exists():
            return default if default is not None else {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default if default is not None else {}

    def save(self, relative_path: str, data) -> None:
        """
        Guarda `data` como JSON en `relative_path` de forma atómica.
        Primero escribe en un archivo temporal y luego lo reemplaza.
        """
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Archivo temporal en la misma carpeta para garantizar atomicidad en el reemplazo
        temp_path = path.with_suffix(path.suffix + ".tmp")
        
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                # Opcional: f.flush() seguido de os.fsync(f.fileno()) para máxima seguridad
                # pero puede afectar un poco el rendimiento en discos mecánicos.
            
            # Reemplazo atómico (en Windows requiere os.replace)
            import os
            os.replace(temp_path, path)
        except Exception as e:
            # Si algo falla, intentamos limpiar el temporal
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            raise e

    def ensure_dir(self, relative_path: str) -> None:
        """Crea un directorio si no existe."""
        self._resolve(relative_path).mkdir(parents=True, exist_ok=True)
