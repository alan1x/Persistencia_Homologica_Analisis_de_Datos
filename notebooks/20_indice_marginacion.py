# %% [markdown]
# # 20 — Índice de Marginación Compuesto
#
# El scoring actual usa: tiempo_caminata + % sin seguro + persistencia topológica.
# Este notebook agrega una cuarta dimensión: marginación socioeconómica.
#
# Sin datos externos de CONAPO, construimos un índice compuesto desde las
# variables censales que ya tenemos en huecos_censal:
#
#   IM = 0.35 × pct_sin_salud_norm    (acceso a salud)
#      + 0.25 × escolaridad_def_norm  (déficit educativo = 12-graproes)
#      + 0.25 × pob_mayor_norm        (vulnerabilidad etaria = % 60+)
#      + 0.15 × densidad_demanda_norm (presión sobre infraestructura)
#
# Se re-rankea el Top 15 de huecos y se compara con el ranking original.
# Un hueco que sube en el ranking compuesto merece mayor atención de política.

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.preprocessing import MinMaxScaler

from lib import config

REGIONES = ["CDMX", "EDOMEX"]
COLORES  = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}

PESOS = {
    "pct_sin_salud":    0.35,
    "escolaridad_def":  0.25,
    "pob_mayor":        0.25,
    "densidad_demanda": 0.15,
}

# %% [markdown]
# ## 1. Construir índice de marginación

# %%
frames = {}

for region in REGIONES:
    censal = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_censal_{region}.parquet")
    score  = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_score_{region}.parquet")

    df = censal.merge(
        score[["hueco_id", "tiempo_est_min", "score", "score_norm",
               "urgencia", "x_utm", "y_utm"]],
        on="hueco_id", how="inner"
    )

    # --- Construir las cuatro dimensiones ---
    # 1. Acceso a salud (ya normalizado en huecos_censal)
    df["pct_sin_salud"] = df["pct_sin_salud_prom"].clip(0, 100)

    # 2. Déficit educativo (12 años = secundaria completa como referencia)
    df["escolaridad_def"] = (12.0 - df["graproes_prom"]).clip(0, None)

    # 3. Vulnerabilidad etaria (% pob 60+)
    df["pob_mayor"] = (df["pob_60_mas"] / df["pob_afectada"].replace(0, np.nan)
                       ).fillna(0) * 100

    # 4. Densidad de demanda (pob_sin_salud por km² aproximado del hueco)
    area_km2 = np.pi * (df["radio_m"] / 1000) ** 2
    df["densidad_demanda"] = (df["pob_sin_salud"] / area_km2.replace(0, np.nan)
                              ).fillna(0)

    # --- Normalizar 0–1 con MinMaxScaler ---
    dims = list(PESOS.keys())
    scaler = MinMaxScaler()
    df_norm = pd.DataFrame(
        scaler.fit_transform(df[dims]),
        columns=[f"{d}_norm" for d in dims],
        index=df.index
    )
    df = pd.concat([df, df_norm], axis=1)

    # --- Índice compuesto ---
    df["indice_marg"] = sum(
        PESOS[d] * df[f"{d}_norm"] for d in dims
    )

    # --- Ranking combinado: score original + índice de marginación ---
    # Score ya está en 0–1, IM en 0–1 → combinamos 60/40
    df["score_combined"] = 0.60 * df["score_norm"] + 0.40 * df["indice_marg"]
    df["rank_marg"]      = df["indice_marg"].rank(ascending=False, method="min").fillna(0).astype(int)
    df["rank_orig"]      = df["score_norm"].rank(ascending=False, method="min").fillna(0).astype(int)
    df["rank_combined"]  = df["score_combined"].rank(ascending=False, method="min").fillna(0).astype(int)
    df["delta_rank"]     = df["rank_orig"] - df["rank_combined"]  # positivo = sube en ranking

    frames[region] = df
    print(f"[{region}]  {len(df)} huecos  "
          f"IM_mean={df['indice_marg'].mean():.3f}  "
          f"IM_max={df['indice_marg'].max():.3f}", flush=True)

# %% [markdown]
# ## 2. Top 15: comparativa ranking original vs combinado

