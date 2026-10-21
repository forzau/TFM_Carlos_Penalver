# Candidatos y proximidad en Gold

Fecha: **20-10-2026**. Segunda etapa del [planteamiento Gold](PLANTEAMIENTO_GOLD.md),
según el [contrato de candidatos v1](CONTRATO_CANDIDATOS_GOLD.md).
Estado: **materializada y validada con limitaciones**.
Prepara elementos para revisión y su proximidad geométrica a recarga registrada.
No genera una recomendación de instalación ni acredita que los lugares sean aptos.

## Organización y entradas

Se añaden cuatro tablas a las tres de [contexto municipal](GOLD_MUNICIPAL.md).
Las siete tienen utilidades distintas; no se sustituyen las entidades Silver
ni se integra toda la información en una sola tabla.

| Tabla nueva | Una fila representa | Filas | Columnas |
| --- | --- | ---: | ---: |
| `gold_candidatos` | Un elemento OSM preseleccionado, con geometría original y punto representativo. | 16.377 | 19 |
| `gold_candidato_municipio` | Una intersección de ese elemento con un municipio. | 16.484 | 5 |
| `gold_correspondencias_candidatos` | Un par punto–área con indicios conservados, sin fusionar. | 75 | 8 |
| `gold_proximidad_candidato_recarga` | La distancia de un elemento a la instalación más próxima de un escenario. | 49.131 | 7 |

Son **39 columnas** entre las cuatro tablas nuevas; estas dos etapas reúnen siete tablas
y 84 columnas contando la etapa municipal. Estos recuentos no se incorporan
al inventario Silver, que mantiene sus 48 tablas y 502 columnas.

Se utilizan las ejecuciones POI `20261016T121902157473Z`, base territorial
`20261015T164603584512Z`, relaciones conjuntas `20261019T094606691147Z`
y Gold municipal `20261020T153200478279Z`. Se comprueba que las relaciones
se calcularon sobre las mismas copias de POI y recintos seleccionadas.
De la validación conjunta histórica se leen solo relaciones OSM; la oferta
proviene de la Gold municipal con recarga versionada, no de aquella recarga histórica.

La instantánea OSM es de **09-09-2026, 20:21:20 UTC**; la recarga principal
fue adquirida el **18-10-2026**. Parque, población y renta mantienen los periodos
de la Gold municipal. No se presume observación simultánea o funcionamiento actual.

## Preselección y representación

La preselección conserva 12.816 aparcamientos mapeados, 1.990 comercios y
1.571 alojamientos. Comercios y alojamientos requieren comprobar estacionamiento;
la etiqueta aparcamiento tampoco acredita acceso público, disponibilidad o permisos.
Los 1.417 elementos de parada viaria siguen disponibles como contexto Silver.

Hay **2.933 puntos y 13.444 áreas**. Los puntos conservan su posición; las áreas
conservan su geometría original completa y reciben un punto interior de su
intersección con CV. El punto no representa un acceso o plaza observados.
No se usan centroides municipales ni se distribuyen vehículos entre elementos.

Los vínculos alcanzan **490 municipios**. Los otros 52 no tienen elementos de
esta preselección en la copia OSM; no se afirma que carezcan de lugares posibles.
16.271 elementos tienen un vínculo, 105 tienen dos y uno tiene tres.
En los 106 casos múltiples el contexto municipal exclusivo queda nulo y todos
los vínculos permanecen consultables. El punto interior no fuerza una asignación.

Los **75 pares** involucran 146 elementos. Se conservan sin fusionar por nombre,
intersección o número OSM; no permiten calcular establecimientos únicos.
También puede haber un aparcamiento dentro de un comercio sin estar recogido
en esos pares, pues la regla Silver compara elementos de la misma categoría.
La selección de lugares físicos exigirá revisar esas correspondencias y solapamientos.

## Qué significa la proximidad

Cada elemento tiene tres filas, con distancia plana mínima en metros desde
su punto representativo a geometrías admitidas de instalaciones:

| Escenario | Instalaciones del inventario | Uso |
| --- | ---: | --- |
| `principal_admitida` | 1.466 | Referencia principal: presentes y con relación municipal admitida. |
| `incluye_pendientes` | 1.517 | Sensibilidad al añadir presentes con asignación pendiente. |
| `incluye_ausentes_historicas` | 1.526 | Sensibilidad adicional al incorporar las nueve ausencias históricas. |

La búsqueda considera toda la oferta CV del escenario, incluyendo municipios
vecinos. Conserva el ID del vecino, el número de empates exactos y el estado
del cálculo. En empate se selecciona el menor ID lexicográfico, sin redondear
las distancias para elegirlo. Al ampliar la oferta, la distancia no aumenta.

