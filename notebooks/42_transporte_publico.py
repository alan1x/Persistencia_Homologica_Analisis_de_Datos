# %% [markdown]
# # 42 — ¿El transporte público cambia el mapa del acceso? (F8.4 de `PLAN_ACCESO.md`)
#
# Hasta aquí el acceso se mide a pie: 30 minutos por calle (2,250 m a 4.5 km/h). Aquí se
# agrega el transporte público con r5py y el GTFS de la CDMX, y se mide cuánto cambian la gente
# con acceso bajo y las islas de F4.
#
# ## Datos, fijados antes de correr
#
# - **GTFS:** la copia más reciente de MobilityDatabase (mdb-1830, 2026-03-09; archivos del
#   2026-02-16) del GTFS de SEMOVI. El portal `datos.cdmx.gob.mx` no respondió desde aquí.
#   Incluye Metro, Metrobús, Tren Ligero, Trolebús, Cablebús, RTP, corredores concesionados,
#   Suburbano, Tren Interurbano y Pumabús. **Todos los calendarios vencen el 2025-12-31**
#   (salvo uno), y el 99.8% de los viajes van por frecuencias. Por eso se usa un martes de
#   2025 dentro de su vigencia. No trae Mexibús, Mexicable ni combis: en EDOMEX el transporte
#   se queda corto, y eso se reporta como límite.
# - **Calles:** el PBF de México recortado a la caja de las celdas, las unidades y las paradas,
#   más 3 km. r5 arma su propia red caminable con OSM, que no es idéntica a la del 33. Por eso
#   hay un **control a pie con r5**: el efecto del transporte se mide contra ese control, no
#   contra el 33.
#
# ## Modelo, fijado antes de correr
#
# - Salida: martes 2025-10-14, entre 08:00 y 09:00 (ventana de 60 min, mediana del tiempo).
# - Tope de 30 minutos puerta a puerta; caminata a 4.5 km/h, igual que el 33; hasta 8 viajes.
# - El tiempo se pasa a distancia equivalente (t × 75 m/min) y se usa el mismo peso gaussiano
#   del 33 con tope de 2,250 m (= 30 min). Misma oferta CLUES (médicos, unidades en dominio) y
#   mismo promedio metropolitano (capacidad total / demanda total, sin cambiar).
# - **Dirección:** se calcula **de cada unidad a todas las celdas** (907 orígenes, no 322 mil),
#   porque es la única forma barata de tener la matriz completa. El paciente viaja al revés, así
#   que se mide la asimetría con una muestra de 2,000 celdas con gente (semilla 0) como origen
#   hacia todas las unidades, a la misma hora.
#
# ## Medidas y criterio
#
# - Gente con acceso 0 y con acceso bajo (f < 0.5), en total y por estado, en tres versiones:
#   calle del 33, a pie con r5 (control) y transporte con r5.
# - Gente con prioridad (acceso bajo y marginación alta o muy alta) que sale de acceso bajo.
# - Cercanía al GTFS: gente sin seguro a ≤ 500 m en recta de una parada del catálogo, por estado.
# - Asimetría: diferencia mediana de tiempo entre ida y vuelta en los pares que ambas
#   direcciones alcanzan, y pares que solo una dirección alcanza.
# - **Criterio (el mismo del 35 y el 40):** las islas estables por calle sobreviven si su
#   cuenca se empareja uno a uno (Jaccard ≥ 0.5) con una isla del acceso con transporte. Si
#   sobrevive ≥ 80%, **la geografía de F4 es robusta al transporte** y el acceso a pie sigue como
#   versión principal. Si no, se reportan las dos. La cifra se lee junto a la del control a pie
#   con r5: si el control ya pierde islas, una parte del cambio es de la red y no del
#   transporte.
#
# *Ajustes tras la crítica de Codex, antes de correr:*
# - el recorte del PBF lee nodos y vías (si no, pyosmium no llena las ubicaciones) y se
#   escribe a un archivo temporal;
# - celdas y unidades llevan ids disjuntos (r5py pone 0 min cuando `from_id == to_id`);
# - bloques de 20 unidades guardados por separado, y cachés con huella de insumos y parámetros;
# - asimetría sobre todos los pares posibles y transiciones de acceso bajo ponderadas por gente;
# - islas emparejadas también entre control y transporte, isla por isla;
# - acceso 0 por estado.
#
# ## Límites que se aceptan
#
# - La matriz principal va de la unidad a la celda; el paciente viaja al revés. Es una
#   **aproximación**: la muestra mide cuánto cambia, pero solo en el segundo paso del E2SFCA.
# - r5 resume 60 salidas (una por minuto) con sorteos de horarios por frecuencias; la mediana
#   tiene ruido de simulación que aquí no se mide. Los tiempos van en minutos enteros.
# - El recorte conserva vías con algún vértice dentro de la caja (más 3 km) y descarta las
#   relaciones; a pie no hay restricciones de giro que perder.
#
# Prueba corta, sin guardar nada: `PRUEBA_R5=4` corre solo 4 unidades en cada modo.

