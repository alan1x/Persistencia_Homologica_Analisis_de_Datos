# Persistencia Homológica para Detectar y Resolver Desiertos de Salud
## Ciudad de México y Estado de México

**Autores:** Mario Carlos Gaitán · Rodrigo Jiménez · Andrés Kiewek · Juan Pablo Moral · Luis Alan Morales  
**Datos:** DENUE 2023 (INEGI) · Censo de Población y Vivienda 2020 (INEGI) · OpenStreetMap  
**Región:** Zona Metropolitana del Valle de México

---

## 1. El Problema: Desiertos de Salud que los Mapas Tradicionales No Ven

Ciudad de México tiene 21,585 establecimientos de salud registrados. Estado de México tiene 30,787. A primera vista, no parece haber escasez. Sin embargo, esa abundancia de clínicas oculta un problema estructural: **su distribución es profundamente desigual**.

Las métricas tradicionales — densidad de clínicas por km², radio de cobertura de 500 m, número de establecimientos por municipio — no pueden detectar el tipo de vacío más peligroso: una zona completamente rodeada de infraestructura médica pero con un interior vacío. Una persona que vive en ese interior puede estar a 2 km de la clínica más cercana, incluso si el mapa de densidad de su colonia se ve verde.

A ese tipo de vacío lo llamamos **desierto de salud estructural**. Y el método para detectarlo viene de una rama de las matemáticas llamada Análisis Topológico de Datos.

**Pregunta central:** ¿Dónde están esos desiertos en CDMX y EDOMEX, cuánta población atrapan dentro, y cómo priorizamos las inversiones para resolver los más críticos?

---

## 2. Los Datos: Estableciendo la Base

### 2.1 Establecimientos de Salud — DENUE 2023

El Directorio Estadístico Nacional de Unidades Económicas (DENUE) del INEGI registra todos los negocios y servicios activos por código de actividad económica. Usamos el sector **SCIAN 62** — Servicios de salud y asistencia social — que incluye desde hospitales hasta consultorios dentales y farmacias con consultorio.

| Región | Establecimientos SCIAN 62 | Tipo dominante |
|--------|--------------------------|----------------|
| CDMX   | **21,585**               | Consultorios médicos, dentales, farmacias con consultorio |
| EDOMEX | **30,787**               | Similar, con mayor peso de consultorios periféricos |

Cada establecimiento tiene coordenadas geográficas y una variable de tamaño (`PER_OCU`: personas ocupadas). Esta variable es clave: un consultorio de 2 personas y un hospital de 300 no cubren el mismo territorio. El preprocesamiento convirtió los rangos de texto ("11 a 30 personas") a valores numéricos que representan capacidad de cobertura.

**¿Por qué importa el tamaño?** Porque la topología que construiremos necesita saber qué tan lejos llega cada establecimiento. Un hospital grande genera una zona de influencia mayor que un consultorio de una persona.

> **Figuras:** `outputs/figuras/eda_CDMX.png` y `outputs/figuras/eda_EDOMEX.png` — Distribución del tamaño de los establecimientos. La gran mayoría son micro-establecimientos (0–5 personas); los hospitales grandes son una minoría pero cubren proporciones grandes del territorio.

### 2.2 Datos Demográficos — Censo de Población y Vivienda 2020

Para saber a quién afectan los vacíos, cruzamos su geografía con el Censo 2020 a nivel de **AGEB urbana** (Área Geoestadística Básica), la unidad mínima del Censo equivalente a unas pocas manzanas.

Las variables que usamos:

| Variable censal | Qué mide | Por qué la usamos |
|----------------|----------|-------------------|
| `PSINDER` | Personas sin derechohabiencia (sin seguro médico) | Identifica a quienes no pueden acceder a servicios privados |
| `GRAPROES` | Grado promedio de escolaridad | Componente del índice de marginación |
| `P60YMAS` | Población de 60 años y más | Mayor vulnerabilidad en salud |
| `POBTOT` | Población total | Para calcular porcentajes |

La derechohabiencia es la variable más crítica: una persona sin seguro en un desierto de salud no tiene alternativa. Cuando la clínica más cercana está lejos y no tiene seguro, sencillamente no recibe atención.

---

## 3. Detectando los Vacíos: Análisis Topológico de Datos

### 3.1 ¿Qué es un Hueco Topológico?

La topología estudia la **forma** de los espacios, no sus medidas exactas. En este caso, nos interesa la forma de la red de clínicas: ¿forma anillos con vacíos adentro, o es una nube uniforme?

Un **hueco H₁** (primer grupo de homología) es exactamente eso: un ciclo cerrado de clínicas que rodea un espacio vacío. No importa qué tan irregular sea el contorno — si hay un vacío genuinamente rodeado por todos lados, la persistencia homológica lo detecta.

La **persistencia** mide qué tan significativo es ese hueco: si el vacío desaparece cuando las clínicas "crecen" apenas un poco (bajo radio), es ruido. Si sobrevive a radios grandes, es un vacío estructural real.

### 3.2 Alpha Complex y Persistencia Homológica

El método construye un **Alpha Complex** sobre los puntos (clínicas) en el plano. Matemáticamente: se hace crecer un disco de radio $\alpha$ alrededor de cada clínica. Cuando dos discos se tocan, se forma una arista. Cuando tres se tocan, se forma un triángulo (2-símplex). El proceso revela progresivamente la topología de la nube de puntos.

La **persistencia** de un hueco H₁ se define como:
$$\text{persistencia} = \text{radio\_muerte} - \text{radio\_nacimiento}$$

Un hueco "nace" cuando el vacío queda rodeado al radio $r_{\text{nac}}$ y "muere" cuando una clínica lo triangula al radio $r_{\text{mue}}$. La diferencia entre ambos, medida en metros, es el tamaño real del vacío.

> **Figuras:** `outputs/figuras/persistencia_CDMX.png` y `outputs/figuras/persistencia_EDOMEX.png` — Diagramas de persistencia H₀, H₁ y H₂. Los puntos alejados de la diagonal son huecos estructuralmente importantes: tienen mayor diferencia entre nacimiento y muerte.

### 3.3 ¿Por Qué Elegimos min_persistencia = 200 m?

