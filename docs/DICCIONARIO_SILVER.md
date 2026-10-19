# Diccionario inicial de salidas Silver

Versión **15, 19 de octubre de 2026**. Define campos, unidades de observación y
claves de las salidas que se prepararán según el [plan de Silver](PLAN_SILVER.md).
Las convenciones comunes han sido aceptadas; **municipios, recintos, parque DGT,
población y renta están preparados**. Recarga tiene las entidades tabulares
preparadas; su capa EPSG:25830 está materializada, con 133 conflictos municipales
conservados. Aforos y red viaria están preparados con
incidencias señaladas. OSM está preparado con clasificación y correspondencias
sin fusión; i-DE tiene tabla histórica y capa complementaria con publicación
04-09-2026, periodo 2026-08 y CRS EPSG:25830 acreditados y aplicados.
La validación conjunta está cerrada operativamente con limitaciones: se conserva
el contraste original y una relación complementaria con 1.474 instalaciones
admitidas y 52 pendientes. i-DE incorpora 423 relaciones municipales admitidas;
Gold pendiente.
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
| `registro_origen` | entero | Ordinal del registro del CSV nacional después de la cabecera; el archivo y su huella se identifican por salida. |

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
| `registro_origen` | entero | Ordinal del registro del CSV nacional después de la cabecera; procedencia de archivo y huella por salida. |

Las 54 filas de `12066` sin valor se han separado del conjunto territorial vigente,
con referencia al origen y motivo. No se remapean a `46902`, ya presente. Se
trabaja con la copia estática registrada, sin sustituirla por el CSV remoto actual.

**`renta_codigos_historicos`** mantiene el mismo esquema y clave de renta, con
`motivo_separacion` textual. Contiene las 54 filas de `12066` apartadas por no
pertenecer a la referencia municipal de 2025. No se les asigna el código `46902`.

Las tablas de parque, población y renta se han materializado en la
[fase 3](DEMOGRAFIA_PARQUE_SILVER.md). El ordinal identifica observaciones, no
personas o vehículos. La precisión física sigue la configuración acordada:
recuentos `BIGINT`, año `SMALLINT`, renta `DECIMAL(18,2)` y códigos `VARCHAR`.

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
| `latitud_origen`, `longitud_origen` | texto | Contenido decimal publicado, tras retirar el envoltorio de exportación; permite revisar la conversión. |
| `estado_coordenadas` | texto | Estado de la ejecución tabular original: `rango_valido_datum_pendiente`, coordenada no admitida o par 0,0; no equivale a validación posicional. No se reescribe por la investigación posterior del CRS. |

**`recarga_puntos`**: una fila por punto dentro de una instalación.
Clave: `instalacion_id` + `punto_id`. Relación con instalaciones por su clave.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `instalacion_id`, `punto_id` | texto | `COD.INSTALACION`, `ID. PUNTO DE RECARGA`. |
| `codigo_punto_origen` | texto | `COD. PUNTO DE RECARGA`, distinto del identificador del punto. |
| `accesibilidad_origen` | texto | `ACCESIBILIDAD`; conservar `NODISPONIBLE` como información desconocida, no como acceso denegado. |

**`recarga_conectores`**: detalle publicado de un conector dentro de punto e
instalación. Clave funcional validada en CV:
`instalacion_id` + `punto_id` + `conector_id`.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `instalacion_id`, `punto_id`, `conector_id` | texto | `COD.INSTALACION`, `ID. PUNTO DE RECARGA`, `ID. CONECTOR`. |
| `tipo_conector`, `tipo_carga`, `formato_conector` | texto | `TIPO CONECTOR`, `TIPO DE CARGA`, `FORMATO`. |
| `potencia_maxima_kw` | decimal, admite nulo | `POTENCIA MAXIMA`; unidad y separador decimal explícitos. |
| `fecha_ultima_modificacion` | fecha y hora sin zona acreditada, admite nulo | `FECHA DE ULTIMA MODIFICACION`; `TIMESTAMP` conserva la hora de origen. No es fecha de instalación ni se presume UTC. |
| `horario_apertura_origen`, `servicios_origen`, `metodos_pago_origen` | texto | `HORARIO APERTURA`, `TIPOS DE SERVICIOS`, `METODOS DE PAGOS`, conservados en el detalle hasta aclarar su semántica. |
| `potencia_maxima_origen`, `estado_potencia` | texto | Potencia publicada con unidad y estado de conversión exacta a kW. |
| `fecha_ultima_modificacion_origen`, `estado_fecha` | texto | Instante publicado y estado; no se inventa zona horaria. |
| `voltaje_origen`, `intensidad_origen` | texto | `VOLTAJE`, `INTENSIDAD`, conservados sin derivar capacidad simultánea. |
| `registro_origen` | entero | Ordinal nacional después de la cabecera; vincula el detalle y los padres con la copia identificada por salida. |

