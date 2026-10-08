# Contexto del proyecto

Actualizado: 2026-10-08. Ambas conversaciones anteriores están incorporadas.

## Marco y procedencia

- Autor: Carlos Peñalver; TFM del Máster de Ciencia de Datos e IA.
- Migración de un proyecto en la nube a este proyecto local.
- Repositorio: https://github.com/forzau/TFM_Carlos_Penalver.
- `Fuentes/` contiene los originales y debe conservarse intacta.
- OneDrive sincroniza el trabajo entre equipos, incluidos los archivos pesados.

Los dos contextos se recibieron el 2026-10-08; sus fechas originales se desconocen.
Los textos íntegros se conservan en `contexto/antecedentes/01_conversacion.md` y
`02_conversacion.md`, fuera de Git y disponibles mediante OneDrive. La segunda
conversación actualiza la primera y describe el estado más reciente del TFM.
Las observaciones sobre datos que siguen proceden de esos antecedentes; no son
una auditoría nueva ni una verificación de fuentes externas realizada en esta migración.

## Tema elegido y objetivo

**Localización óptima de nuevos puntos de recarga para vehículos eléctricos en
la Comunitat Valenciana.**

Construir un sistema de apoyo a decisiones que identifique y priorice zonas o
ubicaciones con mejores condiciones para ampliar la infraestructura pública de
recarga utilizando datos reales y públicos. Los usuarios previstos son las
administraciones públicas y los operadores de recarga.

La decisión principal es dónde instalar nuevos puntos y con qué prioridad. El
valor estará en combinar demanda potencial, tráfico, déficit de infraestructura,
demografía, condiciones socioeconómicas, capacidad eléctrica, accesibilidad y
ubicaciones candidatas para producir recomendaciones interpretables.

## Alcance

Ámbito inicial: Comunitat Valenciana, con Alicante/Alacant, Castellón/Castelló y
Valencia/València. Se descartó abarcar toda España inicialmente para reducir la
complejidad GIS, aprovechar los aforos de la Generalitat y filtrar fuentes nacionales
por provincia o municipio. No se ha fijado un periodo común de análisis.

## Fase alcanzada

Investigación y validación de fuentes **completada preliminarmente**, según la
segunda conversación: localizar, descargar, comprobar disponibilidad, abrir de
forma superficial y valorar utilidad potencial.

Todavía no se han realizado limpieza, joins, dataset maestro, EDA, creación de
variables, ML, optimización ni visualización final. La conclusión previa fue una
viabilidad prometedora por disponibilidad de datos; queda pendiente una auditoría
técnica que determine su calidad e integración efectiva.

## Ocho bloques de datos declarados

| Bloque y referencia prevista | Uso potencial | Comprobación y cautelas descritas en el antecedente |
| --- | --- | --- |
| Parque de vehículos — DGT | Vehículos, propulsión, VE/PHEV y demanda territorial. | TXT nacional descargado de más de 7,5 GB; su apertura convencional agotó memoria. Procesar por lotes o filtrar durante lectura; estructura detallada pendiente. |
| Aforos — Generalitat Valenciana | IMD por tramo, corredores y tráfico próximo. | GeoPackage 2009–2025 abierto en QGIS con capas anuales superpuestas; cobertura de la red autonómica. |
| Censo anual — INE | Población y demanda residencial/demográfica. | CSV 2021–2025 abierto; identificadores municipales y agregados como Total Nacional que deben interpretarse. |
| Recarga existente — MITECO | Distancia, cobertura, potencia instalada y déficit relativo. | Fichero nacional abierto, con CCAA y características técnicas; valores textuales DESCONOCIDO/NODISPONIBLE requieren interpretación posterior. Interesa la situación más reciente. |
| Renta — INE, Atlas de Distribución de Renta de los Hogares | Indicadores socioeconómicos como posible proxy de adopción de VE. | Datos abiertos; 2023 era el último definitivo localizado entonces. Nulos posiblemente estructurales por mezcla de niveles territoriales, pendientes de comprobar. Justificar su uso sin atribuir causalidad simple. |
| Capacidad eléctrica — i-DE; CNMC como posible contraste | Capacidad de nodos, proximidad y viabilidad relativa. | Fuente descargada y abierta, con provincia. La capacidad publicada es orientativa y no garantiza acceso o conexión; uso concreto de CNMC pendiente. |
| Red viaria — IGN/CNIG, Redes de Transporte | Accesibilidad, distancias y relaciones espaciales. | Archivos de las tres provincias cargados en QGIS; capas superpuestas correctamente según la comprobación previa. |
| Ubicaciones candidatas/POI — OpenStreetMap, distribución Geofabrik | Aparcamientos, gasolineras, supermercados, hoteles y otras ubicaciones. | Extracto valenciano en GeoPackage abierto en QGIS. Puntos alejados o marítimos pendientes de inspección; explicación insular posible, sin confirmar. Selección de categorías y recorte territorial aún pendientes. |

