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

## 5. Conclusiones e implicaciones

- **Planeación urbana / salud:** los huecos H₁ de gran radio en EDOMEX identifican
  zonas habitadas mal cubiertas, candidatas a nuevas unidades.
- **Distribución de recursos:** la escala de fusión de H₀ mide accesibilidad
  entre servicios.
- **Decisiones estratégicas:** las distancias entre diagramas dan una métrica
  objetiva y reproducible para comparar regiones o evolución temporal.

**Trabajo futuro:** ponderar coords apiladas; cruzar huecos con densidad
poblacional (censo) para separar "hueco real" de "zona despoblada"; extender a
otros sectores SCIAN.
