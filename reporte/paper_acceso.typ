// Paper del enfoque de acceso (F7 de PLAN_ACCESO.md) — firmado por Mario Carlos Gaitán.
// El paper del equipo (reporte/paper.typ) no se toca; este lo cita como punto de partida.
// Compilar:  typst compile --root . reporte/paper_acceso.typ reporte/paper_acceso.pdf
// Cada cifra sale de outputs/auditoria/*.json (los JSON mandan sobre PLAN_ACCESO.md).

#let FIG = "/outputs/figuras/"

#set document(
  title: [Islas de bajo acceso a la atención primaria pública en CDMX y el Estado de México],
  author: "Mario Carlos Gaitán",
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
#show table: set text(size: 8.5pt)

// ── Título y resumen (ancho completo) ──────────────────────────────────────
#place(top + center, scope: "parent", float: true, clearance: 1.4em)[
  #text(size: 16pt)[
    Islas de bajo acceso a la atención primaria pública\ en la Ciudad de México y el Estado de México
  ]
  #v(0.7em)
  #text(size: 10.5pt)[Mario Carlos Gaitán]
  #v(0.3em)
  #text(size: 9pt, style: "italic")[
    Datos: CLUES (DGIS, oct. 2026) y Recursos Salud Sectorial 2025 · Censo 2020 (INEGI) · Índice de marginación urbana 2020 (CONAPO) · OpenStreetMap · GTFS de SEMOVI
  ]
  #v(0.9em)
  #block(width: 84%)[
    #set text(size: 9pt)
    #set par(justify: true, first-line-indent: 0em)
    _Resumen_ — Un trabajo previo del equipo buscó huecos topológicos ($H_1$) en la nube de establecimientos de salud y encontró que esos huecos captan solo parte de la población lejana. Aquí cambiamos el objeto de estudio: en lugar de la geometría de los puntos, analizamos una superficie de acceso que combina oferta y demanda. Con 898 unidades públicas de primer nivel del catálogo CLUES, ponderadas por sus 4,668 médicos, y 7.3 millones de personas sin afiliación a servicios de salud repartidas en una rejilla de 100 m sobre las AGEB urbanas, calculamos un índice E2SFCA con una cuenca de 30 minutos a pie por la red de calles. 3.21 millones de personas tienen menos de la mitad del acceso de referencia (27.8% en CDMX y 52.2% en el Estado de México) y 1.13 millones no alcanzan ninguna unidad. La persistencia $H_0$ de esa superficie resume el déficit en 760 islas estables que contienen el 86.6% de la población con acceso bajo. Las islas no son una prueba estadística: frente a un nulo espacial calibrado no hay exceso de acceso bajo dentro de islas, aunque el mapa observado tiene más islas (990 contra 779). Al simular nuevas sedes de tres médicos, una selección voraz de 49 sedes (147 médicos) reduce la brecha modelada un 25%; ampliar las unidades saturadas requiere 696 médicos para lo mismo. El transporte público de la CDMX baja el acceso bajo de 27.1% a 21.1% en la ciudad, casi no cambia el Estado de México, donde el GTFS disponible apenas tiene cobertura, y el cambio del índice de concentración por marginación es indeterminado.
  ]
]

= Introducción

El trabajo previo del equipo [1] aplicó persistencia homológica al Alpha Complex de los establecimientos de salud del DENUE y detectó 71 huecos $H_1$ en CDMX y 209 en el Estado de México (EDOMEX). Su propia auditoría mostró el límite del enfoque: con la red pública, los discos de los huecos captaban el 53.0% de las personas lejanas en CDMX y el 48.6% en EDOMEX, y un modelo que buscaba directamente a quien estaba lejos rendía más que uno basado en huecos. Un hueco en la nube de puntos describe la forma de la red, pero no dice si la gente de alrededor tiene acceso.

