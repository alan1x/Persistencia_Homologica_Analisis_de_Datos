# Buzón para la serie de videos

## 2026-11-02

**Qué se quería:** Mario eligió medir el cierre real (B), probar la robustez de verdad (C),
auditar las cifras (D) y extender a otros sectores (E). Descartó la animación de la
filtración (A).

**Qué se aprendió:**

- Una clínica nueva no cierra un hueco grande: lo parte. El radio del vacío es la muerte
  del hueco, no su persistencia.
- Las 7 clínicas de CDMX cierran 1 de 46 huecos prioritarios y las 8 de EDOMEX, 2 de 77. La
  persistencia baja 2.3% y 7.4%, no 14.9% y 16.5%.
- En persistencia, el MCLP no supera a una selección al azar. En personas alcanzadas sí la
  supera en CDMX (42,687 contra 22,403); en EDOMEX queda dentro de su rango.
- El +66% de Laguerre es sobre todo un efecto de escala: con pesos iguales salen 116 huecos
  contra 118. Los hospitales cambian cuáles huecos aparecen, no cuántos.
- Una prueba de robustez que solo cambia un filtro no puede fallar. Perturbando los datos,
  los huecos ≥ 400 m resisten (93% con σ = 100 m) y los menores no (cerca de 50%).
- Con el mismo número de puntos, salud no tiene más huecos que otros sectores. Muchos huecos
  son de la forma de la ciudad.

**Qué se agregó:** `lib/huecos.py`, `lib/viz_eval.py`, `notebooks/22_auditoria_cifras.py`,
`22b_laguerre_artefacto.py`, `23_cierre_real.py`, `24_robustez_real.py`,
`25_otros_sectores.py` y `reporte/auditoria_y_extensiones.md`.

**Dónde está la evidencia:**

- Documento: `reporte/auditoria_y_extensiones.md`
- Datos: `outputs/auditoria/`
- Figuras, en `outputs/figuras/`:
  - `auditoria_laguerre_artefacto.png`
  - `cierre_real_antes_despues.png`, `cierre_real_lineas_base.png`, `cierre_real_personas.png`
  - `robustez_real_supervivencia.png`, `robustez_real_nulo.png`
  - `sectores_huecos_mismo_n.png`, `sectores_actividad_en_huecos.png`

**Qué quedó suelto:** el MCLP sobre red vial real (las redes ya no están en disco), el
pipeline completo con Laguerre y si `Topología Grupos` se relaciona con este proyecto.

## 2026-11-03

**Qué se quería:** corregir lo escrito, medir el éxito por personas y mejorar el modelo, sin la red vial todavía.

**Qué se aprendió:**

- Contando a cada persona una vez, las 42,687 y 35,868 personas del reporte son 26,281 y 17,082.
- Un hueco no es lo mismo que estar lejos: solo 0.9% de las personas en discos prioritarios de CDMX y 5.0% en EDOMEX están a más de 833 m de un establecimiento.
- Si la meta es acceso nuevo, buscar directamente a quienes están lejos rinde mucho más que partir de los huecos.
- Oriente sí tenía solución: quedó fuera por el corte de 20 candidatos.
- Dar más peso a los huecos robustos y con actividad económica no mejoró el resultado. Se reporta aunque no sea lo que se esperaba.
- Dentistas y asistencia social pesan mucho: cerca de la mitad de los 52,372 establecimientos, y cambian qué huecos se ven.
- Fijar los criterios antes de correr sirve, y volver a revisar sirve también: al leer más código aparecieron errores míos y del reporte.

**Qué se agregó:** `notebooks/26_modelo_revisado.py`, `notebooks/27_verificaciones.py` y las secciones 8 a 10 de `reporte/auditoria_y_extensiones.md`.

**Dónde está la evidencia:** `outputs/auditoria/modelo_revisado.*`, `outputs/auditoria/verificaciones.json` y, en `outputs/figuras/`, `modelo_personas_vs_azar.png`, `modelo_acceso_nuevo.png` y `modelo_ubicaciones.png`.

**Qué quedó suelto:** MCLP sobre red vial real, repetir el pipeline con la red médica o pública, y Laguerre en todo el pipeline.

