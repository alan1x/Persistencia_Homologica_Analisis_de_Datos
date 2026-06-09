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
  margin: (top: 1.2cm, bottom: 0.9cm, x: 1.5cm),
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

// Figura protagonista — una imagen
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

// Figura protagonista — dos imágenes lado a lado
#let figslide2(title, caption, img1, img2) = {
  pagebreak(weak: true)
  header(title)
  v(5pt)
  if caption != none { set text(size: 13pt); caption; v(4pt) }
  grid(
    columns: (1fr, 1fr),
    column-gutter: 8pt,
    image(FIG + img1, width: 100%, fit: "contain"),
    image(FIG + img2, width: 100%, fit: "contain"),
  )
}

// Texto izquierda + figura derecha
#let splitslide(title, body, fig, ratio: 48%) = {
  pagebreak(weak: true)
  header(title)
  v(7pt)
  grid(
    columns: (1fr, ratio),
    column-gutter: 20pt,
    align: (left + top, center + horizon),
    body,
    image(FIG + fig, width: 100%, fit: "contain"),
  )
}

// Texto izquierda + dos figuras apiladas derecha
#let splitslide2(title, body, fig1, fig2, ratio: 46%) = {
  pagebreak(weak: true)
  header(title)
  v(7pt)
  grid(
    columns: (1fr, ratio),
    column-gutter: 20pt,
    align: (left + top, center + top),
    body,
    [
      #image(FIG + fig1, width: 100%, fit: "contain")
      #v(4pt)
      #image(FIG + fig2, width: 100%, fit: "contain")
    ],
  )
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
    Persistencia Homológica para\ Detectar Desiertos de Salud
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
  #text(size: 13pt, fill: gris)[Mario Carlos Gaitan Reyna]
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
    [#kpi[④ RED VIAL]],   [OSMnx peatonal 4.5 km/h · isócronas reales · umbral 15 min],   [Tiempos por hueco],
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
      [0–5 pers.],   [Micro-consultorio / farmacia con médico],
      [6–30 pers.],  [Clínica de barrio / centro de salud],
      [31–300 pers.],[Clínica IMSS / ISSSTE],
      [> 300 pers.], [Hospital general — cobertura amplia],
    )
    #v(6pt)
    #nota[La *mayoría* son micro-estab. Los hospitales son minoría pero tienen radio 5–10× mayor → El Alpha clásico los trataba igual.]
  ],
  "eda_CDMX.png",
  "eda_EDOMEX.png",
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
  ratio: 46%,
)


// ===========================================================================
// 6. TDA: ALPHA COMPLEX — EL PROCESO
// ===========================================================================
#figslide("TDA — Cómo construimos los huecos: Alpha Complex paso a paso",
  [
    *1.* Cada clínica = punto en el plano.
    *2.* Radio $alpha$ crece → aristas cuando discos se tocan → triángulos cuando tres se solapan → *Alpha Complex*.
    *3.* Un *hueco H₁* = ciclo cerrado que rodea un vacío que nunca se rellena con triángulos.
    *4.* *Persistencia = radio_muerte − radio_nacimiento* (metros): cuánto «dura» el vacío. Puntos lejos de la diagonal = vacíos estructurales reales, no ruido.
  ],
  "vectorizacion.png",
)


// ===========================================================================
// 7. TDA: DIAGRAMAS DE PERSISTENCIA CDMX Y EDOMEX
// ===========================================================================
#figslide2("Diagramas de persistencia: CDMX (118 huecos) y EDOMEX (241 huecos)",
  [
    Cada punto = un hueco H₁. *Distancia a la diagonal = persistencia* (tamaño del vacío en metros). Esquina superior izquierda = vacíos grandes y duraderos = desiertos estructurales. Los puntos sobre la diagonal = ruido filtrado con min_persistencia = 200 m.
  ],
  "persistencia_CDMX.png",
  "persistencia_EDOMEX.png",
)


