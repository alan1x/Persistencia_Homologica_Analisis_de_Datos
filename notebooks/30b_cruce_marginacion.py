# %% [markdown]
# # 30b — Cruce de acceso con marginación (CONAPO) y referencia por zona
#
# **Marginación:** Índice de Marginación Urbana 2020 de CONAPO por AGEB
# (`Datos/CONAPO/IMU_2020.xls`). Cada celda de 100 m toma el grado de su AGEB. El índice
# incluye el % sin derechohabiencia (PSDSS), que también está en la demanda, así que como
# sensibilidad se arma un índice con los otros diez indicadores.
#
# ## Criterios fijados antes de correr
#
# - **Prioridad:** acceso bajo (notebook 30) y grado de marginación Alto o Muy alto.
# - **Sensibilidad sin PSDSS:** z-score promedio de los diez indicadores restantes, con
#   signo tal que mayor = más marginado. "Alta marginación" = el 20% de las personas sin
#   seguro con mayor valor. Se reporta cuánto coincide la prioridad con la principal.
# - **Referencia del acceso bajo:** la principal es el promedio metropolitano. Como
#   sensibilidad se usa el promedio de cada zona: CDMX, EDOMEX poniente (Toluca, lon < −99.3)
#   y resto de EDOMEX.

# %%
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer

from lib import acceso, config, viz_eval as ve

ve.aplicar()
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
REGIONES = ["CDMX", "EDOMEX"]
GRADOS = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]
INDIC = ["P6A14NAE", "SBASC", "OVSDE", "OVSEE", "OVSAE", "OVPT", "OVSREF", "OVSINT", "OVSCEL", "OVHAC"]

c = pd.read_parquet(config.INTERMEDIOS_DIR / "acceso_e2sfca_celdas.parquet")
claves = []
for r in REGIONES:
    xy, _, cve = acceso.demanda(r, "PSINDER", con_ageb=True)
    claves.append(cve)
    assert np.allclose(xy, c.loc[c["region"] == r, ["x", "y"]].to_numpy())
c["CVEGEO"] = np.concatenate(claves)

imu = acceso.marginacion_conapo()
# Índice sin PSDSS: mayor = más marginado. Los indicadores ya son % de carencia.
z = (imu[INDIC] - imu[INDIC].mean()) / imu[INDIC].std()
imu["sin_psdss"] = z.mean(axis=1)
c = c.merge(imu[["CVEGEO", "GM_2020", "IM_2020", "sin_psdss"]], on="CVEGEO", how="left")
# Las AGEB sin grado de CONAPO quedan como "no alta" en alta_marg (peso 1 en F5). Se reporta
# cuánta gente es y cuánta tiene acceso bajo, para que se vea que no cambia nada material.
res = {"psin_sin_dato_conapo": {r: float(c.loc[(c["region"] == r) & c["GM_2020"].isna(), "psin"].sum()) for r in REGIONES},
       "psin_bajo_sin_dato_conapo": {r: float(c.loc[(c["region"] == r) & c["GM_2020"].isna() & c["bajo"], "psin"].sum())
                                     for r in REGIONES}}
print(res)

# %% [markdown]
# ## Cruce principal

# %%
c["grado"] = pd.Categorical(c["GM_2020"], GRADOS, ordered=True)
c["alta_marg"] = c["grado"].isin(["Alto", "Muy alto"])
c["prioridad"] = c["bajo"] & c["alta_marg"]
orden = np.argsort(-c["sin_psdss"].fillna(-np.inf).to_numpy())
acum = np.cumsum(c["psin"].to_numpy()[orden]) / c["psin"].sum()
corte = c["sin_psdss"].to_numpy()[orden][np.searchsorted(acum, 0.2)]
c["alta_marg_sin_psdss"] = c["sin_psdss"] >= corte
c["prioridad_sin_psdss"] = c["bajo"] & c["alta_marg_sin_psdss"]

