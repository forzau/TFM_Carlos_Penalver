# Diccionario inicial de salidas Silver

Versión **3, 15 de octubre de 2026**. Define campos, unidades de observación y
claves de las salidas que se prepararán según el [plan de Silver](PLAN_SILVER.md).
Las convenciones comunes han sido aceptadas; **municipios y recintos municipales
están preparados**. Las demás tablas siguen en diseño.
Se han contrastado cabeceras, esquemas y claves auditadas, con una comprobación
adicional de relaciones en MITECO. Esto no sustituye la validación al materializar
cada fuente.

## Convenciones de los esquemas

- Los tipos lógicos se concretan en la [configuración técnica](CONFIGURACION_SILVER.md):
  Parquet/GeoParquet, códigos `VARCHAR`, recuentos `BIGINT`, medidas decimales
  `DECIMAL(18,2)`, coordenadas `DOUBLE`, fechas e instantes con su precisión y
  zona acreditadas. No se redondea por defecto ni se atribuye precisión nueva al dato.
- Los nombres de campos usan español, minúsculas y guiones bajos. Los nombres,
  categorías y etiquetas originales pueden conservar tildes y mayúsculas.
- `codigo_municipio` es texto de cinco posiciones y `codigo_provincia`, de dos.
  Los identificadores de proveedor se conservan como códigos textuales.
- Las claves funcionales indicadas se refieren a **una versión de salida ligada
  a sus copias Bronze**. Si se reunieran varias instantáneas en una misma tabla,
  habría que incluir su versión de origen en la clave.
- Una clave identificante debe estar completa. Los registros sin clave suficiente
  se conservan identificados como incidencias u observaciones pendientes; no se
  inventan códigos para incluirlos en una entidad con unicidad declarada.
- Un valor de medida puede ser nulo. `estado_valor` distingue `informado`,
  `no_informado`, `protegido`, `no_aplicable` y `error_conversion`; los estados
  protegido/no aplicable solo se usan si están acreditados. `valor_origen` conserva
  el texto necesario para interpretar ausencias o conversiones. No se atribuye una
  causa concreta a todos los símbolos `.` o `..` sin verificar su significado.
- `origen_id` identifica en los metadatos una entrada concreta: recurso, archivo
  relativo, huella y capa/hoja cuando corresponda. `registro_origen` identifica
  el registro leído dentro de esa entrada; en un GeoPackage se conserva `fid`.
  Son referencias de trazabilidad, no identificadores nuevos de vehículos o POI.
- Las tablas de entidades referenciarán sus orígenes y las relaciones necesarias
  para reconstruir transformaciones. Una entidad obtenida de varios registros
  debe conservar esa relación de procedencia, sin escoger una fila arbitraria.

## 1. Referencia municipal

**`municipios`**: una fila por municipio vigente en la referencia INE de 2025.
Clave: `codigo_municipio`. Cobertura prevista: 542 municipios.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `codigo_municipio` | texto | INE: concatenación de `CPRO` y `CMUN`; excluye `DC`. |
| `codigo_provincia` | texto | INE: `CPRO`. |
| `nombre_municipio` | texto | INE: `NOMBRE`. |
| `fecha_referencia` | fecha | 2025-01-01, acreditado en el título del libro. |

**`recintos_municipales`**: una representación municipal de la respuesta IGN
conservada. Clave técnica: `origen_id` + `codigo_municipio`.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `codigo_municipio` | texto | Cinco últimas posiciones de `nationalCode` en nivel municipal; contrastadas con INE. |
| `codigo_nacional_ign` | texto | Propiedad `nationalCode` completa. |
| `nombre_municipio_ign` | texto | Nombre contenido en `name`, conservado para contraste. |
| `geometria` | geometría | GeoJSON interpretado como OGC:CRS84, longitud/latitud, con contraste documentado en la configuración; salida EPSG:25830 validada en fase 2. |
| `origen_id` | texto | Entrada GeoJSON y fecha de consulta vinculadas en los metadatos. |
| `registro_origen` | texto | Identificador del objeto IGN conservado para rastrear la geometría. |