Comprobación de la preparación con el lector específico: en las 5.244 filas CV,
hay 1.526 instalaciones, 4.402 puntos y **ninguna repetición de la clave triple**.
Las seis repeticiones de la auditoría nacional no deben atribuirse automáticamente
al ámbito valenciano. En los registros CV el horario varía dentro de 510
instalaciones y los servicios dentro de 37; los métodos de pago varían dentro de
426 puntos. Por ello estos campos no se reducen a una primera fila del padre.
La [fase 4](RECARGA_SILVER.md) conserva el texto alterado por el lector permisivo
en ocho registros CV, validando ancho y reconstrucción literal de todos los registros.

Las dependencias padre son consistentes y las claves únicas; una nueva copia con
conflictos detendría la preparación, sin eliminar observaciones por orden de aparición.
La tabla `incidencias` registra tabla, ordinal, campo, texto y motivo de errores
de conversión o coordenadas no admitidas; actualmente tiene cero filas.
La potencia por conector
no acredita capacidad simultánea de la instalación. La investigación posterior
identifica EPSG:4258 como CRS declarado de la distribución CSV. El bloque espacial
de fase 8 crea geometría con X=longitud/Y=latitud y transformación explícita a
EPSG:25830, con contraste territorial y admisión por registro. No se
supone EPSG:4326 desde la referencia OCPI de las instrucciones de entrada; la
diferencia documental y sus límites están en el informe de recarga.

### Capa complementaria y contraste municipal de fase 8

**`recarga_instalaciones_geo`**: una fila por instalación, clave `instalacion_id`.
Conserva todos los campos de `recarga_instalaciones`, incluidos textos y estados
históricos. Añade los siguientes; las reglas completas están en el
[informe espacial](RECARGA_ESPACIAL_SILVER.md).

| Campo | Tipo físico | Regla |
| --- | --- | --- |
| `geometria` | GEOMETRY EPSG:25830, admite nulo | Punto desde el CRS declarado EPSG:4258, XY explícitos; sin desplazar posiciones. |
| `estado_geometria` | VARCHAR | `admitida`, `coordenadas_o_proyeccion_no_admitidas` o `proyeccion_no_admitida`. Admisión geométrica no equivale a precisión certificada. |
| `codigo_provincia_declarada` | VARCHAR, admite nulo | Etiquetas exactas de provincia a `03`, `12`, `46`. |
| `numero_municipios_intersectados` | BIGINT | Número de recintos candidatos; incluye intersección con sus límites. |
| `codigo_municipio_espacial` | VARCHAR, admite nulo | Código solo cuando hay un recinto único. Se conserva incluso si discrepa de la declaración; no equivale por sí solo a asignación contrastada. |
| `codigo_municipio_declarado` | VARCHAR, admite nulo | Provincia y etiqueta normalizada coincidentes con un único código INE/IGN. Sin fuzzy ni código postal. |
| `nombre_municipio_espacial` | VARCHAR, admite nulo | Nombre INE del recinto único. El nombre publicado por MITECO permanece separado. |
| `estado_contraste_territorial` | VARCHAR | `concordante`, `municipio_discrepante`, `provincia_discrepante`, `provincia_no_reconocida`, `nombre_no_resuelto`, `limite_ambiguo`, `fuera_ambito` o `geometria_no_admitida`. |
| `distancia_municipio_declarado_m` | DOUBLE, admite nulo | Distancia mínima plana al recinto declarado resuelto, con geometría admitida. Diagnóstica, sin umbral de corrección. |
| `admitida_asignacion_municipal` | BOOLEAN | Solo `concordante`: geometría admitida, recinto único, provincia y municipio declarados concordantes. |

