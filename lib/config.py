"""Configuración central del proyecto: rutas, columnas, parámetros geográficos."""
from pathlib import Path

# Raíz del proyecto (carpeta Proyecto/), asumiendo lib/ dentro de src/
SRC_DIR = Path(__file__).resolve().parent.parent
PROYECTO_DIR = SRC_DIR.parent
DATOS_DIR = PROYECTO_DIR / "Datos"
OUTPUTS_DIR = SRC_DIR / "outputs"
FIGURAS_DIR = OUTPUTS_DIR / "figuras"
INTERMEDIOS_DIR = OUTPUTS_DIR / "intermedios"

# Archivos DENUE por región. EDOMEX viene partido en 2.
ARCHIVOS_REGION = {
    "CDMX": [DATOS_DIR / "CDMX" / "conjunto_de_datos" / "denue_inegi_09_.csv"],
    "EDOMEX": [
        DATOS_DIR / "EDOMEX" / "1" / "conjunto_de_datos" / "denue_inegi_15_1.csv",
        DATOS_DIR / "EDOMEX" / "2" / "conjunto_de_datos" / "denue_inegi_15_2.csv",
    ],
}

# Encoding de los CSV de INEGI/DENUE.
ENCODING = "latin-1"

# Columnas que conservamos del DENUE.
COLUMNAS = [
    "id", "nom_estab", "codigo_act", "nombre_act", "per_ocu",
    "cve_ent", "entidad", "cve_mun", "municipio",
    "latitud", "longitud",
]

# Proyección: WGS84 (lat/lon) -> UTM 14N (metros) para distancias reales.
CRS_GEO = "EPSG:4326"
CRS_METROS = "EPSG:32614"  # UTM zona 14N (centro de México)

# Sector de análisis por defecto: SCIAN 62 = Servicios de salud y asistencia social.
SECTOR_DEFAULT = "62"

# Mapeo de rangos de personal ocupado a un valor numérico (punto medio aprox.).
PER_OCU_MIDPOINT = {
    "0 a 5 personas": 3,
    "6 a 10 personas": 8,
    "11 a 30 personas": 20,
    "31 a 50 personas": 40,
    "51 a 100 personas": 75,
    "101 a 250 personas": 175,
    "251 y más personas": 300,
}

# Bounding boxes aproximados para descartar coordenadas corruptas (lon, lat).
BBOX_REGION = {
    "CDMX": {"lon": (-99.40, -98.90), "lat": (19.00, 19.65)},
    "EDOMEX": {"lon": (-100.60, -98.50), "lat": (18.30, 20.30)},
}
