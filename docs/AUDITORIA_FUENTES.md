# Auditoría técnica de fuentes

Fecha: **14 de octubre de 2026**. Finalidad: comprobar si las copias reales permiten
preparar un sistema de apoyo a la localización de recarga en la Comunitat Valenciana.
Esta auditoría precede a Silver y Gold; no certifica todavía un dataset listo para ML.

**Actualización del 15 de octubre:** se ha verificado una tabla municipal DGT que
cubre los 542 municipios, adoptando Distintivo 0 como aproximación documentada.
El [informe de cobertura municipal](DGT_COBERTURA_MUNICIPAL.md) desarrolla la
solución y sus límites. Los hallazgos siguientes siguen describiendo las copias
originales auditadas, incluido el TXT con supresión municipal.

Las [referencias territoriales incorporadas](REFERENCIAS_TERRITORIALES.md) confirman
los 542 municipios mediante INE e IGN y resuelven la vigencia del código 12066 de
renta: es histórico y el código actual es 46902. Se identifican las tablas INE
de población y renta, conservando las diferencias de versión observadas. Estos
contrastes no modifican los recuentos originales de la auditoría siguiente.

## Método y reproducción

Se han leído los cinco ficheros tabulares y los 17 GeoPackages, incluyendo las
capas auxiliares de transporte. Se contabilizan todas las filas, los vacíos por
columna, categorías seleccionadas y las repeticiones de las claves indicadas.
SQLite se abre con `mode=ro`; DuckDB lee los textos como cadenas para conservar
ceros iniciales y evitar conversiones automáticas de códigos.

