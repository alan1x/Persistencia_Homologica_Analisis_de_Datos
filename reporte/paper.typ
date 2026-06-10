// Reporte académico — formato paper (5 páginas)
// Compilar:  typst compile --root . reporte/paper.typ reporte/paper.pdf

#let FIG = "/outputs/figuras/"

#set document(
  title: [Persistencia Homológica para Detectar y Resolver Desiertos de Salud],
  author: "Gaitán, Jiménez, Kiewek, Moral, Morales",
)
#set page(paper: "us-letter", margin: (x: 1.9cm, y: 2.2cm), numbering: "1", columns: 2)
#set columns(gutter: 0.9cm)
#set text(font: "New Computer Modern", size: 10pt, lang: "es")
#set par(justify: true, leading: 0.55em, first-line-indent: 1em)
#set heading(numbering: "1.1.")
#show heading: set text(size: 11pt)
#show heading: set block(above: 1.1em, below: 0.6em)
#set math.equation(numbering: "(1)")
#show figure.caption: set text(size: 8.5pt)
#set figure(gap: 0.5em)

// ── Título y autores (ancho completo) ──────────────────────────────────────
#place(top + center, scope: "parent", float: true, clearance: 1.4em)[
  #text(size: 16pt)[
    Persistencia Homológica para Detectar y Resolver\ Desiertos de Salud en la Zona Metropolitana del Valle de México
  ]
  #v(0.7em)
  #text(size: 10.5pt)[
    Mario Carlos Gaitán · Rodrigo Jiménez · Andrés Kiewek · Juan Pablo Moral · Luis Alan Morales
  ]
  #v(0.3em)
  #text(size: 9pt, style: "italic")[
    Análisis Topológico de Datos · Datos: DENUE 2023 (INEGI), Censo de Población y Vivienda 2020 (INEGI), OpenStreetMap
  ]
  #v(0.9em)
  #block(width: 82%)[
    #set text(size: 9pt)
    #set par(justify: true, first-line-indent: 0em)
    _Resumen_ — Las métricas tradicionales de cobertura sanitaria (densidad por km², radios fijos, conteos municipales) no detectan los _desiertos de salud estructurales_: zonas rodeadas de clínicas por fuera pero vacías por dentro. Aplicamos persistencia homológica sobre los 52,372 establecimientos de salud de CDMX y EDOMEX usando un Alpha Complex ponderado (Laguerre) que incorpora el tamaño de cada establecimiento, y detectamos 118 y 241 huecos topológicos H₁ respectivamente. Cruzando con el Censo 2020, cerca de 270,000 personas sin seguro médico habitan estos vacíos. Un score de cuatro ejes (inaccesibilidad peatonal, inequidad, persistencia topológica y marginación socioeconómica), clustering DBSCAN y un modelo de cobertura máxima (MCLP) producen recomendaciones de inversión: 7 clínicas en CDMX cubren 42,687 personas sin seguro (44.0% del total prioritario) y una estrategia subregional en EDOMEX cubre 35,868 (19.0%). La validación topológica confirma reducciones de 14.9% y 16.5% en la persistencia total.
  ]
]

= Introducción

Ciudad de México registra 21,585 establecimientos de salud y el Estado de México 30,787: no existe escasez absoluta. Sin embargo, su distribución es profundamente desigual. Las métricas convencionales no pueden detectar el tipo de vacío más peligroso: una zona completamente rodeada de infraestructura médica pero con interior vacío, donde una persona puede estar a 2 km de la clínica más cercana aunque el mapa de densidad de su colonia se vea «verde». A ese vacío lo llamamos _desierto de salud estructural_.

La topología estudia la _forma_ de los espacios, no sus medidas exactas, y la persistencia homológica [1] detecta precisamente ciclos cerrados de clínicas que rodean un espacio vacío (clases del primer grupo de homología, H₁), sin importar qué tan irregular sea su contorno. La pregunta central del trabajo es: ¿dónde están esos desiertos en CDMX y EDOMEX, cuánta población atrapan y cómo priorizar las inversiones para resolver los más críticos?

Las contribuciones del trabajo son cuatro: (i) la detección de desiertos estructurales con un Alpha Complex _ponderado_ que incorpora la capacidad de cada establecimiento; (ii) la traducción de los vacíos geométricos a impacto social mediante el cruce censal a nivel AGEB; (iii) un esquema de priorización de cuatro ejes (acceso, inequidad, topología y marginación) que alimenta un modelo de localización óptima; y (iv) una validación que usa la misma maquinaria topológica para verificar si las clínicas propuestas efectivamente cierran los vacíos que motivaron su ubicación.

