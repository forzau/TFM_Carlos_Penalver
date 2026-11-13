# Entrega 03 - Machine Learning

**Proyecto:** localización de nuevos puntos de recarga para vehículos eléctricos en la Comunitat Valenciana.

**Estado a 09-11-2026:** baseline y comparación de K-means, GaussianMixture y Bisecting K-means completados en desarrollo, con k de 2 a 10 y contraste específico con ocho grupos. GMM con dos grupos alcanza silhouette media 0,415 y K-means con tres, 0,327; ninguno supera la estabilidad media del baseline. K-means con tres grupos es la opción de trabajo y se ha realizado un piloto descriptivo de contraste con la oferta registrada. Selección definitiva y evaluación final pendientes; los 108 municipios de prueba final siguen reservados.

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

Cada observación representará **un municipio incluido en el ámbito de análisis, en la versión de datos utilizada**. La salida esperada será su pertenencia a un grupo, acompañada de una descripción de las características del perfil. Los identificadores de grupo no tendrán un orden de prioridad.

No habrá una variable objetivo etiquetada de antemano. La oferta registrada y las advertencias de calidad se mostrarán como información complementaria para interpretar los perfiles. Una buena separación estadística de los grupos no acreditará por sí sola mejores decisiones de instalación.

### Momento de uso y alcance

El resultado se utilizará durante la planificación, antes de encargar estudios específicos, con la información disponible en ese momento. Esta primera versión analiza una fotografía territorial construida con las copias de la Entrega 02; no establece un horizonte de predicción futura. La preparación del experimento documentará el corte informativo y las fechas de referencia y disponibilidad de las fuentes, que no comparten necesariamente un mismo periodo.

El ámbito de decisión inicial es municipal. La comparación que ofrezca el producto no acreditará por sí sola necesidad exacta de cargadores, suficiencia operativa ni viabilidad de una instalación. La segmentación es el enfoque inicial de esta entrega; su incorporación al producto dependerá de la utilidad demostrada en la evaluación.

## 2. Datos de entrada y salida

### Variables de entrada y salida esperada

La segmentación partirá de `gold_municipios`, con una fila por municipio en la versión analizada, aplicando las exclusiones documentadas más abajo. Se seleccionan inicialmente las siguientes variables:

| Variable de entrada | Campo de Gold | Aportación al perfil municipal |
| --- | --- | --- |
| Vehículos con Distintivo 0 | `vehiculos_distintivo_0` | Volumen de vehículos utilizado como aproximación de demanda potencial; no mide el uso real de recarga pública. |
| Proporción de vehículos con Distintivo 0 | `proporcion_distintivo_0` | Peso relativo dentro del parque municipal, calculado como vehículos con Distintivo 0 divididos entre parque total, en escala 0–1. |
| Renta neta media por persona | `renta_neta_media_persona_eur` de Gold, con el complemento temporal descrito a continuación | Contexto económico, expresado en euros por persona y año; una renta mayor no implica mayor prioridad de inversión. |
| Población total, como entrada opcional | `poblacion_total` | Tamaño demográfico. Más adelante se compararán versiones con y sin esta variable para valorar su aportación respecto a las demás. |

El parque total se conserva como denominador de la proporción y como contexto, sin incorporarlo como otra entrada. La oferta de recarga y los ratios que la incluyen quedan fuera del agrupamiento y se reservarán para el contraste posterior. El código municipal identificará cada resultado; nombres y geometrías permitirán consultarlo y representarlo.

La **salida esperada** será la pertenencia de cada municipio a un grupo, acompañada de una descripción del perfil elaborada a partir de las características de sus integrantes. No existe una variable objetivo etiquetada de antemano. Los identificadores de grupo no expresarán prioridad, y los perfiles no demostrarán por sí solos déficit de recarga.

La selección inicial deberá revisarse al evaluar los experimentos. Se adopta el tratamiento temporal de seis rentas ausentes y la media de comparables para Sempere, descritos a continuación; Puebla de San Miguel queda fuera del ámbito de esta primera segmentación. Se fija una representación inicial de distancias con logaritmo del volumen y estandarización por entrenamiento, descrita más abajo. No se ha elegido número de clusters de ML ni realizado pruebas con y sin población.

### Ámbito de análisis y exclusiones

La base municipal conserva los **542 municipios**, pero se excluye **Puebla de San Miguel (46201)** del ajuste y evaluación tanto del baseline como de la alternativa ML. Su parque registrado presenta una desproporción respecto a la población y existe evidencia documental de concentración de matriculaciones empresariales por ventajas fiscales, detallada en los riesgos. Se considera insuficientemente representativo de la demanda local que esta primera segmentación pretende aproximar. El tamaño reducido del municipio, por sí solo, no constituye un criterio de exclusión.

El ámbito inicial queda en **541 municipios**, todos con renta disponible para modelado: 534 publicada y siete estimadas, seis mediante histórico e IPC y una mediante media de comparables. La exclusión se registra en [exclusiones_segmentacion.json](../../config/exclusiones_segmentacion.json) y debe aplicarse antes de ajustar transformaciones, calcular medianas, entrenar o evaluar.

Los datos originales, Silver, Gold y la tabla completa de renta se conservan. Puebla de San Miguel se identificará como fuera del ámbito de segmentación, sin asignarle un grupo o interpretar su exclusión como ausencia de necesidad de recarga. Esta decisión limita la cobertura y no resuelve por sí sola posibles sesgos de domiciliación en otros municipios; se deberá mantener el mismo criterio si se confirman casos comparables.

### Tratamiento de las rentas ausentes para el modelado

Gold conserva ocho municipios sin renta publicada de 2023. Para seis se adopta una **estimación a partir del último valor anterior disponible, actualizado con el IPC a precios de 2023**. Se utiliza el mismo indicador municipal, renta neta media por persona, sin mezclarlo con otros indicadores o niveles territoriales:

`renta_estimada_2023 = renta_ultimo_valor × IPC_medio_anual_2023 / IPC_medio_anual_del_ultimo_valor`

