# %% [markdown]
# # 07 — Comparación topológica entre regiones (Mejora 2)
#
# Compara la **estructura de cobertura de salud** entre CDMX y EDOMEX usando
# los huecos H₁. La Persistence Image convierte cada diagrama en un vector
# para similitud matemática; las gráficas muestran qué significa eso en términos
# reales de cobertura.
#
# Pregunta central: ¿cuántos huecos tiene cada estado, de qué tamaño, y dónde?

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pyproj import Transformer
from lib import data, tda, vectorizar, config

# %%
# --- 1. Calcular huecos H₁ significativos por región ---
REGIONES     = ["CDMX", "EDOMEX"]
MIN_PERS     = 200   # metros mínimos de persistencia para considerar un hueco real

# Categorías de gravedad por tamaño del hueco (radio ≈ persistencia / 2)
CATEGORIAS = [
    ("Micro  < 500 m",   0,     500,   "#fee8c8"),  # pequeño, sin impacto mayor
    ("Menor  500m–1km",  500,   1000,  "#fdbb84"),
    ("Medio  1–3 km",    1000,  3000,  "#e34a33"),  # zona de varios barrios
    ("Grande 3–10 km",   3000,  10000, "#b30000"),  # municipio completo sin cobertura
    ("Crítico > 10 km",  10000, 99999, "#4a0000"),  # zona rural crítica
]

_to_geo = Transformer.from_crs(config.CRS_METROS, "EPSG:4326", always_xy=True)

print("Calculando huecos H₁...")
diags_h1_sig = {}
ciclos_info  = {}   # datos ricos por región

for region in REGIONES:
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    P  = data.puntos(df)
    st = tda.alpha_complex(P)
    dr = tda.a_radio(tda.persistencia(st))
    d  = dr[1]
    mask = np.isfinite(d[:, 1]) & ((d[:, 1] - d[:, 0]) >= MIN_PERS)
    sig  = d[mask]
    diags_h1_sig[region] = sig

    pers = sig[:, 1] - sig[:, 0]

    # Clasificar por categoría
    cats = []
    for label, lo, hi, _ in CATEGORIAS:
        n = int(((pers >= lo) & (pers < hi)).sum())
        cats.append((label, n))

    ciclos_info[region] = {
        "df": df, "P": P, "pers": pers,
        "birth": sig[:, 0], "cats": cats,
    }
    print(f"\n{region}: {len(sig)} huecos ≥ {MIN_PERS} m")
    for label, n in cats:
        bar = "█" * n if n <= 40 else "█" * 40 + f"(+{n-40})"
        print(f"  {label:20s} {n:4d}  {bar}")

# %%
# --- 2. Vectorización para similitud (uso interno) ---
pimgr = vectorizar.ajustar_imager(
    list(diags_h1_sig.values()), pixel_size=500.0, sigma=800.0)
vectores = {r: vectorizar.vectorizar(diags_h1_sig[r], pimgr) for r in REGIONES}
sim = vectorizar.matriz_similitud(vectores, REGIONES)
similitud_AB = float(sim[0, 1])
distancia_AB = 1 - similitud_AB
print(f"\nSimilitud coseno CDMX↔EDOMEX: {similitud_AB:.3f}  "
      f"(distancia: {distancia_AB:.3f})")

# %%
# --- 3. Panel de interpretación ---
fig = plt.figure(figsize=(18, 14))
gs  = fig.add_gridspec(2, 3, hspace=0.45, wspace=0.35)

colores_region = {"CDMX": "#d62728", "EDOMEX": "#1f77b4"}

# ----- Gráfica A: barras apiladas por categoría de gravedad -----
ax_bar = fig.add_subplot(gs[0, :2])
cat_labels = [c[0] for c in CATEGORIAS]
cat_colors = [c[3] for c in CATEGORIAS]
x = np.arange(len(REGIONES))
width = 0.55
bottoms = np.zeros(len(REGIONES))

for ci, (label, lo, hi, color) in enumerate(CATEGORIAS):
    vals = []
    for region in REGIONES:
        pers = ciclos_info[region]["pers"]
        vals.append(int(((pers >= lo) & (pers < hi)).sum()))
    ax_bar.bar(x, vals, width, bottom=bottoms, color=color,
               label=label, edgecolor="white", linewidth=0.8)
    # Etiqueta encima si vale la pena
    for xi, v in enumerate(vals):
        if v > 0:
            ax_bar.text(xi, bottoms[xi] + v / 2, str(v),
                        ha="center", va="center", fontsize=10,
                        color="white" if color not in ("#fee8c8", "#fdbb84") else "#333")
    bottoms += np.array(vals)

ax_bar.set_xticks(x)
ax_bar.set_xticklabels(REGIONES, fontsize=14, fontweight="bold")
ax_bar.set_ylabel("número de huecos H₁", fontsize=12)
ax_bar.set_title(
    "¿Cuántos huecos de cobertura tiene cada estado y qué tan graves son?\n"
    "(cada hueco = zona rodeada de servicios de salud pero sin ninguno adentro)",
    fontsize=13)
