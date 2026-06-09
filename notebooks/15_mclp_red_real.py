# %% [markdown]
# # 15 — Fase 3: MCLP con red vial real (OSM local)
#
# Usa las redes GraphML extraídas por `15a_extraer_redes_pbf.py`.
# Si un archivo local no existe, cae a euclidiana × 1.35 con aviso.
#
# **Demanda ponderada:** score × pob_sin_salud
# **K = 3, 4, 5** clínicas nuevas por ciudad.
# **Cobertura:** hueco cubierto si está a ≤ 15 min caminando desde la clínica.

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import math
import numpy as np
import pandas as pd
import osmnx as ox
import networkx as nx
import pulp
from shapely.geometry import Point, MultiPoint
from pyproj import Transformer

from lib import config

REGIONES      = ["CDMX", "EDOMEX"]
VELOCIDAD_KMH = 4.5
TIEMPO_LIM    = 15
DETOUR        = 1.35          # fallback euclidiano
# CDMX: K=7 es el óptimo (máximo retorno marginal). EDOMEX: estrategia subregional en nb19.
K_VALS_CDMX   = [5, 7]
K_VALS_EDOMEX = [5]
MAX_CANDS     = 20
REDES_DIR     = config.OUTPUTS_DIR / "redes"

VEL_M_MIN     = (VELOCIDAD_KMH * 1000) / 60
DIST_MAX_EUC  = (TIEMPO_LIM * VEL_M_MIN) / DETOUR

_TR           = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)
_TR_UTM_GEO   = Transformer.from_crs(config.CRS_METROS, "EPSG:4326", always_xy=True)

# %% [markdown]
# ## 1. Cargar datos de huecos y clusters

# %%
datos = {}
for region in REGIONES:
    huecos   = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_prioritarios_{region}.parquet")
    clusters = pd.read_parquet(config.INTERMEDIOS_DIR / f"clusters_{region}.parquet")
    xs, ys   = _TR.transform(huecos["lon"].values, huecos["lat"].values)
    huecos["x_utm"] = xs
    huecos["y_utm"] = ys
    datos[region]   = {"huecos": huecos, "clusters": clusters}
    print(f"[{region}]  {len(huecos)} huecos  |  {len(clusters)} clusters", flush=True)

# %% [markdown]
# ## 2. Cargar redes locales (o avisar que se usará euclidiana)

# %%
grafos = {}
modos  = {}

for region in REGIONES:
    ruta = REDES_DIR / f"red_{region}.graphml"
    if ruta.exists():
        print(f"[{region}]  Cargando red local ({ruta.stat().st_size/1e6:.0f} MB)...",
              flush=True)
        G = ox.load_graphml(str(ruta))
        grafos[region] = G
        modos[region]  = "red_real"
        print(f"  {len(G.nodes):,} nodos  |  {len(G.edges):,} aristas", flush=True)
    else:
        grafos[region] = None
        modos[region]  = "euclidiana"
        print(f"[{region}]  ⚠ Sin red local — usando euclidiana × {DETOUR}", flush=True)

# %% [markdown]
# ## 3. Funciones de cálculo de tiempos y área de cobertura

# %%
def anclar_nodo(G, lon, lat):
    """Nodo de G más cercano al punto lon/lat."""
    crs  = G.graph["crs"]
    tr   = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    x, y = tr.transform(lon, lat)
    return ox.distance.nearest_nodes(G, x, y), x, y


def tiempos_red(G, nodo_origen, huecos_df):
    """Dijkstra desde nodo_origen → tiempo (min) a cada hueco. Un solo recorrido."""
    crs = G.graph["crs"]
    tr  = Transformer.from_crs("EPSG:4326", crs, always_xy=True)

    dist_nodo = nx.single_source_dijkstra_path_length(
        G, nodo_origen, cutoff=TIEMPO_LIM * 2, weight="time"
    )

    res = {}
    for _, h in huecos_df.iterrows():
        xh, yh = tr.transform(h["lon"], h["lat"])
        nh     = ox.distance.nearest_nodes(G, xh, yh)
        res[int(h["hueco_id"])] = dist_nodo.get(nh, float("inf"))
    return res


def tiempos_euclidiano(x_c, y_c, huecos_df):
    """Tiempo estimado euclidiana × DETOUR (sin red)."""
    dx   = huecos_df["x_utm"].values - x_c
    dy   = huecos_df["y_utm"].values - y_c
    dist = np.hypot(dx, dy)
    return dict(zip(huecos_df["hueco_id"].astype(int), dist * DETOUR / VEL_M_MIN))


