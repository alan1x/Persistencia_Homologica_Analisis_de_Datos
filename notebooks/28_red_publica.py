# %% [markdown]
# # 28 — Red pública: la topología describe, la cobertura se mide directo
#
# El notebook 26 mostró que, con todos los establecimientos SCIAN 62, casi nadie queda a
# más de 833 m de alguno, pero con solo la red pública queda lejos el 20% de las personas
# sin seguro en CDMX y el 35% en EDOMEX. Aquí se repite todo con la red pública.
#
# **Red pública:** consultorios (6211) y hospitales (622) cuyo `nombre_act` dice
# "sector público", de ambos estados. **Variante abierta:** se quitan por nombre los de
# seguridad social (IMSS, ISSSTE, ISSEMYM, PEMEX, SEDENA, SEMAR), que en principio no
# atienden a quien no tiene seguro. Se conserva IMSS-Bienestar. Es una heurística: DENUE no
# dice a quién atiende cada unidad.
#
# **Personas:** la misma rejilla de 100 m con `PSINDER` del notebook 26. **Lejos:** a más de
# 833 m (15 min a pie con rodeo 1.35) del establecimiento público más cercano. Se reporta
# también 1,667 m (30 min).
#
# ## Criterios fijados antes de correr
#
# **Parte A, la topología como descripción.**
#
# 1. *¿La red pública tiene huecos propios o es solo una red más rala?* Se compara con 200
#    submuestras al azar de la red completa del mismo tamaño. Tiene huecos propios si la
#    persistencia total de sus huecos ≥ 200 m supera el p95 de esas submuestras.
# 2. *¿Los huecos de la red pública coinciden con quien está lejos?* Se mide qué parte de
#    las personas lejos vive dentro de los discos vacíos (radio = muerte), llamada
#    *captura*, y cuántas veces más frecuente es estar lejos dentro de los discos que en
#    toda la región, llamado *enriquecimiento*. Coinciden si la captura ≥ 50% y el
#    enriquecimiento ≥ 1.5. Se reporta aparte cuántas personas lejos viven fuera de la
#    envolvente convexa de la red, porque ahí un hueco H1 no puede existir por definición.
#
# **Parte B, la cobertura medida directo.**
#
# 3. *¿Cuántas personas ganan acceso con K clínicas nuevas?* Voraz sobre candidatos libres
#    (centros de una rejilla de 500 m con gente) para K = 1 a 30, maximizando las personas
#    lejos que quedan a ≤ 833 m. Se compara con el MCLP exacto en K = 10 (candidatos
#    reducidos a los 400 de mayor ganancia individual) y con el p95 de 1,000 sorteos al
#    azar del mismo K.
# 4. *¿Los huecos sirven como lista de candidatos?* Mismo voraz usando solo los centros de
#    los huecos. Sirven si en K = 10 alcanzan al menos el 90% de lo que logran los
#    candidatos libres.
#
# Todo se repite con la variante abierta como sensibilidad.

# %%
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import heapq

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pulp
import shapely
from scipy.spatial import cKDTree

from lib import censo, config, huecos, viz_eval as ve

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
REGIONES = ["CDMX", "EDOMEX"]
RADIO = 15 * (4500 / 60) / 1.35  # 833 m
PASO = 100.0
PASO_CAND = 500.0
K_MAX = 30
K_REF = 10
N_NULO = 200
N_AZAR = 1000
SEG_SOCIAL = (r"IMSS(?!.*BIENESTAR)|SEGURO SOCIAL(?!.*BIENESTAR)|ISSSTE|SEGURIDAD Y SERVICIOS SOCIALES|"
              r"ISSEMYM|SEGURIDAD SOCIAL|PEMEX|PETROLEOS|SEDENA|DEFENSA NACIONAL|MILITAR|SEMAR|MARINA|"
              r"UNIDAD DE MEDICINA FAMILIAR|\bU\.?M\.?F\b")


