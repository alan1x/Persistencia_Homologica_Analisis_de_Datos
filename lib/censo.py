"""Carga, cruce y análisis de datos del Censo 2020 (INEGI) a nivel AGEB.

Flujo principal:
  1. Cargar shapefile de AGEBs → GeoDataFrame con polígonos
  2. Cargar CSV censal → DataFrame con indicadores demográficos por AGEB
  3. Unir ambos por CVEGEO → GeoDataFrame enriquecido
  4. Cruce espacial (spatial join) con huecos topológicos H₁
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Point, MultiPoint

from . import config

# ---------------------------------------------------------------------------
# Rutas de datos censales
# ---------------------------------------------------------------------------
CENSO_DIR = config.DATOS_DIR / "Censo"
GEO_DIR = config.DATOS_DIR / "Geoestadistico"

# Archivos por región
CENSO_CSV = {
    "CDMX": CENSO_DIR / "ageb_mza_urbana_09_cpv2020" / "conjunto_de_datos"
             / "conjunto_de_datos_ageb_urbana_09_cpv2020.csv",
    "EDOMEX": CENSO_DIR / "ageb_mza_urbana_15_cpv2020" / "conjunto_de_datos"
              / "conjunto_de_datos_ageb_urbana_15_cpv2020.csv",
}

AGEB_SHP = {
    "CDMX": GEO_DIR / "CDMX" / "conjunto_de_datos" / "09a.shp",
    "EDOMEX": GEO_DIR / "EDOMEX" / "conjunto_de_datos" / "15a.shp",
}

# Columnas del Censo que nos interesan para el análisis de cobertura de salud
COLS_CENSO = [
    "POBTOT",       # Población total
    "POBFEM",       # Población femenina
    "POBMAS",       # Población masculina
    "P_0A2",        # Población de 0 a 2 años
    "P_60YMAS",     # Población de 60 años y más
    "PSINDER",      # Población SIN afiliación a servicios de salud
    "PDER_SS",      # Población CON afiliación a servicios de salud
    "PDER_IMSS",    # Afiliada al IMSS
    "PDER_ISTE",    # Afiliada al ISSSTE
    "PDER_SEGP",    # Afiliada al INSABI / Salud para el Bienestar
    "PDER_IMSSB",   # Afiliada al IMSS-Bienestar
    "PAFIL_IPRIV",  # Afiliada a institución privada
    "GRAPROES",     # Grado promedio de escolaridad
    "PEA",          # Población económicamente activa
    "PDESOCUP",     # Población desocupada
    "VIVTOT",       # Total de viviendas
    "TVIVHAB",      # Viviendas particulares habitadas
]

# Transformer para convertir coordenadas UTM → WGS84 (para los centroides de huecos)
_TO_GEO = Transformer.from_crs(config.CRS_METROS, config.CRS_GEO, always_xy=True)


# ---------------------------------------------------------------------------
# 1. Carga de datos
# ---------------------------------------------------------------------------

def cargar_shapefile_ageb(region):
    """Carga el shapefile de AGEBs urbanas y lo reproyecta a WGS84 (EPSG:4326).

    Devuelve un GeoDataFrame con columna 'CVEGEO' como identificador único
    y geometría de polígonos.
    """
    ruta = AGEB_SHP[region]
    gdf = gpd.read_file(str(ruta))
    # Reproyectar a WGS84 para compatibilidad con Folium y con las coordenadas
    # del Censo (que no tienen CRS propio, pero el shape sí)
    gdf = gdf.to_crs(epsg=4326)
    return gdf


def cargar_censo_ageb(region):
    """Carga el CSV censal y filtra solo filas a nivel AGEB (no manzana ni totales).

    Construye la clave CVEGEO de 13 caracteres para hacer join con el shapefile.
    Las columnas numéricas que contienen '*' (confidencialidad estadística)
    se convierten a NaN.
    """
    ruta = CENSO_CSV[region]
    df = pd.read_csv(str(ruta), encoding="utf-8-sig", low_memory=False)

    # Filtrar solo registros a nivel AGEB:
    #   MZA == 0  → no es manzana (es agregado)
    #   AGEB != '0000'  → no es el total del municipio/localidad
    df = df[
        (df["MZA"] == 0)
        & (df["AGEB"].astype(str) != "0000")
    ].copy()

    # Construir CVEGEO: ENTIDAD(2) + MUN(3) + LOC(4) + AGEB(4) = 13 caracteres
    df["CVEGEO"] = (
        df["ENTIDAD"].astype(str).str.zfill(2)
        + df["MUN"].astype(str).str.zfill(3)
        + df["LOC"].astype(str).str.zfill(4)
        + df["AGEB"].astype(str).str.zfill(4)
    )

    # Limpiar columnas numéricas: '*' → NaN (confidencialidad INEGI)
    cols_interes = [c for c in COLS_CENSO if c in df.columns]
    for col in cols_interes:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def construir_ageb_enriquecido(region):
    """Une el shapefile de AGEBs con los datos censales por CVEGEO.

    Devuelve un GeoDataFrame con geometría + indicadores demográficos,
    proyectado a WGS84.
    """
    gdf = cargar_shapefile_ageb(region)
    censo = cargar_censo_ageb(region)

    # Seleccionar columnas para el merge
    cols_merge = ["CVEGEO"] + [c for c in COLS_CENSO if c in censo.columns]
    censo_slim = censo[cols_merge].copy()

    # Merge por CVEGEO
    gdf_enriq = gdf.merge(censo_slim, on="CVEGEO", how="left")

    # Calcular métricas derivadas
    gdf_enriq["pct_sin_salud"] = np.where(
        gdf_enriq["POBTOT"] > 0,
        (gdf_enriq["PSINDER"] / gdf_enriq["POBTOT"]) * 100,
        np.nan,
    )

    n_antes = len(gdf)
    n_match = gdf_enriq["POBTOT"].notna().sum()
    print(f"  [{region}] AGEBs en shapefile: {n_antes:,}")
    print(f"  [{region}] AGEBs con datos censales: {n_match:,}")
    print(f"  [{region}] Match rate: {n_match / n_antes * 100:.1f}%")

    return gdf_enriq


# ---------------------------------------------------------------------------
# 2. Cruce espacial con huecos topológicos H₁
# ---------------------------------------------------------------------------

def _hueco_a_geometria(ciclo, buffer_factor=0.5):
    """Convierte un ciclo H₁ a un punto WGS84 con un buffer circular (radio en grados aprox).

    El radio del buffer se estima como persistencia/2 en metros,
    convertido a grados de forma aproximada (1° ≈ 111 km en latitud).
    """
    cx, cy = ciclo["centroide"]
    lon, lat = _TO_GEO.transform(cx, cy)
    radio_m = ciclo["pers"] * buffer_factor
    # Conversión aproximada: grados ≈ metros / 111320
    radio_deg = radio_m / 111320
    punto = Point(lon, lat)
    return punto, punto.buffer(radio_deg), lat, lon, radio_m


def cruzar_huecos_con_censo(ciclos, gdf_ageb, region, min_persistencia=200.0):
    """Para cada hueco H₁, encuentra las AGEBs que intersectan su área de influencia
    y agrega la población total, la población sin seguro, etc.

    Devuelve un DataFrame con un registro por hueco, enriquecido con:
      - pob_afectada: suma de POBTOT de las AGEBs que caen dentro del hueco
      - pob_sin_salud: suma de PSINDER de esas AGEBs
      - pct_sin_salud_prom: promedio ponderado del % sin salud
      - n_agebs: número de AGEBs intersectadas
      - pob_60_mas: población adulta mayor afectada
      - graproes_prom: grado promedio de escolaridad (promedio ponderado)
    """
    registros = []

    for i, ciclo in enumerate(ciclos):
        if ciclo["pers"] < min_persistencia:
            continue

        punto, area, lat, lon, radio_m = _hueco_a_geometria(ciclo)

        # Spatial join: encontrar AGEBs que intersectan el área del hueco
        area_gdf = gpd.GeoDataFrame(
            [{"geometry": area, "hueco_id": i}],
            crs="EPSG:4326",
        )
        intersectadas = gpd.sjoin(
            gdf_ageb, area_gdf, how="inner", predicate="intersects"
        )

        if len(intersectadas) == 0:
            # No hay AGEBs en esta zona (posiblemente zona rural sin AGEB urbana)
            registros.append({
                "hueco_id": i,
                "lat": lat,
                "lon": lon,
                "pers_m": ciclo["pers"],
                "birth_m": ciclo["birth"],
                "death_m": ciclo["death"],
                "radio_m": radio_m,
                "pob_afectada": 0,
                "pob_sin_salud": 0,
                "pct_sin_salud_prom": np.nan,
                "n_agebs": 0,
                "pob_60_mas": 0,
                "graproes_prom": np.nan,
                "pea_total": 0,
            })
            continue

        # Agregar indicadores
        pob_total = intersectadas["POBTOT"].sum()
        pob_sin = intersectadas["PSINDER"].sum()
        pob_60 = intersectadas["P_60YMAS"].sum() if "P_60YMAS" in intersectadas.columns else 0

        # Promedio ponderado de escolaridad
        mask_esc = intersectadas["GRAPROES"].notna() & (intersectadas["POBTOT"] > 0)
        if mask_esc.any():
            pesos = intersectadas.loc[mask_esc, "POBTOT"]
            graproes = (intersectadas.loc[mask_esc, "GRAPROES"] * pesos).sum() / pesos.sum()
        else:
            graproes = np.nan

        pea = intersectadas["PEA"].sum() if "PEA" in intersectadas.columns else 0

        registros.append({
            "hueco_id": i,
            "lat": lat,
            "lon": lon,
            "pers_m": ciclo["pers"],
            "birth_m": ciclo["birth"],
            "death_m": ciclo["death"],
            "radio_m": radio_m,
            "pob_afectada": int(pob_total) if pd.notna(pob_total) else 0,
            "pob_sin_salud": int(pob_sin) if pd.notna(pob_sin) else 0,
            "pct_sin_salud_prom": (pob_sin / pob_total * 100) if pob_total > 0 else np.nan,
            "n_agebs": len(intersectadas),
            "pob_60_mas": int(pob_60) if pd.notna(pob_60) else 0,
            "graproes_prom": round(graproes, 2) if pd.notna(graproes) else np.nan,
            "pea_total": int(pea) if pd.notna(pea) else 0,
        })

    df = pd.DataFrame(registros)
    df = df.sort_values("pob_afectada", ascending=False).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 3. Índice de prioridad compuesto
# ---------------------------------------------------------------------------

def calcular_indice_prioridad(df_cruce):
    """Calcula un índice de prioridad compuesto para cada hueco.

    El índice combina:
      - Persistencia topológica (tamaño del hueco)
      - Población afectada (demanda)
      - % de población sin seguro médico (vulnerabilidad)
      - Población adulta mayor (vulnerabilidad etaria)

    Cada componente se normaliza a [0, 1] y se pondera:
      - Persistencia:   0.25
      - Población:      0.30
      - % Sin salud:    0.25
      - Pob. 60+:       0.20

    Devuelve el DataFrame con columna 'indice_prioridad' de 0 a 100.
    """
    df = df_cruce.copy()

    # Solo calcular para huecos con datos válidos
    def _norm(col):
        s = df[col]
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series(0.5, index=df.index)
        return (s - mn) / (mx - mn)

    df["_n_pers"] = _norm("pers_m")
    df["_n_pob"] = _norm("pob_afectada")
    df["_n_pct"] = df["pct_sin_salud_prom"].fillna(0) / 100
    df["_n_60"] = _norm("pob_60_mas")

    df["indice_prioridad"] = (
        0.25 * df["_n_pers"]
        + 0.30 * df["_n_pob"]
        + 0.25 * df["_n_pct"]
        + 0.20 * df["_n_60"]
    ) * 100

    # Clasificar en niveles
    df["nivel_prioridad"] = pd.cut(
        df["indice_prioridad"],
        bins=[-1, 25, 50, 75, 100],
        labels=["Bajo", "Moderado", "Alto", "Crítico"],
    )

    # Limpiar columnas temporales
    df = df.drop(columns=[c for c in df.columns if c.startswith("_n_")])

    return df.sort_values("indice_prioridad", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. Visualización: mapa enriquecido con datos censales
# ---------------------------------------------------------------------------

def mapa_huecos_censales(df_prioridad, gdf_ageb, df_puntos, region):
    """Genera un mapa Folium con huecos coloreados por nivel de prioridad
    y AGEBs sombreadas por % de población sin seguro médico.

    Capas:
      1. Coropleta de AGEBs: color por pct_sin_salud
      2. Unidades de salud: puntos grises
      3. Huecos topológicos: círculos coloreados por prioridad con popup detallado
    """
    import folium
    from branca.colormap import LinearColormap

    if len(df_prioridad) == 0:
        raise ValueError(f"No hay huecos para {region}")

    centro = [df_prioridad["lat"].mean(), df_prioridad["lon"].mean()]
    mapa = folium.Map(location=centro, zoom_start=10, tiles="CartoDB positron")

    # --- Capa 1: coropleta de AGEBs por % sin salud ---
    gdf_plot = gdf_ageb[gdf_ageb["pct_sin_salud"].notna()].copy()
    if len(gdf_plot) > 0:
        colormap = LinearColormap(
            colors=["#2166ac", "#67a9cf", "#fddbc7", "#ef8a62", "#b2182b"],
            vmin=0, vmax=min(gdf_plot["pct_sin_salud"].quantile(0.95), 100),
            caption="% Población sin seguro médico",
        )
        ageb_layer = folium.FeatureGroup(name="AGEBs: % sin salud", show=False)
        for _, row in gdf_plot.iterrows():
            if row.geometry is None:
                continue
            geojson = folium.GeoJson(
                row.geometry.__geo_interface__,
                style_function=lambda _, color=colormap(row["pct_sin_salud"]): {
                    "fillColor": color,
                    "color": "#333",
                    "weight": 0.3,
                    "fillOpacity": 0.5,
                },
                tooltip=f"AGEB {row['CVEGEO']}: {row['pct_sin_salud']:.1f}% sin salud",
            )
            geojson.add_to(ageb_layer)
        ageb_layer.add_to(mapa)
        colormap.add_to(mapa)

    # --- Capa 2: unidades de salud ---
    _to_geo = Transformer.from_crs(config.CRS_METROS, config.CRS_GEO, always_xy=True)
    muestra = df_puntos.sample(min(5000, len(df_puntos)), random_state=42)
    puntos_layer = folium.FeatureGroup(name="Unidades de salud", show=True)
    if "latitud" in muestra.columns:
        coords = list(zip(muestra["latitud"], muestra["longitud"]))
    else:
        lons, lats = _to_geo.transform(muestra["x"].values, muestra["y"].values)
        coords = list(zip(lats, lons))
    for lat, lon in coords:
        folium.CircleMarker(
            location=[lat, lon], radius=1.5,
            color="#555555", fill=True, fill_opacity=0.3, weight=0,
        ).add_to(puntos_layer)
    puntos_layer.add_to(mapa)

    # --- Capa 3: huecos por prioridad ---
    colores_prioridad = {
        "Crítico": "#b2182b",
        "Alto": "#ef8a62",
        "Moderado": "#fddbc7",
        "Bajo": "#67a9cf",
    }

    huecos_layer = folium.FeatureGroup(
        name="Huecos H₁ (prioridad censal)", show=True
    )
    for _, row in df_prioridad.iterrows():
        nivel = str(row.get("nivel_prioridad", "Moderado"))
        color = colores_prioridad.get(nivel, "#999")
        popup_html = (
            f"<b>Hueco #{int(row['hueco_id'])}</b><br>"
            f"<b>Prioridad: {nivel} ({row['indice_prioridad']:.0f}/100)</b><br>"
            f"<hr style='margin:4px 0'>"
            f"Persistencia: <b>{row['pers_m']:.0f} m</b><br>"
            f"Radio aprox: <b>{row['radio_m']:.0f} m</b><br>"
            f"<hr style='margin:4px 0'>"
            f"<b>Datos censales (AGEBs intersectadas: {int(row['n_agebs'])})</b><br>"
            f"Población afectada: <b>{int(row['pob_afectada']):,}</b><br>"
            f"Sin seguro médico: <b>{int(row['pob_sin_salud']):,}</b>"
            f" ({row['pct_sin_salud_prom']:.1f}%)<br>"
            f"Adultos mayores (60+): <b>{int(row['pob_60_mas']):,}</b><br>"
            f"Escolaridad promedio: <b>{row['graproes_prom']}</b> años<br>"
        )

        opacidad = 0.3 + 0.4 * (row["indice_prioridad"] / 100)
        folium.Circle(
            location=[row["lat"], row["lon"]],
            radius=row["radio_m"],
            color=color,
            fill=True,
            fill_opacity=opacidad,
            weight=2,
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f"{nivel}: {int(row['pob_afectada']):,} personas, {row['pers_m']:.0f}m",
        ).add_to(huecos_layer)
    huecos_layer.add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)

    titulo_html = (
        f'<div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);'
        f'z-index:1000;background:white;padding:8px 16px;border-radius:8px;'
        f'box-shadow:0 2px 8px rgba(0,0,0,.3);font-family:sans-serif;font-size:14px;">'
        f'<b>{region}</b> — Huecos de salud × Censo 2020 '
        f'({len(df_prioridad)} huecos, prioridad censal)'
        f'</div>'
    )
    mapa.get_root().html.add_child(folium.Element(titulo_html))

    return mapa


def guardar_mapa_censal(mapa, region):
    """Guarda el mapa enriquecido en outputs/figuras/huecos_censal_{region}.html."""
    ruta = config.FIGURAS_DIR / f"huecos_censal_{region}.html"
    mapa.save(str(ruta))
    print(f"  Mapa guardado: {ruta}")
    return ruta