## 2026-11-12

**Qué se quería:** repetir el análisis solo con la red pública, usar la topología para describir la red y medir la cobertura de forma directa.

**Qué se aprendió:**

- Con la red pública, el 20% de las personas sin seguro en CDMX y el 35% en EDOMEX está a más de 833 m. A más de 30 minutos queda el 1.2% y el 5.6%.
- La red pública tiene más huecos de los que daría una red igual de rala tomada al azar, aunque en CDMX lo supera por poco y desaparece en la variante abierta.
- Sus huecos captan cerca de la mitad de las personas lejos (53% y 52%). El enriquecimiento llega a 1.67 en CDMX y a 1.43 en EDOMEX, solo apenas sobre el umbral en CDMX. La otra mitad vive entre establecimientos, fuera de cualquier disco.
- Con los centros de los huecos como candidatos se logra el 77% y el 79% de lo que logra el modelo directo con K=10, por debajo del 90% fijado.
- El voraz directo coincide con el MCLP exacto y supera por mucho al azar: con 10 clínicas, 91k personas en CDMX y 118k en EDOMEX, contra un p95 de 22k y 19k.

**Qué se agregó:** `notebooks/28_red_publica.py`.

**Dónde está la evidencia:** `outputs/auditoria/red_publica.json`, `outputs/figuras/red_publica_mapa.png` y `outputs/figuras/red_publica_curva_K.png`.

## 2026-11-12 (F3: índice de acceso)

**Qué se quería:** medir el acceso a la atención pública de primer nivel tomando en cuenta distancia y saturación (E2SFCA), y no solo la distancia a la unidad más cercana.

**Qué se aprendió:**

- Promedio metropolitano: 6.4 personas de personal público de primer nivel por cada 1,000 personas sin seguro. CDMX tiene 10.2 y EDOMEX 4.5.
- Tiene acceso bajo (menos de la mitad del promedio) el 23% de las personas sin seguro en CDMX y el 58% en EDOMEX: 0.56 y 2.82 millones.
- Del acceso bajo, una parte se explica por saturación (hay unidad a ≤ 833 m, pero satura): 10% en CDMX y 26% en EDOMEX. Eso no se ve midiendo solo la distancia.
- Lo que más mueve el resultado es cómo se mide la capacidad: si cada unidad vale 1, solo se mantiene el 57-64% del acceso bajo. Hace falta CLUES.

**Qué se agregó:** `lib/acceso.py` y `notebooks/30_acceso_e2sfca.py`.

**Dónde está la evidencia:** `outputs/auditoria/acceso_e2sfca.json`, `outputs/intermedios/acceso_e2sfca_celdas.parquet`, `outputs/figuras/acceso_e2sfca_mapa.png` y `outputs/figuras/acceso_e2sfca_causas.png`.

## 2026-11-12 (cruce con marginación)

**Qué se quería:** cruzar el acceso con la marginación oficial y decidir si CDMX y EDOMEX se separan.

**Qué se aprendió:**

- La prioridad (acceso bajo y marginación Alta o Muy alta, según el índice de CONAPO 2020 por AGEB) abarca 66 mil personas sin seguro en CDMX (3%) y 956 mil en EDOMEX (20%).
- En CDMX, el acceso baja conforme sube la marginación: la mediana pasa de 1.65 a 0.09 veces el promedio. En EDOMEX el acceso es bajo en todos los grados de marginación.
- Quitar del índice de CONAPO el % sin derechohabiencia apenas cambia la prioridad: coincide en 87-91%.
- El acceso se calcula junto porque la cuenca de 1.7 km ya limita la interacción entre zonas. Lo que sí es una decisión es la referencia del acceso bajo. Se usa el promedio metropolitano, para que todos se midan con la misma vara; como sensibilidad se usa el promedio de cada zona.

**Qué se agregó:** `notebooks/30b_cruce_marginacion.py`, `lib/acceso.marginacion_conapo` y `Datos/CONAPO/IMU_2020.xls`, que está fuera de git.

**Dónde está la evidencia:** `outputs/auditoria/acceso_marginacion.json` y `outputs/figuras/acceso_marginacion_mapa.png`.

