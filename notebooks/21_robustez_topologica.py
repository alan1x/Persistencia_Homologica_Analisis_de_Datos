# %% [markdown]
# # 21 — Robustez Topológica: Mismo Hueco a 4 Radios de Persistencia
#
# Pregunta central: ¿los huecos que priorizamos son artefactos del umbral elegido,
# o aparecen consistentemente en un rango amplio de radios mínimos de persistencia?
#
# Metodología:
#   Se re-ejecuta ciclos_H1() con min_persistencia ∈ {100, 200, 400, 600} metros.
#   Un hueco "robusto" es aquel cuyo centroide (lat, lon) aparece en TODOS los umbrales
#   (distancia entre centroides < 500 m → mismo hueco geográfico).
#
# Resultado esperado:
#   Los huecos de alta persistencia (pers_m > 400 m) deben ser los más robustos
#   porque sobreviven incluso al umbral más exigente.

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.spatial import cKDTree
from pyproj import Transformer

from lib import config
from lib.tda import ciclos_H1

# %%
REGIONES      = ["CDMX", "EDOMEX"]
UMBRALES_PERS = [100, 200, 400, 600]    # metros — 4 radios a comparar
RADIO_MATCH   = 500                      # metros — dos centroides = mismo hueco
COLORES_U     = {100: "#d0d0d0", 200: "#fdae61", 400: "#e08214", 600: "#b2182b"}
COLORES_R     = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}

# %% [markdown]
# ## 1. Calcular huecos a cada umbral de persistencia
#
# El Alpha complex se construye UNA sola vez por región; solo cambia el filtro de persistencia.

# %%
import lib.tda as tda

huecos_por_umbral = {region: {} for region in REGIONES}

for region in REGIONES:
    sal   = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    pts   = np.column_stack([sal["x"].values, sal["y"].values])  # UTM
    pesos = tda.pesos_desde_per_ocu(sal)
    st    = tda.weighted_alpha_complex(pts, pesos)
    print(f"[{region}]  Alpha complex construido  ({len(pts):,} clínicas)", flush=True)

    for u in UMBRALES_PERS:
        ciclos = tda.ciclos_H1(st, pts, min_persistencia=u)

        if not ciclos:
            huecos_por_umbral[region][u] = pd.DataFrame()
            print(f"  u={u:4d}m  →  0 huecos")
            continue

        # Convertir lista de dicts → DataFrame
        rows = []
        for c in ciclos:
            cx, cy = c["centroide"]   # UTM metros
            rows.append({"x_utm": cx, "y_utm": cy, "pers_m": c["pers"],
                          "birth_m": c["birth"], "death_m": c["death"]})
        df_u = pd.DataFrame(rows)

        huecos_por_umbral[region][u] = df_u
        print(f"  u={u:4d}m  →  {len(df_u):4d} huecos  "
              f"pers_max={df_u['pers_m'].max():.0f}m", flush=True)
    print()

# %% [markdown]
# ## 2. Clasificar huecos por nivel de robustez (cuántos umbrales sobreviven)

# %%
def encontrar_robustos(huecos_dict, radio_match=RADIO_MATCH):
    """
    Toma huecos del umbral más restrictivo (600 m) como base y verifica
    cuántos umbrales menores también detectan cada hueco (match espacial).

    Devuelve DataFrame con columna 'n_umbrales' (1–4).
    """
    umbrales = sorted(huecos_dict.keys())
    base_u   = umbrales[-1]    # umbral más exigente (600 m) como referencia

    if len(huecos_dict[base_u]) == 0:
        return pd.DataFrame()

    base = huecos_dict[base_u].copy()
    base["n_umbrales"] = 1

    base_xy = np.column_stack([base["x_utm"].values, base["y_utm"].values])
    for u in umbrales[:-1]:
        df_u = huecos_dict[u]
        if len(df_u) == 0:
            continue
        tree_u = cKDTree(np.column_stack([df_u["x_utm"].values, df_u["y_utm"].values]))
        dists, _ = tree_u.query(base_xy)
        base["n_umbrales"] += (dists < radio_match).astype(int)

    return base

robustos = {}
for region in REGIONES:
    robustos[region] = encontrar_robustos(huecos_por_umbral[region])
    if len(robustos[region]) > 0:
        n4 = (robustos[region]["n_umbrales"] == 4).sum()
        n3 = (robustos[region]["n_umbrales"] == 3).sum()
        print(f"[{region}]  Robustos (4 umbrales): {n4}  |  3 umbrales: {n3}  "
              f"|  Total base (u=600m): {len(robustos[region])}")

