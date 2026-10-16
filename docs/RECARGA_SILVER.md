# Recarga existente MITECO en Silver

Fecha: **16 de octubre de 2026**. Preparación de la fase 4 del
[plan de Silver](PLAN_SILVER.md). Las tablas quedan preparadas por entidad.
La investigación posterior identifica **EPSG:4258, ETRS89 geográfico, como CRS
declarado por el proveedor para el CSV**. El [bloque espacial de fase 8](RECARGA_ESPACIAL_SILVER.md)
ya materializa una capa complementaria, con 1.393 asignaciones municipales
admitidas y 133 discrepantes. Las tablas originales de fase 4 se conservan.

## Entrada y lectura

Se utiliza exclusivamente la copia estática `Fuentes/instalaciones_actuales.csv`,
registrada como `miteco_recarga` en el [catálogo Bronze](CATALOGO_BRONZE.md).
Tiene 45.116.072 bytes, codificación UTF-16LE sin BOM, separador punto y coma y
27 columnas. Se comprueban tamaño y SHA-256 contra el manifiesto antes y después
del proceso; el original no cambia ni se sustituye por la exportación actual.

El CSV no sigue las reglas estándar de escape de comillas. Una lectura estricta
falla en la línea física 2.804; desactivar la interpretación de comillas también
falla, porque existen saltos de línea y punto y coma dentro de campos. La lectura
permisiva cuenta filas correctamente en esta copia, pero altera texto en **32
registros nacionales, ocho valencianos**: por ejemplo, elimina una comilla
interior y desplaza otra al final del nombre de una instalación.

El lector específico reconoce los envoltorios exteriores de cada campo y conserva
literalmente el contenido interior, incluidas comillas y saltos de línea. Retira
`="texto"` solo en las cuatro columnas que utilizan ese envoltorio, sin evaluar
fórmulas. Cada registro debe tener exactamente 27 campos y reconstruirse carácter
por carácter con sus envoltorios y separadores originales. Un esquema distinto,
una fila incompleta o una clave vacía detienen el proceso: no se saltan errores.
La comparación con el lector permisivo queda contabilizada en el informe.

Este lector está limitado explícitamente a exportaciones de hasta 64 MiB y al
dialecto comprobado. La copia de 43 MiB se decodifica en memoria; esta estrategia
no se aplica al TXT nacional DGT. Si cambia el exportador o aumenta el tamaño,
se revisará el lector antes de admitir otra copia.

## Ámbito y entidades

Se selecciona la comunidad declarada `Comunitat Valenciana` y se comprueba que
coincida con una de sus tres provincias declaradas. Se leen **43.610 registros
nacionales**, de los que **38.366 quedan fuera del ámbito** y **5.244 se conservan**.
El filtro administrativo no demuestra que las coordenadas estén realmente dentro
de la comunidad; esa comprobación requiere resolver primero su referencia espacial.

| Tabla | Una fila representa | Filas | Clave |
| --- | --- | ---: | --- |
| `recarga_instalaciones` | Instalación registrada por el proveedor. | 1.526 | `instalacion_id` |
| `recarga_puntos` | Punto dentro de una instalación. | 4.402 | `instalacion_id`, `punto_id` |
| `recarga_conectores` | Conector dentro del punto y la instalación. | 5.244 | `instalacion_id`, `punto_id`, `conector_id` |
| `incidencias` | Error de conversión o coordenada no admitida. | 0 | Referencia de tabla, campo y registro de origen. |

Las relaciones entre entidades se comprueban en ambos sentidos, sin huérfanos
ni padres sin detalle. La separación de padres solo se admite si todos sus
atributos coinciden en el detalle: no se toma una primera fila arbitraria.
El ordinal nacional tras la cabecera se conserva en `recarga_conectores` como
`registro_origen`; permite recuperar también las filas de cada padre por sus
identificadores. La copia y su huella se registran por salida, sin repetirlas
en todas las filas.

Los nombres de municipio y provincia son las etiquetas de MITECO, no códigos INE.
Los códigos postales siguen siendo texto, con sus ceros iniciales, y no sirven
como clave municipal. Se conservan los nombres de instalación con sus comillas.

| Provincia declarada | Instalaciones | Puntos | Conectores |
| --- | ---: | ---: | ---: |
| Alicante/Alacant | 663 | 1.871 | 2.168 |
| Castellón/Castelló | 155 | 484 | 563 |
| Valencia/València | 708 | 2.047 | 2.513 |

## Repeticiones y atributos variables

