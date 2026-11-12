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
      - *52,372 establecimientos de salud* entre CDMX y EDOMEX (un tercio son dentistas): no hay escasez absoluta.
      - Las métricas tradicionales son ciegas al vacío estructural:
        - Densidad de clínicas por km² ✗  · Radio de 500 m ✗  · Conteo por municipio ✗
      #v(6pt)
      - *Desierto estructural*: zona rodeada de clínicas por fuera, vacía por dentro. El mapa de su colonia se ve «verde» aunque el interior esté vacío.
      #v(10pt)
      #text(fill: azul, weight: "bold", size: 16pt)[
        ¿Dónde están esos vacíos, cuánta población hay dentro y qué tan útil es la topología para decidir dónde poner clínicas?
      ]
    ],
    [
      #big("≈325k", "personas sin seguro dentro de vacíos habitados")
      #v(12pt)
      #big("< 1% y 5%", "de las personas en discos prioritarios (CDMX y EDOMEX) están a más de 833 m de un establecimiento")
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
    [#kpi[① DATOS]],      [DENUE 2023 (SCIAN 62) + Censo 2020 (AGEBs) + OpenStreetMap],            [21 k / 30 k estab.],
    [#kpi[② TDA]],        [Alpha Complex clásico · persist. > 200 m (Laguerre solo sensibilidad)],  [71 / 209 huecos H₁],
    [#kpi[③ CENSO]],      [AGEBs habitadas · PSINDER · Índice de Marginación],                      [62/99 · ≈325 k sin seguro],
    [#kpi[④ TIEMPOS]],    [Euclidiana × 1.35 a 4.5 km/h (no red vial) · 15 min = 833 m],           [Tiempos estimados],
    [#kpi[⑤ SCORING]],    [Score 4 ejes (percentiles) · filtro OR · DBSCAN · MCLP/PuLP],            [46 / 77 prioritarios],
    [#kpi[⑥ MEDICIÓN]],   [Cierre medido · robustez perturbando datos · modelo revisado],           [cierra 1/46 · 2/77],
  )
  #v(14pt)
  #nota[
    *Resultado*: K=7 en CDMX → #kpi[42,687 personas] (26,281 contando cada una vez) · 8 clínicas en EDOMEX → #kpi[35,868] (17,082 contando una vez)
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
    #nota[La *mayoría* son micro-estab. Los hospitales son minoría y tienen mucho más personal ocupado.]
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
    El *AGEB urbana* es la unidad geoespacial mínima (≈ manzanas). Permite cruzar cada hueco topológico con la población real que lo habita.
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
    #nota[*PSINDER = variable crítica*: sin seguro = sin alternativa cuando la clínica está lejos. #kred[≈325,000 personas] sin seguro dentro de vacíos habitados.]
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
#figslide2("Diagramas de persistencia: CDMX (71 huecos) y EDOMEX (209 huecos)",
  [
    Cada punto = un hueco H₁. *Distancia a la diagonal = persistencia* (tamaño del vacío). Lejos de la diagonal = vacíos estructurales; sobre la diagonal = ruido (min_persistencia = 200 m, Alpha clásico).
  ],
  "persistencia_CDMX.png",
  "persistencia_EDOMEX.png",
)


// ===========================================================================
// 8. WEIGHTED ALPHA / LAGUERRE
// ===========================================================================
#splitslide("Weighted Alpha (Laguerre): solo como sensibilidad",
  [
    Alpha clásico: todos los establecimientos pesan igual. *Laguerre*: radio por tamaño
    $ r_i = 50 + 30 dot sqrt("per_ocu"_i) $
    (de 102 a 570 m).
    #v(6pt)
    #table(
      columns: (1fr, auto, auto, auto),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Huecos]], [#th[Clásico]], [#th[Pesos iguales]], [#th[Laguerre]],
      [CDMX],   [*71*],  [116], [118],
      [EDOMEX], [*209*], [240], [241],
    )
    #v(8pt)
    *¿Por qué sube el conteo?* No por los hospitales: con el *mismo* peso para todos ya salen 116 y 240. La persistencia se mide como $sqrt(alpha')$ y esa diferencia crece al acercarse a cero. Laguerre sí cambia *cuáles* huecos aparecen, no *cuántos*. El análisis usa el clásico.
  ],
  "auditoria_laguerre_artefacto.png",
  ratio: 52%,
)


// ===========================================================================
// 9. MAPAS DE BIFILTRACIÓN (ALPHA CLÁSICO)
// ===========================================================================
#figslide2("Mapas de huecos del Alpha clásico: CDMX y EDOMEX",
  [
    Cada círculo = un hueco H₁ del Alpha *clásico* (notebook 09), radio ∝ persistencia; la densidad es solo de establecimientos de salud. No son huecos de Laguerre.
  ],
  "bifiltracion_CDMX.png",
  "bifiltracion_EDOMEX.png",
)


// ===========================================================================
// 10. CALIBRACIÓN min_persistencia = 200 m
// ===========================================================================
#splitslide2("Calibración y robustez real de los huecos",
  [
    #table(
      columns: (auto, auto, auto),
      stroke: none, inset: 6pt,
      fill: (_, row) => if row == 0 { azul } else if row == 2 { rgb("#d4edda") } else if calc.odd(row) { rgb("#eaf1f8") } else { white },
      [#th[Umbral]], [#th[CDMX]], [#th[EDOMEX]],
      [100 m],    [286],  [544],
      [*200 m* ✓],[*71*], [*209*],
      [400 m],    [16],   [90],
      [600 m],    [6],    [57],
    )
    #v(6pt)
    - La antigua «robustez 100%» no podía fallar: era cierta por definición.
    - Perturbando los *datos* (σ = 100 m): sobrevive *93%* de los huecos ≥ 400 m, contra ≈ 50% de los menores.
    - Pero con σ = 50 m solo 22/46 y 50/77 prioritarios sobreviven ≥ 80% de las veces.
  ],
  "robustez_real_supervivencia.png",
  "robustez_real_nulo.png",
  ratio: 56%,
)


// ===========================================================================
// 11. HUECOS DETECTADOS + DBSCAN
// ===========================================================================
#splitslide("71 + 209 huecos detectados — y cómo los agrupamos",
  [
    Mapa de los clusters de huecos prioritarios: cada color es un cluster, es decir, una decisión de inversión.
    #v(8pt)
    *¿Por qué agrupar?* Dos huecos a 800 m se resuelven con *una sola clínica* bien ubicada.
    #v(8pt)
    *DBSCAN* (eps = 1,500 m): huecos a ≤ 1.5 km forman un cluster.
    #v(8pt)
    #table(
      columns: (1fr, auto, auto),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Ciudad]], [#th[Huecos prioritarios]], [#th[Clusters]],
      [CDMX],   [46], [39],
      [EDOMEX], [77], [74],
    )
  ],
  "clusters_geograficos.png",
  ratio: 54%,
)