# %% [markdown]
# ## 3. Figura 1: Conteo de huecos por umbral — curva de estabilidad TDA

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(
    "Estabilidad topológica: conteo de huecos según umbral mínimo de persistencia\n"
    "Un hueco que aparece a 600 m de persistencia mínima es una señal muy robusta",
    fontsize=12, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    counts = [len(huecos_por_umbral[region].get(u, pd.DataFrame())) for u in UMBRALES_PERS]

    bars = ax.bar([str(u) for u in UMBRALES_PERS], counts,
                  color=[COLORES_U[u] for u in UMBRALES_PERS],
                  edgecolor="white", linewidth=1.5, width=0.55)

    for bar, cnt in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                str(cnt), ha="center", va="bottom", fontsize=11, fontweight="bold")

    # Línea de tendencia suavizada
    ax.plot([str(u) for u in UMBRALES_PERS], counts,
            "o--", color="#555", linewidth=1.5, markersize=6, alpha=0.7,
            label="Tendencia")

    # Anotación del umbral de referencia (análisis principal = 200 m)
    idx_200 = UMBRALES_PERS.index(200)
    ax.bar([str(200)], [counts[idx_200]], color=COLORES_U[200],
           edgecolor="#333", linewidth=2.5, width=0.55)
    ax.text(idx_200, counts[idx_200] + counts[0] * 0.03,
            "← umbral\nprincipal", ha="left", va="bottom",
            fontsize=8, color="#333", fontstyle="italic")

    ax.set_xlabel("Persistencia mínima (metros)", fontsize=10)
    ax.set_ylabel("Número de huecos detectados", fontsize=10)
    ax.set_title(f"{region}", fontsize=12, fontweight="bold", color=COLORES_R[region])
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "robustez_conteo_huecos.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 4. Figura 2: Mapa de robustez — mismo hueco a 4 radios

# %%
fig, axes = plt.subplots(1, 2, figsize=(18, 9))
fig.suptitle(
    "Mapa de robustez topológica — Huecos coloreados por cuántos umbrales los detectan\n"
    "Rojo oscuro = aparece en los 4 umbrales → señal más sólida para política pública",
    fontsize=12, fontweight="bold"
)

COLOR_N = {1: "#d0d0d0", 2: "#fdae61", 3: "#e08214", 4: "#b2182b"}
LABEL_N = {1: "Solo 600 m", 2: "2 umbrales", 3: "3 umbrales", 4: "4 umbrales (máx. robustez)"}

for ax, region in zip(axes, REGIONES):
    ax.set_facecolor("#f0f4f8")

    # Clínicas existentes como fondo de referencia
    sal = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    ax.hexbin(sal["x"].values, sal["y"].values, gridsize=40, cmap="Greys", alpha=0.12, zorder=1, mincnt=1)

    # Todos los huecos de u=200 (análisis principal) en gris claro de fondo
    df_200 = huecos_por_umbral[region].get(200, pd.DataFrame())
    if len(df_200) > 0:
        for _, row in df_200.iterrows():
            circ = plt.Circle((row["x_utm"], row["y_utm"]), row["pers_m"],
                               facecolor="#e0e0e0", alpha=0.25,
                               edgecolor="#ccc", linewidth=0.5, zorder=2)
            ax.add_patch(circ)

    # Huecos robustos (del umbral 600 m) coloreados por nivel de robustez
    df_rob = robustos.get(region, pd.DataFrame())
    if len(df_rob) > 0:
        for n_u in [1, 2, 3, 4]:
            sub = df_rob[df_rob["n_umbrales"] == n_u]
            if len(sub) == 0:
                continue
            for _, row in sub.iterrows():
                circ = plt.Circle((row["x_utm"], row["y_utm"]), row["pers_m"],
                                   facecolor=COLOR_N[n_u],
                                   alpha=0.75 if n_u == 4 else 0.55,
                                   edgecolor="white",
                                   linewidth=2.0 if n_u == 4 else 0.8,
                                   zorder=3 + n_u)
                ax.add_patch(circ)

    ax.set_aspect("equal")
    ax.set_axis_off()

    n4 = (df_rob["n_umbrales"] == 4).sum() if len(df_rob) > 0 else 0
    n_200 = len(df_200)
    ax.set_title(
        f"{region}\n"
        f"Huecos u=200m: {n_200}  |  Robustos (4 umbrales): {n4}",
        fontsize=11, fontweight="bold", color=COLORES_R[region]
    )

