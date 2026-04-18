# Estructura y Manual Técnico - DeudorPro (Modular Engine v2.0)

Este documento detalla la arquitectura y el funcionamiento interno de DeudorPro, una solución de alto rendimiento para la gestión de deudas en entornos locales y de red.

## 1. Arquitectura de Módulos

El proyecto sigue una estructura desacoplada para facilitar el mantenimiento:

- **/core**: Motores de bajo nivel.
    - `keyboard.py`: Puente Win32 para navegación fluida y atajos globales.
    - `sync.py`: Vigilante de red para actualización automática multi-usuario.
    - `whatsapp.py`: Motor de comunicación y plantillas.
- **/database**: Capa de datos.
    - `repositorio.py`: Gestor central de persistencia atómica para Clientes y Faltantes.

## 🧮 Lógica de Negocio y Cálculos

### Distribución de Abonos
El sistema procesa los pagos siguiendo reglas estrictas de prioridad:
1.  **Abonos Selectivos**: Se aplican directamente a los IDs de productos elegidos por el usuario.
2.  **Abonos Generales**: Se distribuyen automáticamente en orden **cronológico descendente** (lo más antiguo primero), basándose en el campo `fecha` de cada producto.
3.  **Cálculo Neto**: En abonos selectivos, el sistema calcula automáticamente el saldo pendiente de cada ítem (Subtotal - Abonos previos) para evitar cobros duplicados.

### Gestión de Deuda
La deuda total se calcula dinámicamente restando la suma de todos los abonos a la suma de los subtotales de los productos.

- **/models**: Estructuras de datos.
    - `cliente.py`, `deuda.py`.
- **/views**: Interfaz de usuario (Flet).
    - `clientes_view.py`: Gestión de listas masivas con navegación optimizada.
    - `deudas_view.py`: Panel principal de transacciones con autocompletado inteligente.
- **/utils**: Servicios de soporte.
    - `pdf_generator.py`, `backup_manager.py`, `catalogo.py`.

## 2. Funcionalidades de Ingeniería

### Navegación Turbo (Win32 Bridge)
Utiliza `user32.GetAsyncKeyState` para permitir un desplazamiento fluido (auto-repeat) por las listas de clientes y productos, superando las limitaciones de latencia de los eventos estándar de Flet.

### Sincronización en Red
Implementa una vigilancia por `st_mtime`. Cuando una instancia de DeudorPro detecta que el archivo JSON en red ha sido modificado por otra PC, refresca los datos localmente y notifica al usuario.

## 🛠️ Persistencia y Seguridad de Datos

### JSON Handler (Escritura Atómica)
Para garantizar que los archivos de datos no se corrompan ante fallos del sistema o cortes de energía, se utiliza una técnica de **Escritura Atómica**:
1.  Los datos se escriben primero en un archivo temporal (`.tmp`).
2.  Se verifica la integridad de la escritura.
3.  Se utiliza `os.replace` para realizar un intercambio instantáneo con el archivo original.

### Backup Manager
El sistema realiza copias de seguridad cada 30 minutos y en cada evento de guardado.
- **Validación de Integridad**: Antes de realizar un respaldo, el sistema verifica que el archivo origen sea un JSON válido. Si el archivo está corrupto, el sistema **no** sobrescribe el respaldo para proteger la última copia buena conocida.

## 🚀 Desarrollo y Versiones

### Entorno de Ejecución
- **Python**: 3.10 o superior recomendado.
- **Flet**: v0.21.0 o superior.
- **Librerías Extra**: `fpdf2`, `openpyxl`.

### Notas sobre Flet (Troubleshooting)
Para evitar errores de ejecución en modo asíncrono (`async main`):
- **Método Update**: Aunque la aplicación corra con `asyncio`, los controles individuales (como `TextField` o `DatePicker`) utilizan el método `.update()` síncrono. **NO** utilizar `await control.update()` ni `update_async()` a menos que la versión de Flet instalada lo soporte específicamente vía extensión, de lo contrario lanzará un `TypeError` o `AttributeError`.
- **Overlay**: Siempre verificar que los diálogos (`AlertDialog`) y selectores (`DatePicker`) estén agregados a `page.overlay` antes de llamar a su apertura.

---

## 🔝 Mejoras Premium Aplicadas
El sistema ha sido elevado a un estándar profesional mediante:
- **Micro-animaciones**: Uso de `ink=True` en filas para feedback visual.
- **Empty States**: Control de visibilidad en listas vacías.
- **Brand Identity**: Barra superior con acentos en colores Material 3 (Indigo/Amber).

### Autocompletado de Precios
El motor de catálogo (`catalogo.py`) extrae automáticamente el `VALOR_UNITARIO` de archivos Excel. Al seleccionar un producto en la interfaz, se rellena instantáneamente el campo de precio y se recalcula el subtotal en tiempo real.

## 3. Atajos de Teclado (Power User)

- **Ctrl + K**: Enfocar buscador de clientes (asíncrono).
- **Ctrl + S**: Liquidar (Saldar) cuenta completa inmediatamente.
- **Ctrl + A**: Registrar nuevo abono (Abonar).
- **Ctrl + P**: Generar y abrir PDF del recibo actual.
- **Ctrl + W**: Enviar estado de cuenta por WhatsApp.
- **Ctrl + N**: Nuevo cliente.
- **Ctrl + L**: Lista de productos faltantes (Compras).
- **Escape**: Limpiar búsqueda / Volver al inicio / Cerrar diálogos.

## 4. Mantenimiento y Compilación

Para compilar una nueva versión:
1. Instalar dependencias: `pip install -r requirements.txt`
2. Ejecutar PyInstaller: `pyinstaller DeudorPro.spec`
3. El resultado estará en `dist/DeudorPro/`.
