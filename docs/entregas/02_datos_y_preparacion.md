# Entrega 02 - Datos y preparación

**Proyecto:** localización de nuevos puntos de recarga para vehículos eléctricos en la Comunitat Valenciana.

**Estado:** borrador de los apartados 1 y 2. Los apartados 3-5 y el procesamiento reproducible quedan pendientes.

## 1. Qué datos necesita vuestro producto

El producto apoyará a administraciones públicas y operadores de recarga en la decisión de dónde ampliar la infraestructura pública y qué zonas priorizar. Combinará demanda potencial, infraestructura existente y accesibilidad, explicando los factores que justifican la prioridad. El ámbito inicial comprende Alicante/Alacant, Castellón/Castelló y Valencia/València. La presentación final se orientará a una aplicación web que consuma los datos preparados.

### Qué representa una observación

Una observación representará la unidad espacial evaluada para ampliar la infraestructura, con su localización y variables de demanda, cobertura y accesibilidad. No equivale a un registro original: las fuentes contienen vehículos, municipios, tramos, instalaciones, nodos y puntos de interés.

La unidad concreta sigue pendiente: zona territorial o ubicación candidata. Se decidirá tras comprobar la granularidad y compatibilidad de las fuentes, sin fijar todavía una cuadrícula, sección censal o radio. Un dato municipal no se interpretará como una medición individual de cada ubicación.

### Datos imprescindibles y deseables

| Prioridad | Información | Uso |
| --- | --- | --- |
| Imprescindible | Parque de vehículos, distinguiendo eléctricos e híbridos enchufables, y referencia territorial. | Aproximar demanda potencial; el parque registrado no mide recargas efectivas. |
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

Se han localizado población de 2021-2025, aforos de 2009-2025 y renta de 2023. El histórico puede aportar contexto, pero no es necesario utilizarlo entero. Para recarga interesa una versión fechada de la infraestructura existente. Falta confirmar el periodo del parque y las versiones locales de cartografía, nodos y puntos de interés.

No se ha fijado un año común. Se distinguirán periodo de referencia, fecha de publicación y descarga: fuentes recientes no necesariamente describen el mismo momento. Tampoco se dispone todavía de demanda real de recarga ni de una etiqueta validada de «ubicación óptima»; el objetivo y la evaluación de Machine Learning deben concretarse antes de elegir modelos.

## 2. Fuentes reales y viabilidad

Los ocho bloques principales se han localizado y descargado, con comprobaciones preliminares de apertura. Esto acredita disponibilidad inicial, no integración ni calidad verificadas. Las páginas públicas de acceso se han contrastado el 8 de octubre de 2026; falta vincular cada archivo local con su recurso, versión y periodo exactos.

Se utilizarán descargas públicas y exportaciones de los proveedores, conservando versiones fijas para el TFM y sin depender inicialmente de scraping.

### Fuentes y acceso