# %%
import hashlib
import json
import os
import sys
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# r5py necesita Java 21+ y arranca la JVM al importarse: se fija antes.
_JDK = Path(os.environ.get("JDK_R5", r"C:\Program Files\Eclipse Adoptium\jdk-25.0.1.8-hotspot"))
if _JDK.exists():
    os.environ["JAVA_HOME"] = str(_JDK)
sys.argv += ["--max-memory", os.environ.get("R5_MEMORIA", "8G")]

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import osmium
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

from lib import acceso, config, f4, topo_rejilla as tr, viz_eval as ve

ve.aplicar()
T0 = time.time()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
DATOS = _ROOT / "Datos"
GTFS = DATOS / "GTFS" / "cdmx_gtfs_20260309.zip"
PBF_MX = DATOS / "OSM" / "mexico-latest.osm.pbf"
PBF_ZONA = DATOS / "OSM" / "zmvm_r5.osm.pbf"
LIM = 30 * 4500 / 60  # 2,250 m = 30 min a 4.5 km/h
M_POR_MIN = 4500 / 60
SALIDA_T = datetime(2025, 10, 14, 8, 0)
VENTANA = timedelta(minutes=60)
TOPE = timedelta(minutes=30)
BLOQUE = int(os.environ.get("BLOQUE_R5", "20"))  # unidades por llamada (20 × 322 mil filas densas)
OFF = 10_000_000  # ids de unidades, disjuntos de los de celdas
N_MUESTRA, SEMILLA = 2000, 0
PRUEBA = int(os.environ.get("PRUEBA_R5", "0"))  # > 0: solo esas unidades, sin guardar nada


def reloj(msg):
    print(f"[{(time.time() - T0) / 60:5.1f} min] {msg}", flush=True)


c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
calle = pd.read_parquet(INT / "acceso_calle.parquet")
assert np.allclose(calle[["x", "y"]].to_numpy(), c[["x", "y"]].to_numpy(), atol=0.01)
o = acceso.oferta()
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
FXY, CAP = o[["x", "y"]].to_numpy(), o["cap"].to_numpy(float)
N, M = len(c), len(o)
PROM = CAP.sum() / PSIN.sum()
F1 = calle["acceso_rel_calle"].to_numpy()
REG = c["region"].to_numpy()
PRIO_MARG = c["alta_marg"].to_numpy(bool)
print(f"celdas {N:,}, unidades {M:,}, fuente {acceso.fuente_oferta()}")

a_geo = Transformer.from_crs(config.CRS_METROS, config.CRS_GEO, always_xy=True)
LON, LAT = a_geo.transform(XY[:, 0], XY[:, 1])
FLON, FLAT = a_geo.transform(FXY[:, 0], FXY[:, 1])


# Limpieza del GTFS (agregada después de la primera prueba, 2026-11-23: r5 lo rechazaba).
# Solo formato: `exact_times` y `direction_id` vienen como "0.0"/"1.0", y una ruta apunta a la
# agencia SEMOVI, que no está en agency.txt. Se escribe una copia; el original no se toca.
GTFS_LIMPIO = GTFS.with_name(GTFS.stem + "_limpio.zip")
if not GTFS_LIMPIO.exists():
    with zipfile.ZipFile(GTFS) as zin, zipfile.ZipFile(GTFS_LIMPIO, "w", zipfile.ZIP_DEFLATED) as zout:
        for nom in zin.namelist():
            df = pd.read_csv(zin.open(nom), dtype=str, keep_default_na=False)
            for col in ("exact_times", "direction_id"):
                if col in df:
                    df[col] = df[col].str.replace(r"\.0$", "", regex=True)
            if nom == "agency.txt" and "SEMOVI" not in set(df["agency_id"]):
                df = pd.concat([df, pd.DataFrame([{"agency_id": "SEMOVI", "agency_name": "SEMOVI",
                                                   "agency_url": "https://www.semovi.cdmx.gob.mx/",
                                                   "agency_timezone": "America/Mexico_City", "agency_lang": "ES"}])])
            zout.writestr(nom, df.to_csv(index=False))
