# %% [markdown]
# # 26 — Modelo revisado: personas contadas una vez y prioridades más firmes
#
# ## Criterios fijados antes de correr
#
# **Una sola definición de personas.** `PSINDER` de cada AGEB se reparte uniforme en una
# rejilla de 100 m. Cada celda se cuenta una vez.
#
# - **Vacío alcanzado:** personas sin seguro dentro de los discos vacíos prioritarios
#   (radio = muerte) y a ≤ 833 m de una clínica nueva.
# - **Acceso nuevo:** personas sin seguro de toda la región que hoy están a > 833 m de
#   cualquier establecimiento, de ambos estados, y quedarían a ≤ 833 m.
#
# **Modelos:**
#
# - **Reporte:** la solución guardada (7 en CDMX, 8 en EDOMEX).
# - **Personas:** MCLP sobre celdas, sin pesos, con todos los clusters como candidatos.
# - **Ponderado:** igual, con peso score × S × A. S es la supervivencia del hueco con
#   σ = 50 m (notebook 24). A = min(1, actividad / 0.25), con la actividad del notebook 25.
# - **Sin topología:** voraz sobre puntos de AGEB, maximizando acceso nuevo. No usa huecos.
#
# **Preguntas y criterio de decisión:**
#
# 1. ¿Supera al azar? Sí, si el vacío alcanzado supera el p95 de 2,000 sorteos con el mismo
#    K y la misma estructura por zonas. "Personas" optimiza esa medida, así que este
#    resultado es un mínimo exigible, no una validación independiente.
# 2. ¿Los pesos dan prioridades más firmes? Sí, si "Ponderado" alcanza más personas que
#    "Personas" en discos recalculados con ruido nuevo (30 réplicas, σ = 50 m, otras
#    semillas) y el intervalo pareado del 95% de la diferencia excluye a cero.
# 3. ¿Oriente tiene solución? Se reportan las personas alcanzadas con sus 3 clínicas.
# 4. ¿La topología ayuda a dar acceso nuevo? Se compara con "Sin topología" con el mismo K.
#    No se fija un umbral: se reporta la razón.
#
# Cualquier cambio posterior a estos criterios se declara en el reporte.
#
# **Agregado después de ver los primeros resultados:** como casi nadie resultó estar a
# más de 833 m de un establecimiento, se repite "acceso nuevo" contando solo consultorios
# médicos y hospitales, y solo la red pública. También se calcula la población exacta de
# los discos con su centro verdadero, porque el notebook 22 usó el baricentro.

# %%
import json
import pickle
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pulp
import shapely
from joblib import Parallel, delayed
from scipy.spatial import cKDTree

from lib import censo, config, huecos, viz_eval as ve

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
REGIONES = ["CDMX", "EDOMEX"]
ZONAS = ["Norte", "Poniente", "ZMVM", "Oriente"]
RADIO = 15 * (4500 / 60) / 1.35  # 833 m: 15 min, 4.5 km/h, rodeo 1.35
PASO = 100.0
N_AZAR = 2000
N_OOS = 30
COLOR = {"Reporte": ve.GRIS, "Personas": ve.AZUL, "Ponderado": ve.NARANJA, "Sin topología": ve.AQUA}


def zona(lat, lon):
    if lat > 19.7:
        return "Norte"
    if lon < -99.3:
        return "Poniente"
    if lon > -98.9:
        return "Oriente"
    return "ZMVM"


