# Auditoría y extensiones del análisis

**Fecha:** 2026-11-02. **Rama:** `mejoras/tda-avanzado`.

Revisa `reporte/trabajo_final.md` y `reporte/paper.typ` contra el código y los archivos
intermedios, y agrega tres experimentos. No modifica el reporte, el paper ni la
presentación, que son de cinco autores. Se puede reproducir con los notebooks `22` a
`25`; los resultados numéricos están en `outputs/auditoria/`.

## Resumen

1. **Lo que se sostiene:** las ubicaciones de los huecos son correctas, el K=7 de CDMX
   es el óptimo exacto de su problema y las coberturas de 42,687 y 35,868 personas se
   reproducen. Los huecos grandes resisten perturbaciones fuertes.
2. **Lo que hay que corregir:**
   - El análisis final usa el Alpha **clásico**, no Laguerre.
   - El aumento de +66% que se atribuye a Laguerre no viene de los hospitales.
   - La cobertura se calculó con distancia euclidiana × 1.35, no con la red vial.
   - La prueba de robustez no puede fallar.
3. **Lo más importante:** las clínicas propuestas casi no cierran huecos. Se cierra 1 de
   46 en CDMX y 2 de 77 en EDOMEX. Su valor está en alcanzar personas, no en cambiar la
   topología.

## 1. Cifras: reporte contra código

| Tema | Reporte y paper | Lo que hay en el código y los datos | Evidencia |
|---|---|---|---|
| Complejo que alimenta el scoring y el MCLP | Weighted Alpha (Laguerre), 118 y 241 huecos | Alpha clásico, 71 y 209; el 100% de `huecos_censal` coincide con el clásico y 0% con Laguerre | `notebooks/10_cruce_censal.py:87`, `auditoria.json` |
| Huecos habitados, CDMX | 62 de 118; en §8.2, "118 habitados" | 62 de 71 clásicos; con Laguerre serían 109 de 118 | `auditoria.json` |
| Huecos habitados, EDOMEX | 180 de 241 | 99 de 209 clásicos; con Laguerre, 131 de 241. El 180 no se pudo reproducir | `auditoria.json` |
| Personas sin seguro en huecos habitados | ~88,000 + ~182,000 = ~270,000 | 112,895 + 216,747 = 329,642. Sin repetir AGEB, 322,954 | `huecos_censal_*.parquet` |
| Causa del +66% de Laguerre | Heterogeneidad de hospitales | Efecto de la escala: pesos iguales dan 116 y 240; pesos barajados, 115 y 240 en promedio | Sección 2 |
| Fórmula del radio | `k·√per_ocu`; la mayoría < 50 m; hospitales de 300 a 500 m | `50 + 30·√per_ocu`; mínimo 102 m, máximo 570 m | `lib/tda.py:31` |
| Tiempos y cobertura | Red peatonal; radio de 1,125 m | Euclidiana × 1.35 en todos los candidatos guardados (`modo: euclidiana`), radio efectivo de 833 m | `soluciones_mclp_red.pkl` |
| Clínicas en EDOMEX | "9 ubicables" | **8** clínicas (Norte 2, Poniente 3, ZMVM 3). El 9 es el número de huecos cubiertos. También aparece en la figura de LinkedIn | `clinicas_subregionales_EDOMEX.pkl` |
| Por qué Oriente queda fuera | Sin candidatos válidos al umbral de 15 min | Sus 6 clusters quedaron fuera del corte de 20 candidatos; el mejor tiene rango 22. Sus tres mayores clusters suman 10,160 personas | `auditoria.json` |
| Clusters de EDOMEX | 74 y 77 en §8.3; 69 y 72 en §9.4 | 74 clusters y 77 huecos; §9.4 quedó de una versión anterior | `clusters_EDOMEX.parquet` |
| Marginación de huecos persistentes | 0.29 en §9.3; 0.28 en §11.1 | Inconsistencia interna | `trabajo_final.md` |
| Justificación de K=7 | Punto antes de la caída sostenida | La mayor caída de la tabla está en K=8→9, así que el codo sugeriría K=8. K=7 es una decisión razonable, no un codo | `trabajo_final.md` §9.2 |

