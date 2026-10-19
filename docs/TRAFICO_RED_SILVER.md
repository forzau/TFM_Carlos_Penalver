# Aforos y red viaria en Silver

Fecha: **16 de octubre de 2026**. Fase 5 del [plan de Silver](PLAN_SILVER.md).
Se preparan los aforos anuales GVA y la geometría de tramos IGN separada de sus
asociaciones con viales. Se mantienen sus identificadores y cobertura propios.

## Entradas y alcance

Las diez entradas del [catálogo Bronze](CATALOGO_BRONZE.md) implicadas son
`Fuentes/Trafico.gpkg` y, para cada provincia, `red_viaria.gpkg`,
`atributos_gpkg.csv` y `leeme_RT_Prov_gpkg.txt`. Tamaño y SHA-256 se comprueban
contra el manifiesto antes y después. No se modifican originales ni se sustituyen
por descargas actuales. Los otros modos de transporte de los paquetes IGN no
forman parte de esta preparación viaria.

Los GeoPackages se leen con SQLite en modo de solo lectura, manteniendo juntos
`fid`, atributos y geometría de cada fila. Se comprueban campos, SRS y autoridad
EPSG del contenedor y de la cabecera geométrica. Se extrae WKB estándar y se carga
por bloques mediante CSV temporales, con esquema, comillas y marcador de nulo
explícitos. Un texto vacío sigue siendo distinto de un nulo. No se utiliza el
identificador de negocio para reconstruir filas ni se pierde `fid` con otro lector.

## Aforos GVA

**`aforos_tramo_anio`** conserva las **9.041 observaciones** de las 17 capas
`Aforos2009`–`Aforos2025`. Clave: `tramo_aforo_id` + `anio`; el identificador
mantiene sus ceros iniciales. El ordinal `fid_origen`, la capa y el recurso con
su huella conservan la trazabilidad.

