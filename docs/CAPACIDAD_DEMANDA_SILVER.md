# Capacidad de demanda i-DE en Silver

Fecha: **16 de octubre de 2026**. Fase 7 del [plan de Silver](PLAN_SILVER.md).
La tabla está preparada; su integración espacial sigue pendiente de acreditar
el huso y datum de la copia. Tampoco se conoce su fecha de referencia.

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
  y la georreferenciación pendientes figuran en estados y límites explícitos.

Según las [instrucciones y nota metodológica de i-DE](https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo),
consultadas el 16-10-2026, se trata de capacidad orientativa de **demanda**, no
energía consumida ni garantía de conexión. Los nudos se influyen mutuamente:
no se suman capacidades por zona, subestación o nivel de tensión como si fueran
independientes. `Nudo 0*=1` señala posible capacidad condicionada a refuerzos;
no se transforma en capacidad positiva. El compromiso regulatorio señala
solicitudes pendientes vinculadas a concurso en transporte. La capacidad ocupada
no aplica los coeficientes de simultaneidad descritos por el proveedor; no se
utiliza para reconstruir un supuesto total de capacidad.

## Fecha y referencia espacial pendientes

La copia carece de campo de fecha. `fecha_referencia` permanece nula y
`estado_fecha=no_acreditada`; la fecha UTC de proceso queda en el informe.
Ni la modificación local, ni la publicación de la web actual, ni la actualización
mensual declarada acreditan la edición de este CSV.

Las X/Y presentan formato numérico con coma decimal; se conserva toda su
precisión textual, sin reducirla a dos decimales ni asignar un EPSG por parecido
de rangos o localización provincial. Las 423 filas tienen
`estado_coordenadas=pendiente_crs`. No se crean geometrías ni distancias,
asignaciones municipales espaciales o relaciones de proximidad con POI.

La documentación pública revisada no vincula inequívocamente esta copia con un
huso y datum. Un [PDF histórico de i-DE de septiembre de 2025](https://www.i-de.es/documents/2803098/3276069/2025_09_09_R1-001_Demanda.pdf/ee65f0db-9a4a-6932-a592-1f4cad84efb7?download=true&t=1764598399660&version=1.0)
menciona ETRS89 en sus cabeceras, pero tiene otro esquema y no acredita la
referencia del CSV local. No se hereda ese dato automáticamente.

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

La suite completa pasa **69 pruebas**, sin omisiones: ocho nuevas cubren
precisión y límites, ausente frente a cero, banderas, claves nacionales,
conservación literal, incidencias, límites espaciales/temporales y exportación.
El material público contiene código, reglas y recuentos agregados; los valores
por punto se conservan únicamente en los resultados locales.

La siguiente fase es la **8: relaciones y validación conjunta**. Deberá distinguir
esta preparación tabular de una integración espacial admitida, igual que en
MITECO. Silver completa, Gold, unidad final y criterio temporal siguen pendientes.