## 2026-11-12 — F4: persistencia de las zonas de acceso bajo
- **Qué se aprendió:** filtración por subniveles de una función sobre una rejilla (complejo cúbico, H0). Cada componente nace en un mínimo local del acceso y muere al unirse con una más vieja. Sirve para partir las zonas grandes de acceso bajo en núcleos distintos. Detalle: la componente que nunca muere recibe "el resto" de su región, así que su extensión no es una isla.
- **Qué se agregó:** `notebooks/31_persistencia_acceso.py` (union-find propio, idéntico a `gudhi.CubicalComplex`: 3,236 pares finitos y 276 esenciales). Se hicieron 100 réplicas sorteando la capacidad dentro de los rangos de DENUE. `lib/acceso.py` ahora contiene el E2SFCA.
- **Resultado:** 370 islas estables (sin contar el "resto"). Por el criterio fijado, solo 11 de 556 zonas de {f < 0.5} contienen ≥ 2 islas estables. Pero en esas 11 vive el 76% de las personas con acceso bajo (2.58 de 3.38 millones). Ahí la persistencia separa núcleos, por ejemplo el oriente: Iztapalapa, Chicoloapan, Ixtapaluca y Valle de Chalco.
- **Evidencia:** `outputs/figuras/persistencia_acceso.png`, `outputs/auditoria/persistencia_acceso.json`.

## 2026-11-12 — F5: optimización con varios objetivos
- **Qué se aprendió:** el objetivo cambia dónde se abren las unidades. Con E2SFCA una unidad nueva suma acceso a sus vecinos sin tocar a los demás, así que los cuatro objetivos son submodulares y el voraz perezoso alcanza (MCLP con K = 10: voraz = exacto de CBC). "Reducir la brecha" y "sacar gente del acceso bajo" no son lo mismo: la brecha va a los lugares más hundidos (f ≈ 0), donde 14 personas de personal no alcanzan a cruzar el umbral.
- **Qué se agregó:** `notebooks/32_optimizacion.py` (MCLP, p-mediana truncada, peor 10%, brecha E2SFCA, frontera α, cota de Minoux, aleatorios, réplicas, sin peso de marginación). `nb31` ahora guarda `islas_acceso.parquet`.
- **Resultado (K = 20):** brecha −6.5% contra −4.0% del MCLP, pero con 42% de su cobertura, así que por el criterio fijado la brecha **no gana**. Peor 10% saca a más personas del acceso bajo (33 mil, 31 mil de ellas en marginación alta). El peso ×2 por marginación cambia 18 de 20 sitios. Con unidades de 14 personas casi ninguna isla de F4 sube 0.25 (0–4 de 370 con K = 20; hasta 15 con K = 50).
- **Evidencia:** `outputs/figuras/optimizacion_mapas.png`, `outputs/figuras/optimizacion_frontera.png`, `outputs/auditoria/optimizacion.json`, `outputs/auditoria/optimizacion_sitios.csv`.
- **Sensibilidad con unidades de 40 personas (K = 20):** la brecha baja 15.4% (contra 6.5% con 14) y saca a 121 mil personas del acceso bajo, 108 mil de ellas en marginación alta. Ahora mueve tanta gente como el MCLP (123 mil), pero cubre 62% de lo que cubre él, así que el criterio sigue sin cumplirse. Islas de F4 atendidas: 6 de 370 (8 con K = 50). Figura: `outputs/figuras/optimizacion_capacidad40.png`.

## 2026-11-13 — F6: distancias por calle (caminata)
- **Qué se aprendió:** con la red peatonal real de OpenStreetMap (4.6 M nodos) el rodeo mediano es 1.33, muy cerca del 1.35 supuesto. El promedio se sostiene, pero la dispersión es grande (p25–p75: 1.22–1.47), y eso mueve a la gente de un lado al otro del umbral de 0.5. Dijkstra local (solo nodos dentro de la cuenca en línea recta) hace que 14 mil orígenes tarden 2 min.
- **Qué se agregó:** `notebooks/33_red_real.py`, `lib/red_peatonal.py` (PBF → grafo disperso → pares por calle) y `lib/topo_rejilla.py` (H0 de F4 reutilizable).
- **Resultado:** 92% de las personas con acceso bajo siguen igual. Spearman 0.92. Porcentaje bajo casi idéntico (CDMX 23.1%, EDOMEX 58.7%). Pero solo 78% de las islas estables de F4 reaparecen (criterio: 80%), así que por la regla fijada la versión por calle pasa a ser la principal. F5 casi no cambia: 17 de 20 sitios iguales y los sitios de línea recta rinden 99% de los óptimos por calle.
- **Evidencia:** `outputs/figuras/red_real.png`, `outputs/auditoria/red_real.json`.

