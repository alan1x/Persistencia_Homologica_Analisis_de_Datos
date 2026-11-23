# %% [markdown]
# # 39 — Figuras de F3 por calle y tablas para entregar
#
# El notebook 30 hizo los mapas de acceso en línea recta. Desde el 2026-11-19 la versión
# principal es por calle (30 min = 2,250 m de red peatonal), así que aquí se rehacen con ese
# acceso y se arman las tablas que puede leer alguien sin correr el código.
#
# **Figuras** (`outputs/figuras/`):
# - `acceso_calle_mapa.png`: acceso relativo al promedio metropolitano.
# - `acceso_calle_causas.png`: acceso bajo por distancia (ninguna unidad a ≤ 1,125 m de calle)
#   o con una unidad cerca (saturación).
# - `acceso_marginacion_calle_mapa.png`: prioridad = acceso bajo y marginación Alta o Muy alta.
#
# **Tablas** (`outputs/entregables/`, coordenadas en grados WGS84):
# - `islas_calle.csv`: islas estables por calle (sin "resto de región"), con su gente en el
#   territorio propio, su p en el nulo espacial y los sitios de F5 que caen en su cuenca.
# - `sitios_propuestos_calle.csv`: los 20 sitios de F5 (brecha, K = 20) con su aporte marginal.
# - `acceso_municipio_calle.csv`: resumen por municipio o alcaldía.
# - `zonas_sospechosas_osm.csv`: grupos de celdas con acceso 0 por calle pero con una unidad a
#   ≤ 1,667 m en recta (posibles huecos de la red de OSM; notebook 35).

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
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree

from lib import acceso, config, red_peatonal as rp, topo_rejilla as tr, viz_eval as ve
from lib.f4 import UMBRAL_B

ve.aplicar()
INT = config.INTERMEDIOS_DIR
FIG = config.FIGURAS_DIR
ENT = config.OUTPUTS_DIR / "entregables"
ENT.mkdir(exist_ok=True)
C30, R15, K = 30 * 4500 / 60, 15 * 4500 / 60, 20
REGIONES = ["CDMX", "EDOMEX"]
GEO = Transformer.from_crs(config.CRS_METROS, config.CRS_GEO, always_xy=True)

c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
N = len(c)
F = pd.read_parquet(INT / "acceso_calle.parquet")["acceso_rel_calle"].to_numpy()
BAJO = F < UMBRAL_B
ALTA = c["alta_marg"].to_numpy(bool)
PRIOR = BAJO & ALTA
PESO = PSIN * np.where(ALTA, 2.0, 1.0)
REG = c["region"].to_numpy()
MUN = c["CVEGEO"].str[:5].to_numpy()
imu = acceso.marginacion_conapo()
NOM_MUN = imu.assign(m=imu["CVEGEO"].str[:5]).groupby("m")["NOM_MUN"].first()
o = acceso.oferta()
PROM1000 = o["cap"].sum() / PSIN.sum() * 1000

pu = pd.read_parquet(INT / "pares_red_unidades.parquet")
D_CALLE = np.full(N, np.inf)
np.minimum.at(D_CALLE, pu["i"].to_numpy(), pu["d"].to_numpy(float))
CERCA = D_CALLE <= R15


def lonlat(x, y):
    lon, lat = GEO.transform(np.asarray(x), np.asarray(y))
    return np.round(lon, 6), np.round(lat, 6)


def mun_de(xy):
    m = MUN[cKDTree(XY).query(xy)[1]]
    return m, pd.Series(m).map(NOM_MUN).to_numpy()


# %% [markdown]
# ## Islas estables y sitios de F5

# %%
isl = pd.read_parquet(INT / "islas_acceso_calle.parquet")
est = isl[isl["estable"] & (isl["tipo"] != "resto de región")].reset_index(drop=True)
ASIG = np.load(INT / "asig_cuencas_calle.npy")
assert (INT / "asig_cuencas_calle.huella").read_text() == rp.huella(F, est["celda"].to_numpy())
en = ASIG >= 0
cuenta = lambda w: np.bincount(ASIG[en], w[en], len(est))
est["psin"], est["psin_bajo"], est["psin_prioridad"] = cuenta(PSIN), cuenta(PSIN * BAJO), cuenta(PSIN * PRIOR)
est["celdas"] = np.bincount(ASIG[en], minlength=len(est))
nulo = pd.read_parquet(INT / "islas_nulo_calle.parquet")[["celda", "p_isla"]]
est = est.merge(nulo, on="celda", how="left")