Se emplea el IPC general de la Comunitat Valenciana, medias anuales de la [tabla histórica 50940 del INE, base 2021](https://www.ine.es/jaxiT3/Tabla.htm?t=50940). Los índices utilizados son 96,809 en 2020, 100,000 en 2021, 108,461 en 2022 y 112,288 en 2023. Se calcula sin redondear previamente el factor y se conserva el importe final con dos decimales.

| Municipio | Año del último valor | Renta publicada de origen (EUR/persona/año) | Renta estimada para 2023 (EUR/persona/año) |
| --- | ---: | ---: | ---: |
| Benimassot | 2022 | 14.089,00 | 14.586,12 |
| Famorca | 2020 | 13.720,00 | 15.913,72 |
| Tollos | 2020 | 13.720,00 | 15.913,72 |
| Espadilla | 2021 | 14.024,00 | 15.747,27 |
| Vallat | 2021 | 14.024,00 | 15.747,27 |
| Carrícola | 2022 | 14.150,00 | 14.649,28 |

La elección se apoya en una comprobación exploratoria sobre tres municipios pequeños con rentas publicadas en 2020 y 2023. La muestra se fijó por tamaño y provincia antes de consultar los importes de 2023: Benifallim, Castell de Cabres y Estubeny. La actualización produjo errores de +0,47%, +8,50% y −4,67%, respectivamente, frente a la renta publicada de 2023. El error porcentual absoluto medio fue 4,54%, frente a 12,55% conservando 2020 sin actualizar; mejoró en dos casos y empeoró en Castell de Cabres. Se acepta como aproximación inicial, sin considerar que tres casos validen el método de forma general ni garanticen esos márgenes para los seis municipios.

La estimación supone renta real constante: el IPC ajusta precios, no acredita la evolución efectiva de los ingresos. Además, el INE documenta [asignaciones territoriales para proteger las rentas de municipios pequeños](https://www.ine.es/GS_FILES/DocTrabajo/art_doctr122024.pdf); actualizar un valor histórico no elimina esa limitación ni los cambios metodológicos entre años.

#### Sempere: media de tres municipios comparables

Sempere no tiene renta disponible en la serie 2015–2023 conservada. Se adopta como aproximación la **media aritmética de las rentas estimadas para 2023 de Tollos, Famorca y Vallat**. Sempere tiene 33 habitantes y 50 vehículos en las copias utilizadas de 2025; esos tres municipios coinciden como los más próximos entre los seis anteriores al ordenar por separado las diferencias absolutas de población y de parque total. La renta no se utiliza como criterio para escogerlos. Es una selección por tamaño demográfico y parque registrado, sin afirmar equivalencia económica demostrada ni vecindad geográfica.

| Municipio donante | Código municipal | Población 2025 | Parque total 2025 | Renta estimada para 2023 (EUR/persona/año) |
| --- | --- | ---: | ---: | ---: |
| Tollos | 03130 | 34 | 46 | 15.913,72 |
| Famorca | 03068 | 44 | 71 | 15.913,72 |
| Vallat | 12123 | 68 | 64 | 15.747,27 |

El cálculo utiliza el mismo peso para cada municipio, sin ponderar por habitantes:

`renta_estimada_Sempere_2023 = (15.913,72 + 15.913,72 + 15.747,27) / 3 = 15.858,2366… → 15.858,24 EUR/persona/año`

Se redondea la media a dos decimales mediante `ROUND_HALF_UP`, partiendo de las rentas de modelado de los donantes ya expresadas en euros de 2023. No se aplica otro ajuste por IPC a esa media. El valor se identifica como `estimada_media_comparables`, conservando ausente la renta original de Sempere. La procedencia registra los tres códigos, sus valores, el método, los pesos iguales y el redondeo.

Este tratamiento **encadena estimaciones**: los tres donantes se actualizaron previamente con histórico e IPC. Además, Tollos y Famorca comparten el mismo valor de origen y no aportan dos mediciones económicas independientes. No se ha validado un margen de error para Sempere; se deberá comprobar la sensibilidad de su perfil al importe imputado. En la evaluación fuera de entrenamiento se recalcula la media con los donantes que pertenezcan al entrenamiento de cada ajuste, según la preparación descrita más abajo. La tabla de renta de referencia no sustituye esa preparación dentro de cada partición.

#### Conservación y cobertura de la renta de modelado

El tratamiento se materializa en una tabla separada, `rentas_modelado`, con los 542 municipios y enlace por versión Gold y código municipal. Conserva la renta original, el año y valor de origen cuando existen, índices y factor aplicados para el método temporal, `renta_modelado_2023_eur` y `estado_renta_modelado`. Las 534 rentas publicadas de 2023 permanecen idénticas, seis se identifican como estimadas con histórico e IPC y Sempere como estimada mediante media. Puebla de San Miguel conserva su renta ausente y queda excluida de la segmentación. La selección analítica incluye **541 municipios, sin rentas pendientes**. Gold mantiene sus ocho nulos originales y las versiones anteriores de modelado se conservan.

El baseline y la alternativa ML utilizarán el mismo tratamiento de renta dentro de cada partición, incluida la recalculación de Sempere. El estado será información de calidad, sin incorporarlo automáticamente como otra dimensión del agrupamiento. Se deberá revisar la sensibilidad de los perfiles a las siete estimaciones antes de interpretar sus resultados como robustos.

### Preparación por partición y escalas

Las rentas publicadas y las seis actualizaciones por histórico e IPC permanecen fijas: estas últimas utilizan información propia del municipio e índices externos ya establecidos, sin aprender estadísticas del conjunto reservado. Para Sempere se toma la media, con pesos iguales y redondeo a dos decimales, de los donantes previamente elegidos que estén en entrenamiento:

| Ajuste | Donantes de entrenamiento | Renta de Sempere (EUR/persona/año) | Papel de Sempere |
| --- | --- | ---: | --- |
| Interna 1 | Famorca, Tollos y Vallat | 15.858,24 | Entrenamiento |
| Interna 2 | Vallat | 15.747,27 | Entrenamiento |
| Interna 3 | Famorca y Tollos | 15.913,72 | Validación |
| Interna 4 | Famorca, Tollos y Vallat | 15.858,24 | Entrenamiento |
| Desarrollo completo | Famorca, Tollos y Vallat | 15.858,24 | Entrenamiento |

Se conserva por ajuste el importe y los códigos, valores y número de donantes. El caso de Vallat se identifica como un único donante. Si no hubiera ninguno, se detendría la preparación para revisar la regla, sin utilizar municipios de validación. Las versiones Gold y de renta de referencia no se sobrescriben.

Para evaluar distancias se utilizan **logaritmo natural de uno más el volumen de Distintivo 0**, proporción y renta, seguidos de estandarización de las tres columnas mediante `z = (x − media_entrenamiento) / desviación_entrenamiento`. Se emplea desviación poblacional (`ddof=0`); una variable constante utiliza divisor 1. Cada validación recibe los parámetros aprendidos exclusivamente de su entrenamiento, siguiendo [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html). Los umbrales del baseline se calcularán sobre las tres entradas originales; no necesitan estas escalas.

La elección inicial del logaritmo se apoya únicamente en desarrollo: el volumen presenta mediana 19, percentil 99 de 1.204,4 y máximo 10.246. `log1p` conserva los ceros y reduce el dominio de diferencias absolutas extremas. No se recortan ni eliminan municipios por estos valores. La estandarización hace comparables las unidades, sin garantizar igual importancia efectiva ni eliminar dependencias entre variables. En desarrollo, las correlaciones de Pearson son 0,461 entre volumen transformado y proporción, −0,189 entre volumen transformado y renta, y 0,238 entre proporción y renta; se conserva esta representación inicial, sin afirmar independencia.

La ejecución `20261106T112331494635Z` conserva entradas originales y escaladas para las cuatro validaciones y el desarrollo completo, parámetros de preparación, planes de estabilidad y manifiesto con huellas. Incluye 433 municipios únicos y 2.165 filas al repetirlos por ajuste; no son observaciones adicionales. Los 108 de prueba final no están incluidos en estas matrices. Las entradas de desarrollo contienen 426 rentas publicadas y siete estimadas. La preparación no ajusta grupos ni calcula resultados del baseline.

### Disponibilidad en el momento de uso y riesgos

#### Información disponible

Durante la planificación, el usuario consultará perfiles calculados con una versión identificada de Gold. Las entradas son estadísticas municipales ya disponibles en las copias conservadas de la Entrega 02; no requieren observar resultados futuros de instalaciones. La primera versión utiliza los siguientes periodos:

| Información | Referencia de los valores | Evidencia y límites de disponibilidad de la copia |
| --- | --- | --- |
| Parque total y vehículos con Distintivo 0 | 31-12-2025 | Excel municipal DGT descargado el 15-10-2026, con ficha de referencia temporal. Esa descarga no acredita su primera fecha de publicación. |
| Población total, opcional | 2025 | Copia contrastada por igualdad de SHA-256 con una descarga oficial el 15-10-2026. No se conoce la fecha original de adquisición. |
| Renta neta media por persona | 2023 | Copia local identificada por su huella. No están acreditadas su adquisición original ni su edición exacta; el descargable contrastado durante la preparación era diferente. |

La proporción de vehículos con Distintivo 0 utiliza numerador y denominador del mismo parque municipal. Para el contraste posterior se dispone de la copia principal de recarga adquirida el 18-10-2026, conservando pendientes y ausencias históricas por separado; esa fecha no indica cuándo comenzó a funcionar cada instalación.

Esta combinación describe una fotografía de información disponible, con distinta antigüedad por variable. No representa una situación simultánea de 2025 ni acredita que todas las copias estuvieran publicadas entonces. El experimento identificará la ejecución Gold y las huellas utilizadas. Una actualización deberá revisar periodos, definiciones, cobertura y compatibilidad con las transformaciones del modelo antes de comparar nuevos perfiles.

#### Fuga de información y circularidad

Aunque no exista una variable objetivo etiquetada, puede contaminarse la evaluación si se utilizan los municipios reservados para evaluar al ajustar el modelo o su preparación. Cuando se evalúe fuera de entrenamiento, cualquier imputación, escalado o selección de variables que se aprenda de los datos se ajustará únicamente con la parte de entrenamiento de cada partición. El conjunto final de evaluación no se utilizará para elegir variables, algoritmo o número de grupos; la estrategia concreta se definirá en el apartado 4, siguiendo las [precauciones de scikit-learn sobre fuga de información](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).

Se partirá de las columnas originales seleccionadas de `gold_municipios`. Las normalizaciones ya existentes en Gold, cuyas referencias se calcularon con todos los municipios, no se trasladarán automáticamente al experimento como si se hubieran ajustado solo con entrenamiento. Esto no requiere modificar las tablas Gold conservadas.

La oferta y los ratios que la incluyen permanecerán fuera de la formación de grupos. Incorporarlos y presentar después sus diferencias entre grupos como un hallazgo independiente introduciría circularidad en la interpretación. Además, el contraste con oferta no constituirá una etiqueta de necesidad real ni una validación independiente de mejores decisiones. Si en el futuro se simula una decisión histórica, solo podrán emplearse versiones cuya disponibilidad en esa fecha esté acreditada.

#### Calidad, sesgos y alcance de los perfiles

- **Ausencias y denominadores:** Gold conserva ocho municipios sin renta. El complemento de modelado estima seis mediante histórico e IPC y Sempere mediante media de tres comparables; Puebla de San Miguel queda excluida por el motivo documentado. Los 541 incluidos disponen de renta publicada o estimada, sin convertir ausencias en renta cero ni en menor demanda. El experimento deberá mostrar la cobertura y la influencia de las siete estimaciones. Se distinguirán ceros observados, ausencias y cocientes no calculables; las proporciones con parques pequeños requieren cautela.
- **Escalas y dependencia entre entradas:** vehículos, proporciones y euros tienen escalas distintas. El volumen y la proporción comparten numerador, y la población podría aportar información parecida al tamaño del parque. La preparación inicial revisa distribuciones y correlaciones solo en desarrollo y aplica logaritmo al volumen y estandarización por entrenamiento. Esto no resuelve todos los efectos de valores extremos o dependencias ni demuestra la necesidad de añadir población; su contraste permanece pendiente.
- **Demanda aproximada:** Distintivo 0 no equivale a un desglose exacto BEV/PHEV ni mide sesiones, energía o necesidad de recarga pública. La localización del parque registrado no describe todos sus desplazamientos. Las entradas seleccionadas tampoco miden directamente visitantes, movilidad de paso o acceso a recarga privada, por lo que los perfiles pueden omitir necesidades relevantes.
- **Domiciliación y flotas:** el municipio de registro no garantiza que los vehículos circulen o recarguen allí. Puebla de San Miguel tiene 53 habitantes, 502 vehículos y 65 con Distintivo 0 en la copia municipal DGT, cifras contrastadas con el Excel original. El [informe de AEA sobre fiscalidad municipal del automóvil de marzo de 2026](https://aeaclub.org/ivtm-impuesto-municipal-vehiculos-paraisos-fiscales/) incluye expresamente el municipio y registra 201 nuevas matriculaciones de turismos de empresa en 2025, dentro del fenómeno de domiciliación de flotas por ventajas fiscales. Esas matriculaciones anuales no son el parque total ni permiten descontar vehículos de él. No se ha identificado qué parte de los 502 o de los 65 con Distintivo 0 utiliza realmente el municipio; conservar el dato requiere advertir este sesgo antes de interpretarlo como demanda local o como señal del nivel económico de sus residentes.
- **Agregación y contexto económico:** las medias municipales ocultan diferencias internas. La renta no permite atribuir capacidad de compra a cada residente ni convertir un perfil económico en prioridad de inversión. Se revisará si los grupos distinguen características útiles para la planificación o reproducen principalmente tamaño y nivel de renta.
- **Comparación territorial y oferta:** municipios próximos pueden compartir condiciones; una partición aleatoria podría sobrestimar la capacidad de trasladar los perfiles a territorios diferentes. Se tendrá en cuenta al diseñar la validación. La oferta utilizada después conserva incertidumbre de asignación, versiones y cobertura; menor oferta registrada no demuestra déficit, ni los grupos garantizan acceso real o viabilidad de emplazamientos.

Estos riesgos orientarán la preparación y la evaluación. No se consideran resueltos por disponer de Gold ni por obtener grupos estadísticamente separados.

## 3. Baseline y selección de modelos

### Baseline ejecutado: segmentación mediante reglas por medianas

Se propone una referencia sencilla que permita responder: **¿aporta el clustering una comparación municipal más útil que unas reglas fáciles de explicar?** La referencia utilizará las tres entradas iniciales: volumen de vehículos con Distintivo 0, su proporción sobre el parque y renta neta media por persona. La población queda fuera de esta primera configuración; su contraste se mantiene para más adelante.

Para cada entrada se calculará la mediana de los municipios de entrenamiento y se aplicará una regla binaria:

| Dimensión | Categoría inferior | Categoría superior |
| --- | --- | --- |
| Volumen Distintivo 0 | Valor menor o igual a su mediana de entrenamiento | Valor mayor que su mediana de entrenamiento |
| Proporción Distintivo 0 | Valor menor o igual a su mediana de entrenamiento | Valor mayor que su mediana de entrenamiento |
| Renta neta media por persona | Valor menor o igual a su mediana de entrenamiento | Valor mayor que su mediana de entrenamiento |

La combinación de las tres categorías definirá el perfil de cada municipio. Por ejemplo, un perfil podría reunir volumen superior, proporción inferior y renta superior a sus respectivas medianas. Son posiciones relativas respecto al entrenamiento, sin umbrales oficiales de demanda ni orden de prioridad.

Habrá **como máximo ocho combinaciones posibles** (dos por cada una de las tres entradas). No se garantiza que todas aparezcan o tengan tamaños parecidos; los valores empatados permanecerán juntos y no se separarán municipios idénticos para equilibrar grupos. Ocho no se adopta como número óptimo de clusters para la alternativa ML.

Las medianas se mantendrán fijas al asignar los municipios de evaluación. Esta referencia no requiere sumar puntuaciones, elegir pesos entre dimensiones ni escalar variables para aplicar sus reglas. Es una discretización sencilla por el percentil 50, dentro de los enfoques de [discretización por cuantiles](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.KBinsDiscretizer.html); su definición no presupone incorporar una dependencia nueva.

Su limitación es que impone cortes por variable: dos municipios casi iguales pueden quedar separados al cruzar una mediana, mientras otros diferentes comparten una combinación. Servirá para comprobar si un método que estudie conjuntamente las distancias o relaciones entre variables mejora esa referencia. La comparación deberá usar los mismos municipios, entradas y tratamiento de ausencias, y considerar el número y tamaño efectivos de los grupos para no atribuir una mejora únicamente a una mayor fragmentación.

La primera ejecución ajusta medianas exclusivamente en el entrenamiento de cada partición y mantiene fijos esos umbrales al asignar su validación. Se conservan umbrales, asignaciones, cobertura, tamaños, métricas y trazabilidad de los ajustes. Puebla de San Miguel permanece excluida. Los resultados del apartado 4 establecen la referencia para una alternativa ML todavía no ejecutada; no constituyen una comparación de modelos.

### Alternativa de Machine Learning

Se comparan tres candidatos: **K-means**, **mezclas gaussianas (GaussianMixture)** y **Bisecting K-means**. Los tres permiten asignar municipios no utilizados en el ajuste sin volver a entrenar. K-means agrupa alrededor de centros; las mezclas gaussianas permiten modelar distinta dispersión y orientación y obtener probabilidades de pertenencia; Bisecting K-means divide grupos sucesivamente y aporta una estructura jerárquica, compartiendo familia con K-means. Su selección como candidatos no presupone que superen al baseline.

Se combinan una **comparación con k nominal igual a 8** y una **exploración común de k de 2 a 10**, utilizando únicamente el desarrollo y su validación cruzada interna. El primer análisis controla el número de grupos previsto; el segundo permite estudiar otras resoluciones. Se registrará también el número efectivo de grupos observados en validación, que puede ser menor que el configurado. El baseline conserva sus reglas y hasta ocho combinaciones, sin ajustar sus cortes para cada k. La elección atenderá conjuntamente a los cuatro objetivos del apartado 4; una mejora con otro k no se atribuirá exclusivamente al algoritmo.

#### Configuración fijada antes de la ejecución

Se mantiene la misma representación de tres variables y las mismas cuatro particiones del baseline. No se exploran otras covarianzas, transformaciones o familias durante esta primera comparación:

| Método | Configuración |
| --- | --- |
| [K-means](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html) | Inicialización k-means++, 20 inicios por ajuste, algoritmo Lloyd, máximo 500 iteraciones y tolerancia 0,0001. |
| [GaussianMixture](https://scikit-learn.org/stable/modules/generated/sklearn.mixture.GaussianMixture.html) | Covarianza completa, inicialización mediante k-means, 10 inicios por ajuste, máximo 500 iteraciones, tolerancia 0,001 y regularización diagonal de covarianza 0,000001. Asignación al componente de mayor probabilidad. |
| [Bisecting K-means](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.BisectingKMeans.html) | Inicialización k-means++, 10 inicios por bisección, división del grupo de mayor inercia, algoritmo Lloyd, máximo 500 iteraciones y tolerancia 0,0001. |

La semilla principal es 20261107 más el número de partición interna; las perturbaciones espaciales y la sensibilidad de renta conservan esa semilla. Para estudiar inicializaciones se repite el procedimiento completo con cuatro semillas adicionales, sumando 100, 200, 300 y 400, sin elegir la semilla según validación. Los inicios múltiples se eligen con el objetivo de entrenamiento propio de cada método. Los presupuestos de los algoritmos no son equivalentes: en Bisecting K-means los inicios son por bisección.

Cada una de las 27 combinaciones método/k incluye cuatro ajustes principales, 40 perturbaciones espaciales, 16 ajustes con semillas adicionales, cuatro sensibilidades de renta y un descriptivo sobre los 433 de desarrollo: **1.755 ajustes en total**. Los descriptivos sirven para interpretar perfiles, no como evaluación adicional. Se conservan asignaciones, parámetros de preparación, modelos principales, avisos de ajuste y huellas de procedencia. Las probabilidades de GMM pertenecen al modelo y no tienen calibración externa.

## 4. Validación y evaluación

### Estrategia de separación acordada

Se han fijado **433 municipios para desarrollo (80,04%) y 108 para prueba final (19,96%)**, con **validación por bloques espaciales y estratificación por población**. El reparto conserva completos los bloques; no se distribuyen municipios individualmente para alcanzar las proporciones.

Se utiliza una cuadrícula de **20 km de lado**, con origen fijo en (0, 0) del sistema métrico EPSG:25830 ya presente en Gold, sin reproyectar los datos. Cada municipio se asigna a una celda mediante un punto de su superficie calculado con `ST_PointOnSurface`; el municipio permanece como una sola observación. Se obtienen **73 bloques ocupados**, 14 en prueba final y 59 en desarrollo. Una celda es una agrupación operativa por ubicación representativa, sin afirmar que contenga todos los recintos municipales ni que todos los municipios del bloque sean contiguos.

El conjunto de desarrollo se utilizará para comparar el baseline y las alternativas ML y elegir la preparación y configuración. Las particiones internas respetarán también la agrupación espacial. La prueba final se reservará para evaluar la solución elegida y no se utilizará para seleccionar variables, algoritmo o número de grupos. Ambos enfoques compartirán los mismos municipios de evaluación y las mismas condiciones de preparación, incluidas las cautelas de imputación del apartado 2.

El desarrollo se divide en **cuatro particiones internas de validación**, con 108, 108, 109 y 108 municipios, respectivamente. Este esquema constituye **validación cruzada espacial de cuatro particiones**: en cada ajuste se entrenará con las otras tres, 325 municipios o 324 cuando se reserven los 109, sin utilizar nunca la prueba final. Cada municipio de desarrollo aparece exactamente una vez en validación interna y no se comparte ningún bloque con su entrenamiento. Esta cantidad permite representar los cinco tramos en todas las validaciones, incluida una de las cuatro grandes ciudades de desarrollo en cada una; cinco particiones internas no lo permitirían.

Las asignaciones quedan identificadas por la ejecución `20261106T110046844319Z`, con código municipal, versión Gold, bloque, tramo, conjunto y partición interna. Se conservan en CSV y Parquet junto con un manifiesto de fuentes, huellas, parámetros y recuentos. Se utiliza una búsqueda determinista de 32 asignaciones a partir de la semilla 20261106, equilibrando desviaciones relativas cuadráticas de los conteos por tramo y del total en cinco lotes, uno final y cuatro internos. Cada lote recibe un bloque con una gran ciudad. La semilla elegida es 20261106; el diseño no consulta rentas, parque, oferta ni resultados de modelos. No se cambiará el reparto en función del rendimiento obtenido.

La preparación y el protocolo de métricas se han aplicado al baseline y a los tres candidatos ML; la comparación de desarrollo está completada y la prueba final sigue pendiente. El resultado final del producto podrá incluir los 541 municipios tras la evaluación; los reservados para prueba no se eliminan del ámbito final.

### Estratificación por población aplicada

Se adoptan cinco tramos de población de 2025 de Gold para equilibrar la representación por tamaño, conservando bloques espaciales completos. Sus límites no se solapan:

| Población | Total | Desarrollo | Prueba final |
| --- | ---: | ---: | ---: |
| Hasta 2.000 | 296 | 237 | 59 |
| Más de 2.000 y hasta 10.000 | 139 | 111 | 28 |
| Más de 10.000 y hasta 50.000 | 91 | 73 | 18 |
| Más de 50.000 y menos de 100.000 | 10 | 8 | 2 |
| Desde 100.000 | 5 | 4 | 1 |
| **Total** | **541** | **433** | **108** |

La estratificación controla la representación por tamaño, sin definir los clusters ni incorporar población a las entradas de esta primera segmentación. El resultado mantiene los cinco tramos en desarrollo, prueba y cada validación interna. Elche queda en prueba final; Alicante, València, Castelló de la Plana y Torrevieja, en las validaciones internas 1, 2, 3 y 4, respectivamente. Son asignaciones de diseño, no resultados sobre su demanda.

**Límite espacial:** los 20 km se adoptan como escala operativa inicial, sin haber estimado un alcance de autocorrelación que demuestre independencia. No se aplica una banda de separación entre conjuntos: municipios vecinos situados en celdas diferentes pueden aparecer en entrenamiento y evaluación. La integridad de los bloques evita mezclarlos, pero no acredita independencia espacial completa. Esta cautela deberá acompañar los resultados.

### Objetivos, métricas y resultados

Se acuerdan cuatro objetivos de evaluación:

- **Coherencia:** semejanza entre municipios del mismo perfil y diferencias reconocibles entre perfiles en las variables seleccionadas.
- **Estabilidad:** consistencia de la agrupación ante cambios en las muestras de desarrollo y, cuando proceda, inicializaciones, además de sensibilidad a las rentas estimadas.
- **Comportamiento fuera del ajuste:** asignación de municipios de zonas reservadas a perfiles aprendidos sin utilizar esos municipios para ajustarlos.
- **Interpretación y aportación frente al baseline:** perfiles explicables y una aportación útil respecto a las reglas por medianas, sin equiparar mejora estadística con mejores decisiones de instalación.

Se fija el siguiente protocolo inicial, sin etiquetas verdaderas de grupo o de necesidad de recarga:

| Objetivo | Evidencia |
| --- | --- |
| Coherencia | Silhouette euclídea sobre la representación común del apartado 2: media, resultado por grupo, fracción de valores negativos y valores municipales. |
| Estabilidad | ARI entre asignaciones de los mismos municipios de validación, alineadas por código, al perturbar el entrenamiento. |
| Comportamiento espacial | Silhouette, cobertura y grupos efectivos en cada una de las cuatro validaciones; resultados individuales, media no ponderada y rango. |
| Interpretación | Tamaño y porcentaje por perfil, mediana y cuartiles de las entradas en unidades originales y municipios de ejemplo. |

[Silhouette](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html) mide cohesión y separación, no acierto frente a necesidad real. Se calcula sobre validación asignada con el método ya ajustado, sin volver a entrenar con ella. Si hay menos de dos grupos observados o tantos como municipios, se registra como no calculable; no se inventa un cero. Se informa también de cobertura para que descartar casos no haga parecer mejor a un método. Baseline y ML compartirán municipios y representación de evaluación.

Para estabilidad se fijan **diez perturbaciones por validación**: se omite aleatoriamente, sin reemplazo y con semillas reproducibles, el 10% de los bloques de entrenamiento, redondeando hacia arriba, manteniendo al menos un donante de Sempere. Se vuelven a ajustar imputación, escalas y método con el subconjunto. El [ARI](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.adjusted_rand_score.html) compara sus asignaciones con las del ajuste principal sobre exactamente la misma validación intacta, sin exigir que coincidan los números de grupo. No se comparan directamente etiquetas de validaciones disjuntas. La condición de conservar donantes limita el tipo de perturbaciones estudiadas. En ML se revisará además la variación de sus inicializaciones cuando corresponda.

La sensibilidad de renta repetirá cada ajuste usando solo municipios con renta publicada, conservando sus roles espaciales. Se comparará mediante ARI con el ajuste principal filtrado a esos mismos municipios y se revisarán los perfiles de los siete estimados. Esto se realizará dentro de desarrollo; la prueba final seguirá reservada.

Se buscará mejora consistente frente al baseline, estabilidad y perfiles interpretables; si las opciones ofrecen resultados parecidos, se preferirá la más sencilla y con menos grupos. Se revisarán grupos pequeños o dominantes sin imponer tamaños iguales. No se fija un umbral universal de silhouette ni se suman los objetivos con pesos arbitrarios. Las cuatro validaciones se mostrarán por separado y no se tratarán como observaciones independientes para inventar intervalos de confianza. Una puntuación geométrica favorable no acredita mejores instalaciones.

La preparación, las funciones de métricas y las reglas del baseline han pasado quince comprobaciones sintéticas, incluidas alteraciones de validación que no cambian la preparación del entrenamiento, ausencia de donantes, separación de bloques, silhouette degenerada, ARI con códigos reordenados, empates y medianas pares. Las matrices guardadas se han contrastado mediante SQL con los parámetros exclusivos de entrenamiento.

### Primera ejecución del baseline

La ejecución `20261106T114636184831Z` aplica el protocolo fijado a desarrollo: cuatro ajustes principales, 40 perturbaciones, cuatro variantes de sensibilidad y un ajuste descriptivo completo, 49 ajustes en total. Cada uno de los 433 municipios aparece una vez en validación fuera de su entrenamiento. Se conservan las asignaciones, los umbrales y los resultados detallados con manifiesto de fuentes y huellas. **No se evalúa ningún municipio de prueba final.**

| Validación | Municipios | Grupos observados | Silhouette | ARI medio de estabilidad | ARI de sensibilidad de renta |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 108 | 8 | 0,086 | 0,932 | 0,964 |
| 2 | 108 | 8 | 0,030 | 0,902 | 1,000 |
| 3 | 109 | 8 | 0,087 | 0,937 | 0,988 |
| 4 | 108 | 7 | 0,048 | 0,894 | 0,893 |

La cobertura es **100% en las cuatro validaciones**. La silhouette media no ponderada es **0,0627**, con rango **0,0296–0,0871**. Un total de **166 de 433 municipios (38,3%)** obtiene silhouette negativa en su validación. Esto indica bastante solapamiento en la representación elegida y aconseja revisar la separación de los perfiles; no equivale a 166 errores frente a una clase verdadera. Los perfiles con proporción y renta superiores a las medianas (I-S-S y S-S-S, en el orden volumen/proporción/renta) tienen silhouette media negativa en las cuatro validaciones.

El **ARI medio de las 40 perturbaciones es 0,9164**, con mínimo **0,7269** y máximo **1**. Las asignaciones son generalmente estables ante las perturbaciones concretas estudiadas, con algunos ajustes sensiblemente menos coincidentes. Esa estabilidad no compensa por sí sola la baja separación geométrica ni prueba estabilidad ante cualquier cambio de datos.

Al excluir los siete municipios con renta estimada, el ARI sobre los mismos municipios de renta publicada presenta media **0,9613** y rango **0,8928–1** entre validaciones. **418 de los 426 municipios publicados conservan la combinación de categorías** y ocho cambian. Esta prueba mide la influencia conjunta de retirar esas filas y recalcular el ajuste; no valida los siete importes imputados ni aísla su error. Los seis estimados por IPC reciben I-S-S en su propia validación y Sempere I-I-S; sus asignaciones e importes quedan registrados individualmente.

#### Perfiles descriptivos en desarrollo

Un ajuste adicional sobre los **433 municipios de desarrollo** permite describir los perfiles con una única referencia: medianas de **19 vehículos con Distintivo 0**, **1,3129% del parque** y **13.395 EUR/persona/año**. Esta descripción es de entrenamiento, no otra evaluación fuera de muestra, y no incluye los 108 municipios reservados.

En la tabla, **I** significa inferior o igual a la mediana y **S** superior; el orden es volumen, proporción y renta. Los ejemplos son los municipios más próximos a la media de su grupo en la representación de distancias, no prioridades de inversión.

| Perfil | Municipios | Porcentaje | Ejemplo |
| --- | ---: | ---: | --- |
| I-I-I | 68 | 15,7% | L'Énova |
| I-I-S | 82 | 18,9% | La Yesa |
| I-S-I | 19 | 4,4% | Bicorp |
| I-S-S | 53 | 12,2% | Penàguila |
| S-I-I | 51 | 11,8% | Ondara |
| S-I-S | 16 | 3,7% | Xixona/Jijona |
| S-S-I | 79 | 18,2% | Orpesa/Oropesa del Mar |
| S-S-S | 65 | 15,0% | Gilet |

Se observan las ocho combinaciones, con tamaños entre 16 y 82. Los perfiles son fáciles de explicar, pero pueden reunir situaciones diversas: S-S-S incluye desde 20 hasta 10.246 vehículos con Distintivo 0. La coincidencia en categorías relativas no demuestra proximidad suficiente entre todos sus integrantes. Las asignaciones descriptivas no deben mezclarse con las de validación como si compartieran umbrales: cada validación usa los de su propio entrenamiento.

Los controles independientes han recalculado las medianas mediante SQL y verificado las 433 reglas de asignación, la silhouette municipal mediante distancias directas y los 40 ARI de estabilidad y cuatro de sensibilidad mediante tablas de contingencia. Las huellas coinciden y no hay municipios de prueba final entre las salidas.

### Resultados de la comparación ML en desarrollo — 07-11-2026

Se han completado las **27 combinaciones** y los **1.755 ajustes** previstos, sin modificar particiones, preparación o baseline según los resultados. Todos los métodos asignan el 100% de los municipios de validación. La ejecución es `20261107T114151583233Z`; los **108 de prueba final siguen sin evaluar**.

#### Comparación con ocho grupos configurados

Las métricas son medias de las cuatro validaciones; estabilidad resume las 40 perturbaciones y semillas los 16 ajustes adicionales. El baseline tiene hasta ocho combinaciones, sin inicialización aleatoria. El número observado puede ser menor en una validación que no reciba municipios de todos los grupos.

| Método | Silhouette | ARI estabilidad | ARI semillas | ARI renta | Grupos observados en las cuatro validaciones |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline | 0,063 | 0,916 | No procede | 0,961 | 8 / 8 / 8 / 7 |
| K-means | 0,210 | 0,746 | 0,790 | 0,727 | 8 / 8 / 8 / 7 |
| GMM | 0,168 | 0,562 | 0,638 | 0,626 | 7 / 6 / 8 / 6 |
| Bisecting K-means | 0,145 | 0,677 | 0,819 | 0,692 | 8 / 8 / 7 / 7 |

Los tres candidatos mejoran la separación media con k nominal 8, pero los tres presentan menor estabilidad frente a perturbaciones y mayor sensibilidad al retirar rentas estimadas que la referencia. Por tanto, esta comparación no demuestra una mejora conjunta de ML. Tampoco garantiza ocho grupos efectivos en cada validación.

#### Exploración del número de grupos

| k configurado | Silhouette K-means | Silhouette GMM | Silhouette Bisecting K-means |
| ---: | ---: | ---: | ---: |
| 2 | 0,311 | 0,415 | 0,309 |
| 3 | 0,327 | 0,266 | 0,305 |
| 4 | 0,279 | 0,250 | 0,277 |
| 5 | 0,215 | 0,229 | 0,201 |
| 6 | 0,189 | 0,204 | 0,172 |
| 7 | 0,235 | 0,167 | 0,143 |
| 8 | 0,210 | 0,168 | 0,145 |
| 9 | 0,206 | 0,143 | 0,149 |
| 10 | 0,194 | 0,085 | 0,144 |

La máxima silhouette media de cada método aparece con pocos grupos. La siguiente tabla muestra esos máximos geométricos; no constituye una selección automática del modelo final. Los tamaños pertenecen al ajuste descriptivo de entrenamiento sobre los 433 y no se agregan etiquetas de validaciones distintas.

| Método | k | Silhouette: media [mín.; máx.] | ARI estabilidad: media [mín.] | ARI semillas | ARI renta | Tamaños descriptivos |
| --- | ---: | --- | --- | ---: | ---: | --- |
| K-means | 3 | 0,327 [0,268; 0,370] | 0,890 [0,730] | 0,978 | 0,969 | 192 / 43 / 198 |
| GMM | 2 | 0,415 [0,319; 0,488] | 0,903 [0,598] | 0,972 | 0,968 | 61 / 372 |
| Bisecting K-means | 2 | 0,309 [0,251; 0,354] | 0,796 [0,016] | 0,914 | 0,855 | 215 / 218 |

**GMM con dos grupos** alcanza la mayor separación media de la búsqueda, 0,415, y ARI de estabilidad 0,903, cercano pero inferior al 0,916 del baseline. Su mínimo de estabilidad es 0,598 frente a 0,727 de la referencia. Produce un grupo de 372 municipios (85,9%) y otro de 61: esa concentración puede limitar la comparación entre municipios parecidos, aunque por sí sola no invalida la solución.

**K-means con tres grupos** alcanza silhouette 0,327, ARI de estabilidad 0,890 y ARI de semillas 0,978. Sus tamaños descriptivos son 192, 43 y 198. Ofrece una alternativa con mayor detalle, menor separación media que GMM de dos grupos y mayor mínimo de estabilidad, 0,730. No se elige únicamente por ese equilibrio numérico: falta cerrar su interpretación para el producto.

Bisecting K-means obtiene su máxima separación con dos grupos, pero su ARI mínimo de estabilidad cae a 0,016, igual que K-means con dos. Con tres grupos Bisecting presenta silhouette 0,305 y estabilidad media 0,848: aumentar grupos puede mejorar estabilidad aun reduciendo ligeramente la silhouette. Las configuraciones de k alto tampoco aportan una mejora clara; GMM con nueve grupos deja un único municipio en uno de sus perfiles descriptivos y con diez deja un grupo de dos.

#### Primera lectura de los dos candidatos más prometedores

Son medianas de entrenamiento, con identificadores arbitrarios sin orden de prioridad. La proporción Distintivo 0 se expresa en porcentaje y la renta en EUR/persona/año de 2023, incluidas las estimaciones documentadas.

| Método | Grupo | Municipios | Vehículos Distintivo 0 | Proporción Distintivo 0 | Renta |
| --- | ---: | ---: | ---: | ---: | ---: |
| GMM (k=2) | 0 | 61 | 20,0 | 3,14% | 15632,0 |
| GMM (k=2) | 1 | 372 | 18,5 | 1,21% | 13276,5 |
| K-means (k=3) | 0 | 192 | 78,5 | 1,50% | 12858,0 |
| K-means (k=3) | 1 | 43 | 162,0 | 3,30% | 15842,0 |
| K-means (k=3) | 2 | 198 | 4,0 | 0,84% | 13959,0 |

GMM distingue principalmente un perfil con mayor proporción de Distintivo 0 y renta mediana, pero volúmenes muy diversos: el grupo de 61 abarca de 1 a 10.246 vehículos. K-means separa además un grupo de bajo volumen, conservando también heterogeneidad. Estas descripciones no acreditan déficit de recarga ni que la renta cause adopción; deben servir para valorar qué comparación municipal resulta útil.

#### Piloto de utilidad: perfiles y oferta registrada — 09-11-2026

Se contrasta K-means con tres grupos con la oferta municipal Gold, únicamente sobre los **433 municipios de desarrollo**, sin ajustar modelos ni evaluar los 108 reservados. El propósito es comprobar si los perfiles permiten proponer comparaciones municipales que una persona responsable de planificación pueda revisar. Es una exploración descriptiva, sin evaluación de usuarios o resultados de instalaciones.

Para evitar seleccionar ejemplos por su oferta, se utilizan los nueve municipios representativos ya guardados y se buscan sus tres vecinos más próximos dentro del mismo grupo mediante distancia euclídea en las tres entradas preparadas del modelo. Para ilustrar cada grupo se elige la pareja más cercana de representante y primer vecino. Los puntos de recarga no intervienen en ese orden. Los 27 contrastes se conservan, incluidos casos con ofertas iguales o incertidumbre.

| Grupo | Municipio | Vehículos Distintivo 0 | Proporción del parque | Renta EUR/persona/año | Puntos con municipio admitido |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | l'Olleria | 104 | 1,38% | 12.575 | 5 |
| 0 | Turís | 89 | 1,38% | 12.507 | 10 |
| 1 | Beniparrell | 136 | 3,44% | 14.835 | 1 |
| 1 | Guadassuar | 182 | 3,65% | 14.140 | 0 |
| 2 | Llocnou de Sant Jeroni | 5 | 0,81% | 13.960 | 0 |
| 2 | Caudiel | 5 | 0,71% | 13.966 | 1 |

Las seis rentas son publicadas y los seis municipios no tienen avisos locales de asignación pendiente o ausencia entre exportaciones en Gold. Esto no acredita exhaustividad del inventario. Los periodos son parque de 31-12-2025, renta de 2023 y copia de recarga adquirida el 18-10-2026.

l'Olleria y Turís presentan entradas muy próximas, con presiones descriptivas de 20,8 y 8,9 vehículos Distintivo 0 por punto admitido. La diferencia propone revisar las condiciones locales; no determina cuántos cargadores faltan. Llocnou y Caudiel muestran que el mismo número reducido de vehículos registrados puede coexistir con ofertas diferentes, sin justificar prioridad automática por el cero. Olocau y Gilet, otra pareja de representantes y primer vecino, tienen cuatro puntos cada uno: el procedimiento también devuelve comparaciones sin contraste de recuento.

| Grupo | Municipios | Sin puntos admitidos | Porcentaje | De esos ceros, con avisos locales |
| --- | ---: | ---: | ---: | ---: |
| 0 | 192 | 49 | 25,5% | 3 |
| 1 | 43 | 17 | 39,5% | 2 |
| 2 | 198 | 168 | 84,8% | 3 |

Cero significa ningún punto con asignación municipal admitida en la copia, no ausencia física de recarga. Se conservan todos los municipios y los avisos; los cocientes con denominador cero permanecen nulos. Los recuentos municipales se han reconciliado con las instalaciones Gold y los avisos con sus relaciones de detalle, sin multiplicar puntos por conectores.

El piloto respalda el uso de **perfil + valores municipales + oferta** para organizar la exploración y proponer casos de revisión. La pertenencia al grupo por sí sola es demasiado amplia para fijar una oferta esperada: el grupo 0 abarca entre 8 y 6.083 vehículos Distintivo 0 y el grupo 1 entre 2 y 10.246. Falta comprobar la ventaja práctica frente a una comparación sencilla y con usuarios. No se han evaluado potencia, funcionamiento, ocupación, recarga privada o accesibilidad a oferta de otros municipios; no se obtiene un ranking ni una prueba de déficit.

#### Comprobaciones y límites

Las quince pruebas sintéticas de preparación, baseline y candidatos pasan. Se han verificado las huellas, los códigos y las coberturas; se han recalculado independientemente las 108 silhouettes por distancias directas y los 1.620 ARI de las variantes por contingencias, además de comprobar escalas y donantes de las 49 preparaciones. Los errores numéricos máximos son inferiores a 5×10⁻¹⁴ y 2×10⁻¹⁶, respectivamente. Las asignaciones principales coinciden con los modelos guardados; en K-means y GMM se han contrastado además con sus centros y densidades, respectivamente. No se han registrado avisos, ajustes GMM sin convergencia o ajustes que alcancen el límite de 500 iteraciones donde este se informa; Bisecting no expone un contador global equivalente.

Se mantienen las limitaciones de bloques de 20 km sin banda de separación, rentas estimadas y silhouette favorable a grupos compactos y convexos. Los cuatro resultados y las perturbaciones no se tratan como muestras independientes para construir intervalos de confianza. La búsqueda informa la selección en desarrollo; no sustituye la prueba final ni demuestra utilidad de instalación.

## 5. Decisión y uso en el producto

Se da por **cerrado el diseño, la ejecución y la evaluación inicial del baseline en desarrollo**, conservando la versión `20261106T114636184831Z` como referencia fija para comparar ML. Se han comprobado reglas, cobertura, comportamiento espacial, estabilidad, sensibilidad y perfiles, con una preparación reproducible que respeta entrenamiento y validación. No se necesita optimizar esta referencia sencilla para elevar su puntuación antes de probar ML.

La interpretación es que las reglas producen categorías explicables y generalmente estables, mientras su capacidad para reunir municipios próximos en las tres dimensiones es limitada. Ambas observaciones son compatibles: cortes parecidos pueden reproducir de forma estable perfiles muy amplios. La baja silhouette indica solapamiento en la representación elegida; no demuestra por sí sola que los datos sean inadecuados o que no exista una estructura aprovechable. Las rentas estimadas muestran una influencia limitada sobre la mayoría de las categorías publicadas en la prueba realizada, sin validar los importes.

La comparación ML utiliza las mismas entradas, preparación, particiones y criterios. Con ocho grupos configurados mejora la separación media y empeora la estabilidad respecto al baseline. K-means con tres grupos se adopta como opción de trabajo por el detalle de sus perfiles, conservando GMM, Bisecting y baseline. GMM con dos grupos mantiene mejores medias de separación y estabilidad entre los candidatos ML; ninguna configuración probada supera la estabilidad media del baseline. El piloto de oferta aporta ejemplos de comparación para revisar y confirma la heterogeneidad interna, sin demostrar todavía mejora de las decisiones frente a una alternativa sencilla. Se mantiene pendiente la selección definitiva razonada antes de evaluar los 108 reservados. No se deriva un ranking ni una necesidad de nuevas instalaciones de estos perfiles.
