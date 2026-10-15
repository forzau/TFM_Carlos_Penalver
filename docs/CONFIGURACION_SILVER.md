# Configuración técnica de Silver

Fecha: **15 de octubre de 2026**. Cierra las decisiones técnicas de la fase 1
del [plan](PLAN_SILVER.md), junto con el [diccionario](DICCIONARIO_SILVER.md).
Se han probado formatos y muestras de lectura. Posteriormente se han generado y
validado las tablas de la [fase 2, base territorial](BASE_TERRITORIAL_SILVER.md).
Las comprobaciones completas del resto se ejecutarán al preparar cada fuente.

## Herramientas y formatos

Se mantienen Python 3.12, DuckDB 1.5.0 y openpyxl 3.1.5. Se incorpora únicamente
la extensión oficial `spatial` de DuckDB, comprobada en Windows con versión
`8734819`. No se necesita instalar por separado GDAL, GeoPandas ni un servidor.
La extensión se guarda en `.venv/duckdb_extensions/`, fuera de Git. Su primera
instalación requiere Internet; después, las comprobaciones locales no descargan datos.

| Componente | Decisión |
| --- | --- |
| Tablas sin geometría | Parquet con compresión ZSTD y esquema explícito. |
| Capas espaciales | GeoParquet con compresión ZSTD, geometría WKB y CRS explícito en los metadatos. En la prueba DuckDB escribe GeoParquet 1.0.0. |
| Consulta y transformación | DuckDB; la base de trabajo puede ser temporal y no constituye otra copia maestra obligatoria. |
| Metadatos de ejecución | JSON junto a las salidas: entradas y huellas Bronze, reglas/código, tipos, CRS, fecha UTC, recuentos e incidencias. |
| Ubicación prevista | `resultados/silver/`, fuera de Git. El código y las reglas sí se versionan. |