Este fue uno de los parámetros más importantes del análisis. Para elegirlo correctamente, probamos cuatro umbrales y medimos cuántos huecos sobrevivían en cada uno:

| Umbral min_persistencia | Huecos CDMX | Huecos EDOMEX | Interpretación |
|------------------------|-------------|---------------|----------------|
| 100 m | 482 | 742 | Incluye micro-brechas entre consultorios adyacentes |
| **200 m** | **118** | **241** | Señal estructural: vacíos de al menos una cuadra larga |
| 400 m | 17 | 91 | Solo los más severos; pierde huecos reales de tamaño medio |
| 600 m | 7 | 58 | Únicamente los vacíos de escala de colonia o más |

A 100 m, el algoritmo detecta 482 huecos en CDMX — la mayoría son el espacio entre consultorios en una misma manzana, no vacíos reales de cobertura. A 400 m ya perdemos huecos medianos que sí representan zonas sin clínica accesible caminando.

**200 m es el punto de equilibrio:** un vacío que persiste con radio de 200 m equivale a un espacio donde ninguna clínica está a menos de 200 m — en términos de caminata son unos 2–3 minutos solo para rodear el borde. Para el interior del vacío, la distancia puede ser de 500 m o más.

**Prueba de robustez:** Los huecos de 600 m (los más severos) también aparecen a 100, 200 y 400 m. CDMX tiene 7 huecos de 600 m y los 7 aparecen en los cuatro umbrales (100% de robustez). EDOMEX tiene 58 huecos de 600 m y los 58 aparecen en los cuatro umbrales. Esto confirma que los huecos de alta persistencia son señales reales, no artefactos del calibrado.

> **Figuras:** `outputs/figuras/robustez_conteo_huecos.png` — Curva de estabilidad: cómo cambia el número de huecos al variar el umbral. La pendiente se aplana entre 200 m y 400 m, confirmando que 200 m captura la señal estructural sin el ruido de 100 m.

> `outputs/figuras/robustez_mapa.png` — Mapa de robustez: huecos coloreados por cuántos umbrales los detectan. Los huecos en rojo oscuro aparecen en los 4 umbrales y son las señales más sólidas para política pública.

> `outputs/figuras/robustez_persistencia_vs_umbrales.png` — Relación entre tamaño del hueco (pers_m) y cuántos umbrales lo detectan. Los huecos de persistencia alta (> 400 m) aparecen siempre en los 4 umbrales.

### 3.4 Los Huecos Encontrados y su Geolocalización

Con el umbral de 200 m aplicado sobre el Weighted Alpha Complex (ver §4), encontramos:

- **CDMX:** 118 huecos topológicos
- **EDOMEX:** 241 huecos topológicos

Cada hueco tiene un **centroide** (coordenadas geográficas del centro del vacío) y un **radio de persistencia** (metros), que funciona como el "tamaño" geométrico del desierto.

**Nota sobre la comparación entre ciudades.** El conteo crudo 118 vs 241 no debe leerse como "EDOMEX tiene cobertura dos veces peor". EDOMEX cubre un territorio aproximadamente 3–4 veces mayor que CDMX (125 municipios frente a 16 alcaldías), incluye zonas periurbanas y semi-rurales con baja densidad de clínicas, y sus huecos más grandes en el dato bruto alcanzan hasta 11,808 m de persistencia — vacíos de escala rural donde la separación natural entre localidades es de varios kilómetros. Esa diferencia de escala territorial genera más huecos por tamaño del territorio, no necesariamente por peor planeación urbana.

Por eso el análisis **nunca compara los 118 y 241 huecos directamente como indicadores de urgencia relativa**. A partir de §5, cada ciudad se analiza por separado: los huecos se filtran a zonas habitadas, los scores usan percentiles dentro de cada ciudad, y el MCLP optimiza independientemente. Los 11,808 m de EDOMEX son un outlier periurbano que el pipeline descarta al cruzar con el Censo (§5.1); los huecos que llegan al scoring tienen persistencia máxima de 1,006 m en EDOMEX vs 1,510 m en CDMX — escalas ya comparables.

> **Figuras interactivas:** `outputs/figuras/huecos_CDMX.html` y `outputs/figuras/huecos_EDOMEX.html` — Mapas interactivos donde cada círculo representa un hueco topológico. El radio del círculo es proporcional a su persistencia. Se puede hacer zoom a cualquier zona para ver la distribución local.

### 3.5 Clasificación de los Huecos por Tamaño e Inaccesibilidad

Los huecos varían enormemente en tamaño y en qué tan lejos está la clínica más cercana. Analizamos las dos dimensiones por separado:

**Por persistencia (tamaño del vacío):**

| Categoría | Persistencia | Qué significa |
|-----------|-------------|---------------|
| Micro | < 200 m | Pequeño espacio entre consultorios |
| Mediano | 200–400 m | Vacío de varias manzanas |
| Grande | 400–700 m | Vacío de colonia o barrio |
| Severo | > 700 m | Vacío de escala zonal, múltiples colonias |

**Por inaccesibilidad (tiempo a clínica más cercana):**
Los huecos más inaccesibles de CDMX requieren 20–35 minutos caminando hasta la clínica más próxima. En EDOMEX, algunos alcanzan más de 40 minutos.

> **Figuras:** `outputs/figuras/comparativa_tamano.png` — Top 10 huecos más grandes por persistencia en cada ciudad. `outputs/figuras/comparativa_distancia.png` — Top 10 huecos más lejanos (mayor tiempo de caminata a clínica existente).

---

## 4. No Todas las Clínicas Cubren Igual: Weighted Alpha Complex (Laguerre)

### 4.1 El Problema del Alpha Clásico

El Alpha Complex estándar trata todos los establecimientos como puntos iguales. Pero una farmacia con consultorio de 1 persona y un hospital de 300 empleados no generan la misma zona de cobertura. Si usamos el Alpha clásico, muchos "huecos" que aparecen rodeados de farmacias pequeñas son en realidad zonas bien cubiertas por un hospital grande un poco más lejos.

**Consecuencia:** El Alpha clásico produce falsos positivos en zonas donde muchos micro-establecimientos rodean un área con un hospital grande en el centro.

