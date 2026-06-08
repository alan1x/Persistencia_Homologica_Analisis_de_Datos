# %% [markdown]
# # 08 — Clasificación topológica de huecos H₁
#
# Cada hueco en el diagrama de persistencia ocupa una posición (birth, death)
# que no es aleatoria: codifica el *tipo* de problema de cobertura.
#
# Clasificamos los huecos en 4 arquetipos topológicos usando sus coordenadas
# en el diagrama. Esto convierte los números abstractos de TDA en categorías
# con significado para planeación urbana.

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from lib import data, tda, clasificar, config

# %%
# --- 1. Calcular huecos H₁ por región ---
REGIONES    = ["CDMX", "EDOMEX"]
MIN_PERS    = 200.0

print("Calculando huecos H₁...")
diags = {}
for region in REGIONES:
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    P  = data.puntos(df)
    st = tda.alpha_complex(P)
    dr = tda.a_radio(tda.persistencia(st))
    d  = dr[1]
    mask = np.isfinite(d[:, 1]) & ((d[:, 1] - d[:, 0]) >= MIN_PERS)
    diags[region] = d[mask]
    print(f"  {region}: {mask.sum()} huecos")

# %%
# --- 2. Calcular umbrales compartidos y clasificar ---
umb_birth, umb_pers = clasificar.umbrales_conjuntos(diags)
print(f"\nUmbrales compartidos (medianas del conjunto combinado):")
print(f"  birth      = {umb_birth:.0f} m  ({umb_birth/1000:.2f} km)")
print(f"  persistencia = {umb_pers:.0f} m  ({umb_pers/1000:.2f} km)")
print(f"  crítico    = 3000 m  (3 km)")

dfs_clas = {}
for region in REGIONES:
    df_c = clasificar.clasificar_huecos(
        diags[region],
        umbral_birth=umb_birth,
        umbral_pers=umb_pers,
        umbral_critico=3000.0,
    )
    dfs_clas[region] = df_c
    print(f"\n{region}:")
    res = clasificar.resumen_arquetipos(df_c, region)
    for _, row in res.iterrows():
        if row["n"] > 0:
            print(f"  [{row['prioridad']}] {row['arquetipo']:25s} "
                  f"n={row['n']:3d}  "
                  f"pers_media={row['pers_media_km']:.2f} km  "
                  f"pers_max={row['pers_max_km']:.2f} km")

# %%
# --- 3. Panel principal ---
fig = plt.figure(figsize=(20, 15))
gs  = fig.add_gridspec(2, 3, hspace=0.42, wspace=0.38)

# Colores y leyenda compartida
arq_items = [
    mpatches.Patch(color=v["color"],
                   label=f"[{v['prioridad']}] {k}\n     {v['descripcion']}")
    for k, v in clasificar.ARQUETIPOS.items()
]

# ----- A y B: Diagrama de persistencia coloreado por arquetipo (uno por región) -----
for col, region in enumerate(REGIONES):
    ax = fig.add_subplot(gs[0, col])
    df_c = dfs_clas[region]

    for arq, info in clasificar.ARQUETIPOS.items():
        sub = df_c[df_c["arquetipo"] == arq]
        if len(sub) == 0:
            continue
        ax.scatter(sub["birth_m"] / 1000, sub["pers_m"] / 1000,
                   c=info["color"], s=80, alpha=0.85,
                   edgecolors="white", linewidths=0.5,
                   zorder=3, label=arq)

    # Líneas de umbral
    ax.axvline(umb_birth / 1000, color="grey", lw=1.2, ls="--", alpha=0.7)
    ax.axhline(umb_pers  / 1000, color="grey", lw=1.2, ls="--", alpha=0.7)
    ax.axhline(3.0,               color="#7b2d8b", lw=1.5, ls=":",  alpha=0.8)

    ax.text(umb_birth / 1000 + 0.05, ax.get_ylim()[1] * 0.97 if ax.get_ylim()[1] > 0 else 1,
            "← birth bajo | alto →", fontsize=8, color="grey", va="top")

    ax.set_xlabel("birth (km) — distancia a la que nació el hueco", fontsize=11)
    ax.set_ylabel("persistencia (km) — tamaño del hueco", fontsize=11)
    ax.set_title(f"{region} — Diagrama de persistencia H₁\n"
                 f"coloreado por arquetipo topológico ({len(df_c)} huecos)",
                 fontsize=12)

    # Anotar los 3 peores huecos
    top3 = df_c.nlargest(3, "pers_m")
    for _, row in top3.iterrows():
        ax.annotate(f"{row['pers_m']/1000:.1f} km",
                    xy=(row["birth_m"]/1000, row["pers_m"]/1000),
                    xytext=(8, 4), textcoords="offset points",
                    fontsize=8, color=row["color"],
                    arrowprops=dict(arrowstyle="-", color=row["color"], lw=0.8))

# ----- C: Barras de composición por arquetipo y región -----
ax_comp = fig.add_subplot(gs[0, 2])
arq_nombres = list(clasificar.ARQUETIPOS.keys())
arq_colors  = [clasificar.ARQUETIPOS[a]["color"] for a in arq_nombres]
x     = np.arange(len(REGIONES))
width = 0.18
offsets = np.linspace(-0.27, 0.27, len(arq_nombres))

