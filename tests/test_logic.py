import unittest
import sys
import os
from datetime import datetime

# Añadir el directorio raíz al path para importar los módulos del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.deuda import Deuda, DeudaItem, Abono
from utils.calculos import calcular_pagos_aplicados, calcular_saldo_pendiente

class TestLogic(unittest.TestCase):

    def setUp(self):
        # Crear una deuda base para las pruebas
        self.deuda = Deuda(cliente_id="test_client")
        self.items = [
            DeudaItem(id="old", nombre="Antiguo", precio=10.0, cantidad=1, fecha="2024-01-01", codigo_barras=""),
            DeudaItem(id="med", nombre="Medio",   precio=10.0, cantidad=1, fecha="2024-02-01", codigo_barras=""),
            DeudaItem(id="new", nombre="Nuevo",   precio=10.0, cantidad=1, fecha="2024-03-01", codigo_barras=""),
        ]
        self.deuda.items = self.items

    def test_prioridad_cronologica_fifo(self):
        """Verificar que un abono general cubra primero lo más antiguo."""
        # Abono de $15: debe pagar "Antiguo" ($10) y la mitad de "Medio" ($5)
        abono = Abono(monto=15.0, fecha="2024-04-01")
        self.deuda.abonos = [abono]
        
        pagos = calcular_pagos_aplicados(self.deuda)
        
        self.assertEqual(pagos.get("old"), 10.0, "El ítem más antiguo debería estar totalmente pago")
        self.assertEqual(pagos.get("med"), 5.0, "El ítem medio debería estar pagado a la mitad")
        self.assertEqual(pagos.get("new", 0), 0.0, "El ítem nuevo no debería tener abonos")

    def test_abono_selectivo_prioridad(self):
        """Verificar que un abono con IDs específicos se aplique solo a esos ítems."""
        # Abono selectivo de $10 solo para el "Nuevo"
        abono = Abono(monto=10.0, fecha="2024-04-01", items_ids=["new"])
        self.deuda.abonos = [abono]
        
        pagos = calcular_pagos_aplicados(self.deuda)
        
        self.assertEqual(pagos.get("new"), 10.0, "El ítem nuevo debería estar pago vía selectivo")
        self.assertEqual(pagos.get("old", 0), 0.0, "El ítem antiguo no debería recibir dinero del selectivo")

    def test_saldo_restante_despues_de_abonos(self):
        """Verificar que el saldo total de la deuda sea correcto."""
        self.deuda.abonos = [
            Abono(monto=5.0, fecha="2024-04-01"), # General
            Abono(monto=5.0, fecha="2024-04-02", items_ids=["new"]) # Selectivo
        ]
        # Total items: 30. Total abonos: 10. Saldo: 20.
        saldo = calcular_saldo_pendiente(self.deuda)
        self.assertEqual(saldo, 20.0)

if __name__ == '__main__':
    unittest.main()