= Desarrollo y metodología

== Datos

Del DENUE 2023 (INEGI) tomamos el sector SCIAN 62 (servicios de salud y asistencia social): 21,585 establecimientos en CDMX y 30,787 en EDOMEX, con coordenadas y personal ocupado (`PER_OCU`), convertido de rangos de texto a valores numéricos de capacidad. Del Censo 2020 usamos las AGEB urbanas (unidad mínima censal) con las variables `PSINDER` (personas sin derechohabiencia), `GRAPROES` (escolaridad media), `P60YMAS` (adultos mayores) y `POBTOT`. La derechohabiencia es la variable crítica: una persona sin seguro dentro de un desierto de salud no tiene alternativa de atención.

== Detección de vacíos: Alpha Complex y persistencia

Sobre las clínicas como puntos del plano se construye un Alpha Complex: al crecer un disco de radio $alpha$ alrededor de cada punto se forman aristas cuando dos discos se tocan y triángulos cuando tres se solapan. Un hueco H₁ «nace» cuando un vacío queda rodeado y «muere» cuando se triangula; su tamaño real es la

$ "persistencia" = r_"muerte" - r_"nacimiento", $

medida en metros. Los huecos cercanos a la diagonal del diagrama de persistencia son ruido; los alejados son vacíos estructurales. Por su tamaño, los huecos se clasifican en _micro_ (< 200 m, espacio entre consultorios), _medianos_ (200–400 m, varias manzanas), _grandes_ (400–700 m, escala de colonia) y _severos_ (> 700 m, escala zonal de múltiples colonias).

== Ponderación por tamaño: Weighted Alpha (Laguerre)

El Alpha clásico trata igual a una farmacia de 2 empleados que a un hospital de 300, de modo que los micro-establecimientos «rellenan» huecos que en realidad no cubren. El Weighted Alpha Complex (diagrama de Laguerre) asigna a cada establecimiento un radio de influencia

$ r_i = k dot sqrt("per_ocu"_i), $

y cada punto del plano pertenece al establecimiento que más puede cubrirlo. El efecto es sustancial (@fig-laguerre): los huecos detectados pasan de 71 a 118 en CDMX (+66.2%) y de 209 a 241 en EDOMEX (+15.3%). El cambio es mayor en CDMX por su heterogeneidad (hospitales IMSS/ISSSTE/privados conviviendo con miles de consultorios); en EDOMEX la infraestructura es más homogénea, dominada por micro-establecimientos, y el incremento es menor.

#figure(
  placement: top,
  scope: "parent",
  image(FIG + "laguerre_comparacion.png", width: 92%),
  caption: [Impacto de la topología ponderada: huecos H₁ detectados por el Alpha clásico vs el Weighted Alpha (Laguerre) y distribución de persistencias por método.],
) <fig-laguerre>

== Calibración y robustez

El umbral de persistencia mínima se calibró probando cuatro valores (@tab-umbral). A 100 m dominan micro-brechas entre consultorios adyacentes; a 400 m se pierden huecos medianos reales. Se eligió 200 m, que corresponde a vacíos de al menos una cuadra larga: para el interior del vacío la distancia a la clínica más cercana puede ser de 500 m o más. Como prueba de robustez, los 7 huecos de CDMX y los 58 de EDOMEX con persistencia mayor a 600 m aparecen en los cuatro umbrales (100% de robustez): las señales severas no son artefactos del calibrado.

#figure(
  table(
    columns: (auto, auto, auto, 1fr),
    stroke: 0.4pt, inset: 4pt,
    align: (center, center, center, left),
    table.header([Umbral], [CDMX], [EDOMEX], [Interpretación]),
    [100 m], [482], [742], [micro-brechas (ruido)],
    [200 m], [118], [241], [señal estructural],
    [400 m], [17], [91], [solo los más severos],
    [600 m], [7], [58], [escala de colonia],
  ),
  caption: [Huecos H₁ detectados según el umbral de persistencia mínima. El análisis usa 200 m.],
) <tab-umbral>

== Cruce censal y marginación