Los niveles autonómico y provincial de la respuesta no se mezclan con municipios.
La fecha de consulta de 2026 no se utiliza como fecha histórica de los límites.
Las dos tablas se han materializado y verificado para los 542 municipios; el
[informe territorial](BASE_TERRITORIAL_SILVER.md) recoge controles y las 58
diferencias nominales conservadas entre INE e IGN.

## 2. Parque de vehículos

**`parque_municipal`**: una fila por municipio y fecha de referencia en el XLSX.
Clave: `codigo_municipio` + `fecha_referencia`.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `codigo_municipio` | texto | `Código INE`, excluyendo las filas PP000 de esta tabla. |
| `fecha_referencia` | fecha | 2025-12-31, según ficha oficial del parque. |
| `parque_total` | entero | `Parque Total`. |
| `vehiculos_distintivo_0` | entero | `Distintivo 0`, aproximación acordada de demanda potencial. |
| `electrificado_origen` | entero | `Electrificado`, conservado con el significado del proveedor. |

No se suman ni restan los dos últimos campos para deducir BEV/PHEV. Los indicadores
seleccionados no requieren trasladar a Silver las 57 columnas del XLSX: el libro
completo permanece disponible en Bronze.

**`parque_sin_municipio`**: las filas PP000 del XLSX, con
`codigo_agrupacion_origen` (texto), `codigo_provincia` (texto), `fecha_referencia`
(fecha) y los mismos tres indicadores enteros. Clave:
`codigo_agrupacion_origen` + `fecha_referencia`. No son municipios ni totales
provinciales; no se les asigna un municipio ficticio.

**`parque_detalle_observado`**: un registro del TXT seleccionado para el ámbito.
Clave técnica: `origen_id` + `registro_origen`. La fuente no ofrece una clave
individual de vehículo, por lo que no se deduplica por coincidencia de atributos.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `origen_id`, `registro_origen` | texto, entero | Referencia de la copia y ordinal del registro leído. |
| `codigo_provincia` | texto | `PROVINCIA`. |
| `codigo_municipio` | texto, admite nulo | `MUNICIPIO`; la ausencia o supresión no se imputa como observada. |
| `periodo` | texto | `2025-12`, periodo acreditado de esta copia; no se inventa un día concreto. |
| `tipo_dgt_codigo` | texto | `TIPO_DGT`. |
| `propulsion_codigo` | texto | `PROPULSION`. |
| `categoria_electrica_codigo` | texto | `CATELECT`. |
| `distintivo_codigo` | texto | `TIPO_DISTINTIVO`. |

La interpretación de códigos se vinculará al diccionario DGT correspondiente.
La lectura será por bloques, conservando el detalle eléctrico publicado donde
esté disponible; no se reconstruye el detalle suprimido de municipios pequeños.

## 3. Población

**`poblacion_municipal`**: una fila por municipio, sexo y año.
Clave: `codigo_municipio` + `sexo` + `anio`.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `codigo_municipio` | texto | Código al inicio de `Municipios`. |
| `sexo` | texto | `Sexo`; conserva Total, Hombres y Mujeres como categorías distintas. |
| `anio` | entero | `Periodo`. |
| `poblacion` | entero, admite nulo | `Total`, interpretando el separador de miles. |
| `estado_valor`, `valor_origen` | texto | Estado de interpretación y valor leído cuando resulte necesario. |

El total nacional no pertenece a esta tabla municipal. Las sumas y comparaciones
seleccionarán una categoría compatible, sin sumar Total con Hombres y Mujeres.

## 4. Renta

**`renta_territorial`**: una fila por territorio, nivel, indicador y año.
Clave: `nivel_territorial` + `codigo_territorio` + `indicador` + `anio`.
El mismo esquema conserva los tres niveles, identificados de forma explícita;
se podrán consultar por separado sin mezclar sus medidas.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `nivel_territorial` | texto | Municipio, distrito o sección, según los campos territoriales informados. |
| `codigo_territorio` | texto | Código del campo que corresponde al nivel de la fila. |
| `codigo_municipio` | texto | Código completo de `Municipios`. |
| `codigo_distrito` | texto, admite nulo | Código de `Distritos`, cuando el nivel lo incluya. |
| `codigo_seccion` | texto, admite nulo | Código de `Secciones`, cuando proceda. |
| `indicador` | texto | `Indicadores de renta media`; conserva los seis indicadores diferenciados. |
| `anio` | entero | `Periodo`. |
| `valor_eur` | decimal, admite nulo | `Total`; la base por persona/hogar/unidad de consumo forma parte del indicador. |
| `estado_valor`, `valor_origen` | texto | Conservan el estado y símbolo leído; sin imputación a cero. |

