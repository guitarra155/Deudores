"""
database/repositorio.py
CRUD de alto nivel para Clientes y Deudas.
Apoya la separación completa entre lógica de negocio e interfaz.
"""
import json
from pathlib import Path
from typing import List, Optional

from models.cliente import Cliente
from models.deuda import Deuda
from .json_handler import JsonHandler
from utils.backup_manager import BackupManager

# Rutas relativas al proyecto
_CLIENTES_FILE = "data_storage/clientes.json"
_CONFIG_FILE = "data_storage/config.json"

# Carpeta UNC por defecto: clientes.json = esta ruta + "/clientes.json".
# Vacío en config → se usa data_storage/clientes.json junto al programa.
# También usada desde la vista de configuración (botón "carpeta por defecto").
DEFAULT_CARPETA_DATOS_CLIENTES = r"\\DESKTOP-40OQDAH\Tio-Hugo\TioHugo\Respaldo_No_Borrar"

_CONFIG_DEFAULT = {
    "nombre_negocio": "Mi Negocio",
    "direccion": "",
    "telefono": "",
    "slogan": "",
    "ruta_exportacion": "data_storage/exportaciones",
    "carga_archivos_habilitada": True,   # switch para habilitar/deshabilitar importar
    "carpeta_respaldo": "",              # carpeta elegida por el usuario para backup
    "carpeta_datos_clientes": DEFAULT_CARPETA_DATOS_CLIENTES,
    "faltantes": [],                     # Lista global de productos por comprar
}