def rejilla(ageb):
    """Reparte PSINDER de cada AGEB entre los puntos de una rejilla dentro de ella."""
    xy, val = [], []
    for geom, psin in zip(ageb.geometry, ageb["PSINDER"].fillna(0).to_numpy(float)):
        x0, y0, x1, y1 = geom.bounds
        xs = np.arange(np.floor(x0 / PASO), np.ceil(x1 / PASO) + 1) * PASO
        ys = np.arange(np.floor(y0 / PASO), np.ceil(y1 / PASO) + 1) * PASO
        xx, yy = np.meshgrid(xs, ys)
        dentro = shapely.contains_xy(geom, xx.ravel(), yy.ravel())
        if dentro.any():
            pts = np.column_stack([xx.ravel()[dentro], yy.ravel()[dentro]])
        else:
            p = geom.representative_point()
            pts = np.array([[p.x, p.y]])
        xy.append(pts)
        val.append(np.full(len(pts), psin / len(pts)))
    return np.vstack(xy), np.concatenate(val)


def resolver(cubre, peso, cuotas=None, K=None, zonas_cand=None):
    """MCLP exacto. Las celdas con la misma cobertura se agrupan para acelerar."""
    filas = cubre.any(axis=1) & (peso > 0)
    firmas, inv = np.unique(cubre[filas], axis=0, return_inverse=True)
    dem = np.bincount(inv.ravel(), weights=peso[filas])
    prob = pulp.LpProblem("mclp", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x{j}", cat="Binary") for j in range(cubre.shape[1])]
    y = [pulp.LpVariable(f"y{i}", lowBound=0, upBound=1) for i in range(len(firmas))]
    prob += pulp.lpSum(d * v for d, v in zip(dem, y))
    if cuotas:
        for z, k in cuotas.items():
            prob += pulp.lpSum(x[j] for j in np.where(zonas_cand == z)[0]) == min(k, int((zonas_cand == z).sum()))
    else:
        prob += pulp.lpSum(x) == K
    for i, f in enumerate(firmas):
        prob += y[i] <= pulp.lpSum(x[j] for j in np.where(f)[0])
    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=300))
    assert pulp.LpStatus[prob.status] == "Optimal", pulp.LpStatus[prob.status]
    return [j for j, v in enumerate(x) if v.value() > 0.5]


def voraz(cands, celdas_xy, peso, K):
    """Selección voraz para maximizar el peso cubierto, sin ninguna información de huecos."""
    arbol = cKDTree(celdas_xy)
    cubre = arbol.query_ball_point(cands, RADIO)
    restante, sel = peso.copy(), []
    for _ in range(K):
        gan = np.array([restante[c].sum() if len(c) else 0.0 for c in cubre])
        j = int(gan.argmax())
        sel.append(j)
        restante[cubre[j]] = 0.0
    return sel


def replica_oos(P, base_prio, celdas_xy, semilla):
    """Celdas dentro de los discos que siguen existiendo tras agregar ruido."""
    rng = np.random.default_rng(semilla)
    Q = P + rng.normal(0, 50, P.shape)
    h = huecos.extraer_huecos(huecos.complejo(Q), Q, 200)
    d = np.hypot(h["cx"].values[:, None] - base_prio["cx"].values,
                 h["cy"].values[:, None] - base_prio["cy"].values)
    vivo = (d < np.maximum(100.0, base_prio["death"].values / 2)).any(axis=1)
    h = h[vivo]
    arbol = cKDTree(celdas_xy)
    masc = np.zeros(len(celdas_xy), bool)
    for idx in arbol.query_ball_point(h[["cx", "cy"]].values, h["death"].values):
        masc[idx] = True
    return masc


