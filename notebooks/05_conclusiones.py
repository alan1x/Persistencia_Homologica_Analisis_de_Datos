# %% [markdown]
# # 05 — Conclusiones y discusión
#
# ## Hallazgos principales
#
# 1. **Fragmentación (H₀).** Ambas regiones inician con miles de componentes que
#    se fusionan al crecer el radio. CDMX se conecta a escalas menores (mayor
#    densidad); EDOMEX requiere radios mayores → cobertura más dispersa.
#
# 2. **Huecos de cobertura (H₁).** Los ciclos persistentes representan zonas
#    rodeadas de servicios de salud pero sin servicios *dentro*. EDOMEX tiene
#    muchos más huecos persistentes y de mayor radio (hasta varios km) que CDMX.
#
# 3. **Sin cavidades (H₂ ≈ 0).** Coherente con datos geográficos planos.
#
# 4. **Diferencia cuantificada.** Las distancias bottleneck/Wasserstein entre
#    los diagramas H₁ confirman que la topología de cobertura difiere de forma
#    sustancial entre CDMX y EDOMEX.
#
# 5. **Mapper.** Confirma la lectura: red más fragmentada en EDOMEX.
#
# ## Integración de las investigaciones propias
#
# - **Alpha_Complexes_Voronoi** → fundamenta el método de construcción
#   (Delaunay/Voronoi → Alpha = Čech restringido), clave para escalar a decenas
#   de miles de puntos en 2D.
# - **Grupos_Homologia** → da el marco para interpretar H₀/H₁/H₂ como invariantes
#   topológicos (componentes, ciclos, cavidades) y su persistencia.
# - **Mapper** → vista complementaria basada en lens + cover + clustering.
#
# ## Implicaciones económicas / urbanas
#
# - **Planeación urbana y salud:** los huecos H₁ de gran radio en EDOMEX señalan
#   zonas habitadas mal cubiertas → candidatas a nuevas unidades de salud.
# - **Distribución de recursos:** la escala de fusión de H₀ mide qué tan
#   accesibles están los servicios entre sí.
# - **Decisiones estratégicas:** las distancias entre diagramas permiten comparar
#   regiones (o el mismo lugar en el tiempo) de forma objetiva y reproducible.
#
# ## Limitaciones y trabajo futuro
#
# - Coords apiladas (mismo edificio) reducen vértices únicos; podría ponderarse.
# - Extender a otros sectores SCIAN y correlacionar huecos con densidad
#   poblacional (censo) para distinguir "hueco real" de "zona despoblada".
