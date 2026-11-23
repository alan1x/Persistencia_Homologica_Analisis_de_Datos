# %% [markdown]
# # 29 — Oferta oficial: CLUES contra DENUE (F8.1 / F1 de `PLAN_ACCESO.md`)
#
# Hasta ahora la oferta de F3 a F5 sale de DENUE: consultorios del "sector público" (6211),
# con el punto medio del rango de personal ocupado como capacidad (`acceso.oferta()`, 1,290
# unidades). DENUE no dice a quién atiende cada unidad ni cuántos consultorios tiene. Aquí se
# prueba si el catálogo oficial de la Secretaría de Salud lo hace mejor.
#
# ## Fuentes (descargadas el 2026-11-22, en `Datos/CLUES/`)
#
# - **Catálogo CLUES** de la DGIS, corte de octubre de 2026 (`ESTABLECIMIENTO_SALUD_202610.xlsx`,
#   hoja `CLUES_202610`): institución, tipología, nivel de atención, estatus, latitud y longitud.
# - **Recursos en Salud Sectorial 2025** (`recursos_2025/BD ABIERTOS SECTORIAL 2025.csv`):
#   consultorios, camas y personal por CLUES, cierre 2025.
#
# ## Universos (fijados antes de correr, tras un sondeo de columnas y conteos)
#
# Todos: entidad 09 o 15, estatus "EN OPERACION", nivel "PRIMER NIVEL", tipo "DE CONSULTA
# EXTERNA". Los textos se normalizan quitando espacios (el catálogo trae
# "SERVICIOS DE SALUD IMSS BIENESTAR " con un espacio al final).
#
# - **Principal (`principal`): atención general a población sin seguridad social.**
#   IMSS-Bienestar y Secretaría de Salud con tipologías de atención general (núcleos básicos
#   urbanos o rurales, CAAPS, centros de salud con servicios ampliados o con hospitalización,
#   casas de salud), más las **Unidades Médicas Rurales del IMSS** (antes IMSS-Coplamar,
#   atienden a población abierta). **Se excluyen:** unidades móviles (sin sitio fijo),
#   consultorios médico-legales del Ministerio Público, UNEMES (salud mental, adicciones,
#   CAPASITS) y clínicas de especialidades. También "Servicios Médicos Estatales" (en EDOMEX
#   son ISSEMYM, seguridad social; en CDMX son clínicas de corporaciones y centros de
#   asistencia social), los 7 "Servicios Médicos Municipales" de CDMX y el DIF: atienden con
#   reglas de elegibilidad o carteras distintas. DIF y municipales quedan como posible
#   escenario ampliado, no se usan aquí.
# - **Pública completa (`pub`), solo para cotejar con la DENUE base:** la principal más la
#   consulta familiar de la seguridad social: IMSS (UMF), ISSSTE (clínicas, consultorios y
#   unidades de medicina familiar), ISSEMYM (tipologías de atención general) y las unidades de
#   SEDENA, SEMAR y PEMEX. Sin bancos de sangre, rehabilitación, especialidades, móviles ni
#   consultorios en centros de trabajo.
#
# Pares comparables: **principal contra DENUE abierta** (`acceso.oferta(abierta=True)`, 1,149
# unidades) y **pública completa contra DENUE base**.
#
# ## Capacidad
#
# - *Fijada antes de correr:* principal, consultorios de medicina general y familiar;
#   sensibilidad, médicos generales, familiares y pasantes, y cada unidad vale 1.
# - **Decidido después de correr (2026-11-22, Mario): médicos como principal.** El criterio 6
#   falló (Jaccard 0.76 entre consultorios y médicos), porque los médicos capturan los turnos
#   (un CAAPS típico: 3 consultorios, 10 médicos) y un consultorio sin médico no atiende.
#   Consultorios queda como sensibilidad. Las unidades con 0 médicos no aportan oferta.
# - Unidad sin registro de recursos: mediana de su tipología **dentro del mismo universo**, y
#   se marca como imputada. Unidad con capacidad 0: se queda con 0 y se reporta.
#
# ## Criterios fijados antes de correr
#
# 1. **Coordenadas utilizables:** numéricas, dentro del polígono de su municipio declarado o a
#    ≤ 250 m de él (Marco Geoestadístico), y sin compartir coordenada exacta (5 decimales)
#    con unidades de otra localidad. Se reportan aparte, sin descartarlas: las de ≤ 3
#    decimales en algún eje (~110 m) como imprecisas, y las **de localidad discordante**
#    (su localidad declarada tiene polígono urbano y el punto queda a > 250 m de él).
# 2. **Capacidad observada:** registro en Recursos 2025 con consultorios generales/familiares
#    > 0 (la medida principal; médicos > 0 no basta).
# 3. **Decisión (la de F1):** si **≥ 90% de las unidades del universo principal cumplen 1 y 2
#    a la vez**, se cambia a CLUES y se recalculan F3 a F5. Si no, se sigue con DENUE y se
#    reporta el cotejo.
# 4. **Cotejo con DENUE** (descriptivo, no decide), solo con coordenadas utilizables:
#    emparejamiento uno a uno con pares a ≤ 200 m que maximiza el número de pares y luego
#    minimiza la distancia (asignación húngara). Se reporta qué fracción de cada lado tiene
#    pareja, la distribución de distancias y cuántos pares comparten una palabra distintiva
#    del nombre. Advertencia, no veto: si menos del 50% de CLUES principal tiene pareja en
#    DENUE abierta, se investiga antes de cambiar.
# 5. **¿Qué tan buen proxy era `per_ocu`?** En los pares principal–abierta con capacidad
#    observada: Spearman de `per_ocu_num` contra consultorios y contra médicos. Por municipio
#    (CLUES por su municipio declarado, demanda por su AGEB): Spearman de la capacidad por
#    persona sin seguro, DENUE abierta contra CLUES principal. Ojo: el municipal puede salir
#    alto por el denominador compartido.
# 6. **Impacto en F3** (descriptivo; la decisión es la del criterio 3): E2SFCA en recta a
#    30 min (1,667 m, gaussiano), la rejilla de F3, acceso bajo = f < 0.5 del promedio
#    metropolitano de cada oferta. Se compara DENUE base, DENUE abierta y CLUES con tres
#    capacidades, y CLUES sin las unidades de localidad discordante. Se reporta gente con
#    acceso bajo, Jaccard del mapa de acceso bajo (ponderado por personas) contra DENUE base y
#    los municipios con más personas que entran o salen. Si la capacidad o las sedes dudosas
#    mueven mucho el mapa (Jaccard entre variantes CLUES < 0.8), se resuelve antes de
#    recalcular F4 y F5.
#
# ## Escenario ampliado (agregado después de correr, 2026-11-22, a pedido de Mario)
#
# El cotejo mostró que DENUE cubre a ~0.65 M de personas que CLUES deja sin unidad, sobre todo
# con DIF y consultorios municipales o de alcaldía. Atienden a gente sin seguro, pero con
# reglas propias (cuotas, carteras), así que entran solo como **escenario ampliado**:
#
# - **Capa CLUES:** DIF y Servicios Médicos Municipales de primer nivel, consulta externa,
#   en operación, sin unidades móviles, con sus médicos de Recursos 2025.
# - **Capa DENUE:** unidades de DENUE abierta sin pareja a ≤ 200 m en CLUES (principal + capa
#   CLUES) cuyo nombre dice DIF, desarrollo integral de la familia, municipal, alcaldía,
#   delegación, ayuntamiento o periférico. Se excluyen por nombre las que no dan consulta
#   general (rehabilitación, bomberos, protección civil, ERUM, oficinas, bodegas, vacunación,
#   centros sociales o comunitarios, adicciones, especialidades). Sus médicos se estiman con
#   la mediana de médicos por rango de `per_ocu` en los pares principal–DENUE abierta.
#
# ## Dominio (agregado después de correr, 2026-11-22: corrige un error)
#
# CLUES cubre todo el Estado de México; la demanda de F3 son solo las AGEB urbanas. Al recorrer
# F3 a F5 con CLUES salieron 375 unidades principales (12% de los médicos), rurales, a más de
# 1,667 m de toda celda de demanda. No atienden a nadie del modelo pero entraban en el promedio
# metropolitano (capacidad total / demanda total), que subía 14% y metía ~0.33 M de personas
# de más en acceso bajo; el notebook 37 además las arrastraba hasta 22 km a nodos urbanos.
# **Regla:** una unidad entra a la oferta si tiene alguna celda de demanda a ≤ 1,667 m en recta
# (`en_dominio`). Vale para el escenario ampliado y, en la sección 6, también para DENUE (9
# unidades, 0.1% de su capacidad; `acceso.oferta` con DENUE no se cambia, para conservar lo
# archivado). El cotejo con DENUE y los criterios 1 a 3 siguen sobre todo el universo.
#
# *Ajustes tras la crítica de Codex, antes de correr:* UMR del IMSS en el universo; el 90% se
# exige sobre la intersección de 1 y 2; marca de localidad discordante; cotejo solo con
# coordenadas utilizables; filtro propio para `pub`; validación del cruce con Recursos (trae
# CLUES vacías y repetidas fuera de la zona); Spearman sobre el par comparable; criterio 6.

