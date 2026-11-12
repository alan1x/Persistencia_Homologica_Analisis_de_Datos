# %% [markdown]
# # 27 — Verificaciones finales antes de corregir el reporte
#
# Comprueba afirmaciones del reporte que el notebook 22 no cubrió:
#
# 1. **Cuarto eje.** El notebook 13 compara 40/40/20 con 25/25/25/25, así que mezcla
#    agregar marginación con cambiar los pesos de los otros ejes. Aquí se compara con
#    tres ejes iguales y se mide si cambian las clínicas elegidas, que es lo que importa.
# 2. **Función objetivo.** El notebook 15 maximiza score × personas; los notebooks 17 y 19
#    maximizan solo personas.
# 3. **Curva de K y "núcleo estable".**
# 4. **Qué cuenta como clínica.** Composición de SCIAN 62 y huecos con redes más estrictas.
# 5. **Cifras sueltas:** tiempos, IM por nivel, casos extremos y figuras duplicadas.

# %%
import hashlib
import json
import pickle
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import pulp
from scipy.spatial import cKDTree

from lib import config, huecos

INT = config.INTERMEDIOS_DIR
REGIONES = ["CDMX", "EDOMEX"]
ZONAS = ["Norte", "Poniente", "ZMVM", "Oriente"]
res = {}
pk = pickle.load(open(INT / "soluciones_mclp_red.pkl", "rb"))


def zona(lat, lon):
    if lat > 19.7:
        return "Norte"
    if lon < -99.3:
        return "Poniente"
    if lon > -98.9:
        return "Oriente"
    return "ZMVM"


