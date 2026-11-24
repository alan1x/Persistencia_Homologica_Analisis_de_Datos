# %% [markdown]
# # 43 — ¿A quién le sirve el transporte público? (sigue de F8.4)
#
# En el E2SFCA la capacidad total se conserva: con o sin transporte, el acceso promedio
# ponderado por gente es el mismo (0.993 en los dos casos del 42; aquí se verifica). Así que el
# transporte **no agrega oferta: la redistribuye**. Unas celdas ganan porque alcanzan más
# unidades, y otras pierden porque sus unidades se reparten entre más gente. La pregunta es
# hacia quién se mueve el acceso, según el grado de marginación de CONAPO.
#
# Se compara el transporte contra el control a pie del mismo motor (r5), como en el 42. Todo
# sale de `acceso_transporte_clues.parquet`; no se corre r5. Los tiempos son de unidad a celda,
# la aproximación del 42.
#
# ## Medidas, fijadas antes de correr
#
# Todo ponderado por gente sin seguro (`psin`), en total y por estado. Se excluyen las celdas
# sin grado de marginación (se reporta cuánta gente).
#
# 1. **Por grado de marginación** (Muy bajo … Muy alto): acceso medio a pie y con transporte,
#    cambio medio neto, gente que sale de acceso bajo y gente que entra.
# 2. **Reparto de ganancias y pérdidas:** de la suma de las ganancias (Σ psin · máx(Δf, 0)),
#    qué parte recibe cada grado, comparada con su parte de la gente. Igual con las pérdidas.
# 3. **Índice de concentración** del acceso f a pie y con transporte. La gente se ordena de la
#    más marginada (IM_2020 más bajo) a la menos marginada; las celdas con el mismo IM (el mismo
#    AGEB) comparten el rango medio de su bloque. CI = 2 · cov_w(f, R) / media_w(f).
#    CI > 0: el acceso se concentra en los menos marginados. ΔCI = CI_transporte − CI_pie.
#    Incertidumbre: bootstrap pareado de municipios (1,000 réplicas, semilla 0), estratificado
#    por estado en el total. Es una sensibilidad a la composición municipal con la red y el
#    E2SFCA fijos, suponiendo municipios independientes (aunque compartan unidades).
#
# ## Criterio, fijado antes de correr
#
# El transporte se llama **regresivo respecto a la marginación** si se cumplen las dos:
# - la gente en marginación Alta y Muy alta recibe una parte de las ganancias menor que su
#   parte de la gente;
# - ΔCI > 0 con el intervalo del 95% por encima de 0.
#
# Si ΔCI < 0 con el intervalo por debajo de 0 y esa gente recibe más que su parte, es
# **progresivo**. Si las señales discrepan o el intervalo cruza 0, es **indeterminado** (no hay
# margen de equivalencia para llamarlo neutro). Junto al veredicto se reportan el cambio neto
# del grupo y su parte de las pérdidas. Se reporta en total y por estado.
#
# Es descriptivo: dice a quién llega el transporte que existe hoy, no qué pasaría con otra red.
#
# *Ajustes tras la crítica de Codex, antes de correr:* rangos empatados por bloque de IM;
# cotejo estricto de coordenadas; bootstrap con multiplicidades de municipio (sin concatenar) y
# estratificado por estado; verificación de la conservación; validación de claves y grados;
# repartos indefinidos si no hay ganancias o pérdidas.

# %%
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from lib import acceso, config, f4, viz_eval as ve

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
GRADOS = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]
REGIONES = ("CDMX", "EDOMEX")
N_BOOT, SEMILLA = 1000, 0

c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
t = pd.read_parquet(INT / f"acceso_transporte{acceso.sufijo_oferta()}.parquet")
assert len(c) == len(t)
assert np.allclose(t[["x", "y"]].to_numpy(), c[["x", "y"]].to_numpy(), rtol=0, atol=0.01), "celdas distintas"
assert not c[["x", "y"]].duplicated().any()

cve = c["CVEGEO"].astype("string")
d = pd.DataFrame({"psin": c["psin"].to_numpy(float), "region": c["region"].to_numpy(),
                  "grado": c["GM_2020"].to_numpy(), "im": c["IM_2020"].to_numpy(float),
                  "mun": cve.str[:5].to_numpy(),
                  "f_pie": t["acceso_rel_pie_r5"].to_numpy(float), "f_tp": t["acceso_rel_transporte"].to_numpy(float)})

# Conservación: Σ psin · Δf ≈ 0 antes del filtro (por estado puede no ser 0).
cons = {"total": float((d.psin * (d.f_tp - d.f_pie)).sum()),
        **{r: float((d.psin * (d.f_tp - d.f_pie))[d.region == r].sum()) for r in REGIONES},
        "escala_total": float((d.psin * d.f_pie).sum())}
print("Σ psin·Δf:", json.dumps(cons))
assert abs(cons["total"]) < 1e-6 * cons["escala_total"], "el acceso total no se conserva"