# Sitios de F5 (brecha, K = 20) y su aporte marginal con el modelo por calle del notebook 32
s32 = pd.read_csv(config.OUTPUTS_DIR / "auditoria" / "optimizacion_sitios_calle.csv")
sit = s32[(s32["objetivo"] == "brecha") & (s32["orden"] <= K)].sort_values("orden").reset_index(drop=True)
pc = pd.read_parquet(INT / "pares_red_candidatos_calle.parquet")
CXY = pc.drop_duplicates("j").sort_values("j")[["cx", "cy"]].to_numpy()
kd = cKDTree(CXY)
dist0, JS = kd.query(sit[["x", "y"]].to_numpy())
assert (dist0 < 1).all()
Ic, Jc, Dc = pc["i"].to_numpy(), pc["j"].to_numpy(), pc["d"].to_numpy(float)
W = acceso.peso(Dc, C30)
M = len(CXY)
DEN = np.bincount(Jc, weights=PSIN[Ic] * W, minlength=M)
CAP = float(o["cap"].median())
DELTA = CAP / np.maximum(DEN[Jc], 1e-9) * W / (o["cap"].sum() / PSIN.sum())
f = F.copy()
filas = []
for k, j in enumerate(JS):
    m = Jc == j
    antes_b = (PESO * np.maximum(0, UMBRAL_B - f)).sum()
    antes_bajo = PSIN[f < UMBRAL_B].sum()
    np.add.at(f, Ic[m], DELTA[m])
    cel = Ic[m & (Dc <= R15)]
    filas.append({"reduccion_brecha": antes_b - (PESO * np.maximum(0, UMBRAL_B - f)).sum(),
                  "personas_salen_de_acceso_bajo": antes_bajo - PSIN[f < UMBRAL_B].sum(),
                  "psin_a_15_min": PSIN[cel].sum(),
                  "psin_sin_unidad_a_15_min_hoy": PSIN[cel[~CERCA[cel]]].sum()})
sit = sit.join(pd.DataFrame(filas))
cel_sit = cKDTree(XY).query(sit[["x", "y"]].to_numpy())[1]
sit["isla"], sit["region"] = ASIG[cel_sit], REG[cel_sit]
sit["cve_mun"], sit["municipio"] = mun_de(sit[["x", "y"]].to_numpy())
sit["lon"], sit["lat"] = lonlat(sit["x"], sit["y"])
sitios_por_isla = sit[sit["isla"] >= 0].groupby("isla")["orden"].apply(lambda s: ",".join(map(str, s)))
est["sitios_f5"] = est.index.map(sitios_por_isla).fillna("")

est["lon"], est["lat"] = lonlat(est["x"], est["y"])
est["cve_mun"] = MUN[est["celda"]]
islas_csv = (est.assign(id_isla=est.index, nace_sin_acceso=est["b"] == 0)
             .sort_values("psin_bajo", ascending=False)
             [["id_isla", "region", "cve_mun", "NOM_MUN", "lon", "lat", "tipo", "nace_sin_acceso", "b", "d", "pers",
               "frecuencia", "celdas", "psin", "psin_bajo", "psin_prioridad", "p_isla", "sitios_f5"]]
             .rename(columns={"NOM_MUN": "municipio", "b": "nacimiento_f", "d": "muerte_f",
                              "pers": "persistencia", "frecuencia": "estabilidad", "p_isla": "p_nulo_espacial"}))
islas_csv.round(4).to_csv(ENT / "islas_calle.csv", index=False, encoding="utf-8-sig")
(sit[["orden", "region", "cve_mun", "municipio", "lon", "lat", "x", "y", "isla",
      "reduccion_brecha", "personas_salen_de_acceso_bajo", "psin_a_15_min", "psin_sin_unidad_a_15_min_hoy"]]
 .round({c: 1 for c in ["reduccion_brecha", "personas_salen_de_acceso_bajo", "psin_a_15_min",
                    "psin_sin_unidad_a_15_min_hoy"]})
 .to_csv(ENT / "sitios_propuestos_calle.csv", index=False, encoding="utf-8-sig"))
print(islas_csv.head(10).to_string())
print(sit.drop(columns=["objetivo"]).round(0).to_string())

# %% [markdown]
# ## Resumen por municipio y zonas sospechosas

# %%
def mediana_pond(v, w):
    o_ = np.argsort(v)
    return float(np.interp(0.5, np.cumsum(w[o_]) / max(w.sum(), 1e-9), v[o_]))


o["cve_mun"], _ = mun_de(o[["x", "y"]].to_numpy())
filas = []
for m in np.unique(MUN):
    s = MUN == m
    filas.append({"cve_mun": m, "municipio": NOM_MUN.get(m, ""), "region": REG[s][0],
                  "psin": PSIN[s].sum(), "psin_bajo": PSIN[s & BAJO].sum(),
                  "pct_bajo": PSIN[s & BAJO].sum() / max(PSIN[s].sum(), 1e-9) * 100,
                  "psin_sin_unidad_a_30_min": PSIN[s & ~np.isfinite(D_CALLE)].sum(),
                  "psin_prioridad": PSIN[s & PRIOR].sum(),
                  "acceso_mediano": mediana_pond(F[s], PSIN[s]),
                  "unidades": int((o["cve_mun"] == m).sum()),
                  "personal_por_1000_sin_seguro": o.loc[o["cve_mun"] == m, "cap"].sum() / max(PSIN[s].sum(), 1e-9) * 1000,
                  "islas_estables": int((est["cve_mun"] == m).sum()),
                  "sitios_f5": int((sit["cve_mun"] == m).sum())})
