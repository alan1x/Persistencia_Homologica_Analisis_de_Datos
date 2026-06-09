# %% [markdown]
# # 15a — Extracción de redes viales desde archivo PBF local
#
# Lee el archivo `Datos/OSM/mexico-*.osm.pbf` y extrae la red peatonal
# de CDMX y EDOMEX sin usar internet.
#
# Pipeline:
#   1. pyosmium lee el PBF filtrando por bbox de cada ciudad
#   2. Se construye un MultiDiGraph de NetworkX con atributos UTM
#   3. Se guarda como GraphML en `outputs/redes/`
#   4. (Opcional) se puede borrar el PBF después
#
# El resultado es idéntico en formato a lo que descargaría OSMnx,
# por lo que notebooks 15 y 16 funcionan sin cambios.

# %%
import sys, math
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import osmium
import networkx as nx
import osmnx as ox
import pandas as pd
from pyproj import Transformer

from lib import config

# Tipos de vía transitables a pie (red "walk" de OSMnx)
WALK_HIGHWAYS = {
    "footway", "pedestrian", "path", "track", "steps", "corridor",
    "residential", "living_street", "service", "unclassified",
    "secondary", "secondary_link", "tertiary", "tertiary_link",
    "primary", "primary_link", "road",
}

VELOCIDAD_KMH  = 4.5
VEL_M_MIN      = (VELOCIDAD_KMH * 1000) / 60
REDES_DIR      = config.OUTPUTS_DIR / "redes"
REDES_DIR.mkdir(parents=True, exist_ok=True)
_TR_GEO_UTM    = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en metros entre dos puntos WGS84."""
    R  = 6_371_000
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a  = math.sin(df/2)**2 + math.cos(f1)*math.cos(f2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# %% [markdown]
# ## 1. Handlers pyosmium — dos pasadas ligeras (bajo consumo de RAM)
#
# Pasada 1: solo guarda nodos dentro del bbox (~cientos de miles, no millones).
# Pasada 2: procesa vías sin locations=True; usa el dict de pasada 1.
# RAM total: ~200 MB en vez de 2-4 GB con locations=True.

# %%
class NodeCollector(osmium.SimpleHandler):
    """Pasada 1: recolecta coords de nodos dentro del bbox."""

    def __init__(self, bbox):
        super().__init__()
        self.bbox  = bbox   # (west, south, east, north)
        self.nodes = {}     # osm_id → (lat, lon)

    def node(self, n):
        if not n.location.valid():
            return
        lat, lon = n.location.lat, n.location.lon
        w, s, e, nrt = self.bbox
        if w <= lon <= e and s <= lat <= nrt:
            self.nodes[n.id] = (lat, lon)


class WayCollector(osmium.SimpleHandler):
    """Pasada 2: extrae aristas de vías walkables usando nodos de pasada 1."""

    def __init__(self, nodes):
        super().__init__()
        self.nodes = nodes  # dict de pasada 1
        self.edges = []     # (u, v, length_m)

    def way(self, w):
        if w.tags.get("highway", "") not in WALK_HIGHWAYS:
            return

        refs = [nd.ref for nd in w.nodes]

        # Descartar vías donde ningún nodo está en nuestro dict
        if not any(r in self.nodes for r in refs):
            return

        oneway = w.tags.get("oneway", "no") == "yes"
        for i in range(len(refs) - 1):
            u, v = refs[i], refs[i + 1]
            if u not in self.nodes or v not in self.nodes:
                continue   # arista en el borde del bbox, ignorar
            u_lat, u_lon = self.nodes[u]
            v_lat, v_lon = self.nodes[v]
            length = haversine(u_lat, u_lon, v_lat, v_lon)
            self.edges.append((u, v, length))
            if not oneway:
                self.edges.append((v, u, length))


def pbf_a_graphml(pbf_path, bbox, ruta_salida, region):
    """Extrae red peatonal del PBF en bbox y guarda como GraphML."""

    print(f"\n[{region}]  Pasada 1/2 — recolectando nodos en bbox...", flush=True)
    nc = NodeCollector(bbox)
    nc.apply_file(str(pbf_path))          # sin locations=True → bajo RAM
    print(f"  {len(nc.nodes):,} nodos en bbox", flush=True)

    print(f"  Pasada 2/2 — extrayendo vías walkables...", flush=True)
    wc = WayCollector(nc.nodes)
    wc.apply_file(str(pbf_path))          # sin locations=True
    print(f"  {len(wc.edges):,} aristas encontradas", flush=True)

    # Alias para claridad
    nodes_dict = nc.nodes
    edges_list  = wc.edges

    n_nodos = len(nodes_dict)
    n_aris  = len(edges_list)
    print(f"  Encontrados: {n_nodos:,} nodos  |  {n_aris:,} aristas", flush=True)

    if n_nodos == 0:
        print(f"  ✗ Sin datos — revisa el bbox o el archivo PBF.")
        return

    # Construir MultiDiGraph compatible con osmnx
    G = nx.MultiDiGraph()
    G.graph["crs"] = config.CRS_METROS   # UTM 14N

    # Agregar nodos con coordenadas UTM
    for osm_id, (lat, lon) in nodes_dict.items():
        x_utm, y_utm = _TR_GEO_UTM.transform(lon, lat)
        G.add_node(osm_id,
                   x=x_utm, y=y_utm,
                   lat=lat, lon=lon,
                   street_count=0)

    # Agregar aristas
    for u, v, length in edges_list:
        if u not in G.nodes or v not in G.nodes:
            continue
        time_min = length / VEL_M_MIN
        G.add_edge(u, v, length=length, time=time_min)

    # Remover nodos aislados (sin aristas)
    aislados = [n for n, d in G.degree() if d == 0]
    G.remove_nodes_from(aislados)

    # Quedarse solo con el componente fuertemente conexo más grande
    if len(G) > 0:
        comps = [c for c in nx.weakly_connected_components(G)]
        comp_mayor = max(comps, key=len)
        G = G.subgraph(comp_mayor).copy()

    print(f"  Grafo final: {len(G.nodes):,} nodos  |  {len(G.edges):,} aristas", flush=True)

    ox.save_graphml(G, filepath=str(ruta_salida))
    tam_mb = ruta_salida.stat().st_size / 1e6
    print(f"  ✓ Guardado: {ruta_salida.name}  ({tam_mb:.1f} MB)", flush=True)


# %% [markdown]
# ## 2. Localizar el archivo PBF

# %%
osm_dir = config.DATOS_DIR / "OSM"
pbfs    = sorted(osm_dir.glob("*.osm.pbf"))

if not pbfs:
    raise FileNotFoundError(f"No se encontró ningún .osm.pbf en {osm_dir}")

pbf_path = pbfs[0]
print(f"Archivo PBF: {pbf_path.name}  ({pbf_path.stat().st_size / 1e6:.0f} MB)")

# %% [markdown]
# ## 3. Calcular bbox de cada región a partir de los huecos reales

# %%
BUFFER = 0.08   # ~8 km de margen

bboxes = {}
for region in ["CDMX", "EDOMEX"]:
    ruta_hueco = config.INTERMEDIOS_DIR / f"huecos_score_{region}.parquet"
    if not ruta_hueco.exists():
        raise FileNotFoundError(
            f"No existe {ruta_hueco}. Ejecuta primero los notebooks 01-13."
        )
    df = pd.read_parquet(ruta_hueco)
    bboxes[region] = (
        df["lon"].min() - BUFFER,   # west
        df["lat"].min() - BUFFER,   # south
        df["lon"].max() + BUFFER,   # east
        df["lat"].max() + BUFFER,   # north
    )
    print(f"[{region}]  bbox = {bboxes[region]}")

# %% [markdown]
# ## 4. Extraer y guardar redes

# %%
print("\n" + "=" * 60, flush=True)
print("EXTRACCIÓN DE REDES VIALES DESDE PBF LOCAL", flush=True)
print("=" * 60, flush=True)

for region, bbox in bboxes.items():
    if region == "EDOMEX":
        print(f"\n[EDOMEX]  Omitido — se usará distancia euclidiana × 1.35", flush=True)
        continue
    ruta_out = REDES_DIR / f"red_{region}.graphml"

    if ruta_out.exists():
        print(f"\n[{region}]  Ya existe '{ruta_out.name}' — omitiendo.", flush=True)
        print(f"  Borra el archivo si quieres regenerarlo.", flush=True)
        continue

    pbf_a_graphml(pbf_path, bbox, ruta_out, region)

# %% [markdown]
# ## 5. (Opcional) Borrar el PBF de 600 MB

# %%
print("\n" + "=" * 60, flush=True)
redes_ok = all((REDES_DIR / f"red_{r}.graphml").exists() for r in ["CDMX", "EDOMEX"])

if redes_ok:
    print(f"Ambas redes están listas en {REDES_DIR}")
    print(f"\nEl archivo PBF ya no es necesario:")
    print(f"  {pbf_path}  ({pbf_path.stat().st_size / 1e6:.0f} MB)")
    print(f"\nPuedes borrarlo manualmente o ejecutar:")
    print(f"  Remove-Item '{pbf_path}'")
else:
    print("Alguna red no se generó — revisa los errores arriba.")
    print("El archivo PBF se conserva para un nuevo intento.")
