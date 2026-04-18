# Convenciones de Desarrollo - DeudorPro

Este documento define los estándares técnicos para mantener la calidad y el rendimiento en PCs de bajos recursos.

## 1. Arquitectura Modular
- **Core**: Lógica de integración técnica (Keyboard Hook, WhatsApp, Sincronización).
- **Database**: Capa de persistencia atómica (Repositorio).
- **Models**: Definiciones de datos (`dataclass`).
- **Utils**: Servicios auxiliares (PDF, Cálculo, Catálogo).
- **Views**: UI en Flet, dividida en componentes (`tabla`, `dialogs`).

## 2. Rendimiento (Low-Resources)
- **Foco Asíncrono**: Siempre usar `page.run_task(control.focus)` para evitar bloqueos.
- **Evitar Re-builds**: No recrear controles en bucles de navegación (flechas ↑↓); actualizar solo propiedades (`bgcolor`, `value`).
- **Navegación Turbo**: Usar `ctypes` para lectura directa del hardware en listas largas.
- **Portal Overlay**: Usar `page.overlay` para menús flotantes o autocompletados. Esto garantiza que ningún contenedor padre recorte el elemento.
- **Botones de Acción**: Tamaño uniforme (`width=165`, `height=44`) con colores premium y etiqueta de atajo de teclado visible (ej: `[Ctrl+S]`).

## 3. Persistencia y Red
- **Atomicidad**: Los archivos (`clientes.json`, `faltantes.json`) se sobrescriben solo tras una escritura confirmada.
- **Multi-usuario**: Vigilancia por tiempo de modificación (`st_mtime`) para detectar cambios externos automáticamente.
- **Respaldos**: Cada guardado dispara una copia asíncrona hacia la carpeta de backup.
