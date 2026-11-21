# Buzón de este repo para Laboratorio IA

## 2026-11-21 — Codex (encargo 2026-11-19-codex-persistencia-homologica-analisis-de-datos)
- **Qué se instaló y dónde:**
  - Plugin `codex@openai-codex` 1.0.6 con su marketplace, en `.claude/settings.json` del repo (alcance de proyecto, sin commit). Para revertir: `claude plugin uninstall codex@openai-codex --scope project` y `claude plugin marketplace remove openai-codex --scope project`, o borrar el archivo.
  - Primero, `/plugin install` lo dejó en alcance **user** (en `~/.claude/settings.json`) porque no preguntó el alcance. La sesión lo detectó y lo movió con `claude plugin … --scope project`. La configuración global de Claude Code quedó limpia.
  - Global de Codex, para `REGISTRO_GLOBAL.md`: `~/.codex/config.toml` con `[windows] sandbox = "unelevated"`. No existía; lo creó la sesión a petición explícita de Mario. Para revertir: borrar el archivo.
- **Material revisado:** `git diff 2faf2d0..HEAD` (39 archivos): `PLAN_ACCESO.md`, `lib/acceso.py`, `lib/red_peatonal.py`, `lib/topo_rejilla.py`, `notebooks/30` a `35` y `outputs/auditoria/*.json`. Codex lo revisó con `/codex:adversarial-review --base 2faf2d0` más el foco del encargo. Claude, con un subagente `general-purpose` y el mismo prompt. La sesión verificó contra el código y los datos los hallazgos centrales de cada lista.
- **Hallazgos:**

| Hallazgo | Quién lo encontró | Estado |
|---|---|---|
| La prueba por cuenca (84%) no tiene línea base: una celda cualquiera con acceso bajo cae en esas cuencas el 75% de las veces | Claude | válido (grave) |
| La "extensión" de las islas deja fuera sus subcuencas: 44% contra 82% de la gente con acceso bajo dentro de islas | Claude | válido (grave) |
| La prueba por cuenca es asimétrica (84% contra 59%), y el salto de 77% a 84% mezcla dos cambios de método | Codex | válido |
| El rodeo (1.33) está censurado por el corte de 2,250 m; sin corte sale ~1.42 | ambos | válido |
| Faltan validaciones de F4 fijadas en el plan (nulo espacial, ruido de ubicación, parámetros de F3) | ambos | válido |
| El plan señala `red_real.json` como F5 principal; hay dos "F5 por calle" (17 contra 13 sitios iguales) | ambos | válido |
| El superorigen de `35_ceros_calle.py` suma anclajes en nodos compartidos (19 nodos, +26 m de media) | ambos | válido (impacto bajo) |
| Cifras viejas de antes de incluir `trunk` en notebooks y `BUZON_VIDEOS.md` | Claude | válido |
| "Isla atendida" mide en un mínimo arbitrario dentro de mesetas de ceros | Claude | válido |
| La estabilidad dice ≤ 500 m pero calcula < 500 m (78 casos) | Claude | válido (bajo) |
| `access=no` excluye vías con `foot=yes` | Claude | válido (sin medir) |
| El anclaje es al nodo más cercano, no a la arista | Claude | válido (bajo) |
| Error de texto en el conteo de indicadores de CONAPO | Claude | válido (solo texto) |
| Los cachés de red y pares no se invalidan si cambian sus entradas | Codex | válido (riesgo; los resultados actuales están bien) |
| El anclaje puede saltar barreras o ignorar componentes chicas | Codex | válido (sin medir) |
| CBC publica `exacto` sin exigir estado óptimo | Codex | válido (menor; hoy sale `Optimal`) |
| "Saturación" es solo el cruce de dos umbrales | Codex | válido (interpretación) |
| CONAPO sin dato se cuenta como marginación no alta (1,961 personas) | Codex | válido (menor) |
| `NaN` en tres JSON de auditoría | Codex | válido |

  Totales: Codex 11 válidos, 0 falsos, 6 que Claude no encontró. Claude 12 válidos, 0 falsos, 8 que Codex no encontró, incluidos los dos más graves.
- **Criterio del encargo:** se cumplió. Codex trajo 6 hallazgos válidos que Claude no encontró, ninguno falso ni genérico. Con un matiz: los suyos son de robustez del código, interpretación y formato. Los que cambian conclusiones del análisis los encontró Claude.
- **Tiempo:** igual o mejor. Codex tardó ~4 min y el subagente de Claude ~11.5 min, ambos en segundo plano. Hay que sumar ~15 min de arreglo de instalación, que solo pasa la primera vez.
- **Calidad:** igual, y se complementan. Codex es más fuerte en ingeniería: cachés, serialización, estados del solver, exactitud de etiquetas. Claude es más fuerte en metodología: corrió verificaciones con datos (líneas base, recálculos) y por eso encontró los dos errores que mueven conclusiones. Codex revisa estático y no ejecuta Python.
- **Fricción:** peor. `/plugin install` no ofreció el alcance de proyecto y lo instaló global. Con el sandbox de Windows desactivado, la primera revisión devolvió "No material findings" sin leer nada, igual que en Carly. Hizo falta leer `~/.codex/.sandbox/*.log` y el binario para encontrar la clave `windows.sandbox`. Además, `/codex:result` y `/codex:status` los corre el usuario, no la sesión.
- **¿La seguirías usando sin que nadie te lo pida?** sí, como segunda opinión en revisiones grandes de metodología contra código, junto con un revisor de Claude y no en su lugar. Juntos cubrieron 19 hallazgos distintos; cada uno solo, 11 o 12.
- **Notas:**
  - Los tokens no se midieron, por decisión de Mario del 2026-11-21. El subagente de Claude reportó 171k tokens por su cuenta.
  - El encargo dice que el `config.toml` "ya lo creó Mario". En este repo lo creó la sesión, porque Mario lo pidió.
  - No se corrigió nada del código. Las correcciones van por el flujo normal del repo con Mario. No hubo push.
