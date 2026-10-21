# Contrato de candidatos y proximidad en Gold

Versión **1 — 20-10-2026**, implementada y validada en la
[segunda etapa Gold](CANDIDATOS_GOLD.md). Complementa las tres tablas de la [Gold municipal](GOLD_MUNICIPAL.md),
sin sustituirlas ni reducir Silver. La unidad inicial es un elemento OSM
preseleccionado para revisión, no una parcela disponible ni un establecimiento
físico único. La selección final de emplazamientos exigirá revisión posterior.

## 1. Utilidad e indicadores municipales

La Gold municipal aporta contexto de demanda potencial y oferta registrada.
Distintivo 0/parque describe composición del parque; Distintivo 0/puntos
admitidos describe presión comparativa. Ninguno acredita uso, déficit exacto
o suficiencia operativa. Los 285 municipios sin puntos admitidos tienen presión
nula con estado explícito; no reciben prioridad máxima por defecto. Las ocho
rentas no informadas se conservan y no penalizan un territorio.

Esta etapa permitirá localizar elementos a revisar dentro de las zonas y
comparar su proximidad geométrica a instalaciones registradas. Vehículos,
población y renta se consultarán como contexto municipal: no se repartirán
entre POI ni se presentarán como demanda observada de cada ubicación.

## 2. Entradas y preselección de destino

Se utilizarán `poi_elementos` y `poi_correspondencias` de Silver, las relaciones
de `validacion_conjunta/relaciones_espaciales` con `tabla_entidad='poi_elementos'`,
los recintos municipales y la Gold municipal vigente. El manifiesto fijará
las ejecuciones y huellas; la validación conjunta histórica se utilizará solo
para relaciones OSM, nunca para sustituir la recarga versionada de Gold.
La versión de POI y base territorial de esas relaciones debe coincidir con
las entradas elegidas; si no coincide, se recalculan antes de usarlas.

Filtro común: `interes_para_revision = true`, que exige categoría/código
admitidos, geometría admitida e intersección con CV. No se eliminan de Silver
los objetos que no pasen a esta Gold.

| Categorías OSM | Uso en esta etapa | Condición que sigue pendiente |
| --- | --- | --- |
| `parking` | Preselección `aparcamiento_mapeado`. | Tipo de acceso, plazas para vehículos, disponibilidad, titularidad y permiso de instalación. La etiqueta no acredita aparcamiento público. |
| `supermarket`, `mall`, `department_store` | Preselección `destino_sin_aparcamiento_acreditado`, grupo comercio. | Comprobar estacionamiento y acceso; una tienda puede carecer de aparcamiento. |
| `hotel`, `motel`, `guesthouse`, `hostel`, `camp_site`, `caravan_site` | Misma preselección condicionada, grupo alojamiento. | Comprobar estacionamiento, acceso y compatibilidad con recarga pública de destino. |
| `fuel`, `service` | Contexto conservado en Silver para recarga de paso. No entra en el universo inicial de candidatos de destino. | Puede revisarse en una ampliación del alcance; no se descarta físicamente el lugar. |

No se exige disponer de i-DE o un aforo cercano para entrar en la preselección.
Tampoco se elimina un elemento por tener recarga próxima: puede servir para
estudiar ampliaciones y la distancia no informa de ocupación o suficiencia.
Los grupos de preselección son estados descriptivos, sin pesos ni orden de mérito.

La inspección de las copias vigentes da **16.377 elementos preseleccionados**:
12.816 aparcamientos, 1.990 comercios y 1.571 alojamientos; 2.933 puntos y
13.444 áreas. Los 1.417 elementos de parada viaria permanecen como contexto.
No son cifras de lugares únicos ni de instalaciones recomendadas.

Hay 16.271 elementos con un vínculo municipal, 105 con dos y uno con tres:
**16.484 vínculos en 490 municipios**. Los otros 52 municipios no tienen
elementos de esta preselección en la copia; no significa que carezcan de
posibles emplazamientos. Hay **75 pares de correspondencia**, que implican
146 elementos, sin fusionarlos. El ensayo de representación genera un punto
para los 16.377 elementos, todos dentro de su geometría original y de la
intersección analítica; no hay áreas de contacto sin superficie en esta copia.

