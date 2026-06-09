"""Módulo para análisis de topología de redes viales e isócronas (Fase 2 - Opción B)."""
import warnings
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import osmnx as ox
import networkx as nx
from pyproj import Transformer

from . import config

warnings.filterwarnings("ignore")

VELOCIDAD_KMH = 4.5
_METROS_POR_MIN = (VELOCIDAD_KMH * 1000) / 60


def _agregar_tiempos(G, velocidad_kmh=VELOCIDAD_KMH):
    """Agrega atributo 'time' (minutos) a todas las aristas del grafo."""
    mpm = (velocidad_kmh * 1000) / 60
    for _, _, _, data in G.edges(data=True, keys=True):
        data["time"] = data["length"] / mpm


def descargar_red(lugar, network_type="walk"):
    """Descarga red vial de OSM para una zona por nombre de lugar."""
    ox.settings.log_console = False
    ox.settings.use_cache = True
    G = ox.graph_from_place(lugar, network_type=network_type)
    return ox.project_graph(G)


def descargar_red_punto(lat, lon, radio_m=2000, network_type="walk"):
    """Descarga red vial de OSM centrada en un punto lat/lon y radio en metros.

    Usa caché de osmnx para evitar descargas repetidas.
    """
    ox.settings.log_console = False
    ox.settings.use_cache = True
    G = ox.graph_from_point((lat, lon), dist=radio_m, network_type=network_type)
    return ox.project_graph(G)


def accesibilidad_desde_punto(G_proj, lat_origen, lon_origen, df_clinicas,
                               velocidad_kmh=VELOCIDAD_KMH, top_n=15):
    """Calcula tiempo de caminata desde el centroide de un hueco a la clínica más cercana.

    Perspectiva del paciente: desde dentro del hueco ¿cuántos minutos tarda en llegar
    a la primera atención médica usando calles reales?

    Args:
        G_proj: Grafo OSMnx proyectado (resultado de descargar_red_punto).
        lat_origen, lon_origen: Centroide del hueco en WGS84.
        df_clinicas: DataFrame con 'latitud'+'longitud' (WGS84) o 'x'+'y' (UTM 32614).
        top_n: Cuántas clínicas evaluar (las más cercanas en línea recta).

    Returns:
        dict con tiempo_min, distancia_m, coordenadas proyectadas para visualización.
    """
    _agregar_tiempos(G_proj, velocidad_kmh)

    crs_grafo = G_proj.graph["crs"]
    tr_a_grafo = Transformer.from_crs("EPSG:4326", crs_grafo, always_xy=True)

    x_orig, y_orig = tr_a_grafo.transform(lon_origen, lat_origen)

    try:
        nodo_origen = ox.distance.nearest_nodes(G_proj, x_orig, y_orig)
    except Exception:
        return {"tiempo_min": None, "distancia_m": None, "clinica_idx": None,
                "x_orig": x_orig, "y_orig": y_orig}

    # Obtener lat/lon de clínicas
    if "latitud" in df_clinicas.columns and "longitud" in df_clinicas.columns:
        lats_c = df_clinicas["latitud"].values
        lons_c = df_clinicas["longitud"].values
    else:
        tr_utm_geo = Transformer.from_crs(config.CRS_METROS, "EPSG:4326", always_xy=True)
        lons_c, lats_c = tr_utm_geo.transform(
            df_clinicas["x"].values, df_clinicas["y"].values
        )

    # Tomar las top_n más cercanas en línea recta para reducir costo
    dist_eucl = np.hypot(lats_c - lat_origen, lons_c - lon_origen)
    idx_top = np.argsort(dist_eucl)[:top_n]
    lats_c, lons_c = lats_c[idx_top], lons_c[idx_top]

    xs_c, ys_c = tr_a_grafo.transform(lons_c, lats_c)

    try:
        nodos_clinicas = ox.distance.nearest_nodes(G_proj, xs_c, ys_c)
    except Exception:
        return {"tiempo_min": None, "distancia_m": None, "clinica_idx": None,
                "x_orig": x_orig, "y_orig": y_orig,
                "xs_clinicas": xs_c, "ys_clinicas": ys_c}

    mejor_tiempo = float("inf")
    mejor_dist = None
    mejor_idx = None

    for i, nodo_c in enumerate(nodos_clinicas):
        try:
            t = nx.shortest_path_length(G_proj, nodo_origen, nodo_c, weight="time")
            if t < mejor_tiempo:
                mejor_tiempo = t
                mejor_dist = nx.shortest_path_length(
                    G_proj, nodo_origen, nodo_c, weight="length"
                )
                mejor_idx = idx_top[i]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

    if mejor_tiempo == float("inf"):
        return {"tiempo_min": None, "distancia_m": None, "clinica_idx": None,
                "nodo_origen": nodo_origen, "xs_clinicas": xs_c, "ys_clinicas": ys_c,
                "x_orig": x_orig, "y_orig": y_orig}

    return {
        "tiempo_min": round(mejor_tiempo, 1),
        "distancia_m": round(mejor_dist),
        "clinica_idx": mejor_idx,
        "nodo_origen": nodo_origen,
        "xs_clinicas": xs_c,
        "ys_clinicas": ys_c,
        "x_orig": x_orig,
        "y_orig": y_orig,
    }


