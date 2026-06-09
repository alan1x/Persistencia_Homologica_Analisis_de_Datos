# %% [markdown]
# # 12 — Fase 2B: Accesibilidad Peatonal Real (Isócronas OSMnx)
#
# **Pregunta:** ¿Cuántos minutos camina una persona desde dentro de cada hueco
# de cobertura de salud hasta la clínica más cercana?
#
# **Nota metodológica — dos velocidades de cálculo:**
#   - KDTree (Sección 2): distancia euclidiana sobre datos ya cargados en memoria
#     (salud_CDMX.parquet / salud_EDOMEX.parquet del DENUE). Instantáneo. Cubre
#     los 280 huecos. Resultado = estimación (se multiplica por factor de desvío 1.35).
#   - OSMnx (Sección 6): descarga la red real de calles de OpenStreetMap para calcular
#     el camino mínimo exacto en minutos. Lento (~30 s por hueco). Solo para los
#     top 3 casos por ciudad.
#   Los datos de /Datos/Censo y /Datos/Geoestadistico son para cruzar AGEBs (notebook 10)
#   y no se usan aquí.
#
# **Estructura:**
#   1. Carga de todos los huecos (solo habitados, pob_afectada > 0)
#   2. Distancia estimada a clínica más cercana — todos los huecos (KDTree)
#   3. Scatter separado CDMX | EDOMEX
#   4. Comparativa 1 — top 10 más grandes (CDMX | EDOMEX)
#   5. Comparativa 2 — top 10 más lejanos (CDMX | EDOMEX)
#   6. Mapas detallados con red OSM: top 3 grandes + top 3 lejanos por ciudad
#   7. Tabla resumen + comparativa Opción A vs B

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import osmnx as ox
from scipy.spatial import cKDTree
from pyproj import Transformer
from lib import config, geo_network

# %%
REGIONES      = ["CDMX", "EDOMEX"]
TIEMPO_LIM    = 15          # minutos — umbral de accesibilidad aceptable
VELOCIDAD     = 4.5         # km/h caminando
DETOUR        = 1.35        # euclidiana → red real (factor de desvío urbano típico)
RADIO_OSM_M   = 2000        # radio de red OSM para los mapas detallados
TOP_BAR       = 10          # posiciones en las comparativas
TOP_MAP       = 3           # huecos por categoría en los mapas

_VEL_M_MIN  = (VELOCIDAD * 1000) / 60
_TR_GEO_UTM = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

COLORES = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}

# %% [markdown]
# ## 1. Cargar huecos — solo habitados (pob_afectada > 0)

# %%
dfs_todos = {}   # todos los huecos (para referencia)
dfs = {}         # solo habitados (para análisis)

for region in REGIONES:
    ruta = config.INTERMEDIOS_DIR / f"huecos_censal_{region}.parquet"
    df   = pd.read_parquet(str(ruta))
    df["ciudad"] = region
    dfs_todos[region] = df
    dfs[region]        = df[df["pob_afectada"] > 0].copy()
    print(f"[{region}]  total: {len(df)}  |  habitados: {len(dfs[region])}  "
          f"|  sin pob (rural/vacío): {len(df) - len(dfs[region])}")

salud = {r: pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{r}.parquet")
         for r in REGIONES}

# %% [markdown]
# ## 2. Distancia a clínica más cercana — todos los huecos habitados (KDTree)
#
# KDTree construye un árbol de búsqueda sobre las coordenadas UTM de las ~21k–31k
# clínicas del DENUE (salud_*.parquet). La consulta es instantánea para los 280 huecos.
# La distancia euclidiana se multiplica por el factor de desvío (1.35) para estimar
# la distancia que una persona realmente camina, y se divide entre la velocidad.

# %%
def estimar_accesibilidad(df_huecos, df_clinicas):
    """KDTree sobre clinicas UTM → distancia euclidiana → tiempo estimado."""
    tree       = cKDTree(df_clinicas[["x", "y"]].values)
    xs, ys     = _TR_GEO_UTM.transform(df_huecos["lon"].values, df_huecos["lat"].values)
    dists, _   = tree.query(np.column_stack([xs, ys]))
    df         = df_huecos.copy()
    df["x_utm"]          = xs
    df["y_utm"]          = ys
    df["dist_eucl_m"]    = dists
    df["dist_red_m"]     = dists * DETOUR
    df["tiempo_est_min"] = df["dist_red_m"] / _VEL_M_MIN
    return df

