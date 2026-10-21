# Punto de partida, dirección del producto y planteamiento de Gold

Fecha: **19-10-2026**. Diseño inicial aceptado para desarrollar la primera
versión. Actualización 20-10-2026: [contrato inicial de tablas](CONTRATO_GOLD.md)
implementado para contexto municipal, instalaciones e incertidumbre en la
[primera etapa Gold](GOLD_MUNICIPAL.md). Las [variables y normalización](VARIABLES_NORMALIZACION_GOLD.md)
cuentan con un bloque propio; radios, pesos definitivos y formulación de la
selección espacial siguen pendientes. El
[contrato de candidatos y proximidad](CONTRATO_CANDIDATOS_GOLD.md) concreta
la segunda etapa, [materializada y validada](CANDIDATOS_GOLD.md).

## Acuerdo de diseño y punto de reanudación

Se adopta como dirección de trabajo la recarga de destino, combinando demanda
potencial y cobertura territorial, con contexto municipal y posterior revisión
de emplazamientos. Se acepta comenzar con indicadores explicables y
priorización multicriterio, y estudiar después una selección conjunta de sitios
que considere cobertura y solapamiento. No se plantea ahora una red neuronal
de predicción de uso sin una variable objetivo observada.

Se acepta ensayar demanda/cobertura 60/40 como escenario inicial y contrastarlo
con 50/50 y 70/30; no son pesos definitivos. La evaluación comparará criterios
sencillos y sensibilidad a datos y supuestos. Se distinguirá información no
evaluable (gris) de incertidumbre parcial (trama o símbolo con explicación),
sin convertir los pendientes de asignación en ausencia de cargadores.

**Actualización 20-10-2026:** [comparación de copias MITECO](COMPARACION_RECARGA_MITECO.md)
completada. Se prepara una versión diferenciada con la exportación
adquirida el 18-10, conservando nueve ausencias como incertidumbre y sin inferir
cierres. Las 81 admisiones documentales mantienen identidad y ubicación.
La elección y la [preparación diferenciada](RECARGA_VERSIONADA_SILVER.md) se han
completado después de la comparación: 1.517 instalaciones presentes, 1.466
admisiones y 51 pendientes; nueve ausencias históricas conservadas por separado.
Silver original no se sustituye.
Las primeras tablas quedan especificadas en el [contrato inicial](CONTRATO_GOLD.md):
claves, unidad de fila, periodos, indicadores, integración, estados de
incertidumbre y controles. No sustituir Silver ni trasladar evidencia
a registros cambiados automáticamente. Las tres tablas iniciales están
materializadas y validadas; la etapa de candidatos añade cuatro tablas verificadas.
La priorización queda pendiente.

## Dónde estamos

Bronze conserva las copias originales y su procedencia. Silver prepara las
entidades de cada fuente, mantiene sus claves, tipos, geometrías y periodos,
y comprueba relaciones y calidad. El [inventario vigente](TABLAS_Y_COLUMNAS_SILVER.md)
recoge 48 tablas y 502 columnas, incluidas doce de recarga versionada; la
[validación conjunta histórica](VALIDACION_CONJUNTA_SILVER.md) conserva sus 36
tablas y cierre operativo con limitaciones explícitas. No se suman las dos
versiones de recarga.

Disponemos de una referencia de 542 municipios de Comunitat Valenciana; parque
DGT y Distintivo 0 como aproximación de demanda potencial; población y renta;
recarga existente con entidades instalación/punto/conector; aforos y red viaria;
POI de OSM; y la capa complementaria de capacidad de demanda i-DE.

La recarga conserva 1.526 instalaciones, de las que 1.474 tienen relación
municipal admitida y 52 quedan pendientes. i-DE aporta 423 puntos de conexión
con relación admitida en 116 municipios. Estas cifras describen las copias
conservadas y su cobertura, no un inventario exhaustivo de toda infraestructura
o distribuidora.

Los cinco segmentos IGN degenerados se conservan señalados y excluidos de
cálculos métricos. Las 52 asignaciones de recarga pendientes se mantienen para
posible revisión futura. Se ha acordado avanzar con ambas limitaciones y
comunicar en Gold la incertidumbre de asignación, sin interpretarla como ausencia
de cargadores. Las fuentes tampoco comparten una única fecha de observación.

