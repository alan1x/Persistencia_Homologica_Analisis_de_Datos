# %% [markdown]
# # 11 — Fase 2A: Topología Ponderada (Weighted Alpha Complex / Laguerre)
#
# **Pregunta central:** ¿Qué huecos de cobertura de salud persisten incluso cuando
# reconocemos que los hospitales grandes cubren más territorio que los consultorios chicos?
#
# **Método:** Weighted Alpha Complex (Gudhi). El radio de influencia de cada clínica
# crece sublinealmente con su personal ocupado:
#   r_i = radio_base + factor × √(per_ocu_i)
#
# Los huecos que **sobreviven** la ponderación = verdaderos desiertos estructurales.
# Ni siquiera la infraestructura mayor alcanza a cubrirlos.

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import folium
from pyproj import Transformer
from lib import data, tda, config

# %%
REGIONES      = ["CDMX", "EDOMEX"]
MIN_PERS      = 200.0   # metros — umbral mínimo de persistencia
RADIO_BASE    = 50.0    # metros — radio mínimo de cualquier consultorio
FACTOR_PESO   = 30.0    # metros / √persona

_TO_GEO = Transformer.from_crs(config.CRS_METROS, "EPSG:4326", always_xy=True)

def _latlon(cx, cy):
    lon, lat = _TO_GEO.transform(cx, cy)
    return lat, lon

# %% [markdown]
# ## 1. Calcular huecos: Alpha Classic vs Weighted Alpha (Laguerre)

# %%
resultados = {}

for region in REGIONES:
    print(f"\n{'='*60}")
    print(f"  {region}")
    print(f"{'='*60}")

    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    P  = data.puntos(df)
    print(f"  Unidades médicas: {len(P):,}")

    # Alpha complex clásico (todas las clínicas pesan igual)
    print("  → Alpha Complex clásico...")
    st_cls    = tda.alpha_complex(P)
    ciclos_cls = tda.ciclos_H1(st_cls, P, min_persistencia=MIN_PERS)

    # Weighted Alpha Complex — diagramas de Laguerre
    print("  → Weighted Alpha Complex (Laguerre)...")
    pesos      = tda.pesos_desde_per_ocu(df, radio_base=RADIO_BASE, factor=FACTOR_PESO)
    st_pond    = tda.weighted_alpha_complex(P, pesos)
    ciclos_pond = tda.ciclos_H1(st_pond, P, min_persistencia=MIN_PERS)

    max_cls  = max(c["pers"] for c in ciclos_cls)  if ciclos_cls  else 0
    max_pond = max(c["pers"] for c in ciclos_pond) if ciclos_pond else 0
    avg_cls  = np.mean([c["pers"] for c in ciclos_cls])  if ciclos_cls  else 0
    avg_pond = np.mean([c["pers"] for c in ciclos_pond]) if ciclos_pond else 0
    reduc_n  = (len(ciclos_cls) - len(ciclos_pond)) / len(ciclos_cls) * 100 if ciclos_cls else 0

    print(f"  Clásico:   {len(ciclos_cls):4d} huecos | peor {max_cls:8,.0f}m | promedio {avg_cls:,.0f}m")
    print(f"  Ponderado: {len(ciclos_pond):4d} huecos | peor {max_pond:8,.0f}m | promedio {avg_pond:,.0f}m")
    print(f"  → Los hospitales grandes absorbieron {len(ciclos_cls)-len(ciclos_pond)} huecos ({reduc_n:.1f}%)")

    # Cargar datos censales de Fase 1 para enriquecer los huecos supervivientes
    ruta_censo = config.INTERMEDIOS_DIR / f"huecos_censal_{region}.parquet"
    df_censo   = pd.read_parquet(str(ruta_censo)) if ruta_censo.exists() else None

    resultados[region] = {
        "df": df, "P": P, "pesos": pesos,
        "clasicos": ciclos_cls, "ponderados": ciclos_pond,
        "df_censo": df_censo,
        "reduc_n": reduc_n, "max_cls": max_cls, "max_pond": max_pond,
        "avg_cls": avg_cls, "avg_pond": avg_pond,
    }

# %% [markdown]
# ## 2. Figura comparativa: impacto de la ponderación

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(
    "Fase 2A — Impacto de la Topología Ponderada (Laguerre)\n"
    "Al dar más 'peso gravitacional' a los hospitales grandes, ¿cuántos huecos desaparecen?",
    fontsize=13, fontweight="bold"
)