con = d["psin"] > 0
excl = {"psin_sin_grado": float(d.psin[con & d.grado.isna()].sum()),
        "psin_grado_inesperado": float(d.psin[con & d.grado.notna() & ~d.grado.isin(GRADOS)].sum())}
d = d[con & d["grado"].isin(GRADOS) & np.isfinite(d["im"])].reset_index(drop=True)
assert np.isfinite(d[["psin", "f_pie", "f_tp"]].to_numpy()).all()
assert d["mun"].notna().all() and (d["mun"].str.len() == 5).all() and d["mun"].str.isdigit().all(), "CVEGEO raro"
d["df"] = d["f_tp"] - d["f_pie"]
excl["psin_analizada"] = float(d.psin.sum())
excl["cambio_neto_analizado"] = float((d.psin * d.df).sum())
print(excl)
print("municipios por estado:", d.groupby("region")["mun"].nunique().to_dict())

# %% [markdown]
# ## 1 y 2. Por grado de marginación

# %%


def por_grado(x):
    w = x["psin"]
    a = pd.DataFrame({
        "grado": x["grado"], "psin": w, "wf_pie": w * x["f_pie"], "wf_tp": w * x["f_tp"],
        "w_bajo_pie": w * (x["f_pie"] < 0.5), "w_bajo_tp": w * (x["f_tp"] < 0.5),
        "psin_sale": w * ((x["f_pie"] < 0.5) & (x["f_tp"] >= 0.5)),
        "psin_entra": w * ((x["f_pie"] >= 0.5) & (x["f_tp"] < 0.5)),
        "gana": w * x["df"].clip(lower=0), "pierde": w * (-x["df"]).clip(lower=0),
    }).groupby("grado").sum().reindex(GRADOS)
    s = ["psin", "wf_pie", "wf_tp", "w_bajo_pie", "w_bajo_tp", "psin_sale", "psin_entra", "gana", "pierde"]
    a[s] = a[s].fillna(0.0)
    p = a["psin"].where(a["psin"] > 0)
    tot_g, tot_p = a["gana"].sum(), a["pierde"].sum()
    return pd.DataFrame({
        "psin": a["psin"], "pct_gente": a["psin"] / a["psin"].sum() * 100,
        "f_pie": a["wf_pie"] / p, "f_tp": a["wf_tp"] / p, "cambio_medio": (a["wf_tp"] - a["wf_pie"]) / p,
        "bajo_pie_pct": a["w_bajo_pie"] / p * 100, "bajo_tp_pct": a["w_bajo_tp"] / p * 100,
        "psin_sale": a["psin_sale"], "psin_entra": a["psin_entra"],
        "pct_ganancias": a["gana"] / tot_g * 100 if tot_g > 0 else np.nan,
        "pct_perdidas": a["pierde"] / tot_p * 100 if tot_p > 0 else np.nan,
    })


tablas = {"total": por_grado(d), **{r: por_grado(d[d.region == r]) for r in REGIONES}}
for k, tab in tablas.items():
    print(f"\n== {k} ==")
    print(tab.round(3).to_string())

# %% [markdown]
# ## 3. Índice de concentración con rangos empatados y bootstrap pareado de municipios

# %%


class Dominio:
    """Precalcula bloques de IM empatado y códigos de municipio para un dominio."""

    def __init__(self, x):
        o = np.argsort(x["im"].to_numpy(), kind="stable")
        im = x["im"].to_numpy()[o]
        self.bloque = np.r_[0, np.cumsum(im[1:] != im[:-1])]  # bloques en orden de IM ascendente
        self.nb = self.bloque[-1] + 1
        self.w = x["psin"].to_numpy()[o]
        self.f1, self.f2 = x["f_pie"].to_numpy()[o], x["f_tp"].to_numpy()[o]
        mun, self.m = np.unique(x["mun"].to_numpy()[o], return_inverse=True)
        self.reg_mun = x.drop_duplicates("mun").set_index("mun").loc[mun, "region"].to_numpy()

    def indices(self, k=None):
        w = self.w if k is None else self.w * k[self.m]
        W_b = np.bincount(self.bloque, w, self.nb)
        S1 = np.bincount(self.bloque, w * self.f1, self.nb)
        S2 = np.bincount(self.bloque, w * self.f2, self.nb)
        W = W_b.sum()
        R = (np.cumsum(W_b) - W_b / 2) / W
        Rm = (W_b * R).sum() / W
        out = []
        for S in (S1, S2):
            mu = S.sum() / W
            out.append(2 * ((S - mu * W_b) * (R - Rm)).sum() / W / mu)
        return out[0], out[1], out[1] - out[0]

    def bootstrap(self, rng):
        nm = len(self.reg_mun)
        B = np.empty((N_BOOT, 3))
        for b in range(N_BOOT):
            k = np.zeros(nm)
            for r in np.unique(self.reg_mun):  # estratificado por estado
                ids = np.flatnonzero(self.reg_mun == r)
                k += np.bincount(rng.choice(ids, len(ids), replace=True), minlength=nm)
            B[b] = self.indices(k)
        return B


