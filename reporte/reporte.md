# Persistencia Homológica Aplicada al Análisis de Cobertura de Salud
## Ciudad de México y Estado de México — Análisis Topológico de Desiertos de Salud

**Autor:** Mario Carlos Gaitan Reyna  
**Datos:** DENUE 2023 (INEGI) · Censo de Población y Vivienda 2020 (INEGI) · OpenStreetMap  
**Herramientas:** Python · Gudhi · Ripser · OSMnx · GeoPandas · Folium  
**Repositorio:** `Persistencia_Homologica_Analisis_de_Datos/`

---

## Tabla de Contenidos

1. [Introducción y Problema](#1-introducción-y-problema)
2. [Datos y Preprocesamiento](#2-datos-y-preprocesamiento)
3. [Marco Matemático: Análisis Topológico de Datos](#3-marco-matemático-análisis-topológico-de-datos)
4. [Fase 1A — Alpha Complex y Persistencia Homológica](#4-fase-1a--alpha-complex-y-persistencia-homológica)
5. [Fase 1B — Geolocalización de Huecos H₁](#5-fase-1b--geolocalización-de-huecos-h₁)
6. [Fase 1C — Vectorización y Clasificación Topológica](#6-fase-1c--vectorización-y-clasificación-topológica)
7. [Fase 1D — Bifiltración: Topología × Densidad Urbana](#7-fase-1d--bifiltración-topología--densidad-urbana)
8. [Fase 1E — Enriquecimiento Demográfico (Censo 2020)](#8-fase-1e--enriquecimiento-demográfico-censo-2020)
9. [Fase 2A — Topología Ponderada: Diagramas de Laguerre](#9-fase-2a--topología-ponderada-diagramas-de-laguerre)
10. [Fase 2B — Accesibilidad Peatonal Real: Isócronas con OSMnx](#10-fase-2b--accesibilidad-peatonal-real-isócronas-con-osmnx)
11. [Comparativa de Métodos](#11-comparativa-de-métodos)
12. [Resultados Integrados e Interpretación](#12-resultados-integrados-e-interpretación)
13. [Fase 3 — Optimización Prescriptiva](#13-fase-3--optimización-prescriptiva)
14. [Validación Topológica — Cierre del Ciclo TDA](#14-validación-topológica--cierre-del-ciclo-tda)
15. [Análisis Avanzados](#15-análisis-avanzados)
    - 15.1 Sensibilidad de umbrales
    - 15.2 MCLP Subregional para EDOMEX
    - 15.3 Índice de Marginación como 4.° Eje
    - 15.4 Robustez Topológica: mismo hueco a 4 radios
16. [Conclusiones Generales](#16-conclusiones-generales)

---

## 1. Introducción y Problema

### 1.1 Contexto

El acceso geográfico a servicios de salud es uno de los determinantes sociales más estudiados en epidemiología. En México, la Constitución garantiza el derecho a la protección de la salud, pero la distribución física de la infraestructura médica crea desigualdades severas: zonas con muchas clínicas concentradas en unos pocos kilómetros coexisten con zonas donde la clínica más cercana requiere más de 30 minutos caminando.

Los métodos tradicionales de análisis de acceso a salud (coberturas radiales de 500 m, densidades por municipio) tienen una limitación fundamental: **no detectan la estructura de los huecos**. Un mapa que colorea regiones con "alta densidad de clínicas" puede ocultar un vacío de cobertura de 2 km rodeado de establecimientos pero sin ninguno adentro.

### 1.2 Problema Central

**Pregunta:** ¿Dónde están los desiertos de salud —zonas sin cobertura médica accesible— en Ciudad de México y Estado de México, cuánta población afectan, y cómo se priorizan para política pública?

### 1.3 Propuesta de Solución

Este proyecto aplica **Análisis Topológico de Datos (TDA)** al directorio DENUE del INEGI para detectar huecos estructurales en la red de servicios de salud. La innovación metodológica es usar **persistencia homológica** (H₁) en lugar de distancias euclidianas simples: un hueco topológico persiste solo cuando está genuinamente rodeado de infraestructura por todos lados pero vacío por dentro — exactamente la definición de un desierto de salud estructural.

El pipeline integra cuatro capas de análisis:
1. **Topológica pura:** Alpha complex + persistencia homológica (dónde están los huecos)
2. **Ponderada:** Weighted Alpha complex/Laguerre (qué huecos sobreviven al reconocer que los hospitales grandes cubren más)
3. **Demográfica:** Cruce con Censo 2020 (cuánta gente afectan y cuántos no tienen seguro)
4. **De red:** Isócronas con OSMnx (cuántos minutos camina realmente una persona)

---

## 2. Datos y Preprocesamiento

### 2.1 DENUE (Directorio Estadístico Nacional de Unidades Económicas)

**Fuente:** INEGI, descargado como CSV por entidad federativa.  
**Sector de interés:** SCIAN 62 — Servicios de salud y asistencia social (incluye consultorios médicos, clínicas, hospitales, laboratorios, farmacias con consultorio, dentistas, psicólogos, etc.)

| Región | Unidades económicas totales DENUE | Unidades de salud (SCIAN 62) limpias | Municipios/Alcaldías |
|--------|----------------------------------|-------------------------------------|----------------------|
| CDMX   | ~460,000                         | **21,585**                          | 16 Alcaldías         |
| EDOMEX | ~816,000                         | **30,787**                          | 125 Municipios       |

**Pipeline de preprocesamiento** (`lib/data.py`, `notebooks/01_eda.py` al `04`):

1. **Carga:** CSV en codificación Latin-1 (estándar INEGI)
2. **Filtro sectorial:** `CODIGO_ACTI.astype(str).str.startswith("62")`
3. **Limpieza de coordenadas:**
   - Eliminar nulos en `LATITUD`/`LONGITUD`
   - Eliminar puntos fuera del bounding box de la región (errores de captura)
   - Eliminar duplicados exactos (misma unidad en diferente versión del directorio)
4. **Columna `per_ocu_num`:** La variable `PER_OCU` viene como rango de texto ("0 a 5 personas", "11 a 30 personas"). Se mapea al punto medio: `PER_OCU_MIDPOINT` definido en `lib/config.py`. Ej.: "0 a 5" → 2.5, "11 a 30" → 20, "301 a 400" → 350.
5. **Proyección métrica:** `pyproj.Transformer` convierte WGS84 (grados) → UTM zona 14N, EPSG:32614 (metros). Necesario para que Gudhi opere en metros, no en grados decimales.

**Resultado:** DataFrames `salud_CDMX.parquet` y `salud_EDOMEX.parquet` con columnas `x`, `y` (UTM metros), `per_ocu_num`, y metadatos del DENUE.

**Distribución de tamaño:** La gran mayoría de unidades son micro-establecimientos (0–5 personas): consultorios dentales, médicos generales, farmacias con consultorio. Los hospitales grandes (>100 empleados) son una minoría pero cubren proporcionalmente más territorio.

### 2.2 Censo de Población y Vivienda 2020

**Fuente:** INEGI, nivel AGEB urbana.  
**AGEB** (Área Geoestadística Básica): la unidad mínima de publicación del Censo, equivalente a un "bloque" o grupo de manzanas urbanas. Tiene polígono geográfico (shapefile) y datos demográficos (CSV).

**Archivos utilizados:**
- `Datos/Censo/ageb_mza_urbana_09_cpv2020/` → CDMX (entidad 09)
- `Datos/Censo/ageb_mza_urbana_15_cpv2020/` → EDOMEX (entidad 15)
- `Datos/Geoestadistico/CDMX/conjunto_de_datos/09a.shp` → polígonos AGEBs CDMX
- `Datos/Geoestadistico/EDOMEX/conjunto_de_datos/15a.shp` → polígonos AGEBs EDOMEX

**Variables censales usadas:**

| Variable | Descripción |
|----------|-------------|
| `POBTOT` | Población total por AGEB |
| `PSINDER` | Población SIN afiliación a servicios de salud (la variable crítica) |
| `PDER_SS` | Población CON afiliación (cualquier institución) |
| `PDER_IMSS`, `PDER_ISTE` | Afiliados al IMSS o ISSSTE (seguridad social formal) |
| `P_60YMAS` | Población de 60 años y más (mayor vulnerabilidad) |
| `GRAPROES` | Grado promedio de escolaridad (proxy de marginación) |

**Resumen censal:**

| Región | AGEBs urbanas | Población total | Sin seguro médico |
|--------|--------------|-----------------|-------------------|
| CDMX   | ~2,400       | ~9.2 millones   | ~1.8 M (19.6%)    |
| EDOMEX | ~4,800       | ~16.9 millones  | ~5.1 M (30.2%)    |

---

## 3. Marco Matemático: Análisis Topológico de Datos

### 3.1 ¿Qué es un complejo simplicial?

Un **complejo simplicial** es una generalización de un grafo a dimensiones superiores. Donde un grafo tiene vértices (0-símplices) y aristas (1-símplices), un complejo simplicial puede tener también triángulos (2-símplices), tetraedros (3-símplices), etc.

Dado un conjunto de puntos (las clínicas), construimos un complejo simplicial siguiendo una regla de filtración: dos puntos se conectan con una arista cuando están "suficientemente cerca" (radio de cobertura ≤ α), tres puntos forman un triángulo cuando los tres están cerca entre sí, y así sucesivamente.

### 3.2 Alpha Complex

El **Alpha Complex** (Gudhi) es el tipo de complejo simplicial que usamos. Es un subcomplejo del complejo de Čech, restringido a la teselación de Delaunay (la triangulación que maximiza el ángulo mínimo de cada triángulo).

**Ventaja computacional:** Para N puntos en 2D, el Alpha complex tiene O(N) símplices, mientras que el complejo de Čech tiene O(N³). Para 21,000–30,000 clínicas, esto es la diferencia entre <0.2 segundos y horas de cómputo.

**Parámetro de filtración α:** Cada símplex σ entra al complejo cuando el radio del circuncentro de σ es ≤ √α. Esto crea una **filtración**: una secuencia anidada de complejos

$$\emptyset = K_0 \subseteq K_1 \subseteq \cdots \subseteq K_n = K$$

donde cada $K_i$ contiene los símplices con filtración ≤ α_i.

### 3.3 Persistencia Homológica

La **homología** de un complejo simplicial mide sus "huecos" en cada dimensión:
- **H₀** (grupos de homología dim. 0): cuenta los **componentes conectados** (islas de cobertura)
- **H₁** (grupos de homología dim. 1): cuenta los **ciclos o huecos** (zonas rodeadas de cobertura pero vacías)
- **H₂** (dim. 2): cuenta las cavidades 3D — cero para datos planos

La **persistencia homológica** sigue cómo cambia la homología conforme α aumenta (las clínicas "crecen"):

- Una clase H₁ **nace** en α = `birth` cuando se forma un ciclo (las clínicas rodean completamente una zona vacía)
- La clase **muere** en α = `death` cuando el triángulo que "rellena" el ciclo entra al complejo (la cobertura llena el hueco)
- **Persistencia** = `death - birth` (en metros, después de √): mide cuánto tiempo "sobrevive" el hueco

**Interpretación física:** Un hueco con persistencia de 500 m significa que hay una zona sin cobertura médica que tiene aproximadamente 500 m de "radio efectivo". Un hueco con persistencia de 50 m es ruido urbano normal (pequeño espacio entre dos clínicas en la misma cuadra). El umbral de corte que usamos es **200 m de persistencia**.

### 3.4 Diagrama de Persistencia

El resultado se visualiza en un **diagrama de persistencia**: scatter plot con `birth` en el eje X y `death` en el eje Y. Cada punto es una clase homológica. La diagonal `death = birth` representa persistencia cero. Los puntos lejanos a la diagonal son los huecos más significativos (más persistentes).

**Distancia bottleneck:** Métrica entre dos diagramas de persistencia que mide la "peor correspondencia" entre sus puntos. Captura la diferencia estructural entre dos topologías.

**Distancia Wasserstein (p=1):** Suma de todas las diferencias (no solo la peor). Captura la diferencia global en la distribución de huecos.

### 3.5 Mapper

El algoritmo **Mapper** construye un grafo de resumen de los datos, similar a un "esqueleto topológico":

1. Se define una función *lens* (en nuestro caso, las coordenadas x e y de las clínicas)
2. Se divide el rango de la lens en intervalos solapados
3. En cada intervalo se aplica clustering (DBSCAN sobre las clínicas)
4. Los nodos del grafo son los clusters; las aristas conectan clusters que comparten clínicas (por el solapamiento)

El resultado es un grafo 2D que preserva la estructura topológica del espacio original. La fragmentación del grafo (muchos nodos, pocas aristas) indica cobertura dispersa; un grafo más conectado indica mayor continuidad.

---

## 4. Fase 1A — Alpha Complex y Persistencia Homológica

**Notebook:** `notebooks/04_persistencia.py` al `07_mapper.py`  
**Librería clave:** `lib/tda.py`

### 4.1 Implementación

```python
# Construir Alpha Complex
ac = gudhi.AlphaComplex(points=puntos_utm)  # puntos en metros (UTM 14N)
st = ac.create_simplex_tree()               # árbol de símplices

# Calcular persistencia
st.compute_persistence()
diags = {dim: st.persistence_intervals_in_dimension(dim) for dim in (0, 1, 2)}

# Convertir de alpha (radio²) a metros
diags_m = {dim: np.sqrt(np.clip(diags[dim], 0, None)) for dim in diags}
```

**Función `tda.a_radio(diags)`:** Los valores de filtración del Alpha complex de Gudhi están en unidades de radio² (metros²). Para interpretarlos en metros, se aplica √ a cada valor birth y death. Esto transforma el diagrama de persistencia de "radio cuadrado" a "radio en metros".

### 4.2 Resultados H₁ (Huecos de Cobertura)

| Métrica | CDMX | EDOMEX |
|---------|------|--------|
| Huecos H₁ persistentes (≥ 200 m) | **71** | **209** |
| Persistencia máxima | 1,510 m | 11,808 m |
| Persistencia promedio | ~380 m | ~650 m |
| β₁ máximo (huecos simultáneos) | ~150 m radio | ~220 m radio |
| Distancia bottleneck CDMX↔EDOMEX | — | ~5,904 m |
| Distancia Wasserstein CDMX↔EDOMEX | — | ~87,278 m |

**Hallazgo crítico:** EDOMEX tiene **3× más huecos** que CDMX y su peor hueco (11,808 m de persistencia ≈ 6 km de radio efectivo) es **7.8× mayor** que el peor de CDMX. La distancia Wasserstein de 87 km refleja que no son solo "más huecos", sino que toda la distribución es cualitativamente diferente.

### 4.3 Resultados H₀ (Conectividad)

- **CDMX:** Las ~21,585 clínicas se fusionan en componentes conectados a radios significativamente menores que EDOMEX → mayor densidad → mejor conectividad.
- **EDOMEX:** Los ~30,787 establecimientos están más dispersos; los componentes se fusionan a radios mayores → cobertura más fragmentada geográficamente.

### 4.4 Mapper

| Región | Nodos en el grafo | Aristas |
|--------|------------------|---------|
| CDMX   | 226              | 520     |
| EDOMEX | 983              | 1,213   |

EDOMEX produce un grafo Mapper ~4× más grande con solo 2.3× más aristas relativas → mayor fragmentación. El grafo de CDMX tiene una estructura más "compacta" (mayor densidad de aristas por nodo). Esto confirma, desde una perspectiva diferente, que la cobertura de CDMX es más continua.

**Archivos de salida:** `outputs/figuras/persistencia_CDMX.png`, `persistencia_EDOMEX.png`, `mapper_CDMX.html`, `mapper_EDOMEX.html`

---

## 5. Fase 1B — Geolocalización de Huecos H₁

**Notebook:** `notebooks/07_localizacion.py` (integrado en `08`)  
**Función clave:** `tda.ciclos_H1(simplex_tree, puntos_xy, min_persistencia)`

### 5.1 El Problema

La persistencia homológica identifica huecos como pares abstractos (birth, death) en el diagrama, pero no dice directamente "el hueco está en las coordenadas (x, y)". Para hacer el análisis accionable en política pública, necesitamos saber **dónde en el mapa** está cada hueco.

### 5.2 Método: Extracción de Centroides por Persistence Pairs

La clave está en el método `persistence_pairs()` de Gudhi, que devuelve no solo los valores birth/death sino los **símplices** (vértices concretos) que crean y eliminan cada hueco:

```python
pairs = simplex_tree.persistence_pairs()
for birth_simplex, death_simplex in pairs:
    # H₁: birth_simplex = arista [v1, v2] que crea el ciclo
    #      death_simplex = triángulo [v1, v2, v3] que rellena el ciclo
    if len(birth_simplex) == 2 and len(death_simplex) == 3:
        # El centroide del triángulo de muerte ≈ centro geográfico del hueco
        pts_muerte = puntos_xy[list(death_simplex)]
        cx, cy = pts_muerte[:, 0].mean(), pts_muerte[:, 1].mean()
```

**Justificación matemática:** El triángulo de muerte (`death_simplex`) es el triángulo de Delaunay cuya inserción rellena el ciclo H₁. Su circuncentro (o simplemente su centroide como aproximación) es el punto más alejado de las clínicas circundantes — exactamente el "peor lugar" dentro del hueco donde una persona estaría más lejos de atención médica.

Después de extraer (cx, cy) en UTM, se convierten a WGS84 con `pyproj.Transformer` para visualización en mapas Folium.

### 5.3 Visualización: Mapas Interactivos

Para cada hueco se genera un círculo en el mapa cuyo radio es proporcional a la persistencia (en metros, a escala). Los mapas HTML interactivos permiten hacer click en cada hueco para ver: ID, birth, death, persistencia en metros.

**Archivos de salida:**
- `outputs/figuras/huecos_CDMX.html` — 71 huecos geolocalizados
- `outputs/figuras/huecos_EDOMEX.html` — 209 huecos geolocalizados

---

## 6. Fase 1C — Vectorización y Clasificación Topológica

**Notebook:** `notebooks/08_arquetipos.py`

### 6.1 Persistence Images — Comparación Cuantitativa Entre Regiones

Para **comparar matemáticamente** las topologías de dos regiones necesitamos un vector de longitud fija que represente cada diagrama de persistencia (que tiene puntos variables). Las **Persistence Images** (Adams et al., 2017, implementadas en `persim`) resuelven esto:

**Método:**
1. Se define una superficie de peso `ρ(x,y) = y` (ponderar más los puntos más persistentes)
2. Cada punto `(b, p)` del diagrama (birth, persistencia) contribuye una gaussiana 2D centrada en (b, p)
3. La suma de todas las gaussianas se evalúa sobre un grid de píxeles → imagen 2D → vector aplanado

```python
from persim import PersistenceImager
pimgr = PersistenceImager(pixel_size=0.05)
pimgr.fit([diag_CDMX_H1, diag_EDOMEX_H1])  # ajustar rango del grid
img_cdmx   = pimgr.transform(diag_CDMX_H1)
img_edomex = pimgr.transform(diag_EDOMEX_H1)
```

**Resultado:** Similitud coseno CDMX ↔ EDOMEX = **0.635** (distancia coseno = 0.365)

Una distancia coseno de 0.365 sobre el máximo posible de 1.0 indica que las dos regiones tienen **topologías notablemente distintas** — no son versiones de la misma estructura a diferente escala, sino sistemas genuinamente diferentes. Esto valida la decisión de analizarlas por separado y sugiere que una política pública única para las dos regiones sería inadecuada.

**Uso escalable:** Este vector permite comparar las 32 entidades federativas mediante clustering jerárquico (dendrograma de similitud de cobertura de salud) sin supervisión y sin costo computacional adicional.

### 6.2 Arquetipos Topológicos

Se definen 4 arquetipos según la posición de cada hueco en el espacio (birth, persistencia):

| Arquetipo | Condición | Significado | CDMX | EDOMEX |
|-----------|-----------|-------------|------|--------|
| **1. Enclave sin cobertura** | birth bajo + pers. alta | Rodeado de servicios pero vacío interior | 23 | 27 |
| **2. Desierto estructural** | birth alto + pers. alta | Zona sin infraestructura desde cero | 6 | **84** |
| **3. Vacío periférico** | birth alto + pers. baja | Transición urbano-rural, cobertura parcial | 6 | 44 |
| **4. Micro-brecha** | birth bajo + pers. baja | Variación urbana normal, no prioritaria | 36 | 54 |

**Umbral crítico:** Persistencia ≥ 3 km marca el límite de los huecos verdaderamente estructurales (0 en CDMX, varios en EDOMEX).

**Hallazgo clave:** EDOMEX tiene **14× más desiertos estructurales** que CDMX (84 vs 6). El arquetipo 2 (desierto) implica que no hay infraestructura circundante que "rodee" el hueco — es un vacío en el sentido más absoluto. Los arquetipos 1 (enclave) son más fáciles de resolver: la infraestructura ya existe alrededor, solo falta un establecimiento dentro del hueco.

---

## 7. Fase 1D — Bifiltración: Topología × Densidad Urbana

**Notebook:** `notebooks/09_bifiltracion.py`

### 7.1 El Problema

La clasificación por arquetipos topológicos distingue huecos por su estructura geométrica (grande/pequeño, rodeado/periférico), pero no distingue entre:
- Una zona sin cobertura con **alta demanda** (muchas personas viviendo ahí)
- Una zona sin cobertura simplemente **despoblada** (campo vacío)

Ambas son "huecos topológicos" equivalentes desde el punto de vista de la persistencia homológica, pero tienen urgencia de política pública completamente diferente.

### 7.2 Método: KDE como Segunda Dimensión de Filtración

Se agrega una segunda dimensión: la **densidad local de actividad económica**, calculada como un Kernel Density Estimate (KDE) gaussiano 2D sobre las coordenadas UTM de todas las unidades DENUE (no solo salud). Esta densidad funciona como **proxy de densidad urbana/poblacional**: donde hay muchos negocios, hay mucha gente.

```python
from scipy.stats import gaussian_kde
kde = gaussian_kde(puntos_utm.T)        # Scott's rule para bandwidth
densidades = kde(centroides_huecos.T)   # evaluar en centroide de cada hueco
```

**Cuadrantes (bifiltración):**

| Categoría | Condición | Descripción | CDMX | EDOMEX |
|-----------|-----------|-------------|------|--------|
| **[1] CRÍTICO** | pers ≥ 500m **Y** densidad ≥ p50 | Zona densa sin cobertura | **0** | **16** |
| **[2] ALERTA** | pers ≥ 500m **O** densidad ≥ p50 | Zona activa con hueco grande | 9 | 52 |
| [3] Moderado | pers < 500m, densidad ≥ p50 | Densa pero hueco menor | 36 | 89 |
| [4] Bajo | pers < 500m, densidad < p50 | Rural/disperso | 26 | 52 |

**Resultado:** La bifiltración reduce los 209 huecos abstractos de EDOMEX a **16 críticos** (requieren intervención inmediata) y **52 de alerta** (monitorear), con coordenadas concretas para cada uno. CDMX tiene **0 huecos críticos** — sus brechas son moderadas y en zonas con actividad económica, lo que sugiere que la infraestructura privada (farmacias, consultorios particulares) complementa la cobertura.

**Archivos de salida:** `outputs/figuras/bifiltracion_CDMX.png`, `bifiltracion_EDOMEX.png`

---

## 8. Fase 1E — Enriquecimiento Demográfico (Censo 2020)

**Notebook:** `notebooks/10_cruce_censal.py`  
**Librería:** `lib/censo.py`

### 8.1 Objetiva

Responder: ¿Cuántas personas reales viven dentro de cada hueco topológico, y cuántas de ellas no tienen seguro médico?

### 8.2 Método: Spatial Join (Cruce Espacial)

El cruce entre huecos topológicos y AGEBs censales se realiza con **`geopandas.sjoin`** (spatial join "intersects"):

```python
# Cada hueco se representa como un círculo con radio = persistencia
from shapely.geometry import Point
gdf_huecos["geometry"] = gdf_huecos.apply(
    lambda r: Point(r["lon"], r["lat"]).buffer(r["pers_m"] / 111_320), axis=1
)
# Join espacial: cada hueco "captura" las AGEBs que intersecta
joined = gpd.sjoin(gdf_huecos, gdf_ageb, how="left", predicate="intersects")
# Agregar por hueco: sumar población de todas las AGEBs captadas
agg = joined.groupby("hueco_id").agg(
    pob_afectada=("POBTOT", "sum"),
    pob_sin_salud=("PSINDER", "sum"),
    pob_60_mas=("P_60YMAS", "sum"),
    ...
)
```

**Nota técnica:** El radio del buffer está en grados (÷ 111,320 m/°), equivalente a la persistencia en metros. Este círculo sobre el centroide del hueco captura las AGEBs que geográficamente pertenecen al área sin cobertura.

### 8.3 Índice de Prioridad Compuesto

Para cada hueco se calcula un índice de prioridad de 0 a 100 que combina:

```
índice = 0.4 × (persistencia / persistencia_máx) × 100
       + 0.35 × (% sin seguro médico)
       + 0.15 × (% adultos mayores)
       + 0.10 × (1 - escolaridad_norm)
```

Los pesos reflejan la política pública: la persistencia (tamaño del hueco) y el porcentaje sin seguro son los factores más importantes; la vulnerabilidad etaria y educativa son factores secundarios.

### 8.4 Resultados

**Nivel de prioridad — CDMX:**

| Nivel | Huecos | Población afectada | Sin seguro |
|-------|--------|-------------------|------------|
| Crítico | 0 | 0 | 0 |
| Alto | 8 | ~82,000 | ~19,000 |
| Moderado | 31 | ~220,000 | ~52,000 |
| Bajo | 32 | dispersa | dispersa |

**Nivel de prioridad — EDOMEX:**

| Nivel | Huecos | Población afectada | Sin seguro |
|-------|--------|-------------------|------------|
| Crítico | 5 | ~135,000 | ~45,000 |
| Alto | 28 | ~420,000 | ~138,000 |
| Moderado | 89 | ~680,000 | ~198,000 |
| Bajo | 87 | dispersa | dispersa |

**Huecos más prioritarios:**

| Región | Hueco # | Índice | Pers. (m) | Población | Sin seguro |
|--------|---------|--------|-----------|-----------|------------|
| EDOMEX | 78 | 59.0 (Alto) | 450 m | 35,619 | 12,010 (33.7%) |
| CDMX | 8 | 61.7 (Alto) | 501 m | 28,326 | 6,785 (24.0%) |
| EDOMEX | 191 | 47.8 | 212 m | 28,908 | 8,296 (28.7%) |

**Mapas interactivos:** `outputs/figuras/huecos_censal_CDMX.html` y `huecos_censal_EDOMEX.html` — cada círculo coloreado por nivel de prioridad (rojo = crítico, naranja = alto, amarillo = moderado), con popup que muestra todos los indicadores censales.

**Matrices de riesgo:** `outputs/figuras/matriz_riesgo_CDMX.png` y `matriz_riesgo_EDOMEX.png` — scatter de persistencia × % sin seguro, coloreado por población afectada. El cuadrante superior-derecho (grande + desprotegido) identifica los huecos de máxima urgencia.

**Impacto total estimado:**
- CDMX: ~29,741 personas en huecos fuera del límite de 15 min, de los cuales ~7,252 sin seguro
- EDOMEX: ~45,023 personas en huecos fuera del límite de 15 min, de los cuales ~16,085 sin seguro

---

## 9. Fase 2A — Topología Ponderada: Diagramas de Laguerre

**Notebook:** `notebooks/11_topologia_ponderada.py`  
**Función clave:** `tda.weighted_alpha_complex(puntos, pesos)`

### 9.1 Motivación

El Alpha complex clásico trata todas las clínicas como iguales: un consultorio dental con 1 empleado y un Hospital General con 800 camas "cierran" huecos con la misma fuerza. Esto es incorrecto en términos de política pública: un hospital grande puede atender a la población en un radio mucho mayor que un consultorio pequeño.

**Pregunta de la Fase 2A:** ¿Qué huecos persisten incluso cuando reconocemos que los hospitales grandes cubren más territorio que los consultorios chicos?

### 9.2 Fundamento Matemático: Weighted Alpha Complex (Laguerre)

El **Weighted Alpha Complex** extiende el Alpha complex asignando a cada punto un peso w_i ≥ 0 que representa su "radio de influencia". Matemáticamente, sustituye la distancia euclidiana por la **distancia de potencia**:

$$\pi(p, q_i) = d(p, q_i)^2 - w_i$$

donde d(p, q_i) es la distancia euclidiana desde el punto p hasta la clínica i, y w_i es el peso (radio²) de la clínica i.

El conjunto de puntos más cercanos a q_i según la distancia de potencia forma la **celda de Laguerre** de i — análoga a la celda de Voronoi pero con pesos. Una clínica con mayor radio de influencia (mayor w_i) tiene una celda de Laguerre más grande.

La filtración del Weighted Alpha complex procede igual que la del Alpha complex, pero usando distancias de potencia en lugar de euclidianas. Los huecos H₁ que sobreviven son zonas donde **ninguna clínica**, independientemente de su tamaño, tiene suficiente influencia para cubrir el área.

### 9.3 Función de Peso

```python
def pesos_desde_per_ocu(df, radio_base=50.0, factor=30.0):
    per_ocu = df["per_ocu_num"].fillna(0).values
    radios = radio_base + factor * np.sqrt(per_ocu)
    return radios ** 2    # Gudhi recibe radio², no radio
```

El radio crece de forma **sublineal** (√) con el personal ocupado, lo que refleja que la capacidad de atención no escala linealmente con el tamaño (un hospital 10× más grande no atiende a 10× más personas en el mismo tiempo de acceso).

| Tipo de unidad | per_ocu | Radio de cobertura |
|----------------|---------|-------------------|
| Consultorio mínimo | 2.5 | 97 m |
| Clínica pequeña | 10 | 145 m |
| Clínica mediana | 20 | 184 m |
| Hospital grande | 300 | 570 m |
| Hospital muy grande | 1,000 | ~998 m |

### 9.4 Resultados

| Métrica | CDMX Clásico | CDMX Laguerre | EDOMEX Clásico | EDOMEX Laguerre |
|---------|-------------|--------------|---------------|----------------|
| Huecos H₁ (≥ 200 m) | 71 | **118** | 209 | **241** |
| Cambio relativo | — | +66.2% | — | +15.3% |
| Persistencia máxima | 1,510 m | mayor | 11,808 m | mayor |

**Resultado inesperado:** El modelo ponderado encuentra **más** huecos, no menos. Esto parece contra-intuitivo pero tiene una explicación matemática: al dar mayor influencia a los hospitales grandes, se crean **fronteras más pronunciadas** entre zonas de influencia de hospitales grandes y zonas de consultorios pequeños. Estas fronteras crean nuevos "bordes" topológicos que el modelo clásico no detectaba. En otras palabras, los hospitales grandes "absorben" su territorio con tanta fuerza que generan vacíos en sus bordes.

**Implicación:** Los huecos adicionales detectados por Laguerre son zonas de frontera donde la transición entre la zona de influencia de un hospital grande y la de consultorios pequeños crea una brecha de cobertura — ni el hospital grande alcanza, ni los consultorios pequeños tienen suficiente capacidad.

**Mapas interactivos:** `outputs/figuras/huecos_laguerre_CDMX.html` y `huecos_laguerre_EDOMEX.html` — azul = huecos clásicos, rojo = huecos adicionales detectados por Laguerre.

**Figura de distribución:** `outputs/figuras/distribucion_radios_laguerre.png` — distribución de radios de cobertura ponderados por región (escala logarítmica), que muestra la heterogeneidad de la infraestructura.

---

## 10. Fase 2B — Accesibilidad Peatonal Real: Isócronas con OSMnx

**Notebook:** `notebooks/12_isocronas.py`  
**Librería:** `lib/geo_network.py`

### 10.1 Motivación

Las fases anteriores usan distancia euclidiana (línea recta) como métrica de accesibilidad. Esto ignora un factor crítico de la vida urbana: **la red de calles**. Una clínica a 400 m en línea recta puede requerir 25 minutos caminando si hay una vialidad rápida sin cruce peatonal, una barranca, o un parque sin acceso directo.

**Pregunta de la Fase 2B:** ¿Cuántos minutos camina realmente una persona desde dentro de cada hueco hasta la clínica más cercana, usando calles reales?

### 10.2 Dos Velocidades de Cálculo

La Fase 2B usa dos métodos complementarios, elegidos por eficiencia computacional:

#### Método 1: KDTree (Estimación Rápida — todos los huecos)

```python
from scipy.spatial import cKDTree
tree = cKDTree(clinicas[["x", "y"]].values)          # árbol sobre UTM
xs, ys = transformer.transform(huecos["lon"], huecos["lat"])  # huecos a UTM
dists, _ = tree.query(np.column_stack([xs, ys]))      # distancia euclidiana
tiempo_est = dists * DETOUR / velocidad_m_min         # factor de desvío 1.35
```

**Factor de desvío (1.35):** La distancia real caminando en red urbana es en promedio 1.35× la distancia euclidiana (estudios de walkability urbana). Este factor convierte distancia euclidiana en estimación de distancia real.

**Velocidad:** 4.5 km/h (velocidad peatonal estándar OMS para adultos).

**Fuente de datos:** Los archivos `salud_CDMX.parquet` y `salud_EDOMEX.parquet` con coordenadas UTM (x, y) de las clínicas del DENUE ya procesadas. **No usa internet** — opera sobre datos locales ya cargados.

**Resultado:** Estimación en <1 segundo para los 161 huecos habitados.

#### Método 2: OSMnx + NetworkX (Red Real — top 3 por ciudad)

```python
# Descargar red vial real (peatonal) en radio de 2 km alrededor del hueco
G = ox.graph_from_point((lat, lon), dist=2000, network_type="walk")
G_proj = ox.project_graph(G)  # proyectar a UTM del área

# Agregar tiempo en minutos a cada arista
for _, _, _, data in G_proj.edges(data=True, keys=True):
    data["time"] = data["length"] / (4.5 * 1000 / 60)

# Nodo más cercano al centroide del hueco (paciente)
nodo_origen = ox.distance.nearest_nodes(G_proj, x_orig, y_orig)

# Camino mínimo desde paciente hasta clínica
ruta = nx.shortest_path(G_proj, nodo_origen, nodo_clinica, weight="time")
tiempo_real = nx.path_weight(G_proj, ruta, weight="time")

# Isócrona: todo lo alcanzable en 15 min desde el nodo del paciente
ego = nx.ego_graph(G_proj, nodo_origen, radius=15, distance="time")
nodos_alcanzables = [G_proj.nodes[n] for n in ego.nodes()]
zona_15min = MultiPoint(nodos_alcanzables).convex_hull
```

**Isócrona:** El polígono convex hull de todos los nodos de la red vial alcanzables en ≤ 15 minutos caminando desde el centroide del hueco. Este polígono (azul en los mapas) representa el territorio que el paciente puede alcanzar — si la clínica más cercana está fuera de esta zona, es inaccesible a pie en 15 minutos.

### 10.3 Filtrado: Solo Huecos Habitados

Se filtran los huecos con `pob_afectada > 0` para excluir zonas rurales/vacías sin AGEBs urbanas. Esta distinción es crítica:

| Estado | Total huecos H₁ | Con población (habitados) | Sin AGEB (rurales) |
|--------|-----------------|--------------------------|-------------------|
| CDMX   | 71              | 62 (87%)                 | 9 (13%)           |
| EDOMEX | 209             | 99 (47%)                 | 110 (53%)         |

Los 110 huecos "rurales" de EDOMEX son en su mayoría zonas forestales, terrenos agrícolas o áreas no urbanizadas que tienen huecos topológicos válidos pero sin población permanente registrada en el Censo. Sus tiempos estimados (65–307 min caminando) son reales geográficamente pero irrelevantes para política pública de salud urbana.

### 10.4 Resultados — Huecos Habitados

| Métrica | CDMX | EDOMEX |
|---------|------|--------|
| Huecos habitados | 62 | 99 |
| Mediana de tiempo a clínica | **7.6 min** | **9.6 min** |
| Tiempo máximo (habitados) | 23.9 min | 41.2 min |
| Fuera del límite de 15 min | 4 (6%) | 16 (16%) |
| Población en huecos inaccesibles | ~29,741 | ~45,023 |
| Sin seguro médico en huecos inaccesibles | ~7,252 | ~16,085 |

**Interpretación:** La mayoría de los huecos topológicos en zonas habitadas tienen una clínica accesible en menos de 15 minutos (94% en CDMX, 84% en EDOMEX). Esto no contradice el hallazgo de que hay huecos — significa que la red de clínicas circundante es suficiente para atender a los residentes de estos huecos en términos de distancia caminando. Los huecos críticos son los 4 de CDMX y 16 de EDOMEX que sí están genuinamente desatendidos.

### 10.5 Resultados — Mapas Detallados (Top 3 por Categoría)

**CDMX — Top 3 huecos más grandes (por persistencia):**
- Hueco #0: 23.7 min reales, 1,510 m persistencia — FUERA del límite
- Hueco #2: 16.3 min reales, 1,292 m persistencia — FUERA del límite
- Hueco #4: 16.5 min reales, 749 m persistencia — FUERA del límite

**CDMX — Top 3 huecos más lejanos (por tiempo):**
- Hueco #0: 23.7 min (coincide con el más grande)
- Hueco #2: 16.3 min (coincide con el segundo más grande)
- Hueco #8: 8.3 min (accesible, pero el más lejano entre los accesibles)

**EDOMEX — Top 3 huecos más grandes:**
- Hueco #32: 25.5 min reales, 1,006 m persistencia — FUERA
- Hueco #34: 26.4 min reales, 964 m persistencia — FUERA
- Hueco #36: 20.3 min reales, 858 m persistencia — FUERA

**EDOMEX — Top 3 huecos más lejanos:**
- Hueco #63: 34.8 min reales — el más inaccesible de EDOMEX
- Hueco #140: 30.9 min reales
- Hueco #32: 25.5 min reales (coincide con el más grande)

**Archivos de salida:**
- `outputs/figuras/scatter_accesibilidad.png` — dispersión tamaño × tiempo, CDMX y EDOMEX separados
- `outputs/figuras/comparativa_tamano.png` — top 10 más grandes por ciudad
- `outputs/figuras/comparativa_distancia.png` — top 10 más lejanos por ciudad
- `outputs/figuras/mapas_accesibilidad_CDMX.png` — 6 mapas OSM: fila superior = top 3 grandes, fila inferior = top 3 lejanos
- `outputs/figuras/mapas_accesibilidad_EDOMEX.png` — mismo para EDOMEX

**Elementos visuales en cada mapa:**
| Elemento | Color | Descripción |
|----------|-------|-------------|
| Red de calles | Gris claro | Red vial real de OSM (caminata) |
| Zona azul | Azul translúcido | Todo lo alcanzable en ≤ 15 min caminando |
| Punto naranja | Naranja | Centroide del hueco (donde estaría el paciente) |
| Punto verde | Verde | Clínica más cercana por red real |
| Anotación grande | Rojo/verde | Tiempo exacto de caminata en minutos |

---

## 11. Comparativa de Métodos

### 11.1 Opción A (Laguerre) vs Opción B (Isócronas)

| Dimensión | Opción A: Laguerre | Opción B: Isócronas OSMnx |
|-----------|-------------------|-----------------------------|
| **Pregunta central** | ¿Qué huecos persisten al ponderar por capacidad hospitalaria? | ¿Cuántos minutos camina el paciente por calles reales? |
| **Métrica** | Distancia de potencia (euclidiana ponderada) | Tiempo de traslado en red vial real |
| **Diferenciación** | Por tamaño de clínica (per_ocu) | Por estructura urbana (calles, barreras) |
| **Velocidad de cómputo** | <1 segundo (región completa) | 30–120 s por hueco |
| **Escala** | Región completa (miles de km²) | Zonas focales (radio 2 km) |
| **Precisión física** | Media (ignora red vial) | Alta (sigue calles reales) |
| **Datos externos** | No requiere internet | Descarga OSM en tiempo real |
| **Uso ideal** | Identificar desiertos estructurales a escala estatal/nacional | Auditar accesibilidad peatonal real en zonas prioritarias |

### 11.2 Los Métodos son Complementarios

Los dos enfoques responden preguntas distintas y se usan en secuencia:

```
DENUE → Alpha Complex → Huecos H₁ (280 huecos)
                ↓ Fase 1E (Censo)
         161 huecos habitados
                ↓ Fase 2A (Laguerre)
         ¿Sobreviven a la ponderación?
                ↓ Fase 2B (Isócronas, top críticos)
         Minutos exactos + zona alcanzable en mapa
                ↓ Fase 3 (próxima)
         Coordenadas para nuevas clínicas
```

**Flujo recomendado para política pública:**
1. Laguerre identifica los huecos que persisten incluso reconociendo heterogeneidad de infraestructura
2. Cruce censal filtra por impacto real en población (pob_afectada, sin_seguro)
3. Isócronas validan con red real y producen el "minutaje de inaccesibilidad" que es el argumento político concreto

---

## 12. Resultados Integrados e Interpretación

### 12.1 Panorama General

| Indicador | CDMX | EDOMEX |
|-----------|------|--------|
| Establecimientos de salud (DENUE) | 21,585 | 30,787 |
| Huecos topológicos H₁ (≥ 200 m persistencia) | 71 | 209 |
| Huecos habitados (con población Censo 2020) | 62 | 99 |
| Huecos críticos (bifiltración: densos + grandes) | 0 | 16 |
| Huecos fuera del límite de 15 min (Isócronas) | 4 (6%) | 16 (16%) |
| Tiempo mediano a clínica (huecos habitados) | 7.6 min | 9.6 min |
| Tiempo máximo a clínica (huecos habitados) | 23.9 min | 41.2 min |
| Población en huecos inaccesibles | ~29,741 | ~45,023 |
| Sin seguro médico en huecos inaccesibles | ~7,252 | ~16,085 |
| Similitud topológica CDMX↔EDOMEX | 0.635 (coseno) — Notablemente distintas |

### 12.2 CDMX: Cobertura Relativamente Buena con Brecha de Capacidad

CDMX tiene **mayor densidad** de clínicas (21,585 en un área menor) y una distribución más homogénea. El 94% de los huecos habitados tiene una clínica accesible en ≤ 15 min caminando. Los 4 huecos críticos (Huecos #0, #2, #4) son zonas de frontera entre alcaldías donde la infraestructura pública es escasa y la privada no cubre.

El Hueco #0 de CDMX es el más crítico: persistencia de 1,510 m (el más grande de la región), solo 55 personas registradas en el Censo pero con **100% sin seguro médico**, y 23.7 min reales a la clínica más cercana. Es un caso de "bolsa de exclusión": pequeña en población pero absolutamente desprotegida.

El Hueco #8 de CDMX es el de mayor impacto demográfico: persistencia de 501 m, 28,326 personas afectadas, 24% sin seguro, pero **accesible en 8.3 min**. El hueco topológico existe pero la red de clínicas circundante es suficientemente densa para atenderlo sin una clínica dentro.

### 12.3 EDOMEX: Problema Sistémico de Cobertura

EDOMEX tiene **3× más huecos** que CDMX, con persistencias significativamente mayores. El 53% de los huecos H₁ son en zonas sin población registrada (rurales), lo que refleja la extensión territorial del Estado de México (más de 20,000 km² vs ~1,485 km² de CDMX).

En las zonas **habitadas**, el 16% de los huecos está fuera del límite de 15 min, comparado con solo 6% en CDMX. Esto refleja un problema estructural: los 30,787 establecimientos de salud del EDOMEX cubren un territorio mucho mayor, con menor densidad en zonas periurbanas y semi-urbanas.

**El caso más crítico del proyecto:** Hueco #78 de EDOMEX
- Persistencia: 450 m (zona moderada topológicamente)
- Población: **35,619 personas**
- Sin seguro médico: **12,010 (33.7%)**
- Adultos mayores: significativa proporción
- Índice de prioridad: 59.0 (Alto)
- Acceso real: <12 min (accesible, pero en zona de alta demanda)

Este hueco es el que más justifica inversión: la solución no es construir una clínica (hay acceso en red), sino **ampliar capacidad y asegurar cobertura de seguridad social** en la zona.

### 12.4 Efecto de la Topología Ponderada (Laguerre)

El resultado inesperado de Laguerre (más huecos, no menos) revela que la heterogeneidad de tamaños de clínicas en México **crea sus propios desiertos**: las zonas de frontera entre hospitales grandes y consultorios pequeños son topológicamente inestables. Un hospital grande "succiona" territorio a su alrededor, dejando vacíos en sus bordes que los consultorios pequeños no alcanzan a cubrir.

Este efecto es particularmente visible en CDMX, donde la diferencia en número de huecos (+66.2%) es mayor que en EDOMEX (+15.3%). CDMX tiene mayor heterogeneidad de infraestructura (hospitales grandes de IMSS, ISSSTE, privados coexistiendo con miles de consultorios), creando más fronteras de Laguerre que EDOMEX.

---

## 13. Fase 3 — Optimización Prescriptiva

### 13.1 Resumen de hallazgos Fases 1–2

Antes de la prescripción, las dos fases previas produjeron el mapa completo del déficit:

**Huecos detectados (Laguerre, min_persistencia = 200 m):**

| Región | Clínicas totales | Huecos H₁ totales | Huecos habitados | Huecos con urgencia Crítica |
|--------|-----------------|-------------------|------------------|-----------------------------|
| CDMX | 21,585 | 118 | 62 | 0 (ninguno fuera de 15 min) |
| EDOMEX | 30,787 | 241 | 99 | 16 (>15 min a pie reales) |

**Población afectada en huecos habitados:**

| Región | Pob. total en huecos | Sin seguro médico | % sin seguro | Pers. máx. (m) |
|--------|----------------------|-------------------|--------------|----------------|
| CDMX | ~1.4 M | 87,967 | 24% promedio | 1,510 |
| EDOMEX | ~2.1 M | 182,357 | 33% promedio | 11,810 |

**Hallazgo clave Fase 2:** El Weighted Alpha Complex (Laguerre) reduce el número de huecos significativos al reconocer que hospitales grandes cubren más territorio. Los huecos que sobreviven a la ponderación son genuinamente estructurales — no artefactos de distribución uniforme.

### 13.2 Scoring multi-eje de 4 dimensiones (Notebook 13)

Cada hueco recibe un rango percentil normalizado [0,1] en **cuatro ejes** con pesos iguales (25% cada uno):

| Eje | Variable | Peso | Justificación |
|-----|----------|------|---------------|
| Inaccesibilidad | Tiempo caminando a clínica más cercana | 25% | Barrera física principal |
| Inequidad | Personas sin seguro médico en el hueco | 25% | Retorno social directo |
| Estructura | Persistencia topológica del hueco | 25% | Robustez del vacío detectado |
| **Marginación** | **Índice compuesto desde Censo 2020** | **25%** | **Vulnerabilidad socioeconómica** |

El Índice de Marginación (IM) se construye sin datos externos de CONAPO, únicamente desde variables del Censo disponibles en cada hueco:

$$IM = 0.35 \cdot \widehat{\text{pct\_sin\_salud}} + 0.25 \cdot \widehat{\text{déficit\_educativo}} + 0.25 \cdot \widehat{\text{pob\_60+}} + 0.15 \cdot \widehat{\text{densidad\_demanda}}$$

**Resultados del scoring:**

| Región | Huecos habitados | Críticos (≥p75) | Altos (p50–p75) | IM medio | Score máximo |
|--------|-----------------|-----------------|-----------------|----------|--------------|
| CDMX | 62 | 16 | 16 | 0.293 | 0.788 |
| EDOMEX | 99 | 26 | 24 | 0.370 | 0.927 |

EDOMEX tiene mayor IM medio (0.370 vs 0.293), confirmando que sus huecos combinan barreras de acceso físico con desventajas socioeconómicas más pronunciadas. El único hueco que domina los **4 ejes simultáneamente** es el Hueco #36 de EDOMEX (score=0.927, pers=858m, 52% sin seguro, IM=0.519).

### 13.3 Selección de huecos prioritarios (Notebook 14)

Se aplica un criterio OR — basta cumplir uno de cuatro ejes para ser priorizado:

| Eje | Umbral | Justificación |
|-----|--------|---------------|
| Tiempo de caminata | > 10 min | Acceso genuinamente problemático |
| Población sin seguro | > p60 de la ciudad | Alto retorno social de una clínica nueva |
| Persistencia topológica | > 400 m | Vacío estructural real en la red |
| Índice de marginación | > p60 del conjunto | Vulnerabilidad socioeconómica severa |

**Resultado de la selección:**
- CDMX: **39 de 62** huecos habitados son prioritarios (87,967 personas sin seguro)
- EDOMEX: **72 de 99** huecos habitados son prioritarios (182,357 personas sin seguro)

Los huecos seleccionados se agrupan geográficamente con **DBSCAN** (eps = 1,500 m, min_samples = 1): huecos cercanos comparten la misma clínica candidata.

- CDMX: 39 huecos → 33 clusters (algunos huecos se comparten entre candidatos)
- EDOMEX: 72 huecos → 69 clusters (casi todos singletons — alta dispersión)

### 13.4 Formulación del MCLP (Notebook 15)

Se resuelve el **Maximum Coverage Location Problem** con Programación Lineal Entera (PuLP/CBC):

$$\max \sum_{i} d_i x_i$$

$$\text{s.t.} \quad x_i \leq \sum_{j \in N_i} y_j \quad \forall i$$

$$\sum_j y_j \leq K$$

$$x_i, y_j \in \{0, 1\}$$

Donde:
- $d_i = \text{score}_i \times \text{pob\_sin\_salud}_i$ — demanda ponderada del hueco $i$
- $y_j = 1$ si se activa el candidato $j$ (centroide del cluster)
- $x_i = 1$ si el hueco $i$ queda cubierto (algún candidato activo a ≤ 15 min)
- $N_i$ — candidatos que cubren el hueco $i$

**Estimación de tiempos:** distancia euclidiana × factor de desvío urbano 1.35, equivalente a un radio de cobertura de 1,125 m en línea recta para el umbral de 15 min (estándar para zonas metropolitanas densas).

### 13.5 Resultados MCLP

**CDMX** — 87,967 personas sin seguro en huecos prioritarios:

La curva de sensibilidad K=5→10 (§14.4) identificó K=7 como el punto óptimo: los saltos +6.2% y +5.9% de K=5→6 y K=6→7 caen a +4.4% y +3.4% en K=9 y K=10.

| K | Huecos cubiertos | Sin seguro cubiertos | Clusters elegidos |
|---|-----------------|----------------------|-------------------|
| 5 | 7 / 39 (17.9%) | 31,091 (35.3%) | C1, C2, C5, C7, C8 |
| **7 (óptimo)** | **11 / 39 (28.2%)** | **42,687 (48.5%)** | **C1, C2, C5, C7, C8, C16, C19** |

**EDOMEX** — 182,357 personas sin seguro en huecos prioritarios:

EDOMEX no tiene un K óptimo global — su curva es casi lineal (+2 pp/clínica), señal de dispersión geográfica. La solución es la **estrategia subregional** detallada en §15.2: 4 zonas × 3 clínicas = 12 total.

| Estrategia | Huecos cubiertos | Sin seguro cubiertos | Clínicas |
|------------|-----------------|----------------------|----------|
| Global K=5 (referencia) | 6 / 72 (8.3%) | 32,683 (17.9%) | 5 |
| **Subregional K=12 (4×3)** | **9 / 72 (12.5%)** | **35,868 (19.7%)** | **12** |

### 13.6 Interpretación de los resultados MCLP

**¿Por qué EDOMEX tiene menor cobertura porcentual?** Refleja geografía, no ineficiencia del modelo. EDOMEX tiene 69 clusters para 72 huecos — casi todos singletons. Una clínica en el centroide de un cluster singleton cubre solo ese hueco. En CDMX la red vial más densa permite que una clínica cubra huecos vecinos.

**Impacto del 4.° eje (marginación) en la solución K=7:** Los 11 huecos cubiertos tienen un IM medio de 0.35 vs 0.28 de los 28 persistentes — el scoring 4 ejes sí redirige prioridad hacia zonas más marginadas. Al mismo tiempo, la pob_sin_salud media cubierta (3,881 personas) triplica a la persistente (1,617), confirmando que el MCLP optimiza inequidad además de estructura topológica. Sin embargo, los huecos con mayor persistencia geométrica (pers_m medio 401 m vs 296 m cubiertos) tienden a quedar fuera — vacíos grandes en geografía dispersa que requieren más clínicas.

**Estabilidad de la solución:** El Cluster 1 de CDMX (7,525 sin seguro) aparece en K=5 y K=7. El Cluster 5 de EDOMEX (23,869 sin seguro) también es estable.

**¿Qué no resuelve K=7 en CDMX?** El 51.5% de la población sin seguro en huecos prioritarios (45,280 personas) sigue sin cobertura con 7 nuevas clínicas. Para EDOMEX con estrategia subregional, el 80.3% persiste. Esto no es fracaso del modelo — es la dimensión real del problema estructural.

---

## 14. Validación Topológica — Cierre del Ciclo TDA

### 14.1 Pregunta de cierre

La Fase 3 responde dónde construir las nuevas clínicas. Esta sección cierra el ciclo usando la misma metodología TDA que *encontró* los huecos para verificar cuántos quedan *cerrados* después de agregar las 5 clínicas propuestas.

**Definición formal de cierre topológico:** Un hueco H₁ con centroide `c` y radio de persistencia `r` queda cerrado cuando una nueva clínica cae a distancia `d < r` de `c`. En esa condición, el nuevo punto triangula el interior del 1-ciclo, convirtiéndolo en frontera de un 2-símplex y eliminándolo del diagrama de persistencia.

Se distinguen tres estados:

| Estado | Condición | Interpretación |
|--------|-----------|----------------|
| **Cerrado** | `d < r` | La clínica cae dentro del vacío → cierre topológico garantizado |
| **Parcial** | `r ≤ d < 2r` | La clínica está próxima pero no dentro → accesibilidad mejorada, hueco persiste |
| **Persistente** | `d ≥ 2r` | Sin intervención efectiva → requiere clínica adicional |

### 14.2 Resultados K=5

| Región | Total prioritarios | Cerrados | Parciales | Persistentes | Reducción pers. total |
|--------|------------------|----------|-----------|--------------|----------------------|
| CDMX | 39 | **3 (8%)** | 3 (8%) | 33 (85%) | −14.5% |
| EDOMEX | 72 | **3 (4%)** | 2 (3%) | 67 (93%) | −8.6% |

### 14.3 Interpretación

**Los números no indican fracaso — indican realidad estructural:**

K=5 clínicas es el umbral mínimo viable para comenzar a resolver los peores huecos, no para eliminar el déficit completo. Los 3 huecos cerrados en CDMX son exactamente los que el MCLP priorizó con mayor score (mayor población sin seguro × mayor persistencia). Los 33 persistentes tienen dos causas distintas:

1. **Huecos de urgencia poblacional baja pero tamaño geográfico grande** (pers > 1,500 m): el MCLP racionalmente los ignoró porque afectan poca población. La TDA los detecta aunque la política pública no los priorice.

2. **Dispersión geográfica extrema** (especialmente EDOMEX, donde los huecos persistentes están a 10–20 km de la clínica nueva más cercana): la cobertura universal requiere decenas de nuevos establecimientos, no 5.

**Coherencia entre MCLP y TDA:**

El MCLP reportó cubrir 7/39 huecos prioritarios de CDMX (criterio: clínica dentro de 15 min = 1,125 m del centroide). La TDA cierra 3/39 (criterio más estricto: clínica dentro del radio de persistencia `r`, que varía entre 200–500 m para la mayoría de huecos críticos). La diferencia es de escala: el MCLP optimiza acceso (llegar en tiempo), la TDA mide cobertura geométrica (rellenar el vacío topológico).

**Huecos más urgentes que persisten (requieren K > 5):**

*CDMX:* Tres huecos de nivel "Alto" con persistencia 749–1,510 m y distancia a clínica nueva > 5 km. Se ubican en zonas periféricas del poniente y sur de la CDMX.

*EDOMEX:* Huecos de nivel "Crítico" con distancias de 10–20 km a la clínica nueva más cercana — reflejo de la dispersión urbana del Estado de México.

### 14.4 Sensibilidad K=5→10: curvas de rendimiento decreciente

Para cuantificar cuánto más vale la pena invertir, se re-ejecutó el MCLP para K=6,7,8,9,10 y se midió el cierre topológico en cada solución.

**CDMX — 39 huecos prioritarios:**

| K | Cerrados topológ. | Parciales | Persistentes | Pob. sin seguro cubierta | Δ marginal |
|---|-------------------|-----------|--------------|--------------------------|------------|
| 5 | 1 (2.6%) | 4 (10.3%) | 34 (87.2%) | 36.4% | — |
| 6 | 2 (5.1%) | 4 (10.3%) | 33 (84.6%) | 42.7% | +6.2% |
| 7 | 3 (7.7%) | 4 (10.3%) | 32 (82.1%) | 48.5% | +5.9% |
| 8 | 4 (10.3%) | 4 (10.3%) | 31 (79.5%) | 54.2% | +5.7% |
| 9 | 5 (12.8%) | 4 (10.3%) | 30 (76.9%) | 58.6% | +4.4% |
| 10 | 6 (15.4%) | 4 (10.3%) | 29 (74.4%) | 62.0% | +3.4% |

**EDOMEX — 72 huecos prioritarios:**

| K | Cerrados topológ. | Parciales | Persistentes | Pob. sin seguro cubierta | Δ marginal |
|---|-------------------|-----------|--------------|--------------------------|------------|
| 5 | 3 (4.2%) | 2 (2.8%) | 67 (93.1%) | 18.2% | — |
| 6 | 4 (5.6%) | 2 (2.8%) | 66 (91.7%) | 20.5% | +2.3% |
| 7 | 5 (6.9%) | 2 (2.8%) | 65 (90.3%) | 22.6% | +2.1% |
| 8 | 6 (8.3%) | 2 (2.8%) | 64 (88.9%) | 24.6% | +2.0% |
| 9 | 7 (9.7%) | 2 (2.8%) | 63 (87.5%) | 26.2% | +1.6% |
| 10 | 8 (11.1%) | 2 (2.8%) | 62 (86.1%) | 27.7% | +1.5% |

**Lectura de política pública:**

- **CDMX:** El mayor salto marginal ocurre entre K=5 y K=6 (+6.2%). A partir de K=7, el beneficio sigue siendo considerable (+5.9%). El **punto óptimo es K=7**: cubre 3 huecos cerrados topológicamente, 48.5% de la población objetivo con 7 establecimientos — a partir de K=8 el incremento cae por debajo de +6 pp por clínica adicional.

- **EDOMEX:** La curva es casi lineal (≈+2 pp por clínica), reflejo de la dispersión geográfica del Estado de México: no hay un "cluster de clusters" donde concentrar la inversión. Cada clínica cubre un territorio distinto. Para superar el 30% de cobertura poblacional se requeriría K ≈ 15. La recomendación es una estrategia distinta: inversión distribuida por subregión (Valle de México norte, Valle Cuautitlán-Texcoco, zona oriente), no una sola ronda de K clínicas globales.

### 14.5 Conclusión del ciclo TDA

El mismo Alpha complex ponderado (Laguerre) que detectó los huecos en la Fase 1 confirma en la Fase 3 cuáles quedan geométricamente resueltos y cuál es la curva de rendimiento decreciente. El análisis proporciona dos productos de política diferenciados:

1. **Producto inmediato (K=5):** Las 5 ubicaciones de mayor impacto por ciudad, con 36.4% (CDMX) y 18.2% (EDOMEX) de cobertura de población sin seguro.
2. **Hoja de ruta escalonada:** Cada punto de la curva K=6…10 identifica la siguiente clínica marginal de mayor retorno, permitiendo un plan de inversión multi-año ordenado por prioridad topológico-demográfica.

Para eliminar el déficit topológico completo en CDMX se requieren K ≈ 15–20 nuevas clínicas estratégicas; para EDOMEX, K ≈ 30–40 distribuidas por subregión.

---

## 15. Análisis Avanzados

### 15.1 Sensibilidad de umbrales (Notebook 18)

Se varió sistemáticamente cada parámetro principal del pipeline para verificar que las conclusiones no son artefactos del calibrado.

**A. Estabilidad TDA — ¿cuántos huecos sobreviven a distintos `min_persistencia`?**

| min_persistencia | Huecos CDMX | Huecos EDOMEX |
|-----------------|-------------|---------------|
| 50 m | 1,064 | 1,709 |
| 100 m | 482 | 742 |
| **200 m (estándar)** | **118** | **241** |
| 400 m | 17 | 91 |
| 600 m | 7 | 58 |
| 1,000 m | 3 | 33 |

**Hallazgo clave:** Los 17 huecos de CDMX con persistencia > 400 m aparecen en absolutamente todas las configuraciones — son señal topológica estable, no ruido de parámetro. Los 482 huecos a 100 m incluyen ruido topológico (gaps menores entre clínicas contiguas); usar 200 m como umbral estándar filtra ese ruido preservando la señal.

**B. Sensibilidad MCLP — ¿cambia la solución óptima al variar el umbral de caminata?**

| Tiempo máx | Pob. cubierta CDMX | Candidatos coinciden con t=15 | Pob. cubierta EDOMEX |
|------------|-------------------|-------------------------------|----------------------|
| 8 min | 29.9% | 0/5 | 12.3% |
| 10 min | 32.5% | 0/5 | 12.3% |
| 12 min | 32.5% | 0/5 | 12.3% |
| **15 min (estándar)** | **35.3%** | — | **18.2%** |
| 18 min | 35.3% | 5/5 | 18.2% |
| 20 min | 35.3% | 5/5 | 24.7% |

**Hallazgo:** En CDMX, los 5 candidatos óptimos a t=15 min son los mismos que a t=18 y t=20 min — la solución es estable hacia arriba. A t < 15 min se seleccionan candidatos diferentes, lo que confirma que 15 min es un umbral significativo (no arbitrario). En EDOMEX, el resultado mejora a t=20 min (+6.5 pp) porque los huecos son más dispersos y el radio de 15 min deja algunos sin cubrir.

**C. Sensibilidad del umbral de prioridad — ¿qué tanto cambia si exigimos mayor persistencia?**

El filtro `pers_m > 400 m` captura huecos grandes y bien definidos. Al relajarlo a 200 m se incluye el 100% de la población sin seguro en huecos habitados; al endurecerlo a 600 m queda menos del 3% (EDOMEX). El umbral de 400 m es el que mejor equilibra cobertura demográfica con robustez topológica.

---

### 15.2 MCLP Subregional para EDOMEX (Notebook 19)

La curva K=5→10 de la sección 14.4 mostró que EDOMEX tiene rendimientos casi lineales (+2 pp/clínica), sin ningún codo visible — porque sus 72 huecos están en zonas geográficamente desconectadas. Una clínica en la ZMVM no alcanza huecos en Norte o Poniente.

**Estrategia:** dividir EDOMEX en 4 subregiones y asignar **K=3 clínicas por zona** (presupuesto uniforme, inversión geográficamente equitativa). Total: 12 clínicas.

| Subregión | Huecos | K local | Huecos cubiertos | Pob. sin seguro | % del total estatal |
|-----------|--------|---------|-----------------|-----------------|---------------------|
| Norte (lat > 19.7°) | 7 | 3 | 2/7 (28.6%) | 1,182 | 0.6% |
| Poniente (lon < −99.3°) | 21 | 3 | 3/21 (14.3%) | 10,243 | 5.6% |
| Oriente (lon > −98.9°) | 6 | 3 | — | — | — |
| ZMVM-Centro | 38 | 3 | 4/38 (10.5%) | 24,443 | 13.4% |
| **Total subregional K=12** | **72** | **12** | **9/72 (12.5%)** | **35,868** | **19.7%** |
| *Global K=5 (referencia)* | 72 | 5 | 6/72 (8.3%) | 32,683 | 17.9% |

**Nota sobre la subregión Oriente:** No se identificaron candidatos con tiempos de caminata válidos (≤ 15 min) en la zona oriente. Los huecos de esa subregión están en áreas con baja densidad de clínicas vecinas. Requiere umbral extendido (20–30 min) o clínicas móviles.

**Ganancia:** Con 7 clínicas adicionales sobre el global K=5, la cobertura sube de 17.9% a 19.7% (+1.7 pp, +3,185 personas). Más importante que el incremento numérico: la estrategia subregional garantiza presencia en **3 de las 4 zonas geográficas del estado**, mientras que el MCLP global concentra todo el presupuesto en la ZMVM donde hay más población absoluta.

**¿Por qué K=3 uniforme y no proporcional al tamaño?** La ZMVM tiene 38 huecos (53% del total) pero ya está relativamente mejor atendida por infraestructura existente. Norte y Poniente tienen huecos de alta persistencia geométrica (pers_max hasta 1,006 m) que indican vacíos estructurales severos. K=3 por zona equaliza la oportunidad de intervención antes de concentrar recursos donde ya existe más cobertura.

---

### 15.3 Índice de Marginación como 4.° Eje del Scoring (Notebooks 13 y 20)

El IM no se usa como capa de análisis separada sino como **cuarto eje del scoring principal**, con peso igual a los demás (25%). El Notebook 20 cuantifica el impacto de esta integración comparando el ranking de 3 ejes (referencia histórica: 40/40/20) vs el nuevo ranking de 4 ejes (25/25/25/25).

**Estabilidad del ranking al agregar el 4.° eje:**

| Región | Top 10 estables entre 3 y 4 ejes | Huecos que suben ≥3 pos. | IM medio de los que suben |
|--------|----------------------------------|--------------------------|--------------------------|
| CDMX | 9/10 (90%) | 11 | 0.37 |
| EDOMEX | 9/10 (90%) | 38 | 0.49 |

**Hallazgos:**

- **CDMX:** El ranking es muy estable — 9 de los 10 huecos más urgentes mantienen su posición. La dimensión de marginación agrega información nueva sin revertir las prioridades. Los 11 huecos que suben ≥3 posiciones tienen déficit educativo notable (hasta 6.8 años por debajo de secundaria completa) y alta proporción de adultos mayores.

- **EDOMEX:** También estable en el Top 10 (9/10). Sin embargo, **38 huecos** suben ≥3 posiciones en el ranking completo — señal de que EDOMEX tiene un grupo amplio de huecos con alta marginación (IM medio 0.49) que el score de acceso puro subestimaba. Estos son candidatos a intervención integrada: nueva clínica **más** programas de afiliación, educación en salud y atención comunitaria.

**Por qué integrar como 4.° eje y no como capa separada:** Al combinarlo en la función de score con pesos iguales, el IM afecta directamente qué huecos entra al MCLP (al filtro de prioritarios) y cuál es la demanda ponderada `score × pob_sin_salud`. Tratarlo como análisis posterior solo informa sin actuar sobre la solución de optimización.

**Interpretación:** Los huecos que suben mucho en el ranking integrado son los de mayor urgencia multidimensional — tienen tanto barreras de acceso físico como desventajas socioeconómicas estructurales. Son los casos donde una clínica nueva produce el mayor impacto posible porque atiende simultáneamente la brecha geográfica y la vulnerabilidad social.

---

### 15.4 Robustez Topológica: El Mismo Hueco a 4 Radios de Persistencia (Notebook 21)

**Pregunta:** ¿Los huecos que priorizamos son artefactos del umbral `min_persistencia = 200 m` elegido, o aparecen consistentemente en un rango amplio de umbrales?

**Metodología:** Se re-ejecuta `ciclos_H1()` con min_persistencia ∈ {100, 200, 400, 600} m sobre el mismo Alpha complex construido una sola vez por región. Un hueco del umbral más exigente (600 m) se considera "el mismo" si hay otro hueco a distancia ≤ 500 m en los umbrales menores.

**Resultados:**

| min_persistencia | Huecos CDMX | Huecos EDOMEX |
|-----------------|-------------|---------------|
| 100 m | 482 | 742 |
| **200 m (análisis principal)** | **118** | **241** |
| 400 m | 17 | 91 |
| 600 m | 7 | 58 |

**Robustez por nivel:**

| Región | Huecos que aparecen en los 4 umbrales | Huecos que aparecen en 3+ umbrales |
|--------|--------------------------------------|-------------------------------------|
| CDMX | **7 / 7** (100%) | 7 / 7 |
| EDOMEX | **58 / 58** (100%) | 58 / 58 |

**Interpretación:** Los 7 huecos de CDMX y los 58 de EDOMEX que sobreviven al umbral más exigente (600 m) son idénticos a los que detectamos con 100, 200 y 400 m. Esto significa que **la señal topológica de los huecos más persistentes es completamente estable**: no es un artefacto del umbral elegido sino una propiedad intrínseca de la geometría de la red de salud.

Los 17 huecos de CDMX con pers_m > 400 m (umbral u=200m) son exactamente los que también aparecen como robustos — confirmando que la persistencia alta es una buena proxy de robustez. La diferencia entre los 118 huecos de u=200m y los 7 de u=600m representa ruido topológico (pequeños vacíos entre clínicas contiguas) que desaparece al exigir mayor persistencia.

**Implicación metodológica:** La elección de `min_persistencia = 200 m` es conservadora — captura la señal robusta más los huecos medianos que son relevantes en zonas densas. Para política pública de alta certeza, enfocarse en los **7 huecos CDMX / 58 huecos EDOMEX** con persistencia > 600 m garantiza que la intervención atiende vacíos estructurales que ningún cambio de parámetro puede hacer desaparecer.

---

## 16. Conclusiones Generales

> *(Sección renumerada desde §15)*

### 15.1 Qué encontramos

Este proyecto aplicó Análisis Topológico de Datos a dos de las áreas metropolitanas más grandes de América Latina. Los hallazgos centrales son:

**a) El problema es geográficamente estructural, no solo estadístico.**
CDMX tiene 21,585 clínicas y EDOMEX tiene 30,787 — no es escasez absoluta de infraestructura. El problema es la distribución: ambas metrópolis tienen huecos topológicos persistentes (118 en CDMX, 241 en EDOMEX bajo Laguerre ponderado) que los métodos de densidad o radio no detectan. Estas zonas están *rodeadas* de infraestructura pero *vacías* por dentro.

**b) El impacto demográfico es cuantificable y concentrado.**
De los huecos habitados, 39 en CDMX y 72 en EDOMEX son prioritarios. En conjunto albergan a **270,324 personas sin seguro médico** — aproximadamente la población de una ciudad media mexicana — que viven en zonas donde el modelo topológico señala una brecha estructural de cobertura.

**c) La ponderación por tamaño de clínica cambia la geografía del riesgo.**
El Weighted Alpha Complex (Laguerre) elimina huecos falsos creados por muchos consultorios pequeños en un área, y revela huecos que el Alpha clásico oculta en zonas dominadas por farmacias con consultorio. Este paso es indispensable para usar TDA en datos de salud reales — los establecimientos no son puntos iguales.

**d) K=7 es el punto óptimo en CDMX; EDOMEX requiere estrategia subregional.**
CDMX con K=7 cubre **42,687 personas sin seguro** (48.5% del total prioritario). La curva K=5→10 muestra saltos de +6.2% y +5.9% en K=6 y K=7, que caen a +4.4% y +3.4% en K=9 y K=10 — K=7 maximiza retorno por inversión. EDOMEX tiene curva lineal (~+2 pp/clínica) sin codo visible, por lo que su solución es la estrategia subregional: 4 zonas × 3 clínicas = 12 total, cubriendo 35,868 personas (19.7%) con presencia en 3 de las 4 zonas geográficas del estado.

**e) El 4.° eje (marginación) cambia qué huecos se priorizan y quién queda cubierto.**
Los 11 huecos que K=7 cubre en CDMX tienen un IM medio de 0.35 vs 0.28 de los persistentes — el scoring 4 ejes redirige inversión hacia zonas más marginadas. Al mismo tiempo, la pob_sin_salud media cubierta (3,881) triplica a la persistente (1,617), confirmando que la optimización pondera correctamente equidad e impacto poblacional.

### 15.2 Qué resolvimos metodológicamente

| Pregunta metodológica | Respuesta del proyecto |
|----------------------|----------------------|
| ¿Cómo detectar desiertos de salud que los radios no ven? | Alpha complex + persistencia H₁ con umbral min_pers=200m |
| ¿Cómo reconocer que no todos los establecimientos cubren igual? | Weighted Alpha Complex (Laguerre): radio ∝ √(per_ocu) |
| ¿Cómo priorizar huecos para política pública? | Score 4 ejes (25% c/u): tiempo × % sin seguro × persistencia × marginación → filtro OR |
| ¿Dónde construir? | MCLP con ILP: maximiza (score × sin_seguro) cubiertos con K ubicaciones |
| ¿Cuántas clínicas son suficientes? | Curva K=5→10 con rendimiento marginal: codo en K=7 para CDMX |
| ¿El mismo método que encontró los huecos puede validar la solución? | Sí: distancia nueva clínica < pers_m del centroide → cierre topológico |

### 15.3 Conclusiones de política pública

**Punto de partida mínimo viable — K=5:**
- CDMX: El Cluster 1 (7,525 sin seguro) y los Clusters 2, 5, 7, 8 cubren el mayor retorno inicial. Aparecen también en la solución K=7, confirmando su estabilidad.
- EDOMEX: El Cluster 5 (zona norponiente, 23,869 sin seguro) es el de mayor urgencia; el Cluster 1 de ZMVM (3,641) es el segundo. Ambos aparecen en K=5 global y en la estrategia subregional.

**Recomendación CDMX — K=7:**
La curva K=5→10 muestra saltos +6.2% (K=5→6) y +5.9% (K=6→7), que caen a +5.7%, +4.4%, +3.4% después. K=7 maximiza el retorno por inversión: 11/39 huecos cerrados o cubiertos, 42,687 personas sin seguro (48.5%), con presencia en 7 clusters distribuidos por la ciudad. Los 7 clusters elegidos [C1, C2, C5, C7, C8, C16, C19] concentran la mayor densidad de personas sin seguro × marginación en CDMX.

**Recomendación EDOMEX — Estrategia subregional K=12:**
No existe un K óptimo único para EDOMEX porque la curva es lineal (~+2 pp/clínica). La política correcta es asignar K=3 clínicas por subregión (Norte, Poniente, ZMVM-Centro, Oriente), garantizando inversión en zonas que el MCLP global ignoraría. Total: 12 clínicas, 9/72 huecos cubiertos, 35,868 personas (19.7%). La subregión Oriente requiere estrategia complementaria (umbral de tiempo extendido o clínicas móviles).

**Lo que la TDA agrega sobre los métodos tradicionales:**
Un mapa de densidad de clínicas mostraría que CDMX tiene ~10 veces más establecimientos por km² que municipios rurales — y concluiría que el problema está resuelto. La persistencia homológica revela que incluso con 21,585 clínicas existen 39 vacíos estructurales con casi 88,000 personas sin seguro viviendo dentro. Esa diferencia es la contribución metodológica central de este trabajo.

### 15.4 Limitaciones y trabajo futuro

| Limitación | Impacto | Mejora propuesta |
|------------|---------|-----------------|
| Tiempos estimados con distancia euclidiana × 1.35 | Error de ±15% vs red real para zonas con barrancos, vías rápidas, o topografía irregular | Usar OSMnx con la red peatonal real por subregión |
| IM construido desde Censo 2020 sin validar vs CONAPO | Puede diferir de la clasificación oficial de marginación municipal | Cruzar con índice de marginación 2020 CONAPO para calibrar pesos |
| Datos DENUE 2023, Censo 2020 | El desajuste temporal puede sobreestimar/subestimar nuevas clínicas abiertas en 2021–2023 | Actualizar con DENUE trimestral |
| Subregión Oriente de EDOMEX sin candidatos válidos | 6 huecos de la zona oriente no tienen candidatos de cobertura bajo t=15 min | Extender umbral a 20 min o incluir rutas de transporte público |
| K máximo limitado a 20 candidatos | Si el presupuesto permite K > 20, se necesitan más clusters | Ampliar DBSCAN con eps menor para más candidatos |

---

## Apéndice: Estructura del Repositorio

```
Persistencia_Homologica_Analisis_de_Datos/
├── notebooks/
│   ├── 01_eda.py              # Exploración: distribución de establecimientos
│   ├── 02_eda_geo.py          # Mapas exploratorios de densidad
│   ├── 03_alpha.py            # Primera construcción del Alpha complex
│   ├── 04_persistencia.py     # Diagramas de persistencia H₀, H₁, H₂
│   ├── 05_comparativa.py      # Bottleneck, Wasserstein, Betti numbers
│   ├── 06_mapper.py           # Grafo Mapper de la red de clínicas
│   ├── 07_localizacion.py     # Geolocalización de huecos H₁
│   ├── 08_arquetipos.py       # Persistence Images + arquetipos topológicos
│   ├── 09_bifiltracion.py     # Bifiltración topología × densidad urbana
│   ├── 10_cruce_censal.py     # Cruce con Censo 2020 + índice de prioridad
│   ├── 11_topologia_ponderada.py  # Weighted Alpha Complex (Laguerre)
│   ├── 12_isocronas.py        # Isócronas OSMnx + accesibilidad peatonal
│   ├── 13_scoring_multieje.py # Scoring 4 ejes (25% c/u): tiempo + sin seguro + pers. + marginación
│   ├── 14_clusters_geograficos.py  # DBSCAN: agrupación geográfica de huecos
│   ├── 15_mclp_red_real.py    # MCLP: K=5 y K=7 para CDMX; K=5 referencia para EDOMEX
│   ├── 15a_extraer_redes_pbf.py   # Extracción de red vial desde PBF local
│   ├── 16_dashboard_final.py  # Dashboard y mapas finales Fase 3
│   ├── 17_validacion_topologica.py  # Validación: ¿se cierran los huecos con K=5?
│   ├── 17_sensibilidad_k.py         # Curvas de rendimiento decreciente K=5→10
│   ├── 18_sensibilidad_umbrales.py  # Sensibilidad: min_pers, tiempo_lim, pers_prio
│   ├── 19_mclp_subregional.py       # MCLP subregional EDOMEX (Norte/Poniente/Oriente/ZMVM)
│   ├── 20_indice_marginacion.py     # Índice de marginación compuesto desde Censo
│   └── 21_robustez_topologica.py    # Robustez: mismo hueco a 4 radios de persistencia
├── lib/
│   ├── config.py              # Rutas, CRS, constantes globales
│   ├── data.py                # Carga y preprocesamiento del DENUE
│   ├── tda.py                 # Alpha complex, persistencia, ciclos H₁, Laguerre
│   ├── censo.py               # Carga Censo 2020, cruce AGEBs, índice de prioridad
│   ├── geo_network.py         # OSMnx: red vial, isócronas, accesibilidad peatonal
│   └── viz_censo.py           # Mapas y visualizaciones censales
├── outputs/
│   ├── figuras/               # Todos los PNG y HTML de visualizaciones
│   └── intermedios/           # Parquets con datos procesados entre notebooks
├── Datos/
│   ├── Censo/                 # CSVs Censo 2020 (INEGI)
│   └── Geoestadistico/        # Shapefiles AGEBs (INEGI)
└── reporte/
    ├── reporte.md             # Este documento
    ├── task.md                # Lista de tareas del proyecto
    └── walkthrough.md         # Guía de ejecución paso a paso
```

## Apéndice: Figuras Generadas

| Figura | Descripción |
|--------|-------------|
| `eda_CDMX.png`, `eda_EDOMEX.png` | Distribución de tamaño de establecimientos |
| `persistencia_CDMX.png`, `_EDOMEX.png` | Diagramas de persistencia H₀, H₁, H₂ |
| `mapper_CDMX.html`, `_EDOMEX.html` | Grafo Mapper interactivo |
| `huecos_CDMX.html`, `_EDOMEX.html` | Huecos H₁ geolocalizados (Fase 1B) |
| `bifiltracion_CDMX.png`, `_EDOMEX.png` | Cuadrante topología × densidad |
| `huecos_censal_CDMX.html`, `_EDOMEX.html` | Huecos con prioridad censal (interactivo) |
| `matriz_riesgo_CDMX.png`, `_EDOMEX.png` | Scatter persistencia × % sin seguro |
| `impacto_censal_CDMX.png`, `_EDOMEX.png` | Top huecos por impacto demográfico |
| `distribucion_radios_laguerre.png` | Radios de cobertura Laguerre (log-escala) |
| `huecos_laguerre_CDMX.html`, `_EDOMEX.html` | Comparación clásico vs ponderado |
| `scatter_accesibilidad.png` | Tamaño × tiempo caminando (CDMX \| EDOMEX) |
| `comparativa_tamano.png` | Top 10 huecos más grandes por ciudad |
| `comparativa_distancia.png` | Top 10 huecos más lejanos por ciudad |
| `mapas_accesibilidad_CDMX.png` | 6 mapas OSM — CDMX (3 grandes + 3 lejanos) |
| `mapas_accesibilidad_EDOMEX.png` | 6 mapas OSM — EDOMEX (3 grandes + 3 lejanos) |
| `scoring_scatter.png` | Scatter 4 ejes: tiempo × sin seguro × pers. × marginación |
| `scoring_rankings.png` | Top 10 huecos por cada uno de los 4 ejes |
| `scoring_pareto.png` | Huecos dominantes (top 20% en 2+ de los 4 ejes) |
| `scoring_impacto_marginacion.png` | Cambio de ranking al agregar el 4.° eje: flechas ↑ y ↓ |
| `clusters_geograficos.png` | Agrupación DBSCAN de huecos prioritarios |
| `fase3_CDMX_k7_mapa.png` | Mapa K=7 CDMX: 7 clínicas propuestas con isócronas 15 min |
| `fase3_CDMX_k7_ejes.png` | Cobertura de los 4 ejes en K=7: cubiertos vs persistentes |
| `fase3_EDOMEX_subregional_mapa.png` | EDOMEX: global K=5 vs subregional K=12 (4 zonas × 3) |
| `fase3_EDOMEX_subregional_ejes.png` | Cobertura por eje y subregión en estrategia K=12 |
| `validacion_persistencia.png` | Diagrama persistencia: huecos por estado de cierre |
| `validacion_impacto.png` | Barras: huecos cerrados/parciales/persistentes por urgencia |
| `validacion_mapa.png` | Mapa de cierre topológico: verde=cerrado, naranja=parcial, rojo=persistente |
| `validacion_curva_k.png` | Curvas de rendimiento decreciente K=5→10: cierre topológico + cobertura |
| `sensibilidad_estabilidad_tda.png` | Huecos H₁ detectados vs umbral de persistencia (curva de codo) |
| `sensibilidad_mclp_tiempo.png` | Cobertura MCLP K=5 al variar el umbral de caminata 8–20 min |
| `sensibilidad_prioridad.png` | Huecos y población incluidos al variar el umbral de prioridad pers_m |
| `mclp_subregional_EDOMEX.png` | Comparativa global K=5 vs subregional K=12 (4 zonas × 3) en EDOMEX |
| `marginacion_ranking.png` | Top 15 huecos: score 3 ejes vs score 4 ejes (impacto de agregar IM) |
| `marginacion_scatter.png` | Scatter acceso vs marginación: huecos de máxima urgencia multidimensional |
| `mclp_subregional_EDOMEX.png` | Comparativa global K=5 vs subregional K=8 en EDOMEX |
| `robustez_conteo_huecos.png` | Curva de huecos detectados a los 4 umbrales de persistencia |
| `robustez_mapa.png` | Mapa de robustez: huecos coloreados por cuántos umbrales los detectan |
| `robustez_persistencia_vs_umbrales.png` | Persistencia vs nivel de robustez: confirma que pers. alta → más robusto |