ax_bar.legend(loc="upper left", title="Tamaño del hueco (persistencia)", fontsize=9)
ax_bar.set_ylim(0, bottoms.max() * 1.15)

# ----- Gráfica B: perfil acumulado (¿qué % de huecos supera X km?) -----
ax_cum = fig.add_subplot(gs[0, 2])
umbrales = np.linspace(0.2, 12, 200)
for region in REGIONES:
    pers_km = ciclos_info[region]["pers"] / 1000
    total = len(pers_km)
    pct = [100 * (pers_km >= u).sum() / total for u in umbrales]
    ax_cum.plot(umbrales, pct, lw=2.5, color=colores_region[region], label=region)

ax_cum.axvline(1, color="grey", lw=1.2, ls="--")
ax_cum.axvline(3, color="grey", lw=1.2, ls="--")
ax_cum.text(1.05, 92, "1 km", fontsize=9, color="grey")
ax_cum.text(3.05, 92, "3 km", fontsize=9, color="grey")
ax_cum.set_xlabel("persistencia mínima (km)", fontsize=11)
ax_cum.set_ylabel("% de huecos que superan ese tamaño", fontsize=11)
ax_cum.set_title("¿Qué proporción de huecos\nson realmente grandes?", fontsize=12)
ax_cum.legend(fontsize=11)
ax_cum.set_ylim(0, 105)
ax_cum.set_xlim(0, 13)

# ----- Gráfica C y D: los 10 peores huecos de cada región -----
for col, region in enumerate(REGIONES):
    ax = fig.add_subplot(gs[1, col])
    pers_km  = ciclos_info[region]["pers"] / 1000
    birth_km = ciclos_info[region]["birth"] / 1000
    idx_top  = np.argsort(pers_km)[::-1][:10]

    y_pos = np.arange(len(idx_top))
    bars = ax.barh(y_pos,
                   pers_km[idx_top],
                   color=[cat_colors[
                       next(ci for ci,(l,lo,hi,_) in enumerate(CATEGORIAS)
                            if pers_km[i]*1000 < hi)] for i in idx_top],
                   edgecolor="white", height=0.6)

    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"Hueco #{i+1}" for i in range(len(idx_top))], fontsize=9)
    ax.set_xlabel("persistencia (km)", fontsize=11)
    ax.set_title(f"{region} — Top 10 huecos más críticos\n"
                 f"(radio ≈ persistencia/2 = zona sin servicio de salud)",
                 fontsize=12)
    for bar, i in zip(bars, idx_top):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                f"{pers_km[i]:.1f} km  (nace a {birth_km[i]:.1f} km)",
                va="center", fontsize=8)
    ax.set_xlim(0, pers_km[idx_top].max() * 1.45)
    ax.invert_yaxis()

# ----- Gráfica E: resumen numérico -----
ax_txt = fig.add_subplot(gs[1, 2])
ax_txt.axis("off")
lineas = [
    ("RESUMEN COMPARATIVO", "", True),
    ("", "", False),
    ("Huecos totales (≥200 m)", "", True),
]
for region in REGIONES:
    pers = ciclos_info[region]["pers"]
    lineas.append((f"  {region}", f"{len(pers)}", False))

lineas += [("", "", False), ("Huecos críticos (≥3 km)", "", True)]
for region in REGIONES:
    pers = ciclos_info[region]["pers"]
    n_crit = int((pers >= 3000).sum())
    lineas.append((f"  {region}", f"{n_crit}  ({100*n_crit/len(pers):.0f}%)", False))

lineas += [("", "", False), ("Peor hueco (persistencia)", "", True)]
for region in REGIONES:
    pers = ciclos_info[region]["pers"]
    lineas.append((f"  {region}", f"{pers.max()/1000:.1f} km  (~{pers.max()/2000:.1f} km radio)", False))

lineas += [
    ("", "", False),
    ("Similitud topológica", "", True),
    ("  CDMX ↔ EDOMEX", f"{similitud_AB:.3f} / 1.0", False),
    ("  (1.0 = idénticos,", "", False),
    ("   0.0 = completamente", "", False),
    ("   distintos)", "", False),
]

y = 0.97
for izq, der, bold in lineas:
    w = "bold" if bold else "normal"
    ax_txt.text(0.02, y, izq, transform=ax_txt.transAxes,
                fontsize=11, va="top", fontweight=w)
    if der:
        ax_txt.text(0.98, y, der, transform=ax_txt.transAxes,
                    fontsize=11, va="top", ha="right",
                    color="#d62728" if "CDMX" in izq else
                          "#1f77b4" if "EDOMEX" in izq else "black")
    y -= 0.07 if bold else 0.06

fig.suptitle(
    "Comparación topológica de cobertura de salud — CDMX vs EDOMEX\n"
    "Sector SCIAN 62 · Fuente: DENUE (INEGI) · Método: Alpha complex + Persistencia H₁",
    fontsize=14, y=1.01)

ruta = config.FIGURAS_DIR / "comparacion_topologica.png"
fig.savefig(ruta, dpi=120, bbox_inches="tight")
plt.close(fig)
print(f"\nFigura guardada: {ruta}")