// ===========================================================================
// 12. CRUCE CENSAL: MATRICES DE RIESGO
// ===========================================================================
#figslide2("Cruce con Censo 2020: ¿sobre qué población caen los huecos?",
  [
    *≈325,000 personas sin seguro* viven dentro de vacíos habitados (62 de 71 huecos en CDMX, 99 de 209 en EDOMEX), suponiendo población uniforme por AGEB.
  ],
  "matriz_riesgo_CDMX.png",
  "matriz_riesgo_EDOMEX.png",
)


// ===========================================================================
// 13. IMPACTO DEMOGRÁFICO
// ===========================================================================
#figslide2("Los huecos más grandes y los más lejanos",
  [
    Izquierda: los 10 huecos más grandes (el número es el tiempo estimado: 4/10 en CDMX y 8/10 en EDOMEX pasan de 15 min). Derecha: los 10 más lejanos de un establecimiento, con su persistencia. Un hueco grande no siempre está lejos ni tiene gente.
  ],
  "comparativa_tamano.png",
  "comparativa_distancia.png",
)


// ===========================================================================
// 14. ACCESIBILIDAD REAL
// ===========================================================================
#figslide("Accesibilidad: tiempos estimados de caminata",
  [
    Tiempo *estimado* con distancia euclidiana × 1.35 a *4.5 km/h* (no es red vial); 15 min = 833 m. CDMX: mediana 7.6 min, 4 de 62 huecos pasan de 15. EDOMEX: mediana 9.6, 16 de 99. \
    Eje X = tiempo al establecimiento más cercano · Eje Y = persistencia. *Esquina superior derecha* = vacíos grandes #kpi[y] lejanos.
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
      columns: (auto, 1fr),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Solución]], [#th[Clínicas que cambian]],
      [CDMX K=7],   [2 de 7 (C16 y C19 en vez de C3 y C17)],
      [EDOMEX K=8], [ninguna],
    )
    #v(6pt)
    En CDMX: 42,687 contra 39,974 personas. El IM incluye % sin seguro (Spearman 0.55 y 0.75), así que en parte repite otro eje.
  ],
  "fase3_CDMX_k7_ejes.png",
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
      - $d_i = "score"_i times "personas"_i$ en CDMX; en EDOMEX subregional, solo personas
      - $x_j in {0,1}$ — ¿se construye clínica $j$?
      - $C_(i j) = 1$ si $j$ alcanza hueco $i$ en ≤ 15 min (833 m)
    ],
    [
      *¿Por qué demanda ponderada $d_i$?*

      En CDMX el score integra los 4 ejes. Cubrir un hueco con score 0.9 y 5,000 personas sin seguro tiene *10× más impacto* que uno con score 0.3 y 500.
      #v(8pt)
      *Candidatos*: centroides de clusters DBSCAN, con tiempos euclidiana × 1.35.
      #v(8pt)
      #nota[MCLP optimiza *acceso* (≤ 15 min). La medición posterior muestra que no *cierra* los huecos: 1 de 46 y 2 de 77.]
    ],
  )
]


