# Plan de trabajo de Silver

Fecha: **15 de octubre de 2026**. Estado: **fases 1 y 2 cerradas; base territorial
preparada y fases 3–8 pendientes**. Este documento concreta el orden de preparación a
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

Las fases **1 y 2 están completadas**. Se continúa con **3 y 4** para disponer del núcleo
de parque, población, renta y recarga existente. Después se preparan **5 y 6**.
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
Estas convenciones ya se aplican a la base territorial; las otras fuentes
siguen pendientes. Los campos y claves
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
El siguiente paso es la fase 3: parque, población y renta.

## Criterios para declarar Silver preparada

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
