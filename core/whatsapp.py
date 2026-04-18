"""
core/whatsapp.py
Diseño de Ingeniería: Módulo especializado en la gestión de comunicaciones vía WhatsApp.
Encapsula la lógica de formateo de números, plantillas y apertura de navegador.
"""
from __future__ import annotations
import webbrowser
import urllib.parse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.cliente import Cliente
    from models.deuda import Deuda
    from database.repositorio import Repositorio

class WhatsAppManager:
    """Gestiona el motor de mensajería para notificaciones de deuda."""
    
    DEFAULT_TEMPLATE_DEUDA = (
        "Hola {nombre} 👋\n\n"
        "📝 *Resumen de tu cuenta:*\n"
        "{detalle}\n\n"
        "💰 Total deuda:  *${total}*\n"
        "✅ Abonado:      *${abonado}*\n"
        "⚠️ Saldo pendiente: *${saldo}*\n\n"
        "_Por favor comunicarse para coordinar el pago._"
    )

    DEFAULT_TEMPLATE_SALDADA = (
        "Hola {nombre} 🎉\n\n"
        "¡Excelentes noticias! Tu cuenta ha sido *saldada completamente*. "
        "Ya no tienes ningún saldo pendiente con nosotros. 🙌\n\n"
        "¡Gracias por tu pago! Te esperamos pronto. 😊"
    )

    @staticmethod
    def _formatear_telefono(telefono: str) -> str:
        """Convierte el teléfono al formato internacional (ej: 593 para Ecuador)."""
        tel = "".join(c for c in telefono if c.isdigit())
        if tel.startswith("0") and len(tel) == 10:
            return "593" + tel[1:]
        return tel

    @classmethod
    def enviar_resumen_deuda(cls, cliente: Cliente, deuda: Deuda, repo: Repositorio) -> str | None:
        """
        Construye y abre el link de WhatsApp con el resumen de la deuda.
        Retorna un mensaje de error si falla, o None si tiene éxito.
        """
        from utils.calculos import calcular_total, calcular_total_abonado, calcular_saldo_pendiente, calcular_pagos_aplicados

        total   = calcular_total(deuda)
        abonado = calcular_total_abonado(deuda)
        saldo   = calcular_saldo_pendiente(deuda)

        # Construir detalle de ítems usando calcular_pagos_aplicados (respeta selectivos)
        MAX_ITEMS = 15
        lineas = []
        pagos = calcular_pagos_aplicados(deuda)

        for item in deuda.items:
            p_aplicado = pagos.get(item.id, 0.0)
            tachado = p_aplicado >= item.subtotal and item.subtotal > 0
            if tachado:
                lineas.append(f"  ~{item.nombre} x{item.cantidad} = ${item.subtotal:.2f}~ (pagado)")
            elif p_aplicado > 0:
                lineas.append(f"  • {item.nombre} x{item.cantidad} = ${item.subtotal:.2f}\n    └ Abonó: ${p_aplicado:.2f} | Resta: ${item.subtotal - p_aplicado:.2f}")
            else:
                lineas.append(f"  • {item.nombre} x{item.cantidad} = ${item.subtotal:.2f}")

        detalle = "\n".join(lineas[-MAX_ITEMS:]) if lineas else " (sin productos)"
        if len(lineas) > MAX_ITEMS:
            detalle = f" ... y {len(lineas)-MAX_ITEMS} más\n" + detalle

        config = repo.get_config()
        template = config.get("wa_template_deuda", cls.DEFAULT_TEMPLATE_DEUDA)
        
        try:
            mensaje = template.format(
                nombre=cliente.nombre,
                detalle=detalle,
                total=f"{total:.2f}",
                abonado=f"{abonado:.2f}",
                saldo=f"{saldo:.2f}",
            )
        except Exception:
            mensaje = template

        tel = cls._formatear_telefono(cliente.telefono)
        url = f"https://wa.me/{tel}?text={urllib.parse.quote(mensaje)}"
        
        try:
            webbrowser.open(url)
            return None
        except Exception as ex:
            return str(ex)
