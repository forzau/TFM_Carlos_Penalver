# Plan de trabajo de Silver

Fecha: **19 de octubre de 2026**. Estado: **fases 1–3 cerradas; base territorial,
parque DGT, población y renta preparados; fase 4 tabular preparada y capa de
recarga materializada con incidencias; fases 5–6 preparadas con limitaciones; fase 7 tabular
preparada y capa complementaria con 423 relaciones municipales admitidas; fase 8 cerrada operativamente
con relaciones verificadas y limitaciones explícitas**. Hay 52 asignaciones
municipales de recarga pendientes, tras resolver 81 de las 133 discrepancias.
Este documento concreta el orden de preparación a
partir del [catálogo Bronze](CATALOGO_BRONZE.md), la
[auditoría](AUDITORIA_FUENTES.md) y las
[referencias territoriales](REFERENCIAS_TERRITORIALES.md).

Silver producirá tablas y capas consistentes por fuente, con claves, tipos,
unidades, periodos y relaciones documentados. La referencia municipal compartida
será el conjunto de 542 códigos contrastados. Esto no impone el municipio como
unidad final de recomendación: los puntos, conectores, tramos y polígonos
conservarán su unidad original.

## Fases y condiciones de cierre

| Fase | Trabajo | Salida prevista | Comprobación para cerrarla |
| --- | --- | --- | --- |
| **1. Reglas comunes y diseño de salidas** | Definir tablas, significado de cada fila, claves, campos necesarios, tipos, unidades, tratamiento de ausencias y criterios temporales. Confirmar interpretación de CRS y ejes y justificar un CRS para las operaciones métricas que se necesiten. Concretar lectores y formatos con Python y DuckDB como base. | Especificaciones de salidas y reglas de transformación, con decisiones justificadas y límites conocidos. | Cada salida tiene unidad de observación y claves definidas. Las operaciones espaciales admitidas tienen referencia acreditada; las dudas de otras fuentes se registran sin bloquear el conjunto. Los periodos desconocidos siguen señalados. No se añaden herramientas sin necesidad demostrada. |
| **2. Base territorial** | Preparar la relación INE y los recintos municipales del IGN; separar niveles administrativos, comprobar geometrías y conservar referencias de edición/consulta. | Referencia municipal de códigos y nombres, capa de recintos y registro de incidencias geométricas. | 542 códigos municipales únicos; cada municipio tiene geometría informada o incidencia explícita. Las reparaciones, si hacen falta, se justifican y comparan con el original. La coincidencia de códigos no se interpreta como prueba de límites históricos idénticos. |
| **3. Parque, población y renta** | Estructurar DGT municipal y detalle observado del TXT; normalizar población por sexo/año y renta por indicador/año/nivel. Separar códigos históricos y registros sin municipio. | Tablas de parque municipal, detalle DGT disponible, población y renta, manteniendo categorías y niveles. | Cobertura reconciliada con la referencia; claves comprobadas según cada tabla; cifras de control reconciliadas con Bronze. Ningún ausente se convierte en cero ni se mezclan niveles territoriales o categorías de total y desglose. |
| **4. Recarga existente: MITECO** | Resolver codificación y comillas, convertir coordenadas, fechas y potencia, distinguir instalación/punto/conector e investigar las seis repeticiones de clave observadas. | Entidades y relaciones de recarga, con unidades explícitas, estados de calidad e incidencias. | Lectura sin pérdidas no explicadas; integridad entre los tres niveles; repeticiones resueltas o apartadas con motivo. Coordenadas y potencias válidas o señaladas. Se documenta qué representa cada recuento y qué capacidad permite interpretar la fuente. |
| **5. Tráfico y red viaria** | Normalizar aforos por tramo/año y tipo de medida. Separar geometrías de tramos IGN y sus asociaciones con viales; comprobar coherencia entre provincias y referencias espaciales. | Aforos estructurados, tramos viarios y relaciones de origen conservadas. | Claves y unidades verificadas; distinción entre medida y estimación cuando se pueda acreditar. Las relaciones múltiples no multiplican inadvertidamente longitudes o recuentos. Se documentan cobertura y variaciones anuales de tramos. |
| **6. Puntos de interés: OSM** | Definir categorías útiles, revisar objetos fuera del ámbito y estudiar correspondencias entre puntos y polígonos. Conservar identificadores y capa de procedencia. | POI y geometrías de origen, clasificación de uso y relaciones o posibles coincidencias documentadas. | Cada inclusión o exclusión tiene una regla; se inspeccionan los objetos alejados antes de descartarlos. Una coincidencia espacial no acredita por sí sola identidad de establecimiento. Un POI tampoco demuestra disponibilidad para instalar recarga. |
| **7. Capacidad eléctrica: i-DE** | Estructurar campos y unidades, documentar temporalidad y resolver formato de coordenadas, ejes, huso y datum antes de integrar espacialmente. | Tabla de capacidad de demanda; geometrías solo cuando la interpretación espacial esté acreditada. | Las unidades y la interpretación de cada campo están documentadas. Si persiste una duda de georreferenciación, la salida queda identificada como pendiente de integración espacial. La capacidad sigue siendo orientativa y no se suma como si todos los nudos fueran independientes. |
| **8. Relaciones y validación conjunta** | Relacionar claves y asignaciones espaciales seguras entre las salidas elegibles. Revisar cardinalidad, cobertura, coherencia temporal e incidencias. Completar diccionario y reproducción. | Conjunto Silver por entidades, relaciones territoriales y reporte de calidad; entradas preparadas para diseñar Gold. | No hay pérdidas, repeticiones o asignaciones ambiguas sin explicar; cada fuente tiene estado de inclusión. Las salidas se regeneran desde las copias Bronze identificadas y sus reglas. Se cumplen los criterios generales de cierre indicados abajo. |

