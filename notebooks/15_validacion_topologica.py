# %% [markdown]
# # 15 — Fase 3: Validación Topológica y Mapas Finales con OSMnx
#
# **Propósito:** Tomar las coordenadas óptimas del notebook 14 y validarlas de dos formas:
#
#   1. **Validación topológica:** Recalcular el Alpha complex *incluyendo* la clínica nueva.
#      Si el hueco H₁ desaparece del diagrama de persistencia → la ubicación realmente
#      cierra el desierto topológico. Si persiste → se necesita ajuste.
#
#   2. **Validación con OSMnx:** Calcular el tiempo real de caminata desde los huecos
#      más críticos hasta la clínica nueva propuesta, y mostrar la isócrona nueva.
#
# Se validan las soluciones K=1 del escenario compuesto (score multi-eje)
# para los top 5 huecos más urgentes de cada ciudad.

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
import geopandas as gpd
import osmnx as ox
import networkx as nx
from scipy.spatial import cKDTree
from pyproj import Transformer

from lib import config, data, tda, geo_network

# %%
REGIONES    = ["CDMX", "EDOMEX"]
VELOCIDAD   = 4.5
DETOUR      = 1.35
TIEMPO_LIM  = 15
RADIO_OSM_M = 2000
MIN_PERS    = 200.0
TOP_VAL     = 3   # huecos a validar por ciudad (OSMnx es lento)

_VEL_M_MIN  = (VELOCIDAD * 1000) / 60
_TR_GEO_UTM = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)
_TR_UTM_GEO = Transformer.from_crs(config.CRS_METROS, "EPSG:4326", always_xy=True)

COLORES = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}

# %% [markdown]
# ## 1. Cargar datos y solución MCLP

# %%
dfs   = {r: pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_score_{r}.parquet")
         for r in REGIONES}
salud = {r: pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{r}.parquet")
         for r in REGIONES}

df_coords = pd.read_csv(config.INTERMEDIOS_DIR / "recomendaciones_mclp.csv")

# Seleccionar soluciones K=1, escenario compuesto, para validar
soluciones = {}
for region in REGIONES:
    sub = df_coords[
        (df_coords["ciudad"] == region) &
        (df_coords["escenario"] == "C_compuesto") &
        (df_coords["K"] == 1)
    ]
    soluciones[region] = sub.iloc[0].to_dict() if len(sub) > 0 else None
    if soluciones[region]:
        print(f"[{region}] Clínica propuesta K=1 Compuesto: "
              f"({sub.iloc[0]['lat']:.5f}, {sub.iloc[0]['lon']:.5f})  "
              f"→ {int(sub.iloc[0]['huecos_cubiertos'])} huecos cubiertos")

# %% [markdown]
# ## 2. Validación Topológica — ¿Desaparece el hueco H₁?

# %%
print("\n" + "="*65)
print("VALIDACIÓN TOPOLÓGICA")
print("="*65)

val_topo = {}

for region in REGIONES:
    sol  = soluciones[region]
    if sol is None:
        continue

    df_reg  = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    df_hue  = dfs[region]

    print(f"\n[{region}]")

    # Alpha complex ORIGINAL (sin clínica nueva)
    P_orig  = data.puntos(df_reg)
    st_orig = tda.alpha_complex(P_orig)
    ciclos_orig = tda.ciclos_H1(st_orig, P_orig, min_persistencia=MIN_PERS)
    n_huecos_orig = len(ciclos_orig)
    print(f"  Alpha complex original: {len(P_orig):,} clínicas → {n_huecos_orig} huecos H₁")

    # Agregar clínica nueva al conjunto de puntos
    lat_n, lon_n = sol["lat"], sol["lon"]
    x_n, y_n    = _TR_GEO_UTM.transform(lon_n, lat_n)
    P_nuevo     = np.vstack([P_orig, [[x_n, y_n]]])

    # Alpha complex CON clínica nueva
    st_nuevo = tda.alpha_complex(P_nuevo)
    ciclos_nuevo = tda.ciclos_H1(st_nuevo, P_nuevo, min_persistencia=MIN_PERS)
    n_huecos_nuevo = len(ciclos_nuevo)
    delta = n_huecos_orig - n_huecos_nuevo

    print(f"  Alpha complex + clínica nueva: {len(P_nuevo):,} clínicas → {n_huecos_nuevo} huecos H₁")
    print(f"  → {'✓' if delta > 0 else '—'} Huecos eliminados: {delta}  "
          f"({'VALIDADO' if delta > 0 else 'Sin cambio — la ubicación no cierra huecos estructurales'})")

    val_topo[region] = {
        "n_orig": n_huecos_orig,
        "n_nuevo": n_huecos_nuevo,
        "delta": delta,
        "ciclos_orig": ciclos_orig,
        "ciclos_nuevo": ciclos_nuevo,
        "P_orig": P_orig,
        "P_nuevo": P_nuevo,
        "clinica_nueva_utm": (x_n, y_n),
    }

