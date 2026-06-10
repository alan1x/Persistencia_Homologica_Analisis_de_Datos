// Presentación — Persistencia Homológica para Detectar Desiertos de Salud
// Compilar:  typst compile --root . presentacion/presentacion.typ presentacion/presentacion.pdf

#let azul       = rgb("#1f4e79")
#let azul-claro = rgb("#2e75b6")
#let gris       = rgb("#333333")
#let rojo       = rgb("#b2182b")
#let verde      = rgb("#1b7837")
#let naranja    = rgb("#e08214")
#let FIG        = "/outputs/figuras/"

#set page(
  paper: "presentation-16-9",
  fill: white,
  margin: (top: 1.1cm, bottom: 0.9cm, x: 1.3cm),
  footer: context {
    set text(size: 9pt, fill: azul-claro)
    grid(columns: (1fr, auto), align: (left, right),
      [Desiertos de Salud · Análisis Topológico de Datos],
      [#counter(page).display()],
    )
  },
)
#set text(font: ("Segoe UI", "Arial"), size: 15pt, fill: gris, lang: "es")
#set par(justify: false, leading: 0.55em)

// ── helpers ─────────────────────────────────────────────────────────────────
#let kpi(x) = text(fill: azul,     weight: "bold")[#x]
#let kred(x) = text(fill: rojo,    weight: "bold")[#x]
#let kver(x) = text(fill: verde,   weight: "bold")[#x]
#let knar(x) = text(fill: naranja, weight: "bold")[#x]

#let header(title) = {
  text(size: 22pt, weight: "bold", fill: azul)[#title]
  v(-3pt)
  line(length: 100%, stroke: 1.4pt + azul-claro)
}

#let slide(title, body) = {
  pagebreak(weak: true)
  header(title)
  v(7pt)
  body
}

// Figura protagonista — una imagen, llena la altura disponible
#let figslide(title, caption, img) = {
  pagebreak(weak: true)
  block(height: 100%, width: 100%, grid(
    rows: (auto, auto, 1fr),
    row-gutter: 6pt,
    header(title),
    if caption != none { set text(size: 14pt); caption } else { [] },
    align(center, image(FIG + img, width: 100%, height: 100%, fit: "contain")),
  ))
}

// Figura protagonista — dos imágenes lado a lado, altura limitada a la página
#let figslide2(title, caption, img1, img2) = {
  pagebreak(weak: true)
  block(height: 100%, width: 100%, grid(
    rows: if caption != none { (auto, auto, 1fr) } else { (auto, 1fr) },
    row-gutter: 6pt,
    header(title),
    ..if caption != none { ({ set text(size: 13.5pt); caption },) } else { () },
    grid(
      columns: (1fr, 1fr),
      column-gutter: 8pt,
      rows: 100%,
      align: center + horizon,
      image(FIG + img1, width: 100%, height: 100%, fit: "contain"),
      image(FIG + img2, width: 100%, height: 100%, fit: "contain"),
    ),
  ))
}

// Texto izquierda + figura derecha (figura llena la altura)
#let splitslide(title, body, fig, ratio: 48%) = {
  pagebreak(weak: true)
  block(height: 100%, width: 100%, grid(
    rows: (auto, 1fr),
    row-gutter: 8pt,
    header(title),
    grid(
      columns: (1fr, ratio),
      column-gutter: 16pt,
      rows: 100%,
      align: (left + top, center + horizon),
      body,
      image(FIG + fig, width: 100%, height: 100%, fit: "contain"),
    ),
  ))
}

// Texto izquierda + dos figuras apiladas derecha (altura limitada)
#let splitslide2(title, body, fig1, fig2, ratio: 50%) = {
  pagebreak(weak: true)
  block(height: 100%, width: 100%, grid(
    rows: (auto, 1fr),
    row-gutter: 8pt,
    header(title),
    grid(
      columns: (1fr, ratio),
      column-gutter: 16pt,
      rows: 100%,
      align: (left + top, center + horizon),
      body,
      grid(
        rows: (1fr, 1fr),
        row-gutter: 6pt,
        image(FIG + fig1, width: 100%, height: 100%, fit: "contain"),
        image(FIG + fig2, width: 100%, height: 100%, fit: "contain"),
      ),
    ),
  ))
}

