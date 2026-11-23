# Plan: de huecos topológicos a acceso real a la salud

Fecha de inicio: 2026-11-12. Rama de partida: `mejoras/tda-avanzado`.

## Por qué cambia el enfoque

Lo que ya sabemos (notebooks 22 a 28, detalle en `reporte/auditoria_y_extensiones.md`):

- Los huecos del alpha complex describen bien la **forma** de la red, pero se calculan solo
  con los puntos de las clínicas. La gente no entra en el cálculo.
- Con la red pública, sus discos captan cerca de la mitad de las personas lejos. La otra
  mitad vive entre establecimientos, en zonas ralas que no forman un hueco.
- Ubicar clínicas buscando directo a quien está lejos rinde de 25% a 30% más que usar los
  centros de los huecos como candidatos.
- El modelo actual (MCLP) tiene tres supuestos débiles: todo o nada a 833 m, sin capacidad
  y distancia en línea recta.

## La pregunta nueva

> ¿Dónde tienen las personas sin seguro un acceso malo a la atención pública de primer
> nivel, tomando en cuenta distancia y saturación, y dónde convendría agregar oferta para
> mejorarlo?

La topología se queda con dos papeles:

1. Describir la forma de la red, con los huecos H1 como hasta ahora.
2. Encontrar las **islas de mal acceso** y medir qué tan profundas y estables son, con
   persistencia sobre la superficie de acceso.

## Principios que no cambian

- **Criterios antes de correr.** Cada notebook fija en su cabecera qué se mide y qué cuenta
  como éxito. Lo agregado después se marca como tal.
- **Siempre contra una línea base simple** (distancia a la más cercana) **y contra el azar.**
- **Una sola definición de población:** la rejilla de 100 m con `PSINDER`, contando cada
  celda una vez.
- **Sensibilidad de cada parámetro arbitrario:** radio, decaimiento y red.
- **Se reporta lo que no funciona.**
- Al terminar cada fase se anota en `BUZON_VIDEOS.md`. Si cambió el estado o se alcanzó un
  hito, se anota también en `BUZON_INDICE.md`.

## Fases

Cada fase tiene una salida concreta y una decisión al final. No se avanza sin esa decisión.

### F0. Cerrar lo actual

- Decidir los commits pendientes: auditoría, modelo revisado y notebook 28.
- Agregar al reporte una sección 11 con la red pública (notebook 28).
- **Decisión:** ninguna técnica; es orden.

### F1. Oferta: CLUES contra DENUE (`notebooks/29_oferta_clues.py`)

- Descargar CLUES (catálogo oficial de unidades de la Secretaría de Salud) y los recursos
  asociados: consultorios y camas.
- Filtrar las unidades de primer nivel en operación que atienden a personas sin seguro:
  SSA, IMSS-Bienestar y servicios estatales.
- Comparar con la red pública de DENUE: cuántas coinciden a menos de 200 m, cuántas faltan
  en cada lado y si las coordenadas son confiables.
- **Decisión:** si CLUES trae coordenadas utilizables para al menos el 90% de las unidades
  de la zona y algún dato de capacidad, se usa CLUES. Si no, se sigue con DENUE, usando
  `per_ocu` como capacidad aproximada.

### F2. Demanda (`lib/acceso.py`)

- Mover a la librería la rejilla de población, que hoy está copiada en los notebooks 26 y 28.
- Demanda principal: `PSINDER`. Sensibilidad: población total, porque la gente con seguro
  también usa la red pública.

### F3. Índice de acceso E2SFCA (`notebooks/30_acceso_e2sfca.py`)

E2SFCA es el método de cuenca flotante en dos pasos, en su versión mejorada.

- **Paso 1:** para cada unidad, su capacidad entre la demanda que la rodea, ponderada por
  distancia.
- **Paso 2:** para cada celda, la suma de esas razones de las unidades cercanas, ponderada
  igual.
- **Parámetros:** cuenca de 15 y 30 min, y decaimiento gaussiano o por escalones. Todos se
  prueban como sensibilidad.
- **Comparación:** contra la distancia simple a la unidad más cercana. ¿Dónde discrepan, y
  por qué: saturación o distancia?