Las 54 filas de `12066` sin valor se separarán del conjunto territorial vigente,
con referencia al origen y motivo. No se remapean a `46902`, ya presente. Se
trabaja con la copia estática registrada, sin sustituirla por el CSV remoto actual.

## 5. Recarga MITECO

Las claves siguientes están acotadas a la copia y al ámbito preparado. La
separación en entidades exige comprobar que sus atributos sean consistentes.

**`recarga_instalaciones`**: una fila por instalación.
Clave: `instalacion_id`.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `instalacion_id` | texto | `COD.INSTALACION`. |
| `nombre_instalacion` | texto | `NOMBRE INSTALACION`. |
| `operador_id`, `nombre_operador` | texto | `COD.OPERADOR`, `NOMBRE OPERADOR`. |
| `provincia_nombre_origen`, `municipio_nombre_origen` | texto | `PROVINCIA`, `MUNICIPIO`; no se presentan como códigos INE. |
| `direccion`, `codigo_postal` | texto | `DIRECCIÓN`, `CODIGO POSTAL`; el código postal no se usa como clave municipal. |
| `latitud`, `longitud` | número de coma flotante de 64 bits, admiten nulo | `LATITUD`, `LONGITUD`; quitar envoltorios de exportación como texto, sin ejecutar fórmulas ni redondear coordenadas. |
| `localizacion_origen`, `tipo_horario_origen` | texto | `LOCALIZACION`, `TIPO HORARIO APERTURA`. |

**`recarga_puntos`**: una fila por punto dentro de una instalación.
Clave: `instalacion_id` + `punto_id`. Relación con instalaciones por su clave.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `instalacion_id`, `punto_id` | texto | `COD.INSTALACION`, `ID. PUNTO DE RECARGA`. |
| `codigo_punto_origen` | texto | `COD. PUNTO DE RECARGA`, distinto del identificador del punto. |
| `accesibilidad_origen` | texto | `ACCESIBILIDAD`; conservar `NODISPONIBLE` como información desconocida, no como acceso denegado. |

**`recarga_conectores`**: detalle publicado de un conector dentro de punto e
instalación. Clave funcional prevista:
`instalacion_id` + `punto_id` + `conector_id`, a validar en la preparación.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `instalacion_id`, `punto_id`, `conector_id` | texto | `COD.INSTALACION`, `ID. PUNTO DE RECARGA`, `ID. CONECTOR`. |
| `tipo_conector`, `tipo_carga`, `formato_conector` | texto | `TIPO CONECTOR`, `TIPO DE CARGA`, `FORMATO`. |
| `potencia_maxima_kw` | decimal, admite nulo | `POTENCIA MAXIMA`; unidad y separador decimal explícitos. |
| `fecha_ultima_modificacion` | fecha y hora sin zona acreditada, admite nulo | `FECHA DE ULTIMA MODIFICACION`; `TIMESTAMP` conserva la hora de origen. No es fecha de instalación ni se presume UTC. |
| `horario_apertura_origen`, `servicios_origen`, `metodos_pago_origen` | texto | `HORARIO APERTURA`, `TIPOS DE SERVICIOS`, `METODOS DE PAGOS`, conservados en el detalle hasta aclarar su semántica. |

Comprobación focal sobre la lectura permisiva auditada: en las 5.244 filas CV,
hay 1.526 instalaciones, 4.402 puntos y **ninguna repetición de la clave triple**.
Las seis repeticiones de la auditoría nacional no deben atribuirse automáticamente
al ámbito valenciano. En los registros CV el horario varía dentro de 510
instalaciones y los servicios dentro de 37; los métodos de pago varían dentro de
426 puntos. Por ello estos campos no se reducen a una primera fila del padre.
Esto es un diagnóstico de los valores leídos, no una validación completa de la
semántica del exportador con comillas no estándar.