# %%
import json
import re
import sys
import unicodedata
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

from lib import acceso, config, viz_eval as ve

ve.aplicar()
DAT = config.DATOS_DIR / "CLUES"
GEO = config.DATOS_DIR / "Geoestadistico"
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
MATCH = 200.0
TOL = 250.0
CUENCA = 2 * acceso.RADIO_15  # 1,667 m
REG = {"09": "CDMX", "15": "EDOMEX"}

INST_PRINCIPAL = {"SERVICIOS DE SALUD IMSS BIENESTAR", "SECRETARIA DE SALUD"}
TIPO_EXCLUIDA = {"UNIDAD MÓVIL", "UNIDAD MEDICA MOVIL", "UNIDAD MINISTERIO PÚBLICO",
                 "UNIDAD DE ESPECIALIDADES MÉDICAS (UNEMES)", "CLÍNICA DE ESPECIALIDADES"}
TIPO_GENERAL = re.compile(r"N[UÚ]CLEOS? B[AÁ]SICOS?|CAAPS|CENTROS? DE SALUD CON|CASA DE SALUD")
# Seguridad social: (clave de institución, tipologías de consulta familiar o general).
TIPO_FAMILIAR = re.compile(r"MEDICINA FAMILIAR|ATENCION FAMILIAR|N[UÚ]CLEOS? B[AÁ]SICOS?|CENTRO DE SALUD CON|NO ESPECIFICADO")
INST_SEG_SOCIAL = {"IMS", "IST", "SME", "SDN", "SMA", "PMX"}
TIPO_SS_EXCLUIDA = re.compile(r"ESPECIALIDADES|REHABILITACI|BANCO DE SANGRE|CENTRO DE TRABAJO|M[OÓ]VIL")

