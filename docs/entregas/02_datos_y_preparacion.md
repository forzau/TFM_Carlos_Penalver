# Entrega 02 - Datos y preparación

**Proyecto:** localización de nuevos puntos de recarga para vehículos eléctricos en la Comunitat Valenciana.

**Estado:** apartados 1-3 redactados y apartado 4 en curso, con Bronze formalizado y base territorial Silver preparada el 15 de octubre de 2026. Se adopta Distintivo 0 como aproximación documentada. El resto de Silver, Gold y apartado 5 siguen pendientes. Las salvedades de uso se recogen en el apartado 3 y en el catálogo del nuevo recurso.

## 1. Qué datos necesita vuestro producto

El producto apoyará a administraciones públicas y operadores de recarga en la decisión de dónde ampliar la infraestructura pública y qué zonas priorizar. Combinará demanda potencial, infraestructura existente y accesibilidad, explicando los factores que justifican la prioridad. El ámbito inicial comprende Alicante/Alacant, Castellón/Castelló y Valencia/València. La presentación final se orientará a una aplicación web que consuma los datos preparados.

### Qué representa una observación

Una observación representará la unidad espacial evaluada para ampliar la infraestructura, con su localización y variables de demanda, cobertura y accesibilidad. No equivale a un registro original: las fuentes contienen vehículos, municipios, tramos, instalaciones, nodos y puntos de interés.

La unidad concreta sigue pendiente: zona territorial o ubicación candidata. Se decidirá tras comprobar la granularidad y compatibilidad de las fuentes, sin fijar todavía una cuadrícula, sección censal o radio. Un dato municipal no se interpretará como una medición individual de cada ubicación.

### Datos imprescindibles y deseables

| Prioridad | Información | Uso |
| --- | --- | --- |
| Imprescindible | Parque de vehículos con referencia municipal e indicador de demanda potencial. | Se adopta Distintivo 0 como aproximación para todos los municipios y se conserva BEV/PHEV donde esté observado. No equivale a un desglose exacto ni mide recargas efectivas. |
| Imprescindible | Población y códigos territoriales. | Contextualizar demanda residencial y comparar territorios. |
| Imprescindible | Localización de recarga pública existente y características técnicas informadas. | Evaluar cobertura e infraestructura disponible. |
| Imprescindible | Red viaria y referencias territoriales oficiales. | Estudiar accesibilidad y asignar datos al territorio; las superficies y densidades requieren recintos adecuados. |
| Imprescindible para evaluar corredores | Intensidad Media Diaria de tráfico por tramo. | Incorporar movilidad de paso donde haya aforos; ausencia de dato no significa tráfico cero. |
| Deseable | Renta e indicadores socioeconómicos. | Contextualizar adopción potencial de VE, sin asumir causalidad automática. |
| Deseable | Capacidad eléctrica y localización de nodos. | Añadir una referencia orientativa, sin garantizar conexión. |
| Deseable | Aparcamientos, estaciones de servicio, comercios y otros puntos de interés. | Concretar candidatos dentro de las zonas priorizadas, sin acreditar disponibilidad del terreno. |

Si se recomiendan emplazamientos concretos, la identificación de candidatos será necesaria para esa función; una evaluación inicial por zonas permite comenzar con el núcleo territorial.

### Granularidad e histórico

El TFM utilizará versiones estáticas y conservadas para reproducir el análisis. La planificación necesita una fotografía territorial fechada, sin conocer en tiempo real si un conector está ocupado. Una evolución futura podría actualizar cada fuente a su ritmo.

La población y el parque aportarán contexto territorial; el tráfico corresponde a tramos y años; recarga, nodos y puntos de interés tienen localización propia. Se comprobará cómo relacionarlos antes de elegir la unidad final.

La auditoría confirma población de 2021-2025, aforos de 2009-2025 y renta de 2015-2023. El parque local corresponde al recurso mensual provisional de diciembre de 2025; OSM declara datos a 9 de septiembre de 2026. El histórico puede aportar contexto, pero no es necesario utilizarlo entero. Para recarga interesa una exportación fechada. Quedan pendientes ediciones exactas de cartografía y fecha de referencia de nodos.

No se ha fijado un año común. Se distinguirán periodo de referencia, fecha de publicación y descarga: fuentes recientes no necesariamente describen el mismo momento. Tampoco se dispone todavía de demanda real de recarga ni de una etiqueta validada de «ubicación óptima»; el objetivo y la evaluación de Machine Learning deben concretarse antes de elegir modelos.