# Leyenda compartida
handles = [mpatches.Patch(color=COLOR_N[n], alpha=0.8, label=LABEL_N[n])
           for n in [4, 3, 2, 1]]
handles.append(mpatches.Patch(color="#e0e0e0", alpha=0.5,
                               label="Huecos u=200m (referencia)"))
fig.legend(handles=handles, loc="lower center", ncol=5,
           fontsize=9, bbox_to_anchor=(0.5, 0.01), framealpha=0.95)

plt.tight_layout(rect=[0, 0.06, 1, 1])
ruta = config.FIGURAS_DIR / "robustez_mapa.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 5. Figura 3: Persistencia vs robustez — validación del criterio de selección

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(
    "Persistencia (radio del hueco) vs nivel de robustez\n"
    "Confirma que persistencia alta → mayor robustez → mejor candidato para intervención",
    fontsize=12, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df_rob = robustos.get(region, pd.DataFrame())
    if len(df_rob) == 0:
        ax.text(0.5, 0.5, "Sin datos", transform=ax.transAxes,
                ha="center", va="center", fontsize=12)
        continue

    for n_u in [1, 2, 3, 4]:
        sub = df_rob[df_rob["n_umbrales"] == n_u]
        if len(sub) == 0:
            continue
        ax.scatter(sub["pers_m"], [n_u] * len(sub),
                   c=COLOR_N[n_u], s=80,
                   alpha=0.80, edgecolors="white", linewidths=0.5, zorder=3,
                   label=f"{LABEL_N[n_u]} ({len(sub)})")

    ax.axvline(400, color="#555", linestyle="--", linewidth=1.5, alpha=0.7,
               label="pers_m = 400 m\n(alta robustez esperada)")
    ax.set_xlabel("Persistencia del hueco (metros)", fontsize=10)
    ax.set_ylabel("Número de umbrales donde aparece", fontsize=10)
    ax.set_yticks([1, 2, 3, 4])
    ax.set_yticklabels(["Solo u=600", "2 umbrales", "3 umbrales", "4 umbrales"], fontsize=9)
    ax.set_title(f"{region}", fontsize=12, fontweight="bold", color=COLORES_R[region])
    ax.legend(fontsize=8, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "robustez_persistencia_vs_umbrales.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 6. Resumen ejecutivo

# %%
print("\n" + "="*72)
print("ROBUSTEZ TOPOLÓGICA — RESUMEN")
print("="*72)

for region in REGIONES:
    print(f"\n  [{region}]")
    print(f"  {'Umbral (m)':>12}  {'Huecos':>7}")
    print(f"  {'—'*22}")
    for u in UMBRALES_PERS:
        n = len(huecos_por_umbral[region].get(u, pd.DataFrame()))
        marca = "  ← análisis principal" if u == 200 else ""
        print(f"  {u:12d}  {n:7d}{marca}")

    df_rob = robustos.get(region, pd.DataFrame())
    if len(df_rob) > 0:
        df_200 = huecos_por_umbral[region].get(200, pd.DataFrame())
        n_alta_pers = int((df_200["pers_m"] > 400).sum()) if len(df_200) > 0 else 0
        print(f"\n  Huecos con pers_m > 400 m (u=200m): {n_alta_pers}")
        print(f"  Huecos robustos (aparecen en 4 umbrales): {(df_rob['n_umbrales'] == 4).sum()}")
        print(f"  Huecos robustos (3+ umbrales):            {(df_rob['n_umbrales'] >= 3).sum()}")
        print(f"\n  Interpretación:")
        print(f"  Los {(df_rob['n_umbrales'] == 4).sum()} huecos que aparecen en los 4 umbrales")
        print(f"  representan señales topológicas sólidas, independientes del umbral elegido.")
        print(f"  Son los candidatos de mayor prioridad para intervención de política pública.")

print("\n✓ Figuras generadas:")
for f in ["robustez_conteo_huecos.png", "robustez_mapa.png",
          "robustez_persistencia_vs_umbrales.png"]:
    print(f"  outputs/figuras/{f}")
