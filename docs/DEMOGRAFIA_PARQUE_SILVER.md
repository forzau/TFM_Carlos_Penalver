# Parque, población y renta en Silver

Fecha: **16 de octubre de 2026**. Preparación de la fase 3 del
[plan de Silver](PLAN_SILVER.md), sobre la
[base municipal validada](BASE_TERRITORIAL_SILVER.md).
Estado: **fase 3 preparada y validada**, con las limitaciones de cobertura y
temporalidad de las fuentes conservadas.

## Fuentes y unidades de observación

Se utilizan cinco entradas del catálogo Bronze: TXT DGT de diciembre de 2025,
Excel municipal DGT 2025 y su ficha PDF, CSV de población y CSV de renta.
Sus tamaños y SHA-256 se contrastan con el manifiesto conservado antes y después
del proceso. La tabla municipal de la fase 2 se comprueba contra su propio
informe Silver. No se descargan versiones nuevas ni se modifica ningún original.

| Salida | Qué representa una fila | Periodos conservados |
| --- | --- | --- |
| `parque_municipal` | Indicadores de parque de un municipio. | 31-12-2025, según la ficha municipal. |
| `parque_sin_municipio` | Registro provincial PP000 sin municipio especificado; no es un total provincial. | 31-12-2025. |
| `parque_detalle_observado` | Un registro del TXT, sin supuesto identificador individual de vehículo. | Mes 2025-12; no se inventa un día de referencia. |
| `poblacion_municipal` | Municipio, sexo y año. | 2021–2025. |
| `renta_territorial` | Territorio, nivel municipal/distrito/sección, indicador y año. | 2015–2023, los seis indicadores originales. |
| `renta_codigos_historicos` | Observaciones del código 12066, fuera de la referencia municipal vigente. | Periodos originales y motivo de separación. |
| `incidencias` | Conversión numérica no admitida, con tabla, origen, registro, campo y valor leído. | Referencia a la observación original. |

## Resultado de la ejecución

Ejecución validada: `resultados/silver/demografia_parque/20261016T105307373142Z/`.
Contiene siete archivos Parquet, `informe.json` y un contraste complementario
de las salidas. El indicador `actual.json` señala esta ejecución.

| Tabla | Filas |
| --- | ---: |
| Parque municipal | 542 |
| Parque sin municipio, PP000 | 3 |
| Detalle DGT observado en CV | 4.124.363 |
| Población municipal | 8.130 |
| Renta territorial vigente | 262.710 |
| Renta del código histórico 12066 | 54 |
| Incidencias de conversión | 0 |

Se han leído 38.641.165 registros nacionales DGT, 121.995 de población y
3.009.312 de renta. Los registros ajenos al ámbito se excluyen por territorio;
las 54 observaciones históricas se conservan aparte. No se han encontrado claves
duplicadas en las salidas ni errores de conversión.

El parque municipal suma **4.124.317 vehículos**; las agrupaciones PP000 aportan
otros **46** (8, 3 y 35 por provincia), reconciliando los 4.124.363 registros del
TXT. La igualdad también se comprueba por provincia. Los 106 municipios con
código publicado en el detalle coinciden en su recuento con el Excel; los
**845.077 registros sin municipio publicado** permanecen nulos, sin asignarlos a
municipios pequeños ni a PP000. Distintivo 0 suma **78.180**, cifra que coincide
con la categoría textual `CERO` del TXT, también en los municipios observados.
Esta coincidencia no convierte el indicador en un desglose BEV/PHEV.

Población tiene 542 municipios por cada combinación de año y sexo, sin valores
ausentes. Total reconcilia con Hombres + Mujeres. Renta conserva:

| Nivel | Observaciones | Valores no informados conservados |
| --- | ---: | ---: |
| Municipio | 29.268 | 1.004 |
| Distrito | 41.526 | 1.064 |
| Sección | 191.916 | 5.046 |
| **Total vigente** | **262.710** | **7.114** |

Las 54 filas de `12066` están todas sin valor informado y permanecen en la tabla
histórica. Los nulos vigentes siguen identificados como tales; no se eliminan ni
se contabilizan como errores de conversión.

Son tablas separadas por entidad. La preparación no construye una tabla ancha
de indicadores ni selecciona un año común para Gold.

## Reglas aplicadas

### Parque DGT

El Excel municipal conserva `Parque Total`, `Distintivo 0` y `Electrificado`,
con códigos textuales y recuentos enteros. **Distintivo 0 sigue siendo la
aproximación acordada**: no se equipara a BEV + PHEV ni se deduce un desglose por
resta. Las filas PP000 se mantienen en una tabla propia.

El TXT se procesa secuencialmente mediante DuckDB: solo los atributos necesarios
se materializan en una base temporal en disco, con dos hilos y un límite de 1 GB
para la memoria de su motor. Este límite no cubre todo el proceso Python.
No se carga el archivo completo en memoria Python. Tras seleccionar las tres
provincias, se mantienen los registros con municipio no informado como nulos.

