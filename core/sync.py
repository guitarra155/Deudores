import asyncio
import flet as ft
from views.helpers import snack

def iniciar_vigilancia_de_red(page: ft.Page, repo, clientes_view, deudas_view):
    """Vigila cada 12 segundos si los JSONs compartidos en red han sido modificados por otro host."""
    async def _vigilar():
        intervalo_segundos = 12
        while True:
            await asyncio.sleep(intervalo_segundos)
            try:
                hubo_cambio = False

                # 1. Sincronizar Clientes/Deudas
                if repo.sincronizar_desde_disco_si_otro_guardo():
                    deudas_view.refrescar_datos_desde_red()
                    if deudas_view._cliente is None:
                        clientes_view._cliente_activo = None
                    clientes_view._refresh_lista()
                    hubo_cambio = True

                # 2. Sincronizar Faltantes
                if repo.sincronizar_faltantes_si_otro_guardo():
                    hubo_cambio = True

                # 3. Sincronizar Notas
                if repo.sincronizar_notas_si_otro_guardo():
                    hubo_cambio = True

                # 4. Sincronizar Tareas
                if repo.sincronizar_tareas_si_otro_guardo():
                    hubo_cambio = True

                if hubo_cambio:
                    snack(page, "Datos sincronizados con éxito desde la red", ft.Colors.TEAL_700)
            except Exception:
                pass

    asyncio.create_task(_vigilar())
