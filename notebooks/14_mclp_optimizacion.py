# %% [markdown]
# # 14 — Fase 3: MCLP — Ubicación Óptima de Nuevas Clínicas
#
# Maximum Coverage Location Problem (MCLP): dado un presupuesto de K clínicas nuevas,
# ¿en qué coordenadas exactas se deben colocar para maximizar la población cubierta?
#
# **Tres escenarios de optimización (sobre todos los 161 huecos habitados):**
#
#   Escenario A — Equidad:       maximizar personas sin seguro cubiertas (PSINDER)
#   Escenario B — Accesibilidad: eliminar huecos fuera del límite de 15 min caminando
#   Escenario C — Compuesto:     maximizar el score multi-eje del notebook 13
#
# **Metodología:**
#   1. Para cada hueco, se genera una grilla de candidatos (puntos donde podría ir la clínica)
#   2. Se calcula la matriz de cobertura: ¿cubre el candidato j al hueco i en ≤ 15 min?
#      (KDTree euclidiana con factor de desvío 1.35 para rapidez; validación OSM en nb 15)
#   3. Se resuelve el ILP con PuLP/CBC (código abierto, sin costo)
#   4. Se evalúan K = 1, 2, 3 clínicas por ciudad
#
# **Nota sobre candidatos:**
#   El centroide del hueco es el punto matemáticamente más lejano de todas las clínicas
#   circundantes — es el candidato natural por construcción del Alpha complex.
#   La grilla agrega puntos alternativos dentro del radio del hueco.

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import pulp
from scipy.spatial import cKDTree
from pyproj import Transformer
from shapely.geometry import Point, MultiPoint
import geopandas as gpd

from lib import config

# %%
REGIONES    = ["CDMX", "EDOMEX"]
VELOCIDAD   = 4.5          # km/h peatonal
DETOUR      = 1.35         # factor de desvío euclidiana → red real
TIEMPO_LIM  = 15           # minutos — umbral de accesibilidad
K_MAX       = 3            # máximo de clínicas nuevas por escenario por ciudad
GRID_PASO   = 200          # metros entre candidatos en la grilla del hueco

_VEL_M_MIN = (VELOCIDAD * 1000) / 60
_RADIO_COB = TIEMPO_LIM * _VEL_M_MIN / DETOUR   # radio euclidiano que cubre 15 min real

_TR_GEO_UTM = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)
_TR_UTM_GEO = Transformer.from_crs(config.CRS_METROS, "EPSG:4326", always_xy=True)

COLORES = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}

print(f"Radio de cobertura euclidiana equivalente a {TIEMPO_LIM} min: {_RADIO_COB:.0f} m")

# %% [markdown]
# ## 1. Cargar datos

# %%
dfs = {}
salud = {}

for region in REGIONES:
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_score_{region}.parquet")
    dfs[region]  = df
    salud[region] = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    print(f"[{region}]  {len(df)} huecos habitados  |  "
          f"Críticos: {(df['urgencia']=='Crítico').sum()}  |  "
          f"Altos: {(df['urgencia']=='Alto').sum()}")

# %% [markdown]
# ## 2. Generador de candidatos y matriz de cobertura

# %%
def generar_candidatos(cx, cy, radio_m, paso_m=GRID_PASO):
    """Genera grilla de candidatos dentro del círculo del hueco (UTM metros)."""
    xs = np.arange(cx - radio_m, cx + radio_m + paso_m, paso_m)
    ys = np.arange(cy - radio_m, cy + radio_m + paso_m, paso_m)
    XX, YY = np.meshgrid(xs, ys)
    pts = np.column_stack([XX.ravel(), YY.ravel()])
    # Solo los que caen dentro del círculo del hueco
    dists = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
    pts = pts[dists <= radio_m]
    # Siempre incluir el centroide exacto
    centroide = np.array([[cx, cy]])
    return np.vstack([centroide, pts])


def matriz_cobertura(candidatos_utm, huecos_utm, radio_cob):
    """C[i,j] = 1 si el candidato j cubre al hueco i (euclidiana ≤ radio_cob).

    La cobertura es de candidato nuevo → centroide de hueco.
    Se usa radio euclidiana que equivale a TIEMPO_LIM minutos con factor desvío.
    """
    tree = cKDTree(candidatos_utm)
    n_huecos    = len(huecos_utm)
    n_candidatos = len(candidatos_utm)
    C = np.zeros((n_huecos, n_candidatos), dtype=np.int8)
    for i, pt in enumerate(huecos_utm):
        idx = tree.query_ball_point(pt, r=radio_cob)
        C[i, idx] = 1
    return C