# %% [markdown]
# ## 1. Catálogo y universos

# %%
cat = pd.read_excel(DAT / "ESTABLECIMIENTO_SALUD_202610.xlsx", sheet_name="CLUES_202610", dtype=str)
cat = cat.apply(lambda s: s.str.strip())
assert not cat["CLUES"].duplicated().any()
z = cat[cat["CLAVE DE LA ENTIDAD"].isin(REG)
        & (cat["ESTATUS DE OPERACION"] == "EN OPERACION")
        & (cat["NIVEL ATENCION"] == "PRIMER NIVEL")
        & (cat["NOMBRE TIPO ESTABLECIMIENTO"] == "DE CONSULTA EXTERNA")
        & ~cat["NOMBRE DE TIPOLOGIA"].isin(TIPO_EXCLUIDA)].copy().reset_index(drop=True)
inst, cinst, tipo = z["NOMBRE DE LA INSTITUCION"], z["CLAVE DE LA INSTITUCION"], z["NOMBRE DE TIPOLOGIA"]
umr = (cinst == "IMS") & (tipo == "UNIDAD MÉDICA RURAL")
z["principal"] = (inst.isin(INST_PRINCIPAL) & tipo.str.contains(TIPO_GENERAL)) | umr
z["pub"] = z["principal"] | (cinst.isin(INST_SEG_SOCIAL) & tipo.str.contains(TIPO_FAMILIAR)
                             & ~tipo.str.contains(TIPO_SS_EXCLUIDA))
z["amp_clues"] = cinst.isin({"DIF", "SMM"}) & ~tipo.str.contains("OFICINAS")  # escenario ampliado
z["region"] = z["CLAVE DE LA ENTIDAD"].map(REG)
z = z[z["pub"] | z["amp_clues"]].reset_index(drop=True)

print("Universo principal:", int(z.principal.sum()), "| pública completa:", int(z.pub.sum()),
      "| capa ampliada CLUES (DIF, SMM):", int(z.amp_clues.sum()))
print(z[z.principal].groupby(["region", "NOMBRE DE LA INSTITUCION"]).size().to_string())
print(z[z.pub & ~z.principal].groupby(["region", "CLAVE DE LA INSTITUCION"]).size().to_string())

# %% [markdown]
# ## 2. Coordenadas (criterio 1)

# %%
z["lat"] = pd.to_numeric(z["LATITUD"], errors="coerce")
z["lon"] = pd.to_numeric(z["LONGITUD"], errors="coerce")
tr = Transformer.from_crs(config.CRS_GEO, config.CRS_METROS, always_xy=True)
z["x"], z["y"] = tr.transform(z["lon"].to_numpy(), z["lat"].to_numpy())
z["coord_num"] = np.isfinite(z["x"]) & np.isfinite(z["y"])


def decimales(s):
    return s.str.split(".").str[1].str.rstrip("0").str.len().fillna(0).astype(int)


z["imprecisa"] = (decimales(z["LATITUD"]) <= 3) | (decimales(z["LONGITUD"]) <= 3)

mun = pd.concat([gpd.read_file(GEO / r / "conjunto_de_datos" / f"{c}mun.shp") for c, r in REG.items()])
mun = mun.to_crs(config.CRS_METROS)
mun["clave"] = mun["CVE_ENT"] + mun["CVE_MUN"]
loc = pd.concat([gpd.read_file(GEO / r / "conjunto_de_datos" / f"{c}l.shp") for c, r in REG.items()])
loc = loc.to_crs(config.CRS_METROS)
loc["clave"] = loc["CVE_ENT"] + loc["CVE_MUN"] + loc["CVE_LOC"]
geo_mun = mun.dissolve("clave").geometry
geo_loc = loc.dissolve("clave").geometry