## 3. Identidad, correspondencias y representación

La clave conserva `origen_id` + `fid_origen`. `candidato_id` será la serialización
JSON de la lista de sus dos valores, con `fid_origen` convertido a texto, igual
que `clave_entidad` en las relaciones Silver. No se concatenan valores con un
separador ambiguo ni se usa `osm_id` como identidad física global. La huella del
origen forma parte de esta identidad técnica; otra copia requiere una nueva
ejecución y no implica continuidad automática de un establecimiento.

Se conservan por separado puntos y áreas y los pares de correspondencia con
ambos extremos preseleccionados. No se resta el número de pares al de elementos
ni se fusiona por nombre, ID numérico, proximidad o intersección. Los pares
pueden ser múltiples y las correspondencias Silver de la misma categoría no
detectan todas las relaciones posibles: por ejemplo, un aparcamiento dentro
de un centro comercial puede pertenecer al mismo destino sin estar en esos pares.
Los recuentos describirán **elementos preseleccionados**, nunca negocios únicos.
Antes de elegir varios emplazamientos se revisarán correspondencias y solapamientos.

Representación analítica EPSG:25830:

1. Para un punto, conservar su posición original admitida.
2. Para un área con superficie dentro de CV, obtener `ST_PointOnSurface` de
   su intersección con la unión de los recintos. Se conserva también la geometría
   original completa; el recorte es exclusivamente analítico.
3. Si el área solo toca el límite y no tiene intersección de dimensión dos,
   conservar el elemento con punto nulo y estado `sin_superficie_en_cv`.
   No inventar una posición ni excluir silenciosamente el registro.
4. Comprobar que el punto resultante es válido, no vacío e intersecta tanto
   la geometría original como CV. No sustituirlo por el centroide si falla.

El punto interior permite una comparación geométrica uniforme; no identifica
entrada, plaza, acceso por carretera o punto de conexión eléctrica. Puede ser
poco representativo de un área extensa o de varias partes: la geometría original
y el método deben poder consultarse al interpretar la distancia. La distancia
cero no acredita que ambas instalaciones compartan parcela.

El vínculo municipal se toma de la geometría original y conserva **todas** las
intersecciones Silver, incluidos contactos de línea o punto. Si solo existe
un vínculo, su municipio sirve como contexto; si hay varios, el campo de
contexto exclusivo queda nulo y se consultan todos los vínculos. La posición
representativa no fuerza una asignación exclusiva ni elimina otros municipios.

## 4. Tablas materializadas

Son cuatro utilidades nuevas. Las tres tablas municipales ya materializadas
se mantienen. No se añade una tabla por cada fuente o indicador.

Todas las tablas nuevas incluirán `version_gold` (`VARCHAR`, obligatorio),
identificador de la ejecución de candidatos. El manifiesto referenciará por
separado la versión Gold municipal utilizada. Al concatenar ejecuciones,
`version_gold` formará parte de todas las claves siguientes.

### `gold_candidatos`

Una fila por elemento OSM preseleccionado; clave `candidato_id`.

| Campo | Tipo / nulos | Regla |
| --- | --- | --- |
| `candidato_id` | `VARCHAR`, obligatorio | Clave técnica JSON descrita arriba. |
| `origen_id`, `capa_origen` | `VARCHAR`, obligatorios | Procedencia Silver. |
| `fid_origen` | `BIGINT`, obligatorio | Identificador de fila de esa capa. |
| `osm_id`, `nombre_origen` | `VARCHAR`, admiten nulo | Valores publicados, sin inventar nombre o identidad física. |
| `categoria_origen`, `grupo_uso`, `representacion` | `VARCHAR`, obligatorios | Categoría, grupo y punto/área conservados. |
| `tipo_preseleccion` | `VARCHAR`, obligatorio | `aparcamiento_mapeado` o `destino_sin_aparcamiento_acreditado`. |
| `estado_revision` | `VARCHAR`, obligatorio | `pendiente_comprobacion_local` en la primera materialización; no se fabrican admisiones de campo. |
| `geometria` | `GEOMETRY('EPSG:25830')`, obligatoria | Original Silver completa. |
| `punto_representativo` | `GEOMETRY('EPSG:25830')`, admite nulo | Punto analítico, no acceso real. Ambas geometrías tendrán metadatos GeoParquet. |
| `metodo_representacion` | `VARCHAR`, obligatorio | `punto_original`, `punto_interior_interseccion_cv` o `sin_superficie_en_cv`. |
| `codigo_municipio_contexto` | `VARCHAR`, admite nulo | Solo con una intersección municipal; FK a `gold_municipios` de la versión referenciada. |
| `numero_municipios_relacionados` | `BIGINT`, obligatorio | Número de vínculos distintos en la tabla siguiente. |
| `estado_relacion_municipal` | `VARCHAR`, obligatorio | `interseccion_unica` o `interseccion_multiple`. Una selección que dice intersectar CV pero carece de vínculos detiene la ejecución. |
| `numero_correspondencias` | `BIGINT`, obligatorio | Pares de la tabla de correspondencias en los que participa; no número de duplicados confirmados. |

