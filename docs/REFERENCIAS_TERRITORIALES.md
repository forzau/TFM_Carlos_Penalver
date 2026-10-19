# Referencias territoriales y procedencia de Bronze

Comprobación del **15 de octubre de 2026**. Se incorporan referencias oficiales
para identificar los municipios del proyecto y preparar la futura integración
espacial. Se conserva cada respuesta original y su recibo de adquisición;
no se han limpiado ni unido los indicadores.

## Relación oficial de municipios

Se descarga la [relación INE de municipios y códigos a 1 de enero de 2025](https://www.ine.es/daco/daco42/codmun/25codmun.xlsx).
La referencia temporal figura dentro del libro, con 52 hojas provinciales y
8.132 municipios españoles. Se elige esta edición para contrastar las fuentes de
población y parque de 2025; no se está imponiendo un año común a todo el análisis.

Los códigos municipales son `CPRO` + `CMUN`, de dos y tres dígitos. `DC` es el
dígito de control y no forma parte del código municipal de cinco posiciones.
El libro mezcla texto con un código numérico de tres cifras; el lector admite
ese caso sin completar códigos ambiguos ni modificar el original.

| Provincia | Municipios INE | Códigos en población | Códigos en DGT municipal | Recintos municipales IGN |
| --- | ---: | ---: | ---: | ---: |
| Alicante/Alacant | 141 | 141 | 141 | 141 |
| Castellón/Castelló | 135 | 135 | 135 | 135 |
| Valencia/València | 266 | 266 | 266 | 266 |
| **Total** | **542** | **542** | **542** | **542** |

Las comparaciones de conjuntos no detectan códigos ausentes ni adicionales
entre estas cuatro referencias. Se mantiene aparte el caso histórico de renta
descrito más abajo.

## Cartografía oficial de unidades administrativas

Se utiliza el servicio de descarga WFS del IGN, publicado en su
[directorio oficial de servicios](https://www.ign.es/web/es/ign/portal/ide-area-nodo-ide-ign).
La petición completa se conserva en `config/catalogo_bronze.json` y en el recibo
de adquisición. Solicita `au:AdministrativeUnit`, con prefijo de código nacional
`3410*` (Comunitat Valenciana), formato GeoJSON y máximo de 600 objetos.

La respuesta contiene **546 unidades**: 542 municipios, tres provincias y una
comunidad autónoma. El recuento independiente `resultType=hits` del mismo servicio
devuelve 546: no hay truncamiento frente a esa consulta. Los 546 objetos tienen
geometría MultiPolygon informada; los códigos municipales son únicos y coinciden
con el INE. El nivel INSPIRE `4thOrder` identifica municipios. Solo en ese nivel,
las cinco últimas posiciones de `nationalCode` corresponden al código INE,
comprobando también que la provincia coincide.

Se preservan GeoJSON, capacidades WFS, respuesta de recuento y sus tres recibos
de adquisición con URL, fecha UTC, tamaño y SHA-256. La consulta del servicio se
conserva como instantánea del 15-10-2026: **no acredita que los límites representen
exactamente la situación de 2025**. La coincidencia de códigos tampoco prueba
identidad histórica de las geometrías. La incorporación a Bronze no simplificó,
recortó, reproyectó ni comprobó topológicamente los recintos. Las capacidades del
proveedor declaran EPSG:4258 por defecto y el GeoJSON no incluye un miembro `crs`.
La [configuración posterior](CONFIGURACION_SILVER.md) documenta la interpretación
espacial adoptada y su contraste; la [fase 2 de Silver](BASE_TERRITORIAL_SILVER.md)
materializa los recintos proyectados y validados. La respuesta Bronze permanece
conservada tal como se recibió.

## Código histórico de Gátova en renta

La [consulta histórica del INE para 12066](https://www.ine.es/intercensal/intercensal.do?btnBuscarCod=Consultar+selecci%C3%B3n&codigoMunicipio=066&codigoProvincia=12&search=3)
identifica Gátova en Castellón y explica su integración en Valencia como
`46902`. La [Ley Orgánica 15/1995](https://www.boe.es/eli/es/lo/1995/12/27/15)
documenta el cambio provincial. La referencia municipal de 2025 contiene
`46902 Gátova` y no contiene `12066`.

En la copia de renta se observan 543 códigos valencianos: los 542 vigentes y
`12066`. Este último aporta **54 filas municipales sin valor informado**, seis
indicadores por nueve años (2015–2023). El código vigente `46902` ya aporta 162
filas informadas: 54 municipales, 54 de distrito y 54 de sección censal.

Por tanto, `12066` no representa un municipio valenciano adicional vigente ni
valores de renta cero. Se conserva íntegro en Bronze. Para Silver queda definida
la necesidad de separar esas filas históricas sin datos del conjunto vigente,
con trazabilidad; **no sustituir automáticamente 12066 por 46902**, porque el
código vigente ya existe y el reemplazo produciría claves repetidas. Esta
comprobación inicial documentó el tratamiento. La [fase 3 de Silver](DEMOGRAFIA_PARQUE_SILVER.md)
ya lo ejecuta, conservando las 54 filas en una tabla histórica separada y sin
modificar las copias Bronze.

## Metadatos recuperados y límites de la recuperación

| Recurso | Resultado comprobado | Qué sigue sin acreditarse |
| --- | --- | --- |
| Población INE | Tabla **68065**, «Población según municipio y sexo»; exportación completa CSV con `;`, periodos 2021–2025. La descarga actual y la copia local tienen el mismo tamaño y SHA-256. El índice indica publicación 02-12-2025. | Fecha en la que se adquirió originalmente la copia local. |
| Renta INE | Tabla **30824**, «Indicadores de renta media y mediana», identificada en el índice y selector oficial de descargas. Serie 2015–2023; contraste completo detecta que el descargable actual difiere del local. | Edición exacta y adquisición original. La publicación indicada por el índice actual (21-10-2025) no acredita identidad con la copia conservada. |
| Aforos GVA | Identificado el recurso CKAN **aeac4d25-cd33-46c2-a9f3-3be342da167f** y su petición WFS de exportación GeoPackage para las 17 capas 2009–2025. | Edición exacta y adquisición de la copia local. La fecha del recurso y la de modificación de la ficha no fechan la exportación. |
| Recarga MITECO | Confirmado recurso CSV **047c1f64-7552-44da-a639-2291292e650d** y endpoint de exportación. La ficha CKAN declara versión **1.0** y `reference_system` **EPSG:4258**. La investigación del 16-10 confirma que ese CRS ya figuraba en la copia de la ficha del 15-10. | La versión 1.0 no fecha la instantánea CSV. El CRS es declaración del proveedor, sin validación geodésica por registro; salvedad OCPI y contraste espacial con incidencias documentados en los informes de recarga. |
| Red de transporte IGN | GeoPackages sin `gpkg_metadata`; documentación local e interfaz del modelo identificadas. | Edición oficial de las tres copias provinciales. `last_change`, `alta_db` y versiones del modelo no acreditan edición del dato. |
| OSM/Geofabrik | README acredita instantánea **09-09-2026, 20:21:20 UTC**. | Adquisición original y enlace histórico de descarga equivalente; `latest` es mutable. |
| DGT | Mensual provisional diciembre de 2025 y tabla municipal 2025 identificados. Referencia del parque municipal: 31-12-2025; nueva descarga municipal: 15-10-2026. | Fecha de adquisición original del TXT nacional. |
| i-DE | Revisión 19-10-2026: CSV local idéntico al descargable histórico de 04-09-2026. Periodo agosto según formato mensual CNMC; EPSG:25830 acreditado en el anexo de demanda BOE-A-2025-9913 citado por i-DE. | Día/hora exactos de corte y adquisición original. Capa Silver incorporada con 423 relaciones municipales contrastadas en 116 municipios. Véase [informe i-DE](CAPACIDAD_DEMANDA_SILVER.md). |

Fuentes de estas identificaciones: [tabla 68065](https://www.ine.es/jaxiT3/Tabla.htm?t=68065),
[descarga de la tabla 30824](https://www.ine.es/jaxiT3/dlgExport.htm?t=30824&L=0),
[índice de población](https://www.ine.es/dynt3/inebase/index.htm?capsel=11398&padre=11555),
[índice de renta](https://www.ine.es/dynt3/inebase/index.htm?capsel=5650&padre=5608),
[ficha GVA](https://dadesobertes.gva.es/api/3/action/package_show?id=intensidad-media-diaria-anual-imd-de-trafico-por-tramos-red-autonomica-de-carreteras-2009-2025),
[ficha MITECO](https://catalogo.datosabiertos.miteco.gob.es/catalogo/api/3/action/package_show?id=6ee8d46f-93bd-478f-8e29-3ba4f6d8405c)
y [mapa i-DE](https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo).
Las fechas no recuperables se mantienen como desconocidas: una consulta nueva
no permite reconstruir cuándo se descargaron los originales anteriores.

La comparación de renta se realiza mediante SHA-256 de todo el flujo de descarga,
en bloques de 1 MiB, sin guardar otra copia. El archivo local tiene 351.901.894
bytes y SHA-256 `a8998c45abc39df71d6537856add9c2ce822cfe078f78ca9a8448773118ee3cd`;
el remoto consultado tiene 353.006.608 bytes y SHA-256
`fb14c283af96d1e948464ffd780fcdf7a58efe3e27fda379498af50a02694dd7`.
Esto acredita diferencias entre archivos, sin determinar si afectan a formato,
etiquetas o valores. Se conserva la entrada original identificada por su huella;
no se reemplaza ni se presenta la descarga actual como copia idéntica.

## Reproducción

Con el entorno del README y las fuentes anteriores disponibles:

```powershell
.\.venv\Scripts\python.exe src/incorporar_referencias.py
.\.venv\Scripts\python.exe src/auditar_referencias.py
.\.venv\Scripts\python.exe src/catalogar_bronze.py
```

El primer script requiere Internet y conserva copias y recibos bajo
`datos/bronze/`. Si la copia existe, comprueba su recibo y la reutiliza; no vuelve
a consultar la fuente ni la sobrescribe. Una nueva edición necesita otra ruta.
El segundo funciona sin red y deja el perfil agregado en
`resultados/referencias_territoriales/perfil.json`. El tercero crea un manifiesto
nuevo del catálogo ampliado; el registro inicial se conserva. Los datos, recibos
y perfiles quedan fuera de Git.

Verificación de la incorporación Bronze: 20 pruebas del proyecto aprobadas; perfil territorial
ejecutado con las copias reales; manifiesto ampliado de 39 archivos comprobado
completo. Las 31 copias del registro inicial mantienen tamaño y SHA-256, y los
29 archivos de `Fuentes/` conservan además la modificación registrada previamente.
