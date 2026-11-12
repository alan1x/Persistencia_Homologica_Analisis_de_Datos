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
    _Resumen_ — Las métricas tradicionales de cobertura sanitaria (densidad por km², radios fijos, conteos municipales) no detectan los _vacíos estructurales_: zonas rodeadas de establecimientos de salud por fuera pero vacías por dentro. Aplicamos persistencia homológica al Alpha Complex clásico de los 52,372 establecimientos de salud de CDMX y EDOMEX y encontramos 71 y 209 huecos H₁ con persistencia de al menos 200 m. Un Alpha ponderado (Laguerre) da 118 y 241, pero casi todo el aumento viene de la escala del peso y no de los hospitales, por lo que lo usamos solo como sensibilidad. Cruzando con el Censo 2020, unas 325,500 personas sin seguro médico viven dentro de los vacíos habitados (62 de 71 y 99 de 209). Un score de cuatro ejes, DBSCAN y un modelo de cobertura máxima (MCLP) proponen 7 clínicas en CDMX y 8 en EDOMEX. Al medir directamente el cierre, las clínicas cierran 1 de 46 y 2 de 77 huecos prioritarios, y su valor está en alcanzar personas, no en cambiar la topología. Además, solo 0.9% y 5.0% de las personas dentro de esos discos están a más de 833 m de un establecimiento: buscar directamente a quienes están lejos da más acceso nuevo que ubicar clínicas según los huecos.
  ]
]

= Introducción

Ciudad de México registra 21,585 establecimientos de salud y el Estado de México 30,787: no existe escasez absoluta. Sin embargo, su distribución es desigual. Las métricas convencionales no detectan una zona rodeada de infraestructura médica pero con interior vacío, aunque el mapa de densidad de su colonia se vea «verde». A ese vacío lo llamamos _vacío estructural_. Aquí «establecimientos de salud» es el sector SCIAN 62 completo; un tercio son dentistas y también incluye asistencia social.

La topología estudia la _forma_ de los espacios, y la persistencia homológica [1] detecta ciclos cerrados de establecimientos que rodean un espacio vacío (clases del primer grupo de homología, H₁), sin importar qué tan irregular sea su contorno. La pregunta central es: ¿dónde están esos vacíos en CDMX y EDOMEX, cuánta población sin seguro hay dentro y qué tan útil es la topología para decidir dónde poner clínicas nuevas?

Las contribuciones son cuatro: (i) la detección de vacíos estructurales con el Alpha Complex clásico, con el Alpha ponderado como análisis de sensibilidad; (ii) el cruce censal a nivel AGEB para estimar la población dentro de cada vacío; (iii) un esquema de priorización de cuatro ejes que alimenta un modelo de localización; y (iv) una auditoría que mide directamente si las clínicas propuestas cierran los huecos, prueba la robustez perturbando los datos y compara contra un modelo que busca acceso nuevo sin usar la topología.

= Desarrollo y metodología

== Datos

Del DENUE 2023 (INEGI) tomamos el sector SCIAN 62 (servicios de salud y asistencia social): 21,585 establecimientos en CDMX y 30,787 en EDOMEX, con coordenadas y personal ocupado (`PER_OCU`), convertido de rangos de texto a valores numéricos. Del Censo 2020 usamos las AGEB urbanas con las variables `PSINDER` (personas sin derechohabiencia), `GRAPROES` (escolaridad media), `P60YMAS` (adultos mayores) y `POBTOT`. `PSINDER` mide falta de afiliación, no falta de atención.

== Detección de vacíos: Alpha Complex y persistencia

Sobre los establecimientos como puntos del plano se construye un Alpha Complex: al crecer un disco de radio $alpha$ alrededor de cada punto se forman aristas cuando dos discos se tocan y triángulos cuando tres se solapan. Un hueco H₁ «nace» cuando un vacío queda rodeado y «muere» cuando los discos lo llenan. Su persistencia es