for region in REGIONES:
    dfs[region] = estimar_accesibilidad(dfs[region], salud[region])

for region in REGIONES:
    df = dfs[region]
    n_fuera = (df["tiempo_est_min"] > TIEMPO_LIM).sum()
    print(f"[{region}]  habitados: {len(df)}  |  "
          f"mediana: {df['tiempo_est_min'].median():.1f} min  |  "
          f"máximo: {df['tiempo_est_min'].max():.1f} min  |  "
          f"fuera de {TIEMPO_LIM}min: {n_fuera} ({n_fuera/len(df)*100:.0f}%)")

# %% [markdown]
# ## 3. Scatter separado: tamaño del hueco vs tiempo de acceso
#
# Un panel por ciudad. Solo huecos habitados.
# Tamaño del punto = población afectada.

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7), sharey=False)
fig.suptitle(
    "Huecos de cobertura de salud — Tamaño topológico vs Tiempo de caminata a clínica\n"
    "(solo huecos con población registrada — Censo 2020 / INEGI)",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df      = dfs[region]
    color   = COLORES[region]
    tam     = np.clip(df["pob_afectada"] / 500 + 20, 20, 300)

    sc = ax.scatter(df["pers_m"], df["tiempo_est_min"],
                    c=color, s=tam, alpha=0.70,
                    edgecolors="white", linewidths=0.4, zorder=3)

    # Líneas de referencia
    ax.axhline(TIEMPO_LIM, color="#b2182b", linestyle="--", linewidth=1.8, alpha=0.8,
               label=f"Límite {TIEMPO_LIM} min")
    ax.axvline(500, color="#555", linestyle=":", linewidth=1.3, alpha=0.6,
               label="500 m (hueco significativo)")

    # Sombreado cuadrante crítico
    y_max = df["tiempo_est_min"].max() * 1.15
    ax.fill_betweenx([TIEMPO_LIM, y_max], 500, df["pers_m"].max() * 1.1,
                     color="#b2182b", alpha=0.07, zorder=1)
    ax.text(520, TIEMPO_LIM * 1.06, "Grande + Inaccesible",
            fontsize=8.5, color="#b2182b", fontweight="bold", alpha=0.8)

    # Etiquetar los 4 peores (más al cuadrante crítico)
    df_crit = df[df["tiempo_est_min"] > TIEMPO_LIM].nlargest(4, "pers_m")
    for _, row in df_crit.iterrows():
        ax.annotate(
            f"#{int(row['hueco_id'])}",
            xy=(row["pers_m"], row["tiempo_est_min"]),
            xytext=(row["pers_m"] + 30, row["tiempo_est_min"] + 0.8),
            fontsize=8, color="#555",
            arrowprops=dict(arrowstyle="-", color="#bbb", lw=0.7),
        )

    n_fuera = (df["tiempo_est_min"] > TIEMPO_LIM).sum()
    ax.set_title(
        f"{region}  —  {len(df)} huecos habitados\n"
        f"{n_fuera} fuera del límite ({n_fuera/len(df)*100:.0f}%)",
        fontsize=11, fontweight="bold", color=color
    )
    ax.set_xlabel("Persistencia topológica del hueco (metros)", fontsize=10)
    ax.set_ylabel("Tiempo estimado a clínica más cercana (min)", fontsize=10)
    ax.legend(fontsize=8.5, framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)

fig.text(0.5, 0.01,
         f"Tamaño del punto ∝ población afectada  |  "
         f"Tiempo = distancia euclidiana × {DETOUR} / {VELOCIDAD}km/h  |  "
         f"Datos: DENUE INEGI + Censo 2020",
         ha="center", fontsize=8, color="#666")

plt.tight_layout(rect=[0, 0.03, 1, 1])
ruta = config.FIGURAS_DIR / "scatter_accesibilidad.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 4. Comparativa 1 — Top huecos más GRANDES (separado por ciudad)

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    f"Comparativa 1 — Top {TOP_BAR} huecos más grandes por persistencia topológica\n"
    "Número en la barra = tiempo estimado caminando a la clínica más cercana",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df_top = dfs[region].nlargest(TOP_BAR, "pers_m").reset_index(drop=True)
    color  = COLORES[region]

    barras = ax.barh(range(len(df_top)), df_top["pers_m"],
                     color=color, edgecolor="white", linewidth=1.0, alpha=0.85)

    for i, row in df_top.iterrows():
        t     = row["tiempo_est_min"]
        ok    = t <= TIEMPO_LIM
        ct    = "#1a9641" if ok else "#b2182b"
        texto = f"  {t:.0f} min  {'✓' if ok else '✗'}"
        ax.text(row["pers_m"] + 10, i, texto,
                va="center", fontsize=9, color=ct, fontweight="bold")

    yticks = [f"#{int(r['hueco_id'])}  —  {int(r['pob_afectada']):,} pers."
              for _, r in df_top.iterrows()]
    ax.set_yticks(range(len(df_top)))
    ax.set_yticklabels(yticks, fontsize=8.5)
    ax.invert_yaxis()

    n_fuera = (df_top["tiempo_est_min"] > TIEMPO_LIM).sum()
    ax.set_title(f"{region}  |  {n_fuera}/{len(df_top)} fuera de {TIEMPO_LIM} min",
                 fontsize=11, fontweight="bold", color=color)
    ax.set_xlabel("Persistencia (metros) — radio del hueco topológico", fontsize=10)
    ax.axvline(500, color="#aaa", linestyle=":", linewidth=1.2)
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "comparativa_tamano.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 5. Comparativa 2 — Top huecos más LEJANOS (separado por ciudad)

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    f"Comparativa 2 — Top {TOP_BAR} huecos más lejanos de una clínica\n"
    "Número en la barra = persistencia topológica del hueco (tamaño geométrico)",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df_top = dfs[region].nlargest(TOP_BAR, "tiempo_est_min").reset_index(drop=True)
    color  = COLORES[region]

    ax.barh(range(len(df_top)), df_top["tiempo_est_min"],
            color=color, edgecolor="white", linewidth=1.0, alpha=0.85)

    for i, row in df_top.iterrows():
        ax.text(row["tiempo_est_min"] + 0.2, i,
                f"  {row['pers_m']:.0f} m  |  {int(row['pob_afectada']):,} pers.",
                va="center", fontsize=8.5, color="#333")

    yticks = [f"#{int(r['hueco_id'])}  —  {r['pct_sin_salud_prom']:.0f}% sin seguro"
              for _, r in df_top.iterrows()]
    ax.set_yticks(range(len(df_top)))
    ax.set_yticklabels(yticks, fontsize=8.5)
    ax.invert_yaxis()

    ax.axvline(TIEMPO_LIM, color="#b2182b", linestyle="--", linewidth=1.8, alpha=0.8,
               label=f"Límite {TIEMPO_LIM} min")
    ax.set_title(f"{region}", fontsize=11, fontweight="bold", color=color)
    ax.set_xlabel("Tiempo estimado de caminata a la clínica más cercana (minutos)", fontsize=10)
    ax.legend(fontsize=8.5)
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "comparativa_distancia.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 6. Mapas detallados con red OSM — Top 3 grandes + Top 3 lejanos por ciudad
#
# **Diseño de cada mapa:**
#   - Fondo gris claro = red de calles real (OpenStreetMap)
#   - Zona azul = todo lo que el paciente puede alcanzar caminando 15 min
#   - Punto naranja = centroide del hueco (donde está el paciente)
#   - Punto verde = clínica más cercana
#   - Anotación grande = tiempo real de caminata en red OSM

# %%
def seleccionar_top3(df_region, col, ascending=False):
    """Top 3 únicos por la columna indicada."""
    return df_region.nlargest(TOP_MAP, col).reset_index(drop=True)


def descargar_y_calcular(row, df_clinicas):
    """Descarga red OSM + calcula tiempo real + isócrona para un hueco."""
    lat_h, lon_h = row["lat"], row["lon"]
    region       = row["ciudad"]
    hueco_id     = int(row["hueco_id"])

    G_proj = None
    try:
        G_proj = geo_network.descargar_red_punto(lat_h, lon_h, radio_m=RADIO_OSM_M)
    except Exception as e:
        print(f"    Error red OSM hueco #{hueco_id}: {e}")
        return {"G_proj": None, "isocrona": None, "tiempo_min": None,
                "distancia_m": None, "x_orig": None, "y_orig": None,
                "x_clin": None, "y_clin": None}

    crs_grafo  = G_proj.graph["crs"]
    tr_a_grafo = Transformer.from_crs("EPSG:4326", crs_grafo, always_xy=True)
    tr_utm_geo = Transformer.from_crs(config.CRS_METROS, "EPSG:4326", always_xy=True)

    x_orig, y_orig = tr_a_grafo.transform(lon_h, lat_h)

    # Clínica más cercana (euclidiana) — coordenadas en el CRS del grafo
    lons_c, lats_c = tr_utm_geo.transform(df_clinicas["x"].values, df_clinicas["y"].values)
    dists_eucl     = np.hypot(lats_c - lat_h, lons_c - lon_h)
    idx_cerca      = np.argmin(dists_eucl)
    x_clin, y_clin = tr_a_grafo.transform(lons_c[idx_cerca], lats_c[idx_cerca])

    # Accesibilidad real en red
    hole_x, hole_y = _TR_GEO_UTM.transform(lon_h, lat_h)
    mask    = (((df_clinicas["x"] - hole_x)**2 +
                (df_clinicas["y"] - hole_y)**2) <= (RADIO_OSM_M * 1.5)**2)
    df_cerca = df_clinicas[mask]

    acceso  = {"tiempo_min": None, "distancia_m": None, "nodo_origen": None}
    if len(df_cerca) > 0:
        acceso = geo_network.accesibilidad_desde_punto(
            G_proj, lat_h, lon_h, df_cerca, top_n=20
        )

    iso = None
    if acceso.get("nodo_origen") is not None:
        iso = geo_network.isocrona_desde_nodo(G_proj, acceso["nodo_origen"], TIEMPO_LIM)

    return {
        "G_proj": G_proj, "isocrona": iso,
        "tiempo_min": acceso.get("tiempo_min"),
        "distancia_m": acceso.get("distancia_m"),
        "x_orig": x_orig, "y_orig": y_orig,
        "x_clin": x_clin, "y_clin": y_clin,
    }


def plot_mapa(ax, datos_hueco, fila_info, categoria):
    """Dibuja un mapa limpio de accesibilidad para un hueco.

    Elementos:
      - Red de calles (gris claro)
      - Zona azul: alcanzable en 15 min caminando (isócrona desde el paciente)
      - Punto naranja: centroide del hueco (paciente)
      - Punto verde: clínica más cercana
      - Anotación: tiempo de caminata real (OSM)
    """
    G      = datos_hueco.get("G_proj")
    iso    = datos_hueco.get("isocrona")
    x_orig = datos_hueco.get("x_orig")
    y_orig = datos_hueco.get("y_orig")
    x_clin = datos_hueco.get("x_clin")
    y_clin = datos_hueco.get("y_clin")
    t      = datos_hueco.get("tiempo_min")
    dist   = datos_hueco.get("distancia_m")

    hueco_id = int(fila_info["hueco_id"])
    pob      = int(fila_info["pob_afectada"])
    pct      = fila_info["pct_sin_salud_prom"]
    pers     = fila_info["pers_m"]

    ax.set_facecolor("#f2f2f2")

    if G is None:
        ax.text(0.5, 0.5, "Red OSM\nno disponible",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=11, color="#888")
        ax.set_axis_off()
        return

    # 1. Red de calles — gris fino
    try:
        edges = ox.graph_to_gdfs(G, nodes=False)
        edges.plot(ax=ax, color="#c0c0c0", linewidth=0.5, alpha=0.9, zorder=1)
    except Exception:
        pass

    # 2. Isócrona — zona alcanzable en 15 min
    if iso is not None:
        gpd.GeoSeries([iso]).plot(ax=ax, color="#4393c3", alpha=0.25,
                                  edgecolor="#2166ac", linewidth=2.0, zorder=2)

    # 3. Clínica más cercana (verde)
    if x_clin is not None:
        ax.plot(x_clin, y_clin, "o", color="#1a9641", markersize=13, zorder=5,
                markeredgecolor="white", markeredgewidth=1.5)
        ax.annotate("Clínica\nmás cercana", xy=(x_clin, y_clin),
                    xytext=(x_clin, y_clin - 250),
                    fontsize=6.5, ha="center", color="#1a9641", zorder=6,
                    fontweight="bold")

    # 4. Centroide del hueco / paciente (naranja)
    if x_orig is not None:
        ax.plot(x_orig, y_orig, "o", color="#e6550d", markersize=13, zorder=7,
                markeredgecolor="white", markeredgewidth=1.5)
        ax.annotate("Paciente\n(centroide)", xy=(x_orig, y_orig),
                    xytext=(x_orig, y_orig + 280),
                    fontsize=6.5, ha="center", color="#e6550d", zorder=8,
                    fontweight="bold")

    # 5. Anotación del tiempo (grande y clara)
    if t is not None:
        dentro  = t <= TIEMPO_LIM
        color_t = "#1a9641" if dentro else "#b2182b"
        dist_txt = f"{dist:.0f} m en red" if dist else ""
        label_t = f"{t:.0f} min caminando\n{dist_txt}"
        estado  = "Accesible" if dentro else f"Fuera del límite de {TIEMPO_LIM} min"
    else:
        color_t = "#888"
        label_t = "Sin ruta\nen red OSM"
        estado  = ""

    ax.text(0.5, 0.98, label_t, transform=ax.transAxes,
            ha="center", va="top", fontsize=12, fontweight="bold", color=color_t,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor=color_t, alpha=0.95, linewidth=1.5))
    if estado:
        ax.text(0.5, 0.86, estado, transform=ax.transAxes,
                ha="center", va="top", fontsize=8, color=color_t, alpha=0.85)

    ax.set_title(
        f"[{categoria}]  Hueco #{hueco_id}\n"
        f"Persistencia: {pers:.0f} m  |  {pob:,} personas  |  {pct:.0f}% sin seguro",
        fontsize=9, fontweight="bold", pad=5
    )
    ax.set_axis_off()


