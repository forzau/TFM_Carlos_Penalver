# Entrega 02 - Datos y preparación

**Proyecto:** localización de nuevos puntos de recarga para vehículos eléctricos en la Comunitat Valenciana.

**Estado a 22-10-2026:** preparación Bronze → Silver → Gold completada y reproducible mediante un único script. Gold reúne trece tablas y 135 columnas para contexto municipal, oferta, candidatos y variables normalizadas. La entrega deja los datos preparados para la fase analítica posterior, con sus limitaciones explícitas; todavía no hay ranking, predicciones de uso ni mapas.

## 1. Qué datos necesita vuestro producto

El producto apoyará a administraciones públicas y operadores de recarga en la decisión de dónde estudiar nuevas instalaciones públicas. Se comienza por recarga de destino: contexto municipal y posterior revisión de candidatos. Se preparan demanda potencial, oferta registrada y separación geométrica respecto a esa oferta, sin afirmar accesibilidad real, suficiencia o viabilidad de conexión. El ámbito comprende Alicante/Alacant, Castellón/Castelló y Valencia/València. La presentación futura permitirá consultar demanda, oferta y prioridad de estudio en modos separados del mapa.

### Qué representa una observación

Hay dos niveles principales: una fila por municipio para demanda y contexto, y una fila por elemento candidato OSM y escenario de oferta para separación geométrica y variables normalizadas. Las tablas auxiliares conservan instalaciones, vínculos territoriales y diagnósticos. Un candidato es un elemento cartográfico pendiente de revisión, no un establecimiento único ni una ubicación viable confirmada.

Los 542 municipios se mantienen, incluidos los 52 sin candidatos preseleccionados. La demanda no se reparte entre POI; los 106 candidatos que intersectan varios municipios no reciben un código exclusivo arbitrario. No se inventa detalle intramunicipal, cuadrícula o radio de cobertura a partir de recuentos municipales.

### Datos imprescindibles y deseables

| Prioridad | Información | Uso |
| --- | --- | --- |
| Imprescindible | Parque de vehículos con referencia municipal e indicador de demanda potencial. | Se adopta Distintivo 0 como aproximación para todos los municipios y se conserva BEV/PHEV donde esté observado. No equivale a un desglose exacto ni mide recargas efectivas. |
| Imprescindible | Población y códigos territoriales. | Contextualizar demanda residencial y comparar territorios. |
| Imprescindible | Localización de recarga pública existente y características técnicas informadas. | Evaluar cobertura e infraestructura disponible. |
| Imprescindible | Códigos y recintos territoriales oficiales. | Relacionar municipios y fuentes; conservar la escala real de la demanda y las intersecciones. |
| Deseable para recorridos posteriores | Red viaria. | Contextualizar accesibilidad; calcular rutas exigiría validar conectividad y restricciones. La Gold actual mide separación plana. |
| Imprescindible para evaluar corredores | Intensidad Media Diaria de tráfico por tramo. | Incorporar movilidad de paso donde haya aforos; ausencia de dato no significa tráfico cero. |
| Deseable | Renta e indicadores socioeconómicos. | Contextualizar adopción potencial de VE, sin asumir causalidad automática. |
| Deseable | Capacidad eléctrica y localización de nodos. | Añadir una referencia orientativa, sin garantizar conexión. |
| Imprescindible para candidatos | Aparcamientos, comercios y alojamientos cartografiados. | Conservar candidatos para revisión, sin acreditar disponibilidad del terreno. Estaciones de servicio quedan como contexto en Silver. |

La primera comparación por zonas utiliza el núcleo municipal. La identificación de candidatos permite preparar la revisión posterior de emplazamientos; no convierte cada POI en una instalación recomendada.

### Granularidad e histórico

El TFM utilizará versiones estáticas y conservadas para reproducir el análisis. La planificación necesita una fotografía territorial fechada, sin conocer en tiempo real si un conector está ocupado. Una evolución futura podría actualizar cada fuente a su ritmo.

