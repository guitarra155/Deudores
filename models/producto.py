"""
models/producto.py
Clase de datos para un Producto que puede agregarse a una deuda.
"""
from dataclasses import dataclass, field
import uuid


@dataclass
class Producto:
    nombre: str
    precio: float = 0.0
    codigo_barras: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "precio": self.precio,
            "codigo_barras": self.codigo_barras,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Producto":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            nombre=data.get("nombre", ""),
            precio=float(data.get("precio", 0.0)),
            codigo_barras=data.get("codigo_barras", ""),
        )