Antes de generar las entidades se comprobarán de nuevo las dependencias y
las coordenadas. Una clave en conflicto conserva sus observaciones e incidencia
hasta resolverla; no se elimina por orden de aparición. La potencia por conector
no acredita capacidad simultánea de la instalación. La geometría de la instalación
y su relación municipal se añadirán cuando se acredite su interpretación espacial.

## 6. Aforos GVA

**`aforos_tramo_anio`**: una observación por tramo y año.
Clave: `tramo_aforo_id` + `anio`. No presupone que los tramos sean estables entre años.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `tramo_aforo_id` | texto | `clau_tramo`. |
| `anio` | entero | Año de la capa `AforosAAAA`. |
| `carretera`, `tipo_medida_trafico` | texto | Campos `carretera`, `tipo_medida_trafico`. |
| `pk_inicio`, `pk_fin` | texto, admiten nulo | Campos homónimos; conservar notaciones como `0+000` hasta justificar conversión y unidad. |
| `imd_vehiculos_dia` | decimal, admite nulo | `imd`; conservar interpretación de medida y estimación. |
| `porcentaje_pesados` | decimal, admite nulo | `vehiculo_pesados_zp`; interpretación y escala por verificar. |
| `geometria` | geometría | `geom`, con EPSG:25830 declarado en la entrada. |

Los campos seleccionados existen en las 17 capas auditadas y `clau_tramo` no
tiene nulos en ellas. Se conservan años y cobertura original. No se suman años
como tráfico actual ni se equipara un tramo de aforo a un tramo IGN por su nombre.

## 7. Red viaria IGN

**`red_tramos`**: una geometría de tramo por copia provincial.
Clave prevista: `provincia_origen` + `tramo_id`.

Campos: `provincia_origen` (texto, procedencia del paquete), `tramo_id` (texto,
`id_tramo`), `tipo_tramo_codigo` (texto, `tipo_tramo`), `tipo_tramo_descripcion`
(texto, `tipo_tramd`), `geometria` (geometría, `geom`). Otros atributos de tramo
solo se incorporarán si su uso y dependencia están comprobados.

**`red_tramo_vial`**: una asociación tramo–vial por copia provincial.
Clave: `provincia_origen` + `tramo_id` + `vial_id`.

Campos: `provincia_origen`, `tramo_id` (`id_tramo`), `vial_id` (`id_vial`),
`codigo_vial` (`codigo`), `nombre_vial` (`nombre`), `tipo_vial_codigo` (`tipo_vial`)
y `tipo_vial_descripcion` (`tipo_viald`), todos textuales.

La clave tramo–vial no se repite en las copias provinciales auditadas; `id_tramo`
sí se repite por sus asociaciones. Extraer una geometría por tramo exige comprobar
que las representaciones coinciden; un conflicto no se resuelve tomando la primera.
La provincia de procedencia no demuestra que una geometría esté enteramente
dentro de ella. Se conserva la información Z y la referencia original hasta
justificar cualquier transformación. Estas salidas no constituyen todavía una
red enrutable.

## 8. Elementos OSM

**`poi_elementos`**: un elemento de una capa de la distribución, antes de resolver
coincidencias entre representaciones. Clave técnica: `origen_id` + `fid_origen`;
`origen_id` distingue la capa, además del archivo y la copia.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `origen_id`, `capa_origen`, `fid_origen` | texto, texto, entero | Metadatos de la entrada y `fid` de su capa. |
| `osm_id` | texto | `osm_id`, como identificador publicado, sin asumir unicidad global. |
| `categoria_codigo_origen`, `categoria_origen` | texto | `code`, `fclass`. |
| `nombre_origen` | texto | `name`. |
| `geometria` | geometría | `geom`, preservando punto o polígono y su referencia documentada. |

El esquema mínimo coincide en las capas de `pois` y `traffic` auditadas. Hay
repeticiones de `osm_id` incluso dentro de algunas de esas capas; por eso no se
usa como clave única del elemento ni como prueba de establecimiento único.
La selección de categorías y las correspondencias punto–polígono se resolverán
en su fase, conservando referencias a todos los elementos que se agrupen.

## 9. Capacidad de demanda i-DE