def resolver_mclp(C, demanda, K, nombre=""):
    """Resuelve el MCLP con PuLP/CBC.

    Maximiza la demanda cubierta dado que podemos colocar K instalaciones.
    C[i,j] = 1 si candidato j cubre hueco i.
    demanda[i] = peso del hueco i (ej. pob_sin_salud).

    Devuelve índices de candidatos seleccionados y demanda cubierta total.
    """
    n_huecos     = C.shape[0]
    n_candidatos = C.shape[1]

    prob = pulp.LpProblem(f"MCLP_{nombre}", pulp.LpMaximize)

    # Variables: y_j = 1 si se coloca clínica en candidato j
    y = [pulp.LpVariable(f"y_{j}", cat="Binary") for j in range(n_candidatos)]
    # Variables: x_i = 1 si hueco i queda cubierto
    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n_huecos)]

    # Objetivo: maximizar demanda cubierta
    prob += pulp.lpSum(demanda[i] * x[i] for i in range(n_huecos))

    # Restricción 1: x_i ≤ Σⱼ C[i,j]*y_j (solo cubierto si hay candidato cerca)
    for i in range(n_huecos):
        vecinos = [j for j in range(n_candidatos) if C[i, j] == 1]
        if vecinos:
            prob += x[i] <= pulp.lpSum(y[j] for j in vecinos)
        else:
            prob += x[i] == 0  # ningún candidato puede cubrir este hueco

    # Restricción 2: solo K clínicas nuevas
    prob += pulp.lpSum(y[j] for j in range(n_candidatos)) <= K

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    seleccionados = [j for j in range(n_candidatos) if pulp.value(y[j]) == 1]
    cubiertos     = [i for i in range(n_huecos)    if pulp.value(x[i]) == 1]
    demanda_cub   = sum(demanda[i] for i in cubiertos)

    return seleccionados, cubiertos, demanda_cub


# %% [markdown]
# ## 3. Optimización por escenario y ciudad

# %%
resultados = {}   # resultados[region][escenario][K] = dict

ESCENARIOS = {
    "A_equidad":       ("pob_sin_salud",    "Equidad (max. personas sin seguro)"),
    "B_accesibilidad": ("tiempo_est_min",   "Accesibilidad (min. tiempo máximo)"),
    "C_compuesto":     ("score",            "Compuesto (score multi-eje)"),
}

for region in REGIONES:
    df = dfs[region]
    resultados[region] = {}

    # Coordenadas UTM de los centroides de los huecos
    xs_h, ys_h = _TR_GEO_UTM.transform(df["lon"].values, df["lat"].values)
    huecos_utm = np.column_stack([xs_h, ys_h])

    # Generar todos los candidatos (unión de grillas de cada hueco)
    print(f"\n[{region}] Generando candidatos...")
    cands_list = []
    for _, row in df.iterrows():
        cx, cy  = _TR_GEO_UTM.transform(row["lon"], row["lat"])
        radio   = max(row["pers_m"] * 1.5, 300)    # radio generoso
        cands   = generar_candidatos(cx, cy, radio, GRID_PASO)
        cands_list.append(cands)
    candidatos_utm = np.unique(np.vstack(cands_list), axis=0)
    print(f"  {len(candidatos_utm):,} candidatos generados")

    # Excluir candidatos donde ya hay clínica (radio < 50 m de una existente)
    tree_clinicas = cKDTree(salud[region][["x", "y"]].values)
    dists_a_clinica, _ = tree_clinicas.query(candidatos_utm)
    candidatos_utm = candidatos_utm[dists_a_clinica > 50]
    print(f"  {len(candidatos_utm):,} candidatos tras excluir zonas con clínica existente")

    # Matriz de cobertura (candidato → hueco) — una sola vez por región
    print(f"  Calculando matriz de cobertura ({len(huecos_utm)}×{len(candidatos_utm)})...")
    C = matriz_cobertura(candidatos_utm, huecos_utm, _RADIO_COB)
    print(f"  Huecos cubribles por al menos 1 candidato: "
          f"{(C.sum(axis=1) > 0).sum()}/{len(huecos_utm)}")

    for esc_key, (col_dem, esc_nombre) in ESCENARIOS.items():
        resultados[region][esc_key] = {}
        # Para accesibilidad: invertir (max de tiempo → más urgente)
        if col_dem == "tiempo_est_min":
            demanda = df[col_dem].values
        else:
            demanda = df[col_dem].values

        print(f"\n  Escenario {esc_key} — {esc_nombre}")
        for K in range(1, K_MAX + 1):
            sel, cub, dem_cub = resolver_mclp(C, demanda, K, f"{region}_{esc_key}_K{K}")
            pob_cub  = df.iloc[cub]["pob_afectada"].sum()
            psin_cub = df.iloc[cub]["pob_sin_salud"].sum()
            # Convertir candidatos seleccionados a lat/lon
            coords = []
            for j in sel:
                lon, lat = _TR_UTM_GEO.transform(
                    candidatos_utm[j, 0], candidatos_utm[j, 1]
                )
                coords.append({"lat": lat, "lon": lon,
                                "x_utm": candidatos_utm[j, 0],
                                "y_utm": candidatos_utm[j, 1]})
            resultados[region][esc_key][K] = {
                "candidatos_sel": sel,
                "huecos_cub": cub,
                "coords": coords,
                "demanda_cubierta": dem_cub,
                "pob_cubierta": pob_cub,
                "psin_cubierta": psin_cub,
            }
            print(f"    K={K}: {len(cub)}/{len(df)} huecos cubiertos  |  "
                  f"pob: {int(pob_cub):,}  |  sin seguro: {int(psin_cub):,}")

