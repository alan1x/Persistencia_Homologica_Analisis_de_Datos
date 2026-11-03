# %% [markdown]
# # 22b — ¿De dónde sale el +66% de huecos de Laguerre?
#
# El reporte lo atribuye a la heterogeneidad: hospitales grandes junto a consultorios
# chicos. Si eso fuera cierto, dar a todas las clínicas **el mismo peso** no debería
# producir el aumento, porque con pesos iguales la geometría es la del Alpha clásico.
#
# Con peso uniforme r², la filtración solo se desplaza: α' = α − r². Los pares son
# los mismos, pero la persistencia medida como √α'_muerte − √α'_nac crece al acercarse
# a cero. Es un efecto de la escala, no de los hospitales.

# %%
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from lib import config, huecos, tda, viz_eval as ve

ve.aplicar()
SALIDA = config.OUTPUTS_DIR / "auditoria"
SALIDA.mkdir(exist_ok=True)
RADIOS = [0, 25, 50, 75, 100, 125, 150, 175, 200, 250]
COLOR = {"CDMX": ve.AZUL, "EDOMEX": ve.NARANJA}

# %%
filas, resumen = [], {}
for r in ["CDMX", "EDOMEX"]:
    sal = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{r}.parquet")
    P = sal[["x", "y"]].to_numpy()
    for rad in RADIOS:
        w = np.full(len(P), float(rad) ** 2)
        h = huecos.extraer_huecos(huecos.complejo(P, w if rad else None), P, 200, w if rad else None)
        filas.append({"region": r, "radio": rad, "huecos": len(h)})
        print(r, rad, len(h), flush=True)

    w = tda.pesos_desde_per_ocu(sal)
    r_med = float(np.sqrt(w).mean())
    pon = huecos.extraer_huecos(huecos.complejo(P, w), P, 200, w)
    wu = np.full(len(P), r_med ** 2)
    uni = huecos.extraer_huecos(huecos.complejo(P, wu), P, 200, wu)
    d, _ = cKDTree(uni[["bx", "by"]].values).query(pon[["bx", "by"]].values)
    # Pesos barajados: misma distribución de tamaños, sin relación con el lugar
    rng = np.random.default_rng(0)
    bar = []
    for _ in range(10):
        wb = rng.permutation(w)
        bar.append(len(huecos.extraer_huecos(huecos.complejo(P, wb), P, 200, wb)))
    resumen[r] = {
        "laguerre": len(pon), "uniforme_mismo_radio_medio": len(uni), "radio_medio": round(r_med, 1),
        "laguerre_en_uniforme_a_500m": int((d < 500).sum()),
        "pesos_barajados_media": float(np.mean(bar)), "pesos_barajados_min": int(min(bar)),
        "pesos_barajados_max": int(max(bar)),
    }
df = pd.DataFrame(filas)
df.to_csv(SALIDA / "laguerre_radio_uniforme.csv", index=False)
(SALIDA / "laguerre_artefacto.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
print(json.dumps(resumen, indent=2))

# %%
fig, ax = plt.subplots(figsize=(9, 5.2))
for r in ["CDMX", "EDOMEX"]:
    s = df[df.region == r]
    ax.plot(s.radio, s.huecos, color=COLOR[r], lw=2, marker="o", ms=5, label=r)
    ax.scatter([resumen[r]["radio_medio"]], [resumen[r]["laguerre"]], s=110, marker="D",
               color=ve.FONDO, edgecolor=COLOR[r], lw=2, zorder=5)
    ax.annotate(f"Laguerre real: {resumen[r]['laguerre']}",
                (resumen[r]["radio_medio"], resumen[r]["laguerre"]),
                textcoords="offset points", xytext=(-10, 16), ha="right", color=ve.TEXTO_2, fontsize=10)
ax.set_xlabel("Radio igual para todas las clínicas (m)")
ax.set_ylabel("Huecos con persistencia ≥ 200 m")
ax.set_ylim(0)
ax.legend(loc="center right")
ve.titulo(fig, "Sin hospitales de por medio, el conteo sube igual",
          "Con el mismo peso para todos, los huecos aumentan solo por el cambio de escala. "
          "El rombo es el Laguerre real.")
fig.tight_layout(rect=(0, 0, 1, 0.91))
ve.guardar(fig, config.FIGURAS_DIR / "auditoria_laguerre_artefacto.png")
