# Resumen de Proyecto - DeudorPro (Versión 2.2.1 Modular)

**DeudorPro** es una aplicación de escritorio diseñada para la gestión eficiente de deudas, clientes y productos faltantes en pequeños negocios. Esta versión representa una evolución hacia una arquitectura modular de grado ingeniería, optimizada para rendimiento y trabajo en red.

## Características Principales

### 1. Gestión de Deudas y Clientes
- Registro atómico de clientes y deudas.
- **Abono Selectivo (v2.2)**: Posibilidad de pagar productos específicos marcando checkboxes, con sumario en tiempo real.
- Sistema de abonos con historial detallado y selector de fecha automático para pagos rápidos.
- Liquidación rápida de cuentas con un solo atajo (`Ctrl + S`).

### 2. Navegación de Alta Velocidad (Ultra-Responsive)
- Puente Win32 para navegación por teclado sin lag en listas de miles de clientes.
- **Autocompletado Circular**: Navegación infinita entre sugerencias y velocidad de repetición mejorada (0.20s).
- **Precios Automáticos**: Carga de `VALOR_UNITARIO` desde Excel y autorrelleno instantáneo al seleccionar productos.

### 3. Sincronización y Respaldo
- **Multi-usuario total**: Soporte para trabajar clientes, deudas, faltantes, notas y tareas en red (UNC).
- **Sincronización Automática**: Los cambios realizados en una PC se reflejan instantáneamente en las demás cada 12 segundos.
- **Respaldo Atómico**: Copias de seguridad automáticas en cada cambio y cada 30 minutos.

### 4. Organización del Local (Módulos Globales)
- **Notas (Ctrl+O)**: Listado dinámico para recordatorios rápidos con edición inline.
- **Tareas (Ctrl+T)**: Sistema de checklist con reordenamiento automático de prioridades.
- **Faltantes (Ctrl+L)**: Lista de compras sincronizada y ahora totalmente editable.

### 5. Exportación y Comunicación
- Generación de tickets PDF profesionales con ruta de guardado configurable desde la UI.
- Envío de estados de cuenta vía WhatsApp con un click (plantillas configurables).

---

## 🛠️ Instrucciones de Compilación (Build)
Para generar el ejecutable optimizado, use los siguientes comandos en la terminal desde la raíz del proyecto:

1. **Instalar dependencias necesarias**:
   ```powershell
   .\.venv\Scripts\python.exe -m pip install pyinstaller
   ```

2. **Compilar proyecto (Modo Modular)**:
   ```powershell
   .\.venv\Scripts\python.exe -m PyInstaller DeudorPro.spec --noconfirm
   ```

*El resultado se encuentra en: `dist/DeudorPro/DeudorPro.exe`*

---

## Estado Técnico (v2.2.1)
- **Lenguaje**: Python 3.
- **Framework UI**: Flet (Flutter) con Keyboard Hooking nativo.
- **Persistencia**: JSON Atómico con redundancia y sistema de vigilancia de red.
- **Arquitectura**: Modular orientada a servicios (MVC).