# %% [markdown]
# ## 3. Comparación de Diagramas de Persistencia (antes/después)

# %%
fig, axes = plt.subplots(2, 2, figsize=(14, 12))
fig.suptitle(
    "Validación Topológica — Diagrama de Persistencia H₁ antes y después\n"
    "de agregar la clínica óptima propuesta (escenario compuesto K=1)",
    fontsize=12, fontweight="bold"
)

for fila, region in enumerate(REGIONES):
    vt = val_topo.get(region)
    if vt is None:
        continue

    for col, (ciclos, titulo, color_pts) in enumerate([
        (vt["ciclos_orig"],  f"ANTES — {vt['n_orig']} huecos H₁",  "#d6604d"),
        (vt["ciclos_nuevo"], f"DESPUÉS — {vt['n_nuevo']} huecos H₁", "#1a9641"),
    ]):
        ax = axes[fila][col]

        births = np.array([c["birth"] for c in ciclos])
        deaths = np.array([c["death"] for c in ciclos])
        pers   = deaths - births

        # Diagonal
        max_val = max(deaths.max(), 2000) if len(deaths) > 0 else 2000
        ax.plot([0, max_val], [0, max_val], "k--", linewidth=0.8, alpha=0.4, label="diagonal")

        # Puntos coloreados por persistencia
        if len(births) > 0:
            sc = ax.scatter(births, deaths, c=pers, cmap="YlOrRd",
                            s=np.clip(pers / 5, 20, 300),
                            alpha=0.8, edgecolors="white", linewidths=0.4, zorder=3)
            plt.colorbar(sc, ax=ax, label="Persistencia (m)", shrink=0.8)

        # Zona de huecos significativos (pers ≥ 200m)
        ax.axhline(200, color="#4393c3", linestyle=":", linewidth=1.2, alpha=0.7,
                   label="Umbral 200m")

        ax.set_xlabel("Birth (metros)", fontsize=9)
        ax.set_ylabel("Death (metros)", fontsize=9)
        ax.set_title(f"{region} — {titulo}", fontsize=10, fontweight="bold",
                     color=COLORES[region] if col == 0 else "#1a9641")
        ax.legend(fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)

    # Anotar delta
    delta = vt["delta"]
    if delta > 0:
        axes[fila][1].text(0.05, 0.95,
                           f"−{delta} hueco{'s' if delta > 1 else ''} eliminado{'s' if delta > 1 else ''}",
                           transform=axes[fila][1].transAxes,
                           fontsize=11, color="#1a9641", fontweight="bold", va="top")
    else:
        axes[fila][1].text(0.05, 0.95,
                           "Sin cambio en H₁\n(hueco persiste topológicamente)",
                           transform=axes[fila][1].transAxes,
                           fontsize=10, color="#e08214", va="top")

plt.tight_layout()
ruta = config.FIGURAS_DIR / "validacion_persistencia.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 4. Validación OSMnx — Tiempo real a la clínica nueva propuesta

# %%
print("\n" + "="*65)
print("VALIDACIÓN CON RED OSM — TOP 3 HUECOS MÁS URGENTES POR CIUDAD")
print("="*65)

val_osm = {}