Cada hueco se cruza con las AGEB que caen dentro de su radio: 62 de los 118 huecos de CDMX y 180 de los 241 de EDOMEX están habitados (el resto cae en zonas industriales, parques o despobladas; este filtro descarta también los vacíos periurbanos de persistencia extrema). Para capturar la barrera de _uso_ además de la geográfica se construye un Índice de Marginación normalizado a $[0,1]$:

$ "IM" = 0.35 p_"ss" + 0.25 d_"esc" + 0.25 p_"60+" + 0.15 rho_"ss", $

con $p_"ss"$ la proporción sin seguro, $d_"esc"$ el déficit de escolaridad, $p_"60+"$ la proporción de adultos mayores y $rho_"ss"$ la densidad de personas sin seguro. Los pesos privilegian la barrera directa de acceso al sistema de salud (35%), seguida de la alfabetización en salud y la vulnerabilidad etaria (25% cada una).

== Accesibilidad peatonal

La distancia euclidiana subestima el costo real de traslado: vías rápidas y barrancas crean rodeos que pueden casi duplicar el trayecto. Con la red peatonal de OpenStreetMap (OSMnx [3]) se calculan isócronas y tiempos de caminata a 4.5 km/h desde el centroide de cada hueco a la clínica más cercana. El umbral de intervención es 15 minutos, respaldado por literatura de salud pública sobre consulta preventiva. Los huecos más inaccesibles de CDMX requieren 20–35 minutos (poniente y sur: Álvaro Obregón, Magdalena Contreras, Xochimilco, Tláhuac); en EDOMEX algunos superan los 40 minutos en el oriente y norte del estado (@fig-scatter).

#figure(
  placement: bottom,
  scope: "parent",
  image(FIG + "scatter_accesibilidad.png", width: 86%),
  caption: [Persistencia topológica vs tiempo de caminata a la clínica más cercana por hueco habitado. La esquina superior derecha (vacíos grandes _y_ lejanos) concentra los candidatos de máxima prioridad.],
) <fig-scatter>

== Priorización: score, DBSCAN y MCLP

Cada hueco recibe un score de cuatro ejes con pesos iguales y ranking por percentil interno a cada ciudad:

$ "score" = 0.25 (r_"tiempo" + r_"sin seguro" + r_"persist" + r_"marg"). $

El percentil evita que un eje con valores grandes domine a los demás: un hueco con 5,000 personas sin seguro no aplasta automáticamente a uno con 1,000 si este último tiene la mayor persistencia y marginación de su ciudad. La selección usa un filtro OR (basta un eje severo): tiempo mayor a 10 min, personas sin seguro sobre el percentil 60, persistencia mayor a 400 m o IM sobre el percentil 60, resultando 46 huecos prioritarios en CDMX y 77 en EDOMEX. Los descartados son micro-brechas bajas en los cuatro ejes simultáneamente.

Los huecos a menos de 1,500 m se agrupan con DBSCAN [4], pues dos huecos cercanos se resuelven con una sola clínica bien ubicada: resultan 39 clusters en CDMX y 74 en EDOMEX (casi todos unitarios, un hallazgo en sí mismo sobre la dispersión mexiquense). Cada cluster es una decisión de inversión. Finalmente, el Maximum Coverage Location Problem (MCLP) [2] se resuelve por programación lineal entera:

$ max sum_i d_i y_i quad "s.t." quad sum_j x_j = K, quad y_i <= sum_j C_(i j) x_j, $

donde $d_i = "score"_i times "pob_sin_salud"_i$ es la demanda ponderada, $x_j in {0,1}$ indica si se construye el candidato $j$ y $C_(i j) = 1$ si $j$ alcanza el hueco $i$ en ≤ 15 min por la red peatonal. La demanda ponderada integra los cuatro ejes automáticamente: cubrir un hueco con score 0.9 y 5,000 personas sin seguro tiene un orden de magnitud más impacto que cubrir uno con score 0.3 y 500 personas.

= Resultados

== Magnitud del problema

Con el umbral de 200 m sobre el complejo ponderado se detectan 118 huecos en CDMX y 241 en EDOMEX. Los conteos no son comparables directamente entre sí: EDOMEX cubre un territorio 3–4 veces mayor, con vacíos periurbanos de escala rural que el cruce censal descarta, por lo que cada ciudad se analiza por separado con percentiles internos. En los huecos habitados viven cerca de 88,000 personas sin seguro en CDMX y 182,000 en EDOMEX: alrededor de 270,000 en total, equivalente a la población de una ciudad media mexicana. Los casos extremos: un cluster de CDMX concentra 7,525 personas sin seguro a más de 12 min de caminata; uno de EDOMEX, 23,869 (33.7% de la población de la zona).