# %%
pk = pickle.load(open(INT / "soluciones_mclp_red.pkl", "rb"))
sub = pickle.load(open(INT / "clinicas_subregionales_EDOMEX.pkl", "rb"))
SALUD = {r: pd.read_parquet(INT / f"salud_{r}.parquet") for r in REGIONES}
P_todos = {r: SALUD[r][["x", "y"]].to_numpy() for r in REGIONES}
arbol_todos = cKDTree(np.vstack(list(P_todos.values())))
_sal = pd.concat(SALUD.values(), ignore_index=True)
_cod = _sal["codigo_act"].astype(str)
_medico = _cod.str.startswith("6211") | _cod.str.startswith("622")
REDES = {
    "Todos los establecimientos": arbol_todos,
    "Consultorios médicos y hospitales": cKDTree(_sal.loc[_medico, ["x", "y"]].to_numpy()),
    "Solo públicos (consultorios y hospitales)": cKDTree(_sal.loc[_medico & _sal["nombre_act"].str.contains("sector p[uú]blico", case=False, regex=True), ["x", "y"]].to_numpy()),
}
print({k: v.n for k, v in REDES.items()}, flush=True)
print(_sal.loc[_medico].groupby(["codigo_act", "nombre_act"]).size().to_string(), flush=True)
c7 = pk["resultados_red"]["CDMX"]
REPORTE = {
    "CDMX": np.array([[c7[j]["x_clinica"], c7[j]["y_clinica"]] for j in pk["soluciones"]["CDMX"][7]["sel_idx"]]),
    "EDOMEX": np.array([[c["x_clinica"], c["y_clinica"]] for c in sub["clinicas_sub"]]),
}