def concentracion(x, rng):
    D = Dominio(x)
    a, b, dd = D.indices()
    B = D.bootstrap(rng)
    lo, hi = np.percentile(B, [2.5, 97.5], axis=0)
    return {"ci_pie": a, "ci_transporte": b, "delta_ci": dd, "ci_pie_ic95": [lo[0], hi[0]],
            "ci_transporte_ic95": [lo[1], hi[1]], "delta_ci_ic95": [lo[2], hi[2]],
            "municipios": int(len(D.reg_mun)), "bloques_im": int(D.nb)}


rng = np.random.default_rng(SEMILLA)
conc = {"total": concentracion(d, rng), **{r: concentracion(d[d.region == r], rng) for r in REGIONES}}
print(json.dumps(conc, indent=1))

# %% [markdown]
# ## Veredicto

# %%


def veredicto(tab, cc):
    marg = tab.loc[["Alto", "Muy alto"]]
    parte_gan, parte_gente = marg["pct_ganancias"].sum(min_count=2), marg["pct_gente"].sum()
    lo, hi = cc["delta_ci_ic95"]
    if np.isnan(parte_gan):
        v = "indeterminado"
    elif parte_gan < parte_gente and lo > 0:
        v = "regresivo"
    elif parte_gan > parte_gente and hi < 0:
        v = "progresivo"
    else:
        v = "indeterminado"
    psin_g = marg["psin"].sum()
    return {"alta_muy_alta_pct_ganancias": float(parte_gan), "alta_muy_alta_pct_gente": float(parte_gente),
            "alta_muy_alta_pct_perdidas": float(marg["pct_perdidas"].sum(min_count=2)),
            "alta_muy_alta_cambio_medio_neto": float((marg["cambio_medio"] * marg["psin"]).sum() / psin_g),
            "veredicto": v}


ver = {k: veredicto(tablas[k], conc[k]) for k in tablas}
print(json.dumps(ver, indent=1))

res = {
    "criterio": "regresivo si Alta+Muy alta recibe menos ganancias que su parte de la gente y ΔCI > 0 (IC 95% > 0)",
    "comparacion": "transporte r5 contra control a pie r5 (notebook 42; tiempos unidad -> celda)",
    "conservacion": cons, "exclusiones": excl,
    "por_grado": {k: v.round(4).reset_index().to_dict(orient="records") for k, v in tablas.items()},
    "concentracion": conc,
    "veredicto": ver,
}
f4.guardar_json(res, SALIDA / "equidad_transporte.json")

# %% [markdown]
# ## Figura

# %%
fig, axs = plt.subplots(1, 3, figsize=(16, 5.6), gridspec_kw={"width_ratios": [1, 1, 1.15]})
xs = np.arange(len(GRADOS))
for ax, r in zip(axs[:2], REGIONES):
    tab = tablas[r]
    ax.bar(xs - 0.2, tab["bajo_pie_pct"], 0.38, color=ve.AZUL, label="A pie (r5)")
    ax.bar(xs + 0.2, tab["bajo_tp_pct"], 0.38, color=ve.AQUA, label="Transporte + pie (r5)")
    for x_, v1, v2 in zip(xs, tab["bajo_pie_pct"], tab["bajo_tp_pct"]):
        if np.isfinite(v2):
            ax.text(x_ + 0.2, v2, f"{v2 - v1:+.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(xs, GRADOS, fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_title(f"{r}: gente con acceso bajo (%)", fontsize=10)
    ax.set_xlabel("Grado de marginación (CONAPO)", fontsize=8)
axs[0].legend(fontsize=8, frameon=False, loc="upper left")
axs[0].set_ylabel("% de la gente sin seguro del grado")

ax = axs[2]
tab = tablas["total"]
ax.bar(xs - 0.27, tab["pct_gente"], 0.26, color=ve.GRIS, label="Parte de la gente")
ax.bar(xs, tab["pct_ganancias"], 0.26, color=ve.AQUA, label="Parte de las ganancias")
ax.bar(xs + 0.27, tab["pct_perdidas"], 0.26, color=ve.NARANJA, label="Parte de las pérdidas")
ax.set_xticks(xs, GRADOS, fontsize=8)
ax.set_ylabel("%")
ax.set_xlabel("Grado de marginación (CONAPO)", fontsize=8)
ax.legend(fontsize=8, frameon=False)
ax.set_title("Toda la zona: ¿a quién le llega lo que mueve el transporte?", fontsize=10)
ct = conc["total"]
ve.titulo(fig, "¿A quién le sirve el transporte público?",
          f"El transporte no agrega oferta: la redistribuye. Índice de concentración del acceso "
          f"(> 0: hacia los menos marginados): a pie {ct['ci_pie']:.3f}, con transporte {ct['ci_transporte']:.3f} "
          f"(Δ {ct['delta_ci']:+.3f}, IC 95% {ct['delta_ci_ic95'][0]:+.3f} a {ct['delta_ci_ic95'][1]:+.3f}). "
          f"Veredicto: {ver['total']['veredicto']}.")
fig.subplots_adjust(top=0.80, wspace=0.22)
ve.guardar(fig, FIG / "equidad_transporte.png")