El cuarto eje cambia la asignación. El Top 10 de urgencia es estable (9 de 10 huecos mantienen posición en ambas ciudades), pero al incluir marginación 11 huecos de CDMX (IM medio 0.37) y 38 de EDOMEX (IM medio 0.49) suben tres o más posiciones en el ranking: una capa de vulnerabilidad que el análisis de acceso puro subestimaba, especialmente profunda en el Estado de México.

== CDMX: solución K=7

El MCLP se ejecutó para $K = 5, dots, 10$. La cobertura de población prioritaria crece de 33.0% (K=5) a 38.6%, 44.0%, 49.1%, 53.1% y 56.1% (K=10): los incrementos marginales caen de +5.6 y +5.3 puntos porcentuales en los primeros saltos a +4.0 (K=8→9) y +3.0 (K=9→10). K=7 es el punto donde la cobertura cruza el 44% antes de la caída sostenida de rendimientos. La solución selecciona los clusters C1, C2, C5, C7 y C8 (núcleo estable presente en toda la curva $K=5 arrow 10$, primera fase de inversión) más C16 y C19 (segunda fase), cubre 11 de 46 huecos prioritarios y 42,687 personas sin seguro, el 44.0% del total prioritario (@fig-cdmx).

#figure(
  placement: top,
  image(FIG + "fase3_CDMX_k7_mapa.png", width: 84%),
  caption: [CDMX, solución K=7: clínicas propuestas, isócronas de 15 min y huecos cubiertos (borde blanco).],
) <fig-cdmx>

La comparación de los cuatro ejes entre huecos cubiertos y persistentes muestra que el MCLP prioriza correctamente: los cubiertos tienen en promedio 2.5 veces más personas sin seguro (3,881 contra 1,555) y mayor marginación (IM de 0.35 contra 0.29), de modo que el cuarto eje efectivamente redirige la inversión hacia zonas más vulnerables. Los vacíos geométricamente más grandes (364 m de persistencia media contra 296 m de los cubiertos) tienden a quedar fuera porque son periféricos y con poca población; análogamente, los cubiertos tienen menor tiempo medio de caminata (7.89 contra 9.27 min) porque los huecos muy lejanos suelen estar despoblados y el algoritmo racionalmente los pospone.

== EDOMEX: estrategia subregional

La curva $K = 5 arrow 10$ de EDOMEX es casi lineal: la cobertura pasa de 17.6% a 26.7% a razón de unos 2 puntos porcentuales por clínica. No hay codo ni K óptimo global, porque 74 de los clusters son prácticamente unitarios y se reparten en cuatro zonas que no se comunican en 15 min: ninguna zona concentra suficiente impacto para justificar concentrar ahí la inversión. Se adoptó por ello una estrategia subregional de 3 clínicas por zona (12 presupuestadas, 9 ubicables), que cubre 35,868 personas sin seguro (19.0%) y garantiza presencia en Norte, Poniente y ZMVM-Centro (@tab-edomex). Frente al MCLP global de K=5 (32,683 personas, solo ZMVM y Poniente), la ventaja principal no es numérica sino de equidad geográfica: atiende zonas que el óptimo global nunca tocaría. La zona Oriente (12,270 personas sin seguro) carece de candidatos válidos al umbral de 15 min y requiere estrategia complementaria (umbral extendido de 20–30 min o clínicas móviles).

#figure(
  table(
    columns: (1fr, auto, auto, auto),
    stroke: 0.4pt, inset: 4pt,
    align: (left, center, center, center),
    table.header([Zona], [K], [Sin seguro cub.], [% local]),
    [Norte], [3], [1,182], [13.9%],
    [Poniente], [3], [10,243], [23.0%],
    [ZMVM-Centro], [3], [24,443], [19.7%],
    [Oriente], [3], [sin candidatos], [—],
    [Total], [9 ubic.], [35,868], [19.0%],
  ),
  caption: [EDOMEX: cobertura de la estrategia subregional 4 × 3.],
) <tab-edomex>

== Validación topológica