mun = pd.DataFrame(filas).sort_values("psin_bajo", ascending=False)
mun.round(3).to_csv(ENT / "acceso_municipio_calle.csv", index=False, encoding="utf-8-sig")
print(mun.head(15).round(2).to_string())

z = pd.read_parquet(INT / "ceros_calle.parquet")
SOS = z["clase"].isin(["rodeo moderado", "rodeo > 2", "sin calle a 300 m", "red desconectada"]).to_numpy()
rej = tr.Rejilla(c["x"], c["y"], acceso.PASO)
mk = np.zeros(rej.ras.shape, bool)
mk[rej.ras >= 0] = SOS[rej.ras[rej.ras >= 0]]
g, _ = ndimage.label(mk, structure=np.ones((3, 3)))
grupo = np.zeros(N, int)
grupo[rej.activa] = g[rej.fr[rej.activa], rej.cr[rej.activa]]
gz = (pd.DataFrame({"grupo": grupo, "psin": PSIN, "x": XY[:, 0], "y": XY[:, 1], "clase": z["clase"],
                    "d_recta": z["d_recta"], "mun": MUN})[grupo > 0]
      .groupby("grupo").agg(psin=("psin", "sum"), celdas=("psin", "size"), x=("x", "mean"), y=("y", "mean"),
                            clase_principal=("clase", lambda s: s.mode().iloc[0]),
                            d_recta_mediana=("d_recta", "median"), cve_mun=("mun", "first"))
      .sort_values("psin", ascending=False).reset_index(drop=True))
gz["municipio"] = gz["cve_mun"].map(NOM_MUN)
gz["lon"], gz["lat"] = lonlat(gz["x"], gz["y"])
gz.insert(0, "id_zona", np.arange(len(gz)))
gz[["id_zona", "cve_mun", "municipio", "lon", "lat", "celdas", "psin", "clase_principal", "d_recta_mediana"]].round({"psin": 1, "d_recta_mediana": 0}) \
    .to_csv(ENT / "zonas_sospechosas_osm.csv", index=False, encoding="utf-8-sig")
print(f"zonas sospechosas: {len(gz)}, personas: {gz['psin'].sum():,.0f}")

res = {r: {"psin": float(PSIN[REG == r].sum()), "psin_bajo": float(PSIN[(REG == r) & BAJO].sum()),
           "pct_bajo": float(PSIN[(REG == r) & BAJO].sum() / PSIN[REG == r].sum() * 100),
           "bajo_lejos_pct": float(PSIN[(REG == r) & BAJO & ~CERCA].sum() / PSIN[REG == r].sum() * 100),
           "bajo_cerca_pct": float(PSIN[(REG == r) & BAJO & CERCA].sum() / PSIN[REG == r].sum() * 100),
           "lejos_no_bajo_pct": float(PSIN[(REG == r) & ~BAJO & ~CERCA].sum() / PSIN[REG == r].sum() * 100),
           "prioridad": float(PSIN[(REG == r) & PRIOR].sum()),
           "prioridad_pct": float(PSIN[(REG == r) & PRIOR].sum() / PSIN[REG == r].sum() * 100)} for r in REGIONES}
res["tablas"] = {"islas": len(islas_csv), "sitios": len(sit), "municipios": len(mun), "zonas_sospechosas": len(gz)}
(config.OUTPUTS_DIR / "auditoria" / "entregables_calle.json").write_text(json.dumps(res, indent=2, ensure_ascii=False),
                                                                         encoding="utf-8")
print(json.dumps(res, indent=1, ensure_ascii=False))

# %% [markdown]
# ## Figuras

# %%
cortes = [0, 0.25, 0.5, 1, 2, np.inf]
colores = ["#b8431a", "#eb9a74", "#d9d8d3", "#8fb6e6", "#2a5fa8"]
etiquetas = ["< 0.25× (muy bajo)", "0.25–0.5× (bajo)", "0.5–1×", "1–2×", "> 2×"]
cmap, norma = ListedColormap(colores), BoundaryNorm(cortes[:-1] + [1e9], len(colores))
fig, axes = plt.subplots(1, 2, figsize=(15, 8), gridspec_kw={"width_ratios": [1, 1.25]})
for ax, r in zip(axes, REGIONES):
    m = (REG == r) & (PSIN > 0)
    ax.scatter(XY[m, 0], XY[m, 1], c=F[m], cmap=cmap, norm=norma, s=0.35, lw=0, rasterized=True)
    of = o[o["region"] == r]
    ax.scatter(of["x"], of["y"], s=3, c=ve.TEXTO, lw=0)
    t = res[r]
    ax.set_title(f"{r}\n{t['pct_bajo']:.0f}% de las personas sin seguro con acceso bajo "
                 f"({t['psin_bajo'] / 1e6:.2f} millones)", fontsize=10.5)
    ax.set_aspect("equal")
    ax.set_axis_off()