def rejilla(ageb):
    """Reparte PSINDER de cada AGEB entre los puntos de una rejilla dentro de ella (igual que el notebook 26)."""
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


def union_discos(arbol, n, cx, cy, r):
    m = np.zeros(n, bool)
    for idx in arbol.query_ball_point(np.column_stack([cx, cy]), r):
        m[idx] = True
    return m


def voraz(cubre, peso, K):
    """Voraz perezoso: en cada paso, el candidato que suma más personas aún no alcanzadas."""
    restante = peso.copy()
    heap = [(-peso[c].sum(), j) for j, c in enumerate(cubre)]
    heapq.heapify(heap)
    sel, acum = [], []
    while heap and len(sel) < K:
        g, j = heapq.heappop(heap)
        real = restante[cubre[j]].sum()
        if heap and real < -heap[0][0] - 1e-9:
            heapq.heappush(heap, (-real, j))
            continue
        sel.append(j)
        restante[cubre[j]] = 0.0
        acum.append(float(peso.sum() - restante.sum()))
    return sel, acum


def mclp(cubre, peso, K, n_celdas):
    """MCLP exacto con celdas agrupadas por firma de cobertura."""
    col = {}
    for j, c in enumerate(cubre):
        for i in c:
            col.setdefault(i, []).append(j)
    firmas = {}
    for i, js in col.items():
        if peso[i] > 0:
            firmas[tuple(js)] = firmas.get(tuple(js), 0.0) + peso[i]
    prob = pulp.LpProblem("mclp", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x{j}", cat="Binary") for j in range(len(cubre))]
    y = [pulp.LpVariable(f"y{i}", lowBound=0, upBound=1) for i in range(len(firmas))]
    prob += pulp.lpSum(d * v for d, v in zip(firmas.values(), y))
    prob += pulp.lpSum(x) == K
    for v, js in zip(y, firmas):
        prob += v <= pulp.lpSum(x[j] for j in js)
    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=600))
    return pulp.LpStatus[prob.status], [j for j, v in enumerate(x) if v.value() > 0.5]


# %% [markdown]
# ## Redes

# %%
SALUD = pd.concat([pd.read_parquet(INT / f"salud_{r}.parquet") for r in REGIONES], ignore_index=True)
cod = SALUD["codigo_act"].astype(str)
medico = cod.str.startswith("6211") | cod.str.startswith("622")
publico = medico & SALUD["nombre_act"].str.contains("sector p[uú]blico", case=False, regex=True)
seg = SALUD["nom_estab"].astype(str).str.upper().str.contains(SEG_SOCIAL, regex=True)
REDES = {"Pública": publico, "Pública abierta": publico & ~seg}
print({k: int(v.sum()) for k, v in REDES.items()})
print("Quitados por seguridad social:")
print(SALUD.loc[publico & seg, "nom_estab"].str.upper().str[:45].value_counts().head(30).to_string())