z["clave_mun"] = z["CLAVE DE LA ENTIDAD"] + z["CLAVE DEL MUNICIPIO"]
z["clave_loc"] = z["clave_mun"] + z["CLAVE DE LA LOCALIDAD"]
pts = gpd.GeoSeries(gpd.points_from_xy(z["x"], z["y"]), crs=config.CRS_METROS)


def dist_a(geo, claves):
    d = np.full(len(z), np.nan)
    for k, c in enumerate(claves):
        if z.at[k, "coord_num"] and c in geo.index:
            d[k] = geo[c].distance(pts[k])
    return d


z["d_mun"] = dist_a(geo_mun, z["clave_mun"])
z["d_loc"] = dist_a(geo_loc, z["clave_loc"])
z["en_mun"] = z["d_mun"] <= TOL
z["loc_discordante"] = z["d_loc"] > TOL  # NaN (sin polígono urbano) cuenta como no discordante

clave_xy = z["lat"].round(5).astype(str) + "," + z["lon"].round(5).astype(str)
z["xy_compartida"] = z.groupby(clave_xy)["clave_loc"].transform("nunique") > 1
z["xy_repetida"] = clave_xy.duplicated(keep=False)
z["coord_ok"] = z["coord_num"] & z["en_mun"] & ~z["xy_compartida"]

P = z[z.principal]
print(f"Coordenadas utilizables: {P.coord_ok.mean():.1%}  (en su municipio {P.en_mun.mean():.1%}, "
      f"compartidas con otra localidad {P.xy_compartida.sum()}, repetidas en total {P.xy_repetida.sum()}, "
      f"imprecisas {P.imprecisa.sum()}, localidad discordante {P.loc_discordante.sum()})")
print("Fuera de su municipio, distancia (m):", P.loc[~P.en_mun, "d_mun"].round(0).tolist())
print("Localidad discordante, distancia (m):", P.loc[P.loc_discordante, "d_loc"].describe().round(0).to_dict())

# %% [markdown]
# ## 3. Recursos (criterio 2) y capacidad

# %%
rec = pd.read_csv(DAT / "recursos_2025" / "BD ABIERTOS SECTORIAL 2025.csv", dtype=str, encoding="latin-1")
rec = rec.apply(lambda s: s.str.strip())
print("Recursos: CLUES vacías", rec["CLUES"].isna().sum(),
      "| repetidas", rec["CLUES"].dropna()[rec["CLUES"].dropna().duplicated()].tolist())
rec = rec[rec["CLUES"].isin(z["CLUES"])]
assert not rec["CLUES"].duplicated().any(), "CLUES repetida dentro del universo"


def suma(cols):
    return rec[cols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)


rec["consultorios"] = suma(["Consultorios de Medicina General", "Consultorios de Medicina Familiar"])
rec["medicos"] = suma(["Médicos Generales", "Médicos Familiares", "Pasantes de medicina"])
z = z.merge(rec[["CLUES", "consultorios", "medicos", "Institución", "Clave Municipio"]],
            on="CLUES", how="left", validate="one_to_one", indicator=True)
z["con_recursos"] = z.pop("_merge") == "both"
discrep = z.con_recursos & ((z["Institución"] != z["NOMBRE DE LA INSTITUCION"])
                            | (z["Clave Municipio"] != z["CLAVE DEL MUNICIPIO"]))
print("Institución o municipio distinto entre catálogo y recursos:", int(discrep.sum()))
z["imputada"] = ~z["con_recursos"]
for c in ["consultorios", "medicos"]:
    med = z.groupby(["CLAVE DE LA INSTITUCION", "NOMBRE DE TIPOLOGIA"])[c].transform("median")
    z[c] = z[c].fillna(med).fillna(0)
z["cap_ok"] = z["con_recursos"] & (z["consultorios"] > 0)
z["unidad"] = 1.0

P = z[z.principal]
crit1, crit2 = float(P.coord_ok.mean()), float(P.cap_ok.mean())
crit3 = float((P.coord_ok & P.cap_ok).mean())
print(f"Con recursos 2025: {P.con_recursos.mean():.1%}; consultorios > 0: {crit2:.1%}; "
      f"coordenadas y capacidad a la vez: {crit3:.1%}")
print(f"Consultorios gen./fam.: {P.consultorios.sum():.0f} (ceros {(P.consultorios == 0).sum()}); "
      f"médicos: {P.medicos.sum():.0f} (ceros {(P.medicos == 0).sum()}); "
      f"consultorios > 0 y médicos = 0: {((P.consultorios > 0) & (P.medicos == 0)).sum()}")
print(P.groupby("NOMBRE DE TIPOLOGIA")[["consultorios", "medicos"]].agg(["count", "sum", "median"]).to_string())

usar_clues = crit3 >= 0.90
print("DECISIÓN:", "se cambia a CLUES" if usar_clues else "se sigue con DENUE")