Este trabajo conserva la topología y cambia lo que se mide. El objeto es un campo discreto de _acceso potencial_ sobre la rejilla de las AGEB urbanas, que toma en cuenta tres cosas: qué tan lejos está cada unidad, cuántos médicos tiene y cuánta gente compite por ellos. Sobre esa superficie, la persistencia de dimensión cero ($H_0$) encuentra _islas_: regiones conexas de acceso bajo, con nacimiento, profundidad y extensión. La pregunta cambia de «¿dónde faltan puntos?» a «¿dónde hay gente con poco acceso, cuánta es y qué la sacaría de ahí?».

Las contribuciones son cinco: (i) un índice E2SFCA [2, 3] por la red peatonal de OpenStreetMap, con oferta oficial CLUES y demanda censal en rejilla de 100 m; (ii) una partición de la superficie en islas $H_0$ estables ante la incertidumbre de la capacidad; (iii) pruebas contra dos tipos de nulo, uno espacial y uno de reubicación de la oferta, para separar lo que la topología describe de lo que prueba; (iv) una comparación de estrategias de expansión (dónde abrir y cuántas unidades) con una cota de calidad de la heurística; y (v) una sensibilidad con transporte público y su efecto sobre la equidad.

= Datos

*Oferta.* Del Catálogo de Establecimientos en Salud (CLUES, DGIS, corte de octubre de 2026) tomamos las unidades públicas de primer nivel de IMSS-Bienestar, la Secretaría de Salud y las unidades médicas rurales del IMSS: 1,321 en CDMX y EDOMEX. El 98.8% tiene coordenadas utilizables y capacidad observada en Recursos Salud Sectorial 2025. La capacidad principal son los médicos generales, familiares y pasantes (mediana 3 por unidad); los consultorios se usan como sensibilidad. Una unidad entra al modelo si alguna celda con demanda está a 1,667 m o menos en línea recta: de 1,306 unidades utilizables pasan 907, y 898 tienen médicos (4,668 en total). Esta regla y la elección de médicos como capacidad se decidieron después de la primera corrida, porque sin el filtro entraban unidades rurales sin población cerca. Frente al DENUE público, solo 675 de las 1,306 unidades CLUES se emparejan uno a uno a 200 m o menos; de las 631 sin pareja, 609 están en EDOMEX, sobre todo unidades rurales de uno o dos núcleos básicos. Por eso CLUES sustituye al DENUE como fuente de oferta.

*Demanda.* Del Censo 2020 tomamos `PSINDER`, las personas sin afiliación a servicios de salud, en las AGEB urbanas de ambas entidades (141 municipios y alcaldías). La población de cada AGEB se reparte uniformemente en una rejilla de 100 m: 7,304,586 personas, 2.48 M en CDMX y 4.83 M en EDOMEX. `PSINDER` mide falta de afiliación, no falta de atención ni uso de servicios.

*Red y marginación.* La red peatonal de OpenStreetMap tiene 4.59 M de nodos. El grado de marginación urbana 2020 de CONAPO se asigna por AGEB y define la _prioridad_: acceso bajo y marginación Alta o Muy alta.

= Método

== Índice de acceso E2SFCA

El método de cuenca flotante en dos pasos [2], en su versión con decaimiento [3], calcula primero la razón de cada unidad $j$ y después la suma de las razones que alcanzan a cada celda $i$:

$ R_j = C_j / (sum_i P_i w(d_(i j))), quad A_i = sum_j R_j w(d_(i j)), $

donde $C_j$ son los médicos, $P_i$ las personas sin afiliación y $d_(i j)$ la distancia por calle ($R_j = 0$ si nadie alcanza la unidad). El peso es gaussiano truncado, con $w(0) = 1$, $w(d_0) = 0$ y cero fuera de la cuenca:

$ w(d) = (e^(-(d slash d_0)^2 slash 2) - e^(-1 slash 2)) / (1 - e^(-1 slash 2)), quad d <= d_0. $

