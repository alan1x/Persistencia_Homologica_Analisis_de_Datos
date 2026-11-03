# %% [markdown]
# # 25 — Otros sectores: ¿hueco de salud o hueco de ciudad?
#
# Dos preguntas:
#
# 1. **¿Otros sectores tienen la misma forma?** Se compara salud con educación, comercio
#    minorista, alimentos y servicios financieros. El conteo crudo depende del número
#    de puntos: con menos puntos hay más huecos. Por eso también se compara con el mismo
#    número de establecimientos en cada sector (rarefacción).
#
# 2. **¿El hueco de salud es específico?** Un disco sin clínicas puede ser un barrio lleno
#    de comercios sin consultorios, o un parque sin nada. Se cuentan los establecimientos
#    de otros sectores dentro del disco vacío de cada hueco prioritario y se compara con
#    la densidad típica de su región.

# %%
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.spatial import cKDTree

from lib import config, data, huecos, viz_eval as ve

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
SALIDA.mkdir(exist_ok=True)
REGIONES = ["CDMX", "EDOMEX"]
SECTORES = {"62": "Salud", "61": "Educación", "46": "Comercio minorista",
            "72": "Alimentos y alojamiento", "52": "Servicios financieros"}
N_REP = 20
COLOR = {"CDMX": ve.AZUL, "EDOMEX": ve.NARANJA}


def preparar_sector(crudo, region, sector):
    """Mismo orden que `data.preparar`: filtrar primero y limpiar después."""
    return data.proyectar(data.limpiar(data.filtrar_sector(crudo, sector), region))


def rarefaccion(P, n, semilla):
    rng = np.random.default_rng(semilla)
    Q = P[rng.choice(len(P), n, replace=False)]
    h = huecos.extraer_huecos(huecos.complejo(Q), Q, 200)
    return len(h), float(h["pers"].sum())


# %%
filas, discos = [], {}
for r in REGIONES:
    crudo = data.cargar_region(r)
    crudo = crudo[crudo["codigo_act"].notna()].copy()
    por_sector = {s: preparar_sector(crudo, r, s)[["x", "y"]].to_numpy() for s in SECTORES}
    assert len(por_sector["62"]) == len(pd.read_parquet(INT / f"salud_{r}.parquet"))
    print(r, {s: len(v) for s, v in por_sector.items()}, flush=True)
    n_comun = min(len(v) for v in por_sector.values())
    salud = huecos.extraer_huecos(huecos.complejo(por_sector["62"]), por_sector["62"], 200)

    for s, nombre in SECTORES.items():
        P = por_sector[s]
        h = huecos.extraer_huecos(huecos.complejo(P), P, 200)
        rar = Parallel(n_jobs=6)(delayed(rarefaccion)(P, n_comun, 100 * i) for i in range(N_REP))
        # ¿Los huecos de salud también son huecos de este sector?
        d, _ = cKDTree(h[["cx", "cy"]].values).query(salud[["cx", "cy"]].values)
        filas.append({
            "region": r, "sector": s, "nombre": nombre, "n": len(P), "huecos": len(h),
            "pers_total_km": h["pers"].sum() / 1000, "pers_max_m": h["pers"].max(),
            "n_comun": n_comun, "huecos_rar": np.mean([x[0] for x in rar]),
            "huecos_rar_min": np.min([x[0] for x in rar]), "huecos_rar_max": np.max([x[0] for x in rar]),
            "pers_rar_km": np.mean([x[1] for x in rar]) / 1000,
            "huecos_salud_compartidos_pct": float((d < np.maximum(100.0, salud["death"].values / 2)).mean() * 100),
        })
        print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in filas[-1].items()}, flush=True)

    # Densidad de actividad no sanitaria dentro de los discos prioritarios
    pr = pd.read_parquet(INT / f"huecos_prioritarios_{r}.parquet")
    prio = salud[np.isin(salud["pers"].round(3), pr["pers_m"].round(3))].copy()
    prio = prio.merge(pr.assign(k=pr["pers_m"].round(3))[["k", "pob_sin_salud", "pob_afectada"]],
                      left_on=prio["pers"].round(3), right_on="k")
    otros = data.proyectar(data.limpiar(crudo[~crudo["codigo_act"].str.startswith("62")], r))[["x", "y"]].to_numpy()
    arbol = cKDTree(otros)
    conteo = np.array([len(i) for i in arbol.query_ball_point(prio[["cx", "cy"]].values, prio["death"].values)])
    area = np.pi * (prio["death"].values / 1000) ** 2
    prio["otros_km2"] = conteo / area
    prio["otros_n"] = conteo
    # Densidad típica: la de discos de 500 m alrededor de establecimientos de salud
    rng = np.random.default_rng(1)
    muestra = por_sector["62"][rng.choice(len(por_sector["62"]), 2000, replace=False)]
    tipica = np.median([len(i) for i in arbol.query_ball_point(muestra, 500)]) / (np.pi * 0.25)
    prio["ratio"] = prio["otros_km2"] / tipica
    prio["tipo"] = np.where(prio["ratio"] >= 0.25, "Con actividad", "Casi sin actividad")
    discos[r] = {"tabla": prio, "tipica": float(tipica)}
    prio.drop(columns="par").to_csv(SALIDA / f"sectores_discos_{r}.csv", index=False)