# %%  Generar mapas para cada región
leyenda_parches = [
    mpatches.Patch(color="#c0c0c0", label="Red de calles (OSM)"),
    mpatches.Patch(color="#4393c3", alpha=0.4, label=f"Zona alcanzable en {TIEMPO_LIM} min (desde paciente)"),
    mlines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#e6550d",
                  markersize=10, label="Paciente (centroide del hueco)"),
    mlines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#1a9641",
                  markersize=10, label="Clínica más cercana"),
]

for region in REGIONES:
    df_reg = dfs[region]

    # Seleccionar top 3 grandes y top 3 lejanos (pueden repetirse si hay overlap)
    top_grandes = df_reg.nlargest(TOP_MAP, "pers_m").reset_index(drop=True)
    top_lejanos = df_reg.nlargest(TOP_MAP, "tiempo_est_min").reset_index(drop=True)

    print(f"\n{'='*55}")
    print(f"  MAPAS — {region}")
    print(f"{'='*55}")

    # Descargar redes y calcular para cada hueco
    datos_grandes = []
    for _, row in top_grandes.iterrows():
        print(f"  [Grande #{int(row['hueco_id'])}] {row['pers_m']:.0f}m — descargando OSM...")
        datos = descargar_y_calcular(row, salud[region])
        if datos["tiempo_min"]:
            print(f"    → {datos['tiempo_min']:.1f} min")
        datos_grandes.append(datos)

    datos_lejanos = []
    for _, row in top_lejanos.iterrows():
        print(f"  [Lejano #{int(row['hueco_id'])}] {row['tiempo_est_min']:.1f}min est. — descargando OSM...")
        datos = descargar_y_calcular(row, salud[region])
        if datos["tiempo_min"]:
            print(f"    → {datos['tiempo_min']:.1f} min real")
        datos_lejanos.append(datos)

    # Figura: 2 filas × 3 columnas
    fig = plt.figure(figsize=(18, 13))
    fig.suptitle(
        f"{region} — Accesibilidad Peatonal Real (Red OSM)\n"
        f"Fila superior: 3 huecos más GRANDES  |  Fila inferior: 3 huecos más LEJANOS",
        fontsize=13, fontweight="bold", y=0.99
    )
    gs = fig.add_gridspec(2, 3, hspace=0.40, wspace=0.25,
                          left=0.06, right=0.98, top=0.93, bottom=0.08)

    # Etiquetas de fila
    fig.text(0.01, 0.72, "TOP 3\nMÁS\nGRANDES", rotation=90, va="center",
             fontsize=10, fontweight="bold", color="#555")
    fig.text(0.01, 0.28, "TOP 3\nMÁS\nLEJANOS", rotation=90, va="center",
             fontsize=10, fontweight="bold", color="#555")

    for col, (datos, row) in enumerate(zip(datos_grandes, top_grandes.iterrows())):
        ax = fig.add_subplot(gs[0, col])
        plot_mapa(ax, datos, row[1], "MÁS GRANDE")

    for col, (datos, row) in enumerate(zip(datos_lejanos, top_lejanos.iterrows())):
        ax = fig.add_subplot(gs[1, col])
        plot_mapa(ax, datos, row[1], "MÁS LEJANO")

    # Leyenda global al pie
    fig.legend(handles=leyenda_parches, loc="lower center", ncol=4,
               fontsize=9, bbox_to_anchor=(0.5, 0.005),
               framealpha=0.95, edgecolor="#ccc")

    ruta = config.FIGURAS_DIR / f"mapas_accesibilidad_{region}.png"
    plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
    plt.show()
    plt.close(fig)
    print(f"\n✓ Figura guardada: {ruta}")

