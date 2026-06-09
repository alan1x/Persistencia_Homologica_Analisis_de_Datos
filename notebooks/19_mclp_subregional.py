# %% [markdown]
# # 19 — MCLP Subregional para EDOMEX
#
# El análisis global de EDOMEX mostró que K=5 clínicas rinden solo ~18% de
# cobertura poblacional con curva casi lineal — señal de que la dispersión
# geográfica impide que una clínica en una zona cubra huecos de otra.
#
# Solución: dividir EDOMEX en 4 subregiones y asignar K=3 clínicas a cada una.
# Resultado: 12 clínicas totales con inversión geográficamente equitativa.
#
# Subregiones:
#   Norte    : lat > 19.7                       ( 7 huecos)
#   Poniente : lon < -99.3  AND lat ≤ 19.7      (21 huecos)
#   Oriente  : lon > -98.9  AND lat ≤ 19.7      ( 6 huecos)
#   ZMVM     : resto                             (38 huecos)

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib
matplotlib.use("Agg")
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import pulp
from scipy.spatial import cKDTree
from pyproj import Transformer

from lib import config

_TR = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

VEL_M_MIN  = (4.5 * 1000) / 60
DETOUR     = 1.35
TIEMPO_LIM = 15.0

# K=3 por subregión: presupuesto uniforme para que cada zona reciba la misma inversión
K_SUB = {
    "Norte":    3,
    "Poniente": 3,
    "Oriente":  3,
    "ZMVM":     3,
}
K_GLOBAL = 5   # referencia: qué daría el MCLP global con mismos candidatos

COLORES_SUB = {
    "Norte":    "#4393c3",
    "Poniente": "#d6604d",
    "Oriente":  "#1b9e77",
    "ZMVM":     "#7570b3",
}

# %% [markdown]
# ## 1. Cargar datos y definir subregiones

# %%
df_prio_all = pd.read_parquet(config.INTERMEDIOS_DIR / "huecos_prioritarios_EDOMEX.parquet")
x_h, y_h   = _TR.transform(df_prio_all["lon"].values, df_prio_all["lat"].values)
df_prio_all = df_prio_all.copy()
df_prio_all["x_utm"] = x_h
df_prio_all["y_utm"] = y_h

def asignar_subregion(row):
    if row["lat"] > 19.7:
        return "Norte"
    elif row["lon"] < -99.3:
        return "Poniente"
    elif row["lon"] > -98.9:
        return "Oriente"
    else:
        return "ZMVM"

df_prio_all["subregion"] = df_prio_all.apply(asignar_subregion, axis=1)

print("Distribución de huecos por subregión:")
for sr in ["Norte", "Poniente", "Oriente", "ZMVM"]:
    sub = df_prio_all[df_prio_all["subregion"] == sr]
    print(f"  {sr:10s}: {len(sub):3d} huecos  "
          f"pob_sin_salud={sub['pob_sin_salud'].sum():>8,.0f}  "
          f"pers_max={sub['pers_m'].max():.0f}m")

with open(str(config.INTERMEDIOS_DIR / "soluciones_mclp_red.pkl"), "rb") as f:
    pkl = pickle.load(f)
cands_all = [c for c in pkl["resultados_red"]["EDOMEX"] if c["tiempos"]]

# Asignar cada candidato a su subregión
def subregion_latlon(lat, lon):
    if lat > 19.7:             return "Norte"
    elif lon < -99.3:          return "Poniente"
    elif lon > -98.9:          return "Oriente"
    else:                      return "ZMVM"

for c in cands_all:
    c["subregion"] = subregion_latlon(c["lat_clinica"], c["lon_clinica"])

# %% [markdown]
# ## 2. MCLP local por subregión

# %%
soluciones_sub = {}
total_ps_global = df_prio_all["pob_sin_salud"].sum()