La cuenca es $d_0 = 2,250$ m, 30 minutos a 4.5 km/h. El acceso relativo es $f_i = A_i slash overline(A)$, con la referencia fija $overline(A) = sum_j C_j slash sum_i P_i = 0.639$ médicos por mil personas, la razón bruta de toda la zona. Una celda tiene _acceso bajo_ si $f_i < 0.5$, es decir, menos de la mitad del acceso de referencia. Por construcción $sum_i P_i f_i$ es constante si ninguna unidad queda sin demanda: el índice redistribuye la oferta y no la crea.

Las distancias se calcularon primero en línea recta multiplicadas por un rodeo de 1.35 y después por la red con Dijkstra. En una muestra de 200 unidades y 97,952 pares a 300–1,667 m en recta, el rodeo mediano fue de 1.40, así que el factor 1.35 era razonable en promedio, pero el 14.7% de esos pares queda fuera de la cuenca por calle. La versión por calle es la principal.

== Islas: persistencia $H_0$ de la superficie

Sobre la rejilla con vecindad de ocho celdas se filtra la superficie por subniveles [7]: al subir un nivel $t$, aparecen las celdas con $f < t$ y se unen en componentes. Cada componente nace en el mínimo de su cuenca y muere cuando se une con una más profunda (regla del más viejo). Una _isla_ es un par $(b, d)$ con nacimiento $b < 0.5$ y persistencia $d - b >= 0.25$; su territorio es la componente de ${f < d}$ conexa a su mínimo, y cada celda se asigna a la cuenca más pequeña que la contiene. Las componentes que no mueren (esenciales, en regiones de la rejilla separadas del resto) se recortan a ${f < 1}$ y se llaman _aisladas_; una esencial que comparte región con otro mínimo seleccionado se reporta aparte como _resto de región_.

La capacidad tiene incertidumbre: entre consultorios y médicos puede cambiar mucho el peso de una unidad. Por eso hay 100 réplicas en las que la capacidad de cada unidad se sortea como un entero uniforme entre esos dos valores, recalculando la referencia. Una isla es _estable_ si en al menos el 80% de las réplicas tiene pareja uno a uno con índice de Jaccard $J >= 0.5$ entre cuencas. Como solo cambia la capacidad, los ceros se conservan en todas las réplicas, y eso favorece la estabilidad de las islas que nacen en cero.

== Nulos

La persistencia describe la superficie, pero toda superficie suave tiene cuencas. Para saber qué es propio de los datos usamos dos nulos. El *nulo espacial N2* (999 réplicas) fija las celdas con acceso cero y conserva la distribución de los valores positivos por remapeo de rangos; los positivos se simulan con una tendencia suave, una rampa según la distancia al cero más cercano y un campo aleatorio calibrado para reproducir el correlograma hasta 2 km (diferencia máxima 0.024, con tolerancia 0.05). El *nulo de oferta S1* (999 réplicas) reubica, con reemplazo, las unidades de cada municipio en sitios de una rejilla de 500 m, con probabilidad proporcional a la población sin afiliación a 15 minutos por calle; cada unidad conserva sus médicos. S1 es una regla que sigue a la demanda, no un azar uniforme. El primero pregunta si las islas son más de lo que da una superficie parecida; el segundo, si la ubicación actual es mejor o peor que esa regla.

== Expansión de la oferta

Los candidatos son 13,646 sitios: los de una rejilla de 500 m con población más los mínimos de las islas estables, evaluados por calle. Cada sede nueva tiene tres médicos (la mediana actual) y se evalúan cuatro objetivos: cobertura nueva a 15 minutos (MCLP [4]), reducción de la distancia a la unidad más cercana (p-mediana, truncada a 30 min), cierre de la brecha en el peor decil y cierre de la brecha total. Todos ponderan a las personas con peso doble $m_i = 2$ si su AGEB tiene marginación Alta o Muy alta. La _brecha_ es $sum_i P_i m_i max(0, 0.5 - f_i)$, con la referencia fija: 1.31 M en la línea base (1.05 M sin el peso doble). La selección es voraz; se reporta la cota de Minoux [9] (la ganancia lograda más las $K$ mayores ganancias marginales restantes) y, para el MCLP con $K = 10$, el óptimo exacto. Para saber _cuántas_ sedes harían falta, se agregan una por una hasta 500 y se compara con _ampliar_: sumar tres médicos a una unidad saturada (razón $R_j$ por debajo de la mediana de las positivas), hasta tres veces por unidad.