$ "persistencia" = r_"muerte" - r_"nacimiento", $

medida en metros. El radio del disco vacío es la muerte, no la persistencia: en la mediana la muerte es 1.75 veces la persistencia en CDMX y 2.85 en EDOMEX. Los huecos cercanos a la diagonal del diagrama son ruido. Por tamaño se clasifican en _micro_ (< 200 m), _medianos_ (200–400 m), _grandes_ (400–700 m) y _severos_ (> 700 m). Todo el análisis posterior usa el Alpha clásico.

== Ponderación por tamaño: sensibilidad con Laguerre

El Alpha ponderado (diagrama de Laguerre) asigna a cada establecimiento un radio de influencia

$ r_i = 50 + 30 sqrt("per_ocu"_i), $

entre 102 y 570 m en estos datos. Da 118 huecos en CDMX y 241 en EDOMEX, contra 71 y 209 del clásico (+66% y +15%). Ese aumento no se debe a la heterogeneidad de los hospitales (@fig-laguerre): con el mismo peso para todos los establecimientos salen 116 y 240, y con pesos barajados 115.1 y 239.6 en promedio. La persistencia se mide como $sqrt(alpha')$ de muerte menos $sqrt(alpha')$ de nacimiento con $alpha' = alpha - r^2$, y esa diferencia crece al acercarse a cero; además los nacimientos negativos se recortan a 0. La ponderación sí cambia _cuáles_ huecos aparecen (36 de los 118 de CDMX no tienen equivalente a 500 m con pesos iguales), pero no explica _cuántos_ hay. Por eso es una sensibilidad: 42 de 46 y 74 de 77 huecos prioritarios clásicos tienen un hueco de Laguerre a menos de 500 m.

#figure(
  placement: top,
  scope: "parent",
  image(FIG + "auditoria_laguerre_artefacto.png", width: 80%),
  caption: [Conteo de huecos según el radio. Pesos iguales, que no distinguen hospitales de consultorios, reproducen casi todo el aumento atribuido a Laguerre.],
) <fig-laguerre>

== Calibración y robustez

El umbral de persistencia mínima se calibró con cuatro valores (@tab-umbral). A 100 m dominan micro-brechas entre consultorios adyacentes; a 400 m se pierden huecos medianos. Se eligió 200 m. La prueba de que los huecos de más de 600 m aparecen en los cuatro umbrales no puede fallar, porque se cumple por definición; no es evidencia de robustez. Por eso perturbamos los _datos_ y recalculamos todo (40 réplicas): con ruido de σ = 100 m sobrevive 93% de los huecos de al menos 400 m, contra cerca de 50% de los menores (Spearman 0.84 y 0.81), así que la persistencia sí predice estabilidad. Pero la lista exacta de prioridades es frágil: con σ = 50 m solo 22 de 46 huecos en CDMX y 50 de 77 en EDOMEX sobreviven en al menos 80% de las réplicas. Un nulo con σ = 1,000 m da 57 y 361 huecos, y casi nunca en los mismos lugares que los reales; es exploratorio y no da valores p.

#figure(
  table(
    columns: (auto, auto, auto, 1fr),
    stroke: 0.4pt, inset: 4pt,
    align: (center, center, center, left),
    table.header([Umbral], [CDMX], [EDOMEX], [Interpretación]),
    [100 m], [286], [544], [micro-brechas (ruido)],
    [200 m], [71], [209], [señal estructural],
    [400 m], [16], [90], [solo los más severos],
    [600 m], [6], [57], [escala de colonia],
  ),
  caption: [Huecos H₁ del Alpha clásico según el umbral de persistencia mínima. El análisis usa 200 m.],
) <tab-umbral>

== Cruce censal y marginación

Cada hueco se cruza con las AGEB bajo su disco vacío (radio igual a la muerte, centro exacto), repartiendo la población de cada AGEB por área, es decir, suponiendo población uniforme dentro de la AGEB. Resultan habitados 62 de los 71 huecos de CDMX y 99 de los 209 de EDOMEX; el resto cae en zonas industriales, parques o despobladas. Para incluir la barrera de _uso_ se construye un Índice de Marginación (IM) normalizado a $[0,1]$:

$ "IM" = 0.35 p_"ss" + 0.25 d_"esc" + 0.25 p_"60+" + 0.15 rho_"ss", $

con $p_"ss"$ la proporción sin seguro, $d_"esc"$ el déficit de escolaridad, $p_"60+"$ la proporción de adultos mayores y $rho_"ss"$ la densidad de personas sin seguro. Como incluye la proporción sin seguro (Spearman 0.55 y 0.75 con esa variable), en parte repite otro eje; es un índice propio, no el de CONAPO.

== Accesibilidad: tiempos estimados

Los tiempos de caminata se estiman con la distancia euclidiana multiplicada por 1.35, desde el baricentro del hueco al establecimiento más cercano, a 4.5 km/h; no se usó la red vial. El umbral de 15 minutos equivale a un radio efectivo de 833 m. En CDMX la mediana es 7.6 min, el máximo 23.9 y 4 de 62 huecos pasan de 15 min; en EDOMEX la mediana es 9.6, el máximo 41.2 y 16 de 99 pasan de 15 min (@fig-scatter). Solo 3 huecos por ciudad tienen mapa con red OSM real (OSMnx [3]), como ilustración.

#figure(
  placement: bottom,
  scope: "parent",
  image(FIG + "scatter_accesibilidad.png", width: 80%),
  caption: [Persistencia vs tiempo estimado (euclidiana × 1.35) al establecimiento más cercano, por hueco habitado.],
) <fig-scatter>

== Priorización: score, DBSCAN y MCLP

Cada hueco recibe un score de cuatro ejes con pesos iguales y ranking por percentil dentro de cada ciudad:

$ "score" = 0.25 (r_"tiempo" + r_"sin seguro" + r_"persist" + r_"marg"). $

La selección usa un filtro OR (basta un eje severo): tiempo mayor a 10 min, personas sin seguro sobre el percentil 60, persistencia mayor a 400 m o IM sobre el percentil 60. Resultan 46 huecos prioritarios en CDMX y 77 en EDOMEX. Los huecos a menos de 1,500 m se agrupan con DBSCAN [4]: 39 clusters en CDMX y 74 en EDOMEX, casi todos unitarios en EDOMEX. Cada cluster es un candidato. El MCLP [2] se resuelve por programación lineal entera:

$ max sum_i d_i y_i quad "s.t." quad sum_j x_j = K, quad y_i <= sum_j C_(i j) x_j, $

donde $x_j in {0,1}$ indica si se construye el candidato $j$ y $C_(i j) = 1$ si $j$ alcanza el hueco $i$ a una distancia euclidiana × 1.35 de a lo más 15 min (833 m). En CDMX $d_i = "score"_i times "personas"_i$. En la estrategia subregional de EDOMEX y en la curva de $K$, $d_i$ son solo las personas sin seguro, aunque el título de algunas figuras diga otra cosa.

= Resultados

== Magnitud del problema

Con el umbral de 200 m y el Alpha clásico se detectan 71 huecos en CDMX y 209 en EDOMEX. Los conteos no son comparables entre sí: EDOMEX cubre un territorio mucho mayor, así que cada ciudad se analiza por separado. En los discos vacíos de los huecos habitados viven unas 325,500 personas sin seguro (115,390 en CDMX y 210,153 en EDOMEX), bajo población uniforme por AGEB. Dos casos: un cluster de CDMX con 7,525 personas sin seguro (31.9% de la población de la zona, tiempo máximo 10.2 min) y uno de EDOMEX con 23,869 (33.0%, máximo 13.8 min).

