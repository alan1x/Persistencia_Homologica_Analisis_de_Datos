# Proyecto: Análisis de Datos Económicos Geolocalizados con Persistencia Homológica

Análisis topológico de datos (TDA) sobre el DENUE (INEGI) para el sector
**salud (SCIAN 62)**, comparando **CDMX vs EDOMEX**.

---

## Objetivos (enunciado original)

1. **Limpieza y preprocesamiento** + visualización descriptiva inicial.
2. **Construcción de complejos simpliciales** (Čech / Vietoris-Rips) para explorar
   conectividad según distancias. Librerías: Ripser, Gudhi, Persim, kmapper.
3. **Persistencia homológica**: identificar características persistentes
   (componentes conexas, agujeros, cavidades); diagramas de barras y dispersión;
   interpretar con la cobertura y conectividad de las unidades económicas.
4. **Conclusiones y discusión**: hallazgos e implicaciones para planeación urbana,
   distribución de recursos y decisiones estratégicas.

**Addons:** usar los datos en `../Datos/` (CDMX y EDOMEX, análisis en paralelo
para ver diferencias) y aplicar las investigaciones propias en
`../Recursos/Investigaciones_Propias` (Grupos de Homología, Mapper,
Alpha Complexes / Voronoi).

---

## Estado: qué se hizo

### Decisiones
- **Sector:** SCIAN 62 (salud y asistencia social) — coincide con `clusteres_tda_salud_cdmx.pptx`.
- **Método:** **Alpha complex (Gudhi)** — escala a decenas de miles de puntos en 2D
  (Rips inviable sobre el conjunto completo; solo se usa en submuestra didáctica).
- **Entrega:** notebooks + reporte.

### 1. Limpieza y EDA — hecho
Pipeline `lib/data.py`: carga Latin-1 → filtro SCIAN 62 → limpieza de coordenadas
(nulas, fuera de bounding box, duplicados) → proyección a metros (UTM 14N).
EDA `lib/eda.py`: mapa de dispersión, top municipios, personal ocupado.

| Región | Unidades DENUE | Salud limpias | Municipios |
|--------|----------------|---------------|------------|
| CDMX   | ~460,000       | **21,585**    | 16         |
| EDOMEX | ~816,000       | **30,787**    | 125        |

### 2. Complejos simpliciales — hecho
`lib/tda.py`: Alpha complex (~105k–150k símplices, <0.2 s) + Vietoris-Rips sobre
submuestra para contraste. Liga investigación **Alpha_Complexes_Voronoi**
(Alpha = Čech restringido a Delaunay/Voronoi).

### 3. Persistencia homológica — hecho
`lib/viz_tda.py`: diagramas, barcodes, curvas de Betti, distancias entre regiones.
Interpretación (liga **Grupos_Homologia**):
- **H₀** componentes → fragmentación/accesibilidad (CDMX se conecta antes que EDOMEX).
- **H₁** huecos → zonas sin cobertura de salud (top ≈ 1.5 km de radio).
- **H₂** ≈ 0 (datos planos, esperado).

Comparación H₁ (persistencia ≥ 200 m): CDMX **71** vs EDOMEX **209** huecos;
bottleneck **≈5.9 km**, Wasserstein **≈87 km** → EDOMEX mucho más disperso.

### 3b. Mapper — hecho
`lib/mapper_viz.py` (liga investigación **Mapper**): CDMX 226 nodos/520 aristas,
EDOMEX 983/1213 → EDOMEX más fragmentado.

### 4. Conclusiones — hecho
`reporte/trabajo_final.md` + `notebooks/05_conclusiones`. Implicaciones: huecos H₁ de
gran radio en EDOMEX = zonas mal cubiertas, candidatas a nuevas unidades de salud.

---

## Estructura
```
src/
  lib/         config, data, eda, tda, viz_tda, mapper_viz
  notebooks/   01_limpieza_eda … 05_conclusiones (.py percent + .ipynb)
  outputs/     intermedios/ (parquet) · figuras/ (PNG + HTML Mapper)
  reporte/     trabajo_final.md
```
Setup y ejecución: ver `README.md` (entorno con `uv`, py3.12).

## Trabajo futuro
- Cruzar huecos H₁ con densidad poblacional (censo) → separar "hueco real" de
  "zona despoblada".
- Ponderar coordenadas apiladas (mismo edificio).
- Extender a otros sectores SCIAN.