**Cómo se cuenta la población.** Un hueco recibe toda la población de cualquier AGEB que
toque un disco de radio `pers/2`. Si solo se cuenta la parte de cada AGEB dentro de ese
disco, quedan 7,416 personas en CDMX, no 112,895. El disco de `pers/2` tampoco es el vacío
real. Usando el disco vacío verdadero (radio = muerte) y repartiendo la población de cada
AGEB por área, salen 116,996 en CDMX y 225,224 en EDOMEX. Así que el orden de magnitud
de unas 330,000 personas es defendible, pero por una razón distinta a la del reporte, y
supone población uniforme dentro de cada AGEB.

**Medida del hueco.** El radio del disco vacío es la muerte, no la persistencia. En la
mediana, la muerte es 1.75 veces la persistencia en CDMX y 2.85 en EDOMEX. Por eso
"persistencia = tamaño real del vacío" es incorrecto, y la regla `d < pers` no equivale a
caer dentro del vacío. Además, un hueco muere cuando los discos se llenan, no cuando "una
clínica lo triangula".

**Comprobado y correcto:**

- Gudhi conserva los índices de los puntos, así que las ubicaciones son válidas.
- El centro calculado de cada hueco coincide con el disco vacío (error 0.0 m).
- La selección K=7 de CDMX es el óptimo exacto; se comprobó con las 77,520 combinaciones.
- 42 de 46 y 74 de 77 huecos prioritarios tienen un hueco de Laguerre a menos de 500 m,
  así que usar uno u otro complejo cambia poco las zonas señaladas.
- Quitar la asistencia social (SCIAN 623 y 624) casi no cambia el conteo: 67 huecos en
  CDMX y 191 en EDOMEX.

## 2. Laguerre: por qué sube el conteo

![Conteo de huecos según el radio](../outputs/figuras/auditoria_laguerre_artefacto.png)

Con el mismo peso r² para todas las clínicas, la geometría es la del Alpha clásico. Los
pares de símplices son los mismos y solo se desplaza la filtración: α' = α − r². Pero la
persistencia se mide como √α'(muerte) − √α'(nacimiento), y esa diferencia crece al
acercarse a cero. Además, `ciclos_H1` recorta a 0 los nacimientos negativos.

| | Clásico | Pesos iguales | Pesos barajados (media de 10) | Laguerre real |
|---|---|---|---|---|
| CDMX | 71 | 116 | 115.1 | 118 |
| EDOMEX | 209 | 240 | 239.6 | 241 |

La ponderación sí cambia **cuáles** huecos aparecen: 36 de los 118 de CDMX no tienen
equivalente a 500 m con pesos iguales. Lo que no explica es **cuántos** hay.

## 3. ¿Las clínicas cierran los huecos?

`notebooks/23_cierre_real.py` agrega las clínicas a la nube de puntos, recalcula la
persistencia con el Alpha clásico y sigue cada hueco prioritario. La regla del reporte se
reprodujo exactamente, así que la diferencia viene de medir y no de los datos de partida.

| | CDMX (7 clínicas, 46 huecos) | EDOMEX (8 clínicas, 77 huecos) |
|---|---|---|
| Regla del reporte: cerrados, parciales, persistentes | 3, 4, 39 | 6, 2, 69 |
| **Medido: cerrados, modificados, intactos** | **1, 13, 32** | **2, 8, 67** |
| Modificados que quedan más chicos | 4 de 13 | 5 de 8 |
| Reducción de persistencia según el reporte | 14.9% | 16.5% |
| **Reducción medida** | **2.3%** | **7.4%** |
| Reducción con selección al azar (media; p5 a p95) | 5.5% (2.8 a 8.0) | 7.4% (5.0 a 9.5) |
| Clínica en el centro de los K huecos más persistentes | 16.7%, 0 cerrados | 10.3%, 1 cerrado |
| Huecos ≥ 200 m en toda la región, antes y después | 71 → 72 | 209 → 210 |