salida, tablas, azares, mapas = {}, {}, {}, {}
for r in REGIONES:
    P = P_todos[r]
    otro = P_todos["EDOMEX" if r == "CDMX" else "CDMX"]
    base = huecos.extraer_huecos(huecos.complejo(P), P, 200)
    pr = pd.read_parquet(INT / f"huecos_prioritarios_{r}.parquet")
    cen = pd.read_parquet(INT / f"huecos_censal_{r}.parquet")
    hab = base[np.isin(base["pers"].round(3), cen.loc[cen["pob_afectada"] > 0, "pers_m"].round(3))]
    prio = base[np.isin(base["pers"].round(3), pr["pers_m"].round(3))].copy().reset_index(drop=True)
    prio["k"] = prio["pers"].round(3)
    rob = pd.read_csv(SALIDA / f"robustez_real_{r}.csv").assign(k=lambda d: d["pers"].round(3))
    sec = pd.read_csv(SALIDA / f"sectores_discos_{r}.csv").assign(k=lambda d: d["pers"].round(3))
    prio = (prio.merge(pr.assign(k=pr["pers_m"].round(3))[["k", "score"]], on="k")
            .merge(rob[["k", "sobrevive_ruido_50", "sobrevive_ruido_100"]], on="k")
            .merge(sec[["k", "ratio"]], on="k"))
    assert len(prio) == len(pr)

    # Comprobación: discos prioritarios que contienen establecimientos del otro estado
    frontera = cKDTree(otro).query(prio[["cx", "cy"]].values, distance_upper_bound=1e5)[0] < prio["death"].values

    # Rejilla de personas sin seguro
    ageb = censo.construir_ageb_enriquecido(r)
    ageb = ageb[ageb["POBTOT"].fillna(0) > 0].to_crs(config.CRS_METROS)
    xy, psin = rejilla(ageb)
    assert abs(psin.sum() - ageb["PSINDER"].sum()) < 1
    arbol_c = cKDTree(xy)
    d0 = arbol_todos.query(xy)[0]
    sin_acceso = d0 > RADIO

    def union_discos(t):
        m = np.zeros(len(xy), bool)
        for idx in arbol_c.query_ball_point(t[["cx", "cy"]].values, t["death"].values):
            m[idx] = True
        return m

    m_hab, m_prio = union_discos(hab), union_discos(prio)

    # Peso de celda: el mayor peso entre los discos que la contienen
    def peso_celdas(S, umbral):
        w_h = prio["score"].values * prio[S].values * np.minimum(1, prio["ratio"].values / umbral)
        w = np.zeros(len(xy))
        for idx, v in zip(arbol_c.query_ball_point(prio[["cx", "cy"]].values, prio["death"].values), w_h):
            if len(idx):
                w[idx] = np.maximum(w[idx], v)
        return w

    # Candidatos: todos los clusters
    cl = pd.read_parquet(INT / f"clusters_{r}.parquet").sort_values("rank_cluster").reset_index(drop=True)
    C = cl[["cx_utm", "cy_utm"]].to_numpy()
    zc = np.array([zona(a, b) for a, b in zip(cl["lat_centroide"], cl["lon_centroide"])])
    d_cand = np.array([np.hypot(xy[:, 0] - x, xy[:, 1] - y) <= RADIO for x, y in C]).T

    def metricas(clin):
        d = cKDTree(clin).query(xy)[0] <= RADIO
        return {"vacio": float(psin[m_prio & d].sum()), "acceso_nuevo": float(psin[sin_acceso & d].sum())}

    peso_plano = np.where(m_prio, psin, 0.0)
    peso_pond = peso_celdas("sobrevive_ruido_50", 0.25) * psin

    sols = {}
    if r == "CDMX":
        sols["Reporte (K=7)"] = REPORTE[r]
        sols["Personas (K=7)"] = C[resolver(d_cand, peso_plano, K=7)]
        sols["Ponderado (K=7)"] = C[resolver(d_cand, peso_pond, K=7)]
    else:
        cuotas = dict.fromkeys(ZONAS, 3)
        sols["Reporte (K=8)"] = REPORTE[r]
        sols["Personas (K=8)"] = C[resolver(d_cand, peso_plano, K=8)]
        sols["Ponderado (K=8)"] = C[resolver(d_cand, peso_pond, K=8)]
        sols["Personas (K=12, sin zonas)"] = C[resolver(d_cand, peso_plano, K=12)]
        sols["Personas (K=12, 3 por zona)"] = C[resolver(d_cand, peso_plano, cuotas=cuotas, zonas_cand=zc)]
        sols["Ponderado (K=12, 3 por zona)"] = C[resolver(d_cand, peso_pond, cuotas=cuotas, zonas_cand=zc)]

    # Sensibilidad de los pesos
    Ks = 7 if r == "CDMX" else 8
    principal = {tuple(p) for p in sols[f"Ponderado (K={Ks})"]}
    sens = {}
    for nombre, (S, u) in {"S con σ=100": ("sobrevive_ruido_100", 0.25), "A con umbral 0.10": ("sobrevive_ruido_50", 0.10),
                           "A con umbral 0.50": ("sobrevive_ruido_50", 0.50)}.items():
        alt = C[resolver(d_cand, peso_celdas(S, u) * psin, K=Ks)]
        sens[nombre] = {"clinicas_en_comun": len(principal & {tuple(p) for p in alt}), **metricas(alt)}

    # Sin topología: candidatos en un punto de cada AGEB, objetivo = acceso nuevo
    puntos_ageb = np.array([[p.x, p.y] for p in ageb.geometry.representative_point()])
    peso_nuevo = np.where(sin_acceso, psin, 0.0)
    for k in ([7] if r == "CDMX" else [8, 12]):
        sols[f"Sin topología (K={k})"] = puntos_ageb[voraz(puntos_ageb, xy, peso_nuevo, k)]

    # Sensibilidad: ¿qué pasa si no toda la oferta cuenta?
    sens_red = {}
    for nombre, arbol_r in REDES.items():
        lejos = arbol_r.query(xy)[0] > RADIO
        fila = {"psin_lejos": float(psin[lejos].sum()), "pct_region": float(psin[lejos].sum() / psin.sum() * 100),
                "psin_lejos_en_discos_prio": float(psin[lejos & m_prio].sum()),
                "pct_discos_prio_lejos": float(psin[lejos & m_prio].sum() / psin[m_prio].sum() * 100)}
        modelos = {}
        for n, c in sols.items():
            if not n.startswith("Sin topología"):
                modelos[n] = float(psin[lejos & (cKDTree(c).query(xy)[0] <= RADIO)].sum())
        for k in ([7] if r == "CDMX" else [8, 12]):
            sel = voraz(puntos_ageb, xy, np.where(lejos, psin, 0.0), k)
            modelos[f"Sin topología (K={k})"] = float(psin[lejos & (cKDTree(puntos_ageb[sel]).query(xy)[0] <= RADIO)].sum())
        fila["alcance"] = modelos
        sens_red[nombre] = fila

    # Población exacta de los discos con centro verdadero, para validar la rejilla
    ageb_val = ageb[["PSINDER", "geometry"]].copy()

    def exacta(t):
        discos = shapely.buffer(shapely.points(t["cx"].values, t["cy"].values), t["death"].values)
        u = shapely.union_all(discos)
        g = ageb_val[ageb_val.intersects(u)]
        return float((g["PSINDER"] * g.geometry.intersection(u).area / g.geometry.area).sum())

    psin_por_zona = {}
    if r == "EDOMEX":
        lat_lon = pr.assign(k=pr["pers_m"].round(3))[["k", "lat", "lon"]]
        zp = prio.merge(lat_lon, on="k")
        zp["zona"] = [zona(a, b) for a, b in zip(zp["lat"], zp["lon"])]
        for z in ZONAS:
            psin_por_zona[z] = {"huecos": int((zp["zona"] == z).sum()),
                                "psin_discos": float(psin[union_discos(zp[zp["zona"] == z])].sum())}

    # Línea base al azar con la misma estructura
    rng = np.random.default_rng(26)

    def sorteo_vacio(sel):
        d = d_cand[:, sel].any(axis=1)
        return float(psin[m_prio & d].sum()), float(psin[sin_acceso & d].sum())

    azar = {}
    for k in ([7] if r == "CDMX" else [8, 12]):
        v = np.array([sorteo_vacio(rng.choice(len(C), k, replace=False)) for _ in range(N_AZAR)])
        azar[f"K={k}, libre"] = v
    if r == "EDOMEX":
        idx = {z: np.where(zc == z)[0] for z in ZONAS}
        v = np.array([sorteo_vacio(np.concatenate([rng.choice(idx[z], min(3, len(idx[z])), replace=False) for z in ZONAS]))
                      for _ in range(N_AZAR)])
        azar["K=12, 3 por zona"] = v
    azares[r] = azar

    # Evaluación con ruido nuevo
    masc = Parallel(n_jobs=6)(delayed(replica_oos)(P, prio, xy, 7000 + i) for i in range(N_OOS))
    masc = np.array(masc)
    cub = {n: cKDTree(c).query(xy)[0] <= RADIO for n, c in sols.items()}
    oos = {n: (masc & cub[n]) @ psin for n in sols}
    pares = []
    if r == "CDMX":
        pares = [("Ponderado (K=7)", "Personas (K=7)")]
    else:
        pares = [("Ponderado (K=8)", "Personas (K=8)"), ("Ponderado (K=12, 3 por zona)", "Personas (K=12, 3 por zona)")]
    dif = {f"{a} − {b}": {"media": float((oos[a] - oos[b]).mean()),
                          "ic95": [float(np.percentile(oos[a] - oos[b], 2.5)), float(np.percentile(oos[a] - oos[b], 97.5))]}
           for a, b in pares}

    # Tabla de resultados
    firme = (prio["sobrevive_ruido_50"] >= 0.8) & (prio["ratio"] >= 0.25)
    m_firme = union_discos(prio[firme])
    filas = []
    for n, c in sols.items():
        filas.append({"region": r, "modelo": n, "K": len(c), **metricas(c),
                      "vacio_con_ruido": float(oos[n].mean()),
                      "vacio_firme": float(psin[m_firme & cub[n]].sum())})
    tablas[r] = pd.DataFrame(filas)

    # Oriente: personas de cada solución de 3 por zona
    por_zona = {}
    if r == "EDOMEX":
        for n in ["Personas (K=12, 3 por zona)", "Ponderado (K=12, 3 por zona)"]:
            por_zona[n] = {}
            zona_sol = [zc[int(np.where((C == p).all(axis=1))[0][0])] for p in sols[n]]
            for z in ZONAS:
                pts = sols[n][[i for i, q in enumerate(zona_sol) if q == z]]
                por_zona[n][z] = {"clinicas": len(pts), **metricas(pts)}

    salida[r] = {
        "celdas": len(xy), "psin_region": float(psin.sum()),
        "psin_discos_habitados": float(psin[m_hab].sum()),
        "psin_discos_prioritarios": float(psin[m_prio].sum()),
        "psin_sin_acceso_833m": float(psin[sin_acceso].sum()),
        "psin_sin_acceso_en_discos_prio": float(psin[sin_acceso & m_prio].sum()),
        "psin_discos_firmes": float(psin[m_firme].sum()), "discos_firmes": int(firme.sum()),
        "discos_prio_con_establecimiento_del_otro_estado": int(frontera.sum()),
        "candidatos_por_zona": pd.Series(zc).value_counts().to_dict(),
        "azar": {k: {"vacio_media": float(v[:, 0].mean()), "vacio_p5": float(np.percentile(v[:, 0], 5)), "vacio_p95": float(np.percentile(v[:, 0], 95)),
                     "acceso_media": float(v[:, 1].mean()), "acceso_p95": float(np.percentile(v[:, 1], 95))} for k, v in azar.items()},
        "psin_exacta_discos_habitados": exacta(hab), "psin_exacta_discos_prioritarios": exacta(prio),
        "diferencia_con_ruido": dif, "sensibilidad_pesos": sens, "por_zona": por_zona,
        "psin_discos_por_zona": psin_por_zona, "sensibilidad_red": sens_red,
    }
    mapas[r] = {"prio": prio, "sols": sols, "P": P}
    print(tablas[r].round(0).to_string(), flush=True)
    print(json.dumps(salida[r], indent=1, ensure_ascii=False), flush=True)

