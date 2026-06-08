"""Clasificación topológica de huecos H₁ en arquetipos interpretativos.

En el diagrama de persistencia, la posición de cada hueco (birth, persistencia)
no es arbitraria — codifica el tipo de problema de cobertura que representa.
Usamos dos dimensiones para clasificar:

  birth      = escala a la que aparece el hueco
               → qué tan separados están los servicios en esa zona
  persistencia = cuánto dura el hueco antes de "llenarse"
               → qué tan grave es la falta de cobertura

Esas dos dimensiones producen 4 arquetipos topológicos naturales, más un
5° especial para casos extremos:

  ┌──────────────────────────────────────────────────────────┐
  │             birth BAJO          birth ALTO               │
  │  pers ALTA  Enclave urbano   │  Desierto estructural     │
  │             (más accionable) │  (zona rural sin cobertura│
  ├─────────────────────────────┼──────────────────────────-─┤
  │  pers BAJA  Micro-brecha    │  Vacío periférico          │
  │             (ruido urbano)  │  (transición urbano-rural) │
  └──────────────────────────────────────────────────────────┘

  Crítico: persistencia > umbral_critico (cualquier birth) — emergencia

Los umbrales se calculan sobre el conjunto de datos combinado para que
sean comparables entre regiones.
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Paleta de colores y descripciones por arquetipo
ARQUETIPOS = {
    "Micro-brecha":          {"color": "#74c476", "prioridad": 4,
                               "descripcion": "Brecha urbana menor. Densidad alta, hueco pequeño y local."},
    "Vacío periférico":      {"color": "#fd8d3c", "prioridad": 3,
                               "descripcion": "Zona de transición. Servicios espaciados, hueco pasa rápido."},
    "Enclave sin cobertura": {"color": "#d62728", "prioridad": 1,
                               "descripcion": "CRÍTICO: rodeado de servicios pero con vacío interno persistente."},
    "Desierto estructural":  {"color": "#7b2d8b", "prioridad": 2,
                               "descripcion": "Zona rural/periférica. Sin servicios en radio amplio."},
}


def clasificar_huecos(diag_h1, umbral_birth=None, umbral_pers=None,
                      umbral_critico=3000.0):
    """Clasifica los huecos H₁ de un diagrama en arquetipos topológicos.

    Parámetros
    ----------
    diag_h1        : array (n, 2) con (birth, death) en metros — huecos ya
                     filtrados por min_persistencia.
    umbral_birth   : float (m) — separa birth bajo/alto. Si None, usa mediana.
    umbral_pers    : float (m) — separa pers baja/alta. Si None, usa mediana.
    umbral_critico : float (m) — persistencia a partir de la cual es crítico.

    Devuelve DataFrame con columnas:
        birth_m, death_m, pers_m, arquetipo, prioridad, color
    """
    if len(diag_h1) == 0:
        return pd.DataFrame()

    birth = diag_h1[:, 0]
    pers  = diag_h1[:, 1] - diag_h1[:, 0]

    if umbral_birth is None:
        umbral_birth = float(np.median(birth))
    if umbral_pers is None:
        umbral_pers = float(np.median(pers))

    arquetipos = []
    for b, p in zip(birth, pers):
        if p >= umbral_critico:
            arq = "Desierto estructural"
        elif b < umbral_birth and p >= umbral_pers:
            arq = "Enclave sin cobertura"
        elif b >= umbral_birth and p >= umbral_pers:
            arq = "Desierto estructural"
        elif b < umbral_birth and p < umbral_pers:
            arq = "Micro-brecha"
        else:
            arq = "Vacío periférico"
        arquetipos.append(arq)

    df = pd.DataFrame({
        "birth_m": birth,
        "pers_m":  pers,
        "death_m": diag_h1[:, 1],
        "arquetipo": arquetipos,
    })
    df["prioridad"] = df["arquetipo"].map(lambda a: ARQUETIPOS[a]["prioridad"])
    df["color"]     = df["arquetipo"].map(lambda a: ARQUETIPOS[a]["color"])
    return df


def umbrales_conjuntos(diags_h1_dict):
    """Calcula umbrales de birth y persistencia sobre el conjunto de todas las
    regiones, para que la clasificación sea comparable entre estados.

    Devuelve (umbral_birth, umbral_pers) en metros.
    """
    births, perss = [], []
    for d in diags_h1_dict.values():
        if len(d) == 0:
            continue
        births.append(d[:, 0])
        perss.append(d[:, 1] - d[:, 0])
    if not births:
        return 500.0, 500.0
    all_births = np.concatenate(births)
    all_perss  = np.concatenate(perss)
    return float(np.median(all_births)), float(np.median(all_perss))


def resumen_arquetipos(df_clasificado, region):
    """Tabla resumen: cuántos huecos por arquetipo y su persistencia media."""
    rows = []
    for arq in ARQUETIPOS:
        sub = df_clasificado[df_clasificado["arquetipo"] == arq]
        rows.append({
            "region":    region,
            "arquetipo": arq,
            "n":         len(sub),
            "pers_media_km": round(sub["pers_m"].mean() / 1000, 2) if len(sub) else 0.0,
            "pers_max_km":   round(sub["pers_m"].max() / 1000, 2) if len(sub) else 0.0,
            "prioridad":     ARQUETIPOS[arq]["prioridad"],
        })
    return pd.DataFrame(rows).sort_values("prioridad")