En esta ejecución todas las geometrías de los tres conjuntos son admisibles
y los 16.377 elementos tienen distancia calculable. Hay 131 elementos con
empate en cada escenario, con un máximo de seis instalaciones a la misma
distancia. Para 2.470 de los 16.271 elementos con contexto municipal exclusivo,
el vecino seleccionado tiene su admisión en otro municipio; restringir la
búsqueda al municipio habría omitido esa oferta.

La distancia disminuye para 524 elementos al añadir pendientes, y para 35
al añadir después históricos ausentes. En conjunto cambia para 554 elementos
frente al principal; los dos grupos se solapan y no se suman directamente.
Esto describe sensibilidad a registros inciertos, no mejora real de servicio.
Las consultas y huellas de este contraste se conservan en la evidencia local
de revisión, sin alterar las tablas o el manifiesto validados.

Pendientes y ausencias no se añaden a la oferta principal por hacer estos ensayos.
No se promedian escenarios ni se convierten en probabilidades de funcionamiento.
Una asignación municipal admitida tampoco certifica la precisión de cada plaza.

La distancia no es recorrido por carretera, tiempo de acceso, adecuación técnica
o disponibilidad. El inventario solo incluye CV y puede faltar oferta más próxima
al otro lado del borde autonómico. No se define un radio de servicio ni un sí/no
de suficiencia. Una distancia alta por sí sola no justifica instalar recarga.

## Controles y reproducción

`src/preparar_gold_candidatos.py` verifica entradas, versiones, claves y
correspondencia de las relaciones territoriales. Se conservan los atributos
OSM, todos los vínculos y los indicios de correspondencia sin multiplicar filas.
Se comprueban campos obligatorios, referencias, geometrías, estados nulos,
escenarios completos y monotonicidad. Se vuelven a contrastar los mínimos,
desempates y número de empates contra toda la oferta de cada escenario.

El exportador ya existente escribe las cuatro tablas; se reabren y comparan
tipos y valores, incluidos WKB y metadatos EPSG:25830 de **ambas** geometrías.
Las huellas de entradas y código se vuelven a comprobar al terminar.

```powershell
.venv\Scripts\python.exe src/preparar_gold_candidatos.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Sin red o dependencias nuevas; se reutiliza la extensión espacial instalada
en el entorno del proyecto. La base temporal en disco limita el motor a 1 GB
y dos hilos; las distancias se calculan por lotes de 512 elementos.
El límite del motor no incluye toda la memoria del proceso Python.

Salidas en una ejecución nueva de `resultados/gold/candidatos/`:
cuatro Parquet/GeoParquet, `manifiesto.json` e `informe.json`. `actual.json`
identifica la ejecución vigente solo después de validar; no se sobrescriben
ejecuciones anteriores ni los indicadores municipales o Silver.
Datos y manifiestos permanecen fuera de Git. Código y documentación están
preparados localmente, pendientes de commit y publicación.

Ejecución vigente: **`20261020T160709239795Z`**. Se verifican 208 archivos
distintos de entrada y código y las cuatro salidas, incluidas las referencias
de la Gold municipal. La suite termina en 74,486 segundos; la ejecución de
datos reales se comprueba además con sus propias reglas y la relectura de salidas.

La suite completa pasa **156 pruebas, sin omisiones**. Las dieciséis nuevas
cubren selección, conservación de nombres nulos y representaciones, municipios
múltiples, área multipartita, contacto sin superficie, oferta vacía, geometría
de recarga no admitida, vecino de otro municipio, empate y escenarios anidados.
También rechazan vínculos repetidos o ausentes, código/categoría incompatible,
evidencia alterada, vecino más lejano, empate mal resuelto, sobreescritura y
referencias fuera del bloque. No se modifican los preparadores anteriores.

Datos © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
distribución [Geofabrik](https://download.geofabrik.de/europe/spain/valencia.html),
bajo ODbL 1.0 según la documentación de la copia conservada.

## Próximo paso

La [revisión territorial](REVISION_EJEMPLOS_GOLD.md) está completada con sus
reservas: doce municipios y 168 distancias de 56 elementos contrastados.
Los [diagnósticos de coincidencia área–recarga, solapamientos y posible
influencia exterior](CONTROLES_ESPACIALES_GOLD.md) ya están materializados
en un bloque propio, manteniendo estas cuatro tablas intactas.
Siguiente: definir cómo combinar contexto municipal y proximidad
para comparar zonas, con normalización y sensibilidad explícitas. Elegir sitios
físicos, pesos definitivos, radios, optimización y aplicación siguen pendientes.