El código ejecutado y sus consultas están en `src/auditar_fuentes.py`; las instrucciones
del entorno están en el [README](../README.md#reproducción). Los perfiles completos,
esquemas, metadatos y diagnósticos se guardan en `resultados/auditoria/perfil.json`,
excluido de Git. El documento recoge únicamente evidencia resumida, sin registros
de vehículos, direcciones particulares ni datos de nodos eléctricos.

**Comprobaciones muestreadas:** duplicados exactos de las primeras 10.000 filas de
cada texto y cabeceras de las primeras 1.000 geometrías por capa, ordenadas por
`fid`. No son muestras aleatorias ni certifican ausencia de problemas en el resto.
`PRAGMA quick_check` comprueba integridad SQLite, no validez geométrica ni topología.
Tamaño y fecha de modificación de todos los originales se comparan antes/después;
no se ha calculado un hash completo del TXT de 7,8 GB.

## Correspondencia, estructura y cobertura

| Fuente y copia bajo `Fuentes/` | Evidencia comprobada | Unidad y relación posible |
| --- | --- | --- |
| DGT, `parque_vehiculos_202512.txt` | 38.641.165 registros, 45 columnas, delimitador `\|`. Lectura Latin-1 compatible; codificación original exacta pendiente. Coincide en nombre y esquema con el recurso mensual de diciembre de 2025. | Registro de vehículo sin identificador individual publicado. `PROVINCIA`, `MUNICIPIO`, `TIPO_DGT`, `PROPULSION`, `CATELECT`. Código municipal informado de cinco dígitos; no necesita concatenar provincia. |
| GVA, `Trafico.gpkg` | 17 capas `Aforos2009`–`Aforos2025`; 513 tramos en 2025. `clau_tramo` es único dentro de cada capa. IMD está almacenada como texto. | Tramo y año. `carretera`, `pk_inicio`, `pk_fin`, `tipo_medida_trafico`, `imd`, geometría LINESTRING. Referencia EPSG:25830 declarada. |
| INE, `Poblacion.csv` | 121.995 filas, cinco columnas, 2021–2025; sexo Total/Hombres/Mujeres. 542 códigos municipales valencianos, 8.130 filas del ámbito. | Municipio × sexo × año, además del total nacional. Clave compuesta sin repeticiones. Código al inicio de `Municipios`; `Total` usa punto como separador de miles. |
| MITECO, `instalaciones_actuales.csv` | 43.610 filas, 27 columnas; UTF-16LE sin BOM. 12.214 instalaciones y 36.465 puntos identificados en la copia nacional. En Comunitat Valenciana: 5.244 filas, 1.526 instalaciones, 4.402 puntos. | Detalle por conector dentro de punto e instalación. Hay identificadores para los tres niveles; no usar el número de filas como número de instalaciones o puntos. |
| INE, `Renta.csv` | 3.009.312 filas, seis columnas, 2015–2023 y seis indicadores. 439.506 filas municipales, 567.918 de distrito y 2.001.888 de sección. | Territorio × indicador × año. Clave de municipio/distrito/sección/indicador/año sin repeticiones. Los campos vacíos de los niveles inferiores son estructurales. |
| i-DE, `Demanda_energetica.csv` | Esquema de capacidad de **demanda**: capacidad firme disponible/ocupada/admitida, tensión, posiciones y coordenadas UTM. El identificador de punto de conexión no se repite en la copia. | Punto de conexión de la distribuidora; no es demanda energética consumida ni capacidad de toda la red española. No consta aquí un CRS/huso inequívoco ni fecha de referencia del contenido. |
| IGN, `RT_ALICANTE_ALACANT_gpkg/`, `RT_CASTELLON_CASTELLO_gpkg/`, `RT_VALENCIA_gpkg/` | Se inspeccionan los cinco GeoPackages de cada carpeta. La capa `rt_tramo_vial` tiene 414.419, 236.418 y 546.609 filas respectivamente. EPSG:4258 declarado; geometrías con dimensión Z. | La fila relaciona tramo y vial. `id_tramo + id_vial` es único dentro de cada provincia, pero `id_tramo` se repite. Hay campos de sentido, acceso, estado y tipo de vehículo. |
| OSM, `ubicaciones_candidatasgpkg/valencia.gpkg` | 20 capas. El README declara datos a 2026-09-09T20:21:20Z. `srs_id=100000` es interno, con definición WGS84/OGC:CRS84 y ejes longitud/latitud. | Elementos OSM puntuales y polígonos; `osm_id`, `code`, `fclass`, `name`. Aparcamientos/gasolineras están en capas `traffic`; hoteles/supermercados en `pois`. |

El tamaño/fecha de un archivo local no prueba la fecha de descarga ni la edición
oficial. GVA y IGN tienen metadatos de almacenamiento, pero quedan por vincular
las copias a la edición y créditos concretos del proveedor. No se ha comparado el
hash de ninguna copia con una distribución remota ni descargado datos adicionales.

## Hallazgos y acciones necesarias

### 1. DGT limita seriamente una comparación municipal — gravedad alta

En las provincias 03, 12 y 46 hay **4.124.363** registros. **845.077 (20,49 %)**
tienen el municipio vacío. Solo hay **106** códigos municipales informados:
38 de Alicante, 12 de Castellón y 56 de Valencia. La ausencia no significa parque cero.

El [diseño oficial mensual de DGT, sección 3.3](https://www.dgt.es/export/sites/web-DGT/.galleries/downloads/dgt-en-cifras/matraba/Interfaz-de-Salida-Fichero-Parque-Mensual.pdf)
documenta la supresión del municipio para poblaciones inferiores a 10.000 habitantes.
También describe enmascaramiento de atributos poco frecuentes. La causa estructural
está documentada; no se ha atribuido individualmente cada vacío a una causa.
El [listado mensual](https://www.dgt.es/menusecundario/dgt-en-cifras/matraba-listados/parque-vehiculos-mensual.html)
incluye la distribución de diciembre de 2025; se trata de una instantánea mensual
provisional, distinta del parque anual consolidado.

**Acción:** buscar tablas municipales agregadas adecuadas o definir explícitamente
qué puede estimarse con esta cobertura. No eliminar ni imputar automáticamente
los municipios suprimidos. Los 23 duplicados exactos en las primeras 10.000 filas
no justifican borrar vehículos: dos vehículos distintos pueden compartir todos
los atributos publicados cuando no existe identificador individual.

### 2. MITECO requiere un lector explícito y contar niveles — gravedad alta

La lectura CSV estricta falla en la línea física 2.804 por comillas no estándar.
Una lectura Python `csv` permisiva obtiene 43.610 registros, todos de 27 campos,
sin descartar registros. Ese perfil no certifica toda la semántica de los campos
de texto; deberá comprobarse antes de materializar Silver.

Las coordenadas aparecen como expresiones `="39.5948000"` y la potencia incluye
unidad, por ejemplo `350,00 kW`. No se han ejecutado fórmulas. Las expresiones de
diagnóstico interpretan todas las coordenadas y potencias: no hay pares incompletos,
fuera del dominio geográfico global ni `(0,0)`. Esto no certifica ubicación correcta
en municipio, dirección o instalación. Las fechas de modificación interpretables
van de 2023-07-04 a 2026-09-09; no son fechas de instalación.

La clave instalación–punto–conector presenta **seis repeticiones**. En accesibilidad,
**39.406 filas (90,36 %)** indican `NODISPONIBLE`. La potencia diagnóstica va de
0,06 a 1.000 kW: extremos que requieren contraste, sin descartarlos por criterio
automático. **Acción:** revisar claves repetidas, normalizar formatos conservando
trazabilidad y definir si cada indicador cuenta instalaciones, puntos o conectores.
La suma de potencias de conectores no acredita capacidad simultánea de una instalación.

### 3. INE mezcla categorías y niveles — gravedad media

En población hay nueve valores no numéricos de `Total` en la copia nacional.
No sumar la categoría `Total` con Hombres y Mujeres ni el total nacional con municipios.
En renta hay **85.270 vacíos**, **162.132 valores `.`** y **158 valores `..`** de
`Total`; se conservan como ausencia/protección pendiente de interpretar según INE.
No convertirlos en cero ni tratar los vacíos de `Distritos`/`Secciones` como errores.

Renta contiene 543 códigos del ámbito frente a 542 en población. El código adicional
`12066`, etiquetado «Gatova», tiene 54 filas y ningún total numérico. Su vigencia y
correspondencia deben contrastarse con un nomenclátor oficial; no remapearlo por nombre
ni incorporarlo como municipio adicional al Gold. **Acción:** elegir nivel, indicador
y año y comprobar vigencia de claves antes de integrar. No se ha fijado todavía
un año común ni realizado un join.

### 4. IGN relaciona entidades; la geometría no basta para rutas — gravedad alta

`id_tramo` presenta 33.490, 12.203 y 33.444 repeticiones en Alicante, Castellón y
Valencia. La documentación `leeme_RT_Prov_gpkg.txt` explica que la capa resulta de
una relación de tramos con viales; la clave compuesta no se repite en cada provincia.
Por tanto, no son errores que deban eliminarse automáticamente.

**Acción:** distinguir geometría de tramo de sus asociaciones antes de medir longitud
o construir accesibilidad. Faltan conectividad, restricciones reales, coherencia
entre provincias y validación topológica. La ausencia de geometrías SQL nulas en `rt_tramo_vial` y
un contenedor íntegro no acredita una red enrutable. No se ha elegido un CRS de trabajo.

### 5. GVA y OSM tienen límites de cobertura — gravedad media

GVA varía entre 488 y 614 tramos por año: no asumir un panel idéntico ni sumar años
como tráfico actual. La unicidad por capa no prueba estabilidad del tramo entre años.
Los tipos de medida requieren interpretar datos medidos y estimados con el proveedor;
su cobertura autonómica no sustituye aforos de todas las carreteras.

OSM contiene candidatos como puntos y polígonos. Hay 801 aparcamientos puntuales
y 12.042 poligonales; 772 gasolineras puntuales y 565 poligonales. Estos recuentos
son de elementos, **no de establecimientos únicos**. No sumar capas sin analizar
coincidencias. La capa `transport` tiene una extensión declarada hasta latitud
35,7094 y longitud 3,0631, más allá del ámbito principal: queda por inspeccionar
esos objetos. No se han borrado puntos lejanos ni recortado geometrías. Datos
© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
distribución Geofabrik, bajo ODbL 1.0; condiciones de publicación en la Entrega 02.

### 6. i-DE: CRS y derechos pendientes — gravedad alta para su integración

El esquema permite confirmar consumo/demanda frente a generación. Sin embargo,
la denominación UTM no identifica huso ni datum. Los rangos numéricos muestran
coordenadas que requieren verificar formato, orden de ejes y referencia espacial;
una conversión numérica exitosa no garantiza posición correcta.

**Acción:** confirmar documentación espacial, fecha y condiciones de reutilización
antes de usarlo en Silver o publicar resultados. No se incluyen aquí registros,
capacidades de nodos ni perfiles provinciales. Sigue siendo una fuente complementaria
con cobertura propia de la distribuidora y capacidad informativa, sin garantía de conexión.

## Resultado y siguiente paso

Los ocho bloques son técnicamente accesibles con este entorno local. La combinación
es viable como preparación gradual, pero **no hay aún cobertura municipal completa
de parque ni integración espacial validada**. Antes de fijar Gold, resolver DGT,
definir el recuento de recarga y confirmar referencias territoriales/espaciales.
Después se acordarán granularidad, criterio temporal y transformaciones de Silver.

No se han creado Silver, Gold, variables predictivas ni modelos. Las pruebas del
lector cubren codificación, preservación de códigos, anchos incorrectos, duplicados,
niveles de renta y cabeceras geométricas. Los resultados observados tienen confianza
alta como recuentos de las copias inspeccionadas, con la salvedad del lector permisivo
de MITECO; las propuestas de tratamiento siguen siendo pendientes, no correcciones aplicadas.