for r in REGIONES:
    g = c[c["region"] == r]
    tabla = g.pivot_table(index="grado", columns="bajo", values="psin", aggfunc="sum", observed=False).fillna(0)
    tabla.columns = ["acceso_no_bajo", "acceso_bajo"]
    tabla["pct_bajo"] = tabla["acceso_bajo"] / tabla.sum(axis=1) * 100
    tot = g["psin"].sum()
    res[r] = {
        "tabla_grado": tabla.round(1).to_dict(orient="index"),
        "prioridad": {"personas": float(g.loc[g["prioridad"], "psin"].sum()),
                      "pct": float(g.loc[g["prioridad"], "psin"].sum() / tot * 100),
                      "pct_del_acceso_bajo": float(g.loc[g["prioridad"], "psin"].sum() / g.loc[g["bajo"], "psin"].sum() * 100)},
        "prioridad_sin_psdss": {"personas": float(g.loc[g["prioridad_sin_psdss"], "psin"].sum()),
                                "coincide_con_principal": float(g.loc[g["prioridad"] & g["prioridad_sin_psdss"], "psin"].sum()
                                                                / max(g.loc[g["prioridad"], "psin"].sum(), 1) * 100)},
        "acceso_rel_mediano_por_grado": g.groupby("grado", observed=False).apply(
            lambda t: float(np.interp(0.5, np.cumsum(t["psin"].values[np.argsort(t["acceso_rel"].values)]) / max(t["psin"].sum(), 1),
                                      np.sort(t["acceso_rel"].values))) if len(t) else None).to_dict(),
    }
    print(r, json.dumps(res[r], indent=1, ensure_ascii=False))

# %% [markdown]
# ## Referencia por zona

# %%
o = acceso.oferta()
tr = Transformer.from_crs(config.CRS_METROS, config.CRS_GEO, always_xy=True)


def zona(df):
    lon, _ = tr.transform(df["x"].values, df["y"].values)
    return np.where(df["region"] == "CDMX", "CDMX", np.where(lon < -99.3, "EDOMEX poniente (Toluca)", "EDOMEX resto"))


c["zona"], o["zona"] = zona(c), zona(o)
prom = o["cap"].sum() / c["psin"].sum() * 1000
ref = {}
for zn, g in c.groupby("zona"):
    rz = o.loc[o["zona"] == zn, "cap"].sum() / g["psin"].sum() * 1000
    b_z = g["acceso"] < 0.5 * rz
    ref[zn] = {"psin": float(g["psin"].sum()), "razon_por_1000": float(rz),
               "pct_bajo_ref_metro": float(g.loc[g["bajo"], "psin"].sum() / g["psin"].sum() * 100),
               "pct_bajo_ref_zona": float(g.loc[b_z, "psin"].sum() / g["psin"].sum() * 100)}
res["referencia_por_zona"] = ref
res["promedio_metropolitano"] = float(prom)
print(json.dumps(ref, indent=1, ensure_ascii=False))
(SALIDA / "acceso_marginacion.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
c.to_parquet(config.INTERMEDIOS_DIR / "acceso_e2sfca_celdas.parquet")

# %% [markdown]
# ## Figura: mapa de prioridad

# %%
COL = {"Prioridad: acceso bajo y marginación alta": "#b8431a", "Acceso bajo, marginación no alta": "#eb9a74",
       "Acceso no bajo, marginación alta": "#8fb6e6", "Ninguno": "#dcdbd6"}
c["clase"] = np.select([c["prioridad"], c["bajo"], c["alta_marg"]], list(COL)[:3], "Ninguno")
fig, axes = plt.subplots(1, 2, figsize=(15, 8), gridspec_kw={"width_ratios": [1, 1.25]})
for ax, r in zip(axes, REGIONES):
    g = c[(c["region"] == r) & (c["psin"] > 0)]
    for k, col in COL.items():
        t = g[g["clase"] == k]
        ax.scatter(t["x"], t["y"], s=0.35, c=col, lw=0, rasterized=True, zorder=2 if k.startswith("Prior") else 1)
    p = res[r]["prioridad"]
    ax.set_title(f"{r}\nPrioridad: {p['personas'] / 1000:,.0f} mil personas sin seguro ({p['pct']:.0f}%)", fontsize=10.5)
    ax.set_aspect("equal")
    ax.set_axis_off()
from matplotlib.patches import Patch
fig.legend(handles=[Patch(color=v, label=k) for k, v in COL.items()], loc="lower center", ncol=4, fontsize=9.5,
           bbox_to_anchor=(0.5, -0.01))
ve.titulo(fig, "Dónde se juntan acceso bajo y marginación alta",
          "Acceso bajo: E2SFCA < 0.5 × promedio metropolitano. Marginación alta: grado Alto o Muy alto, CONAPO 2020 por AGEB.")
fig.subplots_adjust(top=0.84)
ve.guardar(fig, FIG / "acceso_marginacion_mapa.png")
