# %% [markdown]
# # 30 — Índice de acceso E2SFCA (fase F3 de `PLAN_ACCESO.md`)
#
# Cada celda de 100 m donde vive gente recibe un valor de acceso: personal público de primer
# nivel por cada 1,000 personas sin seguro a su alcance, tomando en cuenta distancia y
# saturación. Las clínicas no se califican: son la oferta.
#
# **Método (E2SFCA, Luo y Qi 2009):**
#
# 1. Para cada unidad j: R_j = capacidad_j / Σ_i demanda_i · w(d_ij).
# 2. Para cada celda i: A_i = Σ_j R_j · w(d_ij).
#
# w es el decaimiento gaussiano dentro de la cuenca d0:
# w(d) = (e^{-½(d/d0)²} − e^{-½}) / (1 − e^{-½}). Vale 1 en d = 0 y 0 en d = d0.
#
# CDMX y EDOMEX se calculan juntos, porque la gente cruza el límite estatal.
#
# ## Criterios fijados antes de correr
#
# - **Principal:** primer nivel público (6211, sector público), capacidad = personal ocupado
#   (punto medio del rango de DENUE), demanda = `PSINDER` y cuenca de 1,667 m (30 min a pie
#   con rodeo 1.35), con decaimiento gaussiano.
# - **Promedio metropolitano:** capacidad total entre demanda total de las dos entidades.
# - **Acceso bajo:** A < 0.5 × promedio metropolitano. *Sin acceso:* ninguna unidad dentro
#   de la cuenca.
# - **Sensibilidades:**
#   - cuenca de 833 m;
#   - decaimiento por escalones (1, 0.68 y 0.22 en tercios de la cuenca);
#   - capacidad = 1 por unidad;
#   - capacidad con tope de 75;
#   - sin seguridad social;
#   - con hospitales;
#   - demanda = población total;
#   - acceso bajo = el 20% de la población con peor acceso.
#
#   Para cada una se reportan las personas con acceso bajo y su coincidencia con el
#   análisis principal, medida como la parte de las personas de acceso bajo principal que
#   siguen siendo de acceso bajo.
# - **Comparación con la distancia simple:** se cruza acceso bajo con "lejos" (unidad más
#   cercana a > 833 m). Quien tiene acceso bajo estando cerca tiene un problema de
#   **saturación**; quien lo tiene estando lejos, de **distancia**.

# %%
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from scipy.spatial import cKDTree

from lib import acceso, config, viz_eval as ve

ve.aplicar()
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
REGIONES = ["CDMX", "EDOMEX"]
CUENCA = 2 * acceso.RADIO_15  # 1,667 m


peso, e2sfca = acceso.peso, acceso.e2sfca  # definidos en lib/acceso.py


# %% [markdown]
# ## Demanda y oferta

# %%
partes = []
for r in REGIONES:
    xy, psin = acceso.demanda(r, "PSINDER")
    _, pob = acceso.demanda(r, "POBTOT")
    partes.append(pd.DataFrame({"x": xy[:, 0], "y": xy[:, 1], "psin": psin, "pob": pob, "region": r}))
celdas = pd.concat(partes, ignore_index=True)
XY = celdas[["x", "y"]].to_numpy()
PSIN = celdas["psin"].to_numpy()
REG = celdas["region"].to_numpy()
print(celdas.groupby("region")[["psin", "pob"]].sum().round())


def correr(nivel="primer", abierta=False, capacidad="personal", demanda="psin", d0=CUENCA, tipo="gauss"):
    o = acceso.oferta(nivel, abierta, capacidad)
    dem = celdas[demanda].to_numpy()
    A, R, alcanza = e2sfca(XY, dem, o[["x", "y"]].to_numpy(), o["cap"].to_numpy(), d0, tipo)
    prom = o["cap"].sum() / dem.sum() * 1000
    return {"A": A, "R": R, "alcanza": alcanza, "prom": prom, "oferta": o, "dem": dem}


