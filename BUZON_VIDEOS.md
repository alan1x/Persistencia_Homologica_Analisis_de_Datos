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