## Orden de ejecución

Las fases **1–3 están completadas**. La **4** tiene las entidades tabulares de
recarga preparadas; EPSG:4258 se ha identificado como CRS declarado de su CSV,
con capa y contraste territorial materializados en fase 8 y conflictos pendientes.
La **5** tiene aforos y red viaria preparados con incidencias explícitas.
La **6** conserva POI, clasificación de interés y posibles correspondencias.
La **7** conserva la tabla histórica i-DE y añade capa complementaria EPSG:25830:
423 puntos con relación municipal admitida en 116 municipios. Publicación
04-09-2026 y periodo agosto según formato mensual CNMC, con corte exacto desconocido.
La **8** está cerrada operativamente con el alcance y las restricciones del
[informe conjunto](VALIDACION_CONJUNTA_SILVER.md). El siguiente trabajo es diseñar
Gold, justificando la unidad final y el criterio temporal antes de construirlo;
antes se amplía la revisión de las restricciones de recarga e i-DE.
La investigación técnica de **7** puede avanzar desde el principio; una duda de
i-DE no impide preparar y verificar las demás fuentes. **8** reúne las salidas
admitidas y deja explícitos los componentes que sigan pendientes.

Cada fuente se comprobará al prepararla. La validación final de la fase 8
revisa también cómo se comportan sus relaciones, sin posponer todos los controles
hasta el final. El asistente puede realizar estas tareas con los datos disponibles;
un contacto con proveedores requeriría una instrucción específica del usuario.

## Reglas que guiarán la implementación

### Convenciones comunes aceptadas

El 15 de octubre de 2026 se acepta la primera propuesta de reglas comunes.
Estas convenciones ya se aplican a la base territorial, DGT, población, renta,
recarga, aforos, red viaria y POI OSM;
las otras fuentes siguen pendientes. Los campos y claves
mínimos por fuente se concretan en el
[diccionario inicial de Silver](DICCIONARIO_SILVER.md), distinguiendo las claves
previstas de las comprobaciones pendientes de cada preparación.

