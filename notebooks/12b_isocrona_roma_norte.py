"""Regenera outputs/figuras/isocronas_roma_norte.png con concave_hull."""
import matplotlib
matplotlib.use("Agg")
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import geopandas as gpd
import matplotlib.pyplot as plt
import osmnx as ox

from lib import config, geo_network

# Coordenadas de una clínica mediana representativa en Roma Norte
LAT_CLINICA =  19.4176
LON_CLINICA = -99.1594
RADIO_M     = 2000       # radio de descarga de la red OSM
TIEMPO_LIM  = 15.0       # minutos

print("Descargando red peatonal de Roma Norte desde OSM...", flush=True)
G = geo_network.descargar_red_punto(LAT_CLINICA, LON_CLINICA, radio_m=RADIO_M)
print(f"  Red: {len(G.nodes)} nodos, {len(G.edges)} aristas", flush=True)

# Nodo más cercano a la clínica
nodo_origen = ox.nearest_nodes(G, LON_CLINICA, LAT_CLINICA)

# Isócrona con concave_hull (función corregida por Alan)
iso = geo_network.isocrona_desde_nodo(G, nodo_origen, tiempo_minutos=TIEMPO_LIM)
tipo = type(iso).__name__ if iso is not None else "None"
print(f"  Isócrona generada: {tipo}", flush=True)

# --- Figura ---
fig, ax = plt.subplots(figsize=(10, 10))
fig.patch.set_facecolor("white")

# Red de calles en gris claro
ox.plot_graph(G, ax=ax, show=False, close=False,
              node_size=0, edge_color="#cccccc", edge_linewidth=0.8,
              bgcolor="white")

# Isócrona (concave hull)
if iso is not None:
    gpd.GeoSeries([iso], crs=G.graph["crs"]).plot(
        ax=ax, color="#4393c3", alpha=0.45, zorder=3
    )
    gpd.GeoSeries([iso], crs=G.graph["crs"]).plot(
        ax=ax, facecolor="none", edgecolor="#4393c3",
        linewidth=2.5, zorder=4
    )

# Clínica
ax.plot(*ox.projection.project_geometry(
    __import__("shapely.geometry", fromlist=["Point"]).Point(LON_CLINICA, LAT_CLINICA),
    crs="EPSG:4326", to_crs=G.graph["crs"]
)[0].coords[0], "o",
    color="#d6604d", markersize=14, zorder=8,
    markeredgecolor="white", markeredgewidth=2, label="Clínica")

ax.set_title(
    "Isócrona de 15 min caminando — Colonia Roma Norte\n"
    "La forma refleja la red vial peatonal real (concave hull), "
    "no un disco euclidiano",
    fontsize=13, fontweight="bold"
)
ax.legend(fontsize=11)
ax.set_axis_on()
ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

ruta = config.FIGURAS_DIR / "isocronas_roma_norte.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"✓ {ruta}", flush=True)
