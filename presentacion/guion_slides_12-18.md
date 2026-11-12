# Guion: diapositivas 12–18 (2:30 min)

**[Slide 12 — Cruce con Censo 2020 · 0:00–0:25]**
«Ya tenemos los huecos geométricos, pero un vacío sin gente no es un problema de política pública. Por eso cruzamos cada hueco con el Censo 2020 a nivel de AGEB. De los 71 huecos de CDMX, 62 están habitados; de los 209 del EDOMEX, 99 — el resto cae en zonas industriales o parques. El resultado es este: **unas 325 mil personas sin seguro médico viven dentro de estos vacíos**, suponiendo población uniforme dentro de cada AGEB. Ojo: casi todas están a menos de 833 metros de algún establecimiento, y eso lo retomamos más adelante.»

**[Slide 13 — Impacto demográfico · 0:25–0:45]**
«Aquí comparamos los 10 huecos más grandes y los 10 más lejanos de un establecimiento. Un hueco grande no siempre está lejos ni tiene gente. Por ejemplo, el hueco más grande de CDMX tiene solo 55 personas. En cambio, en CDMX un cluster concentra 7,525 personas sin seguro; en EDOMEX hay una zona con casi 24 mil, donde una de cada tres personas no tiene derechohabiencia.»

**[Slide 14 — Accesibilidad: tiempos estimados · 0:45–1:10]**
«Tercera dimensión: el tiempo de caminata. Es una estimación, no red vial: distancia en línea recta por 1.35, a 4.5 km/h, con un umbral de 15 minutos, que equivale a 833 metros. En CDMX solo 4 de 62 huecos pasan de 15 minutos; en EDOMEX, 16 de 99. En este scatter, la esquina superior derecha es la crítica: huecos **grandes y además lejanos** de cualquier establecimiento.»

**[Slide 15 — Marginación · 1:10–1:35]**
«Y la cuarta dimensión: una clínica cercana resuelve la barrera geográfica, pero no la de uso. Construimos un índice de marginación que pondera población sin seguro, déficit educativo y adultos mayores. Su efecto es acotado: en CDMX cambia 2 de las 7 clínicas, y en EDOMEX con K=8 no cambia ninguna. Además el índice incluye el porcentaje sin seguro, así que en parte repite otro eje.»

**[Slide 16 — Scoring 4 ejes · 1:35–2:00]**
«Integramos todo en un score con pesos iguales, usando percentiles dentro de cada ciudad para que ningún eje domine. Y para seleccionar usamos un filtro tipo OR: basta ser severo en **uno** de los cuatro ejes para entrar. Quedan **46 huecos prioritarios en CDMX y 77 en EDOMEX**.»

**[Slide 17 — Rankings y Pareto · 2:00–2:15]**
«Al rankearlos se ve un patrón de Pareto: pocos huecos concentran la mayor parte del impacto. Los del nivel crítico, en rojo, son la primera ola de inversión.»

**[Slide 18 — DBSCAN · 2:15–2:30]**
«Último paso antes de optimizar: dos huecos a 800 metros se resuelven con una sola clínica. Con DBSCAN agrupamos huecos a menos de 1.5 km y obtenemos **39 clusters en CDMX y 74 en EDOMEX**. Cada cluster es una decisión de inversión — y eso nos lleva al problema de optimización.»

---

## Notas

- El cierre de la slide 18 deja el pie para la slide 19 (MCLP), que es la transición natural.
- Si vas corto de tiempo, lo recortable sin perder el hilo son los ejemplos numéricos de la slide 13 (7,525 / 24 mil).
- Si presentan entre varios, los cortes limpios para cambiar de orador son después de la 14 (termina «datos») o después de la 16 (termina «scoring»).