![Persistencia antes y después](../outputs/figuras/cierre_real_antes_despues.png)

Tres lecturas:

- **Una clínica no cierra un hueco grande, lo parte.** Incluso en el centro exacto del
  vacío suele dejar fragmentos ≥ 200 m. Por eso el conteo global sube. Los huecos cerrados
  son todos pequeños (239 a 273 m), y los más grandes de CDMX (1,510 y 1,292 m) quedan
  intactos.
- **En persistencia, el MCLP no supera al azar.** En CDMX queda por debajo del percentil 5
  y en EDOMEX iguala la media.
- **En personas, sí gana en CDMX.** Alcanza a 42,687 personas sin seguro a menos de 833 m,
  contra una media de 22,403 al azar (p95: 31,343) y 15,419 con la colocación topológica.
  En EDOMEX, los 35,868 quedan dentro del rango del azar (media 25,707; p95 37,503): la
  restricción por zonas sacrifica cobertura a cambio de presencia geográfica.

La distancia media a la clínica más cercana dentro de los discos vacíos casi no cambia:
de 271 a 256 m en CDMX y de 359 a 346 m en EDOMEX.

![Línea base en persistencia](../outputs/figuras/cierre_real_lineas_base.png)

![Línea base en personas](../outputs/figuras/cierre_real_personas.png)

**Conclusión:** "validación topológica" no describe lo que hace el notebook 17. Las
clínicas se justifican por acceso de personas, no por cierre de huecos. Si el objetivo
fuera reducir vacíos, habría que optimizar otra cosa.

**Cómo se definió "modificado":** el par de símplices cambió y queda un hueco ≥ 200 m
centrado en el disco original. Ese hueco puede ser un fragmento o un vecino afectado, y por
eso puede ser más grande. "Cerrado" significa que no queda ninguno ≥ 200 m ahí, no que el
área quede bien cubierta.

## 4. Robustez real

La prueba del notebook 21 no puede fallar: un hueco con persistencia ≥ 600 m pasa por
definición los filtros de 100, 200 y 400 m. `notebooks/24_robustez_real.py` perturba los
**datos** y recalcula todo, con 40 réplicas por escenario.

| Huecos prioritarios que sobreviven | CDMX | EDOMEX |
|---|---|---|
| Quitando 10% de establecimientos | 87% | 84% |
| Quitando 30% | 67% | 62% |
| Ruido σ = 25 m | 84% | 88% |
| Ruido σ = 50 m | 73% | 79% |
| Ruido σ = 100 m | 59% | 65% |
| Ruido σ = 250 m | 29% | 42% |
| Ruido σ = 1,000 m (nulo) | 5% | 10% |

![Supervivencia de huecos](../outputs/figuras/robustez_real_supervivencia.png)

- **La persistencia sí predice estabilidad.** Con σ = 100 m sobrevive 93% de los huecos
  ≥ 400 m, contra 50% y 54% de los menores. Spearman: 0.84 y 0.81.
- **Muchos prioritarios son frágiles.** Con σ = 50 m, solo 22 de 46 en CDMX y 50 de 77 en
  EDOMEX sobreviven al menos 80% de las veces. La lista exacta de prioridades es menos
  firme que lo que sugiere el "100% de robustez".
- **El conteo no es evidencia por sí solo.** Al borrar la estructura fina con σ = 1,000 m
  quedan 57 huecos en CDMX (71 reales) y 361 en EDOMEX (209 reales). Pero casi nunca están
  en los mismos lugares: los huecos reales dependen de dónde están las clínicas, aunque
  su número se parezca al que produce la densidad sola.
- **Comparar contra el hueco nulo más grande es poco útil aquí.** Solo 3 huecos de CDMX y
  ninguno de EDOMEX superan el percentil 95 de la persistencia máxima nula, porque esa
  referencia la fija la periferia, sobre todo en EDOMEX.