for i, (arq, color) in enumerate(zip(arq_nombres, arq_colors)):
    vals = []
    for region in REGIONES:
        df_c = dfs_clas[region]
        total = len(df_c)
        n = len(df_c[df_c["arquetipo"] == arq])
        vals.append(100 * n / total if total > 0 else 0)
    bars = ax_comp.bar(x + offsets[i], vals, width, color=color,
                       label=arq, edgecolor="white")
    for bar, v in zip(bars, vals):
        if v > 2:
            ax_comp.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                         f"{v:.0f}%", ha="center", va="bottom", fontsize=8)

ax_comp.set_xticks(x)
ax_comp.set_xticklabels(REGIONES, fontsize=13, fontweight="bold")
ax_comp.set_ylabel("% del total de huecos", fontsize=11)
ax_comp.set_title("¿Qué proporción de huecos\nes de cada tipo?", fontsize=12)
ax_comp.set_ylim(0, 110)

# ----- D: Curva de Betti β₁ anotada con arquetipos -----
ax_betti = fig.add_subplot(gs[1, :2])
colores_reg = {"CDMX": "#d62728", "EDOMEX": "#1f77b4"}
radios_grid = np.linspace(0, 15000, 400)

for region in REGIONES:
    df_c = dfs_clas[region]
    # β₁(r) = número de huecos activos en radio r
    betti = []
    for r in radios_grid:
        activos = ((df_c["birth_m"] <= r) & (df_c["death_m"] > r)).sum()
        betti.append(activos)
    ax_betti.plot(radios_grid / 1000, betti, lw=2.5,
                  color=colores_reg[region], label=region)

# Zona sombreada por arquetipo según rango de birth típico
zonas = [
    ("Micro-brecha",          0,    umb_birth/1000,     "#74c476", 0.10),
    ("Enclave sin cobertura", 0,    umb_birth/1000,     "#d62728", 0.06),
    ("Vacío periférico",      umb_birth/1000, 3.0,      "#fd8d3c", 0.10),
    ("Desierto estructural",  3.0,  15.0,               "#7b2d8b", 0.07),
]
ylims = ax_betti.get_ylim()
for label, x0, x1, color, alpha in zonas:
    ax_betti.axvspan(x0, x1, alpha=alpha, color=color, label=f"zona {label}")

ax_betti.axvline(umb_birth/1000, color="grey", lw=1.2, ls="--")
ax_betti.axvline(3.0,             color="#7b2d8b", lw=1.5, ls=":")
ax_betti.set_xlabel("radio de filtración (km)", fontsize=12)
ax_betti.set_ylabel("β₁ — número de huecos activos", fontsize=12)
ax_betti.set_title(
    "Curva de Betti β₁: ¿cuántos huecos están 'activos' a cada escala?\n"
    "Pico = escala con más huecos simultáneos | Zonas coloreadas = dominio de cada arquetipo",
    fontsize=12)
ax_betti.legend(fontsize=9, ncol=2, loc="upper right")
ax_betti.set_xlim(0, 15)

# ----- E: Tabla de arquetipos explicada -----
ax_tab = fig.add_subplot(gs[1, 2])
ax_tab.axis("off")

titulo = "GUÍA DE ARQUETIPOS TOPOLÓGICOS"
ax_tab.text(0.5, 1.0, titulo, transform=ax_tab.transAxes,
            ha="center", va="top", fontsize=12, fontweight="bold")

y = 0.90
for arq, info in clasificar.ARQUETIPOS.items():
    # Cuadrado de color + nombre
    ax_tab.add_patch(mpatches.FancyBboxPatch(
        (0.01, y - 0.045), 0.97, 0.07,
        boxstyle="round,pad=0.01",
        facecolor=info["color"], alpha=0.15,
        transform=ax_tab.transAxes, clip_on=False))
    ax_tab.text(0.04, y, f"[{info['prioridad']}] {arq}",
                transform=ax_tab.transAxes, fontsize=10,
                fontweight="bold", color=info["color"], va="top")
    ax_tab.text(0.04, y - 0.032, info["descripcion"],
                transform=ax_tab.transAxes, fontsize=8.5,
                color="#333333", va="top", wrap=True)

    # Conteos por región
    conteo = "  ".join(
        f"{r}: {len(dfs_clas[r][dfs_clas[r]['arquetipo']==arq])}"
        for r in REGIONES)
    ax_tab.text(0.96, y, conteo,
                transform=ax_tab.transAxes, fontsize=9,
                ha="right", va="top", color="#555")
    y -= 0.20

fig.suptitle(
    "Clasificación topológica de huecos H₁ — Cobertura de salud SCIAN 62\n"
    f"Umbrales compartidos: birth={umb_birth/1000:.1f} km | "
    f"persistencia={umb_pers/1000:.1f} km | crítico=3 km",
    fontsize=14, y=1.01)

ruta = config.FIGURAS_DIR / "clasificacion_arquetipos.png"
fig.savefig(ruta, dpi=120, bbox_inches="tight")
plt.close(fig)
print(f"\nFigura guardada: {ruta}")