En CV **no se repite ninguna clave triple** y no se elimina ningún registro.
Las seis filas adicionales por clave del diagnóstico nacional pertenecen a dos
claves con cuatro observaciones cada una, de una misma instalación de Extremadura.
Sus atributos variables son horario y métodos de pago; no son filas idénticas.
El informe conserva claves, ordinales, comunidad y campos variables. Quedan fuera
de la salida por el filtro territorial, sin inventar una regla de deduplicación
nacional ni trasladar ese conflicto a los datos valencianos.

En CV, el horario textual varía dentro de **510 instalaciones**, los servicios
dentro de **37** y los métodos de pago dentro de **426 puntos**. Pueden existir
diferencias de orden de elementos además de diferencias de contenido; aquí no
se interpretan ni se normalizan como conjuntos. Se mantienen esos tres campos
por conector, evitando perder variantes al generar las entidades padre.

`DESCONOCIDO` y `NODISPONIBLE` permanecen como etiquetas originales. En particular,
accesibilidad no disponible no significa acceso denegado. Voltaje e intensidad
se conservan como textos de origen; no se necesitan para estimar una potencia
que el proveedor ya publica y no se deduce de ellos capacidad simultánea.

## Tipos, controles y límites de interpretación

- Coordenadas: `DOUBLE`, con texto numérico original conservado, sin redondeo.
  Se comprueba sintaxis, rango global de latitud/longitud y el par 0,0. Las 1.526
  instalaciones tienen coordenadas numéricas dentro de rango, sin pares 0,0.
  El estado de la ejecución original es `rango_valido_datum_pendiente`; se conserva
  sin reescribir salidas. La evidencia documental posterior se explica abajo y
  no certifica exactitud posicional de cada registro.
- Potencia: `DECIMAL(18,2)` en kW, conversión exacta desde coma decimal y unidad
  explícita. No se aceptan decimales adicionales mediante redondeo. En CV se
  observan **2,30–1.000,00 kW por conector**, sin errores de conversión. Los valores
  altos se conservan como valores publicados; no se certifica su funcionamiento.
- Modificación: `TIMESTAMP` con segundos y sin zona horaria acreditada. No se
  convierte a UTC ni a fecha de instalación; tampoco permite reconstruir la fecha
  de adquisición de esta copia. Admite horas con una o dos cifras, como publica
  el exportador. En CV va de **04-07-2023 10:58:32 a 12-08-2026 13:17:48**.
  Texto original y estado se conservan.
- Ausencias: un dato numérico no informado queda nulo y con su estado. Un error
  conserva el texto y una incidencia; nunca se reemplaza por cero.
- Se comprueban claves, integridad, recuentos y dependencias de los atributos
  padre. Al releer cada Parquet se comparan todos los valores, multiplicidades
  y tipos con las tablas preparadas. La salida es Parquet ZSTD.

**1.526 instalaciones, 4.402 puntos y 5.244 conectores son recuentos distintos.**
La suma de potencias de conectores no acredita potencia simultánea de una
instalación, pues pueden compartir equipamiento o suministro. La fuente refleja
registros públicos observados: no prueba exhaustividad del inventario ni estado
operativo o disponibilidad en tiempo real.

## Referencia espacial declarada e investigación del datum

