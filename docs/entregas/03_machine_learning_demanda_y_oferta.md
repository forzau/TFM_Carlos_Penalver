# Entrega 03 - Machine Learning: perfiles de demanda y oferta de recarga

**Proyecto:** localización de nuevos puntos de recarga para vehículos eléctricos en la Comunitat Valenciana.

**Fecha:** 13-11-2026. **Solución seleccionada para continuar:** K-means con seis grupos, como base provisional de un MVP descriptivo. La ejecución y la evaluación interna están completadas; la comprensión y utilidad de los perfiles en el producto todavía deben comprobarse.

## 1. Qué problema resuelve el modelo

### Usuario y decisión que se quiere mejorar

El usuario principal es una persona responsable de planificar infraestructura pública de recarga en una administración. Dispone de recursos limitados y necesita decidir **qué municipios de la Comunitat Valenciana estudiar primero para valorar una ampliación de la oferta**.

Consultar por separado el parque de vehículos y los puntos de recarga exige comparar muchas situaciones individuales. El producto busca organizar esa información en perfiles comprensibles que ayuden a reconocer situaciones territoriales y a justificar la selección de municipios para estudios posteriores.

### Funcionalidad y tipo de problema

La funcionalidad propuesta es una **segmentación municipal mediante aprendizaje no supervisado (clustering)**. El modelo responde a la pregunta:

**¿Qué municipios presentan combinaciones similares de demanda potencial y oferta registrada de recarga pública?**

Se utiliza el Gold de la [Entrega 02](02_datos_y_preparacion.md), con una observación por municipio incluido. La demanda potencial y la oferta intervienen conjuntamente en la formación de los grupos mediante las dos variables especificadas en el apartado 2.

No se dispone de una etiqueta observada que indique la necesidad real de cargadores de cada municipio. Por ello, se buscan perfiles de similitud sin asignar previamente categorías de necesidad o urgencia. La elección del algoritmo y del número de grupos se justifica en los apartados 3 y 5.

### Interpretación y etiquetado de los perfiles

Los grupos se interpretan mediante sus características habituales, dispersión, diferencias y municipios representativos. A partir de esa lectura se proponen **nombres descriptivos** que faciliten su comprensión; las etiquetas de la solución seleccionada se presentan en el apartado 5.

Los nombres se elaboran después del agrupamiento y resumen las características observadas en relación con el conjunto analizado. No son clases utilizadas para entrenar el modelo ni combinaciones de pocos/muchos vehículos y pocos/muchos puntos impuestas de antemano. La descripción conserva la diversidad interna: pertenecer al mismo grupo no implica que todos sus municipios tengan la misma situación.

### Aportación al producto y alcance

El producto permitirá consultar el perfil de un municipio, entender qué lo caracteriza y explorar otros municipios con combinaciones similares de demanda y oferta. La hipótesis es que esta organización facilite reconocer casos que merezcan revisión y explicar por qué se seleccionan para estudiar una posible ampliación. La comparación con una referencia sencilla permite valorar qué diferencias adicionales describe la segmentación; la utilidad efectiva para el usuario queda sujeta a la comprobación del MVP.

La salida será la pertenencia a un grupo acompañada de su descripción y de los valores e incertidumbres necesarios para interpretarla. Los identificadores de grupo no expresarán un orden de prioridad.

El resultado apoyará la **priorización de estudios**, sin determinar automáticamente la urgencia de actuación, la suficiencia de la oferta o cuántos puntos deben instalarse. Los datos aproximan demanda potencial y describen oferta registrada; comprobar una necesidad efectiva y la viabilidad de una instalación requerirá evidencia y estudios adicionales. Esta primera versión analiza la situación descrita por las copias disponibles, sin predecir necesidades futuras.

## 2. Datos de entrada y salida

### Unidad de análisis y variables

Se reutiliza `gold_municipios` de la Entrega 02, versión `20261020T153200478279Z`, sin repetir la adquisición ni modificar Gold. El análisis incluye **541 municipios** de los 542 presentes en esa capa. Se mantiene la exclusión documentada de Puebla de San Miguel (46201), recogida en `config/exclusiones_segmentacion.json`, por la representatividad de su parque domiciliado como aproximación de demanda local.

El agrupamiento utiliza exclusivamente dos entradas:

| Entrada | Campo Gold | Significado y límite |
| --- | --- | --- |
| Vehículos con Distintivo 0 | `vehiculos_distintivo_0` | Aproximación de demanda potencial registrada. No mide usuarios dependientes de recarga pública, sesiones o energía demandada. |
| Puntos de recarga con municipio admitido | `puntos_con_municipio_admitido` | Puntos de la copia principal cuya instalación tiene una relación municipal admitida. No equivale a instalaciones, conectores, potencia disponible o funcionamiento acreditado. |

El parque corresponde al 31-12-2025 y la copia de recarga fue adquirida el 18-10-2026. La segmentación describe esta combinación de fuentes y fechas; no estima necesidades futuras ni representa una observación simultánea de ambas variables.

La renta, la proporción de Distintivo 0, la población, el parque total y otras variables Gold quedan para interpretar los perfiles en el producto. No intervienen en su formación ni se incorporan ratios o normalizaciones adicionales. La ausencia de renta no exige imputación ni excluye municipios. La información de candidatos y distancias se conserva en su nivel original; no se presenta como accesibilidad municipal sin una definición específica.

### Preparación y controles de calidad

Las dos entradas están informadas en los 541 municipios y son recuentos enteros no negativos. La carga rechaza ausencias, duplicados o valores inválidos; no los transforma en ceros ni los imputa.

Para los modelos y las métricas de distancia se aplica **logaritmo natural de uno más el recuento (`log1p`) y después StandardScaler** en ambas columnas. El logaritmo conserva los ceros y comprime diferencias de magnitud; la estandarización sitúa las variables en escalas comparables. Las medias y desviaciones poblacionales se calculan sobre los municipios utilizados en cada ajuste, con divisor 1 si una columna es constante. Esta preparación se fija antes de evaluar y es común al baseline y a las alternativas ML. Las reglas del baseline se aplican a los recuentos originales.

La transformación no cambia las cantidades reales. En las figuras, el panel original permite leerlas y el transformado muestra la representación utilizada por el modelo. Las coordenadas estandarizadas no son cantidades de vehículos o puntos ni permiten interpretar su cociente como proporción de cobertura.

Se conservan los avisos de calidad: **63 municipios** están relacionados con asignaciones pendientes o ausencias entre copias. Hay **284 municipios sin puntos admitidos**, de los que 12 tienen avisos. Un cero significa ausencia de puntos admitidos en esta versión, no ausencia física certificada. Los recuentos de oferta y los avisos se reconcilian con las tablas Gold de detalle, sin adjudicar registros inciertos. Su efecto se estudia retirando esos 63 municipios y comparando los 478 restantes.

### Salida y disponibilidad en el uso

La salida es la pertenencia a un grupo, acompañada de una descripción, los valores del municipio y sus avisos. No existe una variable objetivo de necesidad real. Para consultar esta fotografía, el producto puede utilizar las asignaciones ya calculadas, identificadas por municipio y versión.

El resto de Gold aporta contexto sin modificar el grupo. Una actualización de datos deberá mantener definiciones y procedencia compatibles y revisar la segmentación; no se presupone que las categorías sean válidas para cualquier fecha o fuente. Los principales riesgos son confundir parque domiciliado con uso local, recuento registrado con capacidad operativa y características del perfil con necesidades de todos sus miembros.

## 3. Baseline y selección de modelos

### Referencia sencilla

El baseline combina dos reglas: **vehículos inferiores o iguales a la mediana frente a superiores**, y **cero puntos frente a algún punto admitido**. La mediana de vehículos del universo incluido es 20; los empates permanecen en la primera categoría. La regla de oferta distingue presencia registrada, sin llamar «oferta alta» a cualquier valor positivo.

| Perfil | Vehículos Distintivo 0 | Puntos admitidos | Municipios | Con avisos |
| --- | --- | --- | ---: | ---: |
| I-0 | Menor o igual a 20 | 0 | 219 | 6 |
| I-P | Menor o igual a 20 | Al menos 1 | 54 | 8 |
| S-0 | Mayor que 20 | 0 | 65 | 6 |
| S-P | Mayor que 20 | Al menos 1 | 203 | 43 |

Es una referencia reproducible y explicable, sin umbral sectorial de necesidad. Su limitación es que no distingue cantidades positivas de puntos: S-P reúne municipios con entre 21 y 10.246 vehículos y entre 1 y 655 puntos. Esta diversidad permite valorar si ML aporta una descripción más informativa.

