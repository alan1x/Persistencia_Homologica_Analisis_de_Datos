"""Índice de marginación compuesto desde variables censales (INEGI Censo 2020).

Sin necesidad de datos externos de CONAPO — construido desde huecos_censal.

Dimensiones (pesos calibrados para salud pública):
  0.35 × pct_sin_salud   — acceso a servicios de salud
  0.25 × escolaridad_def — déficit educativo (12 - graproes)
  0.25 × pob_mayor_pct   — vulnerabilidad etaria (% 60+)
  0.15 × densidad_psin   — presión sobre infraestructura (sin-seguro / km²)
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


PESOS = {
    "pct_sin_salud":   0.35,
    "escolaridad_def": 0.25,
    "pob_mayor_pct":   0.25,
    "densidad_psin":   0.15,
}


def calcular_indice(df_censal: pd.DataFrame) -> pd.Series:
    """Calcula el índice de marginación (0–1) para cada fila de huecos_censal.

    Parámetros
    ----------
    df_censal : DataFrame con columnas pct_sin_salud_prom, graproes_prom,
                pob_60_mas, pob_afectada, pob_sin_salud, radio_m

    Devuelve
    --------
    Serie 'indice_marg' (float 0–1), alineada con el índice de df_censal.
    """
    df = df_censal.copy()

    # 1. Acceso a salud (ya en %)
    df["pct_sin_salud"] = df["pct_sin_salud_prom"].clip(0, 100)

    # 2. Déficit educativo (12 años = secundaria completa)
    df["escolaridad_def"] = (12.0 - df["graproes_prom"]).clip(0, None)

    # 3. Vulnerabilidad etaria
    df["pob_mayor_pct"] = (
        df["pob_60_mas"] / df["pob_afectada"].replace(0, np.nan)
    ).fillna(0) * 100

    # 4. Densidad de demanda (personas sin seguro por km² del hueco)
    area_km2 = np.pi * (df["radio_m"] / 1000) ** 2
    df["densidad_psin"] = (
        df["pob_sin_salud"] / area_km2.replace(0, np.nan)
    ).fillna(0)

    dims = list(PESOS.keys())
    scaler = MinMaxScaler()
    norm = pd.DataFrame(
        scaler.fit_transform(df[dims]),
        columns=[f"{d}_norm" for d in dims],
        index=df.index,
    )

    indice = sum(PESOS[d] * norm[f"{d}_norm"] for d in dims)
    return indice.rename("indice_marg")


def agregar_a_score(df_score: pd.DataFrame,
                    df_censal: pd.DataFrame,
                    w_acceso: float = 0.25,
                    w_psinder: float = 0.25,
                    w_pers: float = 0.25,
                    w_marg: float = 0.25) -> pd.DataFrame:
    """Agrega la dimensión de marginación a huecos_score y recomputa el score.

    El score combinado usa 4 ejes con los pesos especificados (suman 1.0).
    El ranking de urgencia se recalibra sobre el nuevo score_norm.

    Devuelve una copia de df_score con columnas adicionales:
        indice_marg, rank_marg, score (recomputado), score_norm, urgencia
    """
    assert abs(w_acceso + w_psinder + w_pers + w_marg - 1.0) < 1e-6, \
        "Los pesos deben sumar 1.0"

    df = df_score.merge(
        df_censal[["hueco_id", "pct_sin_salud_prom", "graproes_prom",
                   "pob_60_mas", "pob_afectada", "radio_m"]],
        on="hueco_id", how="left",
    )

    # Índice de marginación
    df["indice_marg"] = calcular_indice(df).values

    # Rank de marginación (1 = más marginalizado)
    df["rank_marg"] = df["indice_marg"].rank(ascending=False,
                                              method="min").fillna(0).astype(int)

    # Normalizar ranks a 0–1 (1 = peor, 0 = mejor)
    n = len(df)
    df["rank_tiempo_n"]  = 1 - (df["rank_tiempo"]  - 1) / max(n - 1, 1)
    df["rank_psinder_n"] = 1 - (df["rank_psinder"] - 1) / max(n - 1, 1)
    df["rank_pers_n"]    = 1 - (df["rank_pers"]    - 1) / max(n - 1, 1)
    df["rank_marg_n"]    = 1 - (df["rank_marg"]    - 1) / max(n - 1, 1)

    # Score combinado 4 ejes
    df["score"] = (w_acceso  * df["rank_tiempo_n"]
                 + w_psinder * df["rank_psinder_n"]
                 + w_pers    * df["rank_pers_n"]
                 + w_marg    * df["rank_marg_n"])

    # Normalizar score a 0–1
    s_min, s_max = df["score"].min(), df["score"].max()
    df["score_norm"] = ((df["score"] - s_min) / (s_max - s_min)
                        if s_max > s_min else pd.Series(0.5, index=df.index))

    # Re-calibrar urgencia (percentiles 75/50/25 del score_norm)
    p75 = df["score_norm"].quantile(0.75)
    p50 = df["score_norm"].quantile(0.50)
    p25 = df["score_norm"].quantile(0.25)

    def urgencia(s):
        if s >= p75: return "Crítico"
        if s >= p50: return "Alto"
        if s >= p25: return "Moderado"
        return "Bajo"

    df["urgencia"] = df["score_norm"].apply(urgencia)

    # Limpiar columnas temporales del merge
    df = df.drop(columns=["pct_sin_salud_prom", "graproes_prom",
                           "pob_60_mas", "pob_afectada", "radio_m"],
                 errors="ignore")
    return df