## Hacia dónde nos dirigimos

El producto apoyará a administraciones públicas y operadores en la decisión de
**dónde ampliar la infraestructura pública de recarga y qué zonas o ubicaciones
merecen atención prioritaria**, mostrando los factores que justifican la
comparación y sus límites. La salida final se orienta a una aplicación web,
según el alcance descrito en la [Entrega 02](entregas/02_datos_y_preparacion.md).

Las preguntas principales confirmadas el 20-10 son «¿Qué zonas necesitan la
instalación de cargadores eléctricos?» y «¿Hay suficiente oferta de cargadores
en la zona?». El producto las abordará como priorización relativa de zonas y
contraste de oferta registrada con demanda potencial y proximidad. No acreditará
necesidad exacta o suficiencia operativa sin datos de uso y un criterio adecuado.

La tercera pregunta, sobre infraestructura necesaria para instalar cargadores,
es opcional. La aportación posible de i-DE se limita a contexto orientativo
de red eléctrica publicada; no acredita viabilidad integral de un emplazamiento.
El [contrato Gold](CONTRATO_GOLD.md) concreta qué parte responde cada etapa.

El recorrido previsto es:

**Fuentes conservadas → entidades verificadas → indicadores comparables →
evaluación y priorización explicables → consulta del resultado en la aplicación.**

Los datos actuales permiten estudiar demanda potencial, oferta y cobertura
de recarga, contexto de movilidad y posibles emplazamientos. Distintivo 0 no
mide sesiones reales de recarga; los POI no acreditan disponibilidad de suelo;
la proximidad a un nudo i-DE no garantiza conexión. Estos límites deben acompañar
a las variables para que la comparación responda a lo que realmente observamos.

## Para qué sirve Gold

Gold organiza las variables que necesita la decisión del producto. Selecciona
qué conservar de Silver, define cálculos e indicadores, establece qué representa
cada fila y combina las fuentes sin multiplicar registros o mezclar magnitudes
incompatibles. Conserva además fechas, unidades, cobertura y calidad de cada
resultado. No equivale a unir todas las tablas en una tabla gigante.

Por ejemplo, Silver permite consultar cuántos vehículos con Distintivo 0 y
cuántos puntos de recarga admitidos tiene un municipio. Gold puede preparar
una relación interpretable entre esas cantidades, con denominador definido,
periodos identificados y advertencia si existen asignaciones pendientes.
Ese indicador no estima por sí solo consumo, rentabilidad o necesidad exacta
de nuevos cargadores.

La priorización posterior utilizará estos indicadores con un criterio explícito.
Gold no impone una puntuación, unos pesos o un modelo de aprendizaje automático.
La aplicación consumirá las salidas analíticas y sus explicaciones; su diseño
visual tampoco sustituye la definición de indicadores.

## Propuesta inicial de organización

Se ha acordado comenzar por **recarga de destino**, combinando demanda potencial
y mejora de cobertura territorial, con la secuencia **zonas → emplazamientos
candidatos**. La demanda puede recibir más peso como preferencia de decisión;
no se ha fijado una ponderación. La recarga de paso queda para otra versión.

Para desarrollar esa secuencia se propone la siguiente organización. El
municipio como contexto inicial es una elección de diseño recomendada por la
escala de las observaciones disponibles; no implica que cada municipio sea un
único emplazamiento ni que toda su población tenga la misma accesibilidad.

| Conjunto conceptual | Qué representa una fila | Para qué serviría |
| --- | --- | --- |
| Contexto territorial | Un municipio en una versión analítica definida. | Comparar demanda potencial, oferta de recarga y contexto territorial de los 542 municipios. |
| Contexto de candidatos | Una ubicación candidata revisada en esa versión analítica. | Comparar condiciones locales dentro de las zonas de interés, manteniendo su vínculo con el contexto municipal. |
| Calidad y procedencia | Una variable o resultado de una entidad, con sus fuentes, periodos y estado. | Explicar qué se conoce, qué falta y qué parte de la conclusión depende de datos inciertos. Puede integrarse en los conjuntos anteriores o mantenerse aparte. |