== Transporte público

Con r5py 1.1.7 [5] sobre R5 y el GTFS de SEMOVI (copia de MobilityDatabase del 9 de marzo de 2026; sus calendarios vencen en 2025) se calcularon tiempos de la unidad a la celda, como aproximación al viaje del paciente, con la mediana de las salidas del 14 de octubre de 2025 entre las 8:00 y las 9:00 y tope de 30 minutos. En una muestra, invertir la dirección deja igual la clase de acceso bajo del 99.6% de la gente. Como control se repitió la caminata en el mismo motor: coincide con la red propia (Spearman 0.99 y 98% de la gente con la misma clase), así que el efecto modelado del transporte se estima comparando transporte más caminata contra caminata, ambos en R5. El GTFS no incluye Mexibús, Mexicable ni combis: en EDOMEX solo el 4.7% de la población sin afiliación vive a 500 m o menos de una parada incluida, contra 84.4% en CDMX.

La equidad se mide con el índice de concentración [6] del acceso, $"CI" = 2 "cov"_w (f, R) slash overline(f)_w$, ponderado por `PSINDER`, con $R$ el rango fraccional de la más a la menos marginada según el índice CONAPO de su AGEB (rangos medios en empates; se excluyen 1,961 personas sin grado). El intervalo del cambio $Delta "CI"$ es percentil, con 1,000 remuestreos pareados de municipios con reemplazo, estratificados por entidad.

Los notebooks documentan sus criterios de decisión en el encabezado. Las decisiones tomadas después de una primera corrida (el filtro de oferta, los médicos como capacidad y la rampa de N2) se marcan como tales en el texto.

= Resultados

== Magnitud y geografía del acceso bajo

Por calle, 3.21 M de personas sin afiliación tienen acceso bajo y 1.13 M tienen $f = 0$: ninguna unidad a 30 minutos a pie. En CDMX es el 27.8% y en EDOMEX el 52.2% (@fig-mapa). El acceso bajo no es solo cuestión de distancia. En CDMX, el 22.4% de la población sin afiliación tiene acceso bajo y ninguna unidad a 15 minutos, y otro 5.4% tiene acceso bajo pese a tener una unidad a 15 minutos o menos. En EDOMEX las cifras son 44.5% y 7.7%. Un indicador de cercanía, como el del trabajo previo, no ve a ese segundo grupo.

La prioridad, acceso bajo con marginación Alta o Muy alta, suma 806 mil personas: el 2.0% de la población sin afiliación de CDMX y el 15.7% de la de EDOMEX.

#figure(
  placement: top,
  scope: "parent",
  image(FIG + "acceso_calle_mapa.png", width: 86%),
  caption: [Acceso relativo $f$ por calle (cuenca de 30 min a pie). En rojo, $f < 0.5$.],
) <fig-mapa>

El cambio de recta a calle mueve poco el agregado: 3.19 M contra 3.21 M, Spearman 0.91, y el 91% de quien tenía acceso bajo en recta lo sigue teniendo por calle. El cambio está en el detalle: 302 mil personas entran a acceso bajo y 285 mil salen.

== Islas

La persistencia por calle selecciona 1,112 islas; sin los 122 restos de región quedan 990, de las cuales 760 son estables: 123 en CDMX y 637 en EDOMEX (la entidad es la de su mínimo; una cuenca puede cruzar el límite). Contienen 2.78 M de las 3.21 M de personas con acceso bajo (86.6%), y 2.71 M de ellas están en islas cuyo mínimo vale $f = 0$ (@fig-islas). Eso no significa que toda la isla tenga acceso cero: las personas con $f = 0$ son 1.13 M. Las islas convierten un mapa continuo en una lista de zonas con nombre, tamaño y profundidad.