### `gold_candidato_municipio`

Una fila por `candidato_id` + `codigo_municipio`; ninguna asignación de demanda.

| Campo | Tipo / nulos | Regla |
| --- | --- | --- |
| `candidato_id` | `VARCHAR`, obligatorio | FK a candidatos. |
| `codigo_municipio` | `VARCHAR`, obligatorio | Código de cinco posiciones, FK a municipios. |
| `dimension_interseccion` | `SMALLINT`, obligatorio | 0, 1 o 2, conservado de Silver. |
| `superficie_interseccion_m2` | `DOUBLE`, admite nulo | Medida diagnóstica Silver solo para dimensión dos; no reparto de población ni demanda. |

### `gold_correspondencias_candidatos`

Una fila por `candidato_punto_id` + `candidato_area_id`; ambos FK a candidatos.
Se copian los indicios existentes, filtrando ambos extremos, sin nueva regla de fusión.

| Campo | Tipo / nulos | Regla |
| --- | --- | --- |
| `candidato_punto_id`, `candidato_area_id` | `VARCHAR`, obligatorios | Claves técnicas de cada extremo. |
| `punto_intersecta_area`, `coincide_id_publicado`, `coincide_nombre_normalizado` | `BOOLEAN`, obligatorios | Indicios Silver, sin convertirlos en identidad acreditada. |
| `distancia_plana_m` | `DOUBLE`, obligatoria | Distancia Silver entre esas geometrías, no entre sus puntos representativos. |
| `estado` | `VARCHAR`, obligatorio | `posible_correspondencia_sin_fusion`. |

### `gold_proximidad_candidato_recarga`

Una fila por `candidato_id` + `escenario`. Tres escenarios por elemento, incluso
si la distancia no es evaluable. No se almacena el producto cartesiano completo.

| Campo | Tipo / nulos | Regla |
| --- | --- | --- |
| `candidato_id` | `VARCHAR`, obligatorio | FK a candidatos. |
| `escenario` | `VARCHAR`, obligatorio | Uno de los tres conjuntos definidos abajo. |
| `instalacion_id_mas_cercana` | `VARCHAR`, admite nulo | FK a instalaciones de la Gold municipal referenciada; desempate por menor ID lexicográfico. |
| `distancia_plana_m` | `DOUBLE`, admite nulo | Mínimo de `ST_Distance(punto_representativo, geometria_instalacion)` en metros, sin redondear para elegir vecino. |
| `numero_instalaciones_a_distancia_minima` | `BIGINT`, obligatorio | Empates exactos antes de redondear; cero si no se puede calcular. |
| `estado_distancia` | `VARCHAR`, obligatorio | `calculable`, `sin_posicion_representativa` o `sin_recarga_admisible`. Si coinciden ausencias prevalece la primera. |

## 5. Distancias y sensibilidad de la oferta

Solo participan geometrías de instalación admitidas, válidas y no vacías,
en EPSG:25830. El manifiesto contará las exclusiones geométricas por escenario.
Se compara con toda la oferta del conjunto, **sin restringir al mismo municipio**.
No se exige que dos instalaciones tengan coordenadas distintas ni se fusionan
por compartirlas. La unidad de vecino es instalación, no conector.