- **Salida:** un mapa de acceso por celda y la tabla de personas por nivel de acceso.

### F4. Islas de mal acceso con persistencia (`notebooks/31_persistencia_acceso.py`)

- Tomar la superficie de acceso como un ráster y aplicar una filtración por subniveles en
  un complejo cúbico (gudhi).
- H0: cada componente que aparece con acceso bajo es una isla. Su persistencia mide qué
  tan profunda es antes de fundirse con una zona mejor.
- **Validación con criterios fijados antes de correr:**
  - estabilidad ante los parámetros de F3;
  - estabilidad ante ruido en la ubicación de las unidades;
  - comparación con un nulo que permuta el acceso entre celdas con correlación espacial.
  - **Estado (2026-11-21):** solo está hecha la estabilidad ante la capacidad de las
    unidades (100 réplicas, ahora por cuenca con Jaccard ≥ 0.5). Faltan las otras tres. Las
    islas que nacen en 0 (335 de 682 por calle, con 2.58 de los 2.75 M de personas de acceso
    bajo en islas estables) son estables ante la capacidad por construcción, así que el nulo
    espacial es la validación que más falta hace.
  - **Nulo espacial (2026-11-22, `notebooks/36_nulo_espacial.py`):** 999 superficies con los
    ceros reales fijos, el gradiente urbano, la rampa junto a los ceros y la autocorrelación
    calibrada (N2), más 200 estacionarias de referencia (N1). Resultado:
    - **Que las islas contengan a la mayoría no es evidencia:** 83% observado contra 87% de
      mediana en N2 (p = 0.90). Es una propiedad del método sobre cualquier superficie suave.
    - **Ninguna isla es más profunda que el azar** (Benjamini–Hochberg 5%; ~5% con p < 0.05,
      lo esperable por azar).
    - **Lo que sí es estructura es la fragmentación:** 933 islas contra 668 (p = 0.002), y todo
      el exceso está en las que nacen con acceso > 0: 405 contra ~72 en N2. Son bolsas de acceso
      bajo entre unidades, que un campo gaussiano no produce. Las que nacen en 0 son incluso
      menos que en el nulo (409 contra 472).
    - **Respuesta a la pregunta clave:** las islas sirven para describir y priorizar, pero su
      persistencia no es una señal más allá de "aquí no hay unidades cerca".
  - **Nulo de la oferta (2026-11-22, `notebooks/37_nulo_oferta.py`):** misma oferta y mismo
    número de unidades por municipio, reubicadas en nodos de 500 m. Contra la regla que sigue
    la demanda (S1, 999 réplicas):
    - **La ubicación actual es compatible** en gente con acceso bajo: 3.42 M contra 3.47 M de
      mediana (percentil 20). Contra la regla ciega (S2) es mucho mejor (3.81 M). Con la oferta
      abierta (sin seguridad social) es mejor que S1: 3.25 M contra 3.49 M.
    - **La actual cubre más territorio:** menos gente sin ninguna unidad alcanzable (595 mil
      contra 798 mil) y menor brecha (p = 0.002). A cambio deja más bolsas: 476 islas que nacen
      con acceso > 0 contra 386.
    - **Solo 146 mil personas (4%) tienen acceso bajo atribuible a la ubicación;** 913 mil lo
      tienen en ≥ 80% de las réplicas. El problema es sobre todo la **cantidad** de oferta por
      municipio, no dónde está: esto respalda que F5 agregue capacidad en lugar de reubicar.
    - La fracción de gente en cuencas de islas es frágil: mover 21 unidades al redondear la
      bajó de 83% a 63%, porque una cuenca de 760 mil personas con persistencia 0.30 dejó de
      contar como isla. Pendiente: estratos de macrozonas en lugar de municipios.
  - **Sensibilidad a F3 (2026-11-22, `notebooks/38_sensibilidad_f3.py`):** cuenca 30 o 15 min
    de calle × decaimiento gaussiano o escalones, con criterios fijados antes de correr.
    - **Con 30 min y escalones las conclusiones se sostienen:** Jaccard del mapa de acceso bajo
      0.88, 94% de la gente baja en islas estables cae en islas recuperadas (las chicas cambian,
      las grandes no) y los 20 sitios de F5 de la base logran 99.9% de la reducción de brecha
      del voraz propio (17 de 20 sitios a ≤ 500 m).
    - **Con 15 min cambia la pregunta:** 3.04 M de personas sin ninguna unidad a 1,125 m de calle
      (contra 0.56 M a 30 min), Jaccard 0.60, solo 13% de la gente en islas recuperadas (las
      cuencas se funden en mesetas de cero) y los sitios de la base logran 68–71% de la
      reducción propia. Ningún veredicto cambia moviendo los cortes ±5 puntos.
    - Conclusión: la forma del decaimiento no importa; el **horizonte** sí. Los resultados de F4
      y F5 son "a 30 min a pie" y así deben reportarse.
  - **Entregables por calle (2026-11-22, `notebooks/39_entregables_calle.py`):** mapas de F3
    por calle (`acceso_calle_mapa.png`, `acceso_calle_causas.png`,
    `acceso_marginacion_calle_mapa.png`) y cuatro tablas en `outputs/entregables/`: islas
    estables, los 20 sitios de F5 con su aporte, resumen por municipio y zonas sospechosas de
    OSM. El municipio de una isla es el de su mínimo; su cuenca puede cruzar municipios.