df = pd.DataFrame(filas)
df.to_csv(SALIDA / "sectores_resumen.csv", index=False)
res = {r: {"densidad_tipica_km2": discos[r]["tipica"],
           "prioritarios": len(discos[r]["tabla"]),
           "con_actividad": int((discos[r]["tabla"]["tipo"] == "Con actividad").sum()),
           "mediana_ratio": float(discos[r]["tabla"]["ratio"].median()),
           "psin_con_actividad": int(discos[r]["tabla"].loc[discos[r]["tabla"]["tipo"] == "Con actividad", "pob_sin_salud"].sum()),
           "psin_total": int(discos[r]["tabla"]["pob_sin_salud"].sum())} for r in REGIONES}
(SALIDA / "sectores_discos.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
print(json.dumps(res, indent=2))

# %% [markdown]
# ## Figura 1: huecos con el mismo número de establecimientos

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharex=False)
for ax, r in zip(axes, REGIONES):
    s = df[df.region == r].sort_values("huecos_rar")
    col = [ve.AZUL if x == "62" else ve.GRIS for x in s.sector]
    ax.barh(s.nombre, s.huecos_rar, color=col, height=0.62)
    for y, (v, n) in enumerate(zip(s.huecos_rar, s.n)):
        ax.text(v, y, f"  {v:.0f}", va="center", color=ve.TEXTO, fontsize=10)
    ax.set_title(f"{r}: submuestra de {s.n_comun.iloc[0]:,} por sector")
    ax.set_xlabel("Huecos con persistencia ≥ 200 m")
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.1)
ve.titulo(fig, "Con el mismo número de puntos, ¿salud se reparte distinto?",
          f"Promedio de {N_REP} submuestras al azar. Salud va resaltada.")
fig.tight_layout(rect=(0, 0, 1, 0.91))
ve.guardar(fig, config.FIGURAS_DIR / "sectores_huecos_mismo_n.png")

# %% [markdown]
# ## Figura 2: ¿hay ciudad dentro de los huecos de salud?

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
for ax, r in zip(axes, REGIONES):
    t = discos[r]["tabla"]
    bins = np.logspace(-3, 1, 25)
    ax.hist(np.clip(t["ratio"], 1e-3, 10), bins=bins, color=COLOR[r], edgecolor=ve.FONDO, lw=1)
    ax.set_xscale("log")
    ax.axvline(1, color=ve.TEXTO_2, lw=1.2, ls="--")
    ax.axvline(0.25, color=ve.GRIS, lw=1.2, ls=":")
    ax.set_xticks([0.001, 0.01, 0.1, 0.25, 1, 10])
    ax.set_xticklabels(["≤0.001", "0.01", "0.1", "0.25", "1", "10"])
    ax.minorticks_off()
    n = (t["tipo"] == "Con actividad").sum()
    ax.set_title(f"{r}: {n} de {len(t)} huecos con actividad ≥ 25% de lo típico")
    ax.set_xlabel("Densidad de otros negocios en el disco ÷ densidad típica")
    ax.set_ylabel("Huecos prioritarios")
    ax.grid(axis="x", visible=False)
ve.titulo(fig, "¿Son barrios sin clínica o simplemente zonas vacías?",
          "Línea punteada: densidad típica alrededor de un establecimiento de salud.")
fig.tight_layout(rect=(0, 0, 1, 0.91))
ve.guardar(fig, config.FIGURAS_DIR / "sectores_actividad_en_huecos.png")