for region in REGIONES:
    sol = soluciones[region]
    if sol is None:
        continue

    df_hue = dfs[region]
    lat_n, lon_n = sol["lat"], sol["lon"]

    # Top 3 huecos por score compuesto para validar
    top_huecos = df_hue.head(TOP_VAL)

    print(f"\n[{region}]  Clínica propuesta: ({lat_n:.5f}, {lon_n:.5f})")
    val_osm[region] = []

    for _, row in top_huecos.iterrows():
        hueco_id = int(row["hueco_id"])
        lat_h, lon_h = row["lat"], row["lon"]
        print(f"\n  Hueco #{hueco_id} (score={row['score']:.3f}) — descargando OSM...")

        try:
            G_proj = geo_network.descargar_red_punto(lat_h, lon_h, radio_m=RADIO_OSM_M)
            crs_g  = G_proj.graph["crs"]
            tr_a_g = Transformer.from_crs("EPSG:4326", crs_g, always_xy=True)

            # Nodo del paciente (centroide del hueco)
            xh, yh = tr_a_g.transform(lon_h, lat_h)
            nodo_h = ox.distance.nearest_nodes(G_proj, xh, yh)

            # Tiempo ANTES: a la clínica existente más cercana
            geo_network._agregar_tiempos(G_proj)
            df_clin_area = salud[region]
            acceso_antes = geo_network.accesibilidad_desde_punto(
                G_proj, lat_h, lon_h, df_clin_area, top_n=20
            )
            t_antes = acceso_antes.get("tiempo_min")

            # Tiempo DESPUÉS: a la clínica nueva propuesta
            xn, yn   = tr_a_g.transform(lon_n, lat_n)
            nodo_n   = ox.distance.nearest_nodes(G_proj, xn, yn)
            t_despues = None
            try:
                ruta_osm  = nx.shortest_path(G_proj, nodo_h, nodo_n, weight="time")
                t_despues = nx.path_weight(G_proj, ruta_osm, weight="time")
            except nx.NetworkXNoPath:
                t_despues = None

            # Isócrona desde el hueco hacia la nueva clínica
            iso_nueva = geo_network.isocrona_desde_nodo(G_proj, nodo_h, TIEMPO_LIM)

            print(f"    Tiempo ANTES (clínica existente):  "
                  f"{t_antes:.1f} min" if t_antes else "    Sin ruta ANTES")
            if t_despues is not None:
                mejora = (t_antes or 999) - t_despues
                print(f"    Tiempo DESPUÉS (clínica nueva):    {t_despues:.1f} min  "
                      f"({'✓ dentro' if t_despues <= TIEMPO_LIM else '✗ fuera'} del límite)  "
                      f"[mejora: {mejora:+.1f} min]")
            else:
                print(f"    Sin ruta hacia la clínica nueva en red OSM")

            val_osm[region].append({
                "hueco_id": hueco_id,
                "lat_h": lat_h, "lon_h": lon_h,
                "G_proj": G_proj,
                "xh": xh, "yh": yh,
                "xn": xn, "yn": yn,
                "t_antes": t_antes,
                "t_despues": t_despues,
                "iso_nueva": iso_nueva,
                "score": row["score"],
                "psin": int(row["pob_sin_salud"]),
                "pers_m": row["pers_m"],
            })
        except Exception as e:
            print(f"    Error OSM: {e}")
            val_osm[region].append(None)

# %% [markdown]
# ## 5. Mapas de impacto antes/después con red OSM

# %%
def plot_antes_despues(ax_antes, ax_despues, datos, lat_n, lon_n):
    """Par de mapas: clínica actual vs clínica nueva propuesta."""
    if datos is None:
        for ax in [ax_antes, ax_despues]:
            ax.text(0.5, 0.5, "Sin datos OSM", ha="center", va="center",
                    transform=ax.transAxes)
            ax.set_axis_off()
        return

    G     = datos["G_proj"]
    xh, yh, xn, yn = datos["xh"], datos["yh"], datos["xn"], datos["yn"]
    t_ant  = datos["t_antes"]
    t_des  = datos["t_despues"]
    iso    = datos["iso_nueva"]

    for ax, (t_ref, titulo_ref, color_ref, xc, yc) in zip(
        [ax_antes, ax_despues],
        [
            (t_ant, "ANTES\n(clínica existente más cercana)", "#d6604d", None, None),
            (t_des, "DESPUÉS\n(clínica nueva propuesta)", "#1a9641", xn, yn),
        ]
    ):
        ax.set_facecolor("#f2f2f2")

        # Red de calles
        try:
            edges = ox.graph_to_gdfs(G, nodes=False)
            edges.plot(ax=ax, color="#c8c8c8", linewidth=0.5, alpha=0.9, zorder=1)
        except Exception:
            pass

        # Isócrona de 15 min (en el DESPUÉS)
        if iso is not None and xc is not None:
            gpd.GeoSeries([iso]).plot(ax=ax, color="#4393c3", alpha=0.20,
                                      edgecolor="#2166ac", linewidth=1.5, zorder=2)

        # Paciente (centroide del hueco)
        ax.plot(xh, yh, "o", color="#e6550d", markersize=12, zorder=5,
                markeredgecolor="white", markeredgewidth=1.5)
        ax.annotate("Paciente", xy=(xh, yh), xytext=(xh, yh - 200),
                    fontsize=6.5, ha="center", color="#e6550d", fontweight="bold")

        # Clínica nueva (en el mapa DESPUÉS)
        if xc is not None:
            ax.plot(xc, yc, "*", color="#FFD700", markersize=16, zorder=7,
                    markeredgecolor="#333", markeredgewidth=1.2)
            ax.annotate("Clínica\nnueva ★", xy=(xc, yc), xytext=(xc, yc + 250),
                        fontsize=6.5, ha="center", color="#333", fontweight="bold")

        # Tiempo
        if t_ref is not None:
            color_t = "#1a9641" if t_ref <= TIEMPO_LIM else "#b2182b"
            ax.text(0.5, 0.97, f"{t_ref:.0f} min caminando",
                    transform=ax.transAxes, ha="center", va="top",
                    fontsize=11, fontweight="bold", color=color_t,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                              edgecolor=color_t, alpha=0.95))
        else:
            ax.text(0.5, 0.97, "Sin ruta", transform=ax.transAxes,
                    ha="center", va="top", fontsize=10, color="#888")

        hueco_id = datos["hueco_id"]
        ax.set_title(
            f"{titulo_ref}  —  Hueco #{hueco_id}\n"
            f"Score: {datos['score']:.3f}  |  {datos['psin']:,} sin seguro  |  "
            f"Pers. {datos['pers_m']:.0f}m",
            fontsize=8.5, fontweight="bold"
        )
        ax.set_axis_off()