Según la [ficha oficial de aforos](https://dadesobertes.gva.es/dataset/intensidad-media-diaria-anual-imd-de-trafico-por-tramos-red-autonomica-de-carreteras-2009-2025),
la IMD es la media diaria anual de vehículos que atraviesan una sección, expresada
en vehículos/día. No es un número de usuarios únicos ni de vehículos eléctricos.
El [modelo oficial de datos, páginas 1–2](https://icvficherosweb.icv.gva.es/04/geonetwork/definicion_datos/0902_IMD_catvias_autonoma_mdatos.pdf)
confirma que `vehiculo_pesados_zp` expresa tanto por cien y distingue estos tipos:

| Código | Significado documentado |
| --- | --- |
| `1a`, `2a` | Primaria y secundaria, con campañas de medición periódicas. |
| `C` | Cobertura, mediante una toma puntual anual. |
| `P` | Permanente. |
| `R` | Reforzada. |
| `Est` | Estimada a partir de datos reales anteriores. |
| `Eix` | Salida; remite a la tipología de la estación principal. |
| `Dip` | Diputación; remite a la tipología de la estación principal. |

Se conservan código, descripción y estado, sin reducirlos a una clasificación
binaria de medido/estimado que atribuya una metodología no acreditada a los ramales.
Los **dos códigos `F`** de 2010 no aparecen en el modelo consultado y permanecen
como `codigo_no_documentado`. Otros **55 valores vacíos** de 2011 y 2014 quedan
`no_informado`. No se reclasifican por semejanza con otro código.

IMD y porcentaje se convierten exactamente a `DECIMAL(18,2)`, sin redondear una
precisión excesiva. Se mantienen los textos de origen y estados. Los **45 valores
IMD iguales a cero** se conservan y señalan para revisar su uso; el cero publicado
no acredita ausencia real de tráfico. Un porcentaje fuera de 0–100 conservaría
su texto, un valor numérico nulo y la incidencia.

Los porcentajes del campo están publicados como enteros. La etiqueta del plano
puede contener un decimal diferente, por ejemplo `19` frente a `18,6%` en un tramo
de 2025. Se mantiene `etiqueta_plano_origen`; no se recuperan ni sustituyen cifras
a partir de un texto pensado para rotulación. Almacenar dos decimales no aumenta
la precisión del porcentaje publicado.

Se conservan carretera, titular, tipo de calzada y los tres PK como texto,
incluida la notación `0+000`. No se convierten en distancias medidas de forma
automática. La geometría original se mantiene en **EPSG:25830**, con admisión de
líneas simples o múltiples; la declaración LINESTRING del contenedor no describe
por sí sola todos los objetos encontrados.

La cobertura anual varía entre **488 y 614 observaciones**; 2025 contiene **513**.
El informe compara claves comunes de años consecutivos, carretera/PK y WKB.
Un WKB distinto demuestra una representación distinta, sin acreditar por sí solo
un cambio físico de la carretera. No se presupone un panel fijo, no se suman años
como tráfico actual y no se extrapola la cobertura a todas las vías de la comunidad.
Por ejemplo, 2024 y 2025 comparten 508 claves, con 82 diferencias textuales de
carretera/PK y 484 diferencias de WKB. Son controles de representación y atributos,
sin afirmar que hayan cambiado físicamente 484 tramos.

## Red viaria IGN

La documentación local explica que `rt_tramo_vial` resulta de unir tramos con
viales mediante una tabla de asociaciones. Se separan:

| Salida | Una fila representa | Filas | Clave |
| --- | --- | ---: | --- |
| `red_tramos` | Un tramo dentro de una copia provincial. | 1.118.309 | `provincia_origen`, `tramo_id` |
| `red_tramo_vial` | Una asociación tramo–vial del paquete. | 1.197.446 | `provincia_origen`, `tramo_id`, `vial_id` |

| Copia provincial | Tramos | Asociaciones | Filas adicionales por asociación |
| --- | ---: | ---: | ---: |
| Alicante | 380.929 | 414.419 | 33.490 |
| Castellón | 224.215 | 236.418 | 12.203 |
| Valencia | 513.165 | 546.609 | 33.444 |

Las **79.137 asociaciones adicionales** se conservan. Para extraer cada padre se
agrupan únicamente representaciones idénticas en geometría y atributos
seleccionados de tramo. Si un identificador produce dos padres distintos, la
preparación se detiene; no se elige una primera geometría. `fid_referencia` es el
menor `fid` de las asociaciones idénticas del tramo y sirve como referencia
técnica; cada asociación conserva además su propio `fid_origen`.

Los campos seleccionados del tramo son identificador, tipo y descripción. En la
relación se mantienen identificador del vial, código, nombre, tipo y descripción.
Los demás atributos siguen en Bronze, recuperables por procedencia y `fid`.
Los identificadores son texto; no se deducen códigos municipales de ellos.

La referencia de origen **EPSG:4258** se transforma a **EPSG:25830** con ejes XY
explícitos. Se comprueban dimensión, número de vértices y extremos Z de todos los
tramos antes y después, además de una prueba de los valores Z por vértice en una
geometría controlada. Se conserva Z sin atribuir datum vertical ni interpretar
las longitudes planas como distancias sobre el terreno.

La provincia identifica el paquete, no garantiza contención espacial. El informe
contrasta identificadores compartidos entre copias y sus WKB de origen. No se
fusionan por identificador ni por proximidad; cualquier repetición entre paquetes
se mantiene explícita para revisar las relaciones y agregaciones posteriores.
Las cifras de la tabla cuentan tramos por copia, sin afirmar que todos sean
elementos físicos distintos en el conjunto regional.
En estas copias no aparecen identificadores de tramo compartidos entre provincias;
esto no descarta coincidencias físicas con identificadores diferentes.

Se admiten **1.118.304 geometrías proyectadas**; las otras **cinco**, todas de
Castellón, quedan inválidas y con longitud plana cero. En origen son segmentos
con diferencias XY del orden de `1e-16` grados, que colapsan a XY idénticos al
proyectarse en coma flotante. Se conservan geometría, Z, asociaciones e incidencia,
sin alargar, desplazar ni borrar el segmento. Se excluyen de la admisión para
operaciones métricas mediante `estado_geometria`, no mediante pérdida de filas.

El contraste puntual del 19-10-2026 confirma dos vértices en cada segmento,
diferencias X de entre `1,11e-16` y `3,33e-16` grados y diferencias Y cero en
origen. La prueba de `ST_MakeValid` sobre las cinco geometrías proyectadas,
realizada solo en memoria, devuelve **POINT** en los cinco casos: recupera
validez geométrica, pero no un tramo lineal. No se aplica esa conversión a
Silver. Una reconstrucción lineal requiere evidencia adicional del proveedor o
un estudio explícito de los nodos y tramos vecinos; no se deduce de la longitud
nula. La exclusión métrica no acredita por sí sola que sean irrelevantes para
la conectividad de una futura red de rutas. El diagnóstico se conserva en
`resultados/revision_ign/20261019/diagnostico_cinco.json`, fuera de Git.

**Criterio vigente, 19-10-2026:** conservar estos cinco registros con su incidencia
y excluir sus geometrías de los cálculos métricos y de los cruces que requieren
una línea admitida. Se aplaza su reparación o reconstrucción; el tratamiento ya
está aplicado mediante `estado_geometria`, sin borrar registros o asociaciones.
Reabrir la revisión si se incorpora una edición oficial corregida o se necesita
validar su función en la conectividad de una futura red de rutas.

**Estas salidas no constituyen una red enrutable.** No se han construido nodos,
resuelto conexiones o comprobado restricciones de circulación. Tampoco se unen
aforos GVA con tramos IGN por el nombre de carretera. Edición exacta IGN y
temporalidad de su cartografía siguen sin acreditar; `alta_db` es fecha de
almacenamiento y no se utiliza como año de observación.

## Calidad, salidas y reproducción

Se comprueban claves, integridad tramo–vial en ambos sentidos, recuentos frente
a Bronze, geometrías y estados numéricos. Las incidencias identifican tabla,
capa, provincia cuando proceda, `fid`, entidad, campo, texto y motivo. Señalar
un registro no lo elimina ni lo convierte en una observación sin tráfico.
Hay **107 incidencias sobre 79 registros**: 102 en 74 observaciones de aforos
(45 IMD cero, 55 tipos vacíos y dos `F`) y cinco en tramos IGN. Un registro puede
producir más de una incidencia. No hay errores de conversión numérica.

Las cuatro salidas son `aforos_tramo_anio.parquet`, `red_tramos.parquet`,
`red_tramo_vial.parquet` e `incidencias.parquet`. Se escriben con compresión ZSTD;
las dos capas llevan metadatos GeoParquet con EPSG:25830. Se releen para contrastar
tipos, todos los atributos y el WKB exacto de la geometría exportada.
Las sumas de longitud del informe son controles de las representaciones almacenadas;
en aforos acumulan años y no representan una longitud única de red actual.
La suite completa pasa **53 pruebas, sin omisiones**; las nueve nuevas cubren
separación de asociaciones, geometría y Z, precisión, nulos/textos, incidencias,
claves, relaciones, CRS y protección de salidas existentes.

```powershell
.\.venv\Scripts\python.exe src/preparar_trafico_red.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
```

Se necesitan las copias originales y la extensión `spatial` ya instalada, según
el README. No se necesitan descargas ni dependencias nuevas. Ajustar la ruta del
manifiesto al equipo utilizado. La base temporal usa DuckDB 1.5.0 con formato de
almacenamiento compatible con v1.5.0 para admitir geometrías con CRS, memoria del
motor limitada a 1 GB y dos hilos. Este límite no incluye toda la memoria Python.

La ejecución validada `20261016T115524872944Z` queda señalada por `actual.json`
con estado `preparada_con_limitaciones`. Las cuatro salidas tienen 9.041,
1.118.309, 1.197.446 y 107 filas, respectivamente. Sus tamaños son 65.867.368,
316.228.826, 8.819.497 y 2.634 bytes; las huellas completas están en el informe.

Cada ejecución crea una carpeta bajo `resultados/silver/trafico_red/`. Solo tras
validar tablas, informe y huellas se actualiza `actual.json`. Las ejecuciones
anteriores se conservan y los temporales se eliminan. Datos e informe detallado
quedan fuera de Git; se versionan código, pruebas, reglas y este documento.
El siguiente bloque es la **fase 6, puntos de interés OSM**; la integración
espacial MITECO sigue pendiente de acreditar su datum.
