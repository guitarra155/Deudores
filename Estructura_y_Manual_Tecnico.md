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

### Portal de Autocompletado (Overlay Architecture)
El autocompletado de productos utiliza un "Portal" (`page.overlay`) que flota sobre toda la aplicación. Implementa una lógica de **Flip dinámico** que alterna la posición (arriba/abajo) y ajusta su altura automáticamente según el espacio vertical disponible en la ventana.

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
