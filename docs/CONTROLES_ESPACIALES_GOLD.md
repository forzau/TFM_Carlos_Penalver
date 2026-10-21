# Controles espaciales de candidatos Gold

Contrato **v1 — 21-10-2026**. Implementa los tres diagnósticos propuestos en la
[revisión territorial](REVISION_EJEMPLOS_GOLD.md), sin sustituir las siete tablas
Gold anteriores, fusionar elementos o cambiar distancias y recuentos municipales.
Los controles acompañarán a los indicadores al comparar zonas y revisar lugares.
Estado: **materializados y validados con limitaciones**.

Se preparan tres tablas nuevas bajo `resultados/gold/controles_espaciales/`,
con manifiesto, informe e indicador de ejecución propio. Todas incluyen
`version_gold` (`VARCHAR`, obligatorio), referido a la ejecución de controles.
El manifiesto identifica por separado las versiones de contexto municipal y
candidatos. Sus IDs se conservan, sin inventar identidad física de establecimientos.

## 1. Coincidencia de áreas con recarga registrada

`gold_control_area_recarga` tiene una fila por **área candidata y escenario**,
incluidas las áreas sin coincidencia. No contiene filas para puntos: ausencia
de fila de un punto significa que el control de área no le aplica, no recarga cero.
Se usa la geometría original completa del área, sin recortarla o sustituirla
por su representante. Se consideran instalaciones de todo el inventario del
escenario, sin filtro por municipio.

| Campo, además de `version_gold` | Tipo / nulos | Definición |
| --- | --- | --- |
| `candidato_id` | `VARCHAR`, obligatorio | FK a `gold_candidatos` de la versión referenciada. |
| `escenario` | `VARCHAR`, obligatorio | Uno de los tres escenarios de proximidad existentes. |
| `instalaciones_intersectan` | `BIGINT`, obligatorio | IDs distintos de instalación cuya geometría admitida intersecta el área. |
| `instalaciones_ids` | `VARCHAR[]`, obligatorio | Lista de esos IDs, sin duplicados y ordenada. Lista vacía y recuento cero si no hay coincidencias. |

Clave: `version_gold`, `candidato_id`, `escenario`. No se cuentan conectores,
no se fusionan instalaciones con coordenadas compartidas y no se agregan estos
recuentos entre áreas como si fueran instalaciones distintas de toda CV.
Una instalación puede intersectar varias áreas.

Los escenarios reutilizan la definición de [candidatos Gold](CANDIDATOS_GOLD.md):
`principal_admitida` (presentes con relación municipal admitida),
`incluye_pendientes` (todas las presentes) e `incluye_ausentes_historicas`
(presentes más ausencias históricas). Solo participan geometrías admitidas,
válidas y no vacías. Pendientes e históricos no entran en la oferta principal.

La regla es `ST_Intersects`: incluye coordenadas sobre el borde del área.
El resultado acredita **coincidencia cartográfica**, no acceso a las mismas
plazas, pertenencia al negocio, funcionamiento o suficiencia. Permite evitar
que la distancia positiva desde un representante se lea como «el área no
contiene ninguna coordenada de recarga registrada». La distancia anterior
permanece disponible y mantiene su significado geométrico.

## 2. Intersecciones entre candidatos, sin fusión

`gold_solapamientos_candidatos` conserva todos los pares de geometrías originales
que intersectan. Incluye punto–punto coincidente, punto–área y área–área,
entre categorías iguales o distintas. Cada par aparece una vez, ordenado por
ID lexicográfico (`candidato_a_id < candidato_b_id`); se excluyen autocruces.

| Campo, además de `version_gold` | Tipo / nulos | Definición |
| --- | --- | --- |
| `candidato_a_id`, `candidato_b_id` | `VARCHAR`, obligatorios | FK a candidatos; clave conjunta en una ejecución. |
| `dimension_interseccion` | `SMALLINT`, obligatorio | 0 para punto, 1 para línea o 2 para superficie. |
| `superficie_interseccion_m2` | `DOUBLE`, admite nulo | Área de intersección si la dimensión es dos; nulo en contactos de menor dimensión. |
| `a_cubre_b`, `b_cubre_a` | `BOOLEAN`, obligatorios | Resultado de `ST_Covers` en cada dirección; incluye borde. |
| `misma_categoria`, `misma_representacion` | `BOOLEAN`, obligatorios | Comparaciones de categoría OSM y punto/área de los elementos. |