#figure(
  placement: top,
  scope: "parent",
  image(FIG + "persistencia_calle.png", width: 86%),
  caption: [Islas estables por calle y su diagrama de persistencia. Cada punto es un par finito (nacimiento, muerte); se omiten las esenciales. Las líneas marcan el nacimiento 0.5 y la persistencia 0.25.],
) <fig-islas>

Las islas individuales dependen de la red. Entre recta y calle, solo el 64.3% de las islas estables en recta tiene pareja con $J >= 0.5$ por calle, y solo el 28.4% de las de calle tiene pareja en recta, aunque el 85% de la población con acceso bajo de las islas en recta cae en islas con pareja. El mapa binario $f < 0.5$ coincide más que la unión de cuencas ($J = 0.816$ contra $0.639$): la calle cambia sobre todo cómo se parte el acceso bajo en islas.

== Lo que las islas prueban y lo que no

@tab-nulos resume los contrastes. Con N2, el 88.0% de la población con acceso bajo cae dentro de las 990 islas, contra una mediana de 90.2% en el nulo, cada uno sobre su propia población bajo el umbral ($p = 0.806$, cola superior). El contraste principal no detecta exceso de acceso bajo dentro de islas frente a N2. En un contraste secundario hay más islas que en el nulo (990 contra 779, $p = 0.002$ bilateral): el acceso bajo observado está más fragmentado que una superficie comparable. Por isla, con corrección de Benjamini–Hochberg al 5% y también con el criterio estricto de máximos por réplica, solo una isla finita de nacimiento positivo resulta significativa, con unas 6 personas con acceso bajo en su territorio. La persistencia de cada isla, por sí sola, no es una prueba estadística. N2 se recalibró con la rampa de distancia después de una corrida piloto.

#figure(
  table(
    columns: (auto, 1fr, auto, auto, auto),
    align: (left, left, right, right, right),
    stroke: 0.4pt, inset: 3.5pt,
    table.header([Nulo], [Estadístico], [Obs.], [Nulo (med.)], [$p$]),
    [N2], [% acceso bajo en islas], [88.0], [90.2], [0.806],
    [N2], [Número de islas (secund.)], [990], [779], [0.002],
    [S1], [Personas con acceso bajo (M)], [3.26], [3.63], [0.001],
    [S1], [Personas con $f = 0$ (M)], [1.13], [1.48], [0.001],
  ),
  caption: [Contrastes contra el nulo espacial N2 y el nulo de oferta S1 (999 réplicas cada uno). En N2, el primer $p$ es de cola superior y el segundo bilateral. En S1, $p$ es de cola inferior (menos acceso bajo que la regla). El observado en S1 usa las unidades ajustadas a los sitios de la rejilla (3.26 M; el original da 3.21 M).],
) <tab-nulos>

S1 responde otra pregunta. Si las unidades de cada municipio se reubicaran con la regla que sigue a la demanda, habría 3.63 M de personas con acceso bajo en la mediana, contra 3.26 M en el observado ajustado: la ubicación actual deja a 366 mil personas menos con acceso bajo que esa regla ($p = 0.001$). Además, solo 59.5 mil personas (1.8%) tienen acceso bajo en el observado y en menos del 20% de las réplicas. Con la oferta de cada municipio fija, la ubicación dentro del municipio explica una parte pequeña del acceso bajo por celda; este criterio no mide el efecto de cambiar la oferta total.

== Robustez

Las islas se pusieron a prueba contra varios cambios de supuestos (@tab-robustez). Para la red, los ceros y el transporte, el criterio fijado es que sobreviva al menos el 80% de las islas por conteo; para el decaimiento y el horizonte, el criterio conjunto pide $J >= 0.70$ del mapa, recuperación ponderada de al menos 70% y que los sitios base retengan al menos el 90% de la reducción del voraz del escenario. Resisten la red (cruces de OSM agregados en un escenario permisivo), la forma del decaimiento y el transporte, este último justo en el límite. No resisten los ceros sospechosos tratados con el acceso en recta (75.9%, aunque las islas emparejadas contienen el 96.4% de la población con acceso bajo) ni el horizonte: a 15 minutos el mapa es otro, con 4.18 M de personas sin ninguna unidad y solo el 8.2% de la población de las islas recuperada. Las islas son de 30 minutos a pie; otro horizonte da otro mapa y no una versión más fina del mismo.

