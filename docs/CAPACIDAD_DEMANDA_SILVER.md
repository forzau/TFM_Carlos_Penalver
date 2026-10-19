# Capacidad de demanda i-DE en Silver

Actualizado: **19 de octubre de 2026**. Fase 7 del [plan de Silver](PLAN_SILVER.md).
La fecha de publicación y el CRS de la copia están acreditados documentalmente:
**04-09-2026** y **ETRS89 / UTM 30N, EPSG:25830** para Comunitat Valenciana.
El periodo informado es **agosto de 2026**, derivado de la regla mensual del
formato CNMC. La capa complementaria ya contiene **423 puntos válidos y 423
relaciones municipales admitidas en 116 municipios**, sin incidencias espaciales.
La tabla del 16-10 y los originales se conservan.

## Entrada y ámbito

Se utiliza `Fuentes/Demanda_energetica.csv`, recurso `ide_capacidad_demanda`
del catálogo Bronze. Se verifican tamaño y SHA-256 antes y después contra el
manifiesto, sin modificar el original ni sustituirlo por una descarga actual.
Lectura UTF-8, separador `;`, cabecera de 17 campos y ancho de cada registro
comprobados. El ordinal se asigna antes de seleccionar el ámbito.

La copia tiene **3.019 registros nacionales**, con identificadores de punto de
conexión únicos y sin vacíos. Se seleccionan por las tres etiquetas provinciales
publicadas, conservando **423 registros**, sin deduplicación ni pérdida dentro
de ese ámbito. Los otros 2.596 permanecen en Bronze.

| Provincia declarada | Puntos de conexión | Códigos de subestación distintos | Etiquetas municipales distintas |
| --- | ---: | ---: | ---: |
| Alicante/Alacant | 130 | 44 | 33 |
| Castellón/Castelló | 78 | 33 | 25 |
| Valencia/València | 215 | 81 | 58 |
| Total | **423** | **158** | **116** |

Estas son etiquetas de la fuente, todavía sin correspondencia municipal INE ni
contraste espacial. No se interpreta 116 como cobertura municipal verificada.
Varios puntos pueden compartir subestación y coordenadas; no se fusionan por
esa coincidencia. El recurso describe la red publicada por i-DE, sin acreditar
un inventario de todas las distribuidoras o de todos los municipios.

## Campos, unidades y estados

`capacidad_demanda` tiene una fila por `punto_conexion_id` de esta instantánea.
La clave se valida nacionalmente antes de filtrar y de nuevo en Silver. Se
conservan los 17 campos originales como texto, incluidos ceros iniciales,
espacios exteriores de las denominaciones, coordenadas y comentarios vacíos.
Se añaden `origen_id` —recurso y huella—, `registro_origen` y `codigo_provincia`.
No se asigna todavía `codigo_municipio`.

| Valores preparados | Tipo físico | Regla |
| --- | --- | --- |
| Tensión | `DECIMAL(18,2)`, kV | Positiva; coma decimal de origen. |
| Capacidad firme disponible, ocupada y admitida no evaluada | `DECIMAL(18,2)`, MW | No negativas, sin sumar conceptos ni puntos. |
| Posiciones ocupadas y libres | `BIGINT` | Recuentos enteros no negativos; sin convertirlos en capacidad o conexiones disponibles. |
| Compromiso regulatorio y nudo 0* | `BOOLEAN` | Solo `0` y `1` publicados; el vacío produce nulo. Se conserva además el texto original. |