| Regla común | Aplicación concreta |
| --- | --- |
| **Una fila representa una observación definida.** | Cada tabla declara entidad, categorías y periodo. Población, renta, parque y conectores mantienen unidades diferentes; las relaciones se documentan aparte. |
| **Identificadores estables y explícitos.** | `codigo_municipio` será texto de cinco posiciones, con ceros iniciales. Los identificadores de proveedor se conservarán como texto cuando sean códigos, sin confundirlos con cantidades. Las claves de unicidad se definirán por tabla, no mediante nombres de lugares. |
| **Nombres de campos homogéneos.** | Nombres en español, minúsculas, sin tildes y con guiones bajos: `codigo_municipio`, `anio`, `fecha_referencia`. Se documentará la correspondencia con las columnas originales, conservando los identificadores de origen necesarios. |
| **Tipos y unidades por variable.** | Recuentos enteros cuando corresponda; magnitudes numéricas con unidad documentada. Propuesta: potencia de recarga en kW, capacidad eléctrica en MW y renta en euros según su indicador. El nombre o el diccionario identifica la unidad. La conversión no implica redondear, sumar o transformar indicadores. |
| **Periodos separados de las fechas técnicas.** | `anio` para observaciones anuales y `fecha_referencia` cuando se conozca una fecha concreta. Descarga y procesamiento se registran aparte; los instantes técnicos se expresan en UTC. Se conservan los periodos disponibles y los desconocidos siguen sin completar. |
| **Ausencias e incidencias explícitas.** | Un valor no informado queda nulo y conserva su símbolo o estado original cuando sea necesario para interpretarlo. La causa puede ser desconocida, protegida o no aplicable solo si existe evidencia. Cero conserva su significado numérico. Una conversión fallida queda identificada como incidencia. |
| **Repeticiones revisadas según su significado.** | Cada tabla tendrá una clave candidata y una regla de validación. Una coincidencia de atributos no basta para borrar filas. Los conflictos se investigan y conservan con motivo hasta resolverlos; no se selecciona automáticamente la primera fila. |
| **Trazabilidad y conservación.** | Cada salida referencia copia Bronze, reglas, código y proceso que la generaron. Para cambios o exclusiones se conserva la referencia del registro de origen necesaria para revisarlos. No es necesario repetir toda esa información ni todas las columnas originales en cada fila. |
| **Asignación territorial comprobada.** | El marco de códigos es el conjunto contrastado de 542 municipios, sin imponer esa unidad a todas las tablas. Se distingue el código informado por el proveedor del asignado o comprobado espacialmente cuando difieran. Las asignaciones ambiguas quedan señaladas. |

Como primer esquema de observación, se propone:

| Salida | Qué representa una fila | Clave candidata |
| --- | --- | --- |
| Población municipal | Población de un municipio, categoría de sexo y año. | Municipio + sexo + año. |
| Parque municipal DGT | Indicadores de parque de un municipio en su fecha de referencia. | Municipio + fecha de referencia. |
| Renta por nivel territorial | Un indicador de un territorio y año, distinguiendo municipio, distrito y sección. | Nivel + código territorial completo + indicador + año. |
| Detalle de conectores MITECO | Registro de conector vinculado a punto e instalación; sin reducir atributos variables a un padre único. | Instalación + punto + conector. Las seis repeticiones son nacionales; el contraste focal no observa repeticiones de esa clave en CV. Se volverá a validar al preparar. |

El diccionario concreta las unidades, campos mínimos, correspondencias con el
origen y claves para las fuentes del catálogo. Incluye claves técnicas para
DGT y OSM donde el identificador individual o la unicidad supuesta no existen.
La [configuración técnica](CONFIGURACION_SILVER.md) concreta formatos físicos,
precisión, lectores y operaciones espaciales admitidas, con pruebas de compatibilidad.

### Aplicación a las limitaciones conocidas

- **Conservación y trazabilidad:** los originales permanecen intactos. Cada salida
  identificará recurso Bronze, copia o huella de referencia, transformación y
  versión del código. Las salidas generadas se prevén en `resultados/silver/`,
  fuera de Git; el código y la documentación de reglas se versionarán.
- **Tiempo:** conservar los periodos disponibles y distinguir fecha del dato,
  fecha de descarga y fecha de proceso. La selección temporal para comparar o
  construir indicadores se justificará al diseñar Gold. La renta local seguirá
  vinculada a su propia huella y edición desconocida, sin sustituirla por el
  descargable actual.
- **Ausencias:** conservar el valor original y diferenciar, hasta donde lo
  permita la documentación, desconocido, protegido y no aplicable. Si la causa
  no se conoce, se indicará así. Las imputaciones necesitan una justificación;
  no forman parte del tratamiento por defecto.
- **DGT:** Distintivo 0 se mantiene como la aproximación acordada. Los códigos
  `PP000` quedan separados de los municipios. El TXT se procesará por bloques y
  con los campos necesarios; los registros con atributos iguales no se borrarán
  como vehículos duplicados y la supresión municipal no se imputará como observada.