# %% [markdown]
# ## 4. Cotejo con DENUE (criterio 4)

# %%
VACIAS = {"DE", "LA", "EL", "LOS", "LAS", "DEL", "CENTRO", "SALUD", "CLINICA", "UNIDAD", "MEDICA",
          "MEDICO", "CONSULTORIO", "CONSULTORIOS", "FAMILIAR", "MEDICINA", "IMSS", "BIENESTAR", "ISSSTE",
          "ISSEMYM", "SAN", "SANTA", "URBANO", "RURAL", "SSA", "SECTOR", "PUBLICO", "INSTITUTO",
          "MEXICANO", "SEGURO", "SOCIAL", "UMF", "ISEM", "CEAPS", "CAAPS", "NUCLEOS", "BASICOS", "NUCLEO"}


def palabras(s):
    s = unicodedata.normalize("NFKD", str(s).upper()).encode("ascii", "ignore").decode()
    return {w for w in re.findall(r"[A-Z0-9]+", s) if w not in VACIAS and len(w) > 2}


def cotejar(cl, de, etiqueta):
    """Pares uno a uno a ≤ MATCH m: máximo número de pares y, entre ellos, mínima distancia."""
    a, b = cl[["x", "y"]].to_numpy(), de[["x", "y"]].to_numpy()
    cand = cKDTree(a).sparse_distance_matrix(cKDTree(b), MATCH, output_type="coo_matrix")
    costo = np.full((len(a), len(b)), 1e9)
    costo[cand.row, cand.col] = cand.data
    fi, co = linear_sum_assignment(costo)
    ok = costo[fi, co] <= MATCH
    fi, co, d = fi[ok], co[ok], costo[fi[ok], co[ok]]
    nombre = np.array([len(palabras(cl["NOMBRE DE LA UNIDAD"].iat[i]) & palabras(de["nom_estab"].iat[j])) > 0
                       for i, j in zip(fi, co)])
    # Pares ambiguos: alguno de los dos tenía más de un candidato a ≤ MATCH m.
    na = np.bincount(cand.row, minlength=len(a))
    nb = np.bincount(cand.col, minlength=len(b))
    ambiguo = (na[fi] > 1) | (nb[co] > 1)
    res = {
        "n_clues": len(a), "n_denue": len(b), "pares": int(ok.sum()),
        "frac_clues_con_pareja": round(ok.sum() / len(a), 3),
        "frac_denue_con_pareja": round(ok.sum() / len(b), 3),
        "dist_mediana_m": round(float(np.median(d)), 1),
        "dist_p90_m": round(float(np.percentile(d, 90)), 1),
        "frac_pares_con_nombre_comun": round(float(nombre.mean()), 3),
        "frac_pares_ambiguos": round(float(ambiguo.mean()), 3),
    }
    print(etiqueta, res)
    sin_cl = cl.drop(cl.index[fi])
    sin_de = de.drop(de.index[co])
    res["clues_sin_pareja_por_tipologia"] = sin_cl["NOMBRE DE TIPOLOGIA"].value_counts().head(10).to_dict()
    res["clues_sin_pareja_por_region"] = sin_cl["region"].value_counts().to_dict()
    res["denue_sin_pareja_por_region"] = sin_de["region"].value_counts().to_dict()
    # A qué distancia queda lo no emparejado de su vecino más cercano del otro lado.
    res["clues_sin_pareja_dist_vecino_mediana_m"] = round(float(np.median(cKDTree(b).query(sin_cl[["x", "y"]])[0])), 0)
    res["denue_sin_pareja_dist_vecino_mediana_m"] = round(float(np.median(cKDTree(a).query(sin_de[["x", "y"]])[0])), 0)
    emp = pd.DataFrame({"i": cl.index[fi], "j": de.index[co], "CLUES": cl["CLUES"].to_numpy()[fi],
                        "id_denue": de["id"].to_numpy()[co], "d": d, "nombre": nombre, "ambiguo": ambiguo})
    return res, emp, sin_cl, sin_de


den_base = acceso.oferta(fuente="denue")
den_abierta = acceso.oferta(abierta=True, fuente="denue")
Pq = z[z.principal & z.coord_ok].reset_index(drop=True)
Pub = z[z.pub & z.coord_ok].reset_index(drop=True)
cot_ab, emp_ab, sinc_ab, sind_ab = cotejar(Pq, den_abierta, "principal vs DENUE abierta:")
cot_pub, emp_pub, _, _ = cotejar(Pub, den_base, "pública completa vs DENUE base:")
if cot_ab["frac_clues_con_pareja"] < 0.5:
    print("ADVERTENCIA: menos del 50% de CLUES principal tiene pareja en DENUE abierta; investigar.")
print("DENUE abierta sin pareja (muestra):")
print(sind_ab[["nom_estab", "region", "per_ocu"]].sample(min(20, len(sind_ab)), random_state=0).to_string())
emp_ab.to_csv(INT / "cotejo_clues_denue_abierta.csv", index=False)