Parquet permite leer columnas sin cargar un archivo completo y conserva tipos
que CSV no expresa. No se duplicarán todas las salidas en CSV o GeoJSON; esas
exportaciones se harán cuando un consumidor concreto las necesite.
Véanse la [documentación de Parquet de DuckDB](https://duckdb.org/docs/current/data/parquet/overview)
y su [tipo de geometría con CRS](https://duckdb.org/docs/current/sql/data_types/geometry).

La escritura de producción deberá comprobar esquema, claves y recuentos antes de
dar una ejecución por válida. Se conservará la ejecución anterior hasta validar
la nueva; una salida parcial no se anunciará como Silver preparada.

## Tipos físicos y precisión

| Variables del diccionario | Tipo físico acordado | Regla |
| --- | --- | --- |
| Códigos, identificadores, nombres y categorías | `VARCHAR` | Códigos textuales con su longitud; sin inferencia numérica automática. |
| Recuentos y ordinales de origen | `BIGINT` | Sin fracciones; un valor no entero se señala, no se redondea. |
| Año | `SMALLINT` | Validar el periodo contra la fuente. |
| `valor_eur`, `potencia_maxima_kw`, tensión en kV y capacidades en MW | `DECIMAL(18,2)` | Dieciséis cifras enteras y dos decimales; conserva los valores observados sin convertirlos primero a coma flotante. |
| IMD y porcentaje de pesados, cuando su significado esté contrastado | `DECIMAL(18,2)` | El almacenamiento no decide si un campo es porcentaje ni convierte su escala. |
| PK de aforos | `VARCHAR` | Se han observado valores como `0+000`; conservar la notación hasta justificar una conversión y su unidad. |
| Coordenadas y medidas calculadas de geometría | `DOUBLE` | 64 bits, sin redondear coordenadas a un número fijo de decimales. Las distancias serán metros y las áreas, metros cuadrados. |
| Fecha acreditada sin hora | `DATE` | Sin completar una hora inexistente. |
| Modificación MITECO | `TIMESTAMP` | Conservar fecha y hora; la zona no está acreditada y no se inventa una conversión a UTC. |
| Instantes técnicos de descarga/proceso | `TIMESTAMPTZ` | Instante UTC; representación textual ISO 8601 en JSON. |
| Geometría admitida | `GEOMETRY('EPSG:25830')` | Transformar coordenadas desde su CRS acreditado antes de asignar este tipo. |

El contraste secuencial de los textos encuentra: 2.761.752 valores numéricos de
renta, todos sin decimales; 121.986 valores de población enteros; 43.610 potencias
MITECO con dos decimales; tensión i-DE con hasta un decimal y sus tres capacidades
seleccionadas con hasta dos. Los 9.041 registros de las 17 capas de aforos tienen
IMD y campo de pesados enteros en la copia. Estos resultados describen los datos
leídos, sin atribuir precisión estadística adicional por almacenar dos decimales.

Los textos originales necesarios para interpretar símbolos o errores seguirán
disponibles. Separadores y unidades se interpretarán por fuente: el punto de
millares de INE no es el punto decimal de una coordenada. Antes del cast se
comprobarán escala y rango: un cast a `DECIMAL` puede redondear, por lo que no
basta con que termine sin error. Si aparece un valor fuera de la precisión
acordada, se conservará como incidencia y se revisará el tipo antes de admitirlo.
La elección sigue la [distinción de DuckDB entre decimales exactos y coma flotante](https://duckdb.org/docs/current/sql/data_types/numeric).

Las coordenadas MITECO muestran entre cinco y nueve decimales; no se reducirán
a seis. Sus 43.610 marcas de modificación incluyen hora distinta de medianoche:
almacenarlas solo como fecha perdería información. No son fechas de instalación.

## Lectores y conservación de identificadores

| Entrada | Lectura acordada |
| --- | --- |
| XLSX DGT e INE | openpyxl en modo de solo lectura. |
| CSV INE e i-DE | Lectura con separador y codificación conocidos y columnas textuales antes de convertir; DuckDB o biblioteca estándar según la transformación. |
| TXT nacional DGT | Lectura secuencial o por bloques; nunca cargarlo completo en memoria Python. |
| CSV MITECO | Decodificación UTF-16LE y lector controlado que compruebe 27 campos; revisar la semántica de las comillas antes de admitirlo. No usar `ignore_errors` para saltar filas. |
| GeoPackage | SQLite `mode=ro` para recuperar atributos, `fid` y geometría de la misma fila, por bloques. Extraer WKB estándar y decodificar con `ST_GeomFromWKB`; resolver el CRS desde los metadatos. |
| GeoJSON IGN | `ST_Read`, conservando identificadores y propiedades anidadas necesarias; comprobar su correspondencia con la copia al preparar la base territorial. |

`ST_Read_Meta` permite consultar los metadatos espaciales. `ST_Read` lee
GeoPackages, pero en la versión probada no expone su `fid` como columna. No se
reconstruirá ese identificador mediante orden de lectura ni cruzando por `osm_id`,
que tiene repeticiones. La extracción SQLite/WKB mantiene la fila original y
rechaza cabeceras no admitidas, truncadas o con SRS distinto al de su capa.
Su alcance es geometría GeoPackage estándar; una extensión no admitida quedará
como incidencia. Referencias: [funciones espaciales de DuckDB](https://duckdb.org/docs/current/core_extensions/spatial/functions)
y [codificación binaria de GeoPackage](https://www.geopackage.org/spec/#gpb_format).

Una prueba exploratoria con una vista temporal de GDAL coincidió con un cierre
inesperado de Python en Windows. Esa variante no forma parte del lector elegido.
La captura no permite atribuir una causa interna; las pruebas posteriores de la
ruta SQLite/WKB y del lector GeoJSON terminaron con código de salida cero.

## Referencia espacial y ejes

Se adopta **ETRS89 / UTM huso 30N, EPSG:25830**, para las geometrías de trabajo
admitidas y las operaciones planas de distancia, longitud y superficie. Coincide
con los aforos y con la referencia que el ICV publica para su
[cartografía oficial continua de toda la Comunitat Valenciana](https://dadesobertes.gva.es/va/dataset/cartografia-oficial-de-la-comunitat-valenciana-a-escala-1-50-000-del-institut-cartografic-valen5).
Es una decisión práctica para este ámbito regional; el huso UTM tiene un ámbito
nominal y la proyección introduce distorsión, especialmente hacia su borde oriental.
Al definir los umbrales de Gold se revisará si esa aproximación afecta a la decisión.
No se presentan áreas como superficies oficiales ni distancias planas como rutas.

| Fuente espacial | Interpretación de entrada y admisión |
| --- | --- |
| Aforos GVA | EPSG:25830, X este / Y norte, metros. La muestra real es `MULTILINESTRING` aunque la declaración de capa es línea simple: no forzar un subtipo ni descartar componentes. |
| Red IGN | EPSG:4258; geometrías leídas como longitud / latitud, con Z. Transformar el plano horizontal a 25830 conservando Z; no se acredita ni transforma aquí un datum vertical. |
| OSM | WKT de la copia identifica OGC:CRS84: longitud / latitud WGS84. El `srs_id=100000` es interno del GeoPackage y no se enviará como `EPSG:100000` al transformador. |
| Recintos IGN GeoJSON | Interpretar como OGC:CRS84, longitud / latitud, por el contrato GeoJSON y el contraste adicional descrito abajo. El lector lo etiqueta como EPSG:4326; se controla el orden XY expresamente. |
| MITECO | Columnas longitud / latitud legibles; admisión geométrica pendiente de contrastar el datum del recurso en su fase. Conservar valores y texto necesario, sin declararlas ya integradas. |
| i-DE | X/Y UTM conservadas como texto hasta acreditar formato, huso y datum. Sin geometría admitida por ahora. |

La copia GeoJSON IGN no tiene miembro `crs`, mientras las capacidades WFS declaran
EPSG:4258 como referencia por defecto. No se ha confundido esa declaración con el
CRS de cualquier formato de salida: [GeoJSON RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946#section-4)
define longitud / latitud WGS84, equivalente a OGC:CRS84. Como contraste, se ha
consultado el mismo municipio `34100303075` al WFS con `srsName=OGC:CRS84`
explícito: su geometría es idéntica a la conservada en Bronze. Otra respuesta GML
solicitada en EPSG:4258 declara ese CRS expresamente. Este contraste apoya la
interpretación adoptada; no es una validación geodésica independiente de los 542
recintos. Las respuestas pequeñas y sus URL/huellas se guardan en el perfil local.

En todas las llamadas a `ST_Transform` se indicarán CRS de origen y destino y
`always_xy := true`: X es longitud/este y Y, latitud/norte. Etiquetar una geometría
con otro CRS no transforma sus coordenadas. Antes de escribir GeoParquet se
comprobará que los metadatos incorporan el CRS de las coordenadas realmente escritas.
Las operaciones de proximidad serán 2D; conservar Z no convierte una distancia
plana en distancia sobre el terreno. No se modifican coordenadas Bronze.

## Reproducción y alcance del cierre

Desde la raíz del proyecto, después de instalar `requirements.txt` y disponer de
las copias Bronze:

```powershell
.\.venv\Scripts\python.exe src/comprobar_entorno_silver.py --instalar-spatial
.\.venv\Scripts\python.exe src/comprobar_entorno_silver.py
```

El primer comando instala la extensión oficial si hace falta y ejecuta las
comprobaciones; las siguientes ejecuciones pueden usar solo el segundo. Se
escribe `resultados/diseno_silver/entorno.json`, sin publicar registros de entrada.
La prueba temporal de Parquet se elimina al terminar.

Se han comprobado conservación de código `03001`, decimal exacto, nulo frente a
cero, fecha e instante UTC; CRS GeoParquet explícito y Z; control de ejes y vuelta
de proyección; muestras de ocho capas GeoPackage y un GeoJSON. Las dos pruebas
unitarias del extractor cubren ambos órdenes de bytes, los cinco tamaños de
envolvente estándar y rechazo de cabeceras, SRS o contenido no admitidos. La suite
completa pasa **22 pruebas**. Los 29 originales conservan tamaño y modificación;
la huella completa del GeoPackage OSM también coincide con el manifiesto Bronze.

La fase 1 queda cerrada como diseño y compatibilidad básica. La **fase 2** ya
dispone de una base territorial de 542 municipios validada y materializada.
Siguen pendientes los controles de las restantes fuentes, escala semántica de
algunos campos, referencias espaciales de MITECO/i-DE y decisiones de Gold.
No se ha elegido cuadrícula, año común, modelo ni distancias por red.