La población y el parque aportan contexto municipal; el tráfico corresponde a tramos y años; recarga, nodos y puntos de interés conservan su localización propia. Las claves y relaciones territoriales están preparadas sin convertir un cruce espacial en una nueva entidad o repartir sus recuentos automáticamente.

Silver conserva población de 2021-2025, aforos de 2009-2025 y renta de 2015-2023. Gold selecciona parque municipal DGT a 31-12-2025, población total de 2025, renta neta media por persona de 2023 y OSM de 09-09-2026. La recarga principal procede de una exportación adquirida el 18-10-2026, sin interpretar la adquisición como fecha de instalación u operación simultánea. i-DE tiene publicación de 04-09-2026 y periodo agosto según el formato mensual; su corte exacto y algunas ediciones cartográficas siguen sin acreditarse.

No se fuerza un año común: se distinguen periodo de referencia, publicación y adquisición. No hay sesiones, energía, ocupación ni una etiqueta observada de «ubicación óptima». La fase posterior comenzará por priorización multicriterio interpretable y sensibilidad; no se fuerza aprendizaje supervisado sin una variable objetivo adecuada.

## 2. Fuentes reales y viabilidad

Los ocho bloques principales y las referencias oficiales complementarias se han descargado y preparado. Los enlaces siguientes permiten acceder a las fuentes; el apartado 4 explica su transformación hasta Gold. Se conservan copias fijas y sus metadatos para reproducir el trabajo, ya que una descarga posterior puede cambiar.

### Fuentes y acceso

