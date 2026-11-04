# Entrega 03 - Machine Learning

**Proyecto:** localización de nuevos puntos de recarga para vehículos eléctricos en la Comunitat Valenciana.

**Estado a 04-11-2026:** primera versión del apartado 1, con segmentación municipal como enfoque inicial de ML, pendiente de validación. Pendientes la especificación de entradas, los experimentos y su evaluación.

## 1. Qué problema resuelve el modelo

### Usuario y decisión

El usuario principal de esta primera versión será una persona responsable de planificar la infraestructura pública de recarga en una administración pública. Dispone de recursos limitados y necesita decidir **qué municipios de la Comunitat Valenciana estudiar primero para ampliar la recarga pública**.

La decisión corresponde a una fase previa a los estudios concretos de emplazamiento. Una primera selección territorial permitirá orientar esos estudios; la instalación requerirá después comprobar las condiciones locales del suelo, el acceso y la conexión eléctrica, entre otras.

### Mejora que busca el producto

Consultar por separado el parque de vehículos, la oferta de recarga y las características de cada municipio exige un esfuerzo de comparación y no proporciona por sí solo un criterio para seleccionar zonas.

El producto busca **facilitar una comparación consistente de las condiciones municipales y explicar por qué determinadas zonas merecen estudiarse antes**. Para ello partirá de la demanda potencial, la oferta registrada y el contexto territorial preparados en la [Entrega 02](02_datos_y_preparacion.md), conservando sus limitaciones e incertidumbres.

### Tipo de problema y aportación de Machine Learning

Se abordará un problema de **segmentación territorial mediante aprendizaje no supervisado (clustering)**. La pregunta del modelo será: **¿qué municipios presentan perfiles similares de demanda potencial y contexto territorial?**

El modelo agrupará municipios a partir de las características seleccionadas de Gold. El producto permitirá consultar esos perfiles y contrastar la oferta de recarga registrada entre municipios comparables. La oferta de recarga quedará fuera de las variables que construyan los grupos y se utilizará después en su interpretación y contraste. La selección concreta de variables se desarrollará en el apartado 2.

La hipótesis de utilidad es que esta comparación entre municipios de perfiles similares facilitará detectar contrastes de oferta que merezcan revisión y justificar qué zonas estudiar. Tener menos oferta que otros municipios del mismo perfil será una señal exploratoria, no una demostración de déficit. El modelo no producirá por sí solo un orden de inversión.

Este enfoque responde a los datos disponibles: no se ha identificado una variable observada que mida la necesidad real de nuevas instalaciones o el éxito de un emplazamiento. La segmentación permite estudiar patrones sin inventar esa etiqueta. No se considera demostrada su utilidad: deberá compararse con una segmentación sencilla de referencia y evaluarse su estabilidad, interpretación y aportación a la decisión.

### Unidad de observación y salida esperada

Cada observación representará **un municipio en la versión de datos utilizada para el análisis**. La salida esperada será su pertenencia a un grupo, acompañada de una descripción de las características del perfil. Los identificadores de grupo no tendrán un orden de prioridad.

No habrá una variable objetivo etiquetada de antemano. La oferta registrada y las advertencias de calidad se mostrarán como información complementaria para interpretar los perfiles. Una buena separación estadística de los grupos no acreditará por sí sola mejores decisiones de instalación.

### Momento de uso y alcance

El resultado se utilizará durante la planificación, antes de encargar estudios específicos, con la información disponible en ese momento. Esta primera versión analiza una fotografía territorial construida con las copias de la Entrega 02; no establece un horizonte de predicción futura. La preparación del experimento documentará el corte informativo y las fechas de referencia y disponibilidad de las fuentes, que no comparten necesariamente un mismo periodo.

El ámbito de decisión inicial es municipal. La comparación que ofrezca el producto no acreditará por sí sola necesidad exacta de cargadores, suficiencia operativa ni viabilidad de una instalación. La segmentación es el enfoque inicial de esta entrega; su incorporación al producto dependerá de la utilidad demostrada en la evaluación.

## 2. Datos de entrada y salida

Pendiente de desarrollo a partir de Gold.

## 3. Baseline y selección de modelos

Pendiente de desarrollo.

## 4. Validación y evaluación

Pendiente de desarrollo.

## 5. Decisión y uso en el producto

Pendiente de desarrollo.