El nivel municipal permite una primera comparación con datos observados a esa
escala. El nivel de candidatos acerca el análisis a posibles emplazamientos.
Un dato de vehículos o renta municipal seguirá siendo contexto del municipio:
no se repartirá entre POI como si se hubiese observado en cada aparcamiento.

Antes de considerar cada POI un candidato físico único habrá que revisar
su uso y las correspondencias punto/área. El contrato de candidatos define
la preselección de destino, las relaciones sin fusión y el punto representativo
de cada geometría; queda pendiente materializarlo y revisar lugares físicos.
Una cuadrícula u otra unidad territorial puede evaluarse si aporta una mejora
demostrable; no se adopta por defecto ni se utiliza para aparentar mayor detalle
en los datos municipales.

## Variables que tendría sentido definir

Las expresiones siguientes son familias de variables propuestas, no cálculos
ejecutados ni un diccionario técnico aprobado.

| Dimensión | Posible contenido de Gold | Precaución que debe conservarse |
| --- | --- | --- |
| Demanda potencial | Distintivo 0, proporción sobre parque, población de contexto. | Son aproximaciones; no demanda real de sesiones o energía. |
| Oferta de recarga | Instalaciones, puntos y conectores, con características técnicas seleccionadas. | Separar entidades y relaciones admitidas de pendientes; no multiplicar conectores al unir tablas. |
| Cobertura y proximidad | Medidas definidas de cercanía o disponibilidad territorial de recarga. | No confundir pocos cargadores dentro del municipio con mala cobertura si hay oferta próxima al otro lado del límite. |
| Movilidad | IMD observada y relación de aforos con el entorno evaluado. | Ausencia de aforo no es tráfico cero; no sumar IMD de tramos o años sin una definición válida. |
| Contexto socioeconómico | Población y renta al nivel territorial apropiado. | Mantener nivel y periodo; el papel de la renta depende del objetivo y no determina automáticamente la prioridad. |
| Contexto eléctrico | Proximidad a puntos i-DE y capacidades publicadas consideradas individualmente. | Cobertura parcial, capacidad orientativa y no aditiva; ausencia de i-DE no significa capacidad cero. |
| Características del candidato | Tipo de emplazamiento, geometría y contexto espacial pertinente. | POI no acredita acceso público, terreno disponible o autorización para instalar. |
| Calidad | Periodos, ausencias, asignaciones pendientes y cobertura de cada variable. | Incertidumbre explícita y separada del valor; no convertir desconocidos en ceros. |

Las distancias o áreas de influencia se definirán según el uso del producto.
Una distancia geométrica deberá identificarse como tal; la red viaria actual
no está validada para calcular tiempos o distancias por carretera.

## Criterios adoptados y desarrollo previsto

### Objetivo y alcance acordados

- Combinar demanda potencial y cobertura territorial. Se considera dar mayor
  peso a demanda, sin pesos definitivos. La primera versión atiende recarga de
  destino: aparcamientos, comercios y otros lugares de estancia.
- Primero identificar zonas de interés y después revisar emplazamientos.
- El diseño de indicadores queda delegado al desarrollo técnico, comunicando
  las decisiones que necesiten una preferencia adicional del producto.
- Se solicita compatibilidad temporal entre recarga y territorio. Para renta,
  población y parque se admite estudiar años distintos; su estabilidad debe
  comprobarse, no suponerse.
- La visualización distinguirá zonas no evaluables y resultados con incertidumbre
  parcial, con explicación accesible. Su delimitación concreta está pendiente.
- El enfoque metodológico y la evaluación descritos a continuación se aceptan
  como dirección de trabajo. No representan un modelo entrenado, un ranking
  calculado ni resultados validados; los parámetros se concretarán antes de calcular.

### Indicadores iniciales recomendados

Actualización 21-10: la [definición de variables y normalización](VARIABLES_NORMALIZACION_GOLD.md)
concreta dos dimensiones, escalas y referencias. Propone distancia mínima
a la geometría original como brecha espacial, conservando el representante
como contraste. La definición está ensayada, aún sin tablas normalizadas o pesos.