# %%
fig, axes = plt.subplots(1, 2, figsize=(18, 10))
fig.suptitle(
    "Impacto del índice de marginación sobre la priorización de huecos\n"
    "Flechas: huecos que suben ↑ (más urgentes) o bajan ↓ al incluir marginación",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df = frames[region]
    color_c = COLORES[region]

    # Top 15 por score combinado
    top = df.nsmallest(15, "rank_combined").copy()
    top = top.sort_values("rank_combined")
    ys  = np.arange(len(top))

    # Barras horizontales: score original (gris) + componente marginación (color)
    ax.barh(ys, top["score_norm"],
            color="#cccccc", alpha=0.8, label="Score original", height=0.4)
    ax.barh(ys + 0.4, top["indice_marg"],
            color=color_c, alpha=0.75, label="Índice marginación", height=0.4)

    # Flechas de cambio de ranking
    for y, (_, row) in zip(ys + 0.2, top.iterrows()):
        delta = int(row["delta_rank"])
        if abs(delta) >= 2:
            color_arrow = "#1b7837" if delta > 0 else "#b2182b"
            symbol = f"↑{delta}" if delta > 0 else f"↓{abs(delta)}"
            ax.text(1.02, y, symbol, va="center", ha="left",
                    fontsize=9, fontweight="bold", color=color_arrow,
                    transform=ax.get_yaxis_transform())

    ax.set_yticks(ys + 0.2)
    ax.set_yticklabels([f"#{int(r['hueco_id'])}  {r['urgencia']}"
                        for _, r in top.iterrows()], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Puntuación normalizada (0–1)", fontsize=10)
    ax.set_title(f"{region} — Top 15 por score combinado (60% orig + 40% marg)",
                 fontsize=10, fontweight="bold", color=color_c)
    ax.set_xlim(0, 1.15)
    ax.legend(fontsize=9, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "marginacion_ranking.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## 3. Scatter: score original vs índice de marginación

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 7))
fig.suptitle(
    "Score de acceso vs Índice de marginación por hueco\n"
    "Cuadrante superior derecho = máxima urgencia en ambas dimensiones",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df = frames[region]
    color_c = COLORES[region]

    sc = ax.scatter(df["score_norm"], df["indice_marg"],
                    s=df["pob_sin_salud"] / df["pob_sin_salud"].max() * 400 + 20,
                    c=df["score_combined"], cmap="RdYlGn",
                    alpha=0.75, zorder=3, edgecolors="#555", linewidths=0.4)

    # Cuadrantes
    ax.axvline(0.5, color="#aaa", lw=1.2, ls="--", alpha=0.6)
    ax.axhline(0.5, color="#aaa", lw=1.2, ls="--", alpha=0.6)
    ax.text(0.97, 0.97, "Alta urgencia\nboth axes", transform=ax.transAxes,
            ha="right", va="top", fontsize=8, color="#b2182b",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#fff5f5", alpha=0.8))
    ax.text(0.03, 0.03, "Baja urgencia\nboth axes", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=8, color="#555",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#f5f5f5", alpha=0.8))

    # Anotar Top 5 combinado
    top5 = df.nsmallest(5, "rank_combined")
    for _, row in top5.iterrows():
        ax.annotate(f"#{int(row['hueco_id'])}",
                    (row["score_norm"], row["indice_marg"]),
                    textcoords="offset points", xytext=(6, 4),
                    fontsize=8, color="#333", fontweight="bold")

    plt.colorbar(sc, ax=ax, label="Score combinado", shrink=0.8)
    ax.set_xlabel("Score original (tiempo + sin seguro + pers.)", fontsize=10)
    ax.set_ylabel("Índice de marginación compuesto", fontsize=10)
    ax.set_title(f"{region}", fontsize=12, fontweight="bold", color=color_c)
    ax.set_xlim(-0.05, 1.1)
    ax.set_ylim(-0.05, 1.1)
    ax.spines[["top", "right"]].set_visible(False)

    # Leyenda de tamaño
    for pob, label in [(5000, "5k"), (20000, "20k"), (50000, "50k")]:
        s = pob / df["pob_sin_salud"].max() * 400 + 20
        ax.scatter([], [], s=s, color="#888", alpha=0.5, label=f"{label} sin seguro")
    ax.legend(fontsize=8, title="Pob. sin seguro", title_fontsize=8,
              loc="lower left", framealpha=0.9)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "marginacion_scatter.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## 4. Resumen ejecutivo

# %%
print("\n" + "="*72, flush=True)
print("ÍNDICE DE MARGINACIÓN — RESUMEN", flush=True)
print("="*72, flush=True)

for region in REGIONES:
    df = frames[region]
    top10_orig = set(df.nsmallest(10, "rank_orig")["hueco_id"])
    top10_comb = set(df.nsmallest(10, "rank_combined")["hueco_id"])
    cambios = df[df["delta_rank"].abs() >= 3].sort_values("delta_rank", ascending=False)
    sube = df[df["delta_rank"] >= 3]
    baja = df[df["delta_rank"] <= -3]

    print(f"\n  [{region}]")
    print(f"  Top 10 estables (en ambos rankings): "
          f"{len(top10_orig & top10_comb)}/10 huecos", flush=True)
    print(f"  Huecos que suben ≥3 posiciones al incluir marginación: "
          f"{len(sube)}", flush=True)
    if not sube.empty:
        for _, r in sube.head(3).iterrows():
            print(f"    #{int(r['hueco_id'])}: "
                  f"rank_orig={r['rank_orig']} → rank_comb={r['rank_combined']} "
                  f"(↑{int(r['delta_rank'])} pos)  "
                  f"IM={r['indice_marg']:.2f}  escol_def={r['escolaridad_def']:.1f}",
                  flush=True)
    print(f"  Huecos que bajan ≥3 posiciones: {len(baja)}", flush=True)
    print(f"\n  Interpretación:", flush=True)
    print(f"  Los huecos que suben tienen alta marginación socioeconómica", flush=True)
    print(f"  pero podrían haber quedado subprioritizados por el score de acceso.", flush=True)
    print(f"  Son candidatos a intervención integrada (clínica + programas sociales).", flush=True)
