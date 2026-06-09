// Presentación — Persistencia Homológica para Detectar Desiertos de Salud
// Tema académico azul/blanco · autocontenido (sin paquetes externos)
// Compilar desde la raíz:  typst compile --root . presentacion/presentacion.typ presentacion/presentacion.pdf
// Figuras en /outputs/figuras/ (relativo a la raíz del proyecto)

#let azul       = rgb("#1f4e79")
#let azul-claro = rgb("#2e75b6")
#let gris       = rgb("#333333")
#let FIG        = "/outputs/figuras/"

#set page(
  paper: "presentation-16-9",
  fill: white,
  margin: (top: 1.2cm, bottom: 0.9cm, x: 1.5cm),
  footer: context {
    set text(size: 9pt, fill: azul-claro)
    grid(
      columns: (1fr, auto),
      align: (left, right),
      [Desiertos de Salud · Análisis Topológico de Datos],
      [#counter(page).display()],
    )
  },
)
#set text(font: "DejaVu Sans", size: 16pt, fill: gris, lang: "es")
#set par(justify: false, leading: 0.6em)

// --- helpers ---------------------------------------------------------------
#let kpi(x) = text(fill: azul, weight: "bold")[#x]

#let header(title) = {
  text(size: 23pt, weight: "bold", fill: azul)[#title]
  v(-3pt)
  line(length: 100%, stroke: 1.4pt + azul-claro)
}

// Slide de contenido (sin figura grande)
#let slide(title, body) = {
  pagebreak(weak: true)
  header(title)
  v(8pt)
  body
}

// Slide FIGURA-PROTAGONISTA: título + breve pie + figura que llena la página
#let figslide(title, caption, img) = {
  pagebreak(weak: true)
  block(height: 100%, width: 100%, grid(
    rows: (auto, auto, 1fr),
    row-gutter: 7pt,
    header(title),
    if caption != none {
      set text(size: 15pt)
      caption
    } else { [] },
    align(center, image(FIG + img, width: 100%, height: 100%, fit: "contain")),
  ))
}

// Número grande de impacto
#let big(n, etiqueta) = align(center, block[
  #text(size: 46pt, weight: "bold", fill: azul)[#n]
  #v(-8pt)
  #text(size: 15pt, fill: azul-claro)[#etiqueta]
])

// ===========================================================================
// PORTADA
// ===========================================================================
#align(center + horizon, block[
  #text(size: 36pt, weight: "bold", fill: azul)[
    Persistencia Homológica para\ Detectar Desiertos de Salud
  ]
  #v(8pt)
  #text(size: 20pt, fill: azul-claro)[Ciudad de México y Estado de México]
  #v(22pt)
  #line(length: 45%, stroke: 1pt + azul-claro)
  #v(14pt)
  #text(size: 14pt, fill: gris)[
    Análisis Topológico de Datos · DENUE 2023 · Censo 2020 · OpenStreetMap
  ]
])

// ===========================================================================
#slide("El problema: desiertos que los mapas no ven")[
  #grid(columns: (1.1fr, 1fr), column-gutter: 26pt, align: (left, center + horizon),
    [
      - *52,372 clínicas* de salud entre CDMX y EDOMEX.
      - La abundancia oculta una distribución profundamente *desigual*.
      - Zonas *rodeadas* de servicios, pero *vacías por dentro*.
      #v(8pt)
      #text(fill: azul, weight: "bold", size: 19pt)[
        Un hueco topológico = un desierto de salud estructural.
      ]
    ],
    big("2 km", "a la clínica más cercana, aun en colonias \"verdes\" en densidad"),
  )
]

// ===========================================================================
#slide("Datos", [
  #table(
    columns: (auto, 1fr),
    stroke: none,
    inset: 11pt,
    fill: (_, row) => if calc.odd(row) { rgb("#eaf1f8") } else { white },
    [#kpi[DENUE 2023]],
      [Establecimientos de salud (SCIAN 62): *21,585* CDMX · *30,787* EDOMEX. Coordenadas + tamaño (personal ocupado).],
    [#kpi[Censo 2020]],
      [Población por AGEB: sin seguro médico, escolaridad, adultos mayores. *¿A quién afectan los vacíos?*],
    [#kpi[OpenStreetMap]],
      [Red vial peatonal (OSMnx) para tiempos de caminata reales.],
  )
])

// ===========================================================================
#figslide("¿Qué es un hueco H₁?",
  [Un *ciclo cerrado* de clínicas que rodea un vacío. La *persistencia* (m) mide su tamaño; lejos de la diagonal = vacíos *estructurales*, no ruido.],
  "persistencia_CDMX.png",
)

// ===========================================================================
#figslide("Detección: no todas las clínicas cubren igual",
  [El *Weighted Alpha (Laguerre)* pondera cada clínica por su tamaño y revela #kpi[+66% de huecos en CDMX] que el método clásico ocultaba.],
  "laguerre_comparacion.png",
)

// ===========================================================================
#figslide("Geolocalización de los desiertos",
  [#kpi[118] huecos en CDMX · #kpi[241] en EDOMEX, cada uno con centroide y radio. Análisis por ciudad (percentiles internos): el conteo crudo no es urgencia relativa.],
  "fase3_mapa_CDMX.png",
)

// ===========================================================================
#figslide("¿A quién afectan? Censo 2020",
  [Cruce de huecos habitados con población sin seguro médico (sin seguro = sin alternativa): #kpi[270,000 personas] viven dentro de desiertos de salud.],
  "matriz_riesgo_CDMX.png",
)

// ===========================================================================
#figslide("Priorización: scoring de 4 ejes",
  [Cada hueco puntúa por percentil en *tiempo* · *sin seguro* · *persistencia* · *marginación*. Esquina superior derecha = máxima urgencia.],
  "scoring_scatter.png",
)

// ===========================================================================
#figslide("¿Dónde construir? CDMX — MCLP K=7",
  [Optimización (cobertura máxima a ≤ 15 min): #kpi[7 clínicas] cubren #kpi[42,687 personas] sin seguro, el #kpi[44%] del total prioritario.],
  "fase3_CDMX_k7_mapa.png",
)

// ===========================================================================
#figslide("EDOMEX — estrategia subregional",
  [Huecos dispersos en 4 zonas sin codo en la curva K → presupuesto por zona: #kpi[12 presupuestadas, 9 ubicables], 35,868 personas (Oriente requiere estrategia móvil).],
  "fase3_EDOMEX_subregional_mapa.png",
)

// ===========================================================================
#figslide("Validación y robustez",
  [El *cierre topológico* verifica si las clínicas cierran los huecos. Severos (600 m): #kpi[100% robustos] a los 4 umbrales. Persistencia total: −14.9% CDMX · −16.5% EDOMEX.],
  "validacion_curva_k.png",
)

// ===========================================================================
#slide("Conclusiones", [
  #grid(columns: (1fr, 1fr), column-gutter: 26pt, row-gutter: 16pt,
    [#kpi[Problema estructural, no de escasez.]\ Sobran clínicas; están mal distribuidas.],
    [#kpi[La forma importa.]\ La TDA detecta vacíos que la densidad no ve.],
    [#kpi[Impacto medible.]\ 270k personas sin seguro atrapadas en desiertos.],
    [#kpi[Inversión priorizada.]\ Método objetivo y reproducible para decidir dónde construir.],
  )
  #v(16pt)
  #align(center, text(fill: azul-claro, size: 14pt)[
    DENUE 2023 · Censo 2020 · OpenStreetMap — Zona Metropolitana del Valle de México
  ])
])