El control conserva indicios de contención y contacto, no equivalencias físicas.
Dos áreas pueden representar edificio y recinto; un punto puede describir un
comercio dentro de un área de aparcamiento. Ni el nombre, ni un área compartida,
ni la cobertura completa justifican fusionarlos automáticamente. Una coincidencia
punto–punto tampoco prueba que ambos registros describan el mismo negocio.

La tabla permite revisar candidatos relacionados antes de elegir varios lugares.
No se usa el número de pares como número de duplicados, ni se resta a los elementos
para obtener sitios únicos. No certifica que todas las posibles representaciones
de un lugar intersecten: los indicios no espaciales existentes permanecen en
`gold_correspondencias_candidatos`, que no se sustituye.

## 3. Posible influencia de oferta exterior al inventario CV

`gold_control_borde` tiene una fila por candidato y escenario de proximidad,
incluidos estados no evaluables. La referencia es el borde de la **unión de los
542 recintos municipales**, no cada límite municipal por separado. Incluye costa
y los límites de la geometría conservada; no identifica por sí solo tramos
terrestres con otra comunidad.

| Campo, además de `version_gold` | Tipo / nulos | Definición |
| --- | --- | --- |
| `candidato_id`, `escenario` | `VARCHAR`, obligatorios | FK a candidatos y escenario de la proximidad referenciada. |
| `distancia_borde_cv_m` | `DOUBLE`, admite nulo | Distancia plana en metros desde el representante al borde CV; nulo si falta posición. |
| `posible_influencia_exterior` | `BOOLEAN`, admite nulo | Si hay distancia a recarga calculable: `distancia_recarga > distancia_borde_cv_m`. Nulo si no puede compararse. |
| `estado_control` | `VARCHAR`, obligatorio | Estado de proximidad conservado: `calculable`, `sin_posicion_representativa` o `sin_recarga_admisible`. |

Clave: `version_gold`, `candidato_id`, `escenario`. Se utiliza una desigualdad
estricta, sin redondear ni fijar un radio: igualdad no activa el aviso. Se mantiene
la distancia al borde cuando la posición es válida pero falta oferta evaluable;
el aviso entonces es nulo, no falso.

Un aviso verdadero significa que el límite del inventario está más cerca que
la recarga encontrada y **podría** faltar un vecino exterior más próximo.
No afirma que exista ese cargador; también puede activarse frente al mar.
Un falso no acredita suficiencia, inventario exhaustivo o accesibilidad real.
No se descarga ni valida aquí oferta exterior, no se corrige el vecino elegido
y no se penaliza automáticamente un candidato o municipio.

## Trazabilidad, controles y reproducción

Las entradas son las ejecuciones vigentes de contexto municipal y candidatos,
con sus informes, manifiestos y evidencias verificadas. Se comprueban huellas,
estados y versiones compatibles antes de calcular; un cambio de entrada requiere
una ejecución nueva. No se modifica ningún bloque Silver o Gold anterior.

Se verifican claves, campos obligatorios, cobertura de áreas/escenarios y
candidatos/escenarios, IDs y recuentos de coincidencias contra un nuevo cruce,
pares completos sin autocruces o duplicación simétrica, dimensión/superficie,
cobertura y categorías. Se conservan las correspondencias espaciales anteriores.
El aviso y los nulos de borde se contrastan con las distancias y estados usados.
Al exportar se reabren Parquet y se comparan esquema y todos los valores,
incluidas listas y nulos. Las huellas de entrada y código se verifican al terminar.