El baseline asigna los 541 municipios, con silhouette interna 0,3816 y 85 valores individuales negativos. En las diez perturbaciones espaciales obtiene un ARI medio de 0,9576, con mínimo 0,8920 y máximo 0,9825. Al retirar los municipios con avisos quedan 478; la mediana baja a 16,5 y el ARI es 0,9043. Veinte municipios cambian de etiqueta literal. El procedimiento se explica en el apartado 4.

### Alternativas y configuración

Se comparan [K-means](https://scikit-learn.org/stable/modules/clustering.html#k-means), que agrupa alrededor de centros mediante distancias, y [Gaussian Mixture Model](https://scikit-learn.org/stable/modules/mixture.html) (GMM), que permite componentes de formas y dispersiones diferentes mediante covarianzas completas. Ambos utilizan los mismos municipios, entradas, preparación y controles de calidad.

Se exploran **de dos a seis grupos por método**, diez configuraciones en total, incluyendo cuatro como contraste con el baseline. El rango limita el experimento y facilita la interpretación; no demuestra que el óptimo esté dentro de él. Las configuraciones se fijan antes de ajustar:

| Elemento | Configuración |
| --- | --- |
| K-means | `k-means++`, 20 inicializaciones, máximo 500 iteraciones, tolerancia 0,0001 y algoritmo Lloyd. |
| GMM | Covarianza completa, inicialización K-means, 10 inicializaciones, máximo 500 iteraciones, tolerancia 0,001 y `reg_covar=0.000001`. |
| Semillas | Principal 20261111; adicionales 20261211, 20261311, 20261411 y 20261511. Son identificadores aleatorios, no fechas. |
| Reajustes por configuración | Principal, diez omisiones espaciales, cuatro semillas adicionales y una variante sin avisos: 16 ajustes, 160 en total. |

Cada semilla adicional conserva el mismo número de inicializaciones del método; es un reajuste completo. En GMM se revisan convergencia, componentes estrechos y grupos observados. La regularización no se modifica después de ver las métricas.

### Resultados comparables

Las diez configuraciones principales asignan los 541 municipios. Todas las métricas de la tabla son internas o de robustez; no resultados fuera del ajuste.

| Método | k | Silhouette interna | ARI bloques: media | ARI bloques: mínimo | ARI semillas: mínimo | ARI sin avisos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 4 | 0,3816 | 0,9576 | 0,8920 | No aplica | 0,9043 |
| K-means | 2 | 0,5686 | 0,9254 | 0,8613 | 1,0000 | 0,8510 |
| K-means | 3 | 0,4667 | 0,9853 | 0,9625 | 1,0000 | 0,8869 |
| K-means | 4 | 0,4452 | 0,9536 | 0,8488 | 1,0000 | 0,8363 |
| K-means | 5 | 0,4580 | 0,9639 | 0,7142 | 1,0000 | 0,7860 |
| K-means | 6 | 0,4786 | 0,9550 | 0,8784 | 0,9611 | 0,8627 |
| GMM | 2 | 0,4644 | 1,0000 | 1,0000 | 1,0000 | 1,0000 |
| GMM | 3 | 0,4175 | 0,9894 | 0,9783 | 1,0000 | 0,9749 |
| GMM | 4 | 0,3912 | 0,9034 | 0,6940 | 0,8911 | 0,9259 |
| GMM | 5 | 0,2796 | 0,9529 | 0,8862 | 1,0000 | 0,9878 |
| GMM | 6 | 0,3958 | 0,5715 | 0,4669 | 0,5253 | 0,4755 |

K-means con dos grupos logra la mayor silhouette, pero resume la distribución en dos conjuntos amplios. Tres grupos ofrecen niveles generales bajo, intermedio y alto, todavía con heterogeneidad importante. Con cuatro se distinguen mejor situaciones de poca oferta según el parque; cinco diferencia el extremo alto y seis añade un contraste de parque entre municipios con pocos puntos.

GMM con dos componentes separa exactamente los 284 municipios sin puntos de los 257 con puntos: su estabilidad perfecta reproduce sobre todo esa estructura. Con cinco componentes mantiene juntos todos los ceros, aunque sus parques van de 0 a 377 vehículos, y concentra 28 municipios con exactamente un punto en otro grupo. GMM utiliza ambas entradas; estas franjas no demuestran que ignore los vehículos. La agrupación observada resulta menos adecuada para la lectura conjunta buscada.

Los 160 ajustes terminan sin avisos de ejecución y los 80 GMM declaran convergencia. No obstante, GMM con seis componentes produce solo cinco grupos de asignación máxima en tres réplicas: omisiones 3 y 4 y semilla adicional 3. En los GMM principales una dirección de covarianza alcanza el suelo de regularización de 10⁻⁶. Convergencia y utilidad se evalúan por separado.

La decisión de continuar con K-means y seis grupos combina detalle interpretativo y resultados cuantitativos, sin construir una puntuación ponderada ni declarar un ganador uniforme. Frente a cinco, seis mejora silhouette, sensibilidad sin avisos y el mínimo ARI espacial; cinco conserva mayor ARI espacial medio y estabilidad entre semillas. La elección y su aplicación se concretan en el apartado 5.

### Evidencias y representación visual

Se conservan protocolos, entradas, asignaciones, resúmenes, modelos y manifiestos de procedencia en:

- Baseline: `resultados/modelado/baseline_descriptivo/20261111T160303732930Z/`.
- Comparación ML: `resultados/modelado/comparacion_descriptiva/20261111T161605225327Z/`.
- Diez PNG con centros: `imagenes_clusters/20261111T170051625718Z/`, dentro de la comparación.

Los productores son `src/ejecutar_baseline_descriptivo.py` y `src/ejecutar_comparacion_descriptiva.py`. Sus verificadores independientes conservan las comprobaciones numéricas. `src/exportar_clusters_descriptivos.py` genera las imágenes desde asignaciones y modelos guardados; `src/ejecutar_comparacion_con_imagenes.py` enlaza una nueva comparación con su exportación. Las ejecuciones anteriores se mantienen como antecedentes, sin mezclar sus métricas con las de este diseño.

Cada imagen muestra recuentos originales y representación transformada, con límites comunes entre configuraciones. Los centros se marcan con X: centroides guardados de K-means y medias de componentes en GMM. Su transformación inversa a recuentos no es una media aritmética ni tiene que corresponder a un municipio real. Los 541 municipios ocupan 294 posiciones distintas; se conservan ceros y superposiciones, sin desplazar puntos. Los colores y números son locales a cada configuración y no indican prioridad.

## 4. Validación y evaluación

### Diseño descriptivo sin separación

Se ajusta y describe el **universo actual de 541 municipios, sin reserva de entrenamiento, validación o prueba ni validación cruzada**. La decisión se apoya en el objetivo de organizar esa fotografía, no en predecir etiquetas de necesidad o estimar asignaciones a municipios desconocidos. Se acoge a la aclaración docente que permite prescindir de separación si se justifica según el problema.

Las escalas y los grupos se ajustan con el conjunto descrito. Por tanto, la silhouette es una medida interna, no una estimación fuera de entrenamiento. Comparar varios métodos y valores de k sobre el mismo conjunto puede favorecer las métricas observadas; se acompaña de robustez, sensibilidad e interpretación, sin afirmar generalización. Trasladar el resultado a otra fecha o fuente requiere una evaluación específica.

Se evita mezclar universos o preparaciones entre candidatos. Las únicas entradas son las dos variables declaradas; las etiquetas se redactan después y no intervienen en el ajuste. Los controles de calidad y la exclusión territorial se mantienen para todos los métodos. Esto asegura comparabilidad interna, pero no convierte la evaluación en una prueba independiente.

### Métricas y ensayos

La **silhouette euclídea** mide cohesión y separación en la representación transformada. Un valor individual negativo señala menor proximidad media a su propio grupo que a algún otro, no un error frente a una necesidad real. Se informa junto con tamaños y perfiles, sin utilizarla como criterio único.

El **Adjusted Rand Index (ARI)** compara particiones de los mismos municipios y permite que cambie la numeración de los grupos. Valores próximos a uno indican mayor semejanza; no son porcentajes de municipios bien clasificados ni pruebas de que los perfiles sean correctos.

Los controles aplicados son:

1. **Perturbación espacial.** Diez omisiones distintas de ocho bloques entre los 73 disponibles, correspondientes al 10% redondeado hacia arriba. Se recalculan preparación y modelo con los municipios restantes y se reasignan los 541. Se reutilizan los mismos planes y semilla del baseline. Los bloques de 20 km son una unidad operativa de perturbación, no una garantía de independencia espacial. El ARI incluye municipios usados en el ajuste: mide robustez con solapamiento, no validación cruzada.
2. **Inicialización.** Cuatro reajustes adicionales por configuración sobre los 541 municipios, con semillas distintas y el mismo `n_init`. Se comparan con la asignación principal mediante ARI.
3. **Sensibilidad de calidad.** Se retiran los 63 municipios con avisos, se recalculan preparación y modelo sobre los 478 restantes y se comparan solo esos códigos comunes. El resultado mide el efecto de retirar filas y reajustar; no corrige registros pendientes ni acredita que los restantes sean completos.

El baseline completa 12 ajustes y la comparación ML 160. Los diez ensayos espaciales son dependientes y no se convierten en intervalos de confianza.

### Casos fronterizos y limitaciones relevantes

K-means con seis grupos obtiene silhouette 0,4786, ARI espacial medio 0,9550 y mínimo 0,8784, ARI mínimo entre semillas 0,9611 y ARI sin avisos 0,8627. Sus grupos contienen entre 27 y 162 municipios. Presenta tres silhouettes individuales negativas:

| Municipio | Código | Grupo | Vehículos | Puntos | Silhouette |
| --- | --- | --- | ---: | ---: | ---: |
| Ondara | 03095 | G3 | 85 | 55 | −0,0014 |
| Agullent | 46004 | G2 | 41 | 1 | −0,0142 |
| Ayora | 46044 | G2 | 40 | 1 | −0,0321 |

Son casos para revisar la representatividad de las etiquetas y las fronteras; no se conocen clases verdaderas que permitan declararlos errores de necesidad. Ondara ilustra además que un miembro del perfil de gran concentración puede tener bastante menos parque que la mediana de su grupo: su oferta también interviene en la asignación.

La nube presenta una tendencia creciente y concentración de ceros, sin islas inequívocas para cada k. Los grupos resumen en buena parte volumen conjunto de parque y oferta. Aumentar k modifica fronteras y algunas asignaciones; no es una división jerárquica exacta. Una misma etiqueta no implica que todos sus municipios tengan cantidades o proporciones similares.

El parque domiciliado puede diferir del uso efectivo local. El recuento de puntos no recoge por sí solo potencia, funcionamiento, disponibilidad o demanda de visitantes y vehículos de paso. Las diferencias de puntos entre grupos formados utilizando puntos describen el resultado, pero no validan de forma independiente su utilidad.

### Verificación técnica y alcance de la evidencia

Las verificaciones existentes incluyen 15 pruebas de modelos, baseline y preparación, y cinco de gráficos. El baseline se contrasta mediante mediana por SQL, 541 silhouettes por distancias directas, once ARI por contingencias y doce preparaciones. Para ML se reproducen las predicciones de los diez modelos principales mediante centros o densidades gaussianas, se contrastan doce preparaciones y se recalculan 10.190 silhouettes y 160 ARI. Las réplicas se comprueban a partir de asignaciones guardadas, sin repetir ajustes.

Los errores máximos de la comprobación ML son 3,04×10⁻⁹ en silhouette, 1,12×10⁻¹⁶ en ARI y cero en parámetros de preparación. Las diferencias de silhouette están dentro de la tolerancia 10⁻⁸ utilizada por redondeo en filas coincidentes. Se contrastan también los 40 centros de las imágenes y su transformación inversa. Entorno documentado: Python 3.12.14, NumPy 2.5.4, scikit-learn 1.9.1, joblib 1.6.0 y Matplotlib 3.11.2 para las figuras.

Se conservan los centros exactos del estimador. En K-means k2 difieren hasta 0,0161424 unidades estandarizadas de las medias de sus etiquetas finales, compatible con parada antes de convergencia estricta; en k3..k6 las diferencias son de redondeo. No se modifican ajustes para alterar su representación gráfica.

Estas comprobaciones respaldan la integridad de los cálculos y salidas. No son una prueba de usabilidad, suficiencia de recarga o rendimiento fuera de esta fotografía.

## 5. Decisión y uso en el producto

### Solución seleccionada y mejora obtenida

Se selecciona **K-means con seis grupos para continuar el proyecto**. Su adopción es provisional hasta comprobar que los perfiles sean comprensibles y útiles en el MVP. Se reutiliza `modelos/kmeans_k6.joblib` de la comparación `20261111T161605225327Z`, junto con su preparación y Gold de referencia; no se requiere un nuevo ajuste por esta decisión.

El baseline ofrece cuatro combinaciones simples de parque y presencia de puntos. La solución elegida distingue cantidades positivas de oferta y situaciones con oferta parecida pero parques diferentes. El contraste más claro es el perfil de parque reducido con recarga registrada, con 53 municipios y medianas de 9 vehículos y 2 puntos, frente al de parque intermedio y pocos puntos, con 86 municipios y medianas de 74,5 vehículos y 2 puntos.

Frente al baseline, la silhouette sube de 0,3816 a 0,4786 y los valores negativos bajan de 85 a 3. La mejora no es uniforme: el ARI espacial medio pasa de 0,9576 a 0,9550 y el de sensibilidad sin avisos, de 0,9043 a 0,8627. Se acepta este compromiso como hipótesis de trabajo por el detalle descriptivo adicional. K-means con cinco grupos se conserva como alternativa más simple, y el baseline y GMM como referencias de comparación.

### Etiquetas de los seis perfiles

Se proponen los siguientes nombres para mostrar al usuario. Son **etiquetas descriptivas de trabajo**, revisables al comprobar su comprensión. «Parque» significa vehículos con Distintivo 0 y «oferta» significa puntos admitidos; los niveles son relativos al conjunto analizado.

| Grupo interno | Etiqueta | Municipios | Mediana vehículos | Mediana puntos |
| --- | --- | ---: | ---: | ---: |
| G0 | Parque elevado y muchos puntos | 87 | 287 | 13 |
| G1 | Parque muy reducido y oferta mínima | 162 | 3 | 0 |
| G2 | Parque intermedio y pocos puntos | 86 | 74,5 | 2 |
| G3 | Gran concentración de parque y recarga | 27 | 790 | 51 |
| G4 | Parque reducido con oferta registrada | 53 | 9 | 2 |
| G5 | Parque reducido y oferta mínima | 126 | 20 | 0 |

Las medianas describen perfiles típicos; no son centroides ni límites de pertenencia. «Oferta mínima» incluye algunos municipios con puntos positivos. Los identificadores y colores no expresan prioridad, y el nombre del perfil debe acompañarse de los valores propios del municipio.

### Resultado que consumirá el frontal

La salida prevista es **una categoría descriptiva por municipio**, con estos componentes:

| Información | Significado y uso |
| --- | --- |
| Código y nombre del municipio | Identificar la observación y vincularla con Gold. |
| Grupo, etiqueta y descripción | Explicar el perfil y explorar municipios similares. |
| Vehículos con Distintivo 0 y puntos admitidos | Mostrar las cantidades del municipio en unidades originales. |
| Avisos de calidad | Hacer visibles asignaciones pendientes, ausencias entre copias e incertidumbre sin localizar. |
| Versiones de Gold, modelo y etiquetas | Identificar la fotografía analizada y conservar trazabilidad. |

Para esta fotografía bastan las asignaciones de `kmeans_k6` ya guardadas en `asignaciones_municipales.csv`; consultar un municipio no exige reajustar el modelo. El resto de Gold podrá aportar contexto sin intervenir en la asignación. Este contrato de presentación está definido, pero el frontal y la integración de las etiquetas todavía no están implementados.

Como ejemplo, Caudete de las Fuentes (46095), con 7 vehículos y 3 puntos, pertenece a G4; el Fondó de les Neus/Hondón de las Nieves (03077), con 77 vehículos y 2 puntos, pertenece a G2. Son asignaciones observadas que ilustran perfiles distintos, no diagnósticos de exceso o carencia.

### Suficiencia para el MVP y condiciones de continuidad

La solución constituye una **base técnicamente ejecutable para un MVP de consulta y comparación de perfiles**: hay asignaciones verificadas para los 541 municipios, un modelo guardado y explicaciones iniciales. La evidencia permite continuar con ese prototipo; todavía no demuestra que seis categorías sean suficientes o adecuadas para el uso real del producto. No se han realizado pruebas de usabilidad.

La aceptación se condiciona a revisar casos de los seis perfiles, incluidos extremos y municipios con avisos, y comprobar que una persona pueda interpretar su municipio, diferenciar G2 de G4 y entender sus cantidades y cautelas. Se contrastará esa lectura con el baseline y con cinco grupos. Si el detalle adicional no aporta claridad o deja una heterogeneidad que dificulta el uso previsto, se revisarán las etiquetas o el número de grupos.

El resultado apoya la selección de municipios para estudios posteriores. **No calcula cargadores necesarios, prioridad automática de instalación ni suficiencia o viabilidad de conexión.** Comprobar una carencia requiere evidencia adicional de demanda, capacidad y servicio; un grupo o una proporción de vehículos por punto no aporta por sí solo ese umbral. La conclusión de esta entrega es continuar con seis perfiles descriptivos y mantener su aceptación final sujeta a la comprobación de utilidad del MVP.