GTFS = GTFS_LIMPIO

paradas = pd.read_csv(zipfile.ZipFile(GTFS).open("stops.txt"), dtype={"stop_id": str})
a_utm = Transformer.from_crs(config.CRS_GEO, config.CRS_METROS, always_xy=True)
PXY = np.column_stack(a_utm.transform(paradas["stop_lon"].to_numpy(float), paradas["stop_lat"].to_numpy(float)))

# %% [markdown]
# ## PBF de la zona (se recorta una vez y se guarda)

# %%
if not PBF_ZONA.exists():
    tmp, idx = PBF_ZONA.with_suffix(".tmp.pbf"), PBF_ZONA.with_suffix(".idx")
    marg = 3000 / 111_000  # ~3 km en grados
    lon_all = np.r_[LON, FLON, paradas["stop_lon"].to_numpy(float)]
    lat_all = np.r_[LAT, FLAT, paradas["stop_lat"].to_numpy(float)]
    O_, S_, E_, N_ = lon_all.min() - marg, lat_all.min() - marg, lon_all.max() + marg, lat_all.max() + marg
    reloj(f"recortando PBF a ({O_:.3f}, {S_:.3f}, {E_:.3f}, {N_:.3f})")
    n_vias = 0
    with osmium.BackReferenceWriter(str(tmp), ref_src=str(PBF_MX), overwrite=True, remove_tags=False) as w:
        fp = (osmium.FileProcessor(str(PBF_MX), osmium.osm.NODE | osmium.osm.WAY)
              .with_locations(osmium.index.create_map(f"sparse_file_array,{idx}"))
              .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
              .with_filter(osmium.filter.KeyFilter("highway", "railway", "public_transport")))
        for obj in fp:
            for n in obj.nodes:
                if n.location.valid() and O_ <= n.location.lon <= E_ and S_ <= n.location.lat <= N_:
                    w.add_way(obj)
                    n_vias += 1
                    break
        del fp, obj  # suelta el índice en disco (Windows no deja borrarlo abierto)
    import gc

    gc.collect()
    try:
        idx.unlink(missing_ok=True)
    except PermissionError:
        print(f"aviso: no se pudo borrar {idx.name}; bórralo a mano")
    assert n_vias > 100_000, f"recorte sospechoso: {n_vias} vías"
    tmp.replace(PBF_ZONA)
    reloj(f"PBF de la zona: {n_vias:,} vías, {PBF_ZONA.stat().st_size / 1e6:.0f} MB")

import jpype  # noqa: E402
import r5py  # noqa: E402  (después de fijar JAVA_HOME y la memoria)

assert jpype.getJVMVersion()[0] >= 21, f"r5py necesita Java 21+, arrancó {jpype.getJVMVersion()}"
red = r5py.TransportNetwork(str(PBF_ZONA), [str(GTFS)])
reloj("red de r5 lista")

celdas = gpd.GeoDataFrame({"id": np.arange(N)}, geometry=gpd.points_from_xy(LON, LAT), crs=config.CRS_GEO)
unidades = gpd.GeoDataFrame({"id": OFF + np.arange(M)}, geometry=gpd.points_from_xy(FLON, FLAT), crs=config.CRS_GEO)
COMUN = dict(departure=SALIDA_T, departure_time_window=VENTANA, max_time=TOPE, speed_walking=4.5,
             percentiles=[50], max_public_transport_rides=8)
HUELLA = hashlib.sha1(repr((GTFS.name, GTFS.stat().st_size, PBF_ZONA.stat().st_size, N, M, float(XY.sum()),
                            float(FXY.sum()), float(CAP.sum()), sorted((k, str(v)) for k, v in COMUN.items()),
                            N_MUESTRA, SEMILLA)).encode()).hexdigest()[:10]
