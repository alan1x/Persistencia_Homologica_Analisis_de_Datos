"""Carga, limpieza y proyección de datos DENUE por región."""
import numpy as np
import pandas as pd
from pyproj import Transformer

from . import config


def cargar_region(region):
    """Carga el/los CSV de una región, concatena y conserva columnas clave."""
    archivos = config.ARCHIVOS_REGION[region]
    partes = []
    for ruta in archivos:
        df = pd.read_csv(
            ruta,
            encoding=config.ENCODING,
            usecols=config.COLUMNAS,
            dtype={"codigo_act": str, "cve_mun": str, "cve_ent": str},
            low_memory=False,
        )
        partes.append(df)
    df = pd.concat(partes, ignore_index=True)
    df["region"] = region
    return df


def filtrar_sector(df, sector=config.SECTOR_DEFAULT):
    """Filtra por prefijo de codigo_act SCIAN (p.ej. '62' = salud)."""
    return df[df["codigo_act"].str.startswith(sector)].copy()


def limpiar(df, region):
    """Limpia coordenadas: numéricas, no nulas, dentro del bounding box, sin duplicados."""
    df = df.copy()
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df = df.dropna(subset=["latitud", "longitud"])

    bbox = config.BBOX_REGION[region]
    df = df[
        df["longitud"].between(*bbox["lon"])
        & df["latitud"].between(*bbox["lat"])
    ]

    df = df.drop_duplicates(subset=["id"])
    df = df.drop_duplicates(subset=["latitud", "longitud", "nom_estab"])

    df["per_ocu_num"] = df["per_ocu"].map(config.PER_OCU_MIDPOINT)
    return df.reset_index(drop=True)


def proyectar(df):
    """Agrega columnas x, y en metros (UTM 14N) desde lon/lat."""
    df = df.copy()
    transformer = Transformer.from_crs(
        config.CRS_GEO, config.CRS_METROS, always_xy=True
    )
    x, y = transformer.transform(df["longitud"].values, df["latitud"].values)
    df["x"] = x
    df["y"] = y
    return df


def preparar(region, sector=config.SECTOR_DEFAULT):
    """Pipeline completo: cargar -> filtrar sector -> limpiar -> proyectar."""
    df = cargar_region(region)
    df = filtrar_sector(df, sector)
    df = limpiar(df, region)
    df = proyectar(df)
    return df


def puntos(df):
    """Devuelve array (N, 2) de coordenadas proyectadas para TDA."""
    return df[["x", "y"]].to_numpy()