colores_cls  = ["#4393c3", "#74add1"]   # azul CDMX, azul EDOMEX
colores_pond = ["#d6604d", "#f46d43"]   # rojo CDMX, rojo EDOMEX

# --- Subplot izquierdo: Número de huecos ---
ax1 = axes[0]
x   = np.arange(len(REGIONES))
w   = 0.32

for i, (label, key, colores) in enumerate([
    ("Clásico (igual peso)", "clasicos", colores_cls),
    ("Ponderado / Laguerre", "ponderados", colores_pond),
]):
    vals = [len(resultados[r][key]) for r in REGIONES]
    bars = ax1.bar(x + (i - 0.5) * w, vals, width=w, label=label,
                   color=colores, edgecolor="white", linewidth=1.2)
    for bar, v in zip(bars, vals):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                 str(v), ha="center", va="bottom", fontsize=12, fontweight="bold")

for r_i, region in enumerate(REGIONES):
    n_abs = len(resultados[region]["clasicos"]) - len(resultados[region]["ponderados"])
    pct   = resultados[region]["reduc_n"]
    ax1.annotate(
        f"−{n_abs} huecos\n({pct:.0f}% absorbidos)",
        xy=(r_i, len(resultados[region]["ponderados"]) + 1),
        xytext=(r_i, len(resultados[region]["clasicos"]) * 0.6),
        fontsize=8, ha="center", color="#555",
        arrowprops=dict(arrowstyle="->", color="#888", lw=1),
    )

ax1.set_xticks(x)
ax1.set_xticklabels(REGIONES, fontsize=12)
ax1.set_ylabel("Número de huecos H₁ detectados (pers. ≥ 200m)", fontsize=10)
ax1.set_title("¿Cuántos huecos sobreviven la ponderación?", fontsize=11, fontweight="bold")
ax1.legend(fontsize=9)
ax1.set_ylim(0, max(len(resultados[r]["clasicos"]) for r in REGIONES) * 1.3)
ax1.spines[["top", "right"]].set_visible(False)

# --- Subplot derecho: distribución de persistencia (violin) ---
ax2 = axes[1]
data_vio, labels_vio, colors_vio = [], [], []

for r_i, region in enumerate(REGIONES):
    for label, key, color in [
        ("Clásico", "clasicos",  colores_cls[r_i]),
        ("Ponderado","ponderados", colores_pond[r_i]),
    ]:
        vals = [c["pers"] for c in resultados[region][key]]
        if vals:
            data_vio.append(vals)
            labels_vio.append(f"{region}\n{label}")
            colors_vio.append(color)

vp = ax2.violinplot(data_vio, showmedians=True, showextrema=True)
for pc, color in zip(vp["bodies"], colors_vio):
    pc.set_facecolor(color)
    pc.set_alpha(0.7)
vp["cmedians"].set_color("black")
vp["cmedians"].set_linewidth(2)

ax2.set_xticks(range(1, len(labels_vio) + 1))
ax2.set_xticklabels(labels_vio, fontsize=8)
ax2.set_ylabel("Persistencia del hueco (metros)", fontsize=10)
ax2.set_title("Distribución del tamaño de los huecos por método", fontsize=11, fontweight="bold")
ax2.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta_fig = config.FIGURAS_DIR / "laguerre_comparacion.png"
plt.savefig(str(ruta_fig), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"\n✓ Figura guardada: {ruta_fig}")

# %% [markdown]
# ## 3. Mapas interactivos: Clásico (azul) vs Laguerre (rojo) por región