CACHE = INT / f"r5_{HUELLA}"
CACHE.mkdir(exist_ok=True)
print("huella de la corrida:", HUELLA)


def a_indice(ids):
    """Id de r5 → índice denso (celdas < OFF ≤ unidades)."""
    ids = ids.to_numpy(np.int64)
    return np.where(ids >= OFF, ids - OFF, ids).astype(np.int32)


def tiempos(origenes, destinos, modos, nombre):
    """Matriz origen → destino por bloques; solo pares < 30 min (peso > 0). Cada bloque se guarda."""
    ruta = CACHE / f"{nombre}.parquet"
    if ruta.exists() and not PRUEBA:
        return pd.read_parquet(ruta)
    n_or = min(PRUEBA, len(origenes)) if PRUEBA else len(origenes)
    partes = []
    for k in range(0, n_or, BLOQUE):
        rb = CACHE / f"{nombre}_{k:06d}.parquet"
        if rb.exists() and not PRUEBA:
            partes.append(pd.read_parquet(rb))
            continue
        t0 = time.time()
        ttm = r5py.TravelTimeMatrix(red, origins=origenes.iloc[k:min(k + BLOQUE, n_or)], destinations=destinos,
                                    transport_modes=modos, **COMUN)
        t_ = pd.DataFrame(ttm)[["from_id", "to_id", "travel_time"]].dropna()
        del ttm
        t_ = t_[t_["travel_time"] < TOPE.total_seconds() / 60]
        t_ = pd.DataFrame({"o": a_indice(t_["from_id"]), "d": a_indice(t_["to_id"]),
                           "t": t_["travel_time"].to_numpy(np.float32)})
        if not PRUEBA:
            t_.to_parquet(rb)
        partes.append(t_)
        reloj(f"  {nombre}: {min(k + BLOQUE, n_or)}/{n_or} orígenes ({time.time() - t0:.0f} s el bloque)")
    t = pd.concat(partes, ignore_index=True)
    if not PRUEBA:
        t.to_parquet(ruta)
        for rb in CACHE.glob(f"{nombre}_*.parquet"):
            rb.unlink()
    return t


def acceso_de(t):
    """E2SFCA con pares unidad → celda (o = unidad, d = celda)."""
    j, i = t["o"].to_numpy(np.int64), t["d"].to_numpy(np.int64)
    A, _ = acceso.e2sfca_pares(i, j, acceso.peso(t["t"].to_numpy(float) * M_POR_MIN, LIM), PSIN, CAP, N)
    return A / PROM


sfx = acceso.sufijo_oferta()
PIE = [r5py.TransportMode.WALK]
TP = [r5py.TransportMode.TRANSIT, r5py.TransportMode.WALK]
if PRUEBA:
    for nom, modos in (("pie", PIE), ("transporte", TP)):
        t_ = tiempos(unidades, celdas, modos, nom)
        print(f"prueba {nom}: {len(t_):,} pares < 30 min desde {PRUEBA} unidades; "
              f"tiempo mediano {t_['t'].median():.0f} min")
    raise SystemExit("prueba terminada (no se guardó nada)")
t_pie = tiempos(unidades, celdas, PIE, "pie")
reloj(f"a pie con r5: {len(t_pie):,} pares")
F_PIE = acceso_de(t_pie)
n_pie = len(t_pie)
del t_pie
t_tp = tiempos(unidades, celdas, TP, "transporte")
reloj(f"transporte con r5: {len(t_tp):,} pares")
F_TP = acceso_de(t_tp)

# %% [markdown]
# ## Asimetría: celdas → unidades en una muestra