- **INE:** la población mantiene sexo y año sin sumar totales con desgloses.
  Renta conserva nivel e indicador; las 54 filas sin valor del código histórico
  `12066` se separarán con su motivo. No se reemplazarán automáticamente por
  `46902`, que ya está presente.
- **Relaciones espaciales:** se conservarán tanto la información territorial
  original como el resultado contrastado cuando difieran. Un punto sin
  asignación clara queda señalado; un tramo o polígono que atraviesa varios
  municipios puede requerir una relación múltiple. No se forzará una asignación
  única mediante un centroide o el vecino más próximo sin una regla justificada.
- **Casos problemáticos:** se distinguirán registros utilizables, fuera de
  ámbito y con incidencias. Las exclusiones y cambios tendrán motivo y recuento;
  una conversión fallida no eliminará una fila silenciosamente.

## Cierre de la fase 1

Se han definido las convenciones, el diccionario y la configuración técnica:
Parquet para tablas y GeoParquet para capas, tipos explícitos, DuckDB con su
extensión oficial espacial y EPSG:25830 para operaciones métricas regionales.
Se han probado formatos, ejes, conservación de Z y lecturas de muestras sin perder
el `fid` de los GeoPackages. MITECO e i-DE mantienen pendiente la admisión de sus
coordenadas hasta acreditar su referencia; esto no bloquea las fuentes admitidas.
Las comprobaciones completas por fuente siguen en las fases siguientes.
La fase 2 posterior materializa la base territorial; las restantes fuentes siguen
pendientes de preparación.
No se seleccionan todavía cuadrícula, resolución ni distancias por red.

La granularidad de cada salida Silver responderá a su entidad de origen. La
unidad final para priorizar ubicaciones y el criterio temporal de sus indicadores
se concretarán antes de construir Gold. Si se necesitan rutas reales, habrá que
justificar y comprobar conectividad y restricciones; la existencia de líneas
IGN no se presentará como garantía de una red enrutable.

## Cierre de la fase 2

La [base territorial](BASE_TERRITORIAL_SILVER.md) contiene 542 municipios INE y
542 recintos IGN, con claves únicas y correspondencia completa. Todas las
geometrías son válidas antes y después de proyectar; no se han reparado ni
excluido recintos. Las uniones municipales coinciden con los niveles provincial
y autonómico de la misma respuesta. Se conservan 58 diferencias de nombre,
resueltas para la correspondencia mediante códigos, sin reescribir etiquetas.

Las salidas Parquet/GeoParquet y el informe de ejecución están materializados
fuera de Git, con entradas verificadas, trazabilidad y comprobación de conservación
tras escribir. La diferencia temporal INE 2025 / consulta IGN 2026 sigue explícita.
La fase 3 posterior prepara parque, población y renta.

## Cierre de la fase 3

El [informe de parque, población y renta](DEMOGRAFIA_PARQUE_SILVER.md) documenta
las salidas validadas: 542 registros de parque municipal, tres PP000 separados,
4.124.363 registros DGT del ámbito, 8.130 observaciones de población y 262.710 de
renta vigente. Se conservan aparte las 54 filas históricas de 12066, sin remapearlas.
Las 7.114 ausencias de renta vigente permanecen nulas y documentadas.

Las claves son únicas; los recuentos DGT reconcilian y población conserva sexo/año,
con Total = Hombres + Mujeres. No hay errores de conversión. Se comprueban huellas
de entrada y conservación completa tras escribir Parquet. El TXT se procesa sin
cargarlo entero en memoria Python ni deduplicar por atributos. Se conservan las
limitaciones del indicador Distintivo 0 y del municipio no publicado en el detalle.
La fase 4 posterior prepara la recarga existente MITECO.

## Estado de la fase 4

La [preparación de recarga](RECARGA_SILVER.md) conserva las 5.244 filas CV como
conectores, vinculadas a 4.402 puntos y 1.526 instalaciones. El lector conserva
comillas interiores y campos multilínea, con reconstrucción exacta de registros.
Claves y relaciones comprobadas; sin errores de conversión. Las seis repeticiones
nacionales quedan explicadas fuera del ámbito y se conservan los atributos
variables en el detalle, sin seleccionar una primera variante.