tabla = pd.concat(tablas.values(), ignore_index=True)
tabla.to_csv(SALIDA / "modelo_revisado.csv", index=False)
(SALIDA / "modelo_revisado.json").write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
coords = {r: {n: np.asarray(c).round(1).tolist() for n, c in mapas[r]["sols"].items()} for r in REGIONES}
(SALIDA / "modelo_revisado_ubicaciones.json").write_text(json.dumps(coords, ensure_ascii=False), encoding="utf-8")

# %% [markdown]
# ## Figura 1: personas en los vacíos, contadas una vez

# %%
AZAR_DE = {"Reporte (K=7)": "K=7, libre", "Personas (K=7)": "K=7, libre", "Ponderado (K=7)": "K=7, libre",
           "Reporte (K=8)": "K=8, libre", "Personas (K=8)": "K=8, libre", "Ponderado (K=8)": "K=8, libre",
           "Personas (K=12, sin zonas)": "K=12, libre", "Personas (K=12, 3 por zona)": "K=12, 3 por zona",
           "Ponderado (K=12, 3 por zona)": "K=12, 3 por zona"}


def color_modelo(n):
    return next(c for k, c in COLOR.items() if n.startswith(k))


fig, axes = plt.subplots(1, 2, figsize=(13, 4.9), gridspec_kw={"width_ratios": [1, 1.25]})
for ax, r in zip(axes, REGIONES):
    t = tablas[r][tablas[r]["modelo"].isin(AZAR_DE)].iloc[::-1].reset_index(drop=True)
    ax.barh(t["modelo"], t["vacio"] / 1000, color=[color_modelo(n) for n in t["modelo"]], height=0.6)
    for y, (n, v) in enumerate(zip(t["modelo"], t["vacio"])):
        a = salida[r]["azar"][AZAR_DE[n]]
        ax.plot([a["vacio_p5"] / 1000, a["vacio_p95"] / 1000], [y, y], color=ve.TEXTO, lw=1.6,
                solid_capstyle="butt", label="Azar: p5 a p95" if y == 0 else None)
        ax.text(max(v, a["vacio_p95"]) / 1000, y, f"  {v / 1000:.1f} mil", va="center", color=ve.TEXTO, fontsize=9.5)
    ax.set_xlabel("Personas sin seguro alcanzadas en discos prioritarios (miles)")
    ax.set_title(r)
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.16)
axes[1].legend(loc="lower right", bbox_to_anchor=(1, 1.0), borderaxespad=0.2)
ve.titulo(fig, "Contando a cada persona una vez, el MCLP revisado supera al azar",
          "Cada persona se cuenta una vez, dentro del disco vacío y a ≤ 833 m de una clínica nueva.")