# %%
rng = np.random.default_rng(SEMILLA)
muestra = np.sort(rng.choice(np.flatnonzero(PSIN > 0), N_MUESTRA, replace=False))
t_ida = tiempos(celdas.iloc[muestra], unidades, TP, "transporte_ida")
vuelta = t_tp[np.isin(t_tp["d"], muestra)].rename(columns={"o": "j", "d": "i", "t": "t_vuelta"})
ida = t_ida.rename(columns={"o": "i", "d": "j", "t": "t_ida"})
par = ida.merge(vuelta, on=["i", "j"], how="outer")
ambos = par.dropna()
posibles = N_MUESTRA * M
dif = ambos["t_ida"] - ambos["t_vuelta"]
asim = {
    "pares_posibles": int(posibles),
    "ambas_direcciones_pct": float(len(ambos) / posibles * 100),
    "solo_ida_pct": float(par["t_vuelta"].isna().sum() / posibles * 100),
    "solo_vuelta_pct": float(par["t_ida"].isna().sum() / posibles * 100),
    "ninguna_pct": float((posibles - len(par)) / posibles * 100),
    "solo_un_sentido_de_los_alcanzables_pct": float((len(par) - len(ambos)) / max(len(par), 1) * 100),
    "dif_mediana_min": float(dif.median()),
    "dif_abs_mediana_min": float(dif.abs().median()),
    "dif_abs_p90_min": float(dif.abs().quantile(0.9)),
}
# Acceso de las celdas de la muestra con los tiempos de ida. La demanda de cada unidad (paso 1)
# sigue siendo la de la matriz completa unidad → celda; solo cambia el paso 2.
j_, i_ = t_tp["o"].to_numpy(np.int64), t_tp["d"].to_numpy(np.int64)
w_ = acceso.peso(t_tp["t"].to_numpy(float) * M_POR_MIN, LIM)
dem_j = np.bincount(j_, weights=PSIN[i_] * w_, minlength=M)
R = np.divide(CAP, dem_j, out=np.zeros(M), where=dem_j > 0)
del j_, i_, w_
wi = acceso.peso(t_ida["t"].to_numpy(float) * M_POR_MIN, LIM)
A_ida = np.bincount(t_ida["o"].to_numpy(np.int64), weights=R[t_ida["d"].to_numpy(np.int64)] * wi, minlength=N)
F_ida, F_vu, P_m = A_ida[muestra] / PROM, F_TP[muestra], PSIN[muestra]
asim["muestra_bajo_igual_pct_gente"] = float(np.average((F_ida < 0.5) == (F_vu < 0.5), weights=P_m) * 100)
asim["muestra_bajo_solo_ida_pct_gente"] = float(P_m[(F_ida < 0.5) & (F_vu >= 0.5)].sum() / P_m.sum() * 100)
asim["muestra_bajo_solo_vuelta_pct_gente"] = float(P_m[(F_ida >= 0.5) & (F_vu < 0.5)].sum() / P_m.sum() * 100)
asim["nota"] = "solo cambia el paso 2 del E2SFCA; la demanda de cada unidad sigue siendo la de unidad -> celda"
print(json.dumps(asim, indent=1))

# %% [markdown]
# ## Gente con acceso bajo: calle del 33, a pie con r5 y con transporte

# %%
cerca_parada = np.isfinite(cKDTree(PXY).query(XY, distance_upper_bound=500)[0])


def resumen(F):
    out = {"psin_cero": float(PSIN[F == 0].sum()), "psin_bajo": float(PSIN[F < 0.5].sum()),
           "psin_prioridad": float(PSIN[(F < 0.5) & PRIO_MARG].sum())}
    for r in ("CDMX", "EDOMEX"):
        k = REG == r
        out[f"psin_cero_{r}"] = float(PSIN[k & (F == 0)].sum())
        out[f"psin_bajo_{r}"] = float(PSIN[k & (F < 0.5)].sum())
        out[f"pct_bajo_{r}"] = float(PSIN[k & (F < 0.5)].sum() / PSIN[k].sum() * 100)
    return out


