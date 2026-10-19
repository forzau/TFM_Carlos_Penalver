# Relaciones y validación conjunta de Silver

Fecha: **19 de octubre de 2026**. **Fase 8 cerrada operativamente con limitaciones**.
Las ejecuciones vigentes por fuente están verificadas y las relaciones
territoriales materializadas, incluida la capa complementaria i-DE con 423
relaciones municipales admitidas en 116 municipios;
52 asignaciones municipales de recarga permanecen pendientes. Gold no realizado.

## Entradas y alcance

`src/validar_silver.py` lee los ocho bloques Silver existentes mediante sus
indicadores `actual.json`: base territorial; parque/población/renta; recarga
tabular; tráfico/red; OSM; capacidad i-DE histórica; recarga espacial; y capacidad
i-DE espacial.

Comprueba los 30 Parquet contra los informes: huellas SHA-256, tamaño, esquema,
recuento y claves de entidad. Contrasta también los metadatos GeoParquet con
EPSG:25830, las dependencias Silver conservadas y los manifiestos Bronze.
Verifica de nuevo las entradas al terminar. No exige que la marca de modificación
local coincida entre equipos ni compara el código actual con el de una ejecución
histórica como si hubiera sido regenerada. Las huellas del código ejecutado
quedan registradas en el nuevo informe.

La trazabilidad hacia Bronze se hereda de las preparaciones verificadas: esta
fase no vuelve a recorrer el TXT nacional DGT ni certifica de nuevo la integridad
de todos los originales. Conserva las siete preparaciones previas y añade cuatro salidas i-DE; verifica
también sus copias de evidencia y correspondencia con el CSV acreditado.

## Revisión de las discrepancias MITECO

Se inspeccionan los 133 registros discrepantes: nombre de instalación, dirección,
municipio declarado, municipio espacial y distancia diagnóstica al recinto
declarado. Las menciones textuales son indicios: pueden ser nombres de calles,
marcas o lugares próximos, y no corrigen automáticamente una relación.

La [ampliación de la revisión de recarga](REVISION_RECARGA_SILVER.md) resuelve
**80 de los 132 casos pendientes** mediante fichas de establecimientos/operadores
y direcciones oficiales CartoCiudad (IGN/CNIG). Se añaden 264 puntos y 300
conectores a las relaciones municipales admitidas. Con Consum Ángel Guimerá,
son **81 conflictos resueltos y 52 pendientes**: 50 sin contraste concluyente
incorporado y dos con revisión documental no concluyente (Catadau y SEUR Alaquàs).

Se conservan copias HTML/JSON, recibos y decisiones explícitas bajo
`resultados/revision_recarga/20261018_revision_manual/` y las carpetas anteriores,
fuera de Git. La configuración vigente conserva sus referencias históricas.
Se verifica identidad de la instalación, atributos esperados, huellas, recibos,
dirección/localidad documentadas y coherencia territorial.

La evidencia distingue 19 fichas estructuradas de establecimientos, nueve
registros propios de Iberdrola | bp pulse, dos páginas de contacto, 30 portales
oficiales, 20 viales oficiales y una revisión visual complementada por fuente
primaria (WS Alfafar, Massanassa). Las consultas CartoCiudad parten de dirección
y código postal de origen, sin imponer municipio ni usar búsqueda inversa.
Un vial solo acredita la referencia municipal de la calle: no verifica número,
plaza física ni operación histórica. Sus métodos quedan diferenciados en la
relación admitida. Los POI de recarga derivados de MITECO no se emplean como
evidencia independiente. Una coordenada publicada que contradiga la admisión
impide aplicarla. Las coordenadas comerciales siguen siendo diagnósticas.

No se modifican el municipio ni las coordenadas originales, ni se toma la
proximidad como regla de admisión. La nueva exportación oficial MITECO no cambia
el municipio de los 131 identificadores pendientes que se localizan; un
identificador no aparece, lo que no acredita cierre ni permite eliminarlo.