`registro_origen` es el ordinal del registro nacional después de la cabecera,
asignado antes del filtro territorial, con lectura no paralela. Junto a
`origen_id`, que identifica la copia por su huella, permite rastrear observaciones.
No es el identificador de un vehículo. Dos registros con los mismos atributos
se conservan como dos registros, sin deduplicación.

Los valores de `TIPO_DGT`, `PROPULSION`, `CATELECT` y `TIPO_DISTINTIVO` se
conservan tal como los publica la fuente. En particular, `TIPO_DGT` contiene
denominaciones como `TURISMOS`; el sufijo `_codigo` del esquema no significa que
se haya creado una codificación numérica ni una reclasificación nueva.

### Población y renta

Los CSV se leen con codificación y separador explícitos, comprobando cabeceras
y ancho de todos los registros. La selección valenciana se convierte a tipos
explícitos mediante archivos temporales, que se eliminan al terminar.

El punto se interpreta como separador de miles del INE y la coma como separador
decimal. Se usa `Decimal` para validar las magnitudes exactas: una fracción no
entera en población, un desbordamiento o una renta con más de dos decimales queda
como nulo con estado `error_conversion` y una incidencia, sin redondeo silencioso.
El texto `valor_origen` se conserva, también cuando es vacío.

Los símbolos vacío, `.`, `..` y `...` se clasifican como `no_informado`. No se
atribuye una causa de protección o no aplicabilidad sin evidencia específica.
**Cero sigue siendo un valor informado**; no se imputan ausencias.

Población mantiene Total, Hombres y Mujeres como categorías distintas. Renta
conserva el nivel y el código territorial completo, comprobando los prefijos de
municipio/distrito/sección. No se suman estos niveles ni los seis indicadores.
`registro_origen` conserva el ordinal del CSV nacional y la procedencia del
archivo se registra por salida.

El código `12066` se separa sin convertirlo a `46902`, que ya existe en la copia.
El motivo es su ausencia de la referencia municipal de 2025; la separación no
equivale a convertir valores ausentes en cero ni a inventar otro municipio actual.
La renta procede de la copia local identificada por su huella y no del descargable
remoto que se comprobó diferente durante la auditoría.

## Comprobaciones y conservación

Se comprueban claves completas y únicas por tabla, correspondencia municipal,
jerarquía de renta y recuentos antes y después de la conversión. Se contrasta el
detalle DGT con el parque municipal y las filas PP000, y el recuento observado de
cada municipio informado con su registro del Excel. Población contrasta cobertura
por año/sexo y la igualdad Total = Hombres + Mujeres cuando los valores están informados.

Las salidas se escriben en Parquet ZSTD y se releen, comparando todos los valores
y tipos con las tablas preparadas. El informe conserva entradas y huellas,
referencia municipal usada, código por SHA-256, versión del motor, esquemas,
recuentos, estados y limitaciones. Cada ejecución tiene carpeta propia bajo
`resultados/silver/demografia_parque/`; `actual.json` se actualiza al finalizar la
validación. Una ejecución fallida no sustituye la anterior.

Datos, temporales e informes detallados están excluidos de Git. El código, las
pruebas, el diccionario y las reglas de este documento se versionan.

## Reproducción

Desde la raíz, con el entorno del README y las copias locales disponibles:

```powershell
.\.venv\Scripts\python.exe src/preparar_demografia_parque.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Ajustar el argumento al manifiesto conservado. La fase necesita la base municipal
Silver de fase 2 y espacio temporal en disco; no necesita la extensión espacial
para estas transformaciones tabulares ni nuevas dependencias Python.

La suite completa supera **37 pruebas**, sin omisiones en este equipo. Ocho
nuevas comprueban precisión y símbolos numéricos, códigos y jerarquía territorial,
conservación de registros DGT con atributos repetidos, separaciones históricas,
claves duplicadas, recuentos no válidos y acceso a la referencia dentro de su carpeta.
La ejecución real también verifica las entradas antes/después y la igualdad
completa de valores y tipos tras exportar los siete Parquet. Los temporales de
lectura, la base de trabajo y su desborde se eliminan al cerrar el proceso.

## Alcance

Las series mantienen sus fechas originales. La referencia de códigos INE es de
2025, y los recintos de la fase 2 proceden de una consulta de 2026: esto no acredita
igualdad histórica de todos los territorios. No se agregan renta de distritos o
secciones como si fueran cifras municipales ni se acredita aquí su cartografía.

La preparación no estima recargas reales, adopción futura ni demanda efectiva,
y no reconstruye el detalle municipal suprimido del TXT. La selección temporal,
la unidad final del producto y sus indicadores se decidirán en Gold.
El siguiente bloque es la **fase 4: recarga existente MITECO**.