- **Pregunta clave:** ¿las islas persistentes contienen a la mayoría de las personas con
  peor acceso, y lo hacen mejor que un umbral simple sobre el mapa?

### F5. Optimización con varios objetivos (`notebooks/32_optimizacion.py`)

Se comparan, con los mismos candidatos y el mismo K:

| Objetivo | Qué premia |
|---|---|
| Cobertura máxima (MCLP) | Personas que cruzan el umbral |
| p-mediana | Menor distancia promedio |
| Max-min | Mejorar a los peores |
| Brecha E2SFCA | Menos personas con acceso bajo, con capacidad |

- **Salida:** la frontera entre eficiencia y equidad, ponderada también por marginación,
  y los mapas de los sitios de cada objetivo.
- **Decisión:** qué objetivo o combinación se recomienda y por qué.

### F6. Distancias reales (`notebooks/33_red_real.py`)

- **A pie:** red de calles de OpenStreetMap. Ya existe el flujo de `notebooks/15a_extraer_redes_pbf.py`
  y `lib/geo_network.py`; falta volver a descargar el PBF, porque `Datos/OSM` está vacío.
- **Transporte público:** r5py con el GTFS de CDMX, que incluye Metro, Metrobús, trolebús,
  RTP y tren ligero. EDOMEX casi no tiene GTFS, porque sus combis no están mapeadas, así que
  ahí solo habrá caminata.
- Se recalculan F3 a F5 con tiempos reales y se mide cuánto cambian los resultados.
- **Decisión (2026-11-19): la versión por calle es la principal**, por ser más realista. La
  línea recta con rodeo 1.35 queda como comparación.
  - La regla fijada (≥ 80% de islas que reaparecen; si no, calle principal) se aplicó con
    la distancia entre mínimos (77%). Esa prueba falla con mesetas de acceso 0. El "84% por
    cuenca" que se usó después tampoco sirve: no tenía línea base (una celda cualquiera con
    acceso bajo caía en esas cuencas el 75% de las veces) y medía un solo sentido.
    **Corregido (2026-11-21, tras la revisión de Claude y Codex):** con cuencas emparejadas
    uno a uno (Jaccard ≥ 0.5), 70% de las islas estables en recta tienen pareja por calle,
    pero solo 34% de las de calle la tienen en recta. Las uniones de cuencas se traslapan con
    J = 0.58, frente a J = 0.86 de los dos mapas de umbral {f < 0.5}. **La geografía fina
    de las islas sí depende de cómo se mide la distancia**, más que el mapa de umbral. La
    versión por calle es la principal por realismo, y la diferencia se reporta.
  - Limitación conocida: la red de OSM tiene huecos de cruces peatonales. Por ejemplo, en el
    corredor Gran Canal / Av. Central de Ecatepec no hay cruces mapeados en ~4 km. Las
    celdas "sospechosas" (acceso 0 por calle pero con unidad a ≤ 1,667 m en recta) suman
    174 mil personas. Con el acceso en recta en esas celdas, 86% de las islas estables por
    calle conservan su cuenca (96% de su gente con acceso bajo).
  - Rodeo sin censura (muestra elegida por distancia en recta, Dijkstra sin límite):
    mediana 1.39 (1.37 en CDMX, ~1.40 en EDOMEX), todavía dentro de [1.25, 1.45]. El 1.33
    reportado antes estaba sesgado a la baja por el corte de 2,250 m. 13% de los pares que el
    supuesto 1.35 mete en la cuenca quedan fuera por calle.
  - Archivos principales: `acceso_calle.parquet`, `islas_acceso_calle.parquet`,
    `persistencia_calle.json` (F4) y `optimizacion_calle.json` / `optimizacion_sitios_calle.csv`
    (F5, notebook 32 con `DISTANCIA=calle`). La sección F5 de `red_real.json` es solo una
    comparación con los candidatos de la recta.

