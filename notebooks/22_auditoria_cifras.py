# %% [markdown]
# # 22 — Auditoría: las cifras del reporte contra el código y los datos
#
# Compara lo que dicen `reporte/trabajo_final.md` y `reporte/paper.typ` con lo que
# producen los archivos intermedios guardados. No modifica nada de lo anterior.
# Escribe en `outputs/auditoria/`.

# %%
import itertools
import json
import pickle
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

from lib import censo, config, huecos, tda

SALIDA = config.OUTPUTS_DIR / "auditoria"
SALIDA.mkdir(exist_ok=True)
INT = config.INTERMEDIOS_DIR
REGIONES = ["CDMX", "EDOMEX"]
res = {}

# %% [markdown]
# ## 1. ¿De qué complejo salen los huecos que llegan al MCLP?

# %%
agebs, cat = {}, {}
for r in REGIONES:
    sal = pd.read_parquet(INT / f"salud_{r}.parquet")
    P = sal[["x", "y"]].to_numpy()
    w = tda.pesos_desde_per_ocu(sal)
    radio_medio = float(np.sqrt(w).mean())
    cla = huecos.extraer_huecos(huecos.complejo(P), P, 200)
    pon = huecos.extraer_huecos(huecos.complejo(P, w), P, 200, w)
    uni_w = np.full(len(P), radio_medio ** 2)
    uni = huecos.extraer_huecos(huecos.complejo(P, uni_w), P, 200, uni_w)
    cat[r] = {"P": P, "sal": sal, "cla": cla, "pon": pon, "w": w}

    cen = pd.read_parquet(INT / f"huecos_censal_{r}.parquet")
    coincide_cla = np.isin(cen["pers_m"].round(3), cla["pers"].round(3)).mean()
    coincide_pon = np.isin(cen["pers_m"].round(3), pon["pers"].round(3)).mean()
    d_baric = np.hypot(cla["cx"] - cla["bx"], cla["cy"] - cla["by"])
    d_vacio = cKDTree(P).query(cla[["cx", "cy"]].values)[0]
    res[r] = {
        "n_puntos": len(P),
        "coordenadas_unicas": len(np.unique(P, axis=0)),
        "huecos_clasico": len(cla),
        "huecos_laguerre": len(pon),
        "huecos_pesos_uniformes": len(uni),
        "radio_uniforme_m": round(radio_medio, 1),
        "laguerre_nacimiento_recortado": int(pon["recortado"].sum()),
        "filas_huecos_censal": len(cen),
        "censal_coincide_con_clasico": round(float(coincide_cla), 3),
        "censal_coincide_con_laguerre": round(float(coincide_pon), 3),
        "max_error_disco_vacio_m": round(float((d_vacio - cla["death"]).abs().max()), 2),
        "baricentro_vs_centro_mediana_m": round(float(d_baric.median()), 0),
        "death_entre_pers_mediana": round(float((cla["death"] / cla["pers"]).median()), 2),
    }
    print(r, json.dumps(res[r], ensure_ascii=False, indent=1))

# %% [markdown]
# ## 2. ¿Cuánta gente hay dentro de los huecos?
#
# El reporte asigna a un hueco **toda** la población de cualquier AGEB que toque un
# disco de radio `pers/2`. Una AGEB puede tocar varios huecos y entonces se suma más
# de una vez. Se calcula lo mismo sin repetir, y una versión por área dentro del
# disco vacío real (radio = muerte).

# %%
TR = Transformer.from_crs(config.CRS_GEO, config.CRS_METROS, always_xy=True)

def poblacion_real(df, ageb_m, radio, por_area):
    """Personas sin seguro en la unión de discos. Por área reparte la AGEB uniforme."""
    x, y = TR.transform(df["lon"].values, df["lat"].values)
    discos = gpd.GeoSeries(gpd.points_from_xy(x, y), crs=config.CRS_METROS).buffer(radio)
    union = discos.union_all()
    toca = ageb_m[ageb_m.intersects(union)]
    if not por_area:
        return int(toca["PSINDER"].sum())
    frac = toca.geometry.intersection(union).area / toca.geometry.area
    return int((toca["PSINDER"] * frac).sum())