| Fuente y adquisición | Cobertura, actualización y cautelas de viabilidad |
| --- | --- |
| **DGT - [Microdatos de parque de vehículos anual](https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Microdatos-de-parque-de-vehiculos-Anual/).** Descarga de listados ZIP y diseño de registro; copia local en TXT. | Nacional y anual para este recurso. El TXT supera los 7,5 GB: se procesará por lotes o filtrando durante la lectura. Pendientes periodo, campos territoriales y clasificación de propulsión. |
| **Generalitat Valenciana - [Aforos de la red autonómica](https://dadesobertes.gva.es/dataset/intensidad-media-diaria-anual-imd-de-trafico-por-tramos-red-autonomica-de-carreteras-2009-2025).** Descarga del GeoPackage; también ofrece WFS y documentación. | Red autonómica valenciana, serie 2009-2025 y actualización anual declarada. Abierto preliminarmente en QGIS. No representa todas las vías estatales, provinciales o urbanas; deben comprobarse identificadores y comparabilidad entre años. |
| **INE - [Censo anual de población](https://ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176992&idp=1254735572981&menu=resultados).** Selección y descarga de tablas; copia localizada en CSV. | Nacional, con resultados municipales y serie localizada 2021-2025. Información anual. Los códigos municipales permitirán seleccionar el ámbito; se comprobarán tabla concreta, categorías agregadas y detalle de las variables. |
| **MITECO - [Puntos de Recarga de Vehículos Eléctricos](https://catalogo.datosabiertos.miteco.gob.es/catalogo/es/dataset/6ee8d46f-93bd-478f-8e29-3ba4f6d8405c).** El catálogo enlaza una [exportación pública en CSV](https://energia.serviciosmin.gob.es/Ripree/ExportarInstalaciones/Export). | Infraestructura de acceso público en España; registro actualizado con información remitida por operadores. Se conservará una exportación fechada. Hay valores `DESCONOCIDO` y `NODISPONIBLE`; falta revisar cobertura y relaciones instalación/punto/conector para evitar recuentos duplicados. |
| **INE - [Atlas de Distribución de Renta de los Hogares](https://www.ine.es/dynt3/inebase/index.htm?capsel=12384&padre=5608).** Descarga de tablas territoriales; datos localizados de 2023. | Municipios, distritos y secciones censales; serie anual con desfase de publicación. Los nulos requieren interpretar el nivel territorial. La renta no acredita por sí sola demanda de recarga. |
| **i-DE - [Mapa de capacidad de consumo](https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo).** Consulta y descarga de los ficheros tabulares ofrecidos. | Nodos de su propia red; actualización mínima mensual declarada. Falta confirmar que la copia local corresponde a consumo/demanda y su cobertura. Capacidad informativa, sin garantía de conexión. CNMC queda como posible contraste, sin dataset equivalente confirmado. |
| **IGN/CNIG - [Redes de Transporte](https://centrodedescargas.cnig.es/CentroDescargas/catalogo.do?Serie=REDTR).** Descarga de GeoPackages provinciales de Alicante, Castellón y Valencia. | Producto nacional con nuevas versiones cartográficas. Los tres archivos se abrieron preliminarmente en QGIS. Falta comprobar atributos y geometrías: disponer de líneas viarias no garantiza una red preparada para calcular rutas. |
| **OpenStreetMap, distribuido por [Geofabrik - Valencia](https://download.geofabrik.de/europe/spain/valencia.html).** Extracto regional en GeoPackage, Shapefile o PBF. | Información colaborativa, con extractos renovados y fechados. Se conservará una versión concreta. Deben comprobarse cobertura y categorías; no garantiza inventario completo de servicios. Los elementos alejados deben inspeccionarse antes de excluirlos. |

Se ha identificado además el producto de [límites y unidades administrativas del IGN/CNIG](https://centrodedescargas.cnig.es/CentroDescargas/detalleArchivo?sec=9000029). Falta comprobar si ya se dispone de recintos adecuados o adquirirlos cuando corresponda para asignación territorial y superficies; su disponibilidad local no está confirmada.

### Estabilidad y alternativas

Las fuentes cuentan con proveedores y documentación identificables, pero no se ha comprobado estabilidad permanente de enlaces y esquemas. Antes del procesamiento se registrarán recurso, versión, periodo y fecha de adquisición. Conservar las entradas permitirá reproducir el TFM aunque cambien las publicaciones.

Si una fuente clave dejara de estar accesible, se utilizaría la última copia conservada indicando su antigüedad. Si faltara MITECO, se estudiaría una extracción de cargadores de OpenStreetMap como alternativa provisional, verificando atributos y cobertura; no se asumiría equivalencia ni se mezclarían ambas sin revisar coincidencias. Si faltara renta o capacidad eléctrica, se mantendría el núcleo disponible y se explicaría qué dimensión queda sin valorar.

La viabilidad es **preliminar**: hay fuentes reales para demanda potencial, infraestructura y contexto espacial. Quedan pendientes la auditoría e integración, la unidad de observación, las versiones y fechas, las coberturas efectivas y el objetivo analítico posterior.