class Repositorio:
    """Gestiona toda la persistencia de la aplicación."""

    def __init__(self, base_dir: Path):
        self._handler   = JsonHandler(base_dir)
        self._base_dir  = base_dir
        self._handler.ensure_dir("data_storage")
        self._handler.ensure_dir("data_storage/exportaciones")

        # Cache en memoria: elimina lecturas de disco innecesarias.
        # El JSON se lee UNA sola vez al arrancar; todo lo demás usa el cache.
        self._raw_cache: dict | None = None
        # st_mtime del clientes.json y faltantes.json visto al último leer/escribir nosotros (varias PCs → sondeo).
        self._disk_mtime_cached: float | None = None
        self._faltantes_mtime_cached: float | None = None

        self._backup = BackupManager(self._clientes_path())

        # Activar backup si ya había carpeta guardada en config
        config = self.get_config()
        carpeta = config.get("carpeta_respaldo", "")
        if carpeta:
            self._backup.set_carpeta(carpeta)

        # mtimes para sincronización de archivos globales
        self._notas_mtime_cached: float | None = None
        self._tareas_mtime_cached: float | None = None

    # ------------------------------------------------------------------ #
    # Acceso al BackupManager (para la vista de configuración)            #
    # ------------------------------------------------------------------ #
    @property
    def backup_manager(self) -> BackupManager:
        return self._backup

    # ------------------------------------------------------------------ #
    # CONFIGURACIÓN                                                        #
    # ------------------------------------------------------------------ #
    def get_config(self) -> dict:
        data = self._handler.load(_CONFIG_FILE, default=_CONFIG_DEFAULT.copy())
        # Asegurar que todas las claves por defecto existan
        for k, v in _CONFIG_DEFAULT.items():
            data.setdefault(k, v)
        return data

    def save_config(self, config: dict) -> None:
        self._handler.save(_CONFIG_FILE, config)
        self._backup.set_origen(self._clientes_path())
        self._disk_mtime_cached = None
        self.invalidar_cache()

    def _faltantes_path(self) -> Path:
        """Ruta de faltantes.json, siempre en la misma carpeta que clientes.json."""
        return self._clientes_path().parent / "faltantes.json"

    def _notas_path(self) -> Path:
        """Ruta de notas.json, siempre en la misma carpeta que clientes.json."""
        return self._clientes_path().parent / "notas.json"

    def _tareas_path(self) -> Path:
        """Ruta de tareas.json, siempre en la misma carpeta que clientes.json."""
        return self._clientes_path().parent / "tareas.json"

    def get_faltantes(self) -> List[str]:
        path = self._faltantes_path()
        if path.exists():
            try:
                self._faltantes_mtime_cached = path.stat().st_mtime
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        
        self._faltantes_mtime_cached = None
        
        # MIGRACIÓN: Si no existe el archivo, ver si hay datos en config.json
        cfg = self.get_config()
        faltantes = cfg.get("faltantes", [])
        if faltantes:
            self.save_faltantes(faltantes)
            # Limpiar de config para no duplicar
            if "faltantes" in cfg:
                del cfg["faltantes"]
                self.save_config(cfg)
        return faltantes

    def save_faltantes(self, faltantes: List[str]) -> None:
        path = self._faltantes_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(faltantes, f, indent=4, ensure_ascii=False)
            
            # Actualizar timestamp para no disparar auto-sincronización propia
            self._faltantes_mtime_cached = path.stat().st_mtime
            
            # Notificar al backup manager para que respalde el nuevo estado
            self._backup.respaldar_ahora()
        except Exception as e:
            print(f"[Error] No se pudo guardar faltantes: {e}")

    def _clientes_path(self) -> Path:
        """
        Ruta absoluta de clientes.json.
        Si `carpeta_datos_clientes` está vacía → local al proyecto.
        Si es una carpeta (UNC o local) → .../clientes.json.
        Si termina en .json → se usa esa ruta de archivo completa.
        """
        cfg = self.get_config()
        raw = (cfg.get("carpeta_datos_clientes") or "").strip()
        if not raw:
            return self._base_dir / _CLIENTES_FILE
        p = Path(raw)
        if p.suffix.lower() == ".json":
            return p
        return p / "clientes.json"

    def _load_clientes_file(self) -> dict:
        path = self._clientes_path()
        if not path.exists():
            self._disk_mtime_cached = None
            return {"clientes": [], "deudas": {}}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._disk_mtime_cached = path.stat().st_mtime
            return data
        except (json.JSONDecodeError, OSError):
            return {"clientes": [], "deudas": {}}

    def _save_clientes_file(self, raw: dict) -> None:
        path = self._clientes_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        try:
            self._disk_mtime_cached = path.stat().st_mtime
        except OSError:
            pass

    def sincronizar_desde_disco_si_otro_guardo(self) -> bool:
        """
        Si clientes.json en disco es más reciente que nuestro cache (otra PC guardó),
        invalida cache y recarga desde disco. Devuelve True si hubo recarga.
        """
        path = self._clientes_path()
        try:
            if not path.exists():
                if self._disk_mtime_cached is not None:
                    self.invalidar_cache()
                    self._raw_cache = {"clientes": [], "deudas": {}}
                    self._disk_mtime_cached = None
                    return True
                return False
            m = path.stat().st_mtime
        except OSError:
            return False

        if self._disk_mtime_cached is None:
            self._disk_mtime_cached = m
            return False

        if m <= self._disk_mtime_cached + 1e-6:
            return False

        self.invalidar_cache()
        self._raw_cache = self._load_clientes_file()
        return True

    def sincronizar_faltantes_si_otro_guardo(self) -> bool:
        """Chequea si faltantes.json cambió en red."""
        path = self._faltantes_path()
        if not path.exists():
            if self._faltantes_mtime_cached is not None:
                self._faltantes_mtime_cached = None
                return True
            return False
            
        try:
            m = path.stat().st_mtime
            if self._faltantes_mtime_cached is None:
                self._faltantes_mtime_cached = m
                return False
            
            if m > self._faltantes_mtime_cached + 1e-6:
                # El archivo cambió, el mtime se actualizará al llamar a get_faltantes()
                return True
        except OSError:
            pass
        return False

    def get_notas(self) -> list:
        """Lee las notas del local desde notas.json. Retorna lista vacía si no existe."""
        path = self._notas_path()
        if path.exists():
            try:
                self._notas_mtime_cached = path.stat().st_mtime
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Compatibilidad: formato antiguo era {"texto": "..."}
                    if isinstance(data, dict):
                        texto_viejo = data.get("texto", "")
                        return [l for l in texto_viejo.splitlines() if l.strip()] if texto_viejo else []
                    # Nuevo formato: lista de strings
                    if isinstance(data, list):
                        return data
            except Exception:
                return []
        self._notas_mtime_cached = None
        return []

    def save_notas(self, notas: list) -> None:
        path = self._notas_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(notas, f, ensure_ascii=False, indent=2)
            self._notas_mtime_cached = path.stat().st_mtime
        except Exception as e:
            print(f"[Error] No se pudo guardar notas: {e}")

    def sincronizar_notas_si_otro_guardo(self) -> bool:
        """Chequea si notas.json cambió en red."""
        path = self._notas_path()
        if not path.exists():
            if self._notas_mtime_cached is not None:
                self._notas_mtime_cached = None
                return True
            return False
        try:
            m = path.stat().st_mtime
            if self._notas_mtime_cached is None:
                self._notas_mtime_cached = m
                return False
            if m > self._notas_mtime_cached + 1e-6:
                return True
        except OSError:
            pass
        return False

    def get_tareas(self) -> list:
        """Lee las tareas desde tareas.json. Retorna lista vacía si no existe."""
        path = self._tareas_path()
        if path.exists():
            try:
                self._tareas_mtime_cached = path.stat().st_mtime
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        self._tareas_mtime_cached = None
        return []

    def save_tareas(self, tareas: list) -> None:
        path = self._tareas_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(tareas, f, ensure_ascii=False, indent=2)
            self._tareas_mtime_cached = path.stat().st_mtime
        except Exception as e:
            print(f"[Error] No se pudo guardar tareas: {e}")

    def sincronizar_tareas_si_otro_guardo(self) -> bool:
        """Chequea si tareas.json cambió en red."""
        path = self._tareas_path()
        if not path.exists():
            if self._tareas_mtime_cached is not None:
                self._tareas_mtime_cached = None
                return True
            return False
        try:
            m = path.stat().st_mtime
            if self._tareas_mtime_cached is None:
                self._tareas_mtime_cached = m
                return False
            if m > self._tareas_mtime_cached + 1e-6:
                return True
        except OSError:
            pass
        return False

    # ------------------------------------------------------------------ #
    # CLIENTES                                                             #
    # ------------------------------------------------------------------ #
    def _load_raw(self) -> dict:
        """Carga desde RAM (cache) o disco si es la primera vez — lectura instantánea."""
        if self._raw_cache is not None:
            return self._raw_cache
        self._raw_cache = self._load_clientes_file()
        return self._raw_cache

    def _save_raw(self, raw: dict) -> None:
        self._raw_cache = raw          # actualizar cache antes de escribir al disco
        self._save_clientes_file(raw)
        # Backup en hilo separado: la copia de archivo es lenta en HDD
        # y no necesita bloquear la UI (es dato secundario)
        import threading
        threading.Thread(target=self._backup.respaldar_ahora, daemon=True).start()

    def invalidar_cache(self) -> None:
        """Fuerza recarga desde disco en la próxima operación (usar tras importar JSON)."""
        self._raw_cache = None

    def get_all_clientes(self) -> List[Cliente]:
        raw = self._load_raw()
        return [Cliente.from_dict(c) for c in raw.get("clientes", [])]

    def get_ultimas_fechas_items(self) -> dict:
        """
        Retorna {cliente_id: ultima_fecha_item} en un solo paso por el cache (RAM).
        Fecha en formato YYYY-MM-DD o "" si el cliente no tiene ítems.
        Permite ordenar por último movimiento sin lecturas adicionales de disco.
        """
        raw    = self._load_raw()
        deudas = raw.get("deudas", {})
        resultado = {}
        for cid, d in deudas.items():
            items  = d.get("items", [])
            fechas = [it.get("fecha", "") for it in items if it.get("fecha")]
            resultado[cid] = max(fechas) if fechas else ""
        return resultado

    def get_cliente(self, cliente_id: str) -> Optional[Cliente]:
        for c in self.get_all_clientes():
            if c.id == cliente_id:
                return c
        return None

    def save_cliente(self, cliente: Cliente) -> None:
        """Crea o actualiza un cliente."""
        raw = self._load_raw()
        clientes = raw.get("clientes", [])
        idx = next((i for i, c in enumerate(clientes) if c["id"] == cliente.id), None)
        if idx is not None:
            clientes[idx] = cliente.to_dict()
        else:
            clientes.append(cliente.to_dict())
        raw["clientes"] = clientes
        self._save_raw(raw)

    def delete_cliente(self, cliente_id: str) -> None:
        """Elimina cliente y todas sus deudas."""
        raw = self._load_raw()
        raw["clientes"] = [c for c in raw.get("clientes", []) if c["id"] != cliente_id]
        deudas = raw.get("deudas", {})
        deudas.pop(cliente_id, None)
        raw["deudas"] = deudas
        self._save_raw(raw)

    def get_clientes_con_saldos(self) -> List[tuple[Cliente, float]]:
        """Devuelve una lista de (Cliente, saldo_pendiente) para todos los clientes."""
        from utils.calculos import calcular_saldo_pendiente
        raw = self._load_raw()
        clientes_raw = raw.get("clientes", [])
        deudas_raw = raw.get("deudas", {})

        result = []
        for c_dict in clientes_raw:
            c = Cliente.from_dict(c_dict)
            d_data = deudas_raw.get(c.id)
            if d_data:
                d = Deuda.from_dict(d_data)
                saldo = calcular_saldo_pendiente(d)
            else:
                saldo = 0.0
            result.append((c, saldo))
        return result

    def importar_clientes_desde_json(self, ruta_archivo: str) -> dict:
        """
        Analiza un archivo JSON y detecta diferencias con los datos actuales.
        NO aplica cambios. Retorna un dict con:
            {
              "nuevos": [Cliente, ...],
              "modificados": [(cliente_actual, cliente_importado), ...],
              "eliminados": [Cliente, ...],
              "sin_cambio": [Cliente, ...],
            }
        """
        import json
        try:
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                datos_import = json.load(f)
        except Exception as e:
            raise ValueError(f"No se pudo leer el archivo: {e}")

        # Aceptar tanto el formato completo {"clientes": [...]} como lista directa [...]
        if isinstance(datos_import, list):
            clientes_importados = datos_import
        elif isinstance(datos_import, dict) and "clientes" in datos_import:
            clientes_importados = datos_import["clientes"]
        else:
            raise ValueError("Formato no válido. Se espera {\"clientes\": [...]} o una lista.")

        actuales = {c.id: c for c in self.get_all_clientes()}
        importados = {}
        for d in clientes_importados:
            try:
                c = Cliente.from_dict(d)
                importados[c.id] = c
            except Exception:
                pass  # Omitir entradas inválidas

        nuevos      = [c for cid, c in importados.items() if cid not in actuales]
        eliminados  = [c for cid, c in actuales.items() if cid not in importados]
        sin_cambio  = []
        modificados = []
        for cid in set(actuales) & set(importados):
            ca = actuales[cid]
            ci = importados[cid]
            # Comparar TODOS los campos del cliente
            if (ca.nombre        == ci.nombre and
                    ca.telefono  == ci.telefono and
                    ca.direccion == ci.direccion and
                    ca.fecha_creacion == ci.fecha_creacion):
                sin_cambio.append(ca)
            else:
                modificados.append((ca, ci))

        return {
            "nuevos":      nuevos,
            "modificados": modificados,
            "eliminados":  eliminados,
            "sin_cambio":  sin_cambio,
        }

    def aplicar_importacion(self, ruta_archivo: str) -> None:
        """
        Aplica la importación del JSON: reemplaza la lista de clientes con
        los del archivo importado.
        Si el archivo también contiene 'deudas', las importa también,
        conservando las deudas existentes de clientes que no estén en el archivo.
        """
        import json
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            datos_import = json.load(f)

        if isinstance(datos_import, list):
            # Lista directa de clientes — sin deudas
            clientes_importados = datos_import
            deudas_importadas   = None
        elif isinstance(datos_import, dict) and "clientes" in datos_import:
            clientes_importados = datos_import["clientes"]
            deudas_importadas   = datos_import.get("deudas")  # puede ser None
        else:
            raise ValueError("Formato no válido.")

        raw = self._load_raw()

        # Asegurar que todos los campos del cliente estén completos
        clientes_normalizados = []
        for d in clientes_importados:
            try:
                c = Cliente.from_dict(d)      # normaliza campos faltantes
                clientes_normalizados.append(c.to_dict())  # guarda con todos los campos
            except Exception:
                pass

        raw["clientes"] = clientes_normalizados

        # Importar deudas si vienen en el archivo (respaldo completo)
        if deudas_importadas and isinstance(deudas_importadas, dict):
            deudas_actuales = raw.get("deudas", {})
            # Merge: las del archivo tienen prioridad, las locales se conservan si no están
            deudas_actuales.update(deudas_importadas)
            raw["deudas"] = deudas_actuales

        self._save_raw(raw)
        self.invalidar_cache()   # forzar recarga limpia tras importación masiva

    # ------------------------------------------------------------------ #
    # DEUDAS                                                               #
    # ------------------------------------------------------------------ #
    def get_deuda(self, cliente_id: str) -> Deuda:
        """Devuelve la Deuda del cliente.  Si no existe, crea una vacía."""
        raw = self._load_raw()
        deudas_raw = raw.get("deudas", {})
        if cliente_id in deudas_raw:
            return Deuda.from_dict(deudas_raw[cliente_id])
        return Deuda(cliente_id=cliente_id)

    def save_deuda(self, deuda: Deuda) -> None:
        raw = self._load_raw()
        deudas = raw.get("deudas", {})
        deudas[deuda.cliente_id] = deuda.to_dict()
        raw["deudas"] = deudas
        self._save_raw(raw)