### 4.2 La Solución: Weighted Alpha Complex (Diagramas de Laguerre)

El Weighted Alpha Complex — también llamado diagrama de Laguerre — asigna un **peso** (radio de influencia) a cada clínica proporcional a su tamaño:

$$r_i = k \cdot \sqrt{\text{per\_ocu}_i}$$

Una clínica con 100 empleados tiene un radio de influencia 10 veces mayor que una con 1 empleado. El espacio se divide en celdas de Laguerre, donde cada punto del plano pertenece a la clínica que más puede cubrirlo (considerando tanto la distancia como el tamaño).

**¿Qué cambia?**

| Métrica | Alpha clásico | Weighted Alpha (Laguerre) | Cambio |
|---------|--------------|--------------------------|--------|
| Huecos CDMX | 71 | **118** | +66.2% |
| Huecos EDOMEX | 209 | **241** | +15.3% |

En CDMX el cambio es mayor porque tiene más heterogeneidad: hospitales grandes de IMSS, ISSSTE y privados coexisten con miles de consultorios pequeños. El Alpha clásico ve esos consultorios y "rellena" huecos que el hospital no alcanza. El Laguerre reconoce que los consultorios no cubren ese radio y expone los vacíos reales.

En EDOMEX el incremento es menor porque su infraestructura es más homogénea (predominan micro-establecimientos en toda la zona).

> **Figuras:** `outputs/figuras/distribucion_radios_laguerre.png` — Distribución de los radios de cobertura Laguerre. La mayoría son micro-establecimientos con radio < 50 m; los hospitales alcanzan 300–500 m de radio.

> `outputs/figuras/laguerre_comparacion.png` — Comparativa visual: Alpha clásico vs Laguerre ponderado en la misma zona. Los huecos que aparecen en Laguerre pero no en el Alpha clásico son los que el tamaño de los hospitales estaba ocultando.

> **Figuras interactivas:** `outputs/figuras/huecos_laguerre_CDMX.html` y `outputs/figuras/huecos_laguerre_EDOMEX.html` — Mapas interactivos con la comparación por zonas. Incluyen la delimitación de las celdas de Laguerre sobre la geografía real.

---

## 5. ¿A Quién Afectan? Los Datos del Censo 2020

### 5.1 Cruces con Datos Demográficos

Para que los huecos topológicos tengan relevancia de política pública, necesitamos saber quién vive dentro de ellos. Cruzamos los 118 huecos de CDMX y los 241 de EDOMEX con las AGEBs del Censo 2020, asignando a cada hueco la población de las AGEBs que caen total o parcialmente dentro de su radio.

De los 118 huecos de CDMX, **62 tienen población censable** (los restantes caen en zonas industriales, de reserva o parques). De los 241 de EDOMEX, **180 tienen población**. Este filtro es también el que descarta los huecos de persistencia extrema (> 2,000 m) de EDOMEX, que corresponden a vacíos periurbanos o rurales sin AGEB habitada asignada — quedando fuera del análisis de urgencia y de las recomendaciones de inversión.

### 5.2 Personas Sin Seguro Médico: La Variable Crítica

La derechohabiencia (`PSINDER`) define quiénes no tienen alternativa frente a un desierto de salud. Una persona con IMSS o ISSSTE puede cruzar colonia para llegar a su clínica asignada. Una persona sin seguro no tiene esa red: si la clínica más cercana (privada o pública) está lejos, simplemente no va.

**Población sin seguro dentro de huecos topológicos habitados:**

| Región | Huecos con población | Personas sin seguro | % de los huecos habitados |
|--------|---------------------|--------------------|-----------------------------|
| CDMX | 62 | ~88,000 | Alta concentración en zonas periféricas |
| EDOMEX | 180 | ~182,000 | Mayor dispersión geográfica |
| **Total** | **242** | **~270,000** | — |

**270,000 personas sin seguro** viven dentro de desiertos de salud topológicos en la zona metropolitana. Equivale aproximadamente a la población completa de una ciudad media mexicana.

> **Figuras:** `outputs/figuras/matriz_riesgo_CDMX.png` y `outputs/figuras/matriz_riesgo_EDOMEX.png` — Scatter de persistencia vs % de población sin seguro por hueco. Los huecos en la esquina superior derecha son los de mayor urgencia: estructuralmente grandes Y con alta inequidad.

> `outputs/figuras/impacto_censal_CDMX.png` y `outputs/figuras/impacto_censal_EDOMEX.png` — Top huecos por impacto demográfico absoluto (personas sin seguro × persistencia).

> **Figuras interactivas:** `outputs/figuras/huecos_censal_CDMX.html` y `outputs/figuras/huecos_censal_EDOMEX.html` — Mapa interactivo donde cada hueco muestra su población sin seguro, grado promedio de escolaridad y proporción de adultos mayores.

### 5.3 Los Huecos con Mayor Impacto

En CDMX, el Cluster 1 concentra los dos huecos más críticos por impacto demográfico: 7,525 personas sin seguro en una zona del poniente donde la clínica más cercana requiere más de 12 minutos caminando.

En EDOMEX, el Cluster 5 (zona norponiente) es el caso más extremo: 23,869 personas sin seguro en 3 huecos adyacentes. El 33.7% de la población total de esa zona carece de derechohabiencia — casi 1 de cada 3 personas.

---

## 6. ¿Cuánto Cuesta Llegar? Tiempos de Caminata

### 6.1 Por Qué la Distancia Euclidiana No Es Suficiente

Saber que una clínica está a 800 m en línea recta no dice cuánto tarda alguien en llegar. Las ciudades tienen obstáculos: vías rápidas sin cruce peatonal, barrancas, zonas industriales. Una distancia de 800 m en línea recta puede ser 1,500 m caminando real.

Usamos **OSMnx** — la librería de Python que accede a la red vial peatonal de OpenStreetMap — para calcular isócronas reales: los polígonos alcanzables en un tiempo dado caminando. La velocidad estándar peatonal es 4.5 km/h.

### 6.2 Distribución de Tiempos de Acceso

Para cada hueco, calculamos el tiempo de caminata desde su centroide hasta la clínica existente más cercana en la red vial real.