#let big(n, label) = align(center, block[
  #text(size: 44pt, weight: "bold", fill: azul)[#n]
  #v(-7pt)
  #text(size: 14pt, fill: azul-claro)[#label]
])

#let th(x) = text(fill: white, weight: "bold", size: 12pt)[#x]
#let tf = (_, row) => if row == 0 { azul } else if calc.odd(row) { rgb("#eaf1f8") } else { white }

#let nota(body) = block(
  fill: rgb("#e8f2fa"), stroke: 0.8pt + azul-claro,
  inset: 8pt, radius: 4pt, width: 100%,
)[#set text(size: 13pt); #body]


// ===========================================================================
// 1. PORTADA
// ===========================================================================
#align(center + horizon, block[
  #text(size: 34pt, weight: "bold", fill: azul)[
    Persistencia Homológica para\ Focos de Salud
  ]
  #v(8pt)
  #text(size: 19pt, fill: azul-claro)[Ciudad de México y Estado de México]
  #v(20pt)
  #line(length: 45%, stroke: 1pt + azul-claro)
  #v(12pt)
  #text(size: 13pt, fill: gris)[
    Análisis Topológico de Datos · DENUE 2023 · Censo 2020 · OpenStreetMap
  ]
  #v(6pt)
  #text(size: 13pt, fill: gris)[
    Mario Carlos Gaitán · Rodrigo Jiménez · Andrés Kiewek\
    Juan Pablo Moral · Luis Alan Morales
  ]
])


// ===========================================================================
// 2. EL PROBLEMA
// ===========================================================================
#slide("El problema: desiertos que los mapas no ven")[
  #grid(columns: (1.2fr, 1fr), column-gutter: 28pt, align: (left + top, center + horizon),
    [
      - *52,372 clínicas* entre CDMX y EDOMEX: no hay escasez absoluta.
      - Las métricas tradicionales son ciegas al vacío estructural:
        - Densidad de clínicas por km² ✗  · Radio de 500 m ✗  · Conteo por municipio ✗
      #v(6pt)
      - *Desierto estructural*: zona rodeada de clínicas por fuera, vacía por dentro. Una persona adentro puede estar a 2 km aunque el mapa se vea «verde».
      #v(10pt)
      #text(fill: azul, weight: "bold", size: 16pt)[
        ¿Dónde están esos desiertos, cuánta población atrapan y cómo priorizamos la inversión?
      ]
    ],
    [
      #big("270k", "personas sin seguro en desiertos topológicos")
      #v(12pt)
      #big("≥ 2 km", "a la clínica más cercana en colonias aparentemente cubiertas")
    ],
  )
]