**`recarga_municipios_candidatos`**: clave `instalacion_id` + `codigo_municipio`,
ambos VARCHAR. Conserva todos los candidatos geométricos, sin admitir por defecto
una relación. **`entidad_municipio`** contiene solo las relaciones contrastadas
definidas en el apartado 10: `tabla_entidad=recarga_instalaciones_geo`,
`clave_entidad=instalacion_id`, `metodo_asignacion=interseccion_unica_y_nombre_oficial`
y `estado_asignacion=contrastada`.

**`incidencias_espaciales`**: `instalacion_id`, `campo`, `motivo`, VARCHAR.
La copia conserva 1.526 instalaciones y candidatos, 1.393 relaciones admitidas y
133 incidencias municipales. Los puntos y conectores siguen en las tablas de
fase 4, referenciados por instalación; no se multiplica su detalle por candidatos.

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
| `porcentaje_pesados` | decimal, admite nulo | `vehiculo_pesados_zp`; tanto por cien, confirmado en el modelo oficial. Mantiene el entero publicado sin extraer decimales de etiquetas. |
| `geometria` | geometría | `geom`, con EPSG:25830 declarado en la entrada. |
| `tipo_medida_descripcion`, `estado_tipo_medida` | texto, descripción admite nulo | Dominio del modelo oficial GVA. `F` no se reclasifica; vacío y código no documentado diferenciados. |
| `imd_origen`, `pesados_origen`, `estado_imd`, `estado_pesados` | texto | Valores originales y estados de conversión/rango. IMD cero conserva 0 y una señal de revisión. |
| `titular_origen`, `tipo_calzada_origen`, `pk_estacion` | texto | `titular`, `tipo_calzada`, `pk_estacion`; categorías y notación conservadas. |
| `identificador_origen`, `etiqueta_plano_origen` | texto | `id`, `label2_planos`; no sustituyen la clave del tramo ni las medidas publicadas. |
| `origen_id`, `capa_origen`, `fid_origen` | texto, texto, entero | Recurso con huella, capa anual y `fid` de la misma fila. |
| `estado_geometria` | texto | Admisión o incidencia geométrica; actualmente las 9.041 observaciones son admitidas. |

Los campos seleccionados existen en las 17 capas auditadas y `clau_tramo` no
tiene nulos en ellas. Las 9.041 observaciones están materializadas en la
[fase 5](TRAFICO_RED_SILVER.md). Se conservan años y cobertura original. No se suman años
como tráfico actual ni se equipara un tramo de aforo a un tramo IGN por su nombre.

## 7. Red viaria IGN

**`red_tramos`**: una geometría de tramo por copia provincial.
Clave validada: `provincia_origen` + `tramo_id`.

Campos: `provincia_origen` (texto, procedencia del paquete), `tramo_id` (texto,
`id_tramo`), `tipo_tramo_codigo` (texto, `tipo_tramo`), `tipo_tramo_descripcion`
(texto, `tipo_tramd`), `geometria` (geometría, `geom`). Otros atributos de tramo
solo se incorporarán si su uso y dependencia están comprobados.
Incluye `origen_id`, `capa_origen` y `fid_referencia` (mínimo `fid` entre las
asociaciones del padre, tras verificar igualdad de todos sus atributos seleccionados
y WKB), así como `estado_geometria`. Hay 1.118.309 filas por copia provincial;
cinco no admitidas tras la reproyección, conservadas con incidencia.

**`red_tramo_vial`**: una asociación tramo–vial por copia provincial.
Clave: `provincia_origen` + `tramo_id` + `vial_id`.

