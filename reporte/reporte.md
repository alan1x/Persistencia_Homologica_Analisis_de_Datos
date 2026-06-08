# Análisis de Datos Económicos Geolocalizados con Persistencia Homológica

**Sector:** SCIAN 62 — Servicios de salud y asistencia social
**Regiones:** Ciudad de México (CDMX) vs Estado de México (EDOMEX)
**Fuente:** DENUE (INEGI)

---

## 1. Datos y preprocesamiento

| Región | Unidades totales (DENUE) | Unidades de salud limpias | Municipios |
|--------|--------------------------|---------------------------|------------|
| CDMX   | ~460,000                 | **21,585**                | 16         |
| EDOMEX | ~816,000                 | **30,787**                | 125        |

Pipeline (`lib/data.py`): carga Latin-1 → filtro SCIAN 62 → limpieza de
coordenadas (nulas, fuera de bounding box, duplicados) → proyección a metros
(UTM 14N, EPSG:32614). Dominan consultorios dentales y de medicina general,
mayoritariamente de 0–5 personas (`outputs/figuras/eda_*.png`).

## 2. Complejos simpliciales

Por el volumen se usa **Alpha complex** (Gudhi): subcomplejo de Delaunay, exacto
y eficiente en 2D, equivalente al Čech restringido a la teselación de
Voronoi/Delaunay (investigación *Alpha_Complexes_Voronoi*). Filtración α = radio²
del circuncentro; escala física radio = √α (m). Construcción de ~21k–31k puntos
en **<0.2 s** (~105k–150k símplices). Vietoris-Rips solo es viable sobre
submuestra (contraste didáctico).

## 3. Persistencia homológica

Interpretación (investigación *Grupos_Homologia*):

- **H₀ (componentes):** CDMX ≈ 17,596 componentes iniciales que se fusionan a
  radios menores que EDOMEX → mayor densidad / accesibilidad en CDMX.
- **H₁ (huecos = zonas sin cobertura):** los ciclos persistentes marcan zonas
  rodeadas de servicios pero vacías por dentro. β₁ máximo ≈ radio 150 m.
- **H₂:** ≈ 0 (datos planos, esperado).

**Comparación CDMX vs EDOMEX (H₁, persistencia ≥ 200 m):**

| Métrica            | Valor      |
|--------------------|------------|
| Huecos persistentes CDMX   | 71  |
| Huecos persistentes EDOMEX | 209 |
| Distancia bottleneck       | ~5,904 m |
| Distancia Wasserstein      | ~87,278 m |

EDOMEX tiene ~3× más huecos persistentes y de mayor radio → cobertura de salud
más dispersa y discontinua. (`outputs/figuras/persistencia_*.png`)

## 4. Mapper

Red de clusters (investigación *Mapper*), lens = coordenadas, DBSCAN, color =
personal ocupado:

| Región | Nodos | Aristas |
|--------|-------|---------|
| CDMX   | 226   | 520     |
| EDOMEX | 983   | 1,213   |

EDOMEX = grafo más fragmentado → confirma la lectura de la persistencia.
(`outputs/figuras/mapper_*.html`)

## 5. Geolocalización de huecos H₁ (Mejora 1)

La persistencia homológica identifica huecos abstractos en el diagrama de nacimiento/muerte, pero para que sean accionables en política pública necesitamos saber **dónde están en el mapa**. Usando los pares de persistencia del Alpha complex se extrae el centroide de cada triángulo de muerte y se proyecta de vuelta a coordenadas WGS84, generando círculos geolocalizados cuyo radio es proporcional a la persistencia.

Resultado: mapas interactivos HTML (`outputs/figuras/huecos_CDMX.html` y `huecos_EDOMEX.html`) donde cada círculo rojo es una zona sin cobertura de salud. Click en cualquier círculo muestra birth, death y persistencia en metros.

| Región | Huecos geolocalizados (≥200 m) | Peor hueco |
|--------|-------------------------------|------------|
| CDMX   | 71                            | 1,510 m persistencia |
| EDOMEX | 209                           | 11,808 m persistencia (~6 km radio) |

## 6. Vectorización y clasificación topológica (Mejoras 2 y 2b)

### 6.1 Persistence Images

Para comparar regiones cuantitativamente se convierte cada diagrama H₁ en un vector de longitud fija mediante **Persistence Images** (persim): cada hueco aporta una gaussiana centrada en su posición (birth, persistencia) sobre un grid compartido. Esto permite similitud coseno, clustering y PCA sobre cualquier número de estados.