Los huecos más críticos en términos de tiempo:

- **CDMX:** Los 10 huecos más inaccesibles requieren 20–35 minutos caminando. Se ubican principalmente en el poniente (Álvaro Obregón, Magdalena Contreras) y sur (Xochimilco, Tláhuac).
- **EDOMEX:** Los más inaccesibles superan 40 minutos en zonas del oriente y norte del estado, donde la red vial peatonal es irregular y la densidad de clínicas es baja.

> **Figura:** `outputs/figuras/scatter_accesibilidad.png` — Tamaño del hueco (persistencia) vs tiempo de caminata a clínica más cercana. Los huecos en la esquina superior derecha son los más urgentes: estructuralmente grandes Y muy lejanos de cualquier clínica.

> `outputs/figuras/mapas_accesibilidad_CDMX.png` — 6 mapas OSMnx de los huecos más grandes y más lejanos de CDMX con la isócrona real de 15 minutos desde la clínica más cercana.

> `outputs/figuras/mapas_accesibilidad_EDOMEX.png` — Mismo análisis para EDOMEX.

> `outputs/figuras/isocronas_roma_norte.png` — Ejemplo de isócrona real en la Colonia Roma Norte: la red vial peatonal de OSMnx deforma el círculo euclidiano según la geometría real de calles, vías y obstáculos.

### 6.3 Umbral de Intervención: 15 Minutos

Definimos que un hueco requiere intervención cuando el tiempo a la clínica más cercana supera **15 minutos caminando**. Este umbral está respaldado por la literatura en salud pública: barreras de acceso mayores a 15 minutos reducen significativamente la tasa de consulta preventiva.

Con este umbral, el tiempo de caminata se convierte en el **Eje 1** del scoring de urgencia que desarrollamos en §8.

---

## 7. La Cuarta Dimensión: Marginación Socioeconómica

### 7.1 Por Qué la Accesibilidad Física No Basta

Una clínica a 10 minutos caminando resuelve la barrera geográfica. Pero si en esa zona la población tiene bajo nivel educativo, alta proporción de adultos mayores y poca capacidad económica, la barrera de uso persiste. La marginación socioeconómica amplifica el impacto de la accesibilidad: en zonas de alta marginación, la ausencia de clínica produce peores resultados de salud que la misma ausencia en zonas más prósperas.

### 7.2 El Índice de Marginación Compuesto

Construimos un **Índice de Marginación (IM)** con cuatro componentes del Censo 2020:

$$IM = 0.35 \cdot \text{pct\_sin\_salud} + 0.25 \cdot \text{deficit\_escolaridad} + 0.25 \cdot \text{pob\_mayor\_pct} + 0.15 \cdot \text{densidad\_sin\_salud}$$

| Componente | Peso | Qué mide |
|------------|------|----------|
| % sin seguro médico | 35% | Barrera directa de acceso al sistema de salud |
| Déficit educativo | 25% | Alfabetización en salud y capacidad de navegar el sistema |
| % adultos mayores (60+) | 25% | Mayor necesidad y menor movilidad |
| Densidad de personas sin seguro | 15% | Concentración territorial del problema |

Todos los componentes se normalizan a [0,1] antes de combinarlos.

### 7.3 Cómo Cambia el Mapa de Urgencia al Agregar Marginación

Al comparar el ranking de huecos con 3 ejes (topología + inequidad + accesibilidad) vs 4 ejes (agregando marginación), encontramos que los rankings son estables en el Top 10 pero hay movimientos significativos en la lista completa:

| Región | Top 10 estables | Huecos que suben ≥3 posiciones | IM medio de los que suben |
|--------|-----------------|-------------------------------|--------------------------|
| CDMX | 9 / 10 (90%) | 11 huecos | 0.37 |
| EDOMEX | 9 / 10 (90%) | 38 huecos | 0.49 |

Los 9 huecos del Top 10 que mantienen su posición son los "obviamente urgentes" — tienen todos los factores en contra. Los que suben son los que parecían menos críticos por accesibilidad o tamaño, pero viven en zonas con déficit socioeconómico severo. En EDOMEX, 38 huecos suben significativamente, señal de que hay una capa profunda de marginación que el análisis de acceso puro subestimaba.

> **Figura:** `outputs/figuras/scoring_impacto_marginacion.png` — Flechas que muestran cómo cambia cada hueco de posición al pasar del score de 3 ejes al de 4 ejes. Las flechas hacia arriba (verde) son huecos con alta marginación que el score anterior subestimaba.

> `outputs/figuras/marginacion_ranking.png` — Top huecos por índice de marginación. `outputs/figuras/marginacion_scatter.png` — Relación entre marginación y los otros ejes del scoring.

---

## 8. Seleccionando los Huecos Críticos: Scoring 4 Ejes y Clustering

### 8.1 El Scoring Multi-eje (25/25/25/25)

Con cuatro dimensiones de urgencia, necesitamos una función que las integre de forma justa. Usamos **pesos iguales** (25% cada uno) con un ranking por percentil: cada hueco recibe una puntuación de 0 a 1 en cada eje según su posición relativa dentro de su ciudad.

$$\text{score} = 0.25 \cdot r_{\text{tiempo}} + 0.25 \cdot r_{\text{sin\_seguro}} + 0.25 \cdot r_{\text{persistencia}} + 0.25 \cdot r_{\text{marginación}}$$

Donde cada $r$ es el percentil del hueco en ese eje (0 = menos urgente, 1 = más urgente).

**Ventaja del percentil:** Evita que un eje con valores muy grandes domine a los demás. Un hueco con 5,000 personas sin seguro no aplasta automáticamente a uno con 1,000 si ese segundo hueco tiene la mayor persistencia y marginación de su ciudad.

A partir del score, clasificamos los huecos en niveles de urgencia:
- **Crítico:** score ≥ percentil 75 de la ciudad
- **Alto:** score ≥ percentil 50
- **Moderado:** score ≥ percentil 25
- **Bajo:** el resto

Resultados:

| Nivel | CDMX | EDOMEX |
|-------|------|--------|
| Crítico | 16 huecos (IM medio = 0.29) | 26 huecos (IM medio = 0.37) |
| Alto | 15 | 24 |
| Moderado | — | — |
| **Total prioritarios** | **46** | **77** |