# %% [markdown]
# ## 5. ¿Qué tan buen proxy era `per_ocu`? (criterio 5)

# %%
obs = Pq.loc[emp_ab["i"], "con_recursos"].to_numpy()
pe = den_abierta.loc[emp_ab["j"], "per_ocu_num"].to_numpy(float)[obs]
rho_cons = spearmanr(pe, Pq.loc[emp_ab["i"], "consultorios"].to_numpy()[obs]).statistic
rho_med = spearmanr(pe, Pq.loc[emp_ab["i"], "medicos"].to_numpy()[obs]).statistic

# La rejilla de F3 se arma aquí (no se lee la del notebook 30, que depende de la oferta).
celdas = []
for r in REG.values():
    xy, v = acceso.demanda(r)
    celdas.append(pd.DataFrame({"x": xy[:, 0], "y": xy[:, 1], "psin": v, "region": r}))
celdas = pd.concat(celdas, ignore_index=True)
XY, PSIN = celdas[["x", "y"]].to_numpy(), celdas["psin"].to_numpy()
ARBOL_CEL = cKDTree(XY)


def en_dominio(df):
    """Alguna celda de demanda a ≤ CUENCA en recta (ver «Dominio» en el encabezado)."""
    xy = df[["x", "y"]].to_numpy(float)
    ok = np.isfinite(xy).all(axis=1)
    d = np.full(len(df), np.inf)
    d[ok] = ARBOL_CEL.query(xy[ok])[0]
    return d <= CUENCA


z["en_dominio"] = en_dominio(z)
Pq["en_dominio"] = en_dominio(Pq)
print(f"Principal con coordenadas utilizables dentro del dominio: {Pq.en_dominio.sum()} de {len(Pq)} "
      f"({Pq.loc[Pq.en_dominio, 'medicos'].sum() / Pq.medicos.sum():.1%} de los médicos); "
      f"fuera, por región: {Pq.loc[~Pq.en_dominio, 'region'].value_counts().to_dict()}")
cel_pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(celdas.x, celdas.y), crs=config.CRS_METROS)
celdas["clave_mun"] = gpd.sjoin_nearest(cel_pts, mun[["clave", "geometry"]], how="left").groupby(level=0)["clave"].first()
den_pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(den_abierta.x, den_abierta.y), crs=config.CRS_METROS)
den_abierta["clave_mun"] = gpd.sjoin_nearest(den_pts, mun[["clave", "geometry"]], how="left").groupby(level=0)["clave"].first()

tab = pd.DataFrame({"psin": celdas.groupby("clave_mun")["psin"].sum(),
                    "denue": den_abierta.groupby("clave_mun")["cap"].sum(),
                    "clues": Pq.groupby("clave_mun")["consultorios"].sum()}).fillna(0)
tab = tab[tab.psin > 0]
rho_mun = spearmanr(tab.denue / tab.psin, tab.clues / tab.psin).statistic
print(f"Spearman per_ocu vs consultorios: {rho_cons:.2f}; vs médicos: {rho_med:.2f} (n = {obs.sum()}); "
      f"capacidad por persona sin seguro, municipal, DENUE abierta vs CLUES: {rho_mun:.2f} (n = {len(tab)})")

# %% [markdown]
# ## 5b. Escenario ampliado: DIF y consultorios municipales

# %%
# Médicos por rango de per_ocu, calibrados en los pares principal–DENUE abierta observados.
cal = pd.DataFrame({"per_ocu": den_abierta.loc[emp_ab["j"], "per_ocu"].to_numpy()[obs],
                    "medicos": Pq.loc[emp_ab["i"], "medicos"].to_numpy()[obs]})
MED_POR_RANGO = cal.groupby("per_ocu")["medicos"].agg(["median", "size"])
print("Médicos por rango de per_ocu (calibración):")
print(MED_POR_RANGO.to_string())

SI_AMP = r"\bDIF\b|DESARROLLO INTEGRAL|MUNICIPAL|ALCALD|DELEGACI|AYUNTAMIENTO|\bH\.? ?AYTO|PERIFERIC"
NO_AMP = (r"REHABILITACI|U\.?B\.?R\.?I\.?S|BOMBER|PROTECCI|\bERUM\b|RESCATE|OFICINA|BODEGA|VACUNACI|"
          r"CENTRO SOCIAL|COMUNITARIO|ADICCI|ESPECIALI|PSICOL|\bWC\b|ALMAC|ADMINISTRA|CANINO|ANTIRR|"
          r"HOSPITAL|ISSS?TE|EQUINO|TERAPIA|ODONTOL|DENTAL|ADULTOS? MAYOR|3 EDAD|TERCERA EDAD")