### F8. Mejoras (estrategia acordada el 2026-11-22)

F4 y F5 quedaron validadas (notebooks 36 a 39). Antes de escribir se atacan las limitaciones
principales. **Orden:** primero lo que cambia los datos de entrada, al final lo que se
calcula encima. Cada notebook fija sus criterios en la cabecera y pasa por una crítica de
Codex antes de correr.

1. **CLUES (oferta oficial).** Va primero porque cambia la oferta, de la que depende todo.
   - Ver si el catálogo de establecimientos de la DGIS (datos abiertos) trae coordenadas y
     recursos (consultorios, médicos) para las unidades de primer nivel de la zona.
   - Cotejar con DENUE: coincidencias a ≤ 200 m y faltantes de cada lado.
   - **Decisión (la de F1):** si ≥ 90% de las unidades tienen coordenadas utilizables y algún
     dato de capacidad, se cambia a CLUES y se recalculan F3 a F5. Si no, se sigue con DENUE
     y se reporta el cotejo.
   - **Estado (2026-11-22, `notebooks/29_oferta_clues.py`):** catálogo de oct-2026 y Recursos
     2025 en `Datos/CLUES/`. Universo principal: 1,321 unidades (IMSS-Bienestar, SSA y UMR del
     IMSS; sin ISSEMYM, DIF ni municipales). **Pasa la regla de F1:** 98.8% tiene coordenadas y
     consultorios a la vez. El cotejo con DENUE abierta da 675 pares a ≤ 200 m (mediana 19 m;
     87% comparten nombre). Las 631 de CLUES sin pareja son rurales de EDOMEX que DENUE no
     tiene. Las 474 de DENUE sin pareja (36% de su capacidad) son sobre todo DIF, consultorios
     municipales o de alcaldía, ISSSTE mal clasificado y no-clínicas (bomberos, ERUM). En recta
     a 30 min, CLUES deja 1.04 M de personas sin unidad (DENUE abierta, 0.58 M), concentradas en
     la zona conurbada de EDOMEX. **No pasa el criterio 6:** consultorios contra médicos da
     J = 0.76 (< 0.8), porque los médicos capturan turnos (CAAPS: 3 consultorios, 10 médicos).
     **Pendiente antes de recalcular F3 a F5:** decidir la capacidad y si DIF y municipales
     entran como escenario ampliado.
   - **Decisión y recálculo (2026-11-22/23):** Mario eligió **médicos** (generales, familiares
     y pasantes) como capacidad principal; consultorios queda como sensibilidad. DIF y
     consultorios municipales o de alcaldía (CLUES más DENUE sin pareja, con médicos estimados
     por rango de `per_ocu`) entran solo como **escenario ampliado**, calculado en los
     notebooks 29 y 30. `lib/acceso.py` toma la fuente de la variable `OFERTA` (por defecto
     `clues`); los puntos de control llevan sufijo y lo de DENUE quedó en
     `outputs/intermedios/archivo_denue/`.
   - **Error encontrado y corregido tras correr:** 375 unidades rurales de EDOMEX (12% de los
     médicos) no tienen ninguna celda de demanda a ≤ 1,667 m, pero contaban en el promedio
     metropolitano y metían ~0.33 M de personas de más en acceso bajo. Regla nueva: una unidad
     entra a la oferta solo si tiene demanda a ≤ 1,667 m en recta (`en_dominio`). Por calle, la
     media de f ponderada por personas queda en 0.993; con DENUE era 0.999. Ajuste propuesto
     por Codex y no aplicado: normalizar por la capacidad alcanzada en cada escenario.
   - **Resultados con CLUES** (por calle, contra DENUE). Acceso bajo 3.21 M (3.39 M), con
     CDMX en 27.8% (22.8%) y EDOMEX en 52.2% (58.5%). Sin ninguna unidad, 1.13 M (0.56 M).
     Islas estables: 760 (682), con 2.78 M de personas en acceso bajo dentro (2.75 M). En F5,
     cada unidad nueva vale 3 médicos (la mediana), y 20 unidades cierran 166 k de brecha
     (85 k). Sensibilidad de F3: sigue frágil (robusta a 30 min con escalones, frágil a 15 min).
     Nulo espacial: sigue compatible con el azar (p 0.81 en N2 y 0.55 en N1). **Nulo de la
     oferta: cambia de "compatible" a "mejor":** la ubicación real de CLUES deja 0.37 M menos
     de personas en acceso bajo que reubicar las unidades por municipio siguiendo la demanda
     (p = 0.002). Solo 1.8% del acceso bajo es atribuible a la ubicación (4.3% con DENUE).
     **Empeora:** el chequeo de la geografía híbrida (notebook 35) ya no pasa; sobrevive el
     76% de las islas estables por calle (86% con DENUE).
   - **Supuestos documentados:** las réplicas de capacidad sortean entre consultorios y médicos;
     las 32 unidades con consultorio pero sin médicos quedan fuera; las cabeceras de los
     notebooks 31 a 39 citan todavía las cifras de DENUE (valen los JSON de `outputs/auditoria/`).