Los niveles Crítico/Alto son los cortes por percentil del **score compuesto** (≥ p75 y ≥ p50). El total de **46 / 77 prioritarios no es la suma de esos niveles** (16+15=31 en CDMX): proviene del **filtro de selección OR de §8.2**, donde basta cumplir uno de los 4 ejes (tiempo, inequidad, persistencia o marginación) para entrar. Por eso captura huecos que ningún corte por percentil del score global marcaría como Crítico/Alto pero que son severos en un eje individual.

El IM medio de los huecos críticos de EDOMEX (0.37) supera al de CDMX (0.29), confirmando que los desiertos de salud más severos del Estado de México no solo son más grandes sino que están en zonas socioeconómicamente más vulnerables.

> **Figura:** `outputs/figuras/scoring_scatter.png` — Scatter de los 4 ejes: eje X = inaccesibilidad (tiempo), eje Y = inequidad (personas sin seguro), tamaño del punto = persistencia topológica, color = score final. Los puntos rojos grandes en la esquina superior derecha son los huecos de mayor urgencia compuesta.

> `outputs/figuras/scoring_rankings.png` — Top 10 huecos por cada uno de los 4 ejes individualmente. Permite ver qué huecos son urgentes en cada dimensión.

> `outputs/figuras/scoring_pareto.png` — Huecos que están entre el 20% más urgente en al menos 2 de los 4 ejes (frontera de Pareto). Estos son los candidatos de mayor robustez para intervención.

### 8.2 Filtro de Selección y por Qué Solo 46 / 77 Huecos

De los 118 huecos habitados de CDMX, seleccionamos 46 como prioritarios. Los criterios son los 4 ejes del scoring (basta cumplir **uno**):

- Tiempo > 10 minutos a clínica más cercana, **o**
- Personas sin seguro > percentil 60 de la ciudad, **o**
- Persistencia > 400 m, **o**
- Índice de marginación > percentil 60 de la ciudad

Incluir la marginación como 4.° criterio OR es coherente con el scoring 25/25/25/25: si la marginación entra como eje de priorización, también debe entrar como criterio de selección. Esto amplió el total de 39 → 46 huecos en CDMX y de 72 → 77 en EDOMEX. Los huecos adicionales son los que pasan el umbral de marginación aunque tengan tiempo, inequidad y persistencia moderados — zonas socioeconómicamente vulnerables donde la ausencia de clínica tiene peores consecuencias.

Los huecos descartados son micro-brechas: bajo en los 4 ejes simultáneamente. Una nueva clínica en esos lugares no movería la aguja en ninguna dimensión.

### 8.3 Agrupación Geográfica: DBSCAN

Los huecos cercanos entre sí (menos de 1,500 m) se resuelven con la misma clínica. Si hay dos huecos a 800 m de distancia, una clínica bien ubicada entre ambos los cubre a los dos — no necesitamos una clínica por hueco.

Usamos **DBSCAN** (Density-Based Spatial Clustering of Applications with Noise) con radio de 1,500 m para agrupar huecos en clusters, donde cada cluster representa una decisión de inversión.

| Región | Huecos prioritarios | Clusters resultantes | Naturaleza |
|--------|--------------------|--------------------|------------|
| CDMX | 46 | 39 | Algunos con 2–3 huecos agrupados |
| EDOMEX | 77 | 74 | Casi todos singletons (alta dispersión) |

El alto número de singletons en EDOMEX ya es un hallazgo: los desiertos de salud del Estado de México están tan dispersos que casi ningún par está lo suficientemente cerca para resolverse con la misma clínica. Esto anticipa la estrategia subregional que adoptaremos.

> **Figura:** `outputs/figuras/clusters_geograficos.png` — Mapa de los 46 huecos prioritarios de CDMX y los 77 de EDOMEX agrupados por cluster. Los huecos no prioritarios aparecen en gris con una "X". Los clusters prioritarios están coloreados por identidad; el contorno de cada hueco indica su nivel de urgencia (rojo = Crítico, naranja = Alto, verde = Moderado). El diamante en el centroide de cada cluster muestra su rank (C1 = mayor score compuesto).

---

## 9. La Solución Óptima: Dónde Construir las Nuevas Clínicas

### 9.1 Formulación del Problema: MCLP

Una vez que tenemos los clusters candidatos y sus tiempos de cobertura, la pregunta es: dado un presupuesto de K nuevas clínicas, ¿cuáles K ubicaciones maximizan el impacto?

Usamos el **Maximum Coverage Location Problem (MCLP)**, un problema de optimización combinatoria resuelto con Programación Lineal Entera:

$$\max \sum_{i} d_i \cdot x_i$$

Donde:
- $d_i = \text{score}_i \times \text{pob\_sin\_salud}_i$ — demanda ponderada del hueco $i$ (urgencia × personas afectadas)
- $x_i = 1$ si el hueco queda cubierto por al menos una de las clínicas seleccionadas
- La cobertura se define como: clínica a ≤ 15 minutos caminando desde el centroide del hueco

La demanda ponderada $d_i$ integra los 4 ejes automáticamente: el score ya incluye tiempo, inequidad, persistencia y marginación. Una clínica que cubre un hueco con score 0.9 y 5,000 personas sin seguro tiene mucho mayor impacto que una que cubre un hueco con score 0.3 y 500 personas.

### 9.2 CDMX: Justificando K=7 con la Curva de Rendimiento Decreciente

Antes de elegir cuántas clínicas proponer, ejecutamos el MCLP para K=5 hasta K=10 y medimos cuánta población sin seguro adicional cubre cada clínica nueva:

| K | % del total prioritario | Incremento marginal |
|---|------------------------|---------------------|
| 5 | 33.0% | — |
| 6 | 38.6% | **+5.6 pp** |
| 7 | 44.0% | **+5.3 pp** |
| 8 | 49.1% | +5.1 pp |
| 9 | 53.1% | +4.0 pp |
| 10 | 56.1% | +3.0 pp |