#figure(
  table(
    columns: (1fr, auto, auto),
    align: (left, right, left),
    stroke: 0.4pt, inset: 3.5pt,
    table.header([Cambio], [Sobrevive], [Medida]),
    [Cruces de OSM agregados], [89.3%], [islas],
    [Decaimiento en escalones, 30 min], [87.5% (426)], [población],
    [Transporte público (control a pie en R5: 83.4%)], [80.4%], [islas],
    [Ceros sospechosos con el acceso en recta], [75.9%], [islas],
    [Horizonte de 15 min, gaussiano], [8.2% (128)], [población],
    [Horizonte de 15 min, escalones], [8.3% (131)], [población],
  ),
  caption: [Supervivencia de las 760 islas estables de la red propia. «Islas» cuenta islas con pareja $J >= 0.5$; «población» pondera por la población con acceso bajo asignada a las islas, y entre paréntesis va el conteo de islas recuperadas.],
) <tab-robustez>

Los ceros también se revisaron. De las 1.13 M de personas con $f = 0$, 225 mil viven en celdas con una unidad a 1,667 m o menos en recta, sospechosas de deberse a un error de la red. En el escenario permisivo de cruces, el 18% de ellas pasa a acceso positivo. La mayoría de los ceros sospechosos se mantiene, pero distinguir barreras reales de errores de mapa requiere verificación en campo.

== Dónde abrir

Con $K = 20$ sedes nuevas, los cuatro objetivos eligen lugares distintos (@tab-k20). El objetivo de brecha reduce la brecha 12.6% y saca a 85 mil personas de acceso bajo, 77 mil de ellas con prioridad. El MCLP saca a más personas (104 mil) pero reduce menos la brecha (9.4%), porque prefiere zonas densas que están cerca del umbral. Veinte sedes al azar reducen la brecha 1.8% en promedio (p95 de 2.7%). El criterio fijado pedía que la brecha mejorara el cierre sin perder más del 10% de la cobertura del MCLP: lo mejora en 34.5%, pero conserva solo el 62.6% de su cobertura ponderada, así que ningún objetivo domina. El voraz del MCLP llega al 98.3% del óptimo exacto con $K = 10$; para la brecha, la cota de Minoux garantiza al menos el 55.5% del óptimo con $K = 20$. De los 20 sitios de brecha, 12 tienen un sitio elegido a 500 m o menos en al menos el 80% de las réplicas de capacidad. Sin el peso doble por marginación, solo 4 de los 20 sitios se mantienen a 500 m o menos.

#figure(
  table(
    columns: (1fr, auto, auto, auto),
    align: (left, right, right, right),
    stroke: 0.4pt, inset: 3.5pt,
    table.header([Objetivo], [Brecha \ reducida], [Salen de \ acceso bajo], [Con \ prioridad]),
    [Brecha], [12.6%], [85 mil], [77 mil],
    [Cobertura (MCLP)], [9.4%], [104 mil], [74 mil],
    [p-mediana], [9.3%], [64 mil], [41 mil],
    [Peor 10%], [8.7%], [67 mil], [34 mil],
    [Azar (media)], [1.8%], [—], [—],
  ),
  caption: [Veinte sedes nuevas de tres médicos con cada objetivo.],
) <tab-k20>

#figure(
  placement: top,
  image(FIG + "cuantas_unidades.png", width: 100%),
  caption: [Reducción de la brecha al agregar sedes una por una, de tres médicos cada paso, con cada estrategia.],
) <fig-cuantas>

== Cuántas unidades, y abrir contra ampliar

