"""
utils/calculos.py
Lógica de negocio pura (sin UI): totales, saldos y abonos.
"""
from models.deuda import Deuda, Abono


def calcular_total(deuda: Deuda) -> float:
    """Suma los subtotales de todos los ítems."""
    return round(sum(item.subtotal for item in deuda.items), 2)


def calcular_total_abonado(deuda: Deuda) -> float:
    """Suma todos los abonos realizados."""
    return round(sum(a.monto for a in deuda.abonos), 2)


def calcular_saldo_pendiente(deuda: Deuda) -> float:
    """Deuda total menos lo ya abonado."""
    return round(calcular_total(deuda) - calcular_total_abonado(deuda), 2)


def calcular_pagos_aplicados(deuda: Deuda) -> dict:
    """
    Retorna {item_id: monto_pagado} respetando:
      1. Abonos selectivos (items_ids no vacío) → se aplican directamente a sus ítems.
      2. Abonos generales (items_ids vacío) → se aplican de arriba a abajo
         sobre los ítems que aún tienen saldo pendiente.
    """
    # Inicializar pagos en 0
    pagos = {item.id: 0.0 for item in deuda.items}

    # Paso 1: aplicar abonos selectivos
    for abono in deuda.abonos:
        if not abono.items_ids:
            continue
        # Distribuir el monto del abono entre los ítems vinculados
        items_vinculados = [it for it in deuda.items if it.id in abono.items_ids]
        restante = abono.monto
        for item in items_vinculados:
            if restante <= 0:
                break
            ya_pagado = pagos[item.id]
            puede_pagar = max(0.0, item.subtotal - ya_pagado)
            aplicar = min(puede_pagar, restante)
            pagos[item.id] = round(ya_pagado + aplicar, 2)
            restante = round(restante - aplicar, 2)

    # Paso 2: aplicar abonos generales de arriba a abajo (por fecha)
    for abono in deuda.abonos:
        if abono.items_ids:
            continue
        restante = abono.monto
        
        # IMPORTANTE: Ordenar ítems por fecha para que el abono cubra lo más antiguo primero
        items_ordenados = sorted(deuda.items, key=lambda x: x.fecha)
        
        for item in items_ordenados:
            if restante <= 0:
                break
            ya_pagado = pagos[item.id]
            puede_pagar = max(0.0, item.subtotal - ya_pagado)
            aplicar = min(puede_pagar, restante)
            pagos[item.id] = round(ya_pagado + aplicar, 2)
            restante = round(restante - aplicar, 2)

    return pagos


def aplicar_abono(deuda: Deuda, monto: float, nota: str = "", fecha: str = "") -> Abono:
    """
    Crea un Abono y lo agrega a la deuda.
    Devuelve el objeto Abono creado.
    """
    if monto <= 0:
        raise ValueError("El monto del abono debe ser mayor a cero.")
    kw = {"monto": round(monto, 2), "nota": nota}
    if fecha:
        kw["fecha"] = fecha
    abono = Abono(**kw)
    deuda.abonos.append(abono)
    return abono