## 2026-11-18 — F4 repetida por calle, con estabilidad
- **Qué se aprendió:** por calle hay 1,025 islas y 736 son estables en las réplicas de capacidad. Pero 360 de esas 736 tienen nacimiento b = 0: son zonas sin ninguna unidad a 30 min de caminata. Ahí el acceso vale 0 sin importar la capacidad, así que esas islas salen estables por construcción. Las réplicas solo prueban la incertidumbre de capacidad, no la de la red de OSM.
- **Qué se agregó:** `notebooks/34_persistencia_calle.py`, que guarda `islas_acceso_calle.parquet`.
- **Resultado:** comparando estables contra estables, 69% de las 370 estables en recta tienen una estable por calle a ≤ 500 m, y ahí está el 53% de su gente con acceso bajo. 51 zonas de {f < 0.5} tienen ≥ 2 islas estables y concentran 2.77 de 3.41 millones de personas con acceso bajo. Por calle aparecen núcleos nuevos grandes, como Acolman (236 mil), Tlalpan y Toluca.
- **Evidencia:** `outputs/figuras/persistencia_calle.png`, `outputs/auditoria/persistencia_calle.json`.

## 2026-11-19 — ¿Los ceros por calle son reales? Mesetas y huecos de OSM
- **Qué se aprendió:**
  - Cuando una función tiene mesetas (acceso = 0 en miles de celdas), el mínimo de cada isla cae en un punto arbitrario de la meseta. Comparar islas por la distancia entre mínimos falla. Se cambió por una prueba de cuenca: el mínimo de A cae en el territorio {f < d} de alguna isla de B.
  - En OSM de México muchas avenidas urbanas son `trunk` (Av. Central, Primero de Mayo), y excluirlas las volvía muros. Se agregaron.
  - Aun así, en Ecatepec una celda a 133 m de una unidad del ISSSTE queda a 8.5 km por calle: el corredor Gran Canal / Av. Central no tiene cruces peatonales mapeados en ~4 km. Probablemente es un hueco de OSM.
- **Qué se agregó:** `notebooks/35_ceros_calle.py`, `Rejilla.en_cuencas` en `lib/topo_rejilla.py`, y `trunk` en `lib/red_peatonal.py`. Se volvieron a correr 33 y 34.
- **Resultado:** de las 561 mil personas con acceso 0 por calle, 173 mil están lejos de verdad, 214 mil en zona gris y 175 mil son sospechosas (80 mil con rodeo > 2: barrancas de Álvaro Obregón y Huixquilucan, y el corredor de Ecatepec). Con la prueba de cuenca, 84% de las islas estables en recta reaparecen por calle (con 95% de su gente con acceso bajo). Con el acceso en recta en las celdas sospechosas sobrevive 90% de las islas por calle. La geografía de F4 es robusta a usar calles.
- **Evidencia:** `outputs/figuras/ceros_calle.png`, `outputs/auditoria/ceros_calle.json`, más `red_real.json` y `persistencia_calle.json` actualizados.
- **Decisión:** Mario eligió la versión por calle como principal por realismo. Quedó anotado en `PLAN_ACCESO.md` (F6), junto con la limitación de los cruces faltantes en OSM.