Campos: `provincia_origen`, `tramo_id` (`id_tramo`), `vial_id` (`id_vial`),
`codigo_vial` (`codigo`), `nombre_vial` (`nombre`), `tipo_vial_codigo` (`tipo_vial`)
y `tipo_vial_descripcion` (`tipo_viald`), todos textuales. Se añaden `origen_id`,
`capa_origen` y `fid_origen` para conservar la referencia de las 1.197.446 asociaciones.

La clave tramo–vial no se repite en las copias provinciales auditadas; `id_tramo`
sí se repite por sus asociaciones. Extraer una geometría por tramo exige comprobar
que las representaciones coinciden; un conflicto no se resuelve tomando la primera.
La provincia de procedencia no demuestra que una geometría esté enteramente
dentro de ella. Se transforma de EPSG:4258 a EPSG:25830 con XY explícitos,
conservando Z sin atribuir datum vertical. Se comprueban dimensión, vértices y
extremos Z para todos los tramos. Estas salidas no constituyen todavía una
red enrutable.

Las incidencias de fase 5 contienen `tabla`, `provincia_origen`, `capa_origen`,
`fid_origen`, `entidad_id`, `campo`, `valor_origen` y `motivo`. Una fila puede
producir más de una incidencia; las 107 incidencias afectan a 79 registros.

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
| `representacion` | texto | `punto` o `area` según la capa, sin sustituir polígonos por centroides. |
| `grupo_uso`, `estado_categoria` | texto, grupo admite nulo | Doce categorías seleccionadas, agrupadas en aparcamiento, parada viaria, comercio y alojamiento; las demás permanecen sin selección. Se comprueba concordancia de código. |
| `estado_geometria` | texto | Admisión o motivo de no admisión, sin reparar ni perder la referencia del original. |
| `geometria_origen_no_admitida_wkb` | binario, admite nulo | WKB original CRS84 si no es admisible para proyectar; no se interpreta como geometría EPSG:25830. Actualmente todos nulos. |
| `estado_ambito` | texto | `intersecta_cv`, `fuera_cv` o `no_evaluable`, respecto de la unión de recintos Silver. No asigna municipio. |
| `distancia_ambito_m` | DOUBLE, admite nulo | Distancia plana mínima diagnóstica: cero para intersección; no es recorrido ni umbral de exclusión. |
| `interes_para_revision` | booleano | Categoría seleccionada, geometría admitida e intersección con CV. No acredita disponibilidad o viabilidad de recarga. |

El esquema mínimo coincide en las capas de `pois` y `traffic` auditadas. Hay
repeticiones de `osm_id` incluso dentro de algunas de esas capas; por eso no se
usa como clave única del elemento ni como prueba de establecimiento único.
La [fase 6](POI_OSM_SILVER.md) conserva 269.287 elementos de `pois`, `traffic` y
`transport`, puntos y áreas. No se pierde ninguna fila de esas seis capas. Hay
17.794 elementos de interés dentro del ámbito y 519 exteriores conservados.
Geometrías transformadas de CRS84 a EPSG:25830; srs_id 100000 sigue siendo local.

**`poi_correspondencias`**: un par punto–área de la misma categoría seleccionada,
por intersección o igualdad del identificador publicado. Clave: `origen_punto` +
`fid_punto` + `origen_area` + `fid_area`; ambas referencias apuntan a `poi_elementos`.
Incluye `osm_id_punto`, `osm_id_area`, `categoria_origen`, `punto_intersecta_area`,
`coincide_id_publicado`, `coincide_nombre_normalizado`, `distancia_plana_m` y
`estado`. Este último es `posible_correspondencia_sin_fusion`. En la copia hay
77 pares por intersección; doce además coinciden en nombre normalizado. No se
restan pares a elementos ni se colapsan relaciones múltiples.

Las incidencias OSM contienen `origen_id`, `capa_origen`, `fid_origen`, `osm_id`,
`campo` y `motivo`. Actualmente tienen cero filas; los estados de ámbito y las
posibles correspondencias se documentan en sus tablas, no se confunden con errores.

