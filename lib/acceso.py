"""Oferta y demanda para el análisis de acceso (fases F1 a F3 de `PLAN_ACCESO.md`).

- `oferta`: unidades públicas con su capacidad. Desde F8.1 (2026-11-22) la fuente principal es
  CLUES con médicos (`notebooks/29_oferta_clues.py`); DENUE queda como comparación.
- `rejilla`: personas sin seguro repartidas en una rejilla de 100 m (igual que los notebooks 26 y 28).

La variable de entorno `OFERTA` (denue, clues o clues_ampliado) cambia la fuente por defecto.
"""
import os

import numpy as np
import pandas as pd
import shapely

from lib import config

PASO = 100.0
RADIO_15 = 15 * (4500 / 60) / 1.35  # 833 m: 15 min a 4.5 km/h con rodeo 1.35

# Unidades de seguridad social, que en principio no atienden a quien no tiene seguro.
# Se conserva IMSS-Bienestar.
SEG_SOCIAL = (r"IMSS(?!.*BIENESTAR)|SEGURO SOCIAL(?!.*BIENESTAR)|ISSSTE|SEGURIDAD Y SERVICIOS SOCIALES|"
              r"ISSEMYM|SEGURIDAD SOCIAL|PEMEX|PETROLEOS|SEDENA|DEFENSA NACIONAL|MILITAR|SEMAR|MARINA|"
              r"UNIDAD DE MEDICINA FAMILIAR|\bU\.?M\.?F\b")


FUENTES = ("denue", "clues", "clues_ampliado")


def fuente_oferta():
    """Fuente vigente: la de la variable de entorno OFERTA, o CLUES."""
    f = os.environ.get("OFERTA", "clues")
    if f not in FUENTES:
        raise ValueError(f"OFERTA={f!r}; usa una de {FUENTES}")
    return f


def sufijo_oferta():
    """Sufijo para archivos de puntos de control que dependen de la oferta ("" con DENUE, para
    conservar los nombres de antes de F8.1)."""
    f = fuente_oferta()
    return "" if f == "denue" else f"_{f}"


def oferta(nivel="primer", abierta=False, capacidad="personal", fuente=None):
    """Unidades públicas de ambos estados con columnas id, nom_estab, x, y, region, cap.

    fuente:
        None usa `fuente_oferta()`.
        "clues": IMSS-Bienestar, SSA y UMR del IMSS de primer nivel (notebook 29). Ya excluye la
        seguridad social, así que `abierta` no cambia nada. Se quitan las unidades con cap 0 y
        las que no tienen celda de demanda a ≤ 1,667 m (`en_dominio`, rurales fuera de F3).
        "clues_ampliado": lo anterior más DIF y consultorios municipales (CLUES y DENUE).
        "denue": consultorios del sector público de DENUE (lo usado hasta F7).
    capacidad, con CLUES:
        "personal" o "medicos": médicos generales, familiares y pasantes (principal).
        "consultorios": consultorios de medicina general y familiar (solo "clues").
        "unidad": cada unidad vale 1.

    Con DENUE:
    nivel:
        "primer": consultorios y clínicas (6211), es decir, la consulta de primer contacto.
        "todo": además hospitales (622).
    abierta:
        True quita las unidades de seguridad social, buscando por su nombre.
    capacidad:
        "personal": punto medio del rango de personal ocupado de DENUE.
        "unidad": cada unidad vale 1.
        "personal_tope": como "personal", con tope de 75, para que un hospital grande no
        cuente como cien consultorios.
    """
    fuente = fuente or fuente_oferta()
    if fuente != "denue":
        return _oferta_clues(fuente, nivel, capacidad)
    s = pd.concat([pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{r}.parquet")
                   for r in ["CDMX", "EDOMEX"]], ignore_index=True)
    cod = s["codigo_act"].astype(str)
    publico = s["nombre_act"].str.contains("sector p[uú]blico", case=False, regex=True)
    m = publico & (cod.str.startswith("6211") | (nivel == "todo") & cod.str.startswith("622"))
    if abierta:
        m &= ~s["nom_estab"].astype(str).str.upper().str.contains(SEG_SOCIAL, regex=True)
    o = s.loc[m, ["id", "nom_estab", "nombre_act", "per_ocu", "per_ocu_num", "region", "x", "y"]].copy()
    if capacidad == "unidad":
        o["cap"] = 1.0
    elif capacidad == "personal":
        o["cap"] = o["per_ocu_num"].astype(float)
    elif capacidad == "personal_tope":
        o["cap"] = o["per_ocu_num"].astype(float).clip(upper=75)
    else:
        raise ValueError(capacidad)
    o["fuente"] = "denue"
    return o.reset_index(drop=True)