## 2026-11-19 — F5 por calle (versión principal)
- **Qué se agregó:** modo `DISTANCIA=calle` en `notebooks/32_optimizacion.py`. Usa el acceso por calle de hoy, las islas estables por calle, cobertura a ≤ 1,125 m y cuenca de 2,250 m de calle, y 13,636 candidatos con pares por la red. El modo en recta da resultados idénticos a antes.
- **Resultado (K = 20, 14 personas por unidad):** brecha −6.3%, peor 10% −5.5%, p-mediana −4.0% y MCLP −3.6%. La brecha sigue sin "ganar" (conserva 42% de la cobertura del MCLP). El voraz coincide con el exacto de CBC (K = 10). Las razones de Minoux van de 0.51 a 0.62 y el p95 de 200 conjuntos aleatorios es 1.7%. 14 de 20 sitios de la brecha reaparecen en ≥ 80% de las réplicas. Con 40 personas por unidad, la brecha baja 14.6% y saca a 137 mil personas del acceso bajo, 109 mil de ellas en marginación alta. Sitios iguales a la recta (≤ 500 m): MCLP 18/20, brecha 13, peor 10% 12 y p-mediana 12.
- **Evidencia:** `outputs/figuras/optimizacion_*_calle.png`, `outputs/auditoria/optimizacion_calle.json`, `outputs/auditoria/optimizacion_sitios_calle.csv`.

## 2026-11-21 — Correcciones tras la revisión de Claude + Codex (19 hallazgos)
- **Qué se aprendió:**
  - La "extensión" de una isla tiene que ser su cuenca ({f < d} conexa al mínimo). La etiqueta de entrada del union-find dejaba fuera las subcuencas fundidas en la isla.
  - Con mesetas de ceros, comparar islas por distancia entre mínimos no sirve, y "el mínimo cae en una cuenca" tampoco si no hay línea base. Lo correcto es emparejar cuencas uno a uno con Jaccard, maximizando primero las parejas con J ≥ 0.5.
  - El rodeo medido solo con pares que ya caben en la cuenca sale sesgado a la baja.
  - Codex sirvió como segundo revisor de las propias correcciones: encontró que los empates al mismo nivel pegaban subcuencas desconectadas y que el emparejamiento por suma de J podía perder parejas válidas.
- **Qué se agregó:**
  - `lib/f4.py`, con las piezas comunes de los notebooks 31 y 34.
  - En `lib/topo_rejilla.py`: `h0(cuencas=True)` (la cuenca de cada isla sale del union-find, en 2.5 s en vez de ~30 s), `particion` y `jaccard_emparejado`.
  - Huellas en los cachés (red, pares, partición de cuencas), rodeo sin censura, isla atendida por brecha cerrada en su cuenca, CBC publicado solo con optimalidad probada, JSON sin `NaN`, regla de `foot=yes`, superorigen con el anclaje mínimo, y "saturación" renombrada a "acceso bajo con unidad cerca".
- **Resultado:**
  - **F4:** las islas estables contienen 81% de la gente con acceso bajo por calle (2.75 de 3.39 M) y 59% en recta. Antes decíamos 44% y 41%: la respuesta a la pregunta clave de F4 pasa de "no" a "sí". Pero 2.58 M de esos 2.75 M están en islas que nacen en 0, estables por construcción, así que falta el nulo espacial.
  - **Recta contra calle:** 70% de las islas estables en recta tienen pareja por calle, pero solo 34% en el otro sentido. Las cuencas se traslapan con J = 0.58, contra 0.86 de los mapas de umbral. Se corrigió la frase "las dos versiones coinciden".
  - **Rodeo:** 1.39 (antes 1.33).
  - **F5:** sin cambios materiales. Islas atendidas con K = 20: 5–7 de 682.
  - **Cifras viejas:** las entradas del 13 y 18 de noviembre de este buzón quedan superadas por esta.
- **Evidencia:** `outputs/auditoria/persistencia_calle.json`, `persistencia_acceso.json`, `red_real.json`, `ceros_calle.json`, `optimizacion*.json`, `outputs/figuras/persistencia_calle.png`.

## 2026-11-22 — Nulo espacial de las islas (F4)

- **Qué se agregó:** `lib/nulo.py` (campos gaussianos Matérn por FFT, cópula por rangos,
  calibración por simulación) y `notebooks/36_nulo_espacial.py`. Diseño criticado con Codex:
  ceros fijos, gradiente urbano, significancia por isla con control de comparaciones múltiples.
  Dos cambios tras la prueba de humo, anotados en la cabecera: rampa junto a los ceros (sin ella
  el nulo creaba acantilados) y BH en lugar del máximo por réplica (sin poder).
