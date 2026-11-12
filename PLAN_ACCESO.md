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

### F7. Escritura

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
