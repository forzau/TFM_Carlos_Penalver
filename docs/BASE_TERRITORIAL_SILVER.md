# Base territorial Silver

Preparación ejecutada el **15 de octubre de 2026**. La fase 2 del
[plan de Silver](PLAN_SILVER.md) queda completada para las copias identificadas:
se dispone de una referencia de códigos y nombres del INE y una capa municipal
del IGN, con correspondencia uno a uno para los **542 municipios** del proyecto.

## Entradas y salidas

Se utiliza la relación INE de municipios a **01-01-2025** y la respuesta WFS IGN
consultada el **15-10-2026**, descritas en las
[referencias territoriales de Bronze](REFERENCIAS_TERRITORIALES.md).
Antes y después del proceso se comprueban tamaños y SHA-256 de sus ocho archivos:
XLSX, GeoJSON, capacidades y recuento XML, y sus cuatro recibos de adquisición.
La comprobación se limita a estas entradas; no vuelve a recorrer el TXT nacional DGT.

| Salida | Filas | Contenido y clave | Formato |
| --- | ---: | --- | --- |
| `municipios.parquet` | 542 | Código municipal, provincia, nombre INE y fecha de referencia. Clave: `codigo_municipio`. | Parquet, ZSTD. |
| `recintos_municipales.parquet` | 542 | Código municipal, código y nombre IGN, geometría, `origen_id` y `registro_origen`. Clave en esta ejecución: `codigo_municipio`; procedencia identificada por copia y objeto IGN. | GeoParquet, ZSTD, EPSG:25830. |
| `informe.json` | Un informe | Entradas y huellas, reglas, código por SHA-256, versiones del motor, esquemas y huellas de salidas, controles y diferencias nominales. | JSON. |

La ejecución validada se conserva en
`resultados/silver/base_territorial/20261015T164603584512Z/`.
`resultados/silver/base_territorial/actual.json` indica cuál es la ejecución
válida más reciente. Los datos y el informe detallado quedan fuera de Git;
el código, las pruebas y este documento sí se versionan.

Cada repetición crea una carpeta nueva. Una ejecución fallida no sustituye el
indicador de ejecución válida ni sobreescribe tablas anteriores. La escritura se
verifica releyendo los archivos y comparando todos los atributos y el WKB de las
geometrías con las tablas preparadas, además de comprobar el CRS GeoParquet.

## Transformaciones aplicadas

1. Leer el libro INE sin modificarlo; componer códigos como texto de cinco
   posiciones a partir de `CPRO` y `CMUN`, excluyendo el dígito `DC`. Seleccionar
   las provincias `03`, `12` y `46`, conservando sus nombres originales.
2. Comprobar que la respuesta IGN contiene las 546 unidades que declara su
   recuento. Separar los 542 objetos de nivel municipal `4thOrder` de las tres
   provincias y la comunidad autónoma. Estos cuatro objetos superiores se usan
   para control, sin añadirlos como municipios.
3. Contrastar los códigos IGN con el INE y conservar ambos nombres. No realizar
   coincidencias aproximadas por nombre ni sustituir el código histórico `12066`.
   La referencia vigente contiene `46902`, Gátova.
4. Validar geometrías originales y proyectarlas desde la interpretación
   OGC:CRS84 acordada a EPSG:25830, con orden X/Y explícito. Mantener todas las
   partes de cada MultiPolygon, sin simplificar, recortar, ajustar bordes ni reparar.
5. Escribir tablas con los tipos del [diccionario](DICCIONARIO_SILVER.md) y
   registrar su procedencia y controles. `origen_id` vincula recurso y huella
   GeoJSON; `registro_origen` conserva el identificador del objeto IGN.

La interpretación del GeoJSON, el orden de ejes y la justificación de la
proyección se recogen en la [configuración técnica](CONFIGURACION_SILVER.md).
Los originales de `Fuentes/` y `datos/bronze/` permanecen intactos.

## Resultados de validación

| Comprobación | Resultado |
| --- | --- |
| Municipios por provincia | Alicante: 141; Castellón: 135; Valencia: 266. Total: 542. |
| Unicidad y correspondencia INE–IGN | 542 claves únicas por salida; correspondencia uno a uno, sin ausentes ni adicionales. |
| Geometrías municipales válidas | 542 antes y 542 después de proyectar. |
| Geometrías nulas o vacías | 0. |
| Reparaciones o exclusiones geométricas | 0. |
| Aristas incoherentes de la cobertura municipal | Ninguna detectada con tolerancia cero. |
| Área: suma de municipios frente a su unión | Diferencia de unos 0,000183 m², compatible con precisión numérica; tolerancia de control: 1 m². |
| Unión municipal frente a recinto autonómico | 0 m² fuera del padre y 0 m² sin cubrir. |
| Uniones municipales por provincia frente a recintos provinciales | 0 m² fuera y 0 m² sin cubrir en las tres provincias. |
| Diferencias de nombre INE–IGN | 58; conservadas en el informe, sin modificar las claves. |
| Conservación tras exportar | Atributos y WKB idénticos a las tablas preparadas; metadatos de CRS correctos. |

El control de aristas se aplica después de comprobar que las entradas son
polígonos válidos y no vacíos. La tolerancia de 1 m² afecta únicamente a las
comparaciones agregadas de áreas calculadas con coma flotante; no se aplica un
buffer ni se desplazan límites para hacerlos coincidir. La validez y las
operaciones de cobertura utilizan las
[funciones espaciales de DuckDB](https://duckdb.org/docs/current/core_extensions/spatial/functions).

Las diferencias nominales incluyen `Atzúbia, l'` frente a `l'Atzúbia` o
`Castell de Guadalest, el` frente a `el Castell de Guadalest`. El nombre INE se
mantiene como nombre de referencia, y el IGN sigue disponible para contraste.
Una diferencia de escritura no produce otro municipio ni una unión fallida.

## Reproducción y pruebas

Con el entorno y la extensión espacial instalados según el README:

```powershell
.\.venv\Scripts\python.exe src/preparar_base_territorial.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

La ruta del argumento debe corresponder al manifiesto Bronze conservado en ese
equipo. El proceso trabaja con copias locales, sin red y sin nuevas dependencias.
La suite pasa **29 pruebas**, siete nuevas para esta preparación: conservación de
códigos/nombres/procedencia/CRS, rechazo de geometrías inválidas, solapamientos,
códigos faltantes, cobertura parental distinta, entradas alteradas y prevención
de sobrescritura. Si falta la extensión, las seis pruebas espaciales se señalan
como omitidas; en la comprobación de esta ejecución no hubo omisiones.

## Alcance y límites

La base queda preparada para relacionar las siguientes tablas Silver. La unidad
municipal de referencia no impone la unidad final de recomendación de Gold.
La fecha INE de 2025 y la consulta IGN de 2026 permanecen separadas: no se acredita
que todos los límites sean históricamente idénticos. La coincidencia geométrica
entre niveles de la misma fuente tampoco es una validación geodésica independiente.

Las áreas sirven para controles técnicos en la proyección elegida; no se publican
como superficies oficiales. No se ha integrado todavía población, parque, renta,
recarga, tráfico, POI o capacidad eléctrica. El siguiente bloque es la **fase 3:
parque municipal y detalle DGT observado, población y renta**.