2. **Cruces peatonales de OSM.** Cambia las distancias.
   - Revisar las zonas sospechosas más grandes (`outputs/entregables/zonas_sospechosas_osm.csv`:
     Álvaro Obregón, Ecatepec, Gran Canal).
   - Agregar los cruces que faltan con una regla explícita (por ejemplo, unir aceras a ≤ 30 m
     separadas por una vía sin cruce mapeado) y medir cuánto cambian los ceros y las islas.
   - **Estado (2026-11-23, `notebooks/40_cruces_osm.py`):** la regla de las aceras no aplica,
     porque la red ya incluye las calles y no solo las banquetas. En su lugar se probaron los
     dos defectos típicos de OSM, en un **escenario permisivo** sin etiquetas de puente ni
     barda, dentro de 2,250 m de las 17,545 celdas sospechosas: 7,540 cruces sin nodo y 12,206
     casi-uniones (sin salida a ≤ 20 m de otra calle, lejos por la red). Codex lo criticó antes
     de correr. Resultado:
     - gana acceso solo el 18% de la gente en celdas sospechosas (225 k → 184 k en cero);
     - el acceso bajo pasa de 3.21 M a 3.19 M;
     - la corrección cierra el 25% de la diferencia con el híbrido del 35;
     - **sobrevive el 89% de las islas estables por calle** (92% de las b = 0), así que los
       defectos de OSM no cambian la geografía de F4.

     La falla del híbrido del 35 se debía a un supuesto demasiado generoso (todo cero
     sospechoso es un error de la red). La mayoría son barreras reales: barrancas en Álvaro
     Obregón y Atizapán, la sierra y el Gran Canal en Ecatepec, autopistas. La red base se
     queda como principal.