for sr in ["Norte", "Poniente", "Oriente", "ZMVM"]:
    K_local  = K_SUB[sr]
    df_sub   = df_prio_all[df_prio_all["subregion"] == sr].copy().reset_index(drop=True)
    # Candidatos que pertenecen a esta subregión
    cands_sr = [c for c in cands_all if c["subregion"] == sr]

    if len(df_sub) == 0 or len(cands_sr) == 0:
        print(f"  [{sr}] Sin datos — omitiendo")
        continue

    n       = len(df_sub)
    ids_sub = df_sub["hueco_id"].astype(int).tolist()
    demand  = df_sub.set_index("hueco_id")["pob_sin_salud"].to_dict()
    total_ps_sr = df_sub["pob_sin_salud"].sum()

    I = list(range(n))
    J = list(range(len(cands_sr)))
    C = {(i, j): 1 if cands_sr[j]["tiempos"].get(ids_sub[i], 9999) <= TIEMPO_LIM else 0
         for i in I for j in J}

    prob = pulp.LpProblem(f"mclp_sr_{sr}", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x{j}", cat="Binary") for j in J]
    y = [pulp.LpVariable(f"y{i}", cat="Binary") for i in I]

    prob += pulp.lpSum(demand.get(ids_sub[i], 0) * y[i] for i in I)
    prob += pulp.lpSum(x) == min(K_local, len(cands_sr))
    for i in I:
        prob += y[i] <= pulp.lpSum(C[i, j] * x[j] for j in J)

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    sel_j  = [j for j in J if x[j].value() > 0.5]
    cub_i  = [i for i in I if y[i].value() > 0.5]
    psin_c = sum(demand.get(ids_sub[i], 0) for i in cub_i)

    soluciones_sub[sr] = {
        "df_sub":     df_sub,
        "cands_sr":   cands_sr,
        "sel_j":      sel_j,
        "cub_i":      cub_i,
        "psin_cub":   psin_c,
        "pct_local":  psin_c / total_ps_sr * 100 if total_ps_sr > 0 else 0,
        "pct_global": psin_c / total_ps_global * 100,
        "K_local":    K_local,
    }

    sel_cands = [cands_sr[j] for j in sel_j]
    coords    = [(c["lat_clinica"], c["lon_clinica"]) for c in sel_cands]
    print(f"  [{sr:10s}] K={K_local}  cubiertos={len(cub_i)}/{n}  "
          f"pob_sub={psin_c/total_ps_sr*100:.1f}%  "
          f"pob_total={psin_c/total_ps_global*100:.1f}%  "
          f"coords={[(f'{la:.3f}',f'{lo:.3f}') for la,lo in coords]}", flush=True)

# Comparativa: global K=5 vs subregional (4×3=12)
sol_global = pkl["soluciones"]["EDOMEX"][K_GLOBAL]
psin_global = sol_global["psin_cub"]
psin_sub_total = sum(s["psin_cub"] for s in soluciones_sub.values())
n_cub_sub = sum(len(s["cub_i"]) for s in soluciones_sub.values())
n_total = len(df_prio_all)

K_TOTAL_SUB = sum(K_SUB.values())
print(f"\n  GLOBAL K=5:              pob_sin cubierta = {psin_global:,.0f} "
      f"({psin_global/total_ps_global*100:.1f}%)  "
      f"huecos = {len(sol_global['cub_idx'])}/{n_total}")
print(f"  SUBREGIONAL K={K_TOTAL_SUB} (4×3): pob_sin cubierta = {psin_sub_total:,.0f} "
      f"({psin_sub_total/total_ps_global*100:.1f}%)  "
      f"huecos = {n_cub_sub}/{n_total}")
print(f"  Ganancia subregional: +{(psin_sub_total-psin_global)/total_ps_global*100:.1f} pp "
      f"con {K_TOTAL_SUB-K_GLOBAL} clínicas adicionales")

# %% [markdown]
# ## 3. Mapa comparativo: global vs subregional

# %%
fig, axes = plt.subplots(1, 2, figsize=(20, 10))
fig.suptitle(
    "EDOMEX: estrategia global K=5 vs estrategia subregional K=12 (4 zonas × 3 clínicas)\n"
    "Demanda ponderada = score 4 ejes × personas sin seguro",
    fontsize=13, fontweight="bold"
)

URG_COLOR = {"Crítico": "#b2182b", "Alto": "#e08214", "Moderado": "#4dac26"}

def dibujar_mapa(ax, df_prio, clinicas_sel, cubiertos_ids, titulo, nota):
    ax.set_facecolor("#f0f4f8")
    sal = pd.read_parquet(config.INTERMEDIOS_DIR / "salud_EDOMEX.parquet")
    ax.hexbin(sal["x"].values, sal["y"].values,
              gridsize=40, cmap="Greys", alpha=0.15, zorder=1, mincnt=1)

    for _, row in df_prio.iterrows():
        color = URG_COLOR.get(row["urgencia"], "#aaa")
        cubierto = int(row["hueco_id"]) in cubiertos_ids
        circ = plt.Circle((row["x_utm"], row["y_utm"]), row["pers_m"],
                           facecolor=color, alpha=0.55 if cubierto else 0.30,
                           edgecolor="white" if cubierto else color,
                           linewidth=2.0 if cubierto else 0.5, zorder=3)
        ax.add_patch(circ)

    paleta = ["#4393c3","#d6604d","#1b9e77","#7570b3","#e7298a",
              "#a6761d","#e6ab02","#666666","#1f78b4","#33a02c"]
    for ki, (xc, yc) in enumerate(clinicas_sel):
        col = paleta[ki % len(paleta)]
        ax.plot(xc, yc, "D", color=col, markersize=14, zorder=8,
                markeredgecolor="white", markeredgewidth=2.0)
        ax.text(xc, yc, str(ki+1), ha="center", va="center",
                fontsize=7, fontweight="bold", color="white", zorder=9)

    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(titulo, fontsize=11, fontweight="bold")
    ax.text(0.02, 0.02, nota, transform=ax.transAxes, va="bottom", ha="left",
            fontsize=8.5, bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                                    edgecolor="#aaa", alpha=0.92))