def isocrona_desde_nodo(G_proj, nodo, tiempo_minutos=15, velocidad_kmh=VELOCIDAD_KMH):
    """Polígono de accesibilidad desde un nodo: qué alcanza un paciente en tiempo_minutos.

    Perspectiva del paciente (desde dentro del hueco), no de la clínica.
    """
    _agregar_tiempos(G_proj, velocidad_kmh)
    try:
        sub_g = nx.ego_graph(G_proj, nodo, radius=tiempo_minutos, distance="time")
        puntos = [Point(d["x"], d["y"]) for _, d in sub_g.nodes(data=True)]
        if len(puntos) >= 3:
            return gpd.GeoSeries(puntos).unary_union.convex_hull
    except Exception:
        pass
    return None


def calcular_isocronas(G_proj, gdf_puntos, tiempo_minutos=15, velocidad_kmh=VELOCIDAD_KMH):
    """Isócronas desde un conjunto de clínicas (perspectiva de cobertura desde clínica)."""
    _agregar_tiempos(G_proj, velocidad_kmh)
    x = gdf_puntos.geometry.x.values
    y = gdf_puntos.geometry.y.values
    nodos = ox.distance.nearest_nodes(G_proj, x, y)

    isocronas = []
    for nodo in nodos:
        iso = isocrona_desde_nodo(G_proj, nodo, tiempo_minutos, velocidad_kmh)
        isocronas.append(iso)

    gdf = gdf_puntos.copy()
    gdf["isocrona"] = isocronas
    gdf = gdf.dropna(subset=["isocrona"]).copy()
    return gdf.set_geometry("isocrona")


def calcular_desiertos_red(G_proj, gdf_isocronas):
    """Zonas dentro de la red que NO son alcanzables por ninguna isócrona."""
    cobertura = gdf_isocronas.unary_union
    nodes_gdf = ox.graph_to_gdfs(G_proj, edges=False)
    limite = nodes_gdf.unary_union.convex_hull
    desiertos = limite.difference(cobertura)

    if desiertos.geom_type == "MultiPolygon":
        gdf = gpd.GeoDataFrame(geometry=list(desiertos.geoms), crs=gdf_isocronas.crs)
    else:
        gdf = gpd.GeoDataFrame(geometry=[desiertos], crs=gdf_isocronas.crs)

    gdf["area_km2"] = gdf.geometry.area / 1e6
    return (
        gdf[gdf["area_km2"] > 0.05]
        .sort_values("area_km2", ascending=False)
        .reset_index(drop=True)
    )