Trabajando solo con los huecos significativos (≥ 200 m) se obtiene:

| Par | Similitud coseno | Distancia coseno |
|-----|-----------------|-----------------|
| CDMX ↔ EDOMEX | 0.635 | 0.365 |

Una distancia de 0.365 sobre 1.0 posible indica estructuras topológicas **notablemente distintas**. Con el conjunto completo de 32 estados este vector permite producir un dendrograma de similitud de cobertura de salud sin supervisión.

### 6.2 Arquetipos topológicos

Los huecos H₁ se clasifican en cuatro arquetipos según su posición en el plano (birth, persistencia), usando umbrales calculados sobre el conjunto combinado de regiones (birth = 0.55 km, persistencia = 0.30 km, crítico ≥ 3 km):

| Arquetipo | Significado | CDMX | EDOMEX |
|-----------|-------------|------|--------|
| **[1] Enclave sin cobertura** | birth bajo, pers alta — rodeado de servicios pero vacío interior | 23 | 27 |
| **[2] Desierto estructural** | birth alto, pers alta — zona rural sin infraestructura | **6** | **84** |
| **[3] Vacío periférico** | birth alto, pers baja — transición urbano-rural | 6 | 44 |
| **[4] Micro-brecha** | birth bajo, pers baja — ruido urbano normal | 36 | 54 |

La diferencia crítica: EDOMEX tiene **14× más desiertos estructurales** que CDMX, con persistencia máxima de 11.81 km vs 1.46 km. La curva de Betti β₁ muestra que el pico de EDOMEX es más tardío (huecos activos a escalas mayores) y más pronunciado.

**Implicación para acción:**
- *Enclaves sin cobertura* (prioridad 1): la infraestructura circundante ya existe — un nuevo consultorio dentro del hueco resuelve el problema.
- *Desiertos estructurales* (prioridad 2): requieren inversión estructural desde cero; son los huecos de mayor radio en EDOMEX.

## 7. Bifiltración: persistencia × densidad (Mejora 3)

La clasificación del notebook 08 identifica los arquetipos topológicos, pero no distingue entre una zona sin cobertura con alta demanda poblacional y una simplemente despoblada. Agregamos una segunda dimensión de filtración: la **densidad local de actividad económica** (KDE gaussiano 2D sobre las coordenadas UTM de las unidades DENUE), que sirve como proxy de densidad urbana/poblacional.

### Método

Para cada hueco H₁ con persistencia ≥ 200 m:
1. Se evalúa el KDE (ajustado con Scott's rule) en el centroide del hueco.
2. Se cruza con la persistencia usando umbrales: persistencia ≥ 500 m y densidad ≥ percentil 50.
3. El hueco queda en uno de cuatro cuadrantes accionables.

### Resultados

| Categoría | CDMX | EDOMEX |
|-----------|------|--------|
| **[1] CRÍTICO: zona densa sin cobertura** | **0** | **16** |
| **[2] Alerta: zona activa con hueco grande** | 9 | 52 |
| [3] Moderado: zona densa, hueco menor | 36 | 89 |
| [4] Bajo: zona rural/dispersa | 26 | 52 |

La bifiltración reduce los 209 huecos abstractos de EDOMEX a **16 críticos** y **52 de alerta** con candidatos concretos para nuevas unidades de salud. CDMX tiene 0 huecos en categoría crítica — sus brechas son moderadas y en zonas con actividad.

El hueco más crítico de EDOMEX combina persistencia de **4.25 km** con densidad alta: zona urbana con muchas unidades económicas circundantes pero sin servicio de salud dentro del hueco.

(`outputs/figuras/bifiltracion_CDMX.png` y `bifiltracion_EDOMEX.png`)

## 8. Conclusiones e implicaciones

- **Planeación urbana / salud:** los huecos H₁ de gran radio en EDOMEX identifican
  zonas habitadas mal cubiertas, candidatas a nuevas unidades.
- **Distribución de recursos:** la escala de fusión de H₀ mide accesibilidad
  entre servicios.
- **Decisiones estratégicas:** las distancias entre diagramas dan una métrica
  objetiva y reproducible para comparar regiones o evolución temporal.

**Trabajo futuro:** ponderar coords apiladas; cruzar huecos con densidad
poblacional (censo) para separar "hueco real" de "zona despoblada"; extender a
otros sectores SCIAN.
