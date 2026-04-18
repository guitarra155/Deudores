import os
import json
import sys

# Añadir el raíz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def inspect_all_data():
    data_dir = "data_storage"
    if not os.path.exists(data_dir):
        print(f"Error: No se encontró el directorio {data_dir}")
        return

    report = []
    
    # Escanear archivos json
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            path = os.path.join(data_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Validaciones básicas de estructura
                    if "clientes" in filename:
                        if not isinstance(data, dict) or "clientes" not in data:
                            report.append(f"[ERROR] {filename}: Debería ser un objeto con clave 'clientes'.")
                        else:
                            print(f"[OK] {filename}: Contiene {len(data['clientes'])} clientes y {len(data.get('deudas', {}))} deudas.")
                    
                    elif "deudas" in filename:
                        # Un archivo de deuda puede estar vacío o tener estructura de Deuda
                        if isinstance(data, dict):
                            items = data.get("items", [])
                            abonos = data.get("abonos", [])
                            if not isinstance(items, list) or not isinstance(abonos, list):
                                report.append(f"[ADVERTENCIA] {filename}: Estructura de items/abonos inusual.")
                                
                print(f"[OK] {filename}: Estructura JSON válida.")
            except Exception as e:
                report.append(f"[CRÍTICO] {filename}: No se pudo leer el archivo. Posible corrupción. Error: {str(e)}")

    if not report:
        print("\n>>> ¡Detección de integridad completada! No se encontraron errores en los datos.")
    else:
        print("\n>>> INFORME DE INCIDENCIAS:")
        for r in report:
            print(r)

if __name__ == "__main__":
    inspect_all_data()