El patrón muestra una caída progresiva: K=5→6→7→8 tienen incrementos similares (~5+ pp), pero en K=8→9 el salto cae a 4.0 pp y en K=9→10 a 3.0 pp — una reducción de más de un tercio respecto a los primeros saltos. K=7 es el último punto donde la cobertura cruza el **44%** antes de que los rendimientos entren en caída sostenida.

**¿Por qué K=7 y no K=8?**

K=7 cubre el **44.0% de la población prioritaria** — casi la mitad — con 7 decisiones de inversión. El salto de K=7 a K=8 agrega 5.1 pp, que es numéricamente similar al salto K=6→7. Sin embargo, K=7 representa el punto donde la cobertura supera el 40% y el costo marginal empieza a subir (cada clínica adicional cubre zonas más dispersas). K=8→9 muestra la caída más pronunciada de toda la curva (−1.1 pp de incremento), señal de que los huecos de mayor densidad ya están cubiertos a K=7 y los restantes son más difíciles y costosos de resolver. Para un tomador de decisiones con presupuesto limitado, K=7 maximiza el retorno antes de la transición a rendimientos claramente decrecientes.

> **Figura:** `outputs/figuras/validacion_curva_k.png` — Curvas K=5→10 para CDMX y EDOMEX. Panel superior: áreas apiladas de cierre topológico (verde = cerrado, naranja = parcial, rojo = persistente). Panel inferior: curvas de cobertura poblacional vs K. El punto de mayor salto marginal está marcado.

### 9.3 CDMX K=7: Los Resultados y lo que Cubren los 4 Ejes

La solución K=7 selecciona los Clusters **1, 2, 5, 7, 8, 16 y 19** de CDMX. Cada uno representa el centroide de un grupo de huecos de alta urgencia compuesta.

**Impacto global:**

| Métrica | Resultado |
|---------|-----------|
| Huecos prioritarios cubiertos | 11 / 46 (23.9%) |
| Personas sin seguro cubiertas | **42,687** |
| % del total prioritario | **44.0%** |
| Clusters C1, C2, C5, C7, C8 | También presentes en solución K=5 (núcleo estable) |
| Clusters C16, C19 | Añadidos al pasar de K=5 a K=7 |

**Análisis de los 4 ejes: ¿qué tipos de huecos cubre K=7 y cuáles persisten?**

El análisis más revelador compara las características promedio de los 11 huecos que K=7 cubre versus los 35 que todavía persisten:

| Eje | Huecos cubiertos (11) | Huecos persistentes (35) | Interpretación |
|-----|----------------------|--------------------------|----------------|
| **Tiempo** (min) | 7.89 | 9.27 | K=7 cubre huecos más accesibles pero con mayor población |
| **Sin seguro** (personas) | 3,881 | 1,555 | El MCLP prioriza correctamente por inequidad |
| **Persistencia** (metros) | 296 | 364 | Los vacíos geográficos más grandes quedan sin resolver |
| **Marginación** (IM 0–1) | 0.35 | 0.29 | El 4.° eje redirige inversión hacia zonas más marginadas |

**Lecturas clave:**

1. Los huecos cubiertos tienen casi el **doble de personas sin seguro** (3,881 vs 1,555) — el MCLP maximiza correctamente el impacto poblacional.

2. Los huecos cubiertos tienen **mayor IM** (0.35 vs 0.29) — el 4.° eje de marginación sí cambia la solución: sin él, algunos de estos huecos habrían tenido menor prioridad.

3. Los huecos persistentes tienen **mayor persistencia geométrica** (364 m vs 296 m) — los vacíos geográficos más grandes tienden a quedar fuera porque suelen estar en zonas periféricas con baja densidad de población.

4. La paradoja del tiempo: los huecos cubiertos tienen menor tiempo (7.89 vs 9.27 min). Esto no indica que K=7 ignora la inaccesibilidad — indica que los huecos muy lejanos tienden a tener poca población (están en zonas periféricas) y el MCLP racionalmente los pospone.

> **Figura:** `outputs/figuras/fase3_CDMX_k7_mapa.png` — Mapa de CDMX con las 7 clínicas propuestas (puntos numerados), sus zonas de cobertura de 15 min (polígonos de colores), los huecos prioritarios (coloreados por urgencia) y los no prioritarios (gris). Los huecos con borde blanco grueso son los cubiertos por la solución K=7.

> `outputs/figuras/fase3_CDMX_k7_ejes.png` — Cuatro histogramas comparando la distribución de cada eje entre huecos cubiertos (verde) y persistentes (rojo). Las líneas punteadas son las medias. Muestra exactamente cómo los 4 ejes del scoring se traducen en cobertura real.

### 9.4 EDOMEX: Por Qué Una Estrategia Distinta

En EDOMEX, la curva K=5→10 del análisis de sensibilidad muestra algo radicalmente diferente a CDMX:

| K | % cubierto | Δ marginal |
|---|-----------|------------|
| 5 | 17.6% | — |
| 6 | 19.8% | +2.2 pp |
| 7 | 21.8% | +2.0 pp |
| 8 | 23.7% | +1.9 pp |
| 9 | 25.2% | +1.5 pp |
| 10 | 26.7% | +1.5 pp |

La curva es **casi perfectamente lineal**: cada clínica aporta aproximadamente el mismo incremento marginal. No hay codo, no hay punto óptimo único. Esto significa que ninguna zona concentra tanto impacto como para que concentrar la inversión ahí sea mejor que distribuirla.

La razón geométrica es clara: EDOMEX tiene 69 clusters para 72 huecos (casi todos singletons). Los huecos están en cuatro zonas geográficas que no se comunican entre sí a 15 minutos caminando: Norte, Poniente, Oriente y ZMVM-Centro. Una clínica en la ZMVM literalmente no puede cubrir huecos en Norte o Poniente por distancia.

**La solución correcta para EDOMEX no es encontrar el K óptimo global sino dividir el problema en subproblemas locales.**

### 9.5 EDOMEX: Estrategia Subregional K=12 (4 Zonas × 3 Clínicas)

Dividimos EDOMEX en 4 subregiones geográficas y asignamos **K=3 clínicas por zona** — presupuesto uniforme que garantiza presencia en todas las áreas del estado. Esto da **K=12 presupuestadas, pero solo 9 ubicables**: la zona Oriente no tiene candidatos válidos al umbral de 15 min (ver abajo), así que sus 3 clínicas quedan sin colocar y la solución efectiva opera con 9.