// ===========================================================================
// 3. PIPELINE
// ===========================================================================
#slide("Pipeline metodológico — seis etapas integradas")[
  #table(
    columns: (auto, 1fr, auto),
    stroke: none, inset: (x: 10pt, y: 7pt),
    fill: (_, row) => if calc.odd(row) { rgb("#eaf1f8") } else { white },
    [#kpi[① DATOS]],      [DENUE 2023 (SCIAN 62) + Censo 2020 (AGEBs) + OpenStreetMap],  [21 k / 30 k estab.],
    [#kpi[② TDA]],        [Alpha Complex ponderado (Laguerre) · persist. > 200 m],         [118 / 241 huecos H₁],
    [#kpi[③ CENSO]],      [AGEBs habitadas · PSINDER · Índice de Marginación],             [62/180 · ~270 k sin seguro],
    [#kpi[④ RED VIAL]],   [Red peatonal real 4.5 km/h · isócronas · umbral 15 min],       [Tiempos por hueco],
    [#kpi[⑤ SCORING]],    [Score 4 ejes (percentiles) · filtro OR · DBSCAN · MCLP/PuLP],  [46 / 77 prioritarios],
    [#kpi[⑥ VALIDACIÓN]], [Cierre topológico · robustez 4 umbrales],                       [−14.9% / −16.5%],
  )
  #v(14pt)
  #nota[
    *Resultado*: K=7 clínicas en CDMX → #kpi[42,687 personas] (44.0%) · 9 ubicables en EDOMEX → #kpi[35,868 personas] (19.0%)
  ]
]


// ===========================================================================
// 4. LOS DATOS: DENUE 2023
// ===========================================================================
#splitslide2("Los datos: DENUE 2023 — Establecimientos de Salud",
  [
    - Sector *SCIAN 62*: salud y asistencia social
    - CDMX: *21,585 estab.*  ·  EDOMEX: *30,787 estab.*
    #v(6pt)
    *Variable clave — PER_OCU*: personas ocupadas. Convierte rangos de texto a capacidad de cobertura real.
    #v(6pt)
    #table(
      columns: (1fr, auto),
      stroke: none, inset: 6pt, fill: tf,
      [#th[Estrato]], [#th[Tipo de establecimiento]],
      [0–5 pers.],   [Micro-consultorio / farmacia],
      [6–30 pers.],  [Clínica de barrio],
      [31–300 pers.],[Clínica IMSS / ISSSTE],
      [> 300 pers.], [Hospital general],
    )
    #v(6pt)
    #nota[La *mayoría* son micro-estab. Los hospitales son minoría pero con radio 5–10× mayor.]
  ],
  "eda_CDMX.png",
  "eda_EDOMEX.png",
  ratio: 54%,
)


// ===========================================================================
// 5. LOS DATOS: CENSO 2020
// ===========================================================================
#splitslide("Los datos: Censo 2020 — AGEBs urbanas",
  [
    El *AGEB urbana* es la unidad geoespacial mínima (~manzanas). Permite cruzar cada hueco topológico con la población real que lo habita.
    #v(8pt)
    #table(
      columns: (auto, auto, 1fr),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Variable]], [#th[Peso IM]], [#th[Qué mide]],
      [PSINDER],  [35%], [Personas sin derechohabiencia],
      [GRAPROES], [25%], [Grado promedio de escolaridad],
      [P60YMAS],  [25%], [Población de 60 años y más],
      [POBTOT],   [15%], [Densidad de personas sin seguro],
    )
    #v(8pt)
    #nota[*PSINDER = variable crítica*: sin seguro = sin alternativa cuando la clínica está lejos. #kred[270,000 personas] en esa situación.]
  ],
  "matriz_riesgo_CDMX.png",
  ratio: 48%,
)


// ===========================================================================
// 6. TDA: ALPHA COMPLEX — EL PROCESO
// ===========================================================================
#figslide("TDA — Cómo construimos los huecos: Alpha Complex paso a paso",
  [
    *1.* Cada clínica = punto. *2.* Radio $alpha$ crece → aristas → triángulos → *Alpha Complex*.
    *3.* Un *hueco H₁* = ciclo cerrado que rodea un vacío que nunca se rellena.
    *4.* *Persistencia = radio_muerte − radio_nacimiento* (m): cuánto «dura» el vacío.
  ],
  "vectorizacion.png",
)


// ===========================================================================
// 7. TDA: DIAGRAMAS DE PERSISTENCIA CDMX Y EDOMEX
// ===========================================================================
#figslide2("Diagramas de persistencia: CDMX (118 huecos) y EDOMEX (241 huecos)",
  [
    Cada punto = un hueco H₁. *Distancia a la diagonal = persistencia* (tamaño del vacío). Lejos de la diagonal = desiertos estructurales; sobre la diagonal = ruido filtrado (min_persistencia = 200 m).
  ],
  "persistencia_CDMX.png",
  "persistencia_EDOMEX.png",
)