def _oferta_clues(fuente, nivel, capacidad):
    if nivel != "primer":
        raise NotImplementedError("CLUES solo tiene armado el primer nivel")
    col = {"personal": "medicos", "medicos": "medicos", "consultorios": "consultorios", "unidad": None}
    if capacidad not in col:
        raise ValueError(capacidad)
    if fuente == "clues":
        c = pd.read_parquet(config.INTERMEDIOS_DIR / "oferta_clues.parquet")
        c = c[c["principal"] & c["coord_ok"] & c["en_dominio"]]
        o = pd.DataFrame({"id": c["CLUES"], "nom_estab": c["NOMBRE DE LA UNIDAD"], "region": c["region"],
                          "x": c["x"], "y": c["y"], "medicos": c["medicos"], "consultorios": c["consultorios"]})
        o["fuente"] = "clues"
    else:
        if capacidad == "consultorios":
            raise ValueError("el escenario ampliado no tiene consultorios para la capa DENUE")
        a = pd.read_parquet(config.INTERMEDIOS_DIR / "oferta_clues_ampliada.parquet")
        o = a[a["en_dominio"]].rename(columns={"NOMBRE DE LA UNIDAD": "nom_estab"})
    o["cap"] = 1.0 if col[capacidad] is None else o[col[capacidad]].astype(float)
    return o[o["cap"] > 0].reset_index(drop=True)


def rango_capacidad(o):
    """(lo, hi) enteros para las réplicas que sortean la capacidad de cada unidad de CLUES.

    F8.1: entre consultorios (un médico por consultorio, un turno) y médicos reportados
    (plantilla completa), en el orden que toque, con mínimo 1. Sin consultorios (capa DENUE del
    ampliado, o capacidad = unidad): el valor fijo. DENUE usa los rangos de `per_ocu` de cada
    notebook (`f4.RANGOS`).
    """
    cap = o["cap"].to_numpy(float)
    otra = o["consultorios"].to_numpy(float) if "consultorios" in o else cap
    otra = np.where(np.isnan(otra), cap, otra)
    lo = np.maximum(1, np.minimum(cap, otra)).astype(int)
    hi = np.maximum(lo, np.maximum(cap, otra)).astype(int)
    return lo, hi


def rejilla(ageb, columna="PSINDER", paso=PASO):
    """Reparte `columna` de cada AGEB entre los puntos de una rejilla dentro de ella.

    Cada AGEB sin puntos de la rejilla en su interior se representa con un punto interior.
    Devuelve (xy, valor) y conserva el total.
    """
    xy, val = [], []
    for geom, v in zip(ageb.geometry, ageb[columna].fillna(0).to_numpy(float)):
        x0, y0, x1, y1 = geom.bounds
        xs = np.arange(np.floor(x0 / paso), np.ceil(x1 / paso) + 1) * paso
        ys = np.arange(np.floor(y0 / paso), np.ceil(y1 / paso) + 1) * paso
        xx, yy = np.meshgrid(xs, ys)
        dentro = shapely.contains_xy(geom, xx.ravel(), yy.ravel())
        if dentro.any():
            pts = np.column_stack([xx.ravel()[dentro], yy.ravel()[dentro]])
        else:
            p = geom.representative_point()
            pts = np.array([[p.x, p.y]])
        xy.append(pts)
        val.append(np.full(len(pts), v / len(pts)))
    return np.vstack(xy), np.concatenate(val)


