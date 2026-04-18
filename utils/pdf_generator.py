"""
utils/pdf_generator.py
Genera tickets de deuda en formato POS 58 mm usando fpdf2.
"""
from pathlib import Path
from datetime import datetime
from fpdf import FPDF

from models.cliente import Cliente
from models.deuda import Deuda
from utils.calculos import calcular_total, calcular_total_abonado, calcular_saldo_pendiente, calcular_pagos_aplicados

# Ancho útil en mm para rollo 58mm (márgenes incluidos)
PAGE_WIDTH = 58
MARGIN = 3


class TicketPDF(FPDF):
    """FPDF personalizado para tickets POS de 58 mm."""

    def __init__(self, config: dict, alto: float = 200):
        super().__init__(unit="mm", format=(PAGE_WIDTH, alto))
        self.config = config
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=False)
        self.add_page()

    def header_negocio(self):
        """Encabezado con datos del negocio."""
        self.set_font("Helvetica", "B", 9)
        nombre = self.config.get("nombre_negocio", "Mi Negocio")
        self.cell(0, 5, nombre, ln=True, align="C")

        self.set_font("Helvetica", "", 7)
        if self.config.get("direccion"):
            self.cell(0, 4, self.config["direccion"], ln=True, align="C")
        if self.config.get("telefono"):
            self.cell(0, 4, f"Tel: {self.config['telefono']}", ln=True, align="C")
        if self.config.get("slogan"):
            self.set_font("Helvetica", "I", 7)
            self.cell(0, 4, self.config["slogan"], ln=True, align="C")

        self._linea()

    def _linea(self):
        self.set_font("Helvetica", "", 7)
        self.cell(0, 3, "-" * 42, ln=True, align="C")

    def datos_cliente(self, cliente: Cliente, fecha: str):
        self.set_font("Helvetica", "", 7)
        self.cell(0, 4, f"Cliente : {cliente.nombre}", ln=True)
        if cliente.telefono:
            self.cell(0, 4, f"Tel     : {cliente.telefono}", ln=True)
        self.cell(0, 4, f"Fecha   : {fecha}", ln=True)
        self._linea()

    def tabla_items(self, deuda: Deuda):
        ancho_util = PAGE_WIDTH - 2 * MARGIN
        col_prod = ancho_util * 0.44
        col_cant = ancho_util * 0.12
        col_prec = ancho_util * 0.22
        col_subt = ancho_util * 0.22

        # Cabecera
        self.set_font("Helvetica", "B", 6.5)
        self.cell(col_prod, 4, "Producto", border="B")
        self.cell(col_cant, 4, "Ctd", border="B", align="C")
        self.cell(col_prec, 4, "P.Unit", border="B", align="R")
        self.cell(col_subt, 4, "Subtot.", border="B", align="R", ln=True)

        # Filas — usa calcular_pagos_aplicados para respetar abonos selectivos
        self.set_font("Helvetica", "", 6.5)
        pagos = calcular_pagos_aplicados(deuda)
        
        # Ordenar ítems por fecha (del más antiguo al más nuevo)
        items_ordenados = sorted(deuda.items, key=lambda x: x.fecha)
        
        for item in items_ordenados:
            pago_aplicado = pagos.get(item.id, 0.0)
            tachado   = pago_aplicado >= item.subtotal and item.subtotal > 0
            es_parcial = pago_aplicado > 0 and not tachado

            nombre_limpio = item.nombre[:15] if len(item.nombre) > 15 else item.nombre
            if tachado:
                self.set_text_color(130, 130, 130)
                nombre_limpio = f"(pagado) {nombre_limpio}"
            else:
                self.set_text_color(0, 0, 0)

            self.cell(col_prod, 4, nombre_limpio)
            self.cell(col_cant, 4, str(item.cantidad), align="C")
            self.cell(col_prec, 4, f"{item.precio:.2f}", align="R")
            self.cell(col_subt, 4, f"{item.subtotal:.2f}", align="R", ln=True)
            self.set_text_color(0, 0, 0)

            if es_parcial:
                falta = item.subtotal - pago_aplicado
                self.set_font("Helvetica", "I", 5.5)
                self.set_text_color(80, 80, 80)
                self.cell(2, 3, "")
                self.cell(0, 3, f"-> Abono: ${pago_aplicado:.2f} | Resta: ${falta:.2f}", ln=True)
                self.set_font("Helvetica", "", 6.5)

        self._linea()

    def resumen_financiero(self, deuda: Deuda):
        total = calcular_total(deuda)
        abonado = calcular_total_abonado(deuda)
        saldo = calcular_saldo_pendiente(deuda)

        self.set_font("Helvetica", "", 7)
        self.cell(0, 4, f"Total deuda   : $ {total:.2f}", ln=True, align="R")
        self.cell(0, 4, f"Total abonado : $ {abonado:.2f}", ln=True, align="R")

        self.set_font("Helvetica", "B", 8)
        self.cell(0, 5, f"SALDO PENDIENTE: $ {saldo:.2f}", ln=True, align="R")

        if deuda.abonos:
            self._linea()
            self.set_font("Helvetica", "B", 7)
            self.cell(0, 4, "Historial de abonos:", ln=True)
            self.set_font("Helvetica", "", 6.5)
            for a in deuda.abonos:
                self.cell(0, 3.5, f"  {a.fecha}  +$ {a.monto:.2f}  {a.nota}", ln=True)

    def pie(self):
        self._linea()
        self.set_font("Helvetica", "I", 6.5)
        self.cell(0, 4, "Gracias por su preferencia", ln=True, align="C")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cell(0, 3.5, f"Impreso: {ts}", ln=True, align="C")


class PdfGenerator:
    """Fachada de generación de PDFs."""

    def __init__(self, config: dict, export_dir: Path):
        self.config = config
        self.export_dir = export_dir
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def generar_ticket(self, cliente: Cliente, deuda: Deuda) -> Path:
        """
        Genera un ticket PDF para el cliente dado.
        Devuelve la ruta absoluta del archivo generado.
        """
        # Calcular dinámicamente el alto en mm usando calcular_pagos_aplicados
        alto_estimado = 80 + (len(deuda.items) * 4)

        if deuda.abonos:
            alto_estimado += 7 + (len(deuda.abonos) * 3.5)

        # Añadir 3mm extra por cada ítem con pago parcial (imprime una línea extra)
        pagos = calcular_pagos_aplicados(deuda)
        for item in deuda.items:
            p = pagos.get(item.id, 0.0)
            if 0 < p < item.subtotal:
                alto_estimado += 3

        pdf = TicketPDF(self.config, alto_estimado)
        pdf.header_negocio()
        pdf.datos_cliente(
            cliente,
            fecha=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        pdf.tabla_items(deuda)
        pdf.resumen_financiero(deuda)
        pdf.pie()

        # Omitido: FPDF no permite cambiar tamaño de página dinámicamente post-add_page en muchas versiones
        # pdf.set_page_size((PAGE_WIDTH, pdf.get_y() + 5))

        nombre_archivo = f"ticket_{cliente.nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        ruta = self.export_dir / nombre_archivo
        pdf.output(str(ruta))
        return ruta
