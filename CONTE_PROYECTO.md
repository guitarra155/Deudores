# Contexto Técnico del Proyecto (CONTE_PROYECTO.md)

Este documento sirve como referencia rápida para cualquier desarrollador o agente de IA que trabaje en el sistema DeudorPro.

## 1. Stack Tecnológico
- **UI**: Flet (Flutter para Python).
- **Backend**: Python 3.12+
- **PDF**: fpdf2
- **Excel**: openpyxl
- **Sistema**: Windows (Win32 API vía ctypes para eventos de teclado).

## 2. Puntos Clave del Código
- **main.py**: Orquestador. Inicializa la página y asigna el handler global de teclado.
- **core/keyboard.py**: Gestiona TODOS los atajos. Usa un bucle de auto-repetición para navegación fluida.
- **database/repositorio.py**: Centraliza el acceso al disco. Implementa la lógica de guardado y carga de `clientes` y `faltantes`.
- **views/**: Contiene las vistas. `deudas_view.py` es el coordinador principal de la pantalla de deudas.
- **utils/catalogo.py**: Gestiona el catálogo de productos (3500+ ítems) con caché JSON para carga instantánea.

## 3. Desafíos Resueltos
1. **Latencia de Flet**: Se resolvió usando Win32 hooks para el teclado y minimizando reconstrucciones de widgets.
2. **Sincronización en Red**: Se logró mediante vigilancia de archivos (UNC paths) sin necesidad de una base de datos SQL compleja.
3. **Distribución**: Configurado para empaquetarse en carpeta modular para PCs con pocos recursos.

## 4. Estado Actual (v2.1 Alpha)
El proyecto ha sido optimizado con una **arquitectura de Portal (Page Overlay)** para el autocompletado, eliminando problemas de clipping. Se ha integrado el **pre-procesamiento de precios unitarios** desde Excel, permitiendo una entrada de datos sincronizada y automática que reduce errores humanos y tiempos de registro.