// ===========================================================================
// 8. WEIGHTED ALPHA / LAGUERRE
// ===========================================================================
#splitslide("Weighted Alpha (Laguerre): el tamaño de la clínica importa",
  [
    Alpha clásico: farmacia de 2 empleados ≡ hospital de 300.

    *Laguerre*: radio proporcional al tamaño:
    $ r_i = k dot sqrt("per_ocu"_i) $
    #v(6pt)
    #table(
      columns: (1fr, auto, auto, auto),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Métrica]], [#th[Clásico]], [#th[Laguerre]], [#th[Δ]],
      [Huecos CDMX],   [71],  [*118*], [#kpi[+66%]],
      [Huecos EDOMEX], [209], [*241*], [#kpi[+15%]],
    )
    #v(8pt)
    *¿Por qué subieron los huecos?* El clásico «rellenaba» vacíos con micro-consultorios que no tienen capacidad real de cubrir ese radio. Al ponderar, esos puntos pierden alcance y el vacío real aparece. CDMX +66%: mayor heterogeneidad de tamaños (IMSS + privados + micro-consultorios conviven).
  ],
  "laguerre_comparacion.png",
  ratio: 52%,
)


// ===========================================================================
// 9. LAGUERRE: MAPAS DE BIFILTRACIÓN
// ===========================================================================
#figslide2("Laguerre — Mapas de huecos ponderados: CDMX y EDOMEX",
  [
    Cada círculo = un hueco H₁, radio ∝ persistencia. Muchos eran invisibles sin la ponderación por tamaño.
  ],
  "bifiltracion_CDMX.png",
  "bifiltracion_EDOMEX.png",
)


// ===========================================================================
// 10. CALIBRACIÓN min_persistencia = 200 m
// ===========================================================================
#splitslide2("Calibración: ¿por qué min_persistencia = 200 m?",
  [
    #table(
      columns: (auto, auto, auto),
      stroke: none, inset: 7pt,
      fill: (_, row) => if row == 0 { azul } else if row == 2 { rgb("#d4edda") } else if calc.odd(row) { rgb("#eaf1f8") } else { white },
      [#th[Umbral]], [#th[CDMX]], [#th[EDOMEX]],
      [100 m],    [482],  [742],
      [*200 m* ✓],[*118*],[*241*],
      [400 m],    [17],   [91],
      [600 m],    [7],    [58],
    )
    #v(8pt)
    - La pendiente se *aplana* entre 200 m y 400 m: señal estructural sin el ruido de 100 m.
    - *Robustez 100%*: los huecos de persist. > 600 m (7 CDMX · 58 EDOMEX) aparecen en los 4 umbrales.
  ],
  "robustez_conteo_huecos.png",
  "robustez_persistencia_vs_umbrales.png",
  ratio: 56%,
)


// ===========================================================================
// 11. HUECOS DETECTADOS + DBSCAN
// ===========================================================================
#splitslide("118 + 241 huecos detectados — y cómo los agrupamos",
  [
    Cada círculo = hueco H₁, radio ∝ persistencia. *Color = en cuántos umbrales aparece*: rojo oscuro = 4/4 = desierto sólido.
    #v(8pt)
    *¿Por qué agrupar?* Dos huecos a 800 m se resuelven con *una sola clínica* bien ubicada. Una clínica por hueco desaprovecha presupuesto.
    #v(8pt)
    *DBSCAN* (eps = 1,500 m): huecos a ≤ 1.5 km forman un cluster = *una decisión de inversión*.
    #v(8pt)
    #table(
      columns: (1fr, auto, auto),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Ciudad]], [#th[Huecos prioritarios]], [#th[Clusters]],
      [CDMX],   [46], [39],
      [EDOMEX], [77], [74],
    )
  ],
  "robustez_mapa.png",
  ratio: 54%,
)


// ===========================================================================
// 12. CRUCE CENSAL: MATRICES DE RIESGO
// ===========================================================================
#figslide2("Cruce con Censo 2020: ¿sobre qué población caen los huecos?",
  [
    *~270,000 personas sin seguro* viven dentro de desiertos topológicos habitados.
  ],
  "matriz_riesgo_CDMX.png",
  "matriz_riesgo_EDOMEX.png",
)