Al agregar sedes una por una (@fig-cuantas), el objetivo de brecha reduce la brecha un 25% con 49 sedes nuevas (147 médicos, 3.1% de la oferta actual) y un 50% con 130 (390 médicos, 8.4%). Ampliar las unidades saturadas requiere 232 pasos (696 médicos, 4.7 veces más) para el 25% y no llega al 50% dentro de 500 pasos. Abrir puede llevar acceso a celdas que hoy quedan fuera de toda cuenca (el 35% de la población con acceso bajo tiene $f = 0$); ampliar solo agrega capacidad dentro de las cuencas existentes. Con sedes de siete médicos (el percentil 75) los mismos hitos se alcanzan con 27 y 78 sedes.

Estas cifras miden médicos agregados en un modelo. No incluyen suelo, construcción, personal de apoyo, horarios ni costos de operación, que pesan distinto al abrir que al ampliar.

== Transporte público y equidad

Contra el control a pie del mismo motor, el transporte baja el acceso bajo de CDMX de 27.1% a 21.1% y las personas con $f = 0$ de 182 mil a 82 mil. En EDOMEX pasa de 51.71% a 51.77% con el GTFS disponible, que casi no cubre la entidad. Salen de acceso bajo 225 mil personas y entran 79 mil: como $sum P_i f_i$ se conserva, el transporte redistribuye el acceso. De la población prioritaria salen 9 mil en términos brutos, y el saldo neto es casi nulo.

#figure(
  placement: top,
  image(FIG + "equidad_transporte.png", width: 100%),
  caption: [Cambio del acceso con transporte público por grado de marginación CONAPO: participación en la población, en las ganancias y en las pérdidas.],
) <fig-equidad>

La población en marginación Alta y Muy alta es el 21.7% de la analizada, pero recibe el 3.4% de las ganancias y carga el 3.3% de las pérdidas (@fig-equidad): el transporte casi no la toca. El grupo Bajo recibe la mayor parte de las ganancias (50.9%, con el 30.6% de la población) y el grupo Muy bajo está sobrerrepresentado: el 25.6% de las ganancias con el 9.6% de la población; en CDMX, su acceso bajo pasa de 42% a 26%. El cambio del índice de concentración es $Delta "CI" = +0.003$ (IC 95%: −0.008 a +0.015). Con la regla fijada de antemano el veredicto es _indeterminado_: con los datos disponibles no se detecta un cambio en la desigualdad del acceso, y la población más marginada casi no recibe ganancias.

= Discusión

Tres resultados se sostienen. El primero es la magnitud: 3.21 M de personas sin afiliación tienen menos de la mitad del acceso de referencia, y en EDOMEX es más de la mitad de esa población. Ese número cambia poco al pasar de recta a calle, de gaussiano a escalones o de caminar a usar el transporte de la CDMX, pero depende mucho del horizonte. El segundo es el papel de la topología. Las islas $H_0$ resumen la superficie en zonas estables ante la incertidumbre de la capacidad, y el mapa está más fragmentado que un nulo comparable. Pero la fracción de acceso bajo dentro de islas es la que daría cualquier superficie parecida, y no se demostró que decidir con islas sea mejor que optimizar directamente sobre el mapa de brecha. El tercero es la expansión: en este modelo, por médico agregado, el déficit se reduce más abriendo sedes nuevas que ampliando las existentes.

Esto completa el resultado del trabajo previo [1]. Allí, los huecos $H_1$ de la nube de puntos captaban solo parte de la gente lejana. Aquí, al medir una superficie de acceso, la topología se vuelve una herramienta de descripción y priorización sobre el objeto correcto, aunque sigue sin ser una prueba por sí misma.