// ===========================================================================
// 8. WEIGHTED ALPHA / LAGUERRE: CONCEPTO
// ===========================================================================
#splitslide("Weighted Alpha (Laguerre): el tamaño de la clínica importa",
  [
    El Alpha clásico trata todos los puntos como iguales: farmacia de 2 empleados ≡ hospital de 300. Esto produce *falsos negativos*: el hospital «rellena» huecos que en realidad están vacíos para quien no tiene acceso a él.

    #v(6pt)
    *Solución Laguerre*: radio proporcional al tamaño:
    $ r_i = k dot sqrt("per_ocu"_i) $

    Cada punto del plano pertenece a la clínica que *más puede cubrirlo* (menor distancia ponderada).
    #v(6pt)
    #table(
      columns: (1fr, auto, auto, auto),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Métrica]], [#th[Clásico]], [#th[Laguerre]], [#th[Δ]],
      [Huecos CDMX],   [71],  [*118*], [#kpi[+66%]],
      [Huecos EDOMEX], [209], [*241*], [#kpi[+15%]],
    )
    #v(4pt)
    CDMX +66%: mayor heterogeneidad (IMSS + ISSSTE + privados + micro-consultorios conviven).
  ],
  "laguerre_comparacion.png",
  ratio: 46%,
)


// ===========================================================================
// 9. LAGUERRE: MAPAS DE BIFILTRACIÓN
// ===========================================================================
#figslide2("Laguerre — Mapas de huecos ponderados: CDMX y EDOMEX",
  [
    Cada círculo = un hueco H₁. *Radio ∝ persistencia* del hueco. Las zonas con círculos grandes y densos son los desiertos estructurales de mayor escala. Comparar con el Alpha clásico: muchos de estos huecos eran invisibles sin la ponderación por tamaño.
  ],
  "bifiltracion_CDMX.png",
  "bifiltracion_EDOMEX.png",
)


// ===========================================================================
// 10. DISTRIBUCIÓN DE RADIOS LAGUERRE
// ===========================================================================
#figslide("Distribución de radios de influencia Laguerre por estrato",
  [
    La mayoría de establecimientos son micro-consultorios con radio < 50 m. Los hospitales (≥ 300 empleados) tienen radios de 300–500 m. *Esto es exactamente lo que el Alpha clásico ignoraba*: trataba un consultorio de 2 personas igual que un hospital de 500.
  ],
  "distribucion_radios_laguerre.png",
)


// ===========================================================================
// 11. CALIBRACIÓN min_persistencia = 200 m
// ===========================================================================
#splitslide2("Calibración: ¿por qué min_persistencia = 200 m?",
  [
    #table(
      columns: (auto, auto, auto, 1fr),
      stroke: none, inset: 6pt,
      fill: (_, row) => if row == 0 { azul } else if row == 2 { rgb("#d4edda") } else if calc.odd(row) { rgb("#eaf1f8") } else { white },
      [#th[Umbral]], [#th[CDMX]], [#th[EDOMEX]], [#th[Nivel]],
      [100 m],   [482], [742],  [Micro-brechas entre consultorios adyacentes],
      [*200 m* ✓],[*118*],[*241*],[*Vacíos ≥ 1 cuadra larga — señal estructural*],
      [400 m],   [17],  [91],   [Solo los más severos; pierde huecos medianos],
      [600 m],   [7],   [58],   [Escala de colonia o más],
    )
    #v(7pt)
    *Punto de equilibrio*: pendiente se aplana entre 200 m y 400 m. \
    *Robustez 100%*: los 7 huecos CDMX con persist. > 600 m aparecen en los 4 umbrales. Ídem los 58 de EDOMEX — señales sólidas, no artefactos.
  ],
  "robustez_conteo_huecos.png",
  "robustez_persistencia_vs_umbrales.png",
)