leyenda = [Patch(color=col, label=l) for col, l in zip(colores, etiquetas)]
leyenda.append(Line2D([], [], ls="", marker=".", c=ve.TEXTO, label="Unidad pública de primer nivel"))
fig.legend(handles=leyenda, loc="lower center", ncol=6, fontsize=9.5, bbox_to_anchor=(0.5, -0.01),
           title="Acceso respecto al promedio metropolitano", title_fontsize=9.5)
ve.titulo(fig, "Acceso a la atención pública de primer nivel (por calle)",
          f"E2SFCA: personal público de primer nivel por cada 1,000 personas sin seguro a su alcance "
          f"(30 min a pie por la red de calles). Promedio metropolitano: {PROM1000:.1f}.")
fig.subplots_adjust(top=0.81)
ve.guardar(fig, FIG / "acceso_calle_mapa.png")

fig, ax = plt.subplots(figsize=(10, 3.6))
cats = [("bajo_lejos_pct", "Bajo por distancia (ninguna unidad a ≤ 1,125 m de calle)", "#b8431a"),
        ("bajo_cerca_pct", "Bajo con una unidad a ≤ 1,125 m", "#eb9a74"),
        ("lejos_no_bajo_pct", "Lejos pero no bajo", "#8fb6e6")]
for k, r in enumerate(REGIONES):
    izq = 0
    for clave, etiqueta, color in cats:
        v = res[r][clave]
        ax.barh(k, v, left=izq, color=color, height=0.55, ec=ve.FONDO, lw=2, label=etiqueta if k == 0 else None)
        if v > 3:
            ax.text(izq + v / 2, k, f"{v:.0f}%", ha="center", va="center", fontsize=9.5, color=ve.TEXTO)
        izq += v
ax.set_yticks(range(len(REGIONES)), REGIONES)
ax.invert_yaxis()
ax.set_xlabel("% de las personas sin seguro de la entidad")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.55), ncol=2, fontsize=9)
ve.titulo(fig, "Acceso bajo por calle: ¿lejos de toda unidad o con una cerca?")
fig.subplots_adjust(top=0.85, bottom=0.3)
ve.guardar(fig, FIG / "acceso_calle_causas.png")

COL = {"Prioridad: acceso bajo y marginación alta": "#b8431a", "Acceso bajo, marginación no alta": "#eb9a74",
       "Acceso no bajo, marginación alta": "#8fb6e6", "Ninguno": "#dcdbd6"}
clase = np.select([PRIOR, BAJO, ALTA], list(COL)[:3], "Ninguno")
fig, axes = plt.subplots(1, 2, figsize=(15, 8), gridspec_kw={"width_ratios": [1, 1.25]})
for ax, r in zip(axes, REGIONES):
    s = (REG == r) & (PSIN > 0)
    for k, col in COL.items():
        q = s & (clase == k)
        ax.scatter(XY[q, 0], XY[q, 1], s=0.35, c=col, lw=0, rasterized=True, zorder=2 if k.startswith("Prior") else 1)
    sr = sit[sit["region"] == r]
    ax.scatter(sr["x"], sr["y"], s=60, marker="o", facecolors="none", edgecolors=ve.TEXTO, lw=1.3, zorder=3)
    ax.set_title(f"{r}\nPrioridad: {res[r]['prioridad'] / 1000:,.0f} mil personas sin seguro "
                 f"({res[r]['prioridad_pct']:.0f}%)", fontsize=10.5)
    ax.set_aspect("equal")
    ax.set_axis_off()
fig.legend(handles=[Patch(color=v, label=k) for k, v in COL.items()]
           + [Line2D([], [], ls="", marker="o", mfc="none", mec=ve.TEXTO, label="Sitio propuesto (F5, K = 20)")],
           loc="lower center", ncol=5, fontsize=9.5, bbox_to_anchor=(0.5, -0.01))
ve.titulo(fig, "Dónde se juntan acceso bajo y marginación alta (por calle)",
          "Acceso bajo: E2SFCA por calle < 0.5 × promedio metropolitano. Marginación alta: grado Alto o Muy alto, "
          "CONAPO 2020 por AGEB.")
fig.subplots_adjust(top=0.81)
ve.guardar(fig, FIG / "acceso_marginacion_calle_mapa.png")
