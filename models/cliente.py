"""
models/cliente.py
Clase de datos para un Cliente del sistema.
"""
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class Cliente:
    nombre: str
    telefono: str = ""
    direccion: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    fecha_creacion: str = field(default_factory=lambda: datetime.now().isoformat())

    # ------------------------------------------------------------------ #
    # Serialización                                                        #
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "telefono": self.telefono,
            "direccion": self.direccion,
            "fecha_creacion": self.fecha_creacion,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Cliente":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            nombre=data.get("nombre", ""),
            telefono=data.get("telefono", ""),
            direccion=data.get("direccion", ""),
            fecha_creacion=data.get("fecha_creacion", datetime.now().isoformat()),
        )
