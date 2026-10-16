# Puntos de interés OSM en Silver

Fecha: **16 de octubre de 2026**. Fase 6 del [plan de Silver](PLAN_SILVER.md),
preparada con límites de interpretación explícitos. Se conservan elementos de
interés y contexto; no se certifican establecimientos únicos o terrenos aptos
para instalar recarga.

## Entrada, referencia espacial y trazabilidad

Se utilizan el GeoPackage `Fuentes/ubicaciones_candidatasgpkg/valencia.gpkg`
y su `README`, registrados como `osm_valencia` en el catálogo Bronze. Sus tamaños
y SHA-256 se comprueban antes y después. La instantánea acreditada por el README
es **2026-09-09T20:21:20Z**; no se convierte la modificación del archivo en fecha
de adquisición ni se descarga una versión nueva de `latest`.

Se preparan las seis capas de puntos y áreas de `pois`, `traffic` y `transport`.
Las catorce capas restantes permanecen en Bronze, sin afirmar que esta preparación
sea un inventario completo de objetos OSM.

SQLite en solo lectura conserva `fid`, identificador publicado, código, categoría,
nombre y geometría de la misma fila. El lector admite la definición WKT CRS84
comprobada de esta copia: **`srs_id=100000` es un identificador local, no EPSG:100000**.
Se transforma de **OGC:CRS84 a EPSG:25830** con XY explícitos, conservando puntos,
polígonos y sus partes; no se sustituye un área por su centroide ni se recorta.
Otra definición espacial requiere revisión antes de admitirla.