Cada valor tipado tiene su columna `estado_<campo>`: `informado`,
`no_informado` o `error_conversion`. El código rechaza formato ambiguo,
agrupación de miles, exceso de precisión o desbordamiento; conserva el original
y registra incidencia en vez de redondear o imputar. El diseño y los nombres
de columnas están en el [diccionario](DICCIONARIO_SILVER.md#9-capacidad-de-demanda-i-de).

En la copia seleccionada:

- Tensión, tres capacidades y dos banderas informadas en los 423 puntos.
- Cada campo de posiciones tiene 79 valores informados y **344 ausencias**;
  los ausentes permanecen nulos y los ceros informados permanecen cero.
- **36 puntos** publican capacidad firme disponible positiva y **387** cero.
- **57 puntos** tienen `Nudo 0*=1`; todos conservan capacidad disponible cero.
- Compromiso regulatorio publicado como cero en los 423 registros; no se
  extrapola a otras fechas ni a toda la red.
- **Cero incidencias de conversión o coherencia** en esta ejecución. La fecha
  y la georreferenciación figuraban pendientes en la tabla histórica; la capa
  complementaria aplica los metadatos acreditados.

Según las [instrucciones y nota metodológica de i-DE](https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo),
consultadas el 16-10-2026, se trata de capacidad orientativa de **demanda**, no
energía consumida ni garantía de conexión. Los nudos se influyen mutuamente:
no se suman capacidades por zona, subestación o nivel de tensión como si fueran
independientes. `Nudo 0*=1` señala posible capacidad condicionada a refuerzos;
no se transforma en capacidad positiva. El compromiso regulatorio señala
solicitudes pendientes vinculadas a concurso en transporte. La capacidad ocupada
no aplica los coeficientes de simultaneidad descritos por el proveedor; no se
utiliza para reconstruir un supuesto total de capacidad.

## Acreditación de fecha y referencia espacial

El 19-10-2026 se contrasta el histórico de la
[página oficial de i-DE](https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo).
El [CSV de 04-09-2026](https://www.i-de.es/documents/d/guest/2026_09_04_r1-001_demanda-1-)
es idéntico byte por byte a `Fuentes/Demanda_energetica.csv`: **344.722 bytes**,
SHA-256 `1e486a6a825bcc712ac507a3c8ff3323226a64929224c77ccb4781b1d961f524`.
Coinciden los 17 campos y los 3.019 registros nacionales, incluidos los 423 CV.
El PDF de la misma edición imprime esa fecha en sus 56 páginas. El CSV de
02-10-2026 difiere en 360 registros; se conserva solo como contraste y no
sustituye la copia histórica.

| Metadato acreditado | Valor y alcance |
| --- | --- |
| Fecha de publicación | **2026-09-04**, identificada por igualdad binaria con el descargable histórico. |
| Periodo de referencia | **2026-08**, derivado de la regla del formato CNMC: publicación en los cinco primeros días del mes siguiente al informado. |
| Día/hora exactos de corte | **No acreditados**; no convertir el mes en un supuesto corte a 31 de agosto. |
| Adquisición original | Desconocida. La nueva conservación de evidencia del 19-10 no fecha la descarga histórica. |
| Referencia espacial CV | **ETRS89 / UTM huso 30N, EPSG:25830**, X este e Y norte, en metros. |

i-DE declara que publica según el formato de la resolución CNMC de 30-04-2025.
Su [anexo de demanda, BOE-A-2025-9913](https://www.boe.es/buscar/doc.php?id=BOE-A-2025-9913),
define expresamente **ambas coordenadas** como ETRS89 UTM huso 30 peninsular.
Se acredita así la referencia declarada por el formato del proveedor, sin
deducirla por rangos ni certificar la exactitud posicional de cada subestación.
La revisión preliminar no había localizado esa definición en el anexo; esta
comprobación rectifica aquella limitación. No es necesario heredar el CRS de
otro esquema histórico ni usar el modelo de comunicación de otra circular.

Copias y recibos conservados fuera de Git en
`resultados/investigacion_ide/20261019/`: descargables CSV/PDF/XLSX, extracto
documental del sitio, norma y `metadatos.json` con rutas relativas y huellas.
La comprobación se reproduce sin red ni dependencias nuevas:

```powershell
.\.venv\Scripts\python.exe src/verificar_metadatos_ide.py --evidencias resultados/investigacion_ide/20261019/metadatos.json
```

El verificador comprueba huellas antes y después, igualdad binaria, esquema,
claves y recuentos, enlace del histórico, declaración del proveedor, definición
de X/Y en el apartado de demanda y coherencia del periodo mensual. Esta
acreditación no regenera Silver ni produce geometrías o asignaciones municipales.

## Estado de las tablas ya materializadas

La ejecución `20261016T124247391438Z` conserva los estados conocidos al generarla:
`fecha_referencia=null`, `estado_fecha=no_acreditada` y
`estado_coordenadas=pendiente_crs`. Son metadatos históricos de esa ejecución;
la evidencia posterior queda registrada por separado, vinculada al SHA-256 del
original. Tampoco se reescriben las salidas de validación conjunta del 18-10.

Las X/Y conservan toda su precisión textual con coma decimal. La nueva capa
aplica la evidencia posterior sin reescribir la preparación tabular histórica.

## Capa espacial y contraste municipal

`src/georreferenciar_capacidad_demanda.py` verifica las evidencias, la tabla de
fase 7, su correspondencia literal con el CSV y los recintos vigentes. Genera
puntos directamente desde X/Y en EPSG:25830, sin reproyectar ni desplazar las
coordenadas. Cada identificador de punto de conexión se conserva, aunque varios
compartan subestación o coordenadas; no se fusionan ni suman capacidades.

La admisión municipal exige geometría válida, intersección con un único recinto,
provincia concordante y nombre oficial resuelto sin ambigüedad. Se contrastan
nombres INE/IGN y cada variante oficial separada por `/`, con normalización de
acentos, puntuación y espacios. No se emplea similitud aproximada ni municipio
más cercano. Esto permite reconocer seis registros con `Castelló de la Plana`
frente a la denominación oficial bilingüe, sin cambiar el texto original.

| Provincia declarada | Puntos conservados | Relaciones admitidas | Pendientes |
| --- | ---: | ---: | ---: |
| Alicante/Alacant | 130 | 130 | 0 |
| Castellón/Castelló | 78 | 78 | 0 |
| Valencia/València | 215 | 215 | 0 |
| Total | **423** | **423** | **0** |

Todos los puntos intersectan un solo municipio y concuerdan. Los **116 municipios**
son cobertura contrastada de esta copia i-DE, sin afirmar cobertura de toda la
red de distribución. La capa queda `preparada`; las reservas de uso, precisión
posicional y capacidad orientativa permanecen. La distancia al recinto declarado
es diagnóstica y no interviene en la admisión.

```powershell
.\.venv\Scripts\python.exe src/georreferenciar_capacidad_demanda.py --metadatos-ide resultados/investigacion_ide/20261019/metadatos.json
```

Nueva ejecución `20261019T094517138707Z`, bajo
`resultados/silver/capacidad_demanda_espacial/`, con cuatro salidas:

| Tabla | Filas | Función |
| --- | ---: | --- |
| `capacidad_demanda_geo` | 423 | Atributos originales, metadatos acreditados, coordenadas numéricas, geometría EPSG:25830 y contraste territorial. |
| `capacidad_municipios_candidatos` | 423 | Todas las intersecciones punto–municipio, sin asumir admisión por el mero cruce. |
| `entidad_municipio` | 423 | Relaciones admitidas, con clave `punto_conexion_id` y código municipal. |
| `incidencias_espaciales` | 0 | Puntos no admitidos, con motivo; esquema conservado aunque esté vacía. |

En la capa se separan `fecha_publicacion=2026-09-04`,
`periodo_referencia=2026-08`, `estado_fecha=periodo_mensual_acreditado` y
`estado_coordenadas=crs_acreditado`. `fecha_referencia` sigue nula porque no
se acredita un día exacto de corte. Los estados anteriores se conservan como
`estado_fecha_preparacion` y `estado_coordenadas_preparacion`.

La comparación completa conserva los 39 campos de la preparación original,
con esos dos cambios de nombre explícitos. Las cuatro salidas se reabren y
comparan en ambos sentidos, incluidos tipos, nulos y WKB; el GeoParquet declara
EPSG:25830. `actual.json` solo se actualiza después de cerrar y reverificar las
entradas. No requiere red ni dependencias nuevas; motor de 1 GB y dos hilos.

## Reproducción y comprobaciones

Desde la raíz, con las copias Bronze y el entorno del proyecto disponibles:

```powershell
.\.venv\Scripts\python.exe src/preparar_capacidad_demanda.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
```

No descarga datos ni requiere nuevas dependencias o la extensión espacial.
DuckDB utiliza una base temporal en disco, dos hilos y 1 GB para su motor.
Los temporales se eliminan al cerrar; los originales permanecen intactos.

Salidas bajo `resultados/silver/capacidad_demanda/<ejecucion>/`, excluidas de Git:

- `capacidad_demanda.parquet`: **423 filas**.
- `incidencias.parquet`: **0 filas**, con esquema definido.
- `informe.json`: entradas y huellas, código, entorno, recuentos por provincia,
  estados, unidades documentadas y límites; sin suma de capacidades.

La ejecución validada es `20261016T124247391438Z`; `actual.json` apunta a su
informe solo después de completar las comprobaciones. El estado es
`preparada_pendiente_integracion_espacial`, con `estado_tabular=preparada`.
La exportación Parquet ZSTD se relee y compara íntegramente en ambos sentidos,
incluidos tipos, nulos y textos. También se contrastan los 17 campos originales
con las filas CV del CSV. No se sobrescriben ejecuciones anteriores.

En el cierre original del 16-10 pasaron **69 pruebas**, sin omisiones: ocho nuevas cubrieron
precisión y límites, ausente frente a cero, banderas, claves nacionales,
conservación literal, incidencias, límites espaciales/temporales y exportación.
El material público contiene código, reglas y recuentos agregados; los valores
por punto se conservan únicamente en los resultados locales.

Al acreditar los metadatos el 19-10 pasaron **111 pruebas**, sin omisiones. Siete nuevas
comprueban identidad e integridad de las copias, referencia específica del
apartado de demanda, vínculo del descargable con el histórico y separación entre
publicación, periodo informado y corte exacto desconocido. La comprobación real
de `metadatos.json` también termina correctamente; el inventario sigue en
32 tablas y 314 columnas en aquel punto previo a la incorporación espacial.

Tras incorporar la capa pasan **120 pruebas**, sin omisiones. Nueve nuevas
cubren variantes oficiales y ambiguas, puntos coincidentes, límites, exteriores,
coordenadas inválidas, discrepancias de municipio/provincia, exportación
GeoParquet e integridad conjunta ante desplazamientos o fechas inventadas.

La fase **8, relaciones y validación conjunta**, está cerrada operativamente con
limitaciones desde el 18-10. La incorporación de i-DE del 19-10 aplica los
metadatos acreditados y materializa capa y relaciones. Gold, unidad final y
criterio temporal común siguen pendientes.

La validación conjunta vigente `20261019T094606691147Z` (reglas v4) verifica
la conservación de atributos i-DE, las 423 relaciones admitidas, fecha/periodo
y CRS frente a la evidencia, e incorpora 423 intersecciones y estados al conjunto.