![Modelo nulo](../outputs/figuras/robustez_real_nulo.png)

**Límites:** quitar puntos es una prueba fácil de pasar, y el radio de emparejamiento
(máx. de 100 m y media muerte) es una decisión mía. Con σ = 1,000 m, el ruido también lleva
puntos hacia zonas vacías, así que este nulo es exploratorio y no da valores p.

## 5. Otros sectores

`notebooks/25_otros_sectores.py` compara cinco sectores con el mismo pipeline.

| Sector | CDMX: puntos | Huecos | Con 10,149 puntos | EDOMEX: puntos | Huecos | Con 7,525 puntos |
|---|---|---|---|---|---|---|
| **Salud** | 21,585 | 71 | **73** | 30,787 | 209 | **185** |
| Educación | 10,406 | 79 | 79 | 19,681 | 233 | 218 |
| Comercio minorista | 198,738 | 71 | 81 | 393,087 | 283 | 217 |
| Alimentos y alojamiento | 56,992 | 77 | 80 | 93,730 | 257 | 202 |
| Servicios financieros | 10,149 | 83 | 83 | 7,525 | 141 | 141 |

![Huecos por sector](../outputs/figuras/sectores_huecos_mismo_n.png)

- **La salud no destaca por tener más huecos.** Con el mismo número de puntos es el sector
  con menos en CDMX y el segundo con menos en EDOMEX. Entre 31% y 61% de los huecos de
  salud coinciden con huecos de educación, comercio o alimentos.
- **Muchos huecos son de la forma de la ciudad.** CDMX tiene 71 huecos con 21,585 clínicas
  y también 71 con casi 200,000 comercios. Más puntos no los hacen desaparecer.
- **Muchos discos tienen poca actividad económica.** Solo 20 de 46 en CDMX y 25 de 77 en
  EDOMEX alcanzan 25% de la densidad típica de otros negocios. Esos discos reúnen 55% y 50%
  de las personas sin seguro contadas por el reporte. Son los candidatos más claros a "barrio
  sin clínica"; los demás pueden ser parques, industria o periferia.

![Actividad económica en huecos](../outputs/figuras/sectores_actividad_en_huecos.png)

**Límites:** el umbral de 25% es arbitrario y la distribución es continua, no hay dos grupos
claros. La densidad típica se mide alrededor de establecimientos de salud, que suelen estar
en corredores comerciales, así que tiende a ser alta. Es una señal para revisar zonas, no una
clasificación. Tampoco se distingue la atención pública de la privada, y eso importa para
personas sin seguro.

## 6. Lo que no se resolvió

- **Red vial real:** `outputs/redes` y `Datos/OSM` están vacías, así que no se pudo calcular
  el MCLP sobre red real. Si se corre `15_mclp_red_real.py` así, cae a euclidiana.
- **Laguerre en todo el pipeline:** no se reconstruyeron el scoring ni el MCLP con esos
  huecos. Además, antes habría que definir bien qué significa su persistencia.
- **Origen de 88,000, 182,000 y 180:** no se encontró en los archivos actuales.
- **Oriente y Norte:** falta correr el MCLP con los clusters de cada zona como candidatos.

## 7. Correcciones sugeridas al reporte y al paper

Las deben decidir los autores. En orden de importancia:

1. Decir que los huecos prioritarios salen del Alpha clásico, y presentar Laguerre como
   análisis de sensibilidad.
2. Retirar la explicación del +66% y la afirmación de "47 huecos invisibles".
3. Cambiar "validación topológica" por los valores medidos (1 de 46, 2 de 77; 2.3%, 7.4%).
4. Sustituir la prueba de robustez del notebook 21 por la de la sección 4.
5. Decir que la cobertura usa euclidiana × 1.35 con radio de 833 m.
6. Corregir a 8 clínicas en EDOMEX, la causa de Oriente, la fórmula del radio y las cifras
   de la sección 1. Lo de las 8 clínicas también afecta a `linkedin_3_resultados*.png`.
