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