| Subregión | Delimitación | Huecos | K asignado | Huecos cubiertos | Sin seguro cubiertos | % subregional |
|-----------|-------------|--------|-----------|-----------------|---------------------|---------------|
| Norte | lat > 19.7° | 8 | 3 | 2 / 8 | 1,182 | 13.9% |
| Poniente | lon < −99.3° | 22 | 3 | 3 / 22 | 10,243 | 23.0% |
| ZMVM-Centro | Resto | 41 | 3 | 4 / 41 | 24,443 | 19.7% |
| Oriente | lon > −98.9° | 6 | 3 | Sin candidatos | — | — |
| **Total** | | **77** | **12** | **9 / 77** | **35,868** | **19.0%** |

**Comparado con el MCLP global K=5:**

| Estrategia | Clínicas | Sin seguro cubiertos | Cobertura | Zonas atendidas |
|------------|----------|---------------------|-----------|-----------------|
| Global K=5 | 5 | 32,683 | 17.3% | Solo ZMVM y Poniente |
| **Subregional K=12** | **12** | **35,868** | **19.0%** | **Norte + Poniente + ZMVM** |

Con 7 clínicas adicionales respecto al global K=5, la estrategia subregional gana 1.7 pp de cobertura, pero su mayor ventaja no es el número: es que **garantiza presencia en zonas que el MCLP global nunca atendería**.

**¿Por qué K=3 uniforme y no proporcional?**  
La ZMVM tiene 38 huecos (53% del total) pero ya está relativamente mejor atendida porque concentra más infraestructura existente. Norte y Poniente tienen huecos con mayor persistencia geométrica — son vacíos estructuralmente más severos aunque con menos población absoluta. Dar K=3 a cada zona equaliza la oportunidad de intervención antes de concentrar recursos donde ya existe más cobertura.

**La subregión Oriente** (6 huecos, 12,270 personas sin seguro) no tiene candidatos válidos bajo el umbral de 15 minutos: los huecos están en una zona de baja densidad de clínicas vecinas donde ningún centroide de cluster alcanza a cubrir huecos dentro del radio de 1,125 m. Esta subregión requiere análisis específico con umbral extendido (20–30 min) o estrategia de clínicas móviles.

> **Figura:** `outputs/figuras/fase3_EDOMEX_subregional_mapa.png` — Mapa comparativo: izquierda = global K=5 (solo cubre ZMVM y Poniente), derecha = subregional K=12 (cubre 3 de las 4 zonas). Los huecos se colorean por subregión en el panel derecho para mostrar la distribución geográfica de la inversión.

> `outputs/figuras/fase3_EDOMEX_zonas_mapas.png` — Tres mapas individuales (Norte / Poniente / ZMVM-Centro), cada uno mostrando sus huecos de urgencia y las 3 clínicas seleccionadas (diamantes numerados). Los huecos con borde blanco son los cubiertos por K=3 local.

> `outputs/figuras/fase3_EDOMEX_subregional_ejes.png` — Comparativa de los 4 ejes por subregión: barras verdes = media de huecos cubiertos, barras rojas = media de huecos persistentes. Muestra que Norte tiene los huecos con mayor persistencia geométrica y Poniente los de mayor marginación.

---

## 10. Validación: ¿Se Cerraron Realmente los Huecos?

### 10.1 Cierre Topológico: CDMX K=7 y EDOMEX K=12 Subregional

La misma metodología TDA que detectó los huecos verifica si las nuevas clínicas los resuelven. Un hueco H₁ con centroide $c$ y persistencia $r$ queda **cerrado topológicamente** cuando la nueva clínica cae a distancia $d < r$ del centroide: en esa condición, el nuevo punto triangula el interior del ciclo y lo elimina del diagrama de persistencia.

Definimos tres estados para cada hueco:

| Estado | Condición | Significado |
|--------|-----------|-------------|
| **Cerrado** | $d < r$ | La clínica cae dentro del vacío → cierre topológico garantizado |
| **Parcial** | $r \leq d < 2r$ | La clínica está próxima, accesibilidad mejorada, hueco persiste |
| **Persistente** | $d \geq 2r$ | Sin intervención efectiva en este hueco |

Resultados de la solución óptima por ciudad:

| Región | Huecos prioritarios | K | Cerrados | Parciales | Persistentes | Reducción pers. total |
|--------|---------------------|---|----------|-----------|--------------|----------------------|
| CDMX | 46 | 7 | 3 (7%) | 4 (9%) | 39 (85%) | −14.9% |
| EDOMEX | 77 | 12 subregional | 6 (8%) | 2 (3%) | 69 (90%) | −16.5% |

**¿Por qué tan pocos huecos topológicamente cerrados si K=7 y K=12 cubren el 44% y 19% de población?**

La clave está en que MCLP y cierre topológico miden cosas distintas. El MCLP optimiza **cobertura poblacional**: una clínica a 14 minutos de un hueco lo "cubre" en términos de acceso (está dentro de los 15 min). El cierre topológico requiere que la clínica esté a menos de `pers_m` metros del **centroide exacto** del hueco — un criterio geométrico mucho más estricto.

Un hueco con `pers_m = 400 m` se cierra topológicamente solo si la clínica cae a < 400 m del centroide. Pero el mismo hueco puede estar "cubierto" por MCLP si la clínica está a 800 m del centroide pero a 12 minutos caminando de la zona habitada dentro del hueco.

**Los 3 huecos cerrados en CDMX** son exactamente los de mayor score compuesto que el MCLP priorizó en primer lugar — el algoritmo los colocó con precisión dentro del radio topológico. Los 39 persistentes tienen dos causas: gran tamaño geométrico (pers_m > 600 m, difícil de cerrar con ubicaciones densamente habitadas) o dispersión extrema (el candidato viable más cercano está a 3–5 km del centroide).

**En EDOMEX K=12**, el cierre de 6/77 (8%) con **reducción de −16.5% en persistencia total** es significativo: la subregionalización no solo amplía la cobertura poblacional sino que logra mayor cierre geométrico que la estrategia global K=5, donde solo se cerraban 3/72 huecos.