// ===========================================================================
// 13. IMPACTO DEMOGRÁFICO
// ===========================================================================
#figslide2("Impacto demográfico: huecos por persistencia y población sin seguro",
  [
    Los huecos que destacan en *ambas* métricas (vacío grande + mucha población sin seguro) son los de máxima urgencia compuesta.
  ],
  "impacto_censal_CDMX.png",
  "impacto_censal_EDOMEX.png",
)


// ===========================================================================
// 14. ACCESIBILIDAD REAL
// ===========================================================================
#figslide("Accesibilidad real: tiempo de caminata por la red de calles",
  [
    Tiempo calculado sobre la *red de calles real* (no línea recta) a *4.5 km/h*; vías rápidas y barrancas crean rodeos que la distancia euclidiana ignora. Umbral de intervención: *15 min*. \
    Eje X = tiempo a la clínica más cercana · Eje Y = persistencia. *Esquina superior derecha* = vacíos grandes #kpi[y] lejanos = máxima prioridad.
  ],
  "scatter_accesibilidad.png",
)


// ===========================================================================
// 15. EL 4.° EJE: MARGINACIÓN
// ===========================================================================
#splitslide("El 4.° eje: marginación socioeconómica",
  [
    Una clínica cercana resuelve la barrera *geográfica*; la marginación mantiene la barrera de *uso*.
    #v(6pt)
    $ "IM" = 0.35 dot p_"sin salud" + 0.25 dot "def. escol." \ + 0.25 dot p_"mayores" + 0.15 dot rho_"sin salud" $
    #v(6pt)
    #table(
      columns: (1fr, auto),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Región]], [#th[Huecos que suben ≥ 3 pos.]],
      [CDMX],   [11 (IM medio 0.37)],
      [EDOMEX], [38 (IM medio 0.49)],
    )
    #v(6pt)
    Sin este eje, parte de la inversión habría ido a zonas menos vulnerables.
  ],
  "scoring_impacto_marginacion.png",
  ratio: 56%,
)


// ===========================================================================
// 16. SCORING 4 EJES
// ===========================================================================
#splitslide("Scoring multi-eje: priorización objetiva",
  [
    Pesos iguales, ranking por *percentil* interno a cada ciudad:
    $ "score" = 0.25(r_"tiempo" + r_"sin seguro" \ + r_"persist." + r_"marg.") $
    #v(6pt)
    #table(
      columns: (auto, auto),
      stroke: none, inset: 6pt, fill: tf,
      [#th[Eje]], [#th[Filtro OR]],
      [① Tiempo caminata],     [> 10 min],
      [② Personas sin seguro], [> p60],
      [③ Persistencia],        [> 400 m],
      [④ Marginación IM],      [> p60],
    )
    #v(6pt)
    *Filtro OR*: basta 1 de 4 → #kpi[46 CDMX · 77 EDOMEX] prioritarios.
  ],
  "scoring_scatter.png",
  ratio: 56%,
)


// ===========================================================================
// 17. RANKINGS Y PARETO
// ===========================================================================
#figslide2("Rankings de huecos prioritarios — Top urgencias por ciudad",
  [
    Rojo = Crítico · naranja = Alto. Pocos huecos concentran la mayor parte del impacto (Pareto).
  ],
  "scoring_rankings.png",
  "scoring_pareto.png",
)


// ===========================================================================
// 18. DBSCAN: CLUSTERS DE INVERSIÓN
// ===========================================================================
#figslide("DBSCAN — De huecos a decisiones de inversión",
  [
    Relleno = cluster · contorno = urgencia · diamante = centroide C\#. Grises con × = no prioritarios. *39 clusters CDMX · 74 EDOMEX*.
  ],
  "clusters_geograficos.png",
)


