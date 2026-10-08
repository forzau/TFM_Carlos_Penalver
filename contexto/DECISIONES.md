# Registro de decisiones

| Fecha | Decisión | Motivo |
| --- | --- | --- |
| 2026-10-08 | Conservar `Fuentes/` intacta y fuera de Git. | Contiene el trabajo original y archivos pesados; el usuario utiliza OneDrive para sincronizarlos. |
| 2026-10-08 | Mantener el inventario de fuentes fuera de Git. | Sus nombres, tamaños y fechas describen archivos locales; OneDrive permite conservarlo sin publicarlo en el repositorio. |
| 2026-10-08 | Usar GitHub para el historial del código, la documentación y el contexto. | Permite recuperar versiones y continuar desde otro equipo. |
| 2026-10-08 | Guardar el contexto en archivos Markdown dentro del repositorio. | La continuidad no debe depender del historial de una conversación. |
| 2026-10-08 | Conservar la estructura y el documento existente de `docs/entregas/`. | Forma parte del trabajo previo. |
| 2026-10-08 | Configurar herramientas y dependencias cuando corresponda iniciar la fase técnica. | La segunda conversación confirma que la auditoría y el desarrollo aún no han comenzado. |
| 2026-10-08 | Conservar íntegros ambos contextos en `contexto/antecedentes/`, fuera de Git. | Mantener el historial original mediante OneDrive y un resumen operativo separado. |
| 2026-10-08 | Usar la segunda conversación como referencia del estado más reciente. | Actualiza la ideación de la primera con tema elegido, alcance y fuentes preliminarmente comprobadas. |

## Decisiones recuperadas de la primera conversación

Fecha original desconocida; registradas al incorporar el contexto el 2026-10-08.
La segunda conversación mantiene los criterios de producto y actualiza la
selección del tema y la fase del trabajo.

| Decisión histórica | Motivo |
| --- | --- |
| Proponer incendios forestales, despoblación rural y planificación de recarga eléctrica para la Entrega 1. | Presentar tres productos distintos con decisiones accionables y usuarios concretos. |
| No elegir todavía un TFM definitivo ni iniciar desarrollo técnico en esa etapa. | La entrega pedía ideación y justificación del producto, sin concretar arquitectura, modelos ni datasets. |
| Priorizar problema, usuario y valor sobre la tecnología. | El profesor exige propuestas basadas en necesidades reales. |
| Evaluar viabilidad de datos antes de comprometerse definitivamente con una idea. | La disponibilidad supuesta no garantiza que se puedan obtener datos adecuados. |

## Decisiones recuperadas de la segunda conversación

Fecha original desconocida; registradas al incorporar el contexto el 2026-10-08.

| Decisión vigente | Motivo |
| --- | --- |
| Seleccionar la localización de nuevos puntos de recarga para vehículos eléctricos. | Apoyar decisiones reales sobre ampliación de infraestructura pública con múltiples fuentes de datos. |
| Trabajar inicialmente en la Comunitat Valenciana. | Acotar complejidad GIS, aprovechar aforos regionales y filtrar fuentes nacionales; no abarcar toda España inicialmente. |
| Priorizar datos públicos y oficiales. | Referencias previstas: MITECO para recarga, DGT para vehículos, GVA para tráfico, INE para población y renta, i-DE para capacidad, IGN/CNIG para red viaria y OSM para candidatos. CNMC queda como posible contraste. |
| Tratar la capacidad eléctrica publicada como orientativa. | Sirve para viabilidad relativa, sin garantizar acceso ni conexión. |
| Usar códigos oficiales y geometrías como referencias territoriales. | Evitar depender solo de nombres; el código municipal INE y los prefijos 03, 12 y 46 son referencias previstas. |
| Procesar el TXT de DGT sin cargarlo entero en memoria. | Su volumen agotó memoria con una apertura convencional; herramienta concreta por decidir. |
| Comprender los niveles territoriales de renta antes de eliminar nulos. | Podrían ser valores estructurales, todavía sin auditoría detallada. |
| Inspeccionar y seleccionar los POI de OSM antes de excluir puntos alejados. | No se ha confirmado que sean errores; categorías y recorte espacial están pendientes. |
| Considerar GIS, multicriterio y optimización sin forzar ML supervisado. | No existe todavía una variable objetivo natural de ubicación óptima; ML solo si aporta valor al problema. |
| Realizar auditoría antes de elegir granularidad e integrar fuentes. | La fase previa comprobó disponibilidad y utilidad potencial, no calidad ni compatibilidad detalladas. |

Scoring, pesos, radios, granularidad, CRS, algoritmos y dependencias siguen sin
decidir. La recepción del contexto no inicia esas fases técnicas.

Añadir decisiones cuando se tomen, con su motivo. No registrar suposiciones como
decisiones confirmadas.