# %% [markdown]
# ## 7. Tabla resumen + Comparativa Opción A (Laguerre) vs Opción B (Isócronas)

# %%
print("\n" + "="*65)
print("RESUMEN EJECUTIVO — ACCESIBILIDAD PEATONAL")
print("="*65)

for region in REGIONES:
    df = dfs[region]
    n_fuera   = (df["tiempo_est_min"] > TIEMPO_LIM).sum()
    pob_fuera = df.loc[df["tiempo_est_min"] > TIEMPO_LIM, "pob_afectada"].sum()
    sin_fuera = df.loc[df["tiempo_est_min"] > TIEMPO_LIM, "pob_sin_salud"].sum()
    print(f"\n  [{region}]  {len(df)} huecos habitados")
    print(f"    Fuera del límite de {TIEMPO_LIM} min:  {n_fuera} huecos  ({n_fuera/len(df)*100:.0f}%)")
    print(f"    Población en esos huecos:          {int(pob_fuera):,} personas")
    print(f"    Sin seguro médico:                 {int(sin_fuera):,} personas")
    print(f"    Tiempo mediano a clínica:           {df['tiempo_est_min'].median():.1f} min")

print("""
╔════════════════════╦══════════════════════════════╦══════════════════════════════╗
║ Dimensión          ║ Opción A: Laguerre            ║ Opción B: Isócronas OSMnx   ║
╠════════════════════╬══════════════════════════════╬══════════════════════════════╣
║ Pregunta central   ║ ¿Qué huecos persisten al     ║ ¿Cuántos minutos camina el  ║
║                    ║ ponderar capacidad           ║ paciente a la clínica más    ║
║                    ║ hospitalaria?                ║ cercana por calles reales?   ║
╠════════════════════╬══════════════════════════════╬══════════════════════════════╣
║ Métrica            ║ Euclidiana ponderada         ║ Tiempo en red vial real      ║
║ Diferencia por     ║ Tamaño de la clínica         ║ Estructura urbana (calles)   ║
║ Velocidad          ║ < 1 segundo (región completa)║ 30-120 s por hueco           ║
║ Escala             ║ Región completa              ║ Zonas focales (radio 2 km)   ║
║ Precisión física   ║ Media (ignora calles)        ║ Alta (calles reales)         ║
╠════════════════════╬══════════════════════════════╬══════════════════════════════╣
║ VENTAJAS           ║ Escala a 32 estados          ║ Realismo total               ║
║                    ║ Revela desiertos donde       ║ Perspectiva del paciente     ║
║                    ║ ni hospitales cubren         ║ Resultado en minutos reales  ║
║                    ║ Matemáticamente elegante     ║ Estándar de industria GIS    ║
╠════════════════════╬══════════════════════════════╬══════════════════════════════╣
║ DESVENTAJAS        ║ Asume movilidad en           ║ Lento para grandes áreas     ║
║                    ║ línea recta                  ║ Requiere OSM completo        ║
║                    ║ No detecta barreras viales   ║ Solo viable en zonas focales ║
╠════════════════════╬══════════════════════════════╬══════════════════════════════╣
║ Flujo recomendado  ║ PASO 1: filtra los peores    ║ PASO 2: valida y agrega      ║
║                    ║ desiertos a nivel estatal    ║ minutaje real a los críticos ║
╚════════════════════╩══════════════════════════════╩══════════════════════════════╝
""")

print("Archivos en outputs/figuras/:")
print("  scatter_accesibilidad.png         — todos los huecos habitados (CDMX | EDOMEX)")
print("  comparativa_tamano.png            — top 10 más grandes por ciudad")
print("  comparativa_distancia.png         — top 10 más lejanos por ciudad")
print("  mapas_accesibilidad_CDMX.png      — mapas OSM: top3 grandes + top3 lejanos CDMX")
print("  mapas_accesibilidad_EDOMEX.png    — mapas OSM: top3 grandes + top3 lejanos EDOMEX")
print("\nFase 2 completada.")