| Entidad | Conservadas | Con relación admitida | Asignación pendiente |
| --- | ---: | ---: | ---: |
| Instalaciones | 1.526 | 1.474 | 52 |
| Puntos | 4.402 | 4.231 | 171 |
| Conectores | 5.244 | 5.053 | 191 |

Los pendientes no se pierden ni cuentan como ausencia de infraestructura. La
revisión de todos los casos no equivale a verificar la posición física de todos
los cargadores. La evidencia actual no acredita disponibilidad histórica ni el
datum real por fila.

## Relaciones territoriales

Los POI completos, las observaciones de aforo por tramo/año, los tramos IGN por
copia provincial y los puntos de conexión i-DE se contrastan con los 542 recintos. La clave de entidad es un
array JSON de textos, que evita colisiones por separadores:

| Entidad | Componentes, en este orden |
| --- | --- |
| `poi_elementos` | `origen_id`, `fid_origen` |
| `aforos_tramo_anio` | `tramo_aforo_id`, `anio` |
| `red_tramos` | `provincia_origen`, `tramo_id` |
| `capacidad_demanda_geo` | `punto_conexion_id` |

Se conserva cada intersección, incluidos contactos de frontera y relaciones con
varios municipios. Los polígonos no se sustituyen por centroides y las líneas
no reciben un municipio exclusivo. Se trabaja en 2D sobre EPSG:25830 sin alterar
la geometría Silver de origen ni su Z.

La dimensión y, cuando corresponda, longitud o superficie de la intersección son
diagnósticas. **No reparten IMD, población, capacidad o recuentos**. Una línea que
solo toca un municipio en un punto produce dimensión cero y medidas nulas; un
contacto de un área con una frontera puede producir una línea. Los contactos y
tramos en límites pueden duplicar medidas si se suman entre municipios, por lo
que Gold necesitará una regla específica antes de agregar.

Cada entidad tiene además un estado: intersección única, múltiple, sin
intersección en CV o geometría no admitida. Los objetos exteriores siguen
presentes. Las cinco geometrías IGN degeneradas quedan fuera del cruce métrico,
pero conservadas en la fuente y en el estado de relaciones. La
[capa complementaria i-DE](CAPACIDAD_DEMANDA_SILVER.md) aplica EPSG:25830,
publicación 04-09-2026 y periodo agosto según formato mensual CNMC. Sus
423 intersecciones son únicas y concuerdan con provincia y nombre oficial,
incluidas variantes bilingües explícitas; también están admitidas en
`capacidad_demanda_espacial/entidad_municipio`. La geometría por sí sola no
constituye una regla de admisión nominal.

| Entidad | Conservadas | Intersección única | Múltiple | Sin intersección CV | Geometría no admitida | Relaciones |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| POI | 269.287 | 268.273 | 495 | 519 | 0 | 269.267 |
| Aforos por tramo/año | 9.041 | 3.126 | 5.915 | 0 | 0 | 18.047 |
| Tramos IGN por copia | 1.118.309 | 1.093.269 | 24.885 | 150 | 5 | 1.143.203 |
| Puntos de conexión i-DE | 423 | 423 | 0 | 0 | 0 | 423 |

En total, **1.430.940 relaciones** y **1.397.060 estados de entidad**. Las relaciones
múltiples explican el aumento de filas; no son nuevas entidades ni recuentos
sumables. Los 150 tramos exteriores conservan su procedencia provincial: esta
no garantiza contención en CV. Tampoco se deduplican físicamente las copias
provinciales entre sí. En aforos, una geometría de tramo que cruza varios municipios
no convierte la medida de tráfico en observaciones municipales independientes.

## Controles conjuntos y temporalidad

Se comprueban códigos territoriales y recintos; claves/padres de recarga;
asociaciones tramo–vial; extremos de correspondencias OSM; atributos originales
de instalaciones; y ausencia de multiplicación al incorporar municipios o la
relación validada de recarga. Los registros DGT sin municipio, PP000 y el código
histórico de renta `12066` mantienen su separación.