// ===========================================================================
// 12. HUECOS DETECTADOS + INTRO DBSCAN
// ===========================================================================
#splitslide("118 + 241 huecos detectados — y cómo los agrupamos",
  [
    Cada círculo = hueco H₁. Radio ∝ persistencia. *Color = cuántos umbrales lo detectan*: rojo oscuro = señal en 4/4 = desierto sólido.
    #v(7pt)
    *¿Por qué agrupar huecos?* Dos huecos a 800 m se resuelven con *una sola clínica* bien ubicada. Forzar una por hueco desaprovecha el presupuesto.
    #v(7pt)
    *DBSCAN* (eps = 1,500 m, min_samples = 1): huecos a ≤ 1.5 km forman un cluster = *una decisión de inversión*.
    #v(7pt)
    #table(
      columns: (1fr, auto, auto),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Ciudad]], [#th[Huecos prioritarios]], [#th[Clusters]],
      [CDMX],   [46], [39],
      [EDOMEX], [77], [74],
    )
    #nota[74/77 clusters EDOMEX son *singletons*: huecos tan dispersos que casi ningún par comparte clínica → anticipa estrategia subregional.]
  ],
  "robustez_mapa.png",
  ratio: 50%,
)


// ===========================================================================
// 13. CRUCE CENSAL: MATRICES DE RIESGO
// ===========================================================================
#figslide2("Cruce con Censo 2020: ¿sobre qué población caen los huecos?",
  [
    De los huecos crudos, solo los que caen sobre AGEBs *habitadas* son relevantes. *62/118 CDMX · 180/241 EDOMEX* con población. Resto: zonas industriales, parques o despobladas. Total: ~270,000 personas sin seguro en desiertos topológicos habitados.
  ],
  "matriz_riesgo_CDMX.png",
  "matriz_riesgo_EDOMEX.png",
)


// ===========================================================================
// 14. IMPACTO DEMOGRÁFICO
// ===========================================================================
#figslide2("Impacto demográfico: huecos por persistencia y por población sin seguro",
  [
    Izq.: top huecos por *persistencia* (tamaño del vacío geométrico en metros). \
    Der.: top huecos por *población sin seguro* (impacto social directo). \
    Los huecos que aparecen en *ambas listas* son los de máxima urgencia compuesta. Cluster 1 CDMX: 7,525 sin seguro y > 12 min caminata. Cluster 5 EDOMEX: 23,869 personas (33.7% de la zona).
  ],
  "impacto_censal_CDMX.png",
  "impacto_censal_EDOMEX.png",
)


// ===========================================================================
// 15. ACCESIBILIDAD REAL: OSMnx
// ===========================================================================
#splitslide("Accesibilidad real: red vial peatonal con OSMnx",
  [
    *¿Por qué no distancia euclidiana?* Vías rápidas, barrancas y zonas industriales crean rodeos que pueden triplicar la distancia.
    #v(6pt)
    *Metodología*:
    - OSMnx: red peatonal real de OpenStreetMap
    - Velocidad: *4.5 km/h* (caminata normal)
    - *Isócrona* = polígono alcanzable en $t$ min (concave_hull, ratio = 0.4)
    - *Umbral 15 min*: literatura de salud pública documenta que barreras mayores reducen la consulta preventiva
    #v(6pt)
    *CDMX top 10*: 20–35 min (Álvaro Obregón, Xochimilco, Tláhuac). \
    *EDOMEX top*: > 40 min (norte y oriente).
  ],
  "isocronas_roma_norte.png",
  ratio: 48%,
)


// ===========================================================================
// 16. MAPAS DE ACCESIBILIDAD
// ===========================================================================
#figslide2("Mapas de tiempos de caminata — CDMX y EDOMEX",
  [
    Cada punto = centroide de un hueco. *Color = tiempo de caminata a la clínica más cercana*. Puntos rojos = geográficamente más aislados. Zonas periféricas (Tláhuac, Xochimilco, Oriente EDOMEX) concentran tiempos > 30 min.
  ],
  "mapas_accesibilidad_CDMX.png",
  "mapas_accesibilidad_EDOMEX.png",
)


// ===========================================================================
// 17. SCATTER DE ACCESIBILIDAD
// ===========================================================================
#figslide("Scatter accesibilidad: tamaño del vacío vs tiempo de caminata",
  [
    Eje X = tiempo de caminata a la clínica más cercana. Eje Y = persistencia del hueco (tamaño geométrico en metros). *Esquina superior derecha* = huecos urgentes en dos dimensiones: grandes *y* lejanos. Candidatos de máxima prioridad incluso antes de cruzar con los otros ejes.
  ],
  "scatter_accesibilidad.png",
)