for r in REGIONES:
    ageb = censo.construir_ageb_enriquecido(r)
    ageb = ageb[ageb["POBTOT"].fillna(0) > 0].to_crs(config.CRS_METROS)
    agebs[r] = ageb
    sc = pd.read_parquet(INT / f"huecos_score_{r}.parquet")
    pr = pd.read_parquet(INT / f"huecos_prioritarios_{r}.parquet")
    cen = pd.read_parquet(INT / f"huecos_censal_{r}.parquet")
    hab = cen[cen["pob_afectada"] > 0]
    res[r].update({
        "habitados": len(hab),
        "psin_suma_huecos_habitados": int(hab["pob_sin_salud"].sum()),
        "psin_sin_repetir_agebs": poblacion_real(hab, ageb, hab["radio_m"].values, False),
        "psin_por_area_radio_pers2": poblacion_real(hab, ageb, hab["radio_m"].values, True),
        "psin_por_area_disco_vacio": poblacion_real(hab, ageb, hab["death_m"].values, True),
        "prioritarios": len(pr),
        "psin_prioritarios_suma": int(pr["pob_sin_salud"].sum()),
        "psin_prioritarios_sin_repetir": poblacion_real(pr, ageb, pr["radio_m"].values, False),
        "psin_censo_region": int(ageb["PSINDER"].sum()),
    })
    # Lo que el reporte dice para Laguerre: 62/118 y 180/241 habitados
    filas = []
    for _, h in cat[r]["pon"].iterrows():
        filas.append({"pers": h["pers"], "centroide": (h["bx"], h["by"]),
                      "birth": h["birth"], "death": h["death"]})
    cruce = censo.cruzar_huecos_con_censo(filas, ageb.to_crs("EPSG:4326"), r, 200.0)
    res[r]["laguerre_habitados_recalculado"] = int((cruce["pob_afectada"] > 0).sum())
    res[r]["laguerre_psin_recalculado"] = int(cruce["pob_sin_salud"].sum())

    # Solapamiento de ubicación: ¿los prioritarios (clásico) también son huecos en Laguerre?
    x, y = TR.transform(pr["lon"].values, pr["lat"].values)
    d, _ = cKDTree(cat[r]["pon"][["bx", "by"]].values).query(np.column_stack([x, y]))
    res[r]["prioritarios_con_hueco_laguerre_a_500m"] = int((d < 500).sum())

# %% [markdown]
# ## 3. La solución guardada: modo de cobertura y optimalidad de K=7

# %%
pk = pickle.load(open(INT / "soluciones_mclp_red.pkl", "rb"))
for r in REGIONES:
    cands = pk["resultados_red"][r]
    res[r]["modo_candidatos"] = sorted({c["modo"] for c in cands})
sol = pk["soluciones"]["CDMX"][7]
pr = pd.read_parquet(INT / "huecos_prioritarios_CDMX.parquet")
C = np.asarray(sol["C_mat"]).astype(bool)
dem = (pr["score"] * pr["pob_sin_salud"]).values
psin = pr["pob_sin_salud"].values

def valor(combo):
    return dem[C[:, list(combo)].any(axis=1)].sum()

mejor = max(itertools.combinations(range(C.shape[1]), 7), key=valor)
cub = C[:, sol["sel_idx"]].any(axis=1)
tiempos = np.array([[c["tiempos"].get(int(h), np.inf) for c in pk["resultados_red"]["CDMX"]]
                    for h in pr["hueco_id"]])