```powershell
.venv\Scripts\python.exe src/preparar_controles_gold.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Sin red o dependencias nuevas, con la extensión espacial ya instalada en el
entorno del proyecto, motor limitado a 1 GB y dos hilos. El límite del motor
no incluye toda la memoria de Python. Se reutilizan lectores, comprobación de
integridad y exportador existentes sin modificar sus preparadores.

Cada ejecución conserva tres Parquet, `manifiesto.json` e `informe.json` en
una carpeta nueva. `actual.json` cambia solo tras cerrar las comprobaciones;
una ejecución fallida no sustituye la anterior. Salidas e insumos pesados
quedan fuera de Git; código y documentación se conservan para reproducción.

## Resultado de la ejecución

Ejecución vigente: **`20261021T154333431064Z`**. Referencia municipal
`20261020T153200478279Z` y candidatos `20261020T160709239795Z`, conservadas
sin cambios. Sus periodos y la instantánea OSM se heredan explícitamente en
el manifiesto; la fecha de proceso no se convierte en fecha de observación.

| Tabla | Filas | Columnas |
| --- | ---: | ---: |
| `gold_control_area_recarga` | 40.332 | 5 |
| `gold_solapamientos_candidatos` | 1.269 | 9 |
| `gold_control_borde` | 49.131 | 6 |

Son tres tablas y 20 columnas nuevas: Gold reúne **diez tablas y 104 columnas**.
Silver mantiene su inventario independiente de 48 tablas y 502 columnas.

| Escenario | Áreas evaluadas | Áreas con coincidencia de recarga | Relaciones área–instalación | Candidatos con aviso territorial |
| --- | ---: | ---: | ---: | ---: |
| `principal_admitida` | 13.444 | 292 | 333 | 3.069 |
| `incluye_pendientes` | 13.444 | 300 | 341 | 3.031 |
| `incluye_ausentes_historicas` | 13.444 | 300 | 342 | 3.030 |

Los tres escenarios tienen 16.377 controles de borde calculables cada uno.
Estos avisos incluyen posibles efectos de costa; no son recuentos de lugares
con cargadores exteriores verificados. Los recuentos de los escenarios no se
suman entre sí. Tampoco se suman relaciones área–instalación como instalaciones únicas.

De los 1.269 pares hay 287 con intersección de dimensión cero, 671 de dimensión
uno y 311 de dimensión dos. Se conservan los 75 pares espaciales anteriores y,
entre otros, los 483 pares aparcamiento–comercio/alojamiento de la revisión.
Los contactos sin superficie compartida permanecen identificados por dimensión.

Se verifican **216 archivos de entrada/código** y las tres salidas, reabiertas
sin cambios de tipos o valores. La suite completa pasa **174 pruebas sin
omisiones** en 97,101 segundos, incluidas dieciocho nuevas. Cubren escenarios,
IDs sobre el borde, listas vacías, puntos sin control de área, áreas anidadas,
contactos lineales, categorías distintas, borde autonómico frente a límite
municipal interno, igualdad estricta, nulos, ausencia de oferta, geometría no
admitida y rechazos de datos alterados o referencias incompatibles.

Un contraste adicional reproduce los 483 pares de la revisión y las dos
instalaciones que coinciden con Centro Comercial Bonaire (`2024000132` y
`2024006420`). Al ampliar escenarios, las listas de coincidencias solo crecen
y ningún aviso de borde cambia de falso a verdadero. Las consultas y huellas
del contraste quedan en `resultados/revision_gold/20261021_controles/comprobacion.json`.
No se modifican los informes de revisión del día anterior.

El código, las pruebas y la documentación forman el material académico del
repositorio; los datos y los informes detallados se conservan fuera de Git.

## Continuación

Estos controles permiten acompañar los indicadores con avisos verificables.
La [definición de variables y normalización](VARIABLES_NORMALIZACION_GOLD.md)
está materializada en un bloque propio y la [sensibilidad](SENSIBILIDAD_GOLD.md)
ya está contrastada; siguiente trabajo analítico: ensayar pesos.
Su nueva distancia a la geometría incluye un aviso de borde
coherente con esa misma geometría; el control actual conserva su referencia
al representante y no se sustituye silenciosamente. No se ha generado un ranking ni un umbral
de suficiencia, acceso real, demanda observada o viabilidad de instalación.