- **Qué se aprendió:** el "81% de la gente con acceso bajo está en islas" no distingue nada:
  un relieve aleatorio da 87%. Ninguna isla es más profunda que el azar. Lo real es que el mapa
  tiene muchas más islas que nacen con acceso positivo (405 contra ~72): bolsas entre unidades.
  Moraleja: un resultado que suena fuerte necesita su nulo antes de contarse.
- **Evidencia:** `outputs/auditoria/nulo_espacial.json`, `outputs/figuras/nulo_espacial.png`.

## 2026-11-22 — Nulo de la oferta (F4/F5)

- **Qué se agregó:** `notebooks/37_nulo_oferta.py`. Reubica las 1,290 unidades al azar dentro
  de su municipio (sigue la demanda, uniforme, y con la oferta abierta) y recalcula E2SFCA por
  calle. Diseño criticado con Codex (una cola, diferencia mínima, efecto del redondeo).
- **Qué se aprendió:** la ubicación actual no es peor que una regla que sigue la demanda, y
  cubre más territorio (menos gente sin ninguna unidad). Solo 4% del acceso bajo se explica por
  la ubicación; el resto es falta de oferta. Un estadístico topológico (gente en cuencas de
  islas) resultó frágil: mover 21 unidades lo cambia 20 puntos.
- **Evidencia:** `outputs/auditoria/nulo_oferta.json`, `outputs/figuras/nulo_oferta.png`.

## 2026-11-22 — Sensibilidad a los parámetros de acceso (F4/F5)

- **Qué se agregó:** `notebooks/38_sensibilidad_f3.py`. Recalcula acceso, islas y los sitios de
  F5 con 4 formas de medir el acceso (30 o 15 min × gaussiano o escalones). Diseño revisado con
  Codex (veredicto por el peor escenario, emparejamiento uno a uno de sitios).
- **Qué se aprendió:** cambiar la forma del decaimiento casi no mueve nada (los mismos sitios
  logran 99.9% de la mejora). Cambiar el horizonte a 15 min sí: 3 M de personas quedan sin
  ninguna unidad y los sitios óptimos son otros. Un resultado de acceso siempre lleva su horizonte.
- **Evidencia:** `outputs/auditoria/sensibilidad_f3.json`, `outputs/figuras/sensibilidad_f3.png`.

## 2026-11-22 — Mapas por calle y tablas para entregar

- **Qué se agregó:** `notebooks/39_entregables_calle.py`. Rehace los mapas de acceso con la
  distancia por calle y exporta 4 CSV legibles (islas, sitios propuestos, municipios, zonas
  sospechosas de OSM) con coordenadas en grados.
- **Qué se aprendió:** por calle, 58% de la gente sin seguro de EDOMEX tiene acceso bajo
  (23% en CDMX); en EDOMEX 36% está lejos de toda unidad. Los primeros sitios de F5 reducen
  brecha sin sacar a nadie del umbral: atienden zonas con acceso 0, donde una unidad sube el
  acceso pero no lo suficiente.
- **Evidencia:** `outputs/entregables/*.csv`, `outputs/figuras/acceso_calle_*.png`,
  `outputs/figuras/acceso_marginacion_calle_mapa.png`.


## 2026-11-23 — Oferta oficial CLUES en lugar de DENUE (F8.1)

- **Qué se agregó:** `notebooks/29_oferta_clues.py`. Lee el catálogo CLUES de la DGIS
  (oct-2026) y Recursos en Salud 2025, y coteja contra DENUE con una asignación húngara a
  ≤ 200 m. `lib/acceso.py` cambia de fuente con `OFERTA` (denue, clues, clues_ampliado). Se
  recalcularon los notebooks 30 a 39 con médicos como capacidad, y DIF y municipales quedaron
  como escenario ampliado.