# %%
res, mapas, curvas = {}, {}, {}
for r in REGIONES:
    ageb = censo.construir_ageb_enriquecido(r)
    ageb = ageb[ageb["POBTOT"].fillna(0) > 0].to_crs(config.CRS_METROS)
    xy, psin = rejilla(ageb)
    arbol_c = cKDTree(xy)
    total = float(psin.sum())
    P_todo = SALUD.loc[SALUD["region"] == r, ["x", "y"]].drop_duplicates().to_numpy()

    # Candidatos libres: centros de una rejilla de 500 m que tenga gente
    cel = np.unique(np.floor(xy[psin > 0] / PASO_CAND), axis=0)
    cand_libres = (cel + 0.5) * PASO_CAND
    cubre_libres = arbol_c.query_ball_point(cand_libres, RADIO)

    res[r] = {"psin_region": total, "celdas": len(xy), "candidatos_libres": len(cand_libres)}
    for nombre, mascara in REDES.items():
        arbol_red = cKDTree(SALUD.loc[mascara, ["x", "y"]].to_numpy())  # ambos estados
        d = arbol_red.query(xy)[0]
        lejos = d > RADIO
        lejos30 = d > 2 * RADIO
        peso = np.where(lejos, psin, 0.0)
        fila = {"establecimientos_region": int((mascara & (SALUD["region"] == r)).sum()),
                "psin_lejos": float(peso.sum()), "pct_lejos": float(peso.sum() / total * 100),
                "psin_lejos_30min": float(psin[lejos30].sum()), "pct_lejos_30min": float(psin[lejos30].sum() / total * 100)}
        # Mediana ponderada por personas
        o = np.argsort(d)
        fila["distancia_mediana_ponderada_m"] = float(d[o][np.searchsorted(np.cumsum(psin[o]), total / 2)])

        # --- Parte A: topología ---
        P = SALUD.loc[mascara & (SALUD["region"] == r), ["x", "y"]].drop_duplicates().to_numpy()
        h = huecos.extraer_huecos(huecos.complejo(P), P, 200)
        m_h = union_discos(arbol_c, len(xy), h["cx"].values, h["cy"].values, h["death"].values)
        hull = shapely.convex_hull(shapely.multipoints(P))
        dentro_hull = shapely.contains_xy(hull, xy[:, 0], xy[:, 1])
        # Por hueco: personas y personas lejos dentro de su disco
        por_h = [(psin[i].sum(), peso[i].sum()) for i in arbol_c.query_ball_point(h[["cx", "cy"]].values, h["death"].values)]
        h["psin_disco"], h["psin_lejos_disco"] = np.array(por_h).T if len(por_h) else ([], [])
        captura = float(peso[m_h].sum() / peso.sum())
        enriquecimiento = float((peso[m_h].sum() / psin[m_h].sum()) / (peso.sum() / total))

        rng = np.random.default_rng(28)
        nulo = []
        for _ in range(N_NULO):
            Q = P_todo[rng.choice(len(P_todo), len(P), replace=False)]
            hq = huecos.extraer_huecos(huecos.complejo(Q), Q, 200)
            nulo.append((len(hq), float(hq["pers"].sum())))
        nulo = np.array(nulo)

        fila["topologia"] = {
            "puntos_unicos": len(P), "huecos_200m": len(h), "persistencia_total_m": float(h["pers"].sum()),
            "persistencia_max_m": float(h["pers"].max()), "persistencia_mediana_m": float(h["pers"].median()),
            "radio_disco_mediana_m": float(h["death"].median()),
            "huecos_habitados": int((h["psin_disco"] > 0).sum()),
            "huecos_con_personas_lejos": int((h["psin_lejos_disco"] > 0).sum()),
            "nulo_huecos_media": float(nulo[:, 0].mean()), "nulo_huecos_p95": float(np.percentile(nulo[:, 0], 95)),
            "nulo_persistencia_total_p95": float(np.percentile(nulo[:, 1], 95)),
            "nulo_persistencia_total_media": float(nulo[:, 1].mean()),
            "tiene_huecos_propios": bool(h["pers"].sum() > np.percentile(nulo[:, 1], 95)),
            "psin_en_discos": float(psin[m_h].sum()),
            "captura": captura, "enriquecimiento": enriquecimiento,
            "coinciden": bool(captura >= 0.5 and enriquecimiento >= 1.5),
            "lejos_fuera_envolvente": float(peso[~dentro_hull].sum() / peso.sum()),
            "lejos_dentro_envolvente_fuera_de_discos": float(peso[dentro_hull & ~m_h].sum() / peso.sum()),
            "spearman_persistencia_vs_lejos_en_disco": float(h["pers"].corr(h["psin_lejos_disco"], method="spearman")),
        }

        # --- Parte B: cobertura directa ---
        sel_l, acum_l = voraz(cubre_libres, peso, K_MAX)
        cand_topo = h[["cx", "cy"]].to_numpy()
        cubre_topo = arbol_c.query_ball_point(cand_topo, RADIO)
        sel_t, acum_t = voraz(cubre_topo, peso, min(K_MAX, len(cand_topo)))

        ganancia = np.array([peso[c].sum() for c in cubre_libres])
        top = np.argsort(-ganancia)[:400]
        top = np.union1d(top, sel_l[:K_REF])
        estado, sel_e = mclp([cubre_libres[j] for j in top], peso, K_REF, len(xy))
        exacto = float(peso[union_discos(arbol_c, len(xy), cand_libres[top[sel_e], 0], cand_libres[top[sel_e], 1],
                                          np.full(len(sel_e), RADIO))].sum())

        utiles = np.where(ganancia > 0)[0]
        azar = []
        for _ in range(N_AZAR):
            s = rng.choice(utiles, K_REF, replace=False)
            azar.append(peso[union_discos(arbol_c, len(xy), cand_libres[s, 0], cand_libres[s, 1], np.full(K_REF, RADIO))].sum())

        sitios = cand_libres[sel_l[:K_REF]]
        d_desp = np.minimum(d, cKDTree(sitios).query(xy)[0])
        fila["cobertura"] = {
            "voraz_libres": acum_l, "voraz_huecos": acum_t,
            f"K{K_REF}_voraz": acum_l[K_REF - 1], f"K{K_REF}_exacto": exacto, f"K{K_REF}_exacto_estado": estado,
            f"K{K_REF}_huecos": acum_t[K_REF - 1] if len(acum_t) >= K_REF else None,
            f"K{K_REF}_huecos_sobre_libres": (acum_t[K_REF - 1] / acum_l[K_REF - 1]) if len(acum_t) >= K_REF else None,
            "huecos_sirven_como_candidatos": bool(len(acum_t) >= K_REF and acum_t[K_REF - 1] >= 0.9 * acum_l[K_REF - 1]),
            f"K{K_REF}_azar_media": float(np.mean(azar)), f"K{K_REF}_azar_p95": float(np.percentile(azar, 95)),
            f"K{K_REF}_pct_de_los_lejos": acum_l[K_REF - 1] / peso.sum() * 100,
            f"K{K_REF}_sitios_en_disco_de_hueco": int(m_h[arbol_c.query(sitios)[1]].sum()),
            f"K{K_REF}_sitios_fuera_envolvente": int((~shapely.contains_xy(hull, sitios[:, 0], sitios[:, 1])).sum()),
            "distancia_mediana_ponderada_despues_m": float(d_desp[np.argsort(d_desp)][np.searchsorted(np.cumsum(psin[np.argsort(d_desp)]), total / 2)]),
            "sitios_K10_xy": sitios.round(1).tolist(),
        }
        res[r][nombre] = fila
        curvas[(r, nombre)] = (acum_l, acum_t, float(np.percentile(azar, 95)))
        if nombre == "Pública":
            mapas[r] = {"xy": xy, "peso": peso, "h": h, "P": P, "sitios": sitios, "hull": hull, "m_h": m_h}
        print(r, nombre, json.dumps({k: v for k, v in fila.items() if k != "cobertura"}, ensure_ascii=False, indent=1), flush=True)
        print({k: v for k, v in fila["cobertura"].items() if not isinstance(v, list)}, flush=True)