Se recomienda separar demanda, oferta, cobertura y calidad para evitar que un
único índice oculte el motivo de la prioridad. Los indicadores de contexto y
proximidad al representante ya están preparados; la nueva comparación está pendiente.

| Indicador | Definición y escala | Uso y límite |
| --- | --- | --- |
| Demanda potencial municipal | Número de vehículos con Distintivo 0 del parque municipal DGT, con su fecha de referencia. | Aproximación inicial; no sesiones, consumo ni demanda localizada en cada POI. Proporción sobre parque como descripción complementaria, no otro voto independiente del mismo fenómeno. |
| Oferta confirmada municipal | Recuento de puntos con clave compuesta instalación/punto, asociados a instalaciones con municipio admitido. Instalaciones y conectores se describen por separado. | Describe la copia y las admisiones; conservar recuentos pendientes. Sin puntos confirmados no significa ausencia real cuando hay incertidumbre. |
| Presión descriptiva | Vehículos Distintivo 0 / puntos confirmados en el municipio, solo si el denominador es positivo. | Si es cero: valor nulo y estado explícito «sin puntos confirmados». No usar infinito ni convertirlo automáticamente en máxima prioridad. No mide ocupación de los cargadores. |
| Carencia de proximidad del candidato | Distancia geométrica en metros a la instalación de recarga registrada más cercana con coordenadas y relación admitidas, incluyendo oferta al otro lado de los límites municipales. | Aproximación de acceso espacial, no tiempo de conducción ni cobertura de personas. La sensibilidad a instalaciones pendientes se registra por separado. |

Como contexto: población INE con sexo **Total**, sin sumarla a Hombres/Mujeres;
renta neta media por persona al nivel municipal; características del lugar y de
la recarga; tráfico observado y capacidad i-DE individual. Población y parque
no se incorporan automáticamente como señales independientes con el mismo peso:
pueden duplicar el efecto del tamaño municipal. La renta no debe convertir por
defecto a municipios con menor renta en peores candidatos.

En recarga de destino, los aforos de carretera serán contexto complementario.
La clasificación destino/paso necesita criterios explícitos de uso y estancia;
no se deduce únicamente de potencia o corriente. Tampoco se sumarán potencias
de conectores como si acreditaran potencia simultánea de una instalación.

No hay datos de sesiones, energía vendida, ingresos, inversión o costes de
suelo/conexión suficientes para estimar rentabilidad. La dimensión económica se
interpreta inicialmente como oportunidad potencial, no beneficio previsto.

### Criterio temporal recomendado y pendiente concreto

Definir una fecha de referencia analítica y registrar para cada variable su
periodo real, publicación, adquisición conocida y desfase respecto a esa fecha.
Usar la observación más reciente disponible compatible con el corte, sin
presentar periodos distintos como simultáneos. Una coincidencia exacta entre
todas las fuentes no está acreditada.

Las copias actuales incluyen parque municipal a 31-12-2025, población hasta
2025 y renta hasta 2023; OSM es una instantánea de 09-09-2026. i-DE se refiere a
agosto de 2026 y se publicó el 04-09-2026. La relación INE es de 2025 y la
consulta territorial IGN es de 2026; esta consulta no acredita una edición
histórica exacta de los límites. Véase [procedencia](REFERENCIAS_TERRITORIALES.md).

La fecha de la instantánea CSV original MITECO sigue sin acreditarse; la fecha
de modificación de cada conector no equivale al corte del inventario ni a su
instalación. Existe otra exportación adquirida el 18-10-2026 y conservada para
la [revisión documental](REVISION_RECARGA_SILVER.md). Esa adquisición aporta una
observación fechada, no una fecha común de medición de todos sus registros.
La [comparación completa](COMPARACION_RECARGA_MITECO.md) del 20-10 propone usar
la copia adquirida el 18-10 en una versión diferenciada, conservando nueve
ausencias como incertidumbre. Su preparación diferenciada ya está validada,
con las 81 admisiones documentales revalidadas y las históricas conservadas.
La etapa municipal Gold ya está materializada; no trasladar automáticamente
las resoluciones municipales a registros diferentes en versiones posteriores.