Investigación del **16-10-2026**: la [ficha oficial de la distribución CSV](https://catalogo.datosabiertos.miteco.gob.es/catalogo/dataset/6ee8d46f-93bd-478f-8e29-3ba4f6d8405c/resource/047c1f64-7552-44da-a639-2291292e650d)
declara **EPSG:4258**, correspondiente a ETRS89 geográfico. La [API del catálogo](https://catalogo.datosabiertos.miteco.gob.es/catalogo/api/3/action/package_show?id=6ee8d46f-93bd-478f-8e29-3ba4f6d8405c)
lo recoge en `reference_system` del recurso
`047c1f64-7552-44da-a639-2291292e650d`, enlazado al mismo endpoint de exportación
identificado en Bronze: `http://www.opengis.net/def/crs/EPSG/0/4258`.
Es un metadato de la distribución concreta, no una deducción desde los rangos
de las coordenadas o desde una norma cartográfica general.

La ficha JSON conservada el 15-10-2026 y la descargada para esta investigación
son idénticas por SHA-256. La revisión anterior no había recogido ese campo;
se corrige su conclusión documental sin alterar el historial de ejecuciones.
La declaración permite adoptar **EPSG:4258 como referencia de trabajo documentada
del CSV**. No acredita la edición exacta de la copia ni el datum usado por cada
operador al registrar su instalación.

La [guía oficial RIPREE v9.0, apartado de alta de instalaciones, página 12](https://www.miteco.gob.es/content/dam/miteco/es/energia/hidrocarburos-y-nuevos-combustibles/ripree/inscripcion/Gu%C3%ADa_Usuario_RIPREE_V%209.0_.pdf)
indica latitud y longitud en formato decimal y permite obtenerlas mediante un
mapa. Esto resuelve el formato, pero la guía no declara por sí sola el datum.
La [página informativa de RIPREE](https://www.miteco.gob.es/es/energia/hidrocarburos-nuevos-combustibles/sitio-web-de-informacion-al-ciudadano-con-vehiculo-con-motor-ele/ripree.html)
y el [anexo III de la Orden TED/445/2023](https://www.boe.es/buscar/act.php?id=BOE-A-2023-10707)
usan la expresión «coordenadas UTM» para campos de latitud y longitud, insuficiente
para identificar la referencia de los valores decimales exportados.

Hay una salvedad: las [instrucciones oficiales de carga masiva, revisión 3](https://www.miteco.gob.es/content/dam/miteco/es/energia/hidrocarburos-y-nuevos-combustibles/ripree/envio-de-informacion/Instrucciones-campo-archivo-JSON%20rev3_.xlsx),
hoja `Modelo de datos Instal JSON`, refieren OCPI 2.2 en D4 y vinculan latitud y
longitud con `coordinates.latitude` y `coordinates.longitude` en las filas 15–16.
El [estándar OCPI 2.2-d2, sección 8.4.13, página PDF 78](https://evroaming.org/wp-content/uploads/2024/10/OCPI-2.2-d2.pdf)
define `GeoLocation` en WGS84. Describe el modelo de entrada; no demuestra que el
exportador convierta coordenadas ni que todas las altas cumplan ese datum.
Se conserva esta diferencia documental y se prioriza la declaración específica
del CSV, sin afirmar que ETRS89 y WGS84 sean idénticos.

Para fase 8 se utilizará X = `longitud`, Y = `latitud`, en grados decimales,
y transformación explícita **EPSG:4258 → EPSG:25830**, con `always_xy=true`.
Antes de admitir cada geometría se comprobarán ejes, validez y relación territorial;
los casos discrepantes quedarán señalados, sin desplazarlos o imputar municipios.
La coincidencia con un municipio no valida de forma independiente el datum o la
precisión fina. La [materialización posterior](RECARGA_ESPACIAL_SILVER.md) conserva
las 1.526 instalaciones y documenta los cruces y sus 133 conflictos municipales.

El informe de fase 4 mantiene sus valores históricos `crs_origen: null` e
`integracion_espacial_admitida: false`; no se modifica retrospectivamente ni se
actualiza `actual.json` por una investigación documental. La nueva evidencia,
copias consultadas, recibos y huellas se conservan en
`resultados/investigacion_datum_miteco/20261016/hallazgos.json`, fuera de Git.
La huella del CSV Bronze continúa coincidiendo con el manifiesto.

## Reproducción

Con los requisitos del README y el manifiesto Bronze disponible:

```powershell
.\.venv\Scripts\python.exe src/preparar_recarga.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
```

Ajustar la ruta al manifiesto de ese equipo. No requiere red ni dependencias
nuevas. El proceso crea una carpeta independiente bajo `resultados/silver/recarga/`
y solo actualiza `actual.json` después de validar tablas, huellas e informe.
Conserva ejecuciones anteriores y no sobrescribe una carpeta ya existente.
El JSON documenta entradas, código, versiones, claves, esquemas, incidencias y
limitaciones. Datos, informe detallado y temporales quedan fuera de Git; los
temporales se eliminan al finalizar. Las tablas previas de Silver no se modifican.

Ejecución validada: `20261016T114013461086Z`, señalada por `actual.json`, con
estado tabular `preparada` e integración espacial pendiente en aquel informe.
El script reproduce el estado original de fase 4; el proceso complementario
de fase 8 ya incorpora la evidencia del CRS y el contraste municipal. Las cuatro salidas
ocupan 91.230, 70.875, 95.485 y 188 bytes, respectivamente; sus SHA-256 figuran
en el informe. Se conserva una ejecución previa con incidencias de lectura de
horas, sustituida como referencia vigente tras admitir la hora sin cero inicial.
La carga en bloque mediante CSV temporales con esquema, comillas y formato de
fecha explícitos evita miles de inserciones individuales. La ejecución final
completa, incluidas huellas y relectura, termina en unos siete segundos en el equipo
de preparación; no es una garantía de duración en otros equipos.

Las pruebas cubren comillas literales, envoltorios, campos multilínea, separadores
internos, esquemas rotos, precisión, fechas, coordenadas, conflictos de padres,
claves repetidas, relaciones, conservación de variantes y exportación sin
sobrescritura. El siguiente bloque es la **fase 5: aforos GVA y red viaria IGN**.
La suite completa pasa **44 pruebas, sin omisiones**.