def isocrona_red(G, nodo, tiempo_min):
    """Polígono convex-hull de nodos alcanzables en ≤ tiempo_min."""
    alcanzables = nx.single_source_dijkstra_path_length(
        G, nodo, cutoff=tiempo_min, weight="time"
    )
    pts = [Point(G.nodes[n]["x"], G.nodes[n]["y"]) for n in alcanzables]
    if len(pts) < 3:
        return Point(G.nodes[nodo]["x"], G.nodes[nodo]["y"]).buffer(200)
    return MultiPoint(pts).convex_hull


def isocrona_circulo(x_c, y_c, tiempo_min):
    """Círculo de radio equivalente a tiempo_min caminando (fallback)."""
    return Point(x_c, y_c).buffer((tiempo_min * VEL_M_MIN) / DETOUR)


# %% [markdown]
# ## 4. Calcular candidatos por cluster

# %%
print("\n" + "="*65, flush=True)
print("CALCULANDO TIEMPOS POR CANDIDATO", flush=True)
print("="*65, flush=True)

resultados = {}

for region in REGIONES:
    G        = grafos[region]
    huecos   = datos[region]["huecos"]
    clusters = datos[region]["clusters"]
    modo     = modos[region]
    resultados[region] = []

    clusters_top = clusters.head(MAX_CANDS)
    print(f"\n[{region}]  Modo: {modo}  |  {len(clusters_top)} candidatos", flush=True)

    for _, cl in clusters_top.iterrows():
        cl_id  = int(cl["cluster_id"])
        lat_c  = cl["lat_centroide"]
        lon_c  = cl["lon_centroide"]
        x_c, y_c = _TR.transform(lon_c, lat_c)

        try:
            if modo == "red_real":
                nodo_c, x_n, y_n = anclar_nodo(G, lon_c, lat_c)
                tiempos = tiempos_red(G, nodo_c, huecos)
                iso     = isocrona_red(G, nodo_c, TIEMPO_LIM)
                x_c, y_c = x_n, y_n   # usar coord real del nodo anclado
            else:
                tiempos = tiempos_euclidiano(x_c, y_c, huecos)
                iso     = isocrona_circulo(x_c, y_c, TIEMPO_LIM)

            cubiertos = sum(1 for t in tiempos.values() if t <= TIEMPO_LIM)
            print(f"  C{int(cl['rank_cluster']):02d}  {int(cl['n_huecos'])} huecos  "
                  f"psin={int(cl['psin_total']):,}  "
                  f"→ {cubiertos} cubiertos ≤{TIEMPO_LIM}min",
                  flush=True)

        except Exception as e:
            print(f"  C{int(cl['rank_cluster']):02d}  ✗ {e}", flush=True)
            tiempos = tiempos_euclidiano(x_c, y_c, huecos)
            iso     = isocrona_circulo(x_c, y_c, TIEMPO_LIM)

        lon_f, lat_f = _TR_UTM_GEO.transform(x_c, y_c)
        resultados[region].append({
            "cluster_id":  cl_id,
            "rank":        int(cl["rank_cluster"]),
            "n_huecos_cl": int(cl["n_huecos"]),
            "psin_total":  int(cl["psin_total"]),
            "score_max":   cl["score_max"],
            "lat_clinica": lat_f,
            "lon_clinica": lon_f,
            "x_clinica":   x_c,
            "y_clinica":   y_c,
            "isocrona":    iso,
            "tiempos":     tiempos,
            "modo":        modo,
        })

# %% [markdown]
# ## 5. MCLP Global