## 9. Capacidad de demanda i-DE

**`capacidad_demanda`**: un registro publicado por identificador del punto de
conexión. Clave validada para esta copia: `punto_conexion_id`, sin vacíos ni
repeticiones en los 3.019 registros nacionales o los 423 seleccionados CV.
No se equipara automáticamente a una subestación única.

| Campo | Tipo lógico | Origen o regla |
| --- | --- | --- |
| `punto_conexion_id`, `nombre_punto_conexion` | texto | `Identificador del Punto de Conexión`, `Denominación del Punto de Conexión`. |
| `gestor_red`, `provincia_nombre_origen`, `municipio_nombre_origen` | texto | `Gestor de red`, `Provincia`, `Municipio`. |
| `subestacion_origen` | texto | `Subestación`. |
| `x_utm_origen`, `y_utm_origen` | texto | `Coordenada UTM X`, `Coordenada UTM Y`, con toda la precisión textual. Formato con coma comprobado; CRS declarado EPSG:25830 acreditado el 19-10. Los textos originales se conservan. |
| `nivel_tension_kv` | decimal, admite nulo | `Nivel de Tensión (kV)`. |
| `capacidad_firme_disponible_mw` | decimal, admite nulo | `Capacidad firme disponible (MW)`. |
| `capacidad_ocupada_mw` | decimal, admite nulo | `Capacidad de acceso firme de demanda ocupada (MW)`. |
| `capacidad_admitida_no_evaluada_mw` | decimal, admite nulo | `Capacidad de acceso firme admitida y no evaluada (MW)`. |
| `posiciones_ocupadas`, `posiciones_libres` | BIGINT, admiten nulo | Recuentos publicados no negativos; cada campo tiene 344 ausencias conservadas. |
| `compromiso_regulatorio_origen`, `nudo_0_asterisco_origen` | texto | Textos de las dos banderas publicadas, conservados literalmente. |
| `compromiso_regulatorio`, `nudo_0_asterisco` | BOOLEAN, admiten nulo | `0` → false y `1` → true, según instrucciones i-DE. Vacío → nulo; otro código → nulo e incidencia. |
| `comentarios_origen` | texto | `Comentarios`, incluidos vacíos. |
| `origen_id`, `registro_origen`, `codigo_provincia` | texto, BIGINT, texto | Recurso y huella, ordinal nacional antes de filtrar y código provincial por etiqueta exacta (`03`, `12`, `46`). |
| `fecha_referencia` | fecha, admite nulo | Nula en la ejecución histórica del 16-10. Acreditación posterior: publicación 04-09-2026 y periodo 2026-08 según regla mensual; día exacto de corte desconocido. No confundir estos conceptos. |
| `estado_fecha`, `estado_coordenadas` | texto | Estados históricos del 16-10: `no_acreditada` y `pendiente_crs`; la acreditación documental del 19-10 se conserva aparte, vinculada a la huella del original. Coordenadas vacías o con formato no admitido producen estado e incidencia específicos. |

Las cuatro medidas decimales son `DECIMAL(18,2)`: tensión positiva en kV y
capacidades no negativas en MW. Se conserva además el campo textual
`<nombre_medida>_origen`, también para posiciones. Cada uno de los ocho valores
tipados —cuatro medidas, dos posiciones y dos banderas— tiene
`estado_<nombre_campo>`: `informado`, `no_informado` o `error_conversion`.
No se redondea un exceso de precisión ni se admite agrupación de miles.
Los 17 campos originales quedan preservados, sin recortar nombres o comentarios.

La [fase 7](CAPACIDAD_DEMANDA_SILVER.md) documenta unidades y significado de
banderas. Nudo 0* no convierte un cero publicado en capacidad positiva.
No se suman capacidades de diferentes puntos o tensiones. La tabla no contiene
geometría ni municipio asignado. `incidencias` contiene `origen_id`,
`punto_conexion_id`, `campo`, `valor_origen`, `motivo` y `registro_origen`;
actualmente cero filas. El [informe i-DE](CAPACIDAD_DEMANDA_SILVER.md) distingue
estos estados históricos de la acreditación posterior de publicación, periodo
y CRS. La capa y relaciones aún no se han materializado.