versiones = {"calle_33": resumen(F1), "pie_r5": resumen(F_PIE), "transporte_r5": resumen(F_TP)}
print(pd.DataFrame(versiones).round(1).to_string())
cobertura = {r: float(PSIN[(REG == r) & cerca_parada].sum() / PSIN[REG == r].sum() * 100) for r in ("CDMX", "EDOMEX")}
print("gente a ≤ 500 m de una parada del catálogo del GTFS (%):", cobertura)
sale = (F_PIE < 0.5) & (F_TP >= 0.5)
entra = (F_PIE >= 0.5) & (F_TP < 0.5)  # la unidad reparte entre más gente: f puede bajar
control = {
    "corr_spearman_pie_r5_vs_33": float(pd.Series(F_PIE).corr(pd.Series(F1), method="spearman")),
    "bajo_igual_pie_r5_vs_33_pct_gente": float(np.average((F_PIE < 0.5) == (F1 < 0.5), weights=PSIN) * 100),
}
cambio = {
    "psin_sale_de_bajo": float(PSIN[sale].sum()),
    "psin_entra_a_bajo": float(PSIN[entra].sum()),
    "psin_prioridad_sale": float(PSIN[sale & PRIO_MARG].sum()),
    **{f"psin_sale_{r}": float(PSIN[sale & (REG == r)].sum()) for r in ("CDMX", "EDOMEX")},
    **{f"psin_entra_{r}": float(PSIN[entra & (REG == r)].sum()) for r in ("CDMX", "EDOMEX")},
}
print(json.dumps({"control": control, "cambio": cambio}, indent=1))

# %% [markdown]
# ## Islas: ¿sobreviven las estables por calle?

# %%
rej = tr.Rejilla(c["x"], c["y"], acceso.PASO)
isl = pd.read_parquet(INT / "islas_acceso_calle.parquet")
est = isl[isl["estable"] & (isl["tipo"] != "resto de región")].reset_index(drop=True)
_, _, CUEN1 = rej.h0(F1, cuencas=True)
cer = (est["b"] == 0).to_numpy()


def pct(v):
    return float(v.mean() * 100) if len(v) else None


def islas_de(F):
    p2, _, cu2 = rej.h0(F, cuencas=True)
    i2 = tr.islas(p2)
    return i2, f4.lista_cuencas(i2, cu2)


def emparejar(cu_a, cu_b):
    """Para cada isla de a: índice de su pareja en b (Jaccard ≥ 0.5, uno a uno) o -1."""
    Jm, fil, col, jres = tr.jaccard_emparejado(cu_a, cu_b, N, umbral=f4.J_MIN)
    par_ = np.full(len(cu_a), -1)
    ok = Jm[fil, col] >= f4.J_MIN
    par_[fil[ok]] = col[ok]
    return par_, float(jres)


CU_EST = f4.lista_cuencas(est, CUEN1)
i_pie, cu_pie = islas_de(F_PIE)
i_tp, cu_tp = islas_de(F_TP)
par_pie, j_pie = emparejar(CU_EST, cu_pie)
par_tp, j_tp = emparejar(CU_EST, cu_tp)
par_pt, _ = emparejar(cu_pie, cu_tp)
v_pie, v_tp = par_pie >= 0, par_tp >= 0
v_pie_tp = np.zeros(len(est), bool)  # sobrevive a pie y su isla del control sigue con transporte
v_pie_tp[v_pie] = par_pt[par_pie[v_pie]] >= 0
nuevas_tp = np.setdiff1d(np.arange(len(i_tp)), par_tp[v_tp])
islas = {
    "estables_calle": len(est),
    "pie_r5": {"islas": len(i_pie), "sobreviven_pct": pct(v_pie), "b0_sobreviven_pct": pct(v_pie[cer]),
               "b_pos_sobreviven_pct": pct(v_pie[~cer]), "jaccard_resumen": j_pie},
    "transporte_r5": {"islas": len(i_tp), "sobreviven_pct": pct(v_tp), "b0_sobreviven_pct": pct(v_tp[cer]),
                      "b_pos_sobreviven_pct": pct(v_tp[~cer]), "jaccard_resumen": j_tp,
                      "sin_pareja_entre_las_estables": int(len(nuevas_tp)),
                      "psin_sin_pareja": float(sum(PSIN[cu_tp[k]].sum() for k in nuevas_tp))},
    "cruce_isla_por_isla": {"en_ambas_pct": pct(v_pie & v_tp), "solo_pie_pct": pct(v_pie & ~v_tp),
                            "solo_transporte_pct": pct(~v_pie & v_tp), "ninguna_pct": pct(~v_pie & ~v_tp),
                            "de_las_que_sobreviven_a_pie_siguen_con_transporte_pct": pct(v_pie_tp[v_pie]),
                            "islas_pie_r5_con_pareja_en_transporte_pct": pct(par_pt >= 0)},
}
islas["geografia_robusta_al_transporte"] = bool(islas["transporte_r5"]["sobreviven_pct"] >= 80)
print(json.dumps(islas, indent=1))