La salida tabular está preparada. La investigación posterior del 16-10-2026
identifica **EPSG:4258, ETRS89 geográfico, declarado en el recurso CSV del catálogo
oficial**. Se documenta en el informe de recarga, junto con la salvedad sobre
WGS84 en el modelo OCPI de entrada. Se adopta el metadato específico del CSV
como referencia documental, sin certificar el datum real de cada registro.
La integración posterior se documenta en el avance de fase 8: capa y contraste
municipal materializados, con 133 conflictos conservados para revisión.
Las salidas e informe originales se conservan, sin reescribir sus estados históricos.

## Cierre de la fase 5 con limitaciones

El [informe de tráfico y red](TRAFICO_RED_SILVER.md) documenta 9.041 aforos de
2009–2025, 1.118.309 tramos por copia provincial y 1.197.446 asociaciones tramo–vial.
No se pierde ninguna asociación ni se selecciona una geometría entre variantes
en conflicto. Claves, relaciones, huellas, tipos, atributos, CRS y relectura WKB
comprobados. Los tipos de medida y unidades se contrastan con el modelo GVA.

Se mantienen 107 incidencias: 45 IMD cero, 55 tipos vacíos, dos códigos `F` no
documentados y cinco geometrías IGN que degeneran a longitud cero tras proyectar.
Estas cinco quedan marcadas y no se consideran admitidas para operaciones métricas;
no se reparan ni se eliminan. No hay errores de conversión numérica. Los años de
aforos no forman un panel fijo; la red aún no está validada para rutas.
La fase 6 posterior prepara OSM. El contraste espacial de MITECO queda para fase 8.

## Cierre de la fase 6 con limitaciones

El [informe OSM](POI_OSM_SILVER.md) documenta 269.287 elementos conservados de seis
capas, procedencia por capa/fid y geometrías admitidas. Se marcan 519 objetos
exteriores sin eliminarlos, incluidos terminales de ferry alejados inspeccionados.
Hay 17.794 elementos de categorías seleccionadas que intersectan el ámbito para
revisión posterior; no se presentan como ubicaciones viables confirmadas.

Se mantienen las repeticiones de identificador y se registran 77 posibles
correspondencias punto–área, sin fusionar por identidad supuesta ni calcular
establecimientos únicos. Huellas Bronze y territoriales, claves, referencias,
recuentos y relectura de atributos/WKB comprobados. Sin incidencias de geometría
o conversión en la ejecución. La siguiente fase es i-DE; Gold sigue pendiente.

## Estado de la fase 7

El [informe i-DE](CAPACIDAD_DEMANDA_SILVER.md) documenta 423 puntos de conexión
seleccionados por provincia declarada, sin pérdidas. Se conservan los 17 campos
originales, medidas exactas en kV/MW, posiciones, banderas interpretadas y estados.
Claves nacionales y CV, recuentos, huellas y relectura Parquet comprobados.
No hay errores de conversión; se mantienen 344 ausencias en cada campo de posiciones.

La tabla histórica está preparada. La incorporación del 19-10 aplica publicación
04-09-2026, periodo agosto según formato mensual CNMC y CRS EPSG:25830 en una
capa complementaria de 423 puntos, todos con relación municipal concordante
en 116 municipios. No se desplazan puntos ni se fusionan subestaciones. Capacidad informativa, sin suma
de nudos ni garantía de conexión. La siguiente fase es la 8; MITECO tiene
CRS declarado EPSG:4258 identificado y capa materializada, con conflictos municipales.
Cinco geometrías IGN siguen sin admisión métrica.

## Avance de fase 8: recarga espacial

El [informe espacial MITECO](RECARGA_ESPACIAL_SILVER.md) documenta 1.526 puntos
geométricos válidos, cada uno en un único municipio y con provincia concordante.
Se admiten 1.393 asignaciones municipales que también concuerdan con la etiqueta
oficial resuelta desde MITECO. Las otras 133 quedan como conflictos, conservadas
con coordenadas, candidatos y atributos originales. No se corrigen nombres o
posiciones automáticamente ni se fuerza asignación por proximidad.