La normalización numérica no acredita precisión posicional ni posibilidad de
conexión. El bloque original conserva sus estados históricos, complementados
por la capa siguiente; no se suman capacidades.

### 9.1. Capacidad de demanda espacial

Bloque `capacidad_demanda_espacial`, preparado el 19-10-2026. La capa
**`capacidad_demanda_geo`** conserva los atributos de la tabla original y añade
los campos siguientes. Clave: `punto_conexion_id`; 423 puntos, sin fusión de
coordenadas o subestaciones compartidas.

| Campo | Tipo lógico | Regla |
| --- | --- | --- |
| `estado_fecha_preparacion`, `estado_coordenadas_preparacion` | texto | Estados originales de la tabla del 16-10, renombrados para conservarlos. |
| `fecha_publicacion` | DATE | 2026-09-04, acreditada por identidad binaria del CSV histórico. |
| `periodo_referencia` | texto | 2026-08; mes informado derivado de la regla mensual CNMC. |
| `fecha_referencia` | DATE, nula | Conservada de la tabla original; no inventar un día exacto de corte. |
| `estado_fecha`, `estado_coordenadas` | texto | `periodo_mensual_acreditado` y `crs_acreditado`. La validez de la geometría se expresa aparte. |
| `crs_origen` | texto | EPSG:25830, declarado por el formato del proveedor para el ámbito peninsular. |
| `x_utm`, `y_utm` | DOUBLE | Conversión de los textos X/Y sin desplazar ni reproyectar. El texto con toda su precisión sigue conservado. |
| `geometria` | GEOMETRY('EPSG:25830') | Punto X/Y en metros, con CRS GeoParquet explícito. |
| `estado_geometria` | texto | `admitida`, `coordenadas_no_admitidas` o `geometria_no_admitida`. |
| `numero_municipios_intersectados` | BIGINT | Todas las intersecciones con recintos; no seleccionar por cercanía. |
| `codigo_municipio_espacial`, `nombre_municipio_espacial` | texto, admiten nulo | Solo cuando existe un único recinto intersectado. |
| `codigo_municipio_declarado` | texto, admite nulo | Resolución unívoca por provincia y nombres/variantes oficiales INE/IGN; sin fuzzy. |
| `estado_contraste_territorial` | texto | `concordante`, `geometria_no_admitida`, `fuera_ambito`, `limite_ambiguo`, `provincia_discrepante`, `nombre_no_resuelto` o `municipio_discrepante`. |
| `distancia_municipio_declarado_m` | DOUBLE, admite nulo | Distancia diagnóstica al recinto declarado; no regla de corrección o admisión. |
| `admitida_asignacion_municipal` | BOOLEAN | Verdadero solo si estado `concordante`. |

**`capacidad_municipios_candidatos`**: `punto_conexion_id` y
`codigo_municipio`, clave conjunta; todas las intersecciones. **`entidad_municipio`**:
una relación admitida por `punto_conexion_id`, con `codigo_municipio` y
`metodo_asignacion=interseccion_unica_y_nombre_oficial`. **`incidencias_espaciales`**:
`punto_conexion_id` y `motivo`; una fila por punto no admitido.
Resultado actual: 423 candidatos y 423 admitidos en 116 municipios; cero incidencias.
Las variantes separadas por `/` se admiten solo si identifican un código único
en la provincia. Los originales y la tabla previa no se reescriben.

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

La [validación conjunta](VALIDACION_CONJUNTA_SILVER.md) implementa seis salidas
complementarias. Cada ejecución conserva sus propios informes y no sustituye
las tablas ni los estados históricos de las fuentes:

| Tabla | Unidad y clave | Campos y significado |
| --- | --- | --- |
| `revision_recarga` | Una instalación discrepante; `instalacion_id`. | Nombre, dirección, municipios/códigos originales contrastados, distancia diagnóstica, `indicio_textual`, `estado_revision`, `codigo_municipio_validado` nullable, URL y motivo. Estados: `resuelta_documentalmente`, `pendiente_evidencia_documental_no_concluyente`, `pendiente_contraste_externo`. Un indicio no admite una relación. |
| `recarga_municipio_validado` | Una instalación con relación admitida; `instalacion_id`. | `codigo_municipio`, `metodo`, `url_evidencia` nullable. Combina la admisión previa y las decisiones documentales explícitas; no cambia las coordenadas ni el municipio publicado. |
| `relaciones_espaciales` | Una intersección entidad–municipio; `tabla_entidad` + `clave_entidad` + `codigo_municipio`. | `metodo`, `dimension_interseccion` SMALLINT, `longitud_interseccion_m` y `superficie_interseccion_m2` DOUBLE nullable. Longitud solo en dimensión 1; área solo en dimensión 2. Contactos de dimensión 0 tienen ambas medidas nulas. No son un reparto de indicadores. |
| `estado_relaciones_espaciales` | Una entidad espacial; `tabla_entidad` + `clave_entidad`. | `estado_geometria`, `numero_municipios` BIGINT y `estado_relacion`: `interseccion_unica`, `interseccion_multiple`, `sin_interseccion_cv` o `geometria_no_admitida`. Conserva todos los objetos de entrada de cada capa contrastada. |
| `cobertura_estadistica` | Tabla/periodo/segmento/municipio; clave con esos cuatro campos. | `registros`, `valores_informados`, `valores_ausentes`, todos BIGINT. `periodo` conserva fecha o año de origen como texto; `segmento` distingue sexo en población y un array JSON de nivel/indicador en renta. Solo diagnostica cobertura, no agrega valores estadísticos ni crea Gold. |
| `estado_fuentes` | Un bloque; `bloque`. | `estado`, `integracion_municipal` y `limitacion` VARCHAR. Separa preparación tabular de integración territorial admitida o pendiente. |

`clave_entidad` es un array JSON de textos con orden explícito: OSM
`[origen_id,fid_origen]`; aforos `[tramo_aforo_id,anio]`; red
`[provincia_origen,tramo_id]`; puntos i-DE `[punto_conexion_id]`. No se concatenan claves con un separador que pueda
aparecer en sus componentes. Las repeticiones entre copias provinciales y las
correspondencias OSM conservan su alcance, sin deduplicación física supuesta.
Todos los demás campos citados son VARCHAR salvo indicación contraria.
Las relaciones espaciales usan las geometrías completas en 2D, sin centroides
o asignación exclusiva de líneas/áreas. Un contacto de frontera queda registrado;
no acredita que se pueda sumar longitud, superficie o IMD entre municipios.

Los métodos de `recarga_municipio_validado` diferencian
`interseccion_unica_y_nombre_oficial`, `revision_documental_establecimiento`,
`revision_cartografica_portal_cartociudad` y
`revision_cartografica_via_cartociudad` y `revision_visual_y_documental`.
La revisión visual exige identificación explícita del recinto, fuente primaria
y evidencias fijadas por huella; acredita el municipio del emplazamiento, sin
certificar cada plaza. Un vial valida únicamente la referencia
municipal de la calle, sin acreditar número de portal ni posición del cargador.
La correspondencia textual es una decisión revisada, no un ajuste fuzzy.
Véase la [revisión de recarga](REVISION_RECARGA_SILVER.md).

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
comprobada. La fase 3 materializa parque, población y renta, separa PP000 y 12066,
conserva ausencias y verifica claves, cobertura y cifras de control. El siguiente
paso es recarga MITECO.
Las claves y dependencias que requieren comprobaciones de registros volverán a
validarse al preparar su fuente; no se presentan como unicidad universal garantizada.
Las entidades de las fases 4–7 están materializadas con los límites indicados;
las relaciones y la validación de fase 8 están materializadas con sus limitaciones
documentadas en el informe conjunto. Las incidencias conservadas no se convierten
en asignaciones o valores observados al cerrar Silver.