## 2. Fuentes reales y viabilidad

Los ocho bloques principales se han localizado y descargado. La auditoría del 14 de octubre de 2026 comprueba esquemas, recuentos y limitaciones de las copias locales; sus resultados se recogen en el apartado 4 y en el [diagnóstico técnico](../AUDITORIA_FUENTES.md). Esto acredita accesibilidad técnica, pero todavía no integración ni calidad suficiente para ML. Persisten versiones y condiciones particulares pendientes.

Se utilizarán descargas públicas y exportaciones de los proveedores, conservando versiones fijas para el TFM y sin depender inicialmente de scraping.

### Fuentes y acceso

| Fuente y adquisición | Cobertura, actualización y cautelas de viabilidad |
| --- | --- |
| **DGT - [Microdatos de parque de vehículos mensual](https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Microdatos-de-parque-de-vehiculos-mensual/).** Descarga de listados ZIP y diseño de registro; copia nacional de diciembre de 2025 en TXT. | Instantánea mensual provisional nacional. El [diseño de registro](https://www.dgt.es/export/sites/web-DGT/.galleries/downloads/dgt-en-cifras/matraba/Interfaz-de-Salida-Fichero-Parque-Mensual.pdf) suprime municipios de menos de 10.000 habitantes. Lectura completa ejecutada con memoria acotada; cobertura municipal insuficiente para asumir valores observados en todo el ámbito. |
| **Generalitat Valenciana - [Aforos de la red autonómica](https://dadesobertes.gva.es/dataset/intensidad-media-diaria-anual-imd-de-trafico-por-tramos-red-autonomica-de-carreteras-2009-2025).** Descarga del GeoPackage; también ofrece WFS y documentación. | Red autonómica valenciana, serie 2009-2025 y actualización anual declarada. Abierto preliminarmente en QGIS. No representa todas las vías estatales, provinciales o urbanas; deben comprobarse identificadores y comparabilidad entre años. |
| **INE - [Censo anual de población](https://ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176992&idp=1254735572981&menu=resultados).** Selección y descarga de tablas; copia localizada en CSV. | Nacional, con resultados municipales y serie localizada 2021-2025. Información anual. Los códigos municipales permitirán seleccionar el ámbito; se comprobarán tabla concreta, categorías agregadas y detalle de las variables. |
| **MITECO - [Puntos de Recarga de Vehículos Eléctricos](https://catalogo.datosabiertos.miteco.gob.es/catalogo/es/dataset/6ee8d46f-93bd-478f-8e29-3ba4f6d8405c).** El catálogo enlaza una [exportación pública en CSV](https://energia.serviciosmin.gob.es/Ripree/ExportarInstalaciones/Export). | Infraestructura de acceso público en España; registro actualizado con información remitida por operadores. Se conservará una exportación fechada. Hay valores `DESCONOCIDO` y `NODISPONIBLE`; falta revisar cobertura y relaciones instalación/punto/conector para evitar recuentos duplicados. |
| **INE - [Atlas de Distribución de Renta de los Hogares](https://www.ine.es/dynt3/inebase/index.htm?capsel=12384&padre=5608).** Descarga de tablas territoriales; copia con serie 2015-2023. | Municipios, distritos y secciones censales; serie anual con desfase de publicación. Los nulos requieren interpretar el nivel territorial. La renta no acredita por sí sola demanda de recarga. |
| **i-DE - [Mapa de capacidad de consumo](https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo).** Consulta y descarga de los ficheros tabulares ofrecidos. | Puntos de conexión de su propia red; actualización mínima mensual declarada. La copia contiene capacidad de demanda; cobertura efectiva, fecha y CRS pendientes de verificar. Capacidad informativa, sin garantía de conexión. CNMC queda como posible contraste, sin dataset equivalente confirmado. |
| **IGN/CNIG - [Redes de Transporte](https://centrodedescargas.cnig.es/CentroDescargas/catalogo.do?Serie=REDTR).** Descarga de GeoPackages provinciales de Alicante, Castellón y Valencia. | Producto nacional con nuevas versiones cartográficas. Los tres archivos se abrieron preliminarmente en QGIS. Falta comprobar atributos y geometrías: disponer de líneas viarias no garantiza una red preparada para calcular rutas. |
| **OpenStreetMap, distribuido por [Geofabrik - Valencia](https://download.geofabrik.de/europe/spain/valencia.html).** Extracto regional en GeoPackage, Shapefile o PBF. | Información colaborativa, con extractos renovados y fechados. Se conservará una versión concreta. Deben comprobarse cobertura y categorías; no garantiza inventario completo de servicios. Los elementos alejados deben inspeccionarse antes de excluirlos. |

Se ha identificado además el producto de [límites y unidades administrativas del IGN/CNIG](https://centrodedescargas.cnig.es/CentroDescargas/detalleArchivo?sec=9000029). Falta comprobar si ya se dispone de recintos adecuados o adquirirlos cuando corresponda para asignación territorial y superficies; su disponibilidad local no está confirmada.

### Estabilidad y alternativas

Las fuentes cuentan con proveedores y documentación identificables, pero no se ha comprobado estabilidad permanente de enlaces y esquemas. Antes del procesamiento se registrarán recurso, versión, periodo y fecha de adquisición. Conservar las entradas permitirá reproducir el TFM aunque cambien las publicaciones.

Si una fuente clave dejara de estar accesible, se utilizaría la última copia conservada indicando su antigüedad. Si faltara MITECO, se estudiaría una extracción de cargadores de OpenStreetMap como alternativa provisional, verificando atributos y cobertura; no se asumiría equivalencia ni se mezclarían ambas sin revisar coincidencias. Si faltara renta o capacidad eléctrica, se mantendría el núcleo disponible y se explicaría qué dimensión queda sin valorar.

Hay fuentes reales y técnicamente accesibles para demanda potencial, infraestructura y contexto espacial. La auditoría detecta limitaciones relevantes de cobertura y recuento. La viabilidad de integración sigue **pendiente**: faltan resolver esos hallazgos, unidad de observación, compatibilidad temporal/espacial y objetivo analítico posterior.

## 3. Uso, privacidad y datos personales

Revisión de condiciones realizada el **14 de octubre de 2026** sobre las páginas y metadatos públicos de las fuentes. Acceso público y licencia abierta son conceptos distintos. Las conclusiones siguientes deben asociarse después a las versiones concretas descargadas; las condiciones particulares de cada recurso deben comprobarse antes de publicar muestras o resultados derivados.

### Licencias y condiciones de reutilización

| Fuente | Condiciones identificadas y aplicación al proyecto |
| --- | --- |
| **DGT - parque de vehículos** | La auditoría identifica la copia como mensual. La [ficha oficial mensual de DGT en datos.gob.es](https://datos.gob.es/es/catalogo/e00130502-microdatos-parque-de-vehiculos-mensual) declara **CC BY 4.0** en las distribuciones nacional y provincial. Permite reutilización, también comercial, con atribución, enlace a la licencia e indicación de cambios. Se citarán DGT, recurso mensual y versión utilizada. |
| **Generalitat Valenciana / ICV - aforos** | La [ficha de aforos](https://dadesobertes.gva.es/dataset/intensidad-media-diaria-anual-imd-de-trafico-por-tramos-red-autonomica-de-carreteras-2009-2025) y sus [metadatos públicos](https://dadesobertes.gva.es/api/3/action/package_show?id=intensidad-media-diaria-anual-imd-de-trafico-por-tramos-red-autonomica-de-carreteras-2009-2025) indican **Creative Commons Attribution (CC BY)**. Exige reconocimiento de la fuente. La versión no está especificada en esos metadatos; no se da por confirmada CC BY 4.0 para el fichero concreto. |
| **INE - población y renta** | El [aviso legal del INE](https://www.ine.es/dyngs/AYU/index.htm?cid=125) establece **CC BY 4.0** como licencia general de su información estadística, salvo indicación contraria y para información cuya fuente original sea el INE. Permite uso comercial y no comercial. Se indicarán fuente, última actualización disponible y elaboración propia si hay tratamiento, sin sugerir respaldo del INE. |
| **MITECO - recarga pública** | Los [metadatos oficiales del conjunto de recarga](https://catalogo.datosabiertos.miteco.gob.es/catalogo/api/3/action/package_show?id=6ee8d46f-93bd-478f-8e29-3ba4f6d8405c) declaran **CC BY 4.0**. El [aviso de reutilización del portal](https://www.datosabiertos.miteco.gob.es/es/aviso-legal.html) permite fines comerciales y no comerciales, exigiendo fuente, fecha de actualización disponible, conservación de metadatos y ausencia de apariencia de patrocinio. |
| **i-DE - capacidad de consumo** | No se ha identificado una licencia abierta específica en la información revisada del [mapa](https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo). Su [aviso legal, apartados 2 y 3](https://www.i-de.es/es/informacion-legal), reserva derechos y restringe el uso y la reproducción comercial sin autorización. La posibilidad de descargar no acredita permiso para redistribuir. Debe aclararse el alcance permitido para el TFM compartido y una futura web comercial antes de publicar sus datos o derivados. |
| **IGN/CNIG - red viaria y, si se incorpora, límites administrativos** | La [licencia de uso de IGN](https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf) y la [ficha de límites](https://centrodedescargas.cnig.es/CentroDescargas/detalleArchivo?sec=9000029) establecen condiciones **compatibles con CC BY 4.0**. Se respetará el reconocimiento específico de cada producto y de sus titulares; en los derivados de Redes de Transporte se usará la fórmula indicada para IGR-RT, con el año de la versión utilizada. |
| **OpenStreetMap / Geofabrik - candidatos** | El [extracto de Geofabrik](https://download.geofabrik.de/europe/spain/valencia.html) se distribuye bajo **ODbL 1.0**. Permite uso comercial, con atribución a OpenStreetMap y sus colaboradores y aviso de licencia. La [licencia de OSM](https://www.openstreetmap.org/copyright) y el [texto ODbL, apartados 4.4-4.6](https://opendatacommons.org/licenses/odbl/1-0/) regulan las obligaciones sobre bases derivadas utilizadas públicamente. |

Para los datos bajo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.es), se conservarán autoría, enlace al recurso y a la licencia, versión o fecha e indicación de las transformaciones realizadas. Los resultados se identificarán como elaboración propia; no se presentarán como recomendaciones oficiales ni se utilizarán logotipos para insinuar aval de los proveedores.

**OSM requiere una decisión de publicación específica:** si el Gold incorpora una base derivada de OSM y se usa públicamente, incluso a través de una visualización, puede ser obligatorio ofrecer esa base o las modificaciones en formato legible por máquina bajo las condiciones de ODbL. La obligación no equivale automáticamente a licenciar todo el código de la web bajo ODbL. Se revisará la estructura real del Gold y su compatibilidad antes de publicarlo; los créditos del mapa incluirán «© OpenStreetMap contributors» y un enlace a su licencia.

**i-DE queda como condición pendiente**, no como fuente libremente reutilizable confirmada. Mientras se aclara, se documentará el acceso sin redistribuir sus ficheros o derivados. Si no se obtiene una autorización o unas condiciones adecuadas, se podrá mantener el núcleo del producto sin ese indicador complementario.

### Datos personales y minimización

La finalidad del producto es comparar territorios e infraestructura, no identificar personas, hogares ni propietarios de vehículos. No necesita nombres particulares, documentos de identidad, matrículas, bastidores ni contactos personales. Se utilizarán resultados territoriales agregados de población y renta y características de infraestructura. No se solicitarán datos identificativos adicionales.

Antes de preparar las muestras y el Gold se comprobará el contenido efectivo de los archivos; todavía no se puede certificar que todas las descargas carezcan de datos personales. Se aplicará la minimización prevista en el [RGPD, artículo 5.1.c](https://www.boe.es/buscar/doc.php?id=DOUE-L-2016-80807):

- En DGT se seleccionarán solo los campos necesarios para los recuentos territoriales y la clasificación de vehículos; se excluirán de las salidas identificadores individuales y atributos innecesarios, si estuvieran presentes.
- En INE se mantendrá el nivel agregado publicado, sin intentar reconstruir personas, hogares o valores protegidos mediante cruces de datos.
- En recarga y POI se conservarán localización, categoría y características útiles, excluyendo contactos o datos de personas físicas que no aporten valor. [Geofabrik ya omite nombres, identificadores de usuarios e identificadores de cambios de colaboradores](https://download.geofabrik.de/europe/spain/valencia.html); esto no certifica ausencia de información personal en todos los atributos de los POI.
- Antes de publicar una muestra se revisarán identificadores y combinaciones que puedan facilitar reidentificación, especialmente en recuentos pequeños. La agregación territorial por sí sola no garantiza anonimato.

Los originales existentes se conservan intactos fuera de Git. No se publicarán registros personales innecesarios ni se asumirán permisos de redistribución por su mera disponibilidad pública. La revisión de licencias y los esquemas comprobados están documentados; la selección de campos y revisión de reidentificación siguen pendientes antes de publicar muestras o Gold.

## 4. Preparación de datos: Bronze → Silver → Gold

### Bronze/Raw y auditoría ejecutada

Los originales se mantienen por fuente en `Fuentes/`, fuera de Git y sin modificar,
mover ni duplicar los ficheros pesados. Esta colección constituye la entrada Raw/Bronze
inicial. Las fuentes todavía no se unen: conservar procedencia y versiones permite
revisar las transformaciones posteriores.

Se ha preparado un entorno Python 3.12 con DuckDB 1.5.0 y ejecutado
`src/auditar_fuentes.py` sobre cinco textos y 17 GeoPackages. Se han comprobado
recuentos completos, esquemas, vacíos, categorías seleccionadas y claves candidatas.
Las geometrías se inspeccionan mediante metadatos SQLite y muestras de cabeceras;
no se ha validado todavía toda su geometría ni topología.

El [README](../../README.md#reproducción) contiene las instrucciones de ejecución.
El [diagnóstico por fuente](../AUDITORIA_FUENTES.md) identifica cada fichero esperado,
cobertura, campos útiles y acciones pendientes. El perfil detallado se genera en
`resultados/auditoria/perfil.json`; contiene rutas relativas, tamaños, fechas locales,
esquemas y recuentos, y queda excluido de Git. Las fechas locales no acreditan por
sí mismas fecha de adquisición ni edición oficial. Se comprobó que tamaño y fecha
de modificación de los originales no cambiaron durante la ejecución.

Los principales hallazgos que condicionan Silver son:

- DGT: 106 municipios valencianos informados y 20,49 % de registros del ámbito sin
  municipio. La supresión documentada impide interpretar ausencia como cero vehículos.
- MITECO: formato UTF-16LE, comillas no estándar, coordenadas con envoltorio de hoja
  de cálculo y potencia con unidad; filas de conectores y seis repeticiones de clave.
- INE: categorías de sexo y total nacional en población; niveles territoriales y
  valores ausentes/protegidos en renta. Hay un código de renta adicional pendiente de vigencia.
- IGN/OSM/GVA: relaciones entre entidades, puntos y polígonos y distintos CRS;
  requieren definición de recuentos y comprobación espacial antes de integrar.
- i-DE: esquema de capacidad de demanda confirmado; CRS, fecha y reutilización pendientes.

### Alternativa municipal DGT verificada

El 15 de octubre de 2026 se comprueba el [Excel municipal oficial de DGT de 2025](https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Datos-municipales-informacion-general-2025/).
Los 542 códigos del ámbito presentes en población están en esa tabla, incluidos
municipios pequeños. Hay tres filas provinciales de municipio sin especificar
que se mantendrán separadas, sin tratarlas como municipios o totales provinciales.

Se adopta **Distintivo 0 como aproximación documentada de demanda potencial**,
conservando el detalle BEV/PHEV disponible en los microdatos. La etiqueta no
equivale exactamente a BEV + PHEV y la columna `Electrificado` no permite deducir
el desglose por resta. El panel oficial también agrupa municipios menores de
10.000 habitantes, por lo que no resuelve ese desglose.

El [informe específico](../DGT_COBERTURA_MUNICIPAL.md) recoge fuentes, cobertura,
significado, condiciones pendientes de la nueva descarga y reproducción con
`src/auditar_dgt_municipal.py`. Los originales previos siguen intactos; la descarga
adicional queda preservada en `datos/bronze/dgt_municipal/2025/` y su perfil en
`resultados/auditoria_dgt/`, ambas ubicaciones fuera de Git.

### Registro formal de Bronze

El 15 de octubre de 2026 se formaliza el [catálogo de Bronze](../CATALOGO_BRONZE.md)
en `config/catalogo_bronze.json`: inicialmente nueve recursos en ocho bloques,
ampliados con dos referencias territoriales oficiales hasta once recursos en
nueve bloques. Se documentan proveedor, acceso, versión y periodo acreditados, adquisición,
cobertura, unidad original, formato y condiciones de uso revisadas. Los metadatos
no confirmados permanecen explícitamente pendientes; no se atribuye a los datos
la fecha de modificación de sus archivos.

El registro ampliado abarca 39 archivos, incluidos los documentos acompañantes. Los
originales previos permanecen intactos en `Fuentes/`; la copia municipal de DGT
y su ficha se preservan en una ubicación estable sin duplicar los archivos pesados.
`src/catalogar_bronze.py` genera manifiestos locales con rutas relativas, tamaños
y SHA-256 por bloques, y permite comprobar posteriormente su integridad sin
sobrescribir la referencia. Datos y manifiestos detallados quedan fuera de Git.
Persisten las aclaraciones de versiones, adquisiciones y licencias indicadas en
el catálogo; registrar una entrada no da por resueltas sus condiciones de uso.

### Referencias territoriales y procedencia comprobadas

Se incorporan la relación INE de municipios y códigos a 01-01-2025 y una respuesta
del servicio WFS de unidades administrativas del IGN conservada el 15-10-2026.
El [informe de referencias y procedencia](../REFERENCIAS_TERRITORIALES.md) documenta
la coincidencia de los 542 códigos valencianos entre INE, IGN, población y DGT.
El GeoJSON contiene también las tres provincias y la comunidad autónoma; su
recuento coincide con el del proveedor, sin truncamiento observado. Se conservan
respuestas y recibos de adquisición sin recortar ni simplificar las geometrías.

El código adicional `12066` de renta corresponde al código histórico de Gátova;
el vigente es `46902`, ya presente en los datos. Las 54 filas de 12066 no aportan
valores informados. Se mantiene Bronze intacta y se documenta su separación
posterior en Silver, evitando contar otro municipio o reemplazar el código a
ciegas y generar repeticiones.

Se identifican las tablas INE **68065** (población) y **30824** (renta), así como el
descargable GeoPackage de aforos. El CSV de población es idéntico al descargable
oficial consultado; el de renta difiere. Por ello se preserva la copia local por
su huella y no se inventa una edición exacta. Las fechas históricas de adquisición
no recuperadas quedan documentadas como desconocidas. La referencia territorial
consultada en 2026 no acredita por sí sola la geometría histórica de cada año.

`src/incorporar_referencias.py` permite la adquisición sin sobrescribir copias;
`src/auditar_referencias.py` reproduce las comprobaciones sin red. El manifiesto
inicial se conserva y el ampliado mantiene las huellas de sus 31 entradas.

### Silver: base territorial preparada; restantes fuentes y Gold pendientes

Se documenta un [plan de Silver en ocho fases](../PLAN_SILVER.md): reglas comunes,
base territorial, parque/población/renta, recarga existente, tráfico/red viaria,
POI, capacidad eléctrica y relaciones/validación conjunta. Cada fase define las
salidas y sus comprobaciones de cierre. El tratamiento de i-DE se organiza como
complemento y su incertidumbre técnica no bloquea la preparación del resto.
En la fase 1 se aceptan las convenciones comunes y se documenta un
[diccionario inicial de salidas](../DICCIONARIO_SILVER.md) con unidades de fila,
campos, tipos lógicos y claves por fuente. El contraste focal de MITECO distingue
las seis repeticiones nacionales de la clave triple de su ausencia en la copia
filtrada a CV; conserva horarios, servicios y pagos en el detalle cuando varían
dentro de instalaciones o puntos. La [configuración técnica](../CONFIGURACION_SILVER.md)
cierra la fase 1 con Parquet/GeoParquet, tipos explícitos y DuckDB espacial,
probados sobre muestras. Se adopta EPSG:25830 para las operaciones métricas
regionales admitidas y se conservan como pendientes las referencias espaciales de
MITECO e i-DE. Los PK de aforos mantienen su notación textual y las modificaciones
MITECO conservan fecha y hora en el diseño.

La [fase 2, base territorial](../BASE_TERRITORIAL_SILVER.md), genera las dos primeras
tablas: `municipios` y `recintos_municipales`, con 542 filas cada una y relación uno
a uno por código. Se verifican las huellas de entrada, las claves y geometrías,
la cobertura respecto a los tres recintos provinciales y el autonómico, y la
conservación de atributos y geometría tras exportar Parquet/GeoParquet. No se
necesitan reparaciones ni exclusiones geométricas. Se conservan 58 diferencias
de nombre entre INE e IGN, con los códigos como referencia de correspondencia.
Las fechas INE 2025 y consulta IGN 2026 permanecen separadas. El informe detallado
y las salidas quedan fuera de Git; se versionan código, reglas y pruebas.

La auditoría permite concretar las transformaciones necesarias. La base territorial
de Silver está materializada y el resto de Silver y Gold siguen pendientes.
La cobertura municipal de DGT queda resuelta
para la aproximación adoptada y las referencias territoriales están incorporadas;
faltan las transformaciones por fuente desde la fase 3,
además de la unidad final y el criterio temporal que se justificarán para Gold.
Silver aplicará validaciones y formatos explícitos con trazabilidad; Gold definirá
qué representa cada fila y qué variables aporta a la fase siguiente. No se presentan
estos pasos como completados ni se ha entrenado un modelo.