# %% [markdown]
# ## 4. Curvas de cobertura — impacto de K

# %%
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle(
    "MCLP — Impacto de agregar K clínicas nuevas por escenario\n"
    "Fila superior: Ciudad de México  |  Fila inferior: Estado de México",
    fontsize=13, fontweight="bold"
)

for fila, region in enumerate(REGIONES):
    for col, (esc_key, (_, esc_nombre)) in enumerate(ESCENARIOS.items()):
        ax = axes[fila][col]
        ks    = list(range(1, K_MAX + 1))
        psin  = [resultados[region][esc_key][k]["psin_cubierta"] for k in ks]
        pob   = [resultados[region][esc_key][k]["pob_cubierta"]  for k in ks]
        nhue  = [len(resultados[region][esc_key][k]["huecos_cub"]) for k in ks]

        ax2   = ax.twinx()
        l1, = ax.plot(ks, psin, "o-", color="#762a83", linewidth=2.5,
                      markersize=8, label="Sin seguro cubiertos")
        l2, = ax.plot(ks, pob,  "s--", color="#4393c3", linewidth=2,
                      markersize=7, label="Población total cubierta")
        l3, = ax2.plot(ks, nhue, "^:", color="#1b7837", linewidth=1.8,
                       markersize=7, label="Huecos cerrados")

        ax.set_xticks(ks)
        ax.set_xlabel("K — nuevas clínicas", fontsize=9)
        ax.set_ylabel("Personas cubiertas", fontsize=9, color="#333")
        ax2.set_ylabel("Huecos cerrados", fontsize=9, color="#1b7837")
        ax.set_title(f"{esc_nombre}\n{region}", fontsize=9.5, fontweight="bold",
                     color=COLORES[region])
        ax.spines[["top"]].set_visible(False)
        ax.legend(handles=[l1, l2, l3], fontsize=7.5, loc="upper left")

plt.tight_layout()
ruta = config.FIGURAS_DIR / "mclp_curvas_cobertura.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 5. Mapas de ubicación óptima — K=1 y K=2 por escenario

# %%
def plot_mapa_mclp(ax, region, esc_key, K, df_huecos, clinicas_existentes):
    """Mapa de la solución MCLP: huecos coloreados por cobertura + nuevas clínicas."""
    res    = resultados[region][esc_key][K]
    coords = res["coords"]
    cub    = set(res["huecos_cub"])

    ax.set_facecolor("#f5f5f5")

    # Clínicas existentes (pequeños puntos grises)
    xs_e, ys_e = clinicas_existentes["x"].values, clinicas_existentes["y"].values
    ax.scatter(xs_e, ys_e, s=1, c="#cccccc", alpha=0.3, zorder=1)

    # Huecos — coloreados por si quedan cubiertos o no
    for i, (_, row) in enumerate(df_huecos.iterrows()):
        cx, cy = row["x_utm"], row["y_utm"]
        radio  = row["pers_m"]
        color  = "#1a9641" if i in cub else "#d6604d"
        alpha  = 0.60 if i in cub else 0.35
        circulo = plt.Circle((cx, cy), radio, color=color, alpha=alpha, zorder=2)
        ax.add_patch(circulo)
        ax.plot(cx, cy, ".", color=color, markersize=4, zorder=3)

    # Nuevas clínicas propuestas (estrellas doradas)
    for coord in coords:
        ax.plot(coord["x_utm"], coord["y_utm"],
                "*", color="#FFD700", markersize=18, zorder=6,
                markeredgecolor="#333", markeredgewidth=1.2)
        # Círculo de cobertura de la nueva clínica
        circulo_cob = plt.Circle((coord["x_utm"], coord["y_utm"]),
                                  _RADIO_COB, color="#FFD700", alpha=0.15,
                                  zorder=4, linestyle="--",
                                  fill=True)
        ax.add_patch(circulo_cob)
        ax.add_patch(plt.Circle((coord["x_utm"], coord["y_utm"]), _RADIO_COB,
                                color="#FFD700", alpha=0.6, fill=False,
                                linewidth=2, linestyle="--", zorder=5))

    ax.set_aspect("equal")
    ax.set_axis_off()

    psin = int(res["psin_cubierta"])
    nh   = len(cub)
    _, esc_nombre = ESCENARIOS[esc_key]
    ax.set_title(
        f"K={K}  —  {esc_nombre[:30]}\n"
        f"{nh} huecos cubiertos  |  {psin:,} sin seguro cubiertos",
        fontsize=8.5, fontweight="bold"
    )