def demanda(region, columna="PSINDER", con_ageb=False):
    """Rejilla de demanda de una región en metros (UTM 14N).

    Con `con_ageb=True` devuelve también la clave CVEGEO de la AGEB de cada celda.
    """
    from lib import censo

    ageb = censo.construir_ageb_enriquecido(region)
    ageb = ageb[ageb["POBTOT"].fillna(0) > 0].to_crs(config.CRS_METROS).reset_index(drop=True)
    xy, v = rejilla(ageb, columna)
    assert abs(v.sum() - ageb[columna].sum()) < 1
    if not con_ageb:
        return xy, v
    # La rejilla recorre las AGEB en orden; se reconstruye a qué AGEB pertenece cada celda.
    ageb["_uno"] = 1.0
    _, cuenta = rejilla(ageb, "_uno")
    n = np.rint(1 / cuenta).astype(int)  # cada celda guarda 1/n de su AGEB
    claves, i = [], 0
    for cve in ageb["CVEGEO"]:
        claves.extend([cve] * n[i])
        i += n[i]
    assert len(claves) == len(xy)
    return xy, v, np.array(claves)


def peso(d, d0, tipo="gauss"):
    """Decaimiento con la distancia: gaussiano (1 en d = 0, 0 en d = d0) o por escalones en tercios."""
    if tipo == "gauss":
        return np.where(d <= d0, (np.exp(-0.5 * (d / d0) ** 2) - np.exp(-0.5)) / (1 - np.exp(-0.5)), 0.0)
    return np.select([d <= d0 / 3, d <= 2 * d0 / 3, d <= d0], [1.0, 0.68, 0.22], 0.0)


def pares_e2sfca(xy, fxy, d0, tipo="gauss"):
    """Pares celda-unidad dentro de la cuenca: (i celda, j unidad, peso)."""
    from scipy.spatial import cKDTree

    arbol = cKDTree(xy)
    filas, cols, ws = [], [], []
    for j, idx in enumerate(arbol.query_ball_point(fxy, d0)):
        if not idx:
            continue
        idx = np.asarray(idx)
        filas.append(idx)
        cols.append(np.full(len(idx), j))
        ws.append(peso(np.hypot(*(xy[idx] - fxy[j]).T), d0, tipo))
    return np.concatenate(filas), np.concatenate(cols), np.concatenate(ws)


def e2sfca_pares(i, j, w, dem, cap, n_celdas):
    """E2SFCA con pares ya calculados. Devuelve (A, R) por persona, sin escalar."""
    dem_j = np.bincount(j, weights=dem[i] * w, minlength=len(cap))
    R = np.divide(cap, dem_j, out=np.zeros(len(cap)), where=dem_j > 0)
    A = np.bincount(i, weights=R[j] * w, minlength=n_celdas)
    return A, R


def e2sfca(xy, dem, fxy, cap, d0=2 * RADIO_15, tipo="gauss"):
    """Acceso por celda (capacidad por 1,000 personas), razón de cada unidad y si alguna la alcanza."""
    i, j, w = pares_e2sfca(xy, fxy, d0, tipo)
    A, R = e2sfca_pares(i, j, w, dem, np.asarray(cap, float), len(xy))
    alcanza = np.bincount(i, minlength=len(xy)) > 0
    return A * 1000, R * 1000, alcanza


def marginacion_conapo():
    """Índice de Marginación Urbana 2020 de CONAPO por AGEB (CDMX y Estado de México).

    IM_2020: un valor mayor indica MENOS marginación (método DP2). GM_2020 es el grado.
    El índice incluye PSDSS (% sin derechohabiencia) como uno de sus once indicadores.
    """
    d = pd.read_excel(config.DATOS_DIR / "CONAPO" / "IMU_2020.xls", sheet_name="IMU_2020", dtype={"CVE_AGEB": str})
    d = d[d["ENT"].isin([9, 15])].rename(columns={"CVE_AGEB": "CVEGEO"})
    return d.reset_index(drop=True)