# %%
for region in REGIONES:
    cls  = resultados[region]["clasicos"]
    pond = resultados[region]["ponderados"]

    if not cls:
        print(f"  {region}: sin huecos, saltando mapa.")
        continue

    centro_lat, centro_lon = _latlon(*cls[0]["centroide"])
    mapa = folium.Map(location=[centro_lat, centro_lon], zoom_start=10,
                      tiles="CartoDB positron")

    # Capa 1: huecos clásicos (azul) — algunos serán absorbidos por hospitales
    g_cls = folium.FeatureGroup(name=f"Huecos Clásicos — {len(cls)} total (azul)", show=True)
    for i, c in enumerate(cls):
        lat, lon = _latlon(*c["centroide"])
        folium.Circle(
            location=[lat, lon],
            radius=c["pers"] * 0.5,
            color="#4393c3", fill=True, fill_opacity=0.25, weight=1.5,
            tooltip=f"Clásico #{i}: {c['pers']:.0f}m",
            popup=(f"<b>Hueco Clásico #{i}</b><br>"
                   f"Persistencia: {c['pers']:.0f}m<br>"
                   f"Birth: {c['birth']:.0f}m — Death: {c['death']:.0f}m"),
        ).add_to(g_cls)
    g_cls.add_to(mapa)

    # Capa 2: huecos ponderados (rojo) — los verdaderos desiertos
    g_pond = folium.FeatureGroup(
        name=f"Huecos Laguerre — {len(pond)} supervivientes (rojo)", show=True
    )
    for i, c in enumerate(pond):
        lat, lon = _latlon(*c["centroide"])
        folium.Circle(
            location=[lat, lon],
            radius=c["pers"] * 0.5,
            color="#d6604d", fill=True, fill_opacity=0.55, weight=2,
            tooltip=f"Laguerre #{i}: {c['pers']:.0f}m",
            popup=(f"<b>Hueco Laguerre #{i}</b><br>"
                   f"<b>Desierto estructural — ni los hospitales grandes lo cubren</b><br>"
                   f"Persistencia: {c['pers']:.0f}m<br>"
                   f"Birth: {c['birth']:.0f}m — Death: {c['death']:.0f}m"),
        ).add_to(g_pond)
    g_pond.add_to(mapa)

    titulo = (
        f'<div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);'
        f'z-index:1000;background:white;padding:8px 16px;border-radius:8px;'
        f'box-shadow:0 2px 8px rgba(0,0,0,.3);font-family:sans-serif;font-size:13px;">'
        f'<b>{region}</b> — Clásico: {len(cls)} huecos (azul) → '
        f'Laguerre: {len(pond)} huecos (rojo)<br>'
        f'<small>Rojo = desiertos que persisten incluso con pesos de capacidad hospitalaria</small>'
        f'</div>'
    )
    mapa.get_root().html.add_child(folium.Element(titulo))
    folium.LayerControl(collapsed=False).add_to(mapa)

    ruta_mapa = config.FIGURAS_DIR / f"huecos_laguerre_{region}.html"
    mapa.save(str(ruta_mapa))
    print(f"✓ Mapa {region}: {ruta_mapa}")

# %% [markdown]
# ## 4. Top 5 huecos supervivientes por región

# %%
print("\n" + "=" * 70)
print("TOP 5 HUECOS SUPERVIVIENTES EN EL MODELO PONDERADO (LAGUERRE)")
print("Estos son los verdaderos desiertos: ni los hospitales grandes los cubren.")
print("=" * 70)

for region in REGIONES:
    pond     = resultados[region]["ponderados"]
    df_censo = resultados[region]["df_censo"]

    print(f"\n  [{region}] — {len(pond)} huecos ponderados, top 5:")
    tiene_censo = df_censo is not None and "pob_afectada" in df_censo.columns

    header = f"  {'#':>3}  {'Pers.(m)':>9}  {'Birth(m)':>8}  {'Death(m)':>8}"
    if tiene_censo:
        header += f"  {'Pob.afect.':>10}  {'Sin seguro':>10}  {'%':>6}  {'Nivel':>9}"
    print(header)
    print("  " + "—" * (80 if tiene_censo else 40))

    for i, c in enumerate(pond[:5]):
        lat, lon = _latlon(*c["centroide"])
        fila = f"  {i+1:3d}  {c['pers']:9.0f}  {c['birth']:8.0f}  {c['death']:8.0f}"
        if tiene_censo and i < len(df_censo):
            row = df_censo.iloc[i]
            fila += (
                f"  {int(row.get('pob_afectada', 0)):>10,}"
                f"  {int(row.get('pob_sin_salud', 0)):>10,}"
                f"  {row.get('pct_sin_salud_prom', 0):>6.1f}%"
                f"  {str(row.get('nivel_prioridad', 'N/A')):>9}"
            )
        else:
            fila += f"  (lat={lat:.4f}, lon={lon:.4f})"
        print(fila)

# %%
print("\n\n✓ Fase 2A (Laguerre) completada.")
print("  outputs/figuras/laguerre_comparacion.png   — comparación de métodos")
print("  outputs/figuras/huecos_laguerre_CDMX.html  — mapa interactivo CDMX")
print("  outputs/figuras/huecos_laguerre_EDOMEX.html — mapa interactivo EDOMEX")