(SALIDA / "red_publica.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

# %% [markdown]
# ## Figura 1: dónde está la gente lejos de la red pública y dónde están los huecos

# %%
fig, axes = plt.subplots(1, 2, figsize=(15, 8.2), gridspec_kw={"width_ratios": [1, 1.25]})
for ax, r in zip(axes, REGIONES):
    m = mapas[r]
    lejos = m["peso"] > 0
    ax.scatter(m["xy"][~lejos, 0], m["xy"][~lejos, 1], s=0.15, c="#dcdbd6", lw=0, rasterized=True)
    ax.scatter(m["xy"][lejos, 0], m["xy"][lejos, 1], s=0.3, c=ve.NARANJA, alpha=0.5, lw=0, rasterized=True)
    for _, f in m["h"].iterrows():
        ax.add_patch(plt.Circle((f["cx"], f["cy"]), f["death"], fill=False, ec=ve.AZUL, lw=0.7, alpha=0.8))
    ax.scatter(m["P"][:, 0], m["P"][:, 1], s=2.5, c=ve.TEXTO, lw=0, zorder=3)
    ax.scatter(m["sitios"][:, 0], m["sitios"][:, 1], s=90, marker="*", c=ve.AQUA, ec="white", lw=0.6, zorder=4)
    ax.plot(*m["hull"].exterior.xy, c=ve.GRIS, lw=0.8, ls="--")
    t = res[r]["Pública"]
    ax.set_title(f"{r}\n{t['pct_lejos']:.0f}% de las personas sin seguro está lejos; "
                 f"{t['topologia']['captura'] * 100:.0f}% de ellas vive dentro de un disco", fontsize=10.5)
    ax.set_aspect("equal")
    ax.set_axis_off()
from matplotlib.lines import Line2D
leyenda = [Line2D([], [], ls="", marker="o", c=ve.NARANJA, label="Personas sin seguro a > 833 m de la red pública"),
           Line2D([], [], ls="", marker="o", c="#dcdbd6", label="Personas sin seguro a ≤ 833 m"),
           Line2D([], [], ls="", marker="o", mfc="none", mec=ve.AZUL, label="Disco vacío de un hueco (H1 ≥ 200 m)"),
           Line2D([], [], ls="", marker=".", c=ve.TEXTO, label="Establecimiento público"),
           Line2D([], [], ls="", marker="*", ms=11, c=ve.AQUA, label=f"{K_REF} sitios del voraz directo"),
           Line2D([], [], c=ve.GRIS, ls="--", label="Envolvente convexa de la red")]
fig.legend(handles=leyenda, loc="lower center", ncol=3, fontsize=9.5, bbox_to_anchor=(0.5, -0.02))
ve.titulo(fig, "Personas lejos de la red pública y huecos de la red",
          "Red pública: consultorios y hospitales del sector público (DENUE). Lejos = más de 833 m, 15 min a pie.")
ve.guardar(fig, FIG / "red_publica_mapa.png")

# %% [markdown]
# ## Figura 2: personas que ganan acceso según de dónde salen los candidatos

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=False)
for ax, r in zip(axes, REGIONES):
    libres, topo, p95 = curvas[(r, "Pública")]
    k = np.arange(1, len(libres) + 1)
    ax.plot(k, np.array(libres) / 1000, c=ve.AQUA, lw=2, label="Candidatos libres (rejilla de 500 m)")
    ax.plot(np.arange(1, len(topo) + 1), np.array(topo) / 1000, c=ve.AZUL, lw=2, label="Solo centros de huecos")
    ax.scatter([K_REF], [p95 / 1000], c=ve.GRIS, s=40, zorder=3, label=f"Azar, p95 con K={K_REF}")
    ax.axvline(K_REF, c=ve.REJILLA, lw=1, zorder=0)
    ax.set_title(r)
    ax.set_xlabel("Clínicas nuevas (K)")
    ax.set_ylabel("Miles de personas sin seguro que pasan a ≤ 833 m")
    ax.annotate(f"{libres[-1] / 1000:.0f}k", (k[-1], libres[-1] / 1000), xytext=(4, 0), textcoords="offset points",
                va="center", fontsize=9, color=ve.TEXTO_2)
    ax.annotate(f"{topo[-1] / 1000:.0f}k", (len(topo), topo[-1] / 1000), xytext=(4, 0), textcoords="offset points",
                va="center", fontsize=9, color=ve.TEXTO_2)
axes[0].legend(loc="upper left", fontsize=9)
ve.titulo(fig, "Personas que ganan acceso según de dónde salen los candidatos",
          "Voraz que maximiza las personas sin seguro que hoy están a > 833 m de la red pública y quedarían a ≤ 833 m.")
fig.subplots_adjust(top=0.82)
ve.guardar(fig, FIG / "red_publica_curva_K.png")
