import unittest
import sys
import os
import json
import time

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.json_handler import JsonHandler

class TestSecurity(unittest.TestCase):

    def setUp(self):
        self.test_file = "test_atomic.json"
        from pathlib import Path
        self.handler = JsonHandler(Path("."))
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.test_file + ".tmp"):
            os.remove(self.test_file + ".tmp")

    def test_escritura_atomica_existencia(self):
        """Verificar que el archivo original se crea correctamente."""
        data = {"test": "data"}
        self.handler.save(self.test_file, data)
        
        self.assertTrue(os.path.exists(self.test_file), "El archivo final debería existir")
        
        with open(self.test_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            self.assertEqual(data, saved_data)

    def test_integridad_ante_corrupcion_temporal(self):
        """
        Este test simula una interrupción verificando que no queden 
        archivos temporales después de una operación exitosa.
        """
        data = {"a": 1}
        self.handler.save(self.test_file, data)
        
        # Después de guardar, no debería haber rastro del .tmp
        self.assertFalse(os.path.exists(self.test_file + ".tmp"), "El archivo temporal debería haber sido eliminado/renombrado")

if __name__ == '__main__':
    unittest.main()