C_amp = z[(z.principal | z.amp_clues) & z.coord_ok].reset_index(drop=True)
_, emp_amp, _, sind_amp = cotejar(C_amp, den_abierta, "principal + capa CLUES vs DENUE abierta:")
nom = sind_amp["nom_estab"].astype(str).str.upper()
capa_denue = sind_amp[nom.str.contains(SI_AMP) & ~nom.str.contains(NO_AMP)].copy()
capa_denue["medicos"] = capa_denue["per_ocu"].map(MED_POR_RANGO["median"]).fillna(1.0)
print(f"Capa DENUE: {len(capa_denue)} unidades, {capa_denue.medicos.sum():.0f} médicos estimados")
print(capa_denue[["nom_estab", "region", "per_ocu", "medicos"]].to_string())

capa_clues = z[z.amp_clues & z.coord_ok]
print(f"Capa CLUES: {len(capa_clues)} unidades, {capa_clues.medicos.sum():.0f} médicos "
      f"({(capa_clues.medicos > 0).sum()} con médicos > 0)")
amp = pd.concat([
    Pq.assign(fuente="clues", id=Pq["CLUES"]),
    capa_clues.assign(fuente="clues_dif_mun", id=capa_clues["CLUES"]),
    capa_denue.assign(fuente="denue_dif_mun", id=capa_denue["id"].astype(str),
                      **{"NOMBRE DE LA UNIDAD": capa_denue["nom_estab"]}),
], ignore_index=True)[["id", "fuente", "NOMBRE DE LA UNIDAD", "region", "x", "y", "medicos", "consultorios"]]
amp["en_dominio"] = en_dominio(amp)
amp.to_parquet(INT / "oferta_clues_ampliada.parquet")

# %% [markdown]
# ## 6. Impacto en F3, en recta a 30 min (criterio 6)
#
# Desde la decisión de Mario, la referencia es CLUES con médicos. Las unidades con capacidad 0
# se quitan antes de calcular (no aportan oferta y no deben contar como "alcanzable").

# %%
def f3(o, cap):
    o = o[(o[cap] > 0) & en_dominio(o)]
    fxy = o[["x", "y"]].to_numpy()
    c = o[cap].to_numpy(float)
    A, _, alcanza = acceso.e2sfca(XY, PSIN, fxy, c, CUENCA, "gauss")
    prom = c.sum() / PSIN.sum() * 1000
    return A < 0.5 * prom, ~alcanza


variantes = {
    "denue_base": (den_base, "cap"),
    "denue_abierta": (den_abierta, "cap"),
    "clues_medicos": (Pq, "medicos"),
    "clues_consultorios": (Pq, "consultorios"),
    "clues_unidad": (Pq, "unidad"),
    "clues_sin_discordantes": (Pq[~Pq.loc_discordante], "medicos"),
    "clues_ampliado": (amp, "medicos"),
}
bajos, imp = {}, {}
for k, (o, cap) in variantes.items():
    b, sin = f3(o, cap)
    bajos[k] = b
    imp[k] = {"unidades": int(((o[cap] > 0) & en_dominio(o)).sum()), "personas_bajo": round(float(PSIN[b].sum())),
              "personas_sin_unidad": round(float(PSIN[sin].sum())),
              "por_region_bajo": {r: round(float(PSIN[b & (celdas.region == r)].sum())) for r in REG.values()}}


def jaccard(a, b):
    return float(PSIN[a & b].sum() / PSIN[a | b].sum())


for k in variantes:
    imp[k]["jaccard_vs_denue_base"] = round(jaccard(bajos[k], bajos["denue_base"]), 3)
    imp[k]["jaccard_vs_clues_medicos"] = round(jaccard(bajos[k], bajos["clues_medicos"]), 3)
print(pd.DataFrame(imp).T.drop(columns="por_region_bajo").to_string())

entra = bajos["clues_medicos"] & ~bajos["denue_base"]
sale = ~bajos["clues_medicos"] & bajos["denue_base"]
cambio = pd.DataFrame({"entra": pd.Series(PSIN * entra).groupby(celdas["clave_mun"]).sum(),
                       "sale": pd.Series(PSIN * sale).groupby(celdas["clave_mun"]).sum()})
cambio = cambio.join(mun.set_index("clave")["NOMGEO"]).assign(neto=lambda d: d.entra - d.sale)
print("Municipios con más cambio (CLUES médicos contra DENUE base):")
print(cambio.reindex(cambio.neto.abs().sort_values(ascending=False).index).head(12).round(0).to_string())
estable = min(imp[k]["jaccard_vs_clues_medicos"] for k in ["clues_consultorios", "clues_sin_discordantes"])
print("Variantes CLUES estables (Jaccard ≥ 0.8):", estable >= 0.8,
      "| sin discordantes:", imp["clues_sin_discordantes"]["jaccard_vs_clues_medicos"],
      "| ampliado:", imp["clues_ampliado"]["jaccard_vs_clues_medicos"])

# %% [markdown]
# ## 7. Salidas

