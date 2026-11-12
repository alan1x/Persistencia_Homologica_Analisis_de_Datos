"""Oferta y demanda para el análisis de acceso (fases F1 a F3 de `PLAN_ACCESO.md`).

- `oferta`: unidades públicas de DENUE con una capacidad aproximada.
- `rejilla`: personas sin seguro repartidas en una rejilla de 100 m (igual que los notebooks 26 y 28).
"""
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


def oferta(nivel="primer", abierta=False, capacidad="personal"):
    """Unidades públicas de ambos estados con columnas x, y, region, cap.

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
    return o.reset_index(drop=True)


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


def marginacion_conapo():
    """Índice de Marginación Urbana 2020 de CONAPO por AGEB (CDMX y Estado de México).

    IM_2020: un valor mayor indica MENOS marginación (método DP2). GM_2020 es el grado.
    El índice incluye PSDSS (% sin derechohabiencia) como uno de sus diez indicadores.
    """
    d = pd.read_excel(config.DATOS_DIR / "CONAPO" / "IMU_2020.xls", sheet_name="IMU_2020", dtype={"CVE_AGEB": str})
    d = d[d["ENT"].isin([9, 15])].rename(columns={"CVE_AGEB": "CVEGEO"})
    return d.reset_index(drop=True)