// ===========================================================================
// 19. MCLP: FORMULACIÓN
// ===========================================================================
#slide("Optimización: Maximum Coverage Location Problem (MCLP)")[
  #grid(columns: (1fr, 1fr), column-gutter: 28pt, align: (left + top, left + top),
    [
      *¿Para qué sirve?* Dado un presupuesto de *K clínicas nuevas*, encontrar las K ubicaciones que *maximizan las personas sin seguro cubiertas* a ≤ 15 min caminando.
      #v(8pt)
      *Formulación PLE* (PuLP/CBC):
      $ max sum_i d_i dot y_i $
      $ "s.t." quad sum_j x_j = K $
      $ y_i <= sum_j C_(i j) dot x_j quad forall i $
      - $d_i = "score"_i times "pob\_sin\_salud"_i$
      - $x_j in {0,1}$ — ¿se construye clínica $j$?
      - $C_(i j) = 1$ si $j$ alcanza hueco $i$ en ≤ 15 min
    ],
    [
      *¿Por qué demanda ponderada $d_i$?*

      El score ya integra los 4 ejes. Cubrir un hueco con score 0.9 y 5,000 personas sin seguro tiene *10× más impacto* que uno con score 0.3 y 500.
      #v(8pt)
      *Candidatos*: centroides de clusters DBSCAN, con tiempos sobre la red de calles real.
      #v(8pt)
      #nota[MCLP optimiza *acceso* (≤ 15 min). La validación topológica posterior verifica si la clínica *cierra geométricamente* el hueco — criterio más estricto.]
    ],
  )
]


// ===========================================================================
// 20. CDMX: CURVA DE RENDIMIENTO DECRECIENTE
// ===========================================================================
#figslide2("CDMX — Justificando K=7: curva de rendimiento decreciente",
  [
    K=7 es el último punto con > 5 pp de ganancia marginal; K=8→9 cae −1.1 pp. *Núcleo estable* (C1, C2, C5, C7, C8) presente en toda la curva = primera fase de inversión.
  ],
  "validacion_curva_k.png",
  "fase3_impacto_k.png",
)


// ===========================================================================
// 21. CDMX K=7: MAPA
// ===========================================================================
#splitslide("CDMX — Solución óptima K=7: ubicaciones y cobertura",
  [
    #table(
      columns: (1fr, auto),
      stroke: none, inset: 8pt, fill: tf,
      [#th[Métrica]], [#th[Resultado]],
      [Clínicas ubicadas],    [7 (C1, C2, C5, C7, C8, C16, C19)],
      [Huecos cubiertos],     [11 / 46 (24%)],
      [Personas sin seguro],  [*42,687*],
      [Cobertura poblacional],[*44.0%*],
    )
  ],
  "fase3_CDMX_k7_mapa.png",
  ratio: 58%,
)


// ===========================================================================
// 22. CDMX K=7: ANÁLISIS 4 EJES
// ===========================================================================
#slide("CDMX K=7 — ¿Qué tipos de huecos cubre y cuáles persisten?")[
  #v(10pt)
  #table(
    columns: (1fr, auto, auto, 1.6fr),
    stroke: none, inset: 11pt,
    fill: tf,
    [#text(fill: white, weight: "bold", size: 15pt)[Eje]],
    [#text(fill: white, weight: "bold", size: 15pt)[Cubiertos (11)]],
    [#text(fill: white, weight: "bold", size: 15pt)[Persistentes (35)]],
    [#text(fill: white, weight: "bold", size: 15pt)[Interpretación]],
    [Tiempo (min)],       [7.89],  [9.27],  [MCLP cubre los más accesibles con mayor población],
    [Sin seguro (pers.)], [3,881], [1,555], [Priorización correcta por inequidad (×2.5)],
    [Persistencia (m)],   [296],   [364],   [Vacíos más grandes son periféricos sin candidatos],
    [Marginación (IM)],   [0.35],  [0.29],  [4.° eje redirige inversión a zonas más vulnerables],
  )
]


// ===========================================================================
// 23. EDOMEX: ESTRATEGIA SUBREGIONAL
// ===========================================================================
#splitslide("EDOMEX — Estrategia subregional: K=3 por zona",
  [
    #table(
      columns: (1fr, auto, auto, auto),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Zona]], [#th[K]], [#th[Sin seguro cub.]], [#th[% local]],
      [Norte],         [3], [1,182],                 [13.9%],
      [Poniente],      [3], [10,243],                [23.0%],
      [ZMVM-Centro],   [3], [24,443],                [19.7%],
      [#kred[Oriente]],[3], [#kred[Sin candidatos]], [#kred[—]],
      [*Total*],       [*9 ubic.*],[*35,868*],       [*19.0%*],
    )
    #v(8pt)
    - Curva *lineal* (~+2 pp/clínica): no hay K óptimo único → K=3 por zona (equidad geográfica).
    - #kred[Oriente]: 12,270 personas sin seguro; requiere umbral 20–30 min o clínicas móviles.
  ],
  "fase3_EDOMEX_subregional_mapa.png",
  ratio: 54%,
)