base = correr()
A, prom = base["A"], base["prom"]
bajo = A < 0.5 * prom
d_min = cKDTree(base["oferta"][["x", "y"]].to_numpy()).query(XY)[0]
lejos = d_min > acceso.RADIO_15
print(f"promedio metropolitano: {prom:.2f} personal por 1,000 sin seguro")

# %% [markdown]
# ## Resultados principales

# %%
res = {"promedio_metropolitano_por_1000": prom, "cuenca_m": CUENCA, "unidades": len(base["oferta"])}
for r in REGIONES + ["Total"]:
    m = np.ones(len(A), bool) if r == "Total" else REG == r
    tot = PSIN[m].sum()

    def pct(mask):
        return {"personas": float(PSIN[m & mask].sum()), "pct": float(PSIN[m & mask].sum() / tot * 100)}

    o = base["oferta"] if r == "Total" else base["oferta"][base["oferta"]["region"] == r]
    acceso_medio = float((A[m] * PSIN[m]).sum() / tot)
    res[r] = {
        "psin": float(tot), "unidades": len(o), "capacidad": float(o["cap"].sum()),
        "razon_cruda_por_1000": float(o["cap"].sum() / tot * 1000),
        "acceso_medio_ponderado": acceso_medio,
        "acceso_medio_sobre_promedio": acceso_medio / prom,
        "acceso_bajo": pct(bajo), "sin_acceso": pct(~base["alcanza"]),
        "bajo_y_cerca": pct(bajo & ~lejos), "bajo_y_lejos_distancia": pct(bajo & lejos),
        "no_bajo_pero_lejos": pct(~bajo & lejos),
        "percentiles_A_por_persona": {q: float(np.interp(q / 100, np.cumsum(PSIN[m][np.argsort(A[m])]) / tot, np.sort(A[m])))
                                      for q in [10, 25, 50, 75, 90]},
    }
R_unidad = base["R"]
o = base["oferta"].assign(R=R_unidad)
res["razon_unidades_por_1000"] = {r: o[o["region"] == r]["R"].describe(percentiles=[.1, .5, .9]).round(2).to_dict() for r in REGIONES}
print(json.dumps(res, indent=1, ensure_ascii=False))

# %% [markdown]
# ## Sensibilidades

# %%
SENS = {
    "Cuenca 833 m": dict(d0=acceso.RADIO_15),
    "Decaimiento por escalones": dict(tipo="escalon"),
    "Capacidad = 1 por unidad": dict(capacidad="unidad"),
    "Capacidad con tope de 75": dict(capacidad="personal_tope"),
    "Sin seguridad social": dict(abierta=True),
    "Con hospitales": dict(nivel="todo"),
    "Demanda = población total": dict(demanda="pob"),
}
sens = {}
for nombre, kw in SENS.items():
    s = correr(**kw)
    b = s["A"] < 0.5 * s["prom"]
    fila = {}
    for r in REGIONES:
        m = REG == r
        fila[r] = {"pct_bajo": float(PSIN[m & b].sum() / PSIN[m].sum() * 100),
                   "retiene_bajo_principal": float(PSIN[m & b & bajo].sum() / PSIN[m & bajo].sum() * 100)}
    sens[nombre] = fila
# Acceso bajo como el 20% de la población con peor acceso, en toda la zona
orden = np.argsort(A)
corte = np.sort(A)[np.searchsorted(np.cumsum(PSIN[orden]) / PSIN.sum(), 0.2)]
b20 = A <= corte
sens["Acceso bajo = 20% peor"] = {r: {"pct_bajo": float(PSIN[(REG == r) & b20].sum() / PSIN[REG == r].sum() * 100),
                                      "retiene_bajo_principal": float(PSIN[(REG == r) & b20 & bajo].sum() / PSIN[(REG == r) & bajo].sum() * 100)}
                                  for r in REGIONES}
sens["Acceso bajo = 20% peor"]["corte_sobre_promedio"] = float(corte / prom)
res["sensibilidad"] = sens
print(json.dumps(sens, indent=1, ensure_ascii=False))