# Mapa 1: global K=5
cands_edomex_ok = [c for c in pkl["resultados_red"]["EDOMEX"] if c["tiempos"]]
ids_cub_global  = set(df_prio_all.iloc[i]["hueco_id"]
                      for i in sol_global["cub_idx"])
clinicas_g = [(cands_edomex_ok[j]["x_clinica"], cands_edomex_ok[j]["y_clinica"])
              for j in sol_global["sel_idx"]]

dibujar_mapa(axes[0], df_prio_all, clinicas_g, ids_cub_global,
             f"Estrategia Global — K=5 clínicas\n"
             f"Cobertura: {psin_global:,.0f} sin seguro ({psin_global/total_ps_global*100:.1f}%)",
             f"Huecos cubiertos: {len(sol_global['cub_idx'])}/{n_total}\n"
             f"Limitación: no atiende Norte ni Oriente")

# Mapa 2: subregional K=10
ids_cub_sub = set()
for s in soluciones_sub.values():
    for i in s["cub_i"]:
        ids_cub_sub.add(int(s["df_sub"].iloc[i]["hueco_id"]))

clinicas_sub = []
for sr in ["Norte", "Poniente", "Oriente", "ZMVM"]:
    if sr not in soluciones_sub:
        continue
    s = soluciones_sub[sr]
    for j in s["sel_j"]:
        c = s["cands_sr"][j]
        clinicas_sub.append((c["x_clinica"], c["y_clinica"]))

dibujar_mapa(axes[1], df_prio_all, clinicas_sub, ids_cub_sub,
             f"Estrategia Subregional — K=12 (4 zonas × 3 clínicas)\n"
             f"Cobertura: {psin_sub_total:,.0f} sin seguro ({psin_sub_total/total_ps_global*100:.1f}%)",
             f"Huecos cubiertos: {n_cub_sub}/{n_total}\n"
             f"Cubre las 4 subregiones del estado")