El informe registra periodos y nulos por tabla. `cobertura_estadistica` describe
solo cantidades de registros y valores informados/ausentes por periodo, municipio
y segmento; no combina niveles de renta ni construye indicadores del producto.
Las fuentes parciales no están obligadas a cubrir todos los municipios.

Se conservan población 2021–2025, renta 2015–2023, parque 2025, aforos 2009–2025
y la instantánea OSM de 09-09-2026. Modificación MITECO no equivale a adquisición
o instalación; i-DE separa publicación 04-09-2026 y periodo agosto según
formato mensual CNMC, sin inventar un día exacto de corte. Se conservan los
estados históricos en la tabla previa y la capa aplica la acreditación posterior. Los recintos
consultados en 2026 siguen explícitos. No se elige por esta fase un año común ni la unidad de Gold.

## Salidas y reproducción

```powershell
.\.venv\Scripts\python.exe src/validar_silver.py --evidencias-recarga resultados/revision_recarga/20261018_revision_manual/decisiones.json
```

Requiere las ocho ejecuciones vigentes, sus informes/manifiestos y las copias de
evidencia con recibos. `decisiones.json` es un insumo revisado, conservado con las
evidencias; contiene ID de instalación, atributos esperados, código revisado,
decisión `admitir`/`mantener_pendiente`, motivo, URL, ruta y huella de la copia,
dirección y municipio documentados. Una copia nueva del repositorio necesita
recuperar estos insumos junto a los datos. No se descargan fichas actuales ni
se fabrican decisiones al reproducir la validación.

Se crean seis Parquet ZSTD e informe en una ejecución nueva bajo
`resultados/silver/validacion_conjunta/`, fuera de Git:

| Salida | Contenido |
| --- | --- |
| `revision_recarga` | Los 133 casos, indicios, decisión, motivo y evidencia documental disponible. |
| `recarga_municipio_validado` | Relaciones admitidas previas y resolución documental complementaria. |
| `relaciones_espaciales` | Entidad–municipio, método, dimensión y medidas diagnósticas de intersección. |
| `estado_relaciones_espaciales` | Una fila por entidad espacial, conservando exteriores y no admitidas. |
| `cobertura_estadistica` | Cobertura y ausencias por periodo/segmento/municipio. |
| `estado_fuentes` | Estado y limitaciones de los ocho bloques; tabla i-DE histórica complementada por su capa. |

La escritura se relee y contrasta por tipos, valores y claves. `actual.json` solo
se sustituye tras validar y volver a comprobar las entradas. Motor DuckDB con
1 GB y dos hilos, temporales en disco, sin dependencias nuevas.

Ejecución vigente: **`20261019T094606691147Z`**, estado
`preparada_con_limitaciones`. Las otras dos salidas contienen 96.476 filas de
cobertura estadística y ocho estados de bloque. Se aplican reglas **v4**. Las seis salidas coinciden por
huella con su informe y el código ejecutado conserva las huellas registradas.
**120 pruebas superadas, sin omisiones**, incluidas nueve nuevas para la capa
i-DE y su integridad conjunta, además de las 27 para relaciones,
límites, revisión documental, trazabilidad y exportación.

El cruce IGN se realiza por copias provinciales. El intento de un solo lote
exportaba y releía correctamente, pero sufría una caída nativa al cerrar DuckDB
en este Windows, sin llegar a publicar `actual.json`. La ejecución por provincias
cerró normalmente y eliminó sus temporales. En la comprobación inicial, las seis salidas fueron idénticas por
SHA-256 a las exportaciones del cálculo conjunto con las mismas decisiones;
el cambio de ejecución no altera resultados. No se atribuye una causa universal
ni se cambia DuckDB o la configuración global del equipo.

El cierre operativo admite incidencias conservadas con efecto conocido: no
declara integradas espacialmente las fuentes pendientes. Gold, scoring, modelos
y aplicación web quedan fuera del alcance de este proceso.