Se mantienen 4.402 puntos y 5.244 conectores al relacionar con la capa; la admisión
municipal alcanza 3.965 y 4.751, respectivamente. Sin pérdida ni multiplicación.
Claves, huellas, ejes, CRS, vuelta de proyección y relectura completa comprobados;
77 pruebas superadas. Queda revisar los conflictos y continuar las relaciones y
validación conjunta de otras fuentes. No se declara Silver completa.

## Cierre operativo de fase 8 con limitaciones (18-10, ampliado el 19-10-2026)

La [validación conjunta](VALIDACION_CONJUNTA_SILVER.md) verifica las 30 salidas de
ocho bloques, sus claves, esquemas, huellas, dependencias y periodos; comprueba
integridad referencial, conservación de atributos y ausencia de multiplicación
al relacionar municipios o instalaciones. Se conservan los periodos, nulos,
PP000, 12066 y el detalle DGT sin municipio, sin nuevas imputaciones.

Las 133 discrepancias MITECO tienen una revisión trazable: 81 relaciones resueltas
con evidencia primaria de establecimientos o direcciones oficiales y 52 pendientes. La relación
complementaria admite 1.474 instalaciones, 4.231 puntos y 5.053 conectores;
las entidades originales permanecen intactas. El caso Catadau conserva su
incertidumbre pese a la dirección comercial coincidente.

Se materializan 1.430.940 relaciones entre POI/aforos/tramos/puntos i-DE y
municipios, con 1.397.060 estados que incluyen exteriores, intersecciones múltiples y las cinco
geometrías no admitidas. No se reparten indicadores entre municipios. La
ampliación del 19-10 incorpora la capa i-DE y sus 423 relaciones municipales;
las ejecuciones anteriores se conservan.
Las seis salidas se han releído y verificado con reglas v4; 120 pruebas aprobadas
sin omisiones. La tabla y la capa i-DE mantienen publicación y mes informado
separados; no se acredita un día exacto de corte.
Los originales y las ejecuciones previas se conservan.

Silver queda **preparada con limitaciones**, no libre de incidencias ni homogénea
en el tiempo. Gold aún debe definir unidad, periodos y tratamiento de las
relaciones múltiples o pendientes. No se ha iniciado scoring, modelo o web.

## Criterios para declarar Silver preparada

### Limitaciones conservadas para el diseño de Gold (19-10-2026)

- Los cinco segmentos IGN degenerados se conservan con bandera y fuera de los
  cálculos métricos/cruces que exigen una línea admitida. Reparación aplazada;
  revisar ante una edición corregida o necesidades concretas de conectividad.
- Las 52 asignaciones municipales de recarga siguen pendientes, con registros
  y evidencia preservados. No se imputan municipios ni se interpretan como cero
  cargadores. Su revisión no bloquea plantear Gold.
- Gold contemplará comunicar la incertidumbre de asignación, con una propuesta
  de etiqueta como «Zona con incertidumbre en la asignación de puntos de recarga».
  La unidad, delimitación y efecto en indicadores se decidirán en su diseño;
  no se presume falta general de datos ni se materializa un indicador todavía.

Estas decisiones cierran el tratamiento actual de las incidencias para avanzar
al planteamiento de Gold, manteniendo trazabilidad y posibilidad de revisión.

### Criterios generales

1. Tablas y capas identificadas, con significado de fila, claves, tipos,
   unidades y referencia temporal/espacial documentados.
2. Cobertura por fuente contrastada: las fuentes parciales, como aforos o i-DE,
   no tendrán que informar todos los municipios para considerarse correctamente
   preparadas.
3. Recuentos y cambios reconciliados en cada transformación y nivel de entidad;
   las separaciones o relaciones múltiples explican las variaciones esperadas.
4. Ausencias, conflictos de claves, geometrías problemáticas y asignaciones
   ambiguas resueltos o conservados como incidencias con efecto conocido.
5. Estado explícito por fuente: preparada, preparada con limitaciones o pendiente
   de una integración concreta. Una fuente pendiente no se contará como integrada.
6. Ejecución reproducible con comprobaciones proporcionales a los riesgos, reporte
   de calidad y diccionario de las salidas; originales preservados.

Gold construirá los indicadores finales sobre estas entidades: por ejemplo,
recuentos territoriales de recarga o variables para comparar ubicaciones.
Scoring, ranking, entrenamiento de modelos y aplicación web son fases posteriores.
