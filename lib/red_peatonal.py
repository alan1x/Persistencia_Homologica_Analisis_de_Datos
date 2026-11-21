"""Red peatonal de OpenStreetMap y distancias por calle (fase F6 de `PLAN_ACCESO.md`).

- `descargar_pbf`: baja el PBF de México de Geofabrik si no está.
- `extraer_red`: lee las vías caminables dentro de una caja y devuelve nodos y aristas.
- `Red`: grafo disperso con anclaje de puntos y Dijkstra local con corte.

La red es no dirigida: a pie se puede ir en ambos sentidos de una calle de un solo sentido.
"""
import hashlib
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy import sparse
from scipy.sparse import csgraph
from scipy.spatial import cKDTree

from lib import config

URL_PBF = "https://download.geofabrik.de/north-america/mexico-latest.osm.pbf"
# Se incluye trunk: en México muchas avenidas urbanas con banqueta (Av. Central, Primero de Mayo)
# están etiquetadas así y sin foot=no. Excluirlas las volvía muros (ver notebook 35).
# motorway (autopistas de cuota) sigue fuera.
CAMINABLES = {
    "trunk", "trunk_link", "footway", "pedestrian", "path", "track", "steps", "corridor", "living_street", "residential",
    "service", "unclassified", "road", "tertiary", "tertiary_link", "secondary", "secondary_link",
    "primary", "primary_link", "cycleway",
}
PROHIBIDO = {"no", "private"}
PERMITIDO = {"yes", "designated", "permissive"}
REGLAS_VERSION = 2  # súbelo si cambia la lógica de extracción, para invalidar la red guardada


def huella(*partes):
    """Hash corto de las entradas de un caché (arreglos, números o textos)."""
    h = hashlib.sha1()
    for p in partes:
        h.update(np.ascontiguousarray(p).tobytes() if isinstance(p, np.ndarray) else repr(p).encode())
    return h.hexdigest()[:16]


def huella_reglas(bbox):
    """Huella de la red: reglas de vías y caja de extracción."""
    return huella(sorted(CAMINABLES), sorted(PROHIBIDO), sorted(PERMITIDO), np.round(np.asarray(bbox, float), 6),
                  REGLAS_VERSION)