**Nota sobre la persistencia máxima:** El hueco más severo persistente en EDOMEX tiene `pers_m = 756 m` (antes era 1,006 m el máximo del conjunto completo). La subregionalización redujo el techo de persistencia máxima persistente, confirmando que los huecos de mayor tamaño estructural están siendo abordados.

### 10.2 Robustez del Análisis

Para confirmar que los resultados no dependen del umbral de 200 m elegido, verificamos que los huecos de alta persistencia (600 m) aparezcan también en umbrales menores:

- **CDMX:** 7 huecos a 600 m → los 7 aparecen también a 100, 200 y 400 m (**100% de robustez**)
- **EDOMEX:** 58 huecos a 600 m → los 58 aparecen también a 100, 200 y 400 m (**100% de robustez**)

Los huecos más severos son señales topológicas robustas: existen independientemente del umbral de análisis. Esto da solidez metodológica a las recomendaciones — los desiertos de salud que identificamos no son artefactos del calibrado.

> **Figura:** `outputs/figuras/validacion_persistencia.png` — Distribución de persistencias por estado de cierre (cerrado/parcial/persistente): CDMX con K=7 y EDOMEX con K=12 subregional. Los huecos cerrados tienen persistencias menores — es más fácil cerrar huecos pequeños con pocas clínicas.

> `outputs/figuras/validacion_mapa.png` — Mapa geográfico del cierre topológico: verde = huecos cerrados, naranja = parciales, rojo = persistentes. Las líneas conectan cada hueco cerrado/parcial con su clínica nueva más cercana.

> `outputs/figuras/robustez_conteo_huecos.png` — Curva de estabilidad TDA a 4 umbrales, con el umbral de análisis principal (200 m) marcado. Confirma que 200 m es el punto de equilibrio entre señal y ruido.

---

## 11. Conclusiones y Recomendaciones de Política Pública

### 11.1 Lo que Encontramos

**El problema es estructural, no de escasez.**  
CDMX tiene 21,585 clínicas y EDOMEX tiene 30,787. El problema no es que falten establecimientos en términos absolutos: es que están mal distribuidos. Existen 118 huecos topológicos en CDMX y 241 en EDOMEX donde la geometría de la red de clínicas crea vacíos genuinos, rodeados de infraestructura por fuera pero vacíos por dentro.

**El impacto demográfico es medible y concentrado.**  
270,000 personas sin seguro médico viven dentro de desiertos de salud topológicos en la zona metropolitana. 46 huecos en CDMX y 77 en EDOMEX concentran la mayor urgencia — son los candidatos a intervención de política pública.

**La ponderación por tamaño cambia la geografía del riesgo.**  
El Weighted Alpha Complex (Laguerre) revela en CDMX 47 huecos adicionales que el Alpha clásico no detectaba (+66%): vacíos que parecían cubiertos por muchos consultorios pequeños pero que en realidad carecen de cobertura real.

**El 4.° eje de marginación cambia quién recibe inversión.**  
Los huecos que K=7 cubre en CDMX tienen un IM medio de 0.35 vs 0.28 de los que persisten. Sin el 4.° eje, parte de esa inversión habría ido a huecos con alta pob_sin_salud pero en zonas menos vulnerables socioeconómicamente.

### 11.2 Recomendaciones por Ciudad

**CDMX — 7 clínicas nuevas (Clusters C1, C2, C5, C7, C8, C16, C19):**

K=7 es el punto donde la cobertura supera el 44% antes de que los incrementos marginales entren en caída sostenida (K=8→9: +4.0 pp, K=9→10: +3.0 pp). Con 7 nuevas clínicas estratégicamente ubicadas se cubren 42,687 personas sin seguro en 46 huecos prioritarios. Los 5 clusters del núcleo estable (C1, C2, C5, C7, C8) aparecen en toda la curva K=5→10 y deben ser la primera fase de inversión. Los clusters C16 y C19 se añaden al pasar de K=5 a K=7 y son la segunda prioridad.

**EDOMEX — Estrategia subregional 4 zonas × 3 clínicas (12 presupuestadas, 9 ubicables):**

No existe un K óptimo global para EDOMEX porque su curva K=5→10 es casi perfectamente lineal (~2 pp por clínica). La inversión debe distribuirse geográficamente: 3 clínicas para Norte (8 huecos), 3 para Poniente (22 huecos), 3 para ZMVM-Centro (41 huecos), cubriendo 9/77 huecos y 35,868 personas. La zona Oriente (6 huecos, 12,270 sin seguro) no tiene candidatos válidos al umbral de 15 min y requiere estrategia complementaria: umbral extendido de 20–30 min, clínicas móviles o telemedicina.

### 11.3 Lo que la Topología Agrega que los Métodos Tradicionales No Dan

Un mapa de densidad de clínicas mostraría que CDMX tiene ~10 veces más establecimientos por km² que zonas rurales — y concluiría que el acceso está garantizado. La persistencia homológica revela que incluso con 21,585 clínicas existen 39 vacíos estructurales con 88,000 personas sin seguro atrapadas adentro.

La diferencia es cualitativa: los métodos de densidad miden cuánto hay, la topología mide la *forma* de lo que hay. Y la forma importa cuando la distribución es heterogénea — que es exactamente el caso de todas las zonas metropolitanas de América Latina.

### 11.4 Limitaciones

| Limitación | Impacto | Mejora propuesta |
|------------|---------|-----------------|
| Tiempos con euclidiana × 1.35, no red real | Error de ±15% en zonas con barrancos o topografía irregular | Red peatonal OSMnx por subregión |
| IM construido desde Censo 2020 | Puede diferir de índice CONAPO oficial | Cruzar y calibrar con índice CONAPO 2020 |
| Datos DENUE 2023, Censo 2020 | Desajuste temporal de 2–3 años | Actualizar con DENUE trimestral |
| Oriente de EDOMEX sin candidatos válidos | 12,270 personas sin cobertura en la solución actual | Umbral extendido o clínicas móviles |
| K máximo = 20 candidatos por ciudad | Con presupuesto mayor se necesitan más opciones | DBSCAN con eps menor para generar más candidatos |