La topología describe bien la forma de la red, pero los huecos no son donde la gente está lejos: dentro de los discos prioritarios solo 784 de 91,632 personas (0.9%) en CDMX y 8,900 de 179,612 (5.0%) en EDOMEX están a más de 833 m de cualquier establecimiento, porque casi todos los discos son más chicos que ese radio. Las prioridades también dependen de qué se cuenta: solo 19 de 46 y 34 de 77 huecos prioritarios tienen un hueco de la red de consultorios médicos y hospitales dentro de su disco, y 7 y 19 de la red pública.

== CDMX: solución K=7

El MCLP se ejecutó para $K = 5, dots, 10$. Con solo personas, la cobertura crece de 33.0% a 38.6%, 44.0%, 49.1%, 53.1% y 56.1%. El incremento cae de +5.1 a +4.0 puntos en K=8→9, así que un codo sugeriría K=8; K=7 es una decisión de presupuesto, no un codo. Con K=7 la selección es la misma con score × personas y con solo personas, y es el óptimo exacto (se comprobaron las 77,520 combinaciones). Selecciona los clusters C1, C2, C5, C7 y C8 (el núcleo estable con score × personas, primera fase) más C16 y C19 (segunda fase). Alcanza 42,687 personas sin seguro contando una persona una vez por cada hueco que la contiene; contando cada persona una sola vez son 26,281, contra un azar con p95 de 18,363 (@fig-cdmx).

#figure(
  placement: top,
  image(FIG + "modelo_ubicaciones.png", width: 92%),
  caption: [Ubicaciones propuestas por cada modelo para CDMX y EDOMEX.],
) <fig-cdmx>

Los huecos cubiertos tienen en promedio 2.5 veces más personas sin seguro que los persistentes (3,881 contra 1,555) y menor tiempo medio (7.89 contra 9.27 min); los vacíos de mayor persistencia (364 m contra 296 m) quedan fuera por periféricos y con poca población. El cuarto eje sí cambia a quién se invierte en CDMX K=7: 2 de las 7 clínicas son otras (C16 y C19 en vez de C3 y C17), con 42,687 contra 39,974 personas. En EDOMEX K=8 global no cambia ninguna.

== EDOMEX: estrategia subregional

La curva $K = 5 arrow 10$ de EDOMEX es casi lineal (de 17.6% a 26.7%) y no hay K óptimo global. Se adoptó una estrategia subregional con hasta 3 clínicas por zona. Resultan 8 clínicas: Norte 2 (solo tiene 2 candidatos), Poniente 3, ZMVM-Centro 3 y Oriente 0. Cubren 35,868 personas sin seguro según el conteo del reporte (19.0%) y 17,082 contando cada persona una vez, por debajo del azar con p95 de 18,674. Frente al MCLP global de K=5 son 3 clínicas más. Oriente quedó sin clínicas porque sus 6 clusters quedaron fuera del corte de 20 candidatos, no por falta de candidatos válidos (@tab-edomex).

#figure(
  table(
    columns: (1fr, auto, auto, auto),
    stroke: 0.4pt, inset: 4pt,
    align: (left, center, center, center),
    table.header([Zona], [Clínicas], [Sin seguro cub.], [% local]),
    [Norte], [2], [1,182], [13.9%],
    [Poniente], [3], [10,243], [23.0%],
    [ZMVM-Centro], [3], [24,443], [19.7%],
    [Oriente], [0], [corte de 20 candidatos], [—],
    [Total], [8], [35,868], [19.0%],
  ),
  caption: [EDOMEX: estrategia subregional, conteo del reporte.],
) <tab-edomex>

== Cierre medido de los huecos