La misma metodología TDA verifica el efecto de las clínicas propuestas: un hueco con centroide $c$ y persistencia $r$ queda _cerrado_ si la clínica nueva cae a distancia $d < r$, _parcial_ si $r <= d < 2r$ y _persistente_ en otro caso. En CDMX (K=7) resultan 3 huecos cerrados, 4 parciales y 39 persistentes, con una reducción de 14.9% en la persistencia total; en EDOMEX (subregional) 6, 2 y 69, con reducción de 16.5% — mayor cierre geométrico que la estrategia global K=5, que solo cerraba 3 huecos. El contraste con la cobertura poblacional (44% y 19%) refleja que el MCLP optimiza _acceso_ (≤ 15 min) mientras el cierre topológico exige un criterio geométrico mucho más estricto ($d < r$ al centroide exacto): un hueco puede estar «cubierto» con una clínica a 800 m del centroide que llega en 12 min por la red vial sin quedar topológicamente cerrado. Los tres huecos cerrados de CDMX son precisamente los de mayor score compuesto, que el MCLP colocó con precisión dentro del radio topológico.

= Discusión

Un mapa de densidad concluiría que el acceso en CDMX está garantizado: tiene un orden de magnitud más establecimientos por km² que las zonas rurales. La persistencia homológica revela que, aun con 21,585 clínicas, existen decenas de vacíos estructurales con cerca de 88,000 personas sin seguro atrapadas dentro. La diferencia es cualitativa: los métodos de densidad miden _cuánto_ hay; la topología mide la _forma_ de lo que hay, y la forma importa precisamente cuando la distribución es heterogénea — el caso de todas las zonas metropolitanas de América Latina. El análisis de robustez (cuatro umbrales) y la validación de cierre dan a las recomendaciones una trazabilidad metodológica que los rankings ad hoc no ofrecen.

= Conclusiones

El problema es estructural, no de escasez: con más de 52,000 establecimientos existen 359 vacíos topológicos genuinos, y su _forma_ importa tanto como la cantidad. La ponderación por tamaño cambia la geografía del riesgo: Laguerre revela 47 huecos adicionales en CDMX (+66%) invisibles para el Alpha clásico. El impacto es medible: cerca de 270,000 personas sin seguro habitan estos desiertos. Las recomendaciones son accionables: 7 clínicas en CDMX (fases C1–C2–C5–C7–C8 y luego C16–C19) cubren el 44.0% de la población prioritaria; en EDOMEX la estrategia subregional 4 × 3 cubre el 19.0% y garantiza equidad geográfica. El cuarto eje de marginación redirige la inversión hacia zonas socioeconómicamente vulnerables que el análisis de acceso puro subestimaba.

Las principales limitaciones son cuatro. Primera, los tiempos masivos por hueco se aproximaron con distancia euclidiana multiplicada por 1.35, con error estimado de ±15% en zonas de topografía irregular; la mejora natural es extender la red peatonal OSMnx completa a cada subregión. Segunda, existe un desfase temporal de 2–3 años entre el Censo 2020 y el DENUE 2023, corregible con la actualización trimestral del DENUE. Tercera, el índice de marginación es propio y no está calibrado contra el índice oficial de CONAPO, con el que convendría cruzarlo. Cuarta, la zona Oriente de EDOMEX queda sin candidatos al umbral de 15 minutos y exige instrumentos complementarios (umbrales extendidos, unidades móviles o telemedicina). Con todo, la metodología es replicable en cualquier zona metropolitana que cuente con datos censales y de establecimientos georreferenciados.

#v(0.8em)
#{
  set text(size: 8.5pt)
  set par(first-line-indent: 0em)
  [
    *Referencias*

    #set par(hanging-indent: 1em)
    [1] H. Edelsbrunner y J. Harer, _Computational Topology: An Introduction_. AMS, 2010.

    [2] R. Church y C. ReVelle, «The maximal covering location problem», _Papers of the Regional Science Association_, vol. 32, 1974.

    [3] G. Boeing, «OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks», _Computers, Environment and Urban Systems_, vol. 65, 2017.

    [4] M. Ester, H.-P. Kriegel, J. Sander y X. Xu, «A density-based algorithm for discovering clusters in large spatial databases with noise», _Proc. KDD_, 1996.

    [5] INEGI, _Directorio Estadístico Nacional de Unidades Económicas (DENUE)_ 2023; _Censo de Población y Vivienda_ 2020.
  ]
}