*Limitaciones.* Estimamos acceso espacial potencial para la población censal sin afiliación, repartida uniformemente dentro de las AGEB urbanas. No hay datos de uso, horarios, demanda de afiliados ni disponibilidad real de consultas. La oferta combina el catálogo CLUES de 2026 con el personal de 2025, y el filtro de cercanía a la demanda, agregado después de la primera corrida, afecta la referencia regional. Los resultados dependen de la cuenca de 30 minutos, del decaimiento y del umbral $f < 0.5$; el horizonte es el supuesto más fuerte. N2 condiciona el correlograma, los ceros y la rampa; S1 fija la oferta por municipio y redondea las unidades a nodos. Las cifras de expansión dependen de los candidatos, de la capacidad asignada, del peso doble por marginación y de la referencia fija, y la heurística no es óptima. El transporte es una sola ventana horaria de 2025, de la unidad a la celda, sin Mexibús, Mexicable ni combis; la mediana de R5 tiene un ruido de simulación que no se midió y el bootstrap de CDMX tiene solo 16 alcaldías. Nada de esto prueba que una sede en esos puntos mejore la salud de nadie.

= Conclusiones

Con CLUES, la red de calles y una cuenca de 30 minutos a pie, 3.21 millones de personas sin afiliación en CDMX y EDOMEX tienen acceso bajo a la atención primaria pública, y 1.13 millones no alcanzan ninguna unidad. La persistencia $H_0$ resume ese déficit en 760 islas estables que contienen el 86.6% de la población con acceso bajo; sirven para describir y priorizar, no como prueba estadística. Con 49 sedes nuevas de tres médicos la brecha modelada baja un 25%; ampliar las unidades saturadas pide 696 médicos para lo mismo. Con el GTFS disponible, el transporte público mejora el acceso en la CDMX, casi no cambia el del Estado de México y casi no llega a la población más marginada.

#v(0.8em)
#{
  set text(size: 8.5pt)
  set par(first-line-indent: 0em)
  [
    *Referencias*

    #set par(hanging-indent: 1em)
    [1] M. C. Gaitán, R. Jiménez, A. Kiewek, J. P. Moral y L. A. Morales, «Persistencia homológica para detectar y resolver desiertos de salud en la Zona Metropolitana del Valle de México», manuscrito del equipo.

    [2] W. Luo y F. Wang, «Measures of spatial accessibility to health care in a GIS environment: synthesis and a case study in the Chicago region», _Environment and Planning B: Planning and Design_, vol. 30, núm. 6, pp. 865–884, 2003.

    [3] W. Luo y Y. Qi, «An enhanced two-step floating catchment area (E2SFCA) method for measuring spatial accessibility to primary care physicians», _Health & Place_, vol. 15, núm. 4, pp. 1100–1107, 2009.

    [4] R. Church y C. ReVelle, «The maximal covering location problem», _Papers of the Regional Science Association_, vol. 32, núm. 1, pp. 101–118, 1974.

    [5] C. Fink, W. Klumpenhouwer, M. Saraiva, R. Pereira y H. Tenkanen, «r5py: Rapid Realistic Routing with R5 in Python», Zenodo, 2022. doi:10.5281/zenodo.7060437. Motor R5 de Conveyal.

    [6] A. Wagstaff, P. Paci y E. van Doorslaer, «On the measurement of inequalities in health», _Social Science & Medicine_, vol. 33, núm. 5, pp. 545–557, 1991.

    [7] H. Edelsbrunner, D. Letscher y A. Zomorodian, «Topological persistence and simplification», _Discrete & Computational Geometry_, vol. 28, núm. 4, pp. 511–533, 2002.

    [8] Secretaría de Salud (DGIS), _Catálogo de Establecimientos en Salud (CLUES)_, archivo ESTABLECIMIENTO\_SALUD\_202610; _Recursos Salud Sectorial_ 2025. INEGI, _Censo de Población y Vivienda 2020_, resultados por AGEB urbana. CONAPO, _Índice de marginación urbana 2020_. Colaboradores de OpenStreetMap. SEMOVI, GTFS de la Ciudad de México (MobilityDatabase mdb-1830).

    [9] M. Minoux, «Accelerated greedy algorithms for maximizing submodular set functions», en _Optimization Techniques_, LNCS 7, Springer, 1978, pp. 234–243.
  ]
}