#
# Convierte cada diagrama H₁ en un **vector de números** (Persistence Image)
# para comparar regiones con similitud coseno, dendrograma y PCA.
#
# **¿Por qué?**
# Las distancias bottleneck/Wasserstein solo comparan de a dos. Con vectores
# puedes comparar los 32 estados de México en una sola tabla y detectar cuáles
# tienen topología de cobertura similar — sin necesidad de definir nada a mano.
#
# **Cómo funciona la Persistence Image:**
# 1. Se toma el diagrama H₁ y se rota al plano (birth, persistencia).
# 2. Se coloca una gaussiana centrada en cada punto.
# 3. Se pixeliza en una imagen de tamaño fijo → vector 1D.
# 4. TODOS los estados comparten el mismo grid (ajustado en conjunto),
#    por eso los vectores son comparables entre sí.

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
from lib import data, tda, vectorizar, config

# %%
# --- 1. Calcular diagramas H₁ para cada región ---
# Filtramos a huecos con persistencia >= MIN_PERS_IMG para eliminar el ruido
# de escala fina (hay ~13k clases H₁ en total, la mayoría son artefactos
# microscópicos). Solo los 71/209 huecos >= 200 m son informativos.
REGIONES    = ["CDMX", "EDOMEX"]
MIN_PERS_IMG = 200.0  # metros — mismo umbral que en el notebook 03

print("Calculando diagramas H₁ (solo clases con persistencia >= 200 m)...")
diags_h1     = {}   # diagrama completo (para vectorización)
diags_h1_sig = {}   # solo huecos significativos (para la imagen)
for region in REGIONES:
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    P = data.puntos(df)
    st = tda.alpha_complex(P)
    dr = tda.a_radio(tda.persistencia(st))
    d = dr[1]
    diags_h1[region] = d
    # Filtro: finito Y persistencia >= umbral
    mask = np.isfinite(d[:, 1]) & ((d[:, 1] - d[:, 0]) >= MIN_PERS_IMG)
    diags_h1_sig[region] = d[mask]
    print(f"  {region}: {int(mask.sum())} huecos significativos "
          f"(de {len(d)} clases H₁ totales)")

# %%
# --- 2. Ajustar el imager solo sobre los huecos significativos ---
# pixel_size=500 m → cada píxel cubre 500 metros (adecuado para rango de kms)
# sigma=800 m      → gaussiana ancha, visible en la imagen
print("\nAjustando PersistenceImager...")
pimgr = vectorizar.ajustar_imager(
    list(diags_h1_sig.values()),
    pixel_size=500.0,
    sigma=800.0,
)
print(f"  Grid: birth {pimgr.birth_range[0]/1000:.1f}–{pimgr.birth_range[1]/1000:.1f} km  |  "
      f"pers {pimgr.pers_range[0]/1000:.1f}–{pimgr.pers_range[1]/1000:.1f} km")
img_ejemplo = pimgr.transform([diags_h1_sig[REGIONES[0]]])[0]
print(f"  Tamaño imagen: {img_ejemplo.shape} → vector de {img_ejemplo.size} features")

# %%
# --- 3. Vectorizar cada región (usando solo huecos significativos) ---
print("\nVectorizando diagramas...")
vectores = {}
for region in REGIONES:
    vec = vectorizar.vectorizar(diags_h1_sig[region], pimgr)
    vectores[region] = vec
    print(f"  {region}: vector shape={vec.shape}  norma={np.linalg.norm(vec):.4f}")

# %%
# --- 4. Matriz de similitud coseno ---
mat_sim = vectorizar.matriz_similitud(vectores, REGIONES)
print("\nMatriz de similitud coseno (H₁):")
print(f"  {'':12}", "  ".join(f"{r:>8}" for r in REGIONES))
for i, r in enumerate(REGIONES):
    vals = "  ".join(f"{mat_sim[i, j]:>8.4f}" for j in range(len(REGIONES)))
    print(f"  {r:12} {vals}")

print(f"\nInterpretación:")
sim = mat_sim[0, 1]
if sim > 0.9:
    interp = "muy similares — topología de cobertura casi idéntica"
elif sim > 0.7:
    interp = "moderadamente similares — diferencias estructurales notables"
else:
    interp = "muy distintas — topología de cobertura radicalmente diferente"
print(f"  CDMX vs EDOMEX: {sim:.4f} → {interp}")

# %%
# --- 5. Panel de visualización ---
print("\nGenerando panel de visualización...")
ruta, _ = vectorizar.panel_vectorizacion(pimgr, diags_h1_sig, vectores, REGIONES)
print(f"  Guardado: {ruta}")

print("\n" + "="*60)
print("RESUMEN — Persistence Images H₁")
print("="*60)
print(f"Regiones analizadas : {', '.join(REGIONES)}")
print(f"Features por región : {list(vectores.values())[0].shape[0]}")
print(f"Similitud coseno    : {sim:.4f}")
print(f"\nEste pipeline está listo para escalar a los 32 estados.")
print(f"Solo agrega los parquets de cada estado en INTERMEDIOS_DIR")
print(f"y añade sus nombres a la lista REGIONES.")