Para saber si las clínicas cierran los huecos, se agregan a la nube de puntos, se recalcula la persistencia con el Alpha clásico y se sigue cada hueco prioritario. Un hueco queda _cerrado_ si no queda ninguno de al menos 200 m en su lugar. En CDMX (K=7) se cierra 1 de 46 huecos (13 modificados y 32 intactos) y en EDOMEX 2 de 77 (8 y 67). La persistencia total baja 2.3% y 7.4%. Con selección al azar baja 5.5% (p5 a p95: 2.8 a 8.0) y 7.4% (5.0 a 9.5): el MCLP no supera al azar en persistencia. Una clínica no cierra un hueco grande sino que lo parte, y los más grandes de CDMX (1,510 y 1,292 m) quedan intactos. La regla geométrica anterior ($d < r$ al centroide) daba 3 y 6 cerrados y reducciones de 14.9% y 16.5%; no se sostiene al medir. Las clínicas se justifican por acceso de personas, no por cierre de huecos.

== Modelo revisado y acceso nuevo

Definimos dos medidas con una sola regla de conteo (cada persona una vez, rejilla de 100 m): _vacío alcanzado_, personas sin seguro dentro de discos prioritarios a ≤ 833 m de una clínica, y _acceso nuevo_, personas hoy a más de 833 m que quedarían a ≤ 833 m. El modelo «Personas» maximiza solo las personas alcanzadas: con K=7 en CDMX alcanza 28,418 (contra 26,281 del reporte) y con K=8 en EDOMEX 30,033 (contra 17,082). Con 3 clínicas por zona (K=12) alcanza 31,413 e incluye Oriente, donde sus 3 clínicas llegan a 4,911 de 10,413 personas. Repartir 3 por zona cuesta 10,056 personas frente a no restringir las zonas (41,469). Los pesos de robustez y actividad no mejoran el resultado (diferencia de −920 en CDMX, con intervalo de −1,458 a 32), así que se recomienda «Personas».

Para acceso nuevo, un modelo voraz «sin topología» que busca directamente a quienes están lejos obtiene 4,346 personas en CDMX y 12,124 en EDOMEX, contra 319 y 2,248 de la solución del reporte (@fig-acceso). Con la red médica y la red pública el contraste crece: de 2.5 a 6 veces más acceso nuevo que los modelos basados en huecos.

#figure(
  placement: top,
  image(FIG + "modelo_acceso_nuevo.png", width: 92%),
  caption: [Acceso nuevo por modelo: personas sin seguro que pasan de más de 833 m a 833 m o menos de una clínica.],
) <fig-acceso>

= Discusión

La persistencia homológica describe bien la _forma_ de la red y encuentra vacíos relativos dentro de la ciudad, y los grandes resisten perturbaciones de los datos. No basta para decidir dónde dar acceso nuevo: para eso, medir directamente a quién le queda lejos la oferta es más simple y rinde más. La topología puede complementar ese análisis, pero aquí no se demostró que lo mejore. Tampoco es específica de la salud: con el mismo número de puntos, salud es el sector con menos huecos en CDMX, y muchos huecos reflejan la forma de la ciudad.

= Conclusiones

Los vacíos estructurales existen (71 en CDMX y 209 en EDOMEX con el Alpha clásico) y unas 325,500 personas sin seguro viven dentro de los habitados, pero la mayoría está a menos de 833 m de algún establecimiento. Laguerre aumenta el conteo por la escala del peso, no por los hospitales. Las 7 clínicas de CDMX y las 8 de EDOMEX alcanzan personas, pero cierran solo 1 de 46 y 2 de 77 huecos, y en EDOMEX no superan al azar. Un modelo que optimiza directamente personas, o acceso nuevo, rinde más. La marginación cambia 2 de 7 clínicas en CDMX y ninguna en EDOMEX K=8.

Las limitaciones son: tiempos euclidianos × 1.35 y no red vial; población uniforme por AGEB y solo AGEB urbanas; `PSINDER` es falta de afiliación y la red pública incluye IMSS e ISSSTE, que atienden sobre todo a sus afiliados; DENUE no indica capacidad; desfase de 2–3 años entre Censo 2020 y DENUE 2023; IM propio no calibrado contra CONAPO; y prioridades que dependen de contar o no dentistas y asistencia social. Estos modelos no prueban que una clínica en esos puntos mejore la salud de nadie.

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