(SALIDA / "acceso_e2sfca.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
celdas.assign(acceso=A, acceso_rel=A / prom, bajo=bajo, d_min=d_min, lejos=lejos).to_parquet(
    config.INTERMEDIOS_DIR / "acceso_e2sfca_celdas.parquet")

# %% [markdown]
# ## Figura 1: mapa de acceso relativo al promedio metropolitano

# %%
cortes = [0, 0.25, 0.5, 1, 2, np.inf]
colores = ["#b8431a", "#eb9a74", "#d9d8d3", "#8fb6e6", "#2a5fa8"]
etiquetas = ["< 0.25× (muy bajo)", "0.25–0.5× (bajo)", "0.5–1×", "1–2×", "> 2×"]
cmap, norma = ListedColormap(colores), BoundaryNorm(cortes[:-1] + [1e9], len(colores))
fig, axes = plt.subplots(1, 2, figsize=(15, 8), gridspec_kw={"width_ratios": [1, 1.25]})
rel = A / prom
for ax, r in zip(axes, REGIONES):
    m = (REG == r) & (PSIN > 0)
    ax.scatter(XY[m, 0], XY[m, 1], c=rel[m], cmap=cmap, norm=norma, s=0.35, lw=0, rasterized=True)
    of = base["oferta"][base["oferta"]["region"] == r]
    ax.scatter(of["x"], of["y"], s=3, c=ve.TEXTO, lw=0)
    t = res[r]
    ax.set_title(f"{r}\n{t['acceso_bajo']['pct']:.0f}% de las personas sin seguro con acceso bajo "
                 f"({t['acceso_bajo']['personas'] / 1e6:.2f} millones)", fontsize=10.5)
    ax.set_aspect("equal")
    ax.set_axis_off()
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
leyenda = [Patch(color=c, label=l) for c, l in zip(colores, etiquetas)]
leyenda.append(Line2D([], [], ls="", marker=".", c=ve.TEXTO, label="Unidad pública de primer nivel"))
fig.legend(handles=leyenda, loc="lower center", ncol=6, fontsize=9.5, bbox_to_anchor=(0.5, -0.01),
           title="Acceso respecto al promedio metropolitano", title_fontsize=9.5)
ve.titulo(fig, "Acceso a la atención pública de primer nivel",
          f"E2SFCA: personal público de primer nivel por cada 1,000 personas sin seguro a su alcance "
          f"(cuenca de 30 min a pie). Promedio metropolitano: {prom:.1f}.")
fig.subplots_adjust(top=0.84)
ve.guardar(fig, FIG / "acceso_e2sfca_mapa.png")

# %% [markdown]
# ## Figura 2: por qué el acceso es bajo, distancia o saturación

# %%
fig, ax = plt.subplots(figsize=(10, 3.6))
cats = [("bajo_y_lejos_distancia", "Bajo por distancia (unidad a > 833 m)", "#b8431a"),
        ("bajo_y_cerca", "Bajo con una unidad a ≤ 833 m", "#eb9a74"),
        ("no_bajo_pero_lejos", "Lejos pero no bajo", "#8fb6e6")]
for k, r in enumerate(REGIONES):
    izq = 0
    for clave, etiqueta, color in cats:
        v = res[r][clave]["pct"]
        ax.barh(k, v, left=izq, color=color, height=0.55, ec=ve.FONDO, lw=2, label=etiqueta if k == 0 else None)
        if v > 3:
            ax.text(izq + v / 2, k, f"{v:.0f}%", ha="center", va="center", fontsize=9.5, color=ve.TEXTO)
        izq += v
ax.set_yticks(range(len(REGIONES)), REGIONES)
ax.invert_yaxis()
ax.set_xlabel("% de las personas sin seguro de la entidad")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.55), ncol=3, fontsize=9)
ve.titulo(fig, "Acceso bajo: ¿lejos de toda unidad o con una cerca?")
fig.subplots_adjust(top=0.85)
ve.guardar(fig, FIG / "acceso_e2sfca_causas.png")