| Escenario | Conjunto de instalaciones de `gold_recarga_instalaciones` | Interpretación |
| --- | --- | --- |
| `principal_admitida` | Presentes en copia principal y `estado_admision='admitida_version_principal'`. | Referencia principal de proximidad a oferta registrada con relación municipal admitida. |
| `incluye_pendientes` | Todas las presentes en la copia principal. | Sensibilidad al incorporar las posiciones publicadas de pendientes. No resuelve su asignación o posición física. |
| `incluye_ausentes_historicas` | Todas las presentes más los registros históricos ausentes. | Sensibilidad adicional al cambio de exportación. No acredita que los ausentes sigan operando ni los suma a oferta principal. |

Para la misma posición válida, al ampliar estos conjuntos la distancia mínima
no puede aumentar. Si cambia el vecino, se conserva su ID y estado en la tabla
de instalaciones. Se muestran las tres distancias como escenarios, sin promedio
ni puntuación de confianza inventada. Una admisión municipal no certifica la
posición exacta del cargador: las geometrías conservan las limitaciones de Silver.

La referencia MITECO preparada solo cubre CV. Puede haber oferta más cercana en
otras comunidades; el mínimo obtenido es el mínimo **del inventario utilizado**.
Se advertirá este límite en el manifiesto y en cualquier presentación de la
métrica; no se afirmará cobertura completa cerca del borde autonómico.

No son distancias de conducción o a pie ni tiempos de acceso. Tampoco se evalúan
compatibilidad de conector, potencia adecuada, horario, disponibilidad o uso.
No se define todavía un radio, una zona «sin servicio», porcentaje de población
cubierta o umbral de suficiencia. Esas métricas necesitan una definición adicional
y su sensibilidad; una distancia por sí sola no justifica instalar recarga.

## 6. Controles y trazabilidad exigidos

- Verificar huellas, esquemas, claves, estados y versiones de las entradas,
  incluida la concordancia de POI y recintos con la validación conjunta utilizada.
- Reconciliar la selección por categorías y representación con Silver;
  no forzar los recuentos históricos si cambia una copia. No perder registros
  por nombre nulo, intersecciones múltiples o punto no representable.
- Comprobar unicidad y FK de las cuatro tablas; cada par tiene extremos distintos,
  punto y área de la misma categoría, y conserva exactamente los indicios Silver.
- Conservar WKB y CRS originales; verificar validez, dimensión y pertenencia
  del punto analítico, estados nulos y ambas columnas geométricas al releer Parquet.
- Contrastar todos los vínculos municipales con Silver; contexto exclusivo solo
  con un vínculo y recuentos de correspondencias sin multiplicación de filas.
- Exigir tres filas de proximidad por candidato, valores finitos no negativos,
  vecino perteneciente al escenario, desempate reproducible y mínimo correcto.
  Probar vecino al otro lado de un límite, empate, área multipartita/limítrofe,
  falta de posición o de oferta y monotonicidad de escenarios.
- Manifiesto por ejecución con reglas, periodos reales, instantánea OSM,
  versión Gold municipal, huellas de código y entradas, salidas y controles.
  Carpeta nueva e indicador `actual.json` solo después de validar, sin alterar
  los indicadores municipales, Silver u originales.

## 7. Punto de continuación

Las cuatro tablas están materializadas y validadas en la ejecución
`20261020T160709239795Z`, con informe, manifiesto y `actual.json` en
`resultados/gold/candidatos/`. La inspección local de insumos, consultas y huellas queda fuera
del repositorio, bajo `resultados/diseno_gold/20261020_candidatos/`.
Ejecuciones inspeccionadas: POI `20261016T121902157473Z`, relaciones conjuntas
`20261019T094606691147Z` y base territorial `20261015T164603584512Z`.

La [revisión de ejemplos y sensibilidad](REVISION_EJEMPLOS_GOLD.md) está
completada sin modificar las tablas. Los [diagnósticos de coincidencia
área–recarga, solapamientos y posible influencia exterior](CONTROLES_ESPACIALES_GOLD.md)
ya están materializados en un bloque propio. Siguiente: definir cómo usar proximidad e indicadores municipales para comparar
zonas. Radios, normalización, pesos, elección conjunta de emplazamientos,
tráfico e i-DE se incorporarán cuando su utilidad y regla estén definidas.