res = {
    "datos": {"gtfs": GTFS.name, "fuente_gtfs": "MobilityDatabase mdb-1830 (2026-03-09)",
              "nota_gtfs": "calendarios vencen 2025-12-31; sin Mexibús, Mexicable ni combis",
              "pbf": PBF_ZONA.name, "salida": SALIDA_T.isoformat(), "ventana_min": 60, "tope_min": 30,
              "velocidad_pie_kmh": 4.5, "direccion": "unidad -> celda; asimetría medida en una muestra"},
    "huella": HUELLA,
    "cercania_paradas_catalogo_500m_pct": cobertura,
    "pares": {"pie_r5": int(n_pie), "transporte_r5": int(len(t_tp))},
    "asimetria": asim,
    "acceso": versiones, "control": control, "cambio": cambio,
    "islas": islas,
    "minutos": (time.time() - T0) / 60,
}
f4.guardar_json(res, SALIDA / "transporte_publico.json")
pd.DataFrame({"x": XY[:, 0], "y": XY[:, 1], "acceso_rel_pie_r5": F_PIE, "acceso_rel_transporte": F_TP}).to_parquet(
    INT / f"acceso_transporte{sfx}.parquet")

# %% [markdown]
# ## Figura: gente con acceso bajo por estado y dónde cambia

# %%
fig, axs = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={"width_ratios": [1, 1.35]})
ax = axs[0]
xs = np.arange(2)
for d, (nom, k, col_) in enumerate([("Calle (33)", "calle_33", ve.GRIS), ("A pie, r5 (control)", "pie_r5", ve.AZUL),
                                    ("Transporte + pie, r5", "transporte_r5", ve.AQUA)]):
    v = [versiones[k][f"psin_bajo_{r}"] / 1e6 for r in ("CDMX", "EDOMEX")]
    ax.bar(xs + (d - 1) * 0.27, v, 0.25, color=col_, label=nom)
    for x_, v_ in zip(xs + (d - 1) * 0.27, v):
        ax.text(x_, v_, f"{v_:.2f}", ha="center", va="bottom", fontsize=8)
ax.set_xticks(xs, ["CDMX", "EDOMEX"])
ax.set_ylabel("Personas sin seguro con acceso bajo (millones)")
ax.legend(fontsize=8, frameon=False)
ax.set_title("Acceso bajo (f < 0.5) por estado", fontsize=10)

ax = axs[1]
con = PSIN > 0
ax.scatter(*XY[con & (F_PIE < 0.5) & ~sale].T, s=0.4, c=ve.NARANJA, lw=0, alpha=0.5, label="Bajo a pie y con transporte")
ax.scatter(*XY[con & sale].T, s=0.6, c=ve.AQUA, lw=0, label="Sale de acceso bajo con transporte")
ax.scatter(*XY[con & entra].T, s=0.6, c=ve.AZUL, lw=0, label="Entra a acceso bajo")
ax.scatter(*PXY.T, s=0.3, c=ve.TEXTO, lw=0, alpha=0.4, label="Parada del GTFS")
ax.set_xlim(XY[:, 0].min(), XY[:, 0].max())
ax.set_ylim(XY[:, 1].min(), XY[:, 1].max())
ax.set_aspect("equal")
ax.set_xticks([])
ax.set_yticks([])
ax.legend(fontsize=8, loc="lower left", markerscale=12, frameon=True)
ax.set_title("Cambio contra el control a pie con r5", fontsize=10)
ve.titulo(fig, "¿El transporte público cambia el mapa del acceso?",
          f"30 min puerta a puerta, GTFS CDMX, martes 08:00–09:00. Sale de acceso bajo: "
          f"{cambio['psin_sale_de_bajo'] / 1e6:.2f} M; sobreviven "
          f"{islas['transporte_r5']['sobreviven_pct']:.0f}% de las islas estables por calle "
          f"(control a pie: {islas['pie_r5']['sobreviven_pct']:.0f}%).")
fig.subplots_adjust(top=0.84, wspace=0.08)
ve.guardar(fig, FIG / "transporte_publico.png")
reloj("listo")