| Fuente y adquisición | Cobertura, actualización y cautelas de viabilidad |
| --- | --- |
| **DGT - [Microdatos de parque de vehículos mensual](https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Microdatos-de-parque-de-vehiculos-mensual/).** Descarga de listados ZIP y diseño de registro; copia nacional de diciembre de 2025 en TXT. | Instantánea mensual provisional nacional. El [diseño de registro](https://www.dgt.es/export/sites/web-DGT/.galleries/downloads/dgt-en-cifras/matraba/Interfaz-de-Salida-Fichero-Parque-Mensual.pdf) suprime municipios de menos de 10.000 habitantes. Lectura completa ejecutada con memoria acotada; cobertura municipal insuficiente para asumir valores observados en todo el ámbito. |
| **Generalitat Valenciana - [Aforos de la red autonómica](https://dadesobertes.gva.es/dataset/intensidad-media-diaria-anual-imd-de-trafico-por-tramos-red-autonomica-de-carreteras-2009-2025).** Descarga del GeoPackage; también ofrece WFS y documentación. | Red autonómica valenciana, serie 2009-2025 y actualización anual declarada. Abierto preliminarmente en QGIS. No representa todas las vías estatales, provinciales o urbanas; deben comprobarse identificadores y comparabilidad entre años. |
| **INE - [Censo anual de población](https://ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176992&idp=1254735572981&menu=resultados).** Selección y descarga de tablas; copia conservada de la tabla 68065 en CSV. | Nacional, serie municipal 2021-2025. Se seleccionan códigos CV y categorías de sexo, separando totales; Gold usa población total 2025. La copia contrastada coincide con el descargable oficial consultado. |
| **MITECO - [Puntos de Recarga de Vehículos Eléctricos](https://catalogo.datosabiertos.miteco.gob.es/catalogo/es/dataset/6ee8d46f-93bd-478f-8e29-3ba4f6d8405c).** El catálogo enlaza una [exportación pública en CSV](https://energia.serviciosmin.gob.es/Ripree/ExportarInstalaciones/Export); se conserva el recibo de la petición POST. | Infraestructura registrada de acceso público en España. Instalación, punto y conector tienen claves y relaciones comprobadas, sin sumar sus recuentos como unidades equivalentes. Se preservan dos exportaciones: la principal adquirida el 18-10-2026 y la histórica; sus diferencias no acreditan cierres. Hay estados desconocidos y asignaciones municipales pendientes. |
| **INE - [Atlas de Distribución de Renta de los Hogares](https://www.ine.es/dynt3/inebase/index.htm?capsel=12384&padre=5608).** Descarga de tablas territoriales; copia con serie 2015-2023. | Municipios, distritos y secciones censales; serie anual con desfase de publicación. Los nulos requieren interpretar el nivel territorial. La renta no acredita por sí sola demanda de recarga. |
| **i-DE - [Mapa de capacidad de consumo](https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo).** Consulta y descarga de los ficheros tabulares ofrecidos. | Puntos de conexión de su propia red; actualización mínima mensual declarada. La copia contiene capacidad de demanda; publicación 04-09-2026 identificada por igualdad binaria y periodo agosto según formato mensual CNMC. CRS EPSG:25830 acreditado para CV y aplicado en capa complementaria: 423 puntos con relación municipal contrastada en 116 municipios. Capacidad informativa, sin garantía de conexión. CNMC queda como posible contraste, sin dataset equivalente confirmado. |
| **IGN/CNIG - [Redes de Transporte](https://centrodedescargas.cnig.es/CentroDescargas/catalogo.do?Serie=REDTR).** Descarga de GeoPackages provinciales de Alicante, Castellón y Valencia. | Atributos, relaciones y geometrías preparados, con cinco líneas degeneradas conservadas y excluidas de métricas. La red no está validada para calcular rutas; se utilizan distancias planas en Gold. |
| **OpenStreetMap, distribuido por [Geofabrik - Valencia](https://download.geofabrik.de/europe/spain/valencia.html).** Extracto regional en GeoPackage, Shapefile o PBF. | Copia fechada a 09-09-2026, categorías y relación territorial verificadas. Los elementos exteriores se conservan señalados, incluidos los alejados inspeccionados. La selección de candidatos no acredita cobertura exhaustiva, negocios únicos o disponibilidad del terreno. |

Se incorporan además la [relación oficial de municipios INE de 2025](https://www.ine.es/daco/daco42/codmun/25codmun.xlsx) y los recintos del [servicio de unidades administrativas IGN](https://www.ign.es/web/es/ign/portal/ide-area-nodo-ide-ign), obtenidos por WFS y conservados el 15-10-2026. Sus 542 códigos coinciden con población y DGT; las geometrías se mantienen sin simplificación. La cobertura municipal DGT se completa con el [Excel municipal oficial de 2025](https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Datos-municipales-informacion-general-2025/), sin imputar municipios pequeños desde los microdatos.

### Estabilidad y alternativas

Las fuentes cuentan con proveedores y documentación identificables, sin garantía de estabilidad permanente de enlaces y esquemas. Se registran recurso, versión, periodos y adquisición cuando se conocen, conservando copias y huellas SHA-256. Una descarga actual puede diferir: no se sustituye una copia ni se modifica su huella para forzar compatibilidad. Los cambios de versión se procesan en ejecuciones separadas.

Si una fuente clave dejara de estar accesible, se utilizaría la última copia conservada indicando su antigüedad. Si faltara MITECO, se estudiaría una extracción de cargadores de OpenStreetMap como alternativa provisional, verificando atributos y cobertura; no se asumiría equivalencia ni se mezclarían ambas sin revisar coincidencias. Si faltara renta o capacidad eléctrica, se mantendría el núcleo disponible y se explicaría qué dimensión queda sin valorar.

La viabilidad de integración está **comprobada hasta Gold con limitaciones**: claves y recintos comunes, periodos explícitos, entidades de recarga separadas y escenarios para incertidumbre. La suficiencia operativa, la localización de demanda dentro de los municipios y la viabilidad física de emplazamientos siguen sin demostrarse.

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

La selección de campos y los esquemas Gold están documentados: no se trasladan registros individuales de vehículos a las tablas de consumo analítico. Esto no certifica que todos los atributos de las descargas originales o nombres de POI carezcan de información personal. La revisión antes de redistribuir datos mantiene la minimización prevista en el [RGPD, artículo 5.1.c](https://www.boe.es/buscar/doc.php?id=DOUE-L-2016-80807):

- En DGT se seleccionarán solo los campos necesarios para los recuentos territoriales y la clasificación de vehículos; se excluirán de las salidas identificadores individuales y atributos innecesarios, si estuvieran presentes.
- En INE se mantendrá el nivel agregado publicado, sin intentar reconstruir personas, hogares o valores protegidos mediante cruces de datos.
- En recarga y POI se conservarán localización, categoría y características útiles, excluyendo contactos o datos de personas físicas que no aporten valor. [Geofabrik ya omite nombres, identificadores de usuarios e identificadores de cambios de colaboradores](https://download.geofabrik.de/europe/spain/valencia.html); esto no certifica ausencia de información personal en todos los atributos de los POI.
- Antes de publicar una muestra se revisarán identificadores y combinaciones que puedan facilitar reidentificación, especialmente en recuentos pequeños. La agregación territorial por sí sola no garantiza anonimato.

Los originales y las salidas de datos se conservan fuera de Git. El repositorio ofrece referencias e instrucciones de acceso, código y documentación; no redistribuye los ficheros i-DE ni las bases Gold/OSM. La selección de campos ya está aplicada, pero una futura publicación de datos o mapas requiere revisar atribuciones, obligaciones sobre derivados y posibles atributos identificativos. Las condiciones no confirmadas siguen registradas como pendientes.

## 4. Preparación de datos: Bronze → Silver → Gold

### Flujo implementado

| Capa | Tratamiento y salida |
| --- | --- |
| **Bronze/Raw** | Originales en `Fuentes/` y adquisiciones complementarias en `datos/bronze/`, fuera de Git. Se registran procedencia, periodos, tamaños y huellas SHA-256 para identificar las copias sin modificarlas. |
| **Silver** | Tipos, claves, unidades, nulos y geometrías preparados por fuente: 48 tablas y 502 columnas. Parquet para tablas y GeoParquet EPSG:25830 para cálculos en metros. Las versiones de recarga se conservan por separado. |
| **Gold** | Trece tablas y 135 columnas de contexto municipal, oferta, candidatos, relaciones, diagnósticos y variables normalizadas. El script genera una ejecución nueva con sus datos y un manifiesto de verificación. |

### Transformaciones principales y decisiones de calidad

- **Territorio y DGT:** los 542 códigos INE/IGN se contrastan con población y el Excel municipal DGT. El TXT nacional se procesa secuencialmente con memoria acotada; sus municipios suprimidos no se imputan. Distintivo 0 del Excel cubre todo el ámbito como aproximación. El código histórico de renta `12066` se separa sin reemplazarlo a ciegas por `46902`.
- **Población y renta:** se distinguen sexo, totales, niveles territoriales, indicadores y años. Los símbolos de ausencia permanecen nulos con estado. Gold utiliza población total 2025 y renta neta media por persona 2023, conservando ocho municipios sin renta, sin imputarlos o penalizarlos.
- **Recarga:** el lector trata UTF-16LE, comillas interiores, coordenadas y potencia con unidad. Se separan instalaciones, puntos y conectores; se comprueban claves y relaciones padre-hijo. Las diferencias municipales se contrastan documentalmente, conservando pendientes y evidencia sin desplazar coordenadas automáticamente. EPSG:4258 declarado por MITECO se transforma explícitamente a EPSG:25830.
- **Versiones de oferta:** la exportación adquirida el 18-10 contiene 1.517 instalaciones; 1.466 tienen relación municipal admitida y 51 siguen pendientes. La oferta principal suma 4.194 puntos y 5.017 conectores. Nueve instalaciones históricas ausentes se mantienen como incertidumbre, sin declararlas cerradas. Los escenarios añaden primero pendientes y después ausentes, sin mezclar versiones silenciosamente.
- **Red, tráfico e i-DE:** se separan tramos y asociaciones con viales para no multiplicar geometrías. Los aforos conservan años, tipos y ceros; las cinco líneas IGN degeneradas quedan señaladas y fuera de métricas. i-DE conserva 423 puntos y su contexto en 116 municipios, sin sumar capacidades como si fueran independientes ni garantizar conexión. La red no se utiliza como un sistema de rutas validado.
- **OSM y relaciones:** se conservan puntos y polígonos, exteriores y posibles correspondencias, sin fusionarlos como negocios únicos. Se preseleccionan 16.377 elementos de aparcamiento, comercio y alojamiento para revisión. Los cruces municipales mantienen relaciones múltiples y no reparten demanda por superficie o número de POI. Para áreas se conserva la geometría original y un representante interior en CV, con estado si no existe superficie evaluable.

### Estructura Gold que consumirá la siguiente fase

La siguiente fase podrá consultar demanda potencial, oferta y separación espacial
por separado, y ensayar después una priorización interpretable. Las filas no
representan sesiones, clientes reales, demanda individual o emplazamientos viables.

| Tabla | Filas | Qué significa una fila y columnas principales | Utilidad |
| --- | ---: | --- | --- |
| `gold_municipios` | 542 | Municipio: `codigo_municipio`, `geometria`, `vehiculos_distintivo_0`, población, renta, periodos, puntos admitidos y estados. | Contexto territorial y lectura municipal de demanda/oferta. |
| `gold_recarga_instalaciones` | 1.526 | Instalación conservada en la unión de versiones: ID, geometría, presencia, admisión, puntos y conectores registrados. | Localizar oferta y seleccionar explícitamente el escenario. |
| `gold_incertidumbre_recarga_municipio` | 112 | Vínculo instalación–municipio y tipo de incertidumbre; códigos y motivos. | Explicar pendientes y ausencias sin contarlos como oferta admitida. |
| `gold_candidatos` | 16.377 | Elemento OSM: `candidato_id`, categoría, geometría original, representante, municipio de contexto y estado de revisión. | Conservar candidatos para comprobación local. |
| `gold_candidato_municipio` | 16.484 | Relación candidato–municipio: códigos, dimensión y superficie de intersección. | Mantener todos los vínculos, incluidos los múltiples. |
| `gold_correspondencias_candidatos` | 75 | Par punto–área con coincidencias de identificador, nombre o posición y estado. | Revisar posibles representaciones del mismo lugar sin fusionarlas. |
| `gold_proximidad_candidato_recarga` | 49.131 | Candidato–escenario: instalación más cercana al representante, `distancia_plana_m`, empates y estado. | Contrastar la distancia del representante con la de la geometría original. |
| `gold_control_area_recarga` | 40.332 | Área–escenario: número e IDs de instalaciones que intersectan la geometría original. | Identificar recarga coincidente con un área, sin acreditar acceso o suficiencia. |
| `gold_solapamientos_candidatos` | 1.269 | Par de candidatos: dimensión/superficie de intersección y cobertura en ambos sentidos. | Revisar redundancias cartográficas, sin deduplicación automática. |
| `gold_control_borde` | 49.131 | Candidato–escenario: distancia del representante al borde CV, aviso y estado. | Advertir de posible oferta exterior al ámbito de datos. |
| `gold_referencias_normalizacion` | 2 | Dimensión: variable, unidad, universo, escenario de referencia, contadores, mínimo, máximo y estado. | Mantener escalas comunes y auditables. |
| `gold_variables_municipio` | 542 | Municipio: Distintivo 0, `demanda_normalizada_log`, contraste lineal y estado. | Guardar la dimensión de demanda una sola vez por municipio. |
| `gold_variables_candidato` | 49.131 | Candidato–escenario: contexto exclusivo, `distancia_minima_geometria_m`, escalas log/lineal, distancia al borde de su geometría y aviso. | Comparar separación respecto a oferta, con contexto e incertidumbre explícitos. |

Las tres filas por candidato corresponden a `principal_admitida`,
`incluye_pendientes` e `incluye_ausentes_historicas`. Se busca oferta en todo
el ámbito, también en otros municipios. Distancias planas en metros, sin rutas.
En la distancia a la geometría original, un área con recarga intersectante tiene
distancia cero; no demuestra oferta suficiente, acceso o disponibilidad operativa.

La normalización usa `ln(1+x)/ln(1+M)` y conserva el contraste `x/M`, con unidades
de vehículos y metros explícitas. Las referencias fijas de esta versión son
10.246 vehículos y 36.628,0631790845 m, desde todos los municipios y las distancias
principales, respectivamente. No se reajustan por filtro o escenario ni se
rellenan ausencias. Cero observado, desconocido y fuera de referencia conservan
estados distintos. El resultado 0–1 no es un porcentaje de necesidad o cobertura.
El aviso de borde asociado utiliza la misma geometría que su distancia; se conserva
separado del aviso calculado con el representante.

Las tablas Gold de una ejecución comparten `version_gold`. Se relacionan mediante
el código municipal, el identificador de instalación o el de candidato; las
medidas de cada candidato se enlazan también por escenario. El manifiesto registra
columnas, tipos y claves para comprobar los enlaces. Las relaciones múltiples
se mantienen como tales, sin multiplicar la demanda municipal.

### Acceso, reproducción y verificación

El código entregado es [preparar_dataset.py](../../src/preparar_dataset.py).
Contiene el recorrido completo en `main()` y las transformaciones agrupadas
por fuente, sin depender de otros scripts ni de tablas previamente generadas.

Las fuentes se obtienen mediante los enlaces del apartado 2. El bloque
`ENTRADAS` del script identifica las rutas relativas del catálogo de archivos,
la exportación principal y las evidencias complementarias. Para repetir la
selección exacta se necesitan las copias conservadas, sus recibos, los metadatos
MITECO/i-DE y las decisiones municipales documentadas, fuera de Git. Estas
decisiones son entradas revisadas, no correcciones automáticas. Una descarga
actual puede requerir revisar versiones y no garantiza los mismos resultados.

Con Python 3.12 instalado, desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install duckdb==1.5.0 openpyxl==3.1.5
.\.venv\Scripts\python.exe -c "import duckdb; c=duckdb.connect(config={'extension_directory':'.venv/duckdb_extensions'}); c.execute('INSTALL spatial'); c.close()"
.\.venv\Scripts\python.exe src/preparar_dataset.py --comprobar-entradas
.\.venv\Scripts\python.exe src/preparar_dataset.py
```

La instalación inicial requiere Internet; la preparación lee las copias locales.
La opción `--comprobar-entradas` revisa archivos y metadatos antes de transformar.
Se utiliza disco temporal, con 1 GB de memoria del motor DuckDB y dos hilos.
Cada ejecución escribe sus tablas y manifiestos en
`resultados/entrega02/<ejecución>/`, sin sustituir los originales o salidas previas.
El manifiesto final se guarda tras completar los controles.

**Verificación del 22-10-2026:** 213 pruebas aprobadas y 61 tablas reproducidas
(48 Silver y 13 Gold), con esquemas, valores y geometrías equivalentes a la
preparación anterior; solo cambia el identificador de ejecución Gold. Se
comprueban claves, relaciones, nulos, escenarios, tipos y conservación al
exportar. Esto acredita la reproducción técnica, no la necesidad real de recarga.

## 5. Riesgos y limitaciones

- Faltan sesiones, energía, ocupación y colas: Distintivo 0 aproxima demanda potencial, sin demostrar uso o suficiencia.
- La demanda es municipal; OSM tiene cobertura desigual y representaciones solapadas, sin acreditar negocios únicos o sitios disponibles.
- El inventario de recarga tiene pendientes, ausencias y posible oferta exterior no verificada; proximidad plana no equivale a acceso real.
- Capacidad eléctrica orientativa, periodos distintos y condiciones i-DE pendientes limitan la lectura y una futura publicación de derivados.
- Si falla una fuente, se conservará la última copia fechada con su antigüedad; se revisará la alternativa antes de mezclarla, o se omitirá el indicador complementario.