La renta o población antiguas pueden ser útiles como contexto, pero la
estabilidad de medias y la evolución del parque se contrastarán con la serie
disponible. Revisar cuánto cambia la comparación usando otro año observado;
no extrapolar demanda futura por una tendencia general del parque.

### Incertidumbre: propuesta visual y analítica

Reservar el gris para resultados que no se puedan valorar por falta de datos
suficientes. Si hay información útil e incertidumbre parcial, mantener el color
de prioridad y añadir trama, contorno o símbolo, junto a una explicación del
motivo, variable afectada y registros pendientes. Las 52 asignaciones dudosas
no implican ausencia de toda la información municipal.

La explicación debe abrirse con cursor, clic y foco de teclado, y existir en
la ficha del resultado. No depender solo del color o del hover; referencias
[W3C sobre uso del color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)
y [contenido al pasar el cursor o recibir foco](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html).
La calidad acompaña a la prioridad y no actúa como penalización automática
contra territorios peor documentados. La regla geográfica de afectación aún
debe definirse sin asumir que todos los municipios candidatos estén confirmados.

### Modos de consulta del mapa, acordados el 21-10-2026

La visualización avanzará desde dos lecturas independientes, demanda potencial
y oferta registrada, hasta la prioridad relativa para estudiar nuevas
instalaciones. Se propone un selector de tres modos sobre el mismo territorio:

| Modo | Qué representa | Representación y límite |
| --- | --- | --- |
| Demanda potencial | Número municipal de vehículos con Distintivo 0 | Municipios coloreados por valor; es una aproximación, no un recuento exacto de vehículos recargables ni demanda observada. |
| Oferta registrada | Número municipal de puntos de recarga admitidos del escenario principal | Municipios coloreados y ubicaciones de instalaciones consultables; distinguir instalaciones, puntos y conectores, sin sumarlos como unidades equivalentes. |
| Prioridad de estudio | Combinación interpretable de demanda y separación respecto a la oferta | Mostrar componentes, escenario e incertidumbre; respetar el nivel municipal de demanda y la geometría de cada candidato. Pendiente de calcular y evaluar. |

La estética puede inspirarse en mapas de temperatura, con gradientes y una
leyenda clara. La demanda conocida es municipal: no interpolar sus totales
entre centroides ni dibujar variaciones dentro de un municipio como si se
conociera dónde están los vehículos. El primer diseño usará polígonos
municipales coloreados. La existencia de coordenadas de instalaciones permite
mostrar ubicaciones de oferta, pero no acredita su disponibilidad operativa.

La prioridad tampoco será una superficie continua inventada entre POI: el
contexto municipal y los candidatos conservarán sus unidades de observación.
Una mayor separación geométrica no demuestra por sí sola necesidad de recarga.
El tercer modo se denominará prioridad de estudio; no se presentará como
predicción de uso o número de cargadores necesarios.

Cada modo tendrá título, unidad, periodo y leyenda propios. Mantener sus
referencias de escala al filtrar el territorio y separar cero observado de
valor desconocido. La transformación visual se declarará si se comprimen
valores; no confundir la leyenda de recuentos con una puntuación normalizada.
Los pendientes de asignación y ausencias históricas seguirán como escenarios
e incertidumbre, sin agregarse silenciosamente a la oferta principal.

Este acuerdo define la presentación futura y no añade mapas ejecutables
ni un ranking. Las variables y normalización se preparan en un bloque propio,
antes de contrastar sensibilidad y ponderar.

### Método acordado y forma de evaluarlo