3. **¿Cuántas unidades convienen?** Da la cifra central del paper.
   - Curvas de K = 1 a 500 para tres soluciones: **llegar a los peores** (brecha),
     **cubrir más gente** (MCLP) y **mixta** (α·p-mediana o cobertura + (1 − α)·brecha, con α
     elegido en la frontera).
   - Cuarta opción: **ampliar las unidades existentes saturadas**. El 22% de la gente sin
     seguro de EDOMEX tiene acceso bajo con una unidad a ≤ 1,125 m, así que puede salir más
     barato que abrir unidades nuevas.
   - "Cuántas conviene", fijado antes de correr: el K donde la ganancia marginal cae bajo una
     fracción de la inicial (rendimientos decrecientes); el K que reduce la brecha 25% y 50%;
     el K que saca de acceso bajo a la mitad de la gente con prioridad.
   - Se corre con los datos actuales y se repite cuando entren CLUES y los cruces.
   - **Estado (2026-11-23, `notebooks/41_cuantas_unidades.py`):** corrido con CLUES, por calle
     y sobre la red base (F8.2 la dejó como principal). Cada paso suma 3 médicos (la mediana).
     Criterios fijados en la cabecera y criticados por Codex antes de correr.
     - **Unidades nuevas con la brecha:** 25% de la brecha con K = 49 (147 médicos, +3% de
       la oferta) y 50% con K = 130. La mitad de la gente con prioridad sale de acceso bajo
       con K = 186. La ganancia sostenida cae bajo el 10% de la inicial en K = 359; con el
       umbral de 25%, en K = 195. Con K = 500 se cierra el 91% de la brecha.
     - **Mixta (α = 0.5):** cuesta poco en brecha (25% con K = 55) y cubre mucha más gente
       nueva (2.29 M contra 1.56 M en K = 500). El MCLP solo necesita K = 87 para el 25%.
     - **Ampliar las saturadas** (≤ 3 por sede) necesita 696 médicos para el 25% contra 147
       abriendo unidades, y no llega al 50% ni con 500 pasos. Ampliar cualquiera sin tope
       casi no cambia esto. La brecha está sobre todo donde ninguna unidad llega (1.13 M sin
       unidad por calle), así que agregar médicos donde ya hay unidades rinde poco.
     - Con 7 médicos por unidad (P75): 25% con K = 27 y 50% con K = 78.
     - Cota de Minoux de la brecha: 0.56 con K = 20 y 0.86 con K = 500 (holgada con K chico).
     - Límite: el promedio metropolitano queda fijo; con K = 500 la oferta crece 32%.
4. **Transporte público.** Al final, por ser lo más caro.
   - Antes de comprometerse, verificar que r5py funcione (necesita Java 21) y que el GTFS de
     CDMX esté vigente.
   - EDOMEX casi no tiene GTFS (las combis no están mapeadas): ahí sigue siendo solo caminata,
     y eso se reporta como limitación.

Opcionales: estratos de macrozonas en el nulo de la oferta y pendiente del terreno.

### F7. Escritura

Va al final, después de F8. Será un paper nuevo, `reporte/paper_acceso.typ`, firmado por
Mario; el paper del equipo no se toca.

Reporte, paper, presentación y figuras con el enfoque nuevo.

## Cómputo

| Tarea | Recursos | ¿Dónde? |
|---|---|---|
| F1 a F5 en línea recta | Lo de ahora: minutos, < 4 GB | Laptop |
| Red peatonal (OSM) | PBF de México ~700 MB; grafo de la zona de 2 a 4 GB de RAM | Laptop; ya se hizo antes |
| Tiempos a pie celda → unidad | Dijkstra con corte de 30 min desde cada unidad; de minutos a una hora | Laptop |
| Transporte (r5py) | Java 21+ y 8 a 12 GB de RAM para la zona | Laptop justo; Colab de respaldo |

Laptop: 16 GB de RAM, 12 hilos, 156 GB libres y Java 25. r5py pide Java 21; hay que
confirmar que funcione con 25 o instalar la 21 aparte.

## Riesgos conocidos

- **CLUES:** puede no tener coordenadas buenas o capacidad para todas las unidades. Plan B:
  DENUE con `per_ocu`.
- **Demanda:** `PSINDER` mide afiliación, no uso real.
- **Transporte:** sin GTFS en EDOMEX, la comparación entre estados no es pareja.
- **E2SFCA:** depende de parámetros. Por eso cada uno lleva su sensibilidad.