// ===========================================================================
// 20. CDMX: CURVA DE RENDIMIENTO DECRECIENTE
// ===========================================================================
#figslide("CDMX — K=7 es una decisión, no un codo",
  [
    Con solo personas el incremento marginal cae de +5.1 pp a +4.0 pp en K=8→9: un codo sugeriría K=8. K=7 es una decisión de presupuesto y es el óptimo exacto (77,520 combinaciones). *Núcleo estable* con score × personas: C1, C2, C5, C7, C8. La figura muestra el impacto incremental de las primeras clínicas.
  ],
  "fase3_impacto_k.png",
)


// ===========================================================================
// 21. CDMX K=7: MAPA
// ===========================================================================
#splitslide("CDMX — Solución óptima K=7: ubicaciones y cobertura",
  [
    #table(
      columns: (auto, 1fr),
      stroke: none, inset: 8pt, fill: tf,
      [#th[Métrica]], [#th[Resultado]],
      [Clínicas],    [7 (C1, C2, C5, C7, C8, C16, C19)],
      [Huecos cubiertos], [11 / 46 (24%)],
      [Sin seguro],  [*42,687* (26,281 contando una vez)],
      [Cobertura (reporte)],[*44.0%*],
    )
  ],
  "fase3_CDMX_k7_mapa.png",
  ratio: 52%,
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
    [Marginación (IM)],   [0.35],  [0.29],  [IM incluye % sin seguro: en parte repite el eje 2],
  )
]