La clave técnica es `origen_id` + `fid_origen`; el primero identifica recurso,
huella y capa. `osm_id` sigue siendo texto. La
[documentación de Geofabrik, secciones 2.5 y 2.8](https://download.geofabrik.de/osm-data-in-gis-formats-free.pdf)
explica que un objeto puede originar varias representaciones y que el identificador
publicado no garantiza unicidad. Tampoco incorpora aquí un tipo node/way/relation
que permita interpretar dos números iguales como identidad global inequívoca.

## Elementos conservados y selección inicial

**`poi_elementos` contiene 269.287 filas**, sin eliminar ninguna de las seis capas.

| Familia | Puntos | Áreas | Elementos de interés para revisión dentro del ámbito |
| --- | ---: | ---: | ---: |
| `pois` | 88.320 | 68.145 | 3.561 |
| `traffic` | 91.859 | 12.835 | 14.233 |
| `transport` | 7.863 | 265 | 0; se conserva como contexto y control territorial. |

La clasificación inicial tiene doce categorías, elegidas por su relación con
parada de vehículos o estancia. Es una regla de preparación revisable, sin pesos,
ranking ni prioridad de inversión:

| Grupo | Categorías publicadas seleccionadas | Elementos de interés dentro del ámbito |
| --- | --- | ---: |
| Aparcamiento | `parking` | 12.816 |
| Parada viaria | `fuel`, `service` | 1.417 |
| Comercio | `supermarket`, `mall`, `department_store` | 1.990 |
| Alojamiento | `hotel`, `motel`, `guesthouse`, `hostel`, `camp_site`, `caravan_site` | 1.571 |

El código de cada categoría se comprueba frente a la regla, documentada en código
y en el informe JSON. Hay **17.830 elementos** de esas categorías en la copia;
**17.794** tienen geometría admitida e intersección con el ámbito. Los otros 36
quedan conservados fuera del ámbito. Las categorías restantes siguen en la tabla
como `sin_seleccion`; por ejemplo, aparcamiento de bicicletas no se convierte en
aparcamiento de coches. Un código incompatible con su categoría quedaría señalado.

`interes_para_revision` solo combina categoría seleccionada, geometría admitida
e intersección territorial. No acredita acceso público, aparcamiento disponible,
titularidad del suelo, permiso de instalación o conexión eléctrica. El extracto
no aporta todos esos atributos; tampoco se supone que un hotel tenga aparcamiento.

## Ámbito y objetos alejados

Se comprueban las huellas de municipios, recintos y su informe Silver y se utiliza
la unión de los 542 recintos como referencia. No se asigna todavía un municipio.

- **268.768 elementos** intersectan la referencia CV, incluidos sus límites.
- **519 elementos** quedan fuera y se mantienen con `estado_ambito=fuera_cv`.
- Las **269.287 geometrías** son admitidas en esta ejecución; no hay reparaciones.

En polígonos basta una intersección para marcar interés territorial. No significa
que toda la superficie esté dentro ni identifica un lugar concreto de instalación.
Las discrepancias próximas al límite pueden depender de posición o cartografía;
no se reinterpretan automáticamente como errores de OSM.

Se inspeccionaron identificadores, nombres y coordenadas de los extremos del
extracto. Los ocho más distantes son puntos `ferry_terminal` etiquetados Alger,
Oran, Mostaganem, Port de Palma, Barcelona-Terminal F2, Ibiza-Botafoc, Formentera y
Sant Antoni de Portmany. La causa concreta de su inclusión en este extracto
histórico no está acreditada; se conservan como contexto fuera del ámbito.
El informe recoge los veinte elementos exteriores más distantes con su procedencia.

`distancia_ambito_m` es cero si hay intersección y, en los casos exteriores, distancia
plana mínima a la referencia. Sirve para diagnóstico, sin umbral de eliminación.
Fuera de la región no se garantiza la precisión de EPSG:25830 para una aplicación
de distancias; no son recorridos de conducción ni radios de servicio.

## Identificadores y correspondencias punto–área

Hay **249 filas adicionales por `osm_id` dentro de sus respectivas capas**.
No se deduplican: capa y `fid` mantienen cada representación identificable.

**`poi_correspondencias` contiene 77 pares** de categorías seleccionadas: un
punto intersecta un área de la misma categoría. En doce pares coinciden además
los nombres tras quitar espacios exteriores y pasar a minúsculas; en los otros
65 no se acredita esa coincidencia. Ninguno comparte identificador publicado en
esta copia. La regla también registraría igualdad de ID en la misma categoría,
aunque no hubiera intersección, como indicio que requiere revisión.

Cada par conserva las dos claves técnicas, identificadores, categoría, indicadores
de coincidencia y distancia plana. El estado es
`posible_correspondencia_sin_fusion`. No se aplica proximidad arbitraria, semejanza
de nombres ni selección de una representación preferida. Los pares pueden tener
cardinalidad múltiple: **no se restan 77 a los elementos para calcular negocios
únicos**. Ni una coincidencia de nombre ni una intersección certifican identidad.

## Salidas, controles y reproducción

| Salida | Filas | Tamaño |
| --- | ---: | ---: |
| `poi_elementos.parquet` | 269.287 | 14.173.669 bytes |
| `poi_correspondencias.parquet` | 77 | 4.774 bytes |
| `incidencias.parquet` | 0 | 204 bytes |

Las incidencias prevén geometría no admitida, categoría/código incompatible e
identificador no informado. Una geometría de origen inválida conservaría su WKB
sin proyectar, su estado y la referencia de origen; no se repararía ni borraría.
Los objetos exteriores y las posibles correspondencias son estados de uso y
evidencia, no errores que deban desaparecer de la salida.

Se comprueban recuentos frente a Bronze, claves técnicas y referencias de los
pares. Al releer Parquet se comparan todos los valores, tipos y WKB exportados;
la capa tiene metadatos GeoParquet EPSG:25830. También se verifican las huellas
de entradas y base territorial al terminar.
La suite completa pasa **61 pruebas sin omisiones**. Las ocho nuevas cubren IDs
repetidos, indicios sin fusión, objetos exteriores y sin selección, geometría
inválida conservada, códigos discordantes, CRS local, exportación y huella territorial.

```powershell
.\.venv\Scripts\python.exe src/preparar_poi_osm.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
```

Requiere las copias Bronze, base territorial Silver y extensión `spatial` ya
instalada, sin dependencias nuevas ni red. El trabajo usa una base temporal en
disco, almacenamiento v1.5.0, dos hilos y 1 GB de memoria del motor. Este límite
no incluye todo Python. Se mantiene la separación del cruce espacial y su filtro
por categoría para evitar un fallo del optimizador de la versión instalada.

Ejecución validada: `20261016T121902157473Z`, bajo `resultados/silver/poi_osm/`,
con estado `preparada_con_limitaciones`. `actual.json` solo cambia tras validar
salidas, huellas e informe; no se sobrescriben ejecuciones anteriores. Las salidas,
informe y contexto privado permanecen fuera de Git. Los temporales se eliminan.
Se versionan código, reglas, pruebas y documentación.

Datos © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
distribución [Geofabrik](https://download.geofabrik.de/europe/spain/valencia.html),
bajo ODbL 1.0 según el README conservado. El siguiente bloque es la **fase 7,
capacidad de demanda i-DE**; la integración conjunta y Gold siguen pendientes.