// ===========================================================================
// 18. EL 4.° EJE: MARGINACIÓN
// ===========================================================================
#splitslide("El 4.° eje: marginación socioeconómica",
  [
    Una clínica a 10 min resuelve la barrera *geográfica*. En zonas de alta marginación persiste la barrera de *uso*: bajo nivel educativo, adultos mayores sin apoyo y poca capacidad económica amplifican el impacto de cualquier vacío.
    #v(6pt)
    *Índice de Marginación (IM)*:
    $ "IM" = 0.35 dot p_"sin salud" + 0.25 dot "def. escol." + 0.25 dot p_"mayores" + 0.15 dot rho_"sin salud" $
    #v(6pt)
    *Efecto en el ranking*:
    #table(
      columns: (1fr, auto, auto),
      stroke: none, inset: 6pt, fill: tf,
      [#th[Región]], [#th[Top 10 estables]], [#th[Suben ≥ 3 pos.]],
      [CDMX],   [9/10], [11 huecos (IM med. 0.37)],
      [EDOMEX], [9/10], [38 huecos (IM med. 0.49)],
    )
    #v(4pt)
    Sin este eje, parte de la inversión habría ido a zonas ya menos vulnerables.
  ],
  "scoring_impacto_marginacion.png",
  ratio: 46%,
)


// ===========================================================================
// 19. SCORING 4 EJES
// ===========================================================================
#splitslide("Scoring multi-eje: priorización objetiva de los huecos",
  [
    Pesos iguales con ranking por *percentil interno* a cada ciudad:
    $ "score" = 0.25(r_"tiempo" + r_"sin seguro" + r_"persist." + r_"marg.") $
    #v(5pt)
    #table(
      columns: (auto, 1fr, auto),
      stroke: none, inset: 6pt, fill: tf,
      [#th[Eje]], [#th[Variable]], [#th[Filtro OR]],
      [① Inaccesib.],  [Tiempo caminata],     [> 10 min],
      [② Inequidad],   [Personas sin seguro], [> p60],
      [③ Topológico],  [Persistencia (m)],    [> 400 m],
      [④ Marginación], [Índice IM],           [> p60],
    )
    #v(5pt)
    *Filtro OR*: basta 1 de 4 → *46 CDMX · 77 EDOMEX* prioritarios. \
    El percentil evita que un eje con valores grandes domine a los demás.
  ],
  "scoring_scatter.png",
  ratio: 46%,
)


// ===========================================================================
// 20. RANKINGS Y PARETO
// ===========================================================================
#figslide2("Rankings de huecos prioritarios — Top urgencias por ciudad",
  [
    Izq.: ranking CDMX por score compuesto (rojo = Crítico, naranja = Alto). \
    Der.: distribución Pareto — pocos huecos concentran la mayor parte del impacto. \
    Los huecos del cuadrante *Crítico* son la primera ola de inversión en ambas ciudades.
  ],
  "scoring_rankings.png",
  "scoring_pareto.png",
)


// ===========================================================================
// 21. DBSCAN: CLUSTERS DE INVERSIÓN
// ===========================================================================
#figslide("DBSCAN — De huecos a decisiones de inversión: clusters geográficos",
  [
    Relleno = identidad del cluster (mismo color = misma decisión). *Contorno = urgencia* (rojo=Crítico, naranja=Alto, verde=Moderado). Diamante = centroide C\# (C1 = mayor score). Círculos grises con × = no prioritarios (bajos en los 4 ejes). *39 clusters CDMX · 74 clusters EDOMEX*.
  ],
  "clusters_geograficos.png",
)


