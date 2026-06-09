# %% [markdown]
# # 15a — Descarga única de redes viales CDMX / EDOMEX
#
# Descarga la red peatonal completa de cada ciudad UNA SOLA VEZ
# desde OpenStreetMap y la guarda en `outputs/redes/`.
#
# Ejecutar este script requiere internet. Una vez guardadas, los
# notebooks 15 y posteriores leen los archivos locales sin conexión.
#
# Tiempo estimado: 2-5 min por ciudad (depende de la conexión).

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import osmnx as ox
import pandas as pd
from pyproj import Transformer

from lib import config

BUFFER_DEG  = 0.08   # ~8 km de margen alrededor de los huecos
REDES_DIR   = config.OUTPUTS_DIR / "redes"
REDES_DIR.mkdir(parents=True, exist_ok=True)

# Servidores Overpass alternativos — se intentan en orden si el principal falla
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.karte.io/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

ox.settings.timeout = 60   # máximo 60s de espera por petición

print("=" * 60)
print("DESCARGA DE REDES VIALES — CDMX y EDOMEX")
print("=" * 60)
print(f"Guardando en: {REDES_DIR}\n")

for region in ["CDMX", "EDOMEX"]:
    ruta_graphml = REDES_DIR / f"red_{region}.graphml"

    if ruta_graphml.exists():
        print(f"[{region}]  Ya existe '{ruta_graphml.name}' — omitiendo descarga.")
        print(f"  Elimina el archivo si quieres volver a descargarlo.\n")
        continue

    # Calcular bbox real de los huecos con buffer
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_score_{region}.parquet")
    north = df["lat"].max() + BUFFER_DEG
    south = df["lat"].min() - BUFFER_DEG
    east  = df["lon"].max() + BUFFER_DEG
    west  = df["lon"].min() - BUFFER_DEG

    print(f"[{region}]  bbox: lat [{south:.3f}, {north:.3f}]  lon [{west:.3f}, {east:.3f}]")

    G_proj = None
    for endpoint in OVERPASS_ENDPOINTS:
        ox.settings.overpass_url = endpoint
        print(f"  Intentando servidor: {endpoint} ...")
        try:
            G = ox.graph_from_bbox(
                bbox=(north, south, east, west),
                network_type="walk",
            )
            G_proj = ox.project_graph(G)
            print(f"  ✓ Descarga exitosa desde {endpoint}")
            break
        except Exception as e:
            print(f"  ✗ Falló ({type(e).__name__}) — probando siguiente servidor...")

    if G_proj is None:
        print(f"  ✗ Todos los servidores fallaron para {region}. Intenta más tarde.")
        continue

    # Agregar atributo 'time' (minutos) a cada arista
    vel_m_min = (4.5 * 1000) / 60
    for _, _, _, data in G_proj.edges(data=True, keys=True):
        data["time"] = data["length"] / vel_m_min

    ox.save_graphml(G_proj, filepath=str(ruta_graphml))

    tam_mb = ruta_graphml.stat().st_size / 1e6
    print(f"  ✓ {len(G_proj.nodes):,} nodos  |  {len(G_proj.edges):,} aristas")
    print(f"  ✓ Guardado: {ruta_graphml.name}  ({tam_mb:.1f} MB)\n")

print("Listo. Los notebooks 15+ usarán estos archivos locales.")
print("No se necesita internet para ejecuciones posteriores.")
