"""Geolocalización de huecos H₁: convierte ciclos topológicos a geometrías reales.

Flujo:
  ciclos (coords UTM metros) -> proyección inversa (lon/lat) -> círculo
  de cobertura en Folium -> HTML interactivo con popup de datos.
"""
import folium
import numpy as np
import pandas as pd
from pyproj import Transformer

from . import config

# Proyección inversa: UTM 14N (metros) -> WGS84 (lon/lat)
_TO_GEO = Transformer.from_crs(config.CRS_METROS, config.CRS_GEO, always_xy=True)


def _utm_a_latlon(x, y):
    """Convierte un punto UTM 14N (x, y) a (lat, lon) para Folium."""
    lon, lat = _TO_GEO.transform(x, y)
    return lat, lon


def ciclos_a_geodataframe(ciclos):
    """Convierte la lista de ciclos a un DataFrame con columnas geográficas.

    Columnas resultantes:
        lat, lon   : centroide del ciclo en WGS84
        radio_m    : radio aproximado = persistencia / 2  (estimación conservadora)
        birth_m    : radio en el que nació el hueco
        death_m    : radio en el que murió
        pers_m     : persistencia en metros
    """
    rows = []
    for c in ciclos:
        cx, cy = c["centroide"]
        lat, lon = _utm_a_latlon(cx, cy)
        rows.append({
            "lat": lat,
            "lon": lon,
            "radio_m": c["pers"] / 2,
            "birth_m": c["birth"],
            "death_m": c["death"],
            "pers_m": c["pers"],
        })
    return pd.DataFrame(rows)


def mapa_huecos(df_puntos, ciclos, region, top_n=None):
    """Genera un mapa Folium con:
       - Puntos gris claro: unidades de salud (muestra aleatoria si >5000)
       - Círculos rojos semitransparentes: huecos H₁ (radio proporcional a persistencia)
       - Popup en cada círculo: birth, death, persistencia en metros

    Parámetros
    ----------
    df_puntos : DataFrame con columnas lat/lon (WGS84) de las unidades de salud.
                Si no existen, se derivan de x/y UTM.
    ciclos    : lista devuelta por tda.ciclos_H1()
    region    : str, para el título del mapa
    top_n     : int o None — si se especifica, dibuja solo los N huecos más persistentes

    Devuelve el objeto folium.Map (llama a .save() para exportar).
    """
    if len(ciclos) == 0:
        raise ValueError(f"No hay ciclos para {region}. Prueba con min_persistencia menor.")

    seleccionados = ciclos if top_n is None else ciclos[:top_n]
    gdf = ciclos_a_geodataframe(seleccionados)

    # Centro del mapa: centroide de todos los huecos
    centro = [gdf["lat"].mean(), gdf["lon"].mean()]
    mapa = folium.Map(location=centro, zoom_start=10, tiles="CartoDB positron")

    # --- Capa 1: unidades de salud (muestra para no saturar el HTML) ---
    muestra = df_puntos
    if len(df_puntos) > 5000:
        muestra = df_puntos.sample(5000, random_state=42)

    # Determinar lat/lon: puede venir directo o hay que derivar de x, y
    if "latitud" in muestra.columns and "longitud" in muestra.columns:
        lats = muestra["latitud"].values
        lons = muestra["longitud"].values
    else:
        lons_arr, lats_arr = _TO_GEO.transform(
            muestra["x"].values, muestra["y"].values
        )
        lats, lons = lats_arr, lons_arr

    puntos_layer = folium.FeatureGroup(name="Unidades de salud", show=True)
    for lat, lon in zip(lats, lons):
        folium.CircleMarker(
            location=[lat, lon],
            radius=2,
            color="#555555",
            fill=True,
            fill_opacity=0.3,
            weight=0,
        ).add_to(puntos_layer)
    puntos_layer.add_to(mapa)

    # --- Capa 2: huecos H₁ ---
    huecos_layer = folium.FeatureGroup(name="Huecos H₁ (zonas sin cobertura)", show=True)
    max_pers = gdf["pers_m"].max()

    for _, row in gdf.iterrows():
        # Opacidad proporcional a la persistencia relativa
        opacidad = 0.15 + 0.50 * (row["pers_m"] / max_pers)
        popup_html = (
            f"<b>Hueco H₁</b><br>"
            f"Radio aprox: <b>{row['radio_m']:.0f} m</b><br>"
            f"Persistencia: <b>{row['pers_m']:.0f} m</b><br>"
            f"Nace en: {row['birth_m']:.0f} m &nbsp;|&nbsp; Muere en: {row['death_m']:.0f} m"
        )
        folium.Circle(
            location=[row["lat"], row["lon"]],
            radius=row["radio_m"],
            color="#d62728",
            fill=True,
            fill_opacity=opacidad,
            weight=1.5,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"Persistencia: {row['pers_m']:.0f} m",
        ).add_to(huecos_layer)
    huecos_layer.add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)

    titulo_html = (
        f'<div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);'
        f'z-index:1000;background:white;padding:6px 14px;border-radius:6px;'
        f'box-shadow:0 2px 6px rgba(0,0,0,.3);font-family:sans-serif;">'
        f'<b>{region}</b> — Huecos H₁ de cobertura de salud '
        f'({len(seleccionados)} ciclos persistentes)</div>'
    )
    mapa.get_root().html.add_child(folium.Element(titulo_html))

    return mapa


def guardar_mapa(mapa, region):
    """Guarda el mapa en outputs/figuras/huecos_{region}.html."""
    ruta = config.FIGURAS_DIR / f"huecos_{region}.html"
    mapa.save(str(ruta))
    return ruta