# %%
def resolver_mclp(huecos_df, candidatos, K, region):
    n_h     = len(huecos_df)
    n_c     = len(candidatos)
    demanda = (huecos_df["score"].fillna(0) * huecos_df["pob_sin_salud"].fillna(0)).values
    ids_h   = huecos_df["hueco_id"].astype(int).tolist()

    C = np.zeros((n_h, n_c), dtype=np.int8)
    for j, cand in enumerate(candidatos):
        for i, hid in enumerate(ids_h):
            if cand["tiempos"].get(hid, float("inf")) <= TIEMPO_LIM:
                C[i, j] = 1

    prob = pulp.LpProblem(f"MCLP_{region}_K{K}", pulp.LpMaximize)
    y    = [pulp.LpVariable(f"y_{j}", cat="Binary") for j in range(n_c)]
    x    = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n_h)]

    prob += pulp.lpSum(demanda[i] * x[i] for i in range(n_h))
    for i in range(n_h):
        vecinos = [j for j in range(n_c) if C[i, j] == 1]
        prob   += x[i] <= (pulp.lpSum(y[j] for j in vecinos) if vecinos else 0)
    prob += pulp.lpSum(y) <= K
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    sel      = [j for j in range(n_c) if pulp.value(y[j]) == 1]
    cub      = [i for i in range(n_h) if pulp.value(x[i]) == 1]
    psin_cub = huecos_df.iloc[cub]["pob_sin_salud"].sum()
    pob_cub  = huecos_df.iloc[cub]["pob_afectada"].sum()
    return sel, cub, pob_cub, psin_cub, C


# %%
soluciones = {}

print("\n" + "="*65, flush=True)
print("MCLP — SELECCIONANDO K MEJORES UBICACIONES", flush=True)
print("="*65, flush=True)

for region in REGIONES:
    huecos_df  = datos[region]["huecos"]
    candidatos = resultados[region]
    soluciones[region] = {}
    K_VALS = K_VALS_CDMX if region == "CDMX" else K_VALS_EDOMEX
    print(f"\n[{region}]", flush=True)

    for K in K_VALS:
        sel, cub, pob, psin, C_mat = resolver_mclp(huecos_df, candidatos, K, region)
        soluciones[region][K] = {
            "sel_idx":    sel,
            "cub_idx":    cub,
            "pob_cub":    pob,
            "psin_cub":   psin,
            "C_mat":      C_mat,
            "candidatos": candidatos,
        }
        pct   = psin / huecos_df["pob_sin_salud"].sum() * 100
        ranks = [candidatos[j]["rank"] for j in sel]
        print(f"  K={K}:  {len(cub)}/{len(huecos_df)} huecos  |  "
              f"{int(psin):,} sin seguro ({pct:.1f}%)  |  Clusters {ranks}",
              flush=True)

# %% [markdown]
# ## 6. Guardar resultados

# %%
import pickle

ruta_pkl = config.INTERMEDIOS_DIR / "soluciones_mclp_red.pkl"
with open(str(ruta_pkl), "wb") as f:
    pickle.dump({"soluciones": soluciones, "resultados_red": resultados}, f)
print(f"\n✓ {ruta_pkl}", flush=True)

filas = []
for region in REGIONES:
    for K, sol in soluciones[region].items():
        for j in sol["sel_idx"]:
            cand = sol["candidatos"][j]
            filas.append({
                "ciudad":           region,
                "K":                K,
                "cluster_id":       cand["cluster_id"],
                "rank_cluster":     cand["rank"],
                "lat":              round(cand["lat_clinica"], 6),
                "lon":              round(cand["lon_clinica"], 6),
                "modo":             cand["modo"],
                "psin_cubiertos":   int(sol["psin_cub"]),
                "huecos_cubiertos": len(sol["cub_idx"]),
            })

ruta_csv = config.INTERMEDIOS_DIR / "recomendaciones_fase3.csv"
pd.DataFrame(filas).to_csv(str(ruta_csv), index=False)
print(f"✓ {ruta_csv}", flush=True)

# %% [markdown]
# ## 7. Resumen final

# %%
print("\n" + "="*65, flush=True)
print("RESUMEN — IMPACTO POR NÚMERO DE CLÍNICAS NUEVAS", flush=True)
print("="*65, flush=True)

for region in REGIONES:
    total_psin = datos[region]["huecos"]["pob_sin_salud"].sum()
    total_h    = len(datos[region]["huecos"])
    modo       = modos[region]
    print(f"\n[{region}]  ({modo})  {int(total_psin):,} sin seguro en huecos prioritarios",
          flush=True)
    for K in sorted(soluciones[region].keys()):
        sol   = soluciones[region][K]
        pct   = sol["psin_cub"] / total_psin * 100
        ranks = [sol["candidatos"][j]["rank"] for j in sol["sel_idx"]]
        print(f"  K={K}:  {len(sol['cub_idx'])}/{total_h} huecos  |  "
              f"{int(sol['psin_cub']):,} sin seguro ({pct:.1f}%)  |  Clusters {ranks}",
              flush=True)