// ===========================================================================
// 24. EDOMEX: RESULTADOS POR ZONA
// ===========================================================================
#figslide2("EDOMEX — Resultados por zona y análisis de los 4 ejes",
  none,
  "fase3_EDOMEX_zonas_mapas.png",
  "fase3_EDOMEX_subregional_ejes.png",
)


// ===========================================================================
// 25. VALIDACIÓN TOPOLÓGICA
// ===========================================================================
#splitslide2("Validación topológica: ¿se cerraron realmente los huecos?",
  [
    Hueco con centroide $c$ y persistencia $r$:
    #v(4pt)
    #table(
      columns: (1fr, auto, auto),
      stroke: none, inset: 6pt, fill: tf,
      [#th[Estado]], [#th[CDMX K=7]], [#th[EDOMEX K=12]],
      [Cerrado ($d < r$)],       [3/46 (7%)],  [6/77 (8%)],
      [Parcial ($r <= d < 2r$)], [4/46 (9%)],  [2/77 (3%)],
      [Persistente ($d >= 2r$)], [39/46 (85%)],[69/77 (90%)],
      [*Δ persist. total*],      [*−14.9%*],   [*−16.5%*],
    )
    #v(6pt)
    *MCLP ≠ cierre topológico*: MCLP optimiza acceso (≤ 15 min); el cierre exige $d < r$ del centroide — criterio geométrico más estricto.
  ],
  "validacion_mapa.png",
  "validacion_persistencia.png",
  ratio: 52%,
)


// ===========================================================================
// 26. CONCLUSIONES
// ===========================================================================
#slide("Conclusiones y recomendaciones de política pública")[
  #grid(columns: (1fr, 1fr), column-gutter: 24pt, row-gutter: 12pt,
    [
      #kpi[Problema estructural, no de escasez.]
      21k + 30k clínicas con 118 + 241 vacíos. La *forma* de la distribución importa tanto como la cantidad.
    ],
    [
      #kpi[El 4.° eje cambia quién recibe inversión.]
      IM medio cubiertos 0.35 vs persistentes 0.29. Sin marginación, la inversión habría ido a zonas menos vulnerables.
    ],
    [
      #kpi[CDMX: 7 clínicas → 42,687 personas (44.0%).]
      C1–C5–C7–C8 (fase 1) + C2–C16–C19 (fase 2). K=7 maximiza retorno antes de la caída en K=8→9.
    ],
    [
      #kpi[EDOMEX: 9 ubicables → 35,868 personas (19.0%).]
      K=3 por zona (equidad). Oriente (12,270 personas) requiere umbral 20–30 min o clínicas móviles.
    ],
  )
  #v(10pt)
  #table(
    columns: (1fr, 1fr, 1fr),
    stroke: none, inset: 6pt,
    fill: (_, row) => if calc.odd(row) { rgb("#eaf1f8") } else { white },
    [*Limitación*], [*Impacto*], [*Mejora propuesta*],
    [Tiempos euclidiana × 1.35], [Error ±15% en zonas con barrancos], [Red vial completa por subregión],
    [Censo 2020 vs DENUE 2023],  [Desajuste temporal 2–3 años],      [DENUE trimestral],
    [Oriente sin candidatos],    [12,270 personas sin cobertura],     [Umbral 20–30 min o clínicas móviles],
  )
  #v(4pt)
  #align(center, text(fill: azul-claro, size: 12pt)[
    DENUE 2023 · Censo 2020 · OpenStreetMap — Zona Metropolitana del Valle de México
  ])
]