def descargar_pbf(destino, url=URL_PBF):
    """Descarga el PBF si no existe. Escribe primero a un .parcial y renombra al terminar."""
    destino = Path(destino)
    if destino.exists():
        print(f"PBF ya existe: {destino} ({destino.stat().st_size / 1e6:,.0f} MB)", flush=True)
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(".parcial")
    t0 = time.time()
    with urllib.request.urlopen(url) as r, open(parcial, "wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        print(f"Descargando {url} ({total / 1e6:,.0f} MB)", flush=True)
        hecho, aviso = 0, 0
        while bloque := r.read(1 << 20):
            f.write(bloque)
            hecho += len(bloque)
            if hecho - aviso > 50e6:
                aviso = hecho
                print(f"  {hecho / 1e6:,.0f} MB", flush=True)
    if total and parcial.stat().st_size != total:
        raise IOError(f"Descarga incompleta: {parcial.stat().st_size} de {total} bytes")
    parcial.rename(destino)
    print(f"Descarga lista en {(time.time() - t0) / 60:.1f} min", flush=True)
    return destino


def extraer_red(pbf, bbox):
    """Vías caminables con al menos un nodo dentro de bbox = (oeste, sur, este, norte).

    Devuelve (xy de nodos en CRS_METROS, aristas u, v, longitud en m).
    """
    import osmium

    oeste, sur, este, norte = bbox

    class Vias(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.ids, self.lon, self.lat = [], [], []
            self.u, self.v = [], []
            self.n = 0

        def way(self, w):
            t = w.tags
            # access=no/private excluye la vía salvo que foot la permita explícitamente.
            pie = t.get("foot")
            if (t.get("highway") not in CAMINABLES or pie in PROHIBIDO
                    or (t.get("access") in PROHIBIDO and pie not in PERMITIDO)):
                return
            pts = [(nd.ref, nd.lon, nd.lat) for nd in w.nodes if nd.location.valid()]
            if not any(oeste <= lo <= este and sur <= la <= norte for _, lo, la in pts):
                return
            for (a, lo, la) in pts:
                self.ids.append(a)
                self.lon.append(lo)
                self.lat.append(la)
            for (a, _, _), (b, _, _) in zip(pts[:-1], pts[1:]):
                self.u.append(a)
                self.v.append(b)
            self.n += 1

    h = Vias()
    h.apply_file(str(pbf), locations=True, idx="flex_mem", filters=[osmium.filter.KeyFilter("highway")])
    ids = np.array(h.ids, dtype=np.int64)
    uniq, pos = np.unique(ids, return_index=True)
    lon, lat = np.array(h.lon)[pos], np.array(h.lat)[pos]
    x, y = Transformer.from_crs(config.CRS_GEO, config.CRS_METROS, always_xy=True).transform(lon, lat)
    xy = np.column_stack([x, y])
    u = np.searchsorted(uniq, np.array(h.u, dtype=np.int64))
    v = np.searchsorted(uniq, np.array(h.v, dtype=np.int64))
    m = u != v
    u, v = u[m], v[m]
    largo = np.hypot(*(xy[u] - xy[v]).T)
    print(f"vías: {h.n:,}, nodos: {len(xy):,}, aristas: {len(u):,}", flush=True)
    return xy, u, v, largo


class Red:
    """Grafo no dirigido en CSR, anclaje de puntos al nodo más cercano y Dijkstra local."""

    def __init__(self, xy, u, v, largo, min_comp=1000):
        n = len(xy)
        # Aristas repetidas: se queda la más corta (csr suma duplicados, por eso se depura antes).
        a, b = np.minimum(u, v), np.maximum(u, v)
        e = pd.DataFrame({"a": a, "b": b, "l": largo}).groupby(["a", "b"], as_index=False)["l"].min()
        a, b, l = e["a"].to_numpy(), e["b"].to_numpy(), e["l"].to_numpy()
        l = np.maximum(l, 1e-3)  # csgraph trata 0 como ausencia de arista
        self.G = sparse.csr_matrix((np.r_[l, l], (np.r_[a, b], np.r_[b, a])), shape=(n, n))
        _, comp = csgraph.connected_components(self.G, directed=False)
        tam = np.bincount(comp)
        self.util = tam[comp] >= min_comp  # se ancla solo a componentes grandes
        self.xy = xy
        self.arbol_util = cKDTree(xy[self.util])
        self.idx_util = np.flatnonzero(self.util)
        self.arbol = cKDTree(xy)
        print(f"red: {n:,} nodos, {len(a):,} aristas, {len(tam):,} componentes; "
              f"{self.util.mean() * 100:.1f}% de nodos en componentes de ≥ {min_comp}", flush=True)

    def anclar(self, pts):
        d, k = self.arbol_util.query(pts)
        return self.idx_util[k], d

    def pares(self, cel_xy, fue_xy, limite, cada=500):
        """Pares (celda i, fuente j, distancia por red) con distancia ≤ limite.

        distancia = anclaje de la fuente + red + anclaje de la celda. Como la distancia por red
        nunca es menor que la recta, basta con explorar los nodos a ≤ limite en línea recta.
        """
        cel_nodo, cel_anc = self.anclar(cel_xy)
        fue_nodo, fue_anc = self.anclar(fue_xy)
        arbol_cel = cKDTree(cel_xy)
        I, J, D = [], [], []
        t0 = time.time()
        for j in range(len(fue_xy)):
            resto = limite - fue_anc[j]
            if resto <= 0:
                continue
            cel = np.asarray(arbol_cel.query_ball_point(fue_xy[j], limite), dtype=int)
            if not len(cel):
                continue
            nod = np.sort(np.asarray(self.arbol.query_ball_point(self.xy[fue_nodo[j]], resto), dtype=int))
            sub = self.G[nod][:, nod]
            s = np.searchsorted(nod, fue_nodo[j])
            dist = csgraph.dijkstra(sub, directed=False, indices=s, limit=resto)
            p = np.searchsorted(nod, cel_nodo[cel])
            p = np.minimum(p, len(nod) - 1)
            ok = nod[p] == cel_nodo[cel]
            d = np.where(ok, dist[p], np.inf) + cel_anc[cel] + fue_anc[j]
            m = d <= limite
            I.append(cel[m])
            J.append(np.full(m.sum(), j))
            D.append(d[m])
            if (j + 1) % cada == 0:
                print(f"  {j + 1:,}/{len(fue_xy):,} fuentes, {(time.time() - t0) / 60:.1f} min", flush=True)
        return (np.concatenate(I), np.concatenate(J), np.concatenate(D), cel_anc)