// ===========================================================================
// 22. MCLP: FORMULACIÓN
// ===========================================================================
#slide("Optimización: Maximum Coverage Location Problem (MCLP)")[
  #grid(columns: (1fr, 1fr), column-gutter: 28pt, align: (left + top, left + top),
    [
      *¿Para qué sirve?* Dado un presupuesto de *K clínicas nuevas*, encontrar las K ubicaciones que *maximizan el número de personas sin seguro cubiertas* a ≤ 15 min caminando.
      #v(8pt)
      *Formulación PLE* (PuLP/CBC):
      $ max sum_i d_i dot y_i $
      $ "s.t." quad sum_j x_j = K $
      $ y_i <= sum_j C_(i j) dot x_j quad forall i $
      - $d_i = "score"_i times "pob\_sin\_salud"_i$ — urgencia × personas
      - $x_j in {0,1}$ — ¿se construye clínica $j$?
      - $C_(i j) = 1$ si $j$ alcanza hueco $i$ en ≤ 15 min
    ],
    [
      *¿Por qué demanda ponderada $d_i$?*

      El score ya integra los 4 ejes. Cubrir un hueco con score 0.9 y 5,000 personas sin seguro tiene *10× más impacto* que uno con score 0.3 y 500.
      #v(8pt)
      *Candidatos*: centroides de clusters DBSCAN. Tiempos evaluados sobre la red peatonal real OSMnx.
      #v(8pt)
      #nota[MCLP optimiza *acceso* (≤ 15 min). La validación topológica posterior verifica si la clínica *cierra geométricamente* el hueco — criterio más estricto.]
    ],
  )
]


// ===========================================================================
// 23. CDMX: CURVA DE RENDIMIENTO DECRECIENTE
// ===========================================================================
#figslide2("CDMX — Justificando K=7: curva de rendimiento decreciente",
  [
    Izq.: cobertura acumulada y ganancia marginal por clínica adicional. K=7 es el último punto con > 5 pp de ganancia; K=8→9 muestra la caída más pronunciada (−1.1 pp). \
    Der.: impacto acumulado en personas sin seguro. *Núcleo estable* (C1,C2,C5,C7,C8): presentes en toda la curva K=5→10 = primera fase de inversión.
  ],
  "validacion_curva_k.png",
  "fase3_impacto_k.png",
)


// ===========================================================================
// 24. CDMX K=7: MAPA
// ===========================================================================
#splitslide("CDMX — Solución óptima K=7: ubicaciones y zonas de cobertura",
  [
    *7 clínicas* en Clusters C1, C2, C5, C7, C8, C16, C19.
    #v(6pt)
    #table(
      columns: (1fr, auto),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Métrica]], [#th[Resultado]],
      [Clínicas ubicadas],    [7],
      [Huecos cubiertos],     [11 / 46 (24%)],
      [Personas sin seguro],  [*42,687*],
      [Cobertura poblacional],[*44.0%*],
    )
    #v(6pt)
    Polígonos de color = isócrona 15 min por clínica. Círculos *borde blanco* = huecos cubiertos. Límites de alcaldías: INEGI 2020.
    #v(4pt)
    *Fase 1*: C1–C2–C5–C7–C8 (núcleo estable). \
    *Fase 2*: C16–C19 (segunda prioridad).
  ],
  "fase3_CDMX_k7_mapa.png",
  ratio: 54%,
)


// ===========================================================================
// 25. CDMX K=7: ANÁLISIS 4 EJES
// ===========================================================================
#figslide("CDMX K=7 — ¿Qué tipos de huecos cubre y cuáles persisten?",
  [
    #table(
      columns: (1fr, auto, auto, 1fr),
      stroke: none, inset: 7pt, fill: tf,
      [#th[Eje]], [#th[Cubiertos (11)]], [#th[Persistentes (35)]], [#th[Interpretación]],
      [Tiempo (min)],       [7.89],  [9.27],  [MCLP cubre los más accesibles con mayor población],
      [Sin seguro (pers.)], [3,881], [1,555], [Priorización correcta por inequidad (×2.5)],
      [Persistencia (m)],   [296],   [364],   [Vacíos más grandes son periféricos sin candidatos],
      [Marginación (IM)],   [0.35],  [0.29],  [4.° eje redirige inversión a zonas más vulnerables],
    )
  ],
  "fase3_CDMX_k7_ejes.png",
)