- **Qué se aprendió:**
  - El dato oficial pasa la regla de F1: 98.8% de las unidades tiene coordenadas y recursos.
    Pero DENUE contaba DIF, municipales y hasta bomberos como sector público.
  - `per_ocu` era un buen proxy de la capacidad por unidad (Spearman 0.80).
  - Con CLUES se duplica la gente sin ninguna unidad (1.13 M) y la ubicación actual sale
    *mejor* que el azar.
  - Error de dominio: si la oferta cubre más territorio que la demanda, las unidades sin
    nadie alrededor inflan el promedio y fabrican acceso bajo. Se vio al revisar un
    desplazamiento de 6.7 km en el nulo de la oferta.
- **Evidencia:** `outputs/auditoria/oferta_clues.json`, `outputs/figuras/oferta_clues_cotejo.png`
  y los JSON y figuras de los notebooks 30 a 39 recalculados. La versión DENUE está en git
  (`HEAD`) y en `outputs/intermedios/archivo_denue/`.

## 2026-11-23 — ¿Los ceros por calle son huecos de OSM? (F8.2)

- **Qué se agregó:** `notebooks/40_cruces_osm.py`. Corrige la red peatonal con los dos
  defectos típicos de OSM (calles que se cruzan sin nodo y sin salidas a ≤ 20 m de otra calle)
  en un escenario permisivo y repite E2SFCA y las islas por calle. `lib/red_peatonal.py` ahora
  permite fijar los anclajes en `Red.pares`.
- **Qué se aprendió:**
  - Aun conectando ~20 mil enlaces, incluidos puentes legítimos, solo el 18% de la gente en
    zonas sospechosas gana acceso, y el 89% de las islas sobrevive.
  - Los ceros por calle son sobre todo barreras reales (barrancas, sierra, canal), no datos
    malos.
  - Una prueba de sensibilidad que reemplaza lo dudoso por el mejor caso (el híbrido del 35)
    puede exagerar la fragilidad. Corregir el dato con una regla explícita da una respuesta
    más honesta.
- **Evidencia:** `outputs/auditoria/cruces_osm.json`, `outputs/figuras/cruces_osm.png`.

## 2026-11-23 — ¿Cuántas unidades convienen? (F8.3)

- **Qué se agregó:** `notebooks/41_cuantas_unidades.py`. Curvas de K = 1 a 500 para cuatro
  soluciones: llegar a los peores, cobertura (MCLP), mixta y ampliar las unidades saturadas.
  Las metas ("cuántas") quedaron fijas antes de correr.
- **Qué se aprendió:**
  - Con unidades de 3 médicos, 49 cierran una cuarta parte de la brecha y 130 la mitad.
  - Ampliar las unidades que ya existen necesita casi 5 veces más médicos para la cuarta
    parte y nunca llega a la mitad. El problema es de lugar, no de tamaño: la brecha está
    donde no llega ninguna unidad.
  - Una curva dice más que un K fijo: muestra dónde empiezan los rendimientos decrecientes.
- **Evidencia:** `outputs/auditoria/cuantas_unidades.json`,
  `outputs/auditoria/cuantas_unidades_curvas.csv`, `outputs/figuras/cuantas_unidades.png`.

## 2026-11-23 — Transporte público con r5py (F8.4)

- **Qué se agregó:** `notebooks/42_transporte_publico.py`. Usa r5py (motor R5 en Java) con el
  GTFS de la CDMX y el PBF de OSM recortado a la zona. Calcula tiempos puerta a puerta de 30
  minutos de cada unidad a cada celda, con un control a pie en el mismo motor y una muestra
  para medir la asimetría entre ida y vuelta.
- **Qué se aprendió:**
  - En CDMX el transporte baja el acceso bajo de 27% a 21%. En EDOMEX no cambia nada, porque
    el GTFS casi no llega ahí (solo el 5% de su gente sin seguro vive cerca de una parada).
  - El transporte ayuda donde ya hay red: de la gente con prioridad (acceso bajo y
    marginación alta) casi nadie sale de acceso bajo.
  - Medir contra un control en el mismo motor separa el efecto del transporte del efecto de
    cambiar de red de calles.
  - Problemas prácticos: JPype tomaba un Java viejo, el GTFS oficial trae errores de formato y
    sus calendarios ya vencieron, y la corrida se detuvo una vez por falta de memoria (se
    retomó desde los bloques guardados).
- **Evidencia:** `outputs/auditoria/transporte_publico.json`,
  `outputs/figuras/transporte_publico.png`.