**`capacidad_demanda`**: un registro publicado por identificador del punto de
conexión. Clave candidata: `punto_conexion_id`, sin vacíos ni repeticiones en el
perfil nacional auditado. No se equipara automáticamente a una subestación única.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `punto_conexion_id`, `nombre_punto_conexion` | texto | `Identificador del Punto de Conexión`, `Denominación del Punto de Conexión`. |
| `gestor_red`, `provincia_nombre_origen`, `municipio_nombre_origen` | texto | `Gestor de red`, `Provincia`, `Municipio`. |
| `subestacion_origen` | texto | `Subestación`. |
| `x_utm_origen`, `y_utm_origen` | texto | `Coordenada UTM X`, `Coordenada UTM Y`, conservadas hasta acreditar formato, huso y datum. |
| `nivel_tension_kv` | decimal, admite nulo | `Nivel de Tensión (kV)`. |
| `capacidad_firme_disponible_mw` | decimal, admite nulo | `Capacidad firme disponible (MW)`. |
| `capacidad_ocupada_mw` | decimal, admite nulo | `Capacidad de acceso firme de demanda ocupada (MW)`. |
| `capacidad_admitida_no_evaluada_mw` | decimal, admite nulo | `Capacidad de acceso firme admitida y no evaluada (MW)`. |
| `compromiso_regulatorio_origen`, `nudo_0_asterisco_origen` | texto | `Capacidad comprometida por cuestiones regulatorias`, `Nudo 0*`; interpretar su codificación antes de convertirlos a booleanos. |
| `fecha_referencia` | fecha, admite nulo | Desconocida en la copia; no se completa con fecha de registro. |

La normalización numérica no acredita posición espacial ni posibilidad de
conexión. La fuente puede prepararse como tabla con limitaciones, manteniendo
pendiente la geometría y la integración territorial si no se resuelve la referencia.

## 10. Relaciones y control de preparación

**`entidad_municipio`**: relación contrastada entre una entidad espacial y un
municipio. Campos: `tabla_entidad`, `clave_entidad`, `codigo_municipio`,
`metodo_asignacion`, `estado_asignacion`, todos textuales y con definición
documentada de la clave compuesta referenciada. Clave de relación para coincidencias
resueltas: tabla + clave de entidad + municipio. Los casos sin correspondencia
segura se registran como incidencias, sin forzar un municipio ficticio.

Una línea o polígono puede tener relaciones con varios municipios. El método
de asignación y la necesidad de fraccionar geometrías se justificarán según las
operaciones requeridas, sin multiplicar inadvertidamente indicadores o entidades.

**Incidencias y metadatos**, por salida: identificación del origen y registro,
tabla/campo afectados, motivo, valor leído necesario y acción aplicada o pendiente.
Se conservarán además los orígenes de la salida, huellas, versión de reglas/código,
fecha UTC de proceso y recuentos de control. No hace falta repetir este conjunto
de metadatos en cada fila de datos ni crear una plataforma adicional para registrarlo.

## Estado de preparación

En la fase 1 se realizó la comprobación documental y de entrada: 76 correspondencias distintas de campos
de origen citadas en las tablas contrastadas con las cabeceras/perfiles, campos
viarios revisados en los tres paquetes provinciales y esquema mínimo de aforos
presente en las 17 capas. Enlaces locales comprobados y 29 originales conservan
el tamaño y modificación previamente registrados. Esta comprobación no ejecuta
conversiones, deduplicaciones ni las validaciones completas de las futuras salidas.

Quedan definidos los campos mínimos y las claves previstas o técnicas por fuente,
con su correspondencia de origen. La [configuración técnica](CONFIGURACION_SILVER.md)
completa formatos físicos, precisión, lectores, ejes y CRS métrico, con pruebas
pequeñas de compatibilidad y límites espaciales por fuente. La fase 1 queda
cerrada como diseño. La fase 2 materializa `municipios` y `recintos_municipales`,
con correspondencia completa, geometrías válidas y relectura de las salidas
comprobada. La preparación de parque, población y renta es el siguiente paso.
Las claves y dependencias que requieren comprobaciones de registros volverán a
validarse al preparar su fuente; no se presentan como unicidad universal garantizada.
Las demás entidades de este diccionario todavía no se han materializado.