// ===========================================================================
// 26. EDOMEX: ESTRATEGIA SUBREGIONAL
// ===========================================================================
#splitslide("EDOMEX — Por qué una estrategia subregional K=3 por zona",
  [
    Curva K=5→10 de EDOMEX: *casi perfectamente lineal* (~+2 pp/clínica). No hay codo → no hay K óptimo único. *Causa*: 74/77 clusters son singletons — huecos tan dispersos que casi ningún par comparte clínica.
    #v(5pt)
    Las 4 zonas no se comunican a 15 min → K=3 por zona (equidad geográfica):
    #v(4pt)
    #table(
      columns: (1fr, auto, auto, auto),
      stroke: none, inset: 6pt, fill: tf,
      [#th[Zona]], [#th[K]], [#th[Sin seguro cub.]], [#th[% local]],
      [Norte],         [3], [1,182],                 [13.9%],
      [Poniente],      [3], [10,243],                [23.0%],
      [ZMVM-Centro],   [3], [24,443],                [19.7%],
      [#kred[Oriente]],[3], [#kred[Sin candidatos]], [#kred[—]],
      [*Total*],       [*9 ubic.*],[*35,868*],       [*19.0%*],
    )
    #v(4pt)
    #kred[Oriente]: 12,270 personas sin seguro. Requiere umbral 20–30 min o clínicas móviles.
  ],
  "fase3_EDOMEX_subregional_mapa.png",
  ratio: 52%,
)


// ===========================================================================
// 27. EDOMEX: MAPAS POR ZONA Y ANÁLISIS DE EJES
// ===========================================================================
#figslide2("EDOMEX — Resultados por zona y análisis de los 4 ejes",
  [
    Izq.: mapas Norte / Poniente / ZMVM con isócronas 15 min. Huecos *borde blanco* = cubiertos. \
    Der.: análisis de los 4 ejes por subregión. Como en CDMX, el MCLP cubre los huecos con mayor población sin seguro (cubiertos: sin_seguro medio >> persistentes).
  ],
  "fase3_EDOMEX_zonas_mapas.png",
  "fase3_EDOMEX_subregional_ejes.png",
)


// ===========================================================================
// 28. VALIDACIÓN TOPOLÓGICA
// ===========================================================================
#slide("Validación topológica: ¿se cerraron realmente los huecos?")[
  #grid(columns: (1fr, 1fr), column-gutter: 24pt, align: (left + top, left + top),
    [
      La TDA que *detectó* los huecos también *verifica* si las clínicas nuevas los resuelven. Hueco con centroide $c$ y persistencia $r$:
      #v(5pt)
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
      *MCLP ≠ cierre topológico*: MCLP optimiza acceso (≤ 15 min al centroide). El cierre topológico requiere $d < r$ — criterio geométrico más estricto. Un hueco «cubierto» por MCLP puede no estar topológicamente cerrado si la clínica cae a 800 m del centroide pero llega en 12 min por la red vial.
      #v(5pt)
      #nota[*Robustez*: los huecos de persist. > 600 m aparecen en los 4 umbrales (7 CDMX · 58 EDOMEX). Las señales más severas son independientes del calibrado.]
    ],
    [
      *¿Cómo cambia el territorio?*
      #v(4pt)
      #image(FIG + "validacion_mapa.png", width: 100%, fit: "contain")
      #v(4pt)
      #image(FIG + "validacion_persistencia.png", width: 100%, fit: "contain")
    ],
  )
]


// ===========================================================================
// 29. CONCLUSIONES
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
    [Tiempos euclidiana × 1.35], [Error ±15% en zonas con barrancos], [Red OSMnx completa por subregión],
    [Censo 2020 vs DENUE 2023],  [Desajuste temporal 2–3 años],      [DENUE trimestral],
    [Oriente sin candidatos],    [12,270 personas sin cobertura],     [Umbral 20–30 min o clínicas móviles],
  )
  #v(4pt)
  #align(center, text(fill: azul-claro, size: 12pt)[
    DENUE 2023 · Censo 2020 · OpenStreetMap — Zona Metropolitana del Valle de México
  ])
]
