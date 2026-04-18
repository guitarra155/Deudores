"""
models/deuda.py
Clases de datos para una Deuda, sus ítems y los Abonos realizados.
"""
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class DeudaItem:
    """Un renglón de producto dentro de una deuda."""
    nombre: str
    codigo_barras: str
    precio: float
    cantidad: int = 1
    fecha: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def subtotal(self) -> float:
        return round(self.precio * self.cantidad, 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "codigo_barras": self.codigo_barras,
            "precio": self.precio,
            "cantidad": self.cantidad,
            "subtotal": self.subtotal,   # cantidad × precio — calculado al guardar
            "fecha": self.fecha,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeudaItem":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            nombre=data.get("nombre", ""),
            codigo_barras=data.get("codigo_barras", ""),
            precio=float(data.get("precio", 0.0)),
            cantidad=int(data.get("cantidad", 1)),
            fecha=data.get("fecha", datetime.now().strftime("%Y-%m-%d")),
        )


@dataclass
class Abono:
    """Pago parcial sobre una deuda."""
    monto: float
    nota: str = ""
    fecha: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # IDs de ítems cubiertos por este abono selectivo. Si está vacío → abono general.
    items_ids: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "monto": self.monto,
            "nota": self.nota,
            "fecha": self.fecha,
        }
        if self.items_ids:  # Solo guardar si no está vacío (compatibilidad hacia atrás)
            d["items_ids"] = self.items_ids
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Abono":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            monto=float(data.get("monto", 0.0)),
            nota=data.get("nota", ""),
            fecha=data.get("fecha", datetime.now().strftime("%Y-%m-%d")),
            items_ids=data.get("items_ids", []),
        )


@dataclass
class Deuda:
    """Deuda completa de un cliente, con ítems y abonos."""
    cliente_id: str
    items: list = field(default_factory=list)       # Lista de DeudaItem
    abonos: list = field(default_factory=list)      # Lista de Abono
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    fecha_creacion: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "fecha_creacion": self.fecha_creacion,
            "items": [i.to_dict() for i in self.items],
            "abonos": [a.to_dict() for a in self.abonos],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Deuda":
        deuda = cls(
            id=data.get("id", str(uuid.uuid4())),
            cliente_id=data.get("cliente_id", ""),
            fecha_creacion=data.get("fecha_creacion", datetime.now().isoformat()),
        )
        deuda.items = [DeudaItem.from_dict(i) for i in data.get("items", [])]
        deuda.abonos = [Abono.from_dict(a) for a in data.get("abonos", [])]
        return deuda