fig.tight_layout(rect=(0, 0, 1, 0.91))
ve.guardar(fig, config.FIGURAS_DIR / "modelo_personas_vs_azar.png")

# %% [markdown]
# ## Figura 2: quienes hoy están lejos, según qué oferta cuente

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 4.9))
ESC = list(REDES)
ETQ = ["Todos los\nestablecimientos", "Consultorios médicos\ny hospitales", "Solo\npúblicos"]
for ax, r in zip(axes, REGIONES):
    k = 7 if r == "CDMX" else 8
    series = [(f"Reporte (K={k})", "Reporte"), (f"Personas (K={k})", "Personas"), (f"Sin topología (K={k})", "Sin topología")]
    ancho = 0.26
    for i, (n, et) in enumerate(series):
        v = [salida[r]["sensibilidad_red"][e]["alcance"][n] / 1000 for e in ESC]
        b = ax.bar(np.arange(3) + (i - 1) * ancho, v, ancho * 0.92, color=COLOR[et], label=et)
        ax.bar_label(b, fmt="%.1f", fontsize=8.5, color=ve.TEXTO, padding=2)
    ax.set_xticks(range(3))
    ax.set_xticklabels(ETQ)
    ax.set_ylabel("Personas sin seguro que dejan de estar lejos (miles)")
    ax.set_title(f"{r}, K={k}")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left")