# Leyenda compartida
urg_handles = [mpatches.Patch(color=c, alpha=0.7, label=u)
               for u, c in URG_COLOR.items()]
borde_handle = mpatches.Patch(facecolor="#888", edgecolor="white", linewidth=2.5,
                               label="Hueco cubierto (borde blanco)")
fig.legend(handles=urg_handles + [borde_handle],
           loc="lower center", ncol=4, fontsize=9,
           bbox_to_anchor=(0.5, 0.01), framealpha=0.95)

plt.tight_layout(rect=[0, 0.05, 1, 1])
ruta = config.FIGURAS_DIR / "mclp_subregional_EDOMEX.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## 4. Tabla resumen por subregión

# %%
print("\n" + "="*72, flush=True)
print("MCLP SUBREGIONAL EDOMEX — RESUMEN", flush=True)
print("="*72, flush=True)
print(f"\n  {'Subregión':12s}  {'Huecos':>7}  {'K local':>7}  "
      f"{'Cub. local':>12}  {'Pob. cubierta':>14}  {'% del total':>11}", flush=True)
print(f"  {'—'*68}", flush=True)
for sr in ["Norte", "Poniente", "Oriente", "ZMVM"]:
    if sr not in soluciones_sub:
        continue
    s = soluciones_sub[sr]
    n_sr = len(s["df_sub"])
    print(f"  {sr:12s}  {n_sr:7d}  {s['K_local']:7d}  "
          f"{len(s['cub_i']):4d}/{n_sr:<6d}  "
          f"{s['psin_cub']:>10,.0f}    "
          f"{s['pct_global']:>8.1f}%", flush=True)

print(f"  {'—'*68}", flush=True)
print(f"  {'TOTAL sub':12s}  {n_total:>7}  "
      f"{sum(K_SUB.values()):7d}  "
      f"{n_cub_sub:4d}/{n_total:<6d}  "
      f"{psin_sub_total:>10,.0f}    "
      f"{psin_sub_total/total_ps_global*100:>8.1f}%", flush=True)
print(f"\n  {'Global K=5':12s}  {n_total:>7}  {'5':>7}  "
      f"{len(sol_global['cub_idx']):4d}/{n_total:<6d}  "
      f"{psin_global:>10,.0f}    "
      f"{psin_global/total_ps_global*100:>8.1f}%", flush=True)
print(f"\n  Ganancia subregional: "
      f"+{(psin_sub_total-psin_global)/1000:.1f}k personas adicionales "
      f"(+{(psin_sub_total-psin_global)/total_ps_global*100:.1f} pp) "
      f"con {sum(K_SUB.values())-K_GLOBAL} clínicas más", flush=True)

# Guardar clínicas subregionales para que nb17_validacion pueda usarlas
import pickle as _pkl
clinicas_sub_export = []
for sr in ["Norte", "Poniente", "Oriente", "ZMVM"]:
    if sr not in soluciones_sub:
        continue
    s = soluciones_sub[sr]
    for j in s["sel_j"]:
        c = s["cands_sr"][j]
        clinicas_sub_export.append({
            "subregion":  sr,
            "x_clinica":  c["x_clinica"],
            "y_clinica":  c["y_clinica"],
            "lat":        c["lat_clinica"],
            "lon":        c["lon_clinica"],
            "tiempos":    c["tiempos"],
        })

ruta_sub = config.INTERMEDIOS_DIR / "clinicas_subregionales_EDOMEX.pkl"
with open(str(ruta_sub), "wb") as f:
    _pkl.dump({"clinicas_sub": clinicas_sub_export,
               "ids_cub_sub":  list(ids_cub_sub),
               "psin_sub":     psin_sub_total,
               "n_cub_sub":    n_cub_sub}, f)
print(f"\n✓ {ruta_sub}  ({len(clinicas_sub_export)} clínicas subregionales)", flush=True)