Las rutas, tamaños y fechas de los archivos locales se conservan únicamente en
`docs/inventario_fuentes.csv`, fuera de Git. La correspondencia exacta entre cada
archivo y estos bloques debe comprobarse durante la auditoría; no se ha deducido
el contenido de un archivo por su nombre.

## Relaciones territoriales

Priorizar códigos oficiales y geometrías frente a nombres de municipios. El
antecedente identifica el código INE municipal como `PPMMM`, con prefijos `03`,
`12` y `46` para las tres provincias. Un identificador como `03014 Nombre` se
interpreta como código municipal, no postal. Su estructura real y utilidad como
clave de unión deben contrastarse en cada fuente.

La unidad de análisis no está decidida: municipio, sección censal, cuadrícula,
H3 o ubicación candidata. Una malla de 1×1 km se mencionó como posibilidad,
sin fijar resolución. El reto principal previsto es integrar granularidades
espaciales y temporales diferentes.

## Metodología contemplada, todavía abierta

Se considera un enfoque de GIS, análisis multicriterio, análisis espacial y
optimización de localización. Se mencionó un posible *Charging Opportunity Score*
para alimentar un ranking o mapa de recomendaciones, sin fórmula ni pesos definidos.

No hay una variable objetivo natural de ubicación óptima que justifique por sí
sola un modelo supervisado. ML podría incorporarse si aporta una estimación de
demanda futura o adopción de VE útil para la planificación; no está decidido.
Tampoco están fijados los radios de cobertura, variables, restricciones ni
criterios de evaluación de la solución.

## Herramientas y reproducción

QGIS se utilizó en la etapa anterior para inspeccionar y superponer GeoPackages;
no se ha comprobado su instalación en este equipo durante la migración.
Python/Jupyter se contemplan como herramientas principales de procesamiento,
sin entorno local ni dependencias configurados todavía.

Se consideraron pandas, GeoPandas, NumPy, matplotlib y Shapely. Polars, DuckDB o
lectura por lotes son opciones para DGT; scikit-learn, NetworkX, OSMnx, H3 y
PuLP/OR-Tools son posibilidades condicionadas al enfoque final. Ninguna de estas
posibilidades implica una dependencia instalada o una decisión de arquitectura.

## Siguiente trabajo previsto, cuando corresponda

1. Auditoría técnica por fuente: procedencia, formato, filas, columnas, periodo,
   granularidad, CRS, clave territorial, coordenadas, variables útiles, nulos,
   duplicados y limitaciones.
2. Elegir la granularidad tras comprender las fuentes.
3. Preparar e integrar el dataset maestro: limpieza, filtrado territorial, joins,
   operaciones GIS y creación de variables.

No iniciar estas fases solo por recibir el contexto. Quedan por confirmar el
enunciado vigente, calendario, estado de las entregas, licencias, URLs exactas y
versiones de las fuentes, así como criterios de evaluación del producto.

## Antecedente de ideación: Entrega 1

La primera conversación pedía tres propuestas, cada una con nombre, problema,
motivación, público y valor: incendios forestales, despoblación rural y recarga
eléctrica. La ruta exigida era `docs/entregas/01_ideas_producto.md`; la copia actual
contiene las tres. No se ha confirmado si esa entrega se envió o evaluó.

La ausencia de elección definitiva descrita en esa primera conversación quedó
superada por la selección de recarga eléctrica en la segunda. Las otras ideas y
alternativas quedan como historial en el original, no como líneas activas del TFM.

Se mantiene el criterio de partir de un problema real, usuarios concretos y una
decisión accionable; ajustar el trabajo al enunciado; evitar complejidad técnica
innecesaria y comprobar datos antes de asumir su viabilidad.