leyenda = [
    mpatches.Patch(color="#c8c8c8", label="Red de calles (OSM)"),
    mpatches.Patch(color="#4393c3", alpha=0.25, label="Zona 15 min desde paciente"),
    mlines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#e6550d",
                  markersize=10, label="Paciente (centroide del hueco)"),
    mlines.Line2D([0], [0], marker="*", color="w", markerfacecolor="#FFD700",
                  markersize=12, label="Clínica nueva propuesta"),
]

for region in REGIONES:
    datos_val = val_osm.get(region, [])
    n         = len([d for d in datos_val if d is not None])
    if n == 0:
        continue

    fig, axes = plt.subplots(n, 2, figsize=(14, 5.5 * n))
    fig.suptitle(
        f"{region} — Impacto de la clínica nueva: antes vs después\n"
        "Top 3 huecos más urgentes (score compuesto)",
        fontsize=12, fontweight="bold"
    )

    if n == 1:
        axes = axes[np.newaxis, :]

    sol = soluciones[region]
    lat_n, lon_n = sol["lat"], sol["lon"]

    fila_real = 0
    for datos in datos_val:
        if datos is None:
            continue
        plot_antes_despues(axes[fila_real][0], axes[fila_real][1],
                           datos, lat_n, lon_n)
        fila_real += 1

    fig.legend(handles=leyenda, loc="lower center", ncol=4,
               fontsize=9, bbox_to_anchor=(0.5, 0.005), framealpha=0.95)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    ruta = config.FIGURAS_DIR / f"validacion_osm_{region}.png"
    plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
    plt.show()
    plt.close(fig)
    print(f"✓ {ruta}")

# %% [markdown]
# ## 6. Resumen de validaciones

# %%
print("\n" + "="*70)
print("RESUMEN FINAL — VALIDACIÓN FASE 3")
print("="*70)

for region in REGIONES:
    vt  = val_topo.get(region, {})
    vo  = val_osm.get(region, [])
    sol = soluciones.get(region, {})

    if not sol:
        continue

    print(f"\n  [{region}]")
    print(f"  Clínica propuesta (K=1, escenario compuesto):")
    print(f"    Coordenadas: ({sol['lat']:.5f}, {sol['lon']:.5f})")
    print(f"    Huecos cubiertos (KDTree): {int(sol['huecos_cubiertos'])}")
    print(f"    Sin seguro cubiertos: {int(sol['psin_cubierta']):,}")

    if vt:
        print(f"\n  Validación topológica:")
        print(f"    Huecos H₁ antes: {vt['n_orig']}  →  después: {vt['n_nuevo']}")
        print(f"    Huecos eliminados: {vt['delta']}  "
              f"({'✓ Validado' if vt['delta'] > 0 else '— Persiste topológicamente'})")

    print(f"\n  Validación OSMnx (top {TOP_VAL} huecos):")
    for d in vo:
        if d is None:
            continue
        t_a  = d["t_antes"]
        t_d  = d["t_despues"]
        mejora = (t_a or 99) - (t_d or 99) if t_d else None
        print(f"    Hueco #{d['hueco_id']:3d}:  "
              f"antes={f'{t_a:.1f}min' if t_a else 'N/A':>8}  →  "
              f"después={f'{t_d:.1f}min' if t_d else 'sin ruta':>9}  "
              f"[{f'mejora: {mejora:+.1f}min' if mejora else '—'}]")

print("\nArchivos generados:")
print("  validacion_persistencia.png  — diagramas H₁ antes y después")
print("  validacion_osm_CDMX.png      — mapas antes/después con red OSM")
print("  validacion_osm_EDOMEX.png")