def mclp(pr, cands, demanda, K):
    """MCLP exacto sobre huecos, igual que el notebook 15. Devuelve (rangos, cubiertos)."""
    ids = pr["hueco_id"].astype(int).tolist()
    C = np.array([[c["tiempos"].get(h, np.inf) <= 15 for c in cands] for h in ids])
    prob = pulp.LpProblem("m", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x{j}", cat="Binary") for j in range(len(cands))]
    y = [pulp.LpVariable(f"y{i}", cat="Binary") for i in range(len(ids))]
    prob += pulp.lpSum(float(d) * v for d, v in zip(demanda, y))
    prob += pulp.lpSum(x) == min(K, len(cands))
    for i in range(len(ids)):
        prob += y[i] <= pulp.lpSum(x[j] for j in np.where(C[i])[0])
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    sel = sorted(c["rank"] for c, v in zip(cands, x) if v.value() > 0.5)
    cub = np.array([v.value() > 0.5 for v in y])
    return sel, cub


# %% [markdown]
# ## 1. Cuarto eje

# %%
for r in REGIONES:
    sc = pd.read_parquet(INT / f"huecos_score_{r}.parquet")
    pr = pd.read_parquet(INT / f"huecos_prioritarios_{r}.parquet")
    cands = pk["resultados_red"][r]
    s404020 = 0.4 * sc["rank_tiempo"] + 0.4 * sc["rank_psinder"] + 0.2 * sc["rank_pers"]
    s3 = (sc["rank_tiempo"] + sc["rank_psinder"] + sc["rank_pers"]) / 3
    s4 = sc["score"]
    r4 = s4.rank(ascending=False, method="min")

    def cambio(ref):
        rr = ref.rank(ascending=False, method="min")
        d = rr - r4
        return {"suben_3_o_mas": int((d >= 3).sum()), "im_medio_suben": round(float(sc.loc[d >= 3, "indice_marg"].mean()), 3),
                "top10_comunes": len(set(ref.nlargest(10).index) & set(s4.nlargest(10).index))}

    # El filtro de prioridad sin marginación
    p60p = sc["pob_sin_salud"].quantile(0.6)
    sin_im = (sc["tiempo_est_min"] > 10) | (sc["pob_sin_salud"] > p60p) | (sc["pers_m"] > 400)
    s3p = s3.set_axis(sc["hueco_id"])
    d4 = (pr["score"] * pr["pob_sin_salud"]).values
    d3 = pr["hueco_id"].map(s3p).values * pr["pob_sin_salud"].values
    Ks = {"CDMX": 7, "EDOMEX": 8}[r]
    con, cub4 = mclp(pr, cands, d4, Ks)
    sin, cub3 = mclp(pr, cands, d3, Ks)
    solo_persona, _ = mclp(pr, cands, pr["pob_sin_salud"].values, Ks)
    res[f"eje4_{r}"] = {
        "reporte_40_40_20": cambio(s404020), "tres_ejes_iguales": cambio(s3),
        "prioritarios_sin_filtro_im": int(sin_im.sum()), "prioritarios_con_filtro_im": len(pr),
        f"K{Ks}_con_4_ejes": con, f"K{Ks}_con_3_ejes": sin, f"K{Ks}_solo_personas": solo_persona,
        "clinicas_que_cambian_3_vs_4": len(set(con) - set(sin)),
        "correlacion_im_con_pct_sin_seguro": round(float(sc["indice_marg"].corr(sc["pct_sin_salud_prom"], method="spearman")), 3),
        "psin_cubierta_4_ejes": int(pr.loc[cub4, "pob_sin_salud"].sum()), "psin_cubierta_3_ejes": int(pr.loc[cub3, "pob_sin_salud"].sum()),
        "im_medio_cubiertos_4_ejes": round(float(pr.loc[cub4, "indice_marg"].mean()), 3),
        "im_medio_cubiertos_3_ejes": round(float(pr.loc[cub3, "indice_marg"].mean()), 3),
        "im_medio_no_cubiertos_4_ejes": round(float(pr.loc[~cub4, "indice_marg"].mean()), 3),
    }

# %% [markdown]
# ## 2 y 3. Función objetivo, curva de K y núcleo estable

# %%
pr = pd.read_parquet(INT / "huecos_prioritarios_CDMX.parquet")
c = pk["resultados_red"]["CDMX"]
tot = pr["pob_sin_salud"].sum()
curva = {}
for K in range(5, 11):
    a, ca = mclp(pr, c, pr["pob_sin_salud"].values, K)
    b, cb = mclp(pr, c, (pr["score"] * pr["pob_sin_salud"]).values, K)
    curva[K] = {"solo_personas": a, "pct_solo_personas": round(pr.loc[ca, "pob_sin_salud"].sum() / tot * 100, 1),
                "score_por_personas": b, "pct_score_por_personas": round(pr.loc[cb, "pob_sin_salud"].sum() / tot * 100, 1)}
res["curva_K_CDMX"] = curva
res["nucleo_solo_personas"] = sorted(set.intersection(*[set(v["solo_personas"]) for v in curva.values()]))
res["nucleo_score_por_personas"] = sorted(set.intersection(*[set(v["score_por_personas"]) for v in curva.values()]))
res["seleccion_guardada_K7"] = sorted(c[j]["rank"] for j in pk["soluciones"]["CDMX"][7]["sel_idx"])
res["seleccion_guardada_K5"] = sorted(c[j]["rank"] for j in pk["soluciones"]["CDMX"][5]["sel_idx"])

pr = pd.read_parquet(INT / "huecos_prioritarios_EDOMEX.parquet")
pr["zona"] = [zona(a, b) for a, b in zip(pr["lat"], pr["lon"])]
cands = pk["resultados_red"]["EDOMEX"]
subr = {}
for z in ZONAS:
    cz = [k for k in cands if zona(k["lat_clinica"], k["lon_clinica"]) == z]
    t = pr[pr["zona"] == z]
    fila = {"huecos": len(t), "candidatos": len(cz), "psin_conteo_reporte": int(t["pob_sin_salud"].sum())}
    if cz:
        a, ca = mclp(t, cz, t["pob_sin_salud"].values, 3)
        b, cb = mclp(t, cz, (t["score"] * t["pob_sin_salud"]).values, 3)
        fila |= {"solo_personas": a, "cubre": int(t.loc[ca, "pob_sin_salud"].sum()), "score_por_personas": b,
                 "cubre_con_score": int(t.loc[cb, "pob_sin_salud"].sum())}
    subr[z] = fila
res["EDOMEX_objetivo_por_zona"] = subr

# %% [markdown]
# ## 4. ¿Qué cuenta como clínica?

# %%
sal = pd.concat([pd.read_parquet(INT / f"salud_{r}.parquet") for r in REGIONES], ignore_index=True)
cod = sal["codigo_act"].astype(str)
grupo = np.select(
    [cod.str.startswith("6212"), cod.str.startswith("6211"), cod.str.startswith("622"), cod.str.startswith("621"),
     cod.str.startswith("623") | cod.str.startswith("624")],
    ["Dentistas", "Consultorios y clínicas médicas", "Hospitales", "Otros servicios ambulatorios", "Asistencia social"], "Otro")
res["composicion_scian62"] = {k: int(v) for k, v in pd.Series(grupo).value_counts().items()}

medico = cod.str.startswith("6211") | cod.str.startswith("622")
publico = medico & sal["nombre_act"].str.contains("sector p[uú]blico", case=False, regex=True)
for r in REGIONES:
    mask_r = sal["region"] == r
    base_p = sal.loc[mask_r, ["x", "y"]].to_numpy()
    base = huecos.extraer_huecos(huecos.complejo(base_p), base_p, 200)
    prr = pd.read_parquet(INT / f"huecos_prioritarios_{r}.parquet")
    prio = base[np.isin(base["pers"].round(3), prr["pers_m"].round(3))]
    fila = {}
    for nombre, m in {"médicos y hospitales": medico, "solo públicos": publico}.items():
        P = sal.loc[mask_r & m, ["x", "y"]].drop_duplicates().to_numpy()
        h = huecos.extraer_huecos(huecos.complejo(P), P, 200)
        dentro = cKDTree(h[["cx", "cy"]].values).query(prio[["cx", "cy"]].values)[0] < prio["death"].values
        fila[nombre] = {"establecimientos": len(P), "huecos_200m": len(h), "persistencia_max_m": round(float(h["pers"].max())),
                        "mediana_pers_m": round(float(h["pers"].median())),
                        "prioritarios_con_hueco_de_esta_red_dentro_del_disco": int(dentro.sum()), "prioritarios": len(prio)}
    res[f"redes_{r}"] = fila

# %% [markdown]
# ## 5. Cifras sueltas

# %%
for r in REGIONES:
    sc = pd.read_parquet(INT / f"huecos_score_{r}.parquet")
    cl = pd.read_parquet(INT / f"clusters_{r}.parquet")
    top = cl.nlargest(1, "psin_total").iloc[0]
    res[f"cifras_{r}"] = {
        "habitados": len(sc), "tiempo_top10_min": sc["tiempo_est_min"].nlargest(10).round(1).tolist(),
        "mas_de_15_min": int((sc["tiempo_est_min"] > 15).sum()), "mediana_min": round(float(sc["tiempo_est_min"].median()), 1),
        "urgencia": sc["urgencia"].value_counts().to_dict(),
        "im_medio_por_urgencia": sc.groupby("urgencia")["indice_marg"].mean().round(2).to_dict(),
        "im_medio_global": round(float(sc["indice_marg"].mean()), 2),
        "cluster_mayor": {"rank": int(top["rank_cluster"]), "huecos": int(top["n_huecos"]), "psin": int(top["psin_total"]),
                          "pob": int(top["pob_total"]), "pct": round(float(top["psin_total"] / top["pob_total"] * 100), 1),
                          "tiempo_max": round(float(top["tiempo_max"]), 1)},
    }


def md5(nombre):
    return hashlib.md5((config.FIGURAS_DIR / nombre).read_bytes()).hexdigest()


res["figuras_identicas"] = {f"{a} == {b}": md5(a) == md5(b) for a, b in [
    ("matriz_riesgo_CDMX.png", "impacto_censal_CDMX.png"), ("matriz_riesgo_EDOMEX.png", "impacto_censal_EDOMEX.png")]}

(config.OUTPUTS_DIR / "auditoria" / "verificaciones.json").write_text(
    json.dumps(res, indent=2, ensure_ascii=False, default=int), encoding="utf-8")
print(json.dumps(res, indent=1, ensure_ascii=False, default=int))
