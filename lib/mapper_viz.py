"""Mapper (KeplerMapper) sobre las unidades económicas (Fase 3b).

Complemento a la persistencia: resume la estructura de los datos como una
red de nodos (clusters) y aristas (clusters que comparten puntos). Liga la
investigación propia 'Mapper'.
"""
import kmapper as km
import numpy as np
from sklearn.cluster import DBSCAN

from . import config


def construir_mapper(puntos, color_values, region,
                     n_cubes=15, perc_overlap=0.4, eps=600, min_samples=5):
    """Construye el grafo Mapper y exporta HTML.

    - lens: las coordenadas proyectadas (x, y) -> esqueleto espacial.
    - cluster: DBSCAN por cubo (eps en metros).
    - color: valor por punto (p.ej. personal ocupado) para colorear nodos.
    """
    mapper = km.KeplerMapper(verbose=0)
    lens = mapper.fit_transform(puntos, projection=[0, 1])  # usa x, y
    grafo = mapper.map(
        lens,
        puntos,
        cover=km.Cover(n_cubes=n_cubes, perc_overlap=perc_overlap),
        clusterer=DBSCAN(eps=eps, min_samples=min_samples),
    )
    ruta = config.FIGURAS_DIR / f"mapper_{region}.html"
    mapper.visualize(
        grafo,
        path_html=str(ruta),
        title=f"Mapper — unidades de salud {region}",
        color_values=color_values,
        color_function_name="personal ocupado",
    )
    n_nodos = len(grafo["nodes"])
    n_aristas = sum(len(v) for v in grafo["links"].values())
    return ruta, n_nodos, n_aristas