ve.titulo(fig, "Para dar acceso nuevo, conviene buscar directo a quienes están lejos",
          "Personas que hoy están a más de 833 m de esa oferta y quedarían a 833 m o menos.")
fig.tight_layout(rect=(0, 0, 1, 0.91))
ve.guardar(fig, config.FIGURAS_DIR / "modelo_acceso_nuevo.png")

# %% [markdown]
# ## Figura 3: dónde cambia la propuesta

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 6.4))
PARES = {"CDMX": [("Reporte (K=7)", "Reporte", "X"), ("Personas (K=7)", "Personas", "o")],
         "EDOMEX": [("Reporte (K=8)", "Reporte", "X"), ("Personas (K=12, 3 por zona)", "Personas", "o")]}
for ax, r in zip(axes, REGIONES):
    m = mapas[r]
    ax.scatter(m["P"][:, 0], m["P"][:, 1], s=0.4, color=ve.REJILLA, rasterized=True)
    for _, h in m["prio"].iterrows():
        ax.add_patch(plt.Circle((h["cx"], h["cy"]), h["death"], facecolor=ve.GRIS, edgecolor="none", alpha=0.55))
    for n, et, mk in PARES[r]:
        c = m["sols"][n]
        ax.scatter(c[:, 0], c[:, 1], s=95, marker=mk, color=COLOR[et], edgecolor=ve.TEXTO, lw=0.7, zorder=4, label=n)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(r)
    ax.legend(loc="lower left")
ve.titulo(fig, "Ubicaciones del reporte y del modelo revisado",
          "En gris, los discos vacíos prioritarios; de fondo, los establecimientos de salud.")
fig.tight_layout(rect=(0, 0, 1, 0.91))
ve.guardar(fig, config.FIGURAS_DIR / "modelo_ubicaciones.png")
