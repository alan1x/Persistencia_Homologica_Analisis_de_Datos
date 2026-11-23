# Buzón para el índice

## 2026-11-02
- ESTADO: terminado -> activo. Se retomó para la serie de videos.
- HITO: auditoría y tres experimentos nuevos (cierre medido, robustez perturbando datos, otros sectores SCIAN) en `reporte/auditoria_y_extensiones.md` y `notebooks/22` a `25`. Encontró correcciones importantes al reporte, que siguen pendientes de decisión de los autores.
- HUECO RESUELTO: "Contenido de `reporte/trabajo_final.md`" -> se leyó y se contrastó con el código. Los huecos prioritarios salen del Alpha clásico, no de Laguerre, y la cobertura guardada usa euclidiana × 1.35, no red vial.
- HUECO RESUELTO: "Los resultados de la fase 3" -> K=7 en CDMX (42,687 personas, 44%) y 8 clínicas en EDOMEX (35,868, 19%). El reporte dice 9, pero ese número es de huecos cubiertos. La ficha habla de K = 1, 2 o 3 sobre 161 huecos habitados, que corresponde a una etapa anterior.
- HUECO RESUELTO: "Qué hay en `presentacion/`" -> presentación en Typst con sus PDF. También hay `reporte/paper.typ` y `presentacion/guion_slides_12-18.md`, y `clusteres_tda_salud_cdmx.pptx` no está ahí.
- LINAJE: el repositorio es `alan1x/Persistencia_Homologica_Analisis_de_Datos`. El trabajo es de cinco autores: Mario Carlos Gaitán, Rodrigo Jiménez, Andrés Kiewek, Juan Pablo Moral y Luis Alan Morales.

## 2026-11-03
- HITO: modelo revisado (`notebooks/26` y `27`) y corrección del reporte, el paper y la presentación en la rama `mejoras/tda-avanzado`. El hallazgo central es que los huecos topológicos casi no coinciden con las personas que están lejos de la oferta de salud.

## 2026-11-13
- HITO: el proyecto pasó de huecos topológicos a acceso medido (`PLAN_ACCESO.md`, `notebooks/30` a `33`). Incluye E2SFCA con cruce de marginación CONAPO, persistencia H0 por subniveles de las zonas de acceso bajo, optimización con cuatro objetivos y distancias por la red peatonal de OpenStreetMap. Falta F7 (escritura) y, opcional, transporte público con r5py.

## 2026-11-22
- HITO: validación de F4 completa (`notebooks/36` a `38`). Ni el nulo espacial (campos Matérn con ceros fijos) ni el nulo de la oferta (unidades reubicadas por municipio) dan evidencia de que las islas o la ubicación actual sean peores que el azar. El acceso bajo se explica sobre todo por falta de oferta: solo 4% es atribuible a la ubicación. Los resultados resisten un cambio en la forma del decaimiento, pero no un horizonte de 15 min; se reportan como acceso a pie en 30 min. Sigue pendiente F7 (escritura).

## 2026-11-23
- HITO: cambio de fuente de la oferta, de DENUE a CLUES/DGIS con Recursos en Salud 2025 (médicos como capacidad; DIF y municipales como escenario ampliado), y F3 a F5 recalculados (`notebooks/29`, `lib/acceso.py`). Cambia el veredicto del nulo de la oferta, que pasa a "mejor que el azar", y se duplica la gente sin unidad cercana (1.13 M). Sigue pendiente F7 (escritura).