pr_cub = pr[cub]
res["MCLP_CDMX"] = {
    "seleccion_guardada": sorted(int(j) for j in sol["sel_idx"]),
    "optimo_por_fuerza_bruta": sorted(int(j) for j in mejor),
    "demanda_guardada": round(float(valor(sol["sel_idx"])), 1),
    "demanda_optima": round(float(valor(mejor)), 1),
    "psin_cubiertos": int(psin[cub].sum()),
    "psin_cubiertos_sin_repetir": poblacion_real(pr_cub, agebs["CDMX"], pr_cub["radio_m"].values, False),
    "psin_cubiertos_por_area_disco": poblacion_real(pr_cub, agebs["CDMX"], pr_cub["death_m"].values, True),
    "pct_prioritario": round(float(psin[cub].sum() / psin.sum() * 100), 1),
    "cobertura_igual_a_tiempo_15": bool(((tiempos <= 15) == C).all()),
    "radio_efectivo_m": round(15 * 4500 / 60 / 1.35, 0),
    "incrementos_K5_K10_pp": [5.6, 5.3, 5.1, 4.0, 3.0],
}

# %% [markdown]
# ## 4. Composición de "salud" y resultado sin asistencia social

# %%
for r in REGIONES:
    sal = cat[r]["sal"]
    sub = sal["codigo_act"].str[:3].value_counts().to_dict()
    solo = sal[sal["codigo_act"].str[:3].isin(["621", "622"])]
    Pm = solo[["x", "y"]].to_numpy()
    n = len(huecos.extraer_huecos(huecos.complejo(Pm), Pm, 200))
    res[r]["subsectores"] = sub
    res[r]["huecos_solo_621_622"] = n

# %%
(SALIDA / "auditoria.json").write_text(
    json.dumps(res, ensure_ascii=False, indent=2, default=int), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=2, default=int))

# %% [markdown]
# ## 5. EDOMEX: ¿cuántas clínicas hay y por qué Oriente queda fuera?
#
# El MCLP subregional solo puede elegir entre los 20 candidatos globales, que son los
# clusters con mejor rango. Una zona sin clusters en ese corte se queda sin candidatos,
# aunque sus propios clusters estén disponibles.

# %%
def subregion(lat, lon):
    if lat > 19.7:
        return "Norte"
    if lon < -99.3:
        return "Poniente"
    if lon > -98.9:
        return "Oriente"
    return "ZMVM"


sub = pickle.load(open(INT / "clinicas_subregionales_EDOMEX.pkl", "rb"))
cl = pd.read_parquet(INT / "clusters_EDOMEX.parquet")
cl["zona"] = [subregion(a, b) for a, b in zip(cl["lat_centroide"], cl["lon_centroide"])]
cand = pk["resultados_red"]["EDOMEX"]
res["EDOMEX_subregional"] = {
    "clinicas_guardadas": len(sub["clinicas_sub"]),
    "huecos_cubiertos": sub["n_cub_sub"],
    "clinicas_por_zona": pd.Series([c["subregion"] for c in sub["clinicas_sub"]]).value_counts().to_dict(),
    "candidatos_por_zona": pd.Series([subregion(c["lat_clinica"], c["lon_clinica"]) for c in cand]).value_counts().to_dict(),
    "clusters_por_zona": cl["zona"].value_counts().to_dict(),
    "oriente_mejor_rango_cluster": int(cl.loc[cl["zona"] == "Oriente", "rank_cluster"].min()),
    "oriente_psin_top3_clusters": int(cl[cl["zona"] == "Oriente"].nlargest(3, "psin_total")["psin_total"].sum()),
    "oriente_psin_total": int(cl.loc[cl["zona"] == "Oriente", "psin_total"].sum()),
}
print(json.dumps(res["EDOMEX_subregional"], ensure_ascii=False, indent=2))
(SALIDA / "auditoria.json").write_text(
    json.dumps(res, ensure_ascii=False, indent=2, default=int), encoding="utf-8")