for region in REGIONES:
    df = dfs[region]
    df["x_utm"], df["y_utm"] = _TR_GEO_UTM.transform(df["lon"].values, df["lat"].values)

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(
        f"{region} — Soluciones MCLP: ubicaciones óptimas de nuevas clínicas\n"
        "Fila superior: K=1 clínica  |  Fila inferior: K=2 clínicas\n"
        "Verde = hueco cubierto  ·  Rojo = hueco aún sin cubrir  ·  ★ = nueva clínica propuesta",
        fontsize=11, fontweight="bold"
    )

    for col, esc_key in enumerate(ESCENARIOS.keys()):
        for fila, K in enumerate([1, 2]):
            plot_mapa_mclp(axes[fila][col], region, esc_key, K, df, salud[region])

    # Leyenda global
    parches = [
        mpatches.Patch(color="#1a9641", alpha=0.6, label="Hueco cubierto por clínica nueva"),
        mpatches.Patch(color="#d6604d", alpha=0.35, label="Hueco aún sin cubrir"),
        mlines.Line2D([0], [0], marker="*", color="w", markerfacecolor="#FFD700",
                      markersize=12, label="Clínica nueva propuesta"),
        mpatches.Patch(color="#FFD700", alpha=0.15, label="Zona de cobertura nueva (15 min)"),
        mlines.Line2D([0], [0], marker=".", color="#aaa", markersize=4, label="Clínica existente"),
    ]
    fig.legend(handles=parches, loc="lower center", ncol=5, fontsize=8.5,
               bbox_to_anchor=(0.5, 0.005), framealpha=0.95)

    # Títulos de columnas
    for col, (_, (_, esc_nombre)) in enumerate(ESCENARIOS.items()):
        axes[0][col].set_title(
            f"Escenario: {esc_nombre}\n" + axes[0][col].get_title(),
            fontsize=9, fontweight="bold"
        )

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    ruta = config.FIGURAS_DIR / f"mclp_mapas_{region}.png"
    plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
    plt.show()
    plt.close(fig)
    print(f"✓ {ruta}")

# %% [markdown]
# ## 6. Tabla de coordenadas óptimas exportada

# %%
filas = []
for region in REGIONES:
    for esc_key, (_, esc_nombre) in ESCENARIOS.items():
        for K in range(1, K_MAX + 1):
            res = resultados[region][esc_key][K]
            for idx_c, coord in enumerate(res["coords"]):
                filas.append({
                    "ciudad":        region,
                    "escenario":     esc_key,
                    "descripcion":   esc_nombre,
                    "K":             K,
                    "clinica_num":   idx_c + 1,
                    "lat":           round(coord["lat"], 6),
                    "lon":           round(coord["lon"], 6),
                    "huecos_cubiertos": len(res["huecos_cub"]),
                    "pob_cubierta":  int(res["pob_cubierta"]),
                    "psin_cubierta": int(res["psin_cubierta"]),
                })

df_coords = pd.DataFrame(filas)
ruta_csv  = config.INTERMEDIOS_DIR / "recomendaciones_mclp.csv"
df_coords.to_csv(str(ruta_csv), index=False)
print(f"\n✓ Coordenadas exportadas: {ruta_csv}")
print(f"  {len(df_coords)} filas  ({len(df_coords['ciudad'].unique())} ciudades × "
      f"{len(df_coords['escenario'].unique())} escenarios × K hasta {K_MAX})")

print("\n" + "="*65)
print("RESUMEN EJECUTIVO — MCLP")
print("="*65)
for region in REGIONES:
    print(f"\n  [{region}]")
    df = dfs[region]
    total_psin = df["pob_sin_salud"].sum()
    for esc_key, (_, esc_nombre) in ESCENARIOS.items():
        r3 = resultados[region][esc_key][3]
        pct = r3["psin_cubierta"] / total_psin * 100 if total_psin > 0 else 0
        print(f"    {esc_nombre[:40]:40s}  K=3 → "
              f"{int(r3['psin_cubierta']):,} sin-seguro cubiertos ({pct:.1f}%)")