Comenzar con **priorización multicriterio interpretable**, manteniendo separadas
demanda y cobertura. Como escenarios de ensayo, comparar pesos demanda/cobertura
50/50, 60/40 y 70/30 después de definir indicadores y normalización. Son
preferencias ilustrativas, no pesos aprendidos ni una elección definitiva.
Evitar doble conteo y estudiar estabilidad del orden; el
[JRC trata la ponderación](https://knowledge-for-policy.ec.europa.eu/composite-indicators/toolkit_en/navigation-page/10-step-guide_en/step-6-weighting_en)
y su [análisis de sensibilidad](https://knowledge-for-policy.ec.europa.eu/composite-indicators/toolkit_en/navigation-page/10-step-guide_en/step-8-sensitivity-analysis_en).

Para escoger varios emplazamientos, estudiar después un modelo de
**localización y cobertura conjunta**: seleccionar un número de sitios bajo una
regla de cobertura, considerando el solapamiento y la oferta existente. Elegir
los primeros de un ranking sin considerar proximidad puede concentrar sitios
que aporten una mejora redundante. Esta familia de formulaciones tiene
antecedentes específicos de recarga, por ejemplo
[Lamontagne et al.](https://arxiv.org/abs/2206.11165).
Su aplicación exige definir candidatos elegibles, representación de la demanda,
distancia/radio y número de instalaciones o presupuesto. No se afirma que ya
podamos calcular personas o vehículos cubiertos por cada emplazamiento: los
datos municipales no aportan su localización dentro del municipio.

No se recomienda ahora una red neuronal ni predicción supervisada de uso:
no hay variable objetivo observada de sesiones, energía u ocupación. Entrenar
con presencia de cargadores podría reproducir decisiones e insuficiencias
existentes; entrenar con una puntuación propia solo imitaría esa puntuación.
La literatura distingue predicción con historial de uso y optimización de
emplazamientos: [Gopalakrishnan et al.](https://arxiv.org/abs/1604.05472).
El aprendizaje supervisado se reconsiderará si aparece un objetivo observado
adecuado, con validación espacial y temporal.

Evaluar el método es una decisión distinta de elegirlo. Plan propuesto:

1. Comparar, con los mismos candidatos y número de instalaciones, la propuesta
   combinada con referencias sencillas de solo demanda y solo carencia de
   proximidad. Informar por separado el beneficio de cada dimensión.
2. Medir mejora marginal y solapamiento bajo la representación de cobertura
   adoptada. No presentar una aproximación geográfica como nuevos clientes reales.
3. Revisar sensibilidad a pesos, radios, periodos y escenarios compatibles con
   las asignaciones pendientes. Distinguir resultados estables y dependientes
   de supuestos; estos escenarios no son intervalos estadísticos de confianza.
4. Revisar ejemplos urbanos, rurales y fronterizos, duplicidades y elegibilidad
   de sitios. Publicar las razones y límites de la recomendación.

Sin resultados observados posteriores de uso no procede declarar exactitud
predictiva, rentabilidad demostrada o impacto causal de las ubicaciones propuestas.

## Primer resultado esperado del diseño

Una especificación de Gold con objetivo de decisión, unidad de fila, tablas,
claves, indicadores, periodos, reglas de integración y controles de calidad.
Las primeras tablas ya están materializadas y verificadas desde Silver; queda
revisar si sus variables permiten distinguir situaciones útiles para el
producto. Ranking, modelos, optimización y aplicación se abordarán según esas
conclusiones y el alcance acordado.

El contrato de las primeras tablas e indicadores está definido como propuesta
inicial del 20-10. La entrada temporal de recarga ya está preparada y validada;
la [revisión de ejemplos y sensibilidad](REVISION_EJEMPLOS_GOLD.md) está completada.
Los [tres diagnósticos espaciales](CONTROLES_ESPACIALES_GOLD.md) ya están
materializados, conservando las tablas anteriores. La [definición de variables
y normalización](VARIABLES_NORMALIZACION_GOLD.md) añade referencias, variables
municipales y por candidato, con aviso de borde coherente con la geometría.
La [comparación de sensibilidad](SENSIBILIDAD_GOLD.md) está completada, sin cambiar
Gold. La fase de datos y preparación está terminada técnicamente. El diseño del
modelo queda en pausa, pendiente de orientación académica: antes de ensayar
ponderaciones se concretarán las reglas de combinación y el plan de evaluación.
Radios, pesos definitivos, revisión física y evaluación de
la selección conjunta se concretarán antes de su cálculo. Las fuentes, tablas
Silver y ejecuciones validadas se conservan; las etapas municipal y de candidatos
están implementadas, sin ranking calculado.