# %%
cols = ["CLUES", "NOMBRE DE LA UNIDAD", "NOMBRE DE LA INSTITUCION", "CLAVE DE LA INSTITUCION",
        "NOMBRE DE TIPOLOGIA", "region", "clave_mun", "MUNICIPIO", "clave_loc", "lat", "lon", "x", "y",
        "imprecisa", "loc_discordante", "xy_repetida", "coord_ok", "con_recursos", "imputada",
        "consultorios", "medicos", "principal", "pub", "en_dominio"]
z[cols].to_parquet(INT / "oferta_clues.parquet")

res = {
    "fuentes": {"catalogo": "ESTABLECIMIENTO_SALUD_202610.xlsx", "recursos": "Recursos Salud Sectorial 2025"},
    "universo": {"principal": int(z.principal.sum()), "publica_completa": int(z.pub.sum()),
                 "principal_por_region": z[z.principal].region.value_counts().to_dict(),
                 "principal_por_institucion": z[z.principal]["NOMBRE DE LA INSTITUCION"].value_counts().to_dict()},
    "criterio1_coordenadas_utilizables": round(crit1, 4),
    "criterio2_capacidad_observada": round(crit2, 4),
    "criterio3_ambos": round(crit3, 4),
    "decision_usar_clues": bool(usar_clues),
    "detalle_coordenadas": {"en_municipio": round(float(P.en_mun.mean()), 4),
                            "compartidas_otra_localidad": int(P.xy_compartida.sum()),
                            "repetidas": int(P.xy_repetida.sum()),
                            "imprecisas_3dec": int(P.imprecisa.sum()),
                            "localidad_discordante": int(P.loc_discordante.sum())},
    "capacidad": {"consultorios": float(P.consultorios.sum()), "medicos": float(P.medicos.sum()),
                  "ceros_consultorios": int((P.consultorios == 0).sum()), "ceros_medicos": int((P.medicos == 0).sum()),
                  "imputadas": int(P.imputada.sum()), "discrepancia_catalogo_recursos": int(discrep.sum())},
    "cotejo_principal_vs_denue_abierta": cot_ab,
    "cotejo_publica_vs_denue_base": cot_pub,
    "proxy_per_ocu": {"spearman_consultorios": round(float(rho_cons), 3),
                      "spearman_medicos": round(float(rho_med), 3), "n_pares": int(obs.sum()),
                      "spearman_cap_por_persona_municipal": round(float(rho_mun), 3), "n_municipios": int(len(tab))},
    "dominio": {"regla": "alguna celda de demanda a <= 1,667 m en recta; agregada tras correr",
                "principal_utilizable": int(len(Pq)), "principal_en_dominio": int(Pq.en_dominio.sum()),
                "frac_medicos_en_dominio": round(float(Pq.loc[Pq.en_dominio, "medicos"].sum() / Pq.medicos.sum()), 4),
                "fuera_por_region": Pq.loc[~Pq.en_dominio, "region"].value_counts().to_dict(),
                "ampliado_en_dominio": int(amp.en_dominio.sum()), "ampliado_total": int(len(amp))},
    "capacidad_principal": "medicos (generales + familiares + pasantes); decidido tras correr",
    "ampliado": {"capa_clues_unidades": int(len(capa_clues)), "capa_clues_medicos": float(capa_clues.medicos.sum()),
                 "capa_denue_unidades": int(len(capa_denue)), "capa_denue_medicos_estimados": float(capa_denue.medicos.sum()),
                 "medicos_por_rango_per_ocu": MED_POR_RANGO["median"].to_dict()},
    "impacto_f3_recta_30min": imp,
    "variantes_clues_estables": bool(estable >= 0.8),
}
(SALIDA / "oferta_clues.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

# %% [markdown]
# ## 8. Mapa del cotejo

# %%
fig, ax = plt.subplots(figsize=(9, 9))
mun.boundary.plot(ax=ax, color=ve.REJILLA, linewidth=0.4)
m_emp = Pq.index.isin(set(emp_ab["i"]))
ax.scatter(Pq.x[m_emp], Pq.y[m_emp], s=8, color=ve.AQUA, label=f"En ambas ({m_emp.sum()})", zorder=3)
ax.scatter(Pq.x[~m_emp], Pq.y[~m_emp], s=8, color=ve.AZUL, label=f"Solo CLUES ({(~m_emp).sum()})", zorder=3)
ax.scatter(sind_ab.x, sind_ab.y, s=12, color=ve.NARANJA, marker="x", linewidths=1,
           label=f"Solo DENUE ({len(sind_ab)})", zorder=4)
ax.set_aspect("equal")
ax.set_axis_off()
ax.legend(loc="upper left", frameon=False)
ve.titulo(fig, "CLUES (IMSS-Bienestar y SSA) contra DENUE público sin seguridad social",
          f"Pareja uno a uno a ≤ {MATCH:.0f} m · solo unidades con coordenadas utilizables")
ve.guardar(fig, FIG / "oferta_clues_cotejo.png")