// ===========================================================================
// 23. EDOMEX: ESTRATEGIA SUBREGIONAL
// ===========================================================================
#splitslide("EDOMEX — Estrategia subregional: 8 clínicas",
  [
    #table(
      columns: (1fr, auto, auto, auto),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Zona]], [#th[Clínicas]], [#th[Sin seguro cub.]], [#th[% local]],
      [Norte],         [2], [1,182],                 [13.9%],
      [Poniente],      [3], [10,243],                [23.0%],
      [ZMVM-Centro],   [3], [24,443],                [19.7%],
      [#kred[Oriente]],[0], [#kred[—]], [#kred[—]],
      [*Total*],       [*8*],[*35,868*],             [*19.0%*],
    )
    #v(8pt)
    - Contando cada persona una vez: *17,082*, bajo el azar (p95 18,674). Norte tiene solo 2 candidatos.
    - #kred[Oriente] quedó fuera por el corte de 20 candidatos, no por falta de candidatos: en el modelo revisado, 3 clínicas alcanzan 4,911 de 10,413 personas.
  ],
  "modelo_ubicaciones.png",
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
// 25. MEDICIÓN DIRECTA
// ===========================================================================
#splitslide2("Medición directa: ¿se cerraron los huecos?",
  [
    Se agregan las clínicas a los puntos, se recalcula la persistencia (Alpha clásico) y se sigue cada hueco prioritario:
    #v(4pt)
    #table(
      columns: (1fr, auto, auto),
      stroke: none, inset: 6pt, fill: tf,
      [#th[Medido]], [#th[CDMX K=7]], [#th[EDOMEX K=8]],
      [Cerrados],   [1/46],  [2/77],
      [Modificados], [13],   [8],
      [Intactos],   [32],    [67],
      [*Δ persist. total*],  [*−2.3%*], [*−7.4%*],
      [Azar (media)],        [−5.5%],   [−7.4%],
    )
    #v(6pt)
    Una clínica *parte* un hueco grande, no lo cierra. Antes: «−14.9% y −16.5%» con una regla geométrica que no se sostiene.
  ],
  "cierre_real_antes_despues.png",
  "cierre_real_lineas_base.png",
  ratio: 52%,
)


// ===========================================================================
// 26. MODELO REVISADO
// ===========================================================================
#figslide2("Modelo revisado: personas y acceso nuevo",
  [
    «Personas» (solo maximizar personas alcanzadas): CDMX 28,418 y EDOMEX 30,033, sobre el reporte (26,281 y 17,082). Para *acceso nuevo* (de > 833 m a ≤ 833 m), un modelo sin topología logra 4,346 y 12,124 personas, contra 319 y 2,248 del reporte. Los pesos de robustez no mejoran.
  ],
  "modelo_acceso_nuevo.png",
  "modelo_personas_vs_azar.png",
)


// ===========================================================================
// 27. CONCLUSIONES
// ===========================================================================
#slide("Conclusiones y limitaciones")[
  #set text(size: 13.5pt)
  #grid(columns: (1fr, 1fr), column-gutter: 24pt, row-gutter: 10pt,
    [
      #kpi[Hay vacíos, pero no donde la gente está lejos.]
      71 + 209 huecos y ≈325,000 personas sin seguro dentro; solo 0.9% y 5.0% están a más de 833 m.
    ],
    [
      #kpi[Las clínicas no cierran los huecos.]
      Cierran 1 de 46 y 2 de 77; no superan al azar en persistencia. Su valor es alcanzar personas.
    ],
    [
      #kpi[CDMX: 7 clínicas → 42,687 personas (26,281 contando una vez).]
      Fase 1: C1, C2, C5, C7, C8; fase 2: C16, C19. Supera al azar (p95 18,363).
    ],
    [
      #kpi[EDOMEX: 8 clínicas → 35,868 (17,082 contando una vez).]
      Norte 2, Poniente 3, ZMVM 3, Oriente 0. No supera al azar (p95 18,674).
    ],
  )
  #v(6pt)
  #nota[La topología describe bien la *forma* de la red, pero no basta para decidir dónde dar *acceso nuevo*: medir directamente a quién le queda lejos la oferta rinde de 2.5 a 6 veces más.]
  #v(6pt)
  #table(
    columns: (1fr, 1fr),
    stroke: none, inset: 5pt,
    fill: (_, row) => if calc.odd(row) { rgb("#eaf1f8") } else { white },
    [*Limitación*], [*Detalle*],
    [Euclidiana × 1.35, no red vial],  [Radio efectivo de 833 m; tiempos estimados],
    [Población uniforme por AGEB],     [Solo AGEB urbanas; PSINDER es afiliación, no atención],
    [Depende de qué se cuenta],        [Solo 19/46 y 34/77 prioritarios tienen hueco en la red médica],
  )
  #v(4pt)
  #align(center, text(fill: azul-claro, size: 12pt)[
    DENUE 2023 · Censo 2020 — Zona Metropolitana del Valle de México
  ])
]
