# Contrato inicial de tablas Gold

Versión **1 — 20-10-2026**, implementada en la [primera etapa municipal](GOLD_MUNICIPAL.md).
Tres tablas municipales materializadas y validadas; la [etapa de candidatos](CANDIDATOS_GOLD.md)
añade otras cuatro. Cobertura de personas y priorización pendientes.

## Finalidad y alcance de la primera etapa

Preparar el contexto de los 542 municipios para comparar demanda potencial y
oferta registrada de recarga, y explicar sus incertidumbres. La secuencia sigue
siendo **contexto municipal → revisión de candidatos → priorización**. Un municipio
no es un emplazamiento ni tiene accesibilidad uniforme en todo su territorio.

### Preguntas del producto y alcance de la respuesta

Las dos preguntas principales confirmadas son dónde se necesitan cargadores
y si hay suficiente oferta en una zona. La tercera, sobre infraestructura
para instalarlos, es opcional. Se traducen al alcance observable siguiente:

| Pregunta del usuario | Respuesta que se buscará con estos datos | Papel de Gold y límite |
| --- | --- | --- |
| ¿Qué zonas necesitan la instalación de cargadores eléctricos? | ¿Qué zonas conviene priorizar para estudiar nuevas instalaciones, según demanda potencial y cobertura registrada? | La primera etapa compara contexto municipal y oferta. La cobertura y priorización requieren la etapa posterior; no se estima una necesidad física exacta ni cuántos cargadores hacen falta. |
| ¿Hay suficiente oferta de cargadores en la zona? | ¿Qué oferta está registrada y cómo se sitúa respecto a la demanda potencial y la proximidad a esa oferta? | Recuentos, presión descriptiva y, después, proximidad con una definición espacial explícita. No se genera un sí/no de suficiencia operativa sin un criterio justificado y observaciones de uso. |
| ¿Tiene la zona la infraestructura necesaria para poner cargadores? Opcional. | ¿Qué información orientativa de la red eléctrica publicada existe en el entorno de un candidato? | i-DE puede aportar contexto posterior de puntos y capacidades publicados. No acredita acometida, conexión posible en la parcela, suelo, permisos, coste o viabilidad técnica integral. |

No se dispone de sesiones, ocupación, colas o demanda de energía suficientes
para comprobar si la oferta atiende el uso real. Tampoco se ha definido un
umbral de suficiencia. Un cociente alto puede ser un indicio comparativo;
uno bajo no acredita oferta suficiente. Estas preguntas no justifican añadir
una columna `oferta_suficiente` ni `instalacion_viable` con valores inventados.

La comparación municipal inicial se presentará a esa escala. La oferta próxima
al otro lado de un límite puede ser relevante; las zonas concretas y su medida
de accesibilidad se definirán en la etapa de candidatos. La pregunta eléctrica
se conserva como contexto opcional, sin condicionar la prioridad por demanda
y cobertura ni ampliar ahora las tres tablas.

Se definen **tres tablas y un manifiesto de ejecución**. Los estados de calidad
acompañan a los valores; no se necesita una tabla genérica de indicadores ni
una puntuación para esta etapa.

| Tabla materializada | Una fila representa | Clave dentro de una ejecución | Uso |
| --- | --- | --- | --- |
| `gold_municipios` | Un municipio de la referencia vigente. | `codigo_municipio` | Comparar contexto, oferta municipal y presión descriptiva; mostrar un mapa municipal. |
| `gold_recarga_instalaciones` | Un ID de instalación observado en la copia principal o conservado como ausencia del contraste histórico. | `instalacion_id` | Explicar los recuentos y distinguir presencia, asignación y registro histórico. |
| `gold_incertidumbre_recarga_municipio` | Un vínculo documentado de una instalación con un municipio afectado por un tipo de incertidumbre. | `instalacion_id`, `codigo_municipio`, `tipo_incertidumbre` | Localizar incertidumbre sin adjudicar cargadores pendientes a un municipio. |

Cada tabla incluye `version_gold` (`VARCHAR`, obligatorio), igual al identificador
de la ejecución. Si se concatenan ejecuciones, este campo se añade a todas las
claves. Las tres se almacenarán como Parquet/GeoParquet en una carpeta nueva de
`resultados/gold/`; no son vistas o tablas SQL ya registradas.

## 1. Entradas y selección temporal

No hay restricción académica de fechas. Se fijan periodos explícitos para que
dos municipios no se comparen con años elegidos silenciosamente de forma distinta.

| Variable o referencia | Entrada Silver o evidencia | Selección para el contrato v1 |
| --- | --- | --- |
| Municipio y provincia | `base_territorial/municipios` | 542 códigos de la relación INE de 2025. |
| Recinto | `base_territorial/recintos_municipales` | Geometría vigente conservada, EPSG:25830. Consulta de 2026; no acredita límite histórico de 2025. |
| Parque y Distintivo 0 | `demografia_parque/parque_municipal` | `fecha_referencia = 2025-12-31`. No usar PP000 ni reconstruir el TXT nacional. |
| Población | `demografia_parque/poblacion_municipal` | `sexo = 'Total' AND anio = 2025`. No sumar Total + Hombres + Mujeres. |
| Renta | `demografia_parque/renta_territorial` | `nivel_territorial = 'municipio' AND indicador = 'Renta neta media por persona' AND anio = 2023`. |
| Recarga principal seleccionada | `recarga_versionada`, desde la copia MITECO adquirida el 18-10-2026, con recibo y comparación conservados | Preparación diferenciada y validada; no confundir con la Silver histórica. |
| Asignaciones y evidencia de recarga | `validacion_conjunta/recarga_municipio_validado`, revisión y contraste espacial | Revalidar compatibilidad en la preparación diferenciada antes de admitirlas en la versión principal. |
| Ausencias entre exportaciones | Comparación completa de ambas copias | Conservar los nueve IDs ausentes como incertidumbre, sin concluir cierres. |

La inspección de las entradas verifica 542 filas de parque, 542 observaciones de
población Total en 2025 y 542 de renta seleccionada en 2023. En renta hay **534
valores informados y ocho nulos con estado `no_informado`**. No se sustituyen por
cero, por renta de distritos o por otro año individual. El código histórico
`12066` permanece separado y no se convierte a `46902`.

Las fuentes y periodos de esta tabla están disponibles. La entrada de
[recarga versionada](RECARGA_VERSIONADA_SILVER.md), adoptada tras la comparación,
ya está preparada en una ejecución diferenciada y conserva las históricas.
Cualquier cambio de copia o periodo generará otra ejecución y quedará
identificado en el manifiesto.

## 2. `gold_municipios`

**542 filas por ejecución**, incluidas las que tengan renta nula, ningún punto
con municipio admitido o incertidumbre. Códigos de municipio y provincia como
texto de cinco y dos posiciones; no se convierten a números.

Además de `version_gold`, contiene estos campos:

| Campo | Tipo / nulos | Origen o regla |
| --- | --- | --- |
| `codigo_municipio` | `VARCHAR`, obligatorio | Clave INE vigente. |
| `codigo_provincia` | `VARCHAR`, obligatorio | Referencia municipal. |
| `nombre_municipio` | `VARCHAR`, obligatorio | Nombre de la referencia municipal. |
| `geometria` | `GEOMETRY('EPSG:25830')`, obligatoria | Recinto Silver, sin simplificar o sustituir por centroide. |
| `fecha_referencia_parque` | `DATE`, obligatoria | 31-12-2025. |
| `parque_total` | `BIGINT`, admite nulo si fuente no informada | Parque municipal; nunca PP000. |
| `vehiculos_distintivo_0` | `BIGINT`, admite nulo si fuente no informada | Aproximación de demanda potencial, no BEV+PHEV exacto. |
| `proporcion_distintivo_0` | `DOUBLE`, admite nulo | Distintivo 0 / parque total, en escala 0–1; nulo si falta un operando o el parque es cero. |
| `anio_poblacion` | `SMALLINT`, obligatorio | 2025, incluso si faltase su valor. |
| `poblacion_total` | `BIGINT`, admite nulo | Población municipal con sexo Total. |
| `estado_poblacion` | `VARCHAR`, obligatorio | Estado conservado de Silver; una fila ausente es fallo de cobertura, no población cero. |
| `anio_renta` | `SMALLINT`, obligatorio | 2023, sin retroceso individual a otro año. |
| `renta_neta_media_persona_eur` | `DECIMAL(18,2)`, admite nulo | Renta municipal seleccionada; no media de distritos/secciones ni suma de rentas medias. |
| `estado_renta` | `VARCHAR`, obligatorio | Estado original, incluidos los ocho `no_informado`. |
| `fecha_adquisicion_recarga` | `TIMESTAMPTZ`, obligatoria para la copia seleccionada | 18-10-2026 18:38:01.029767 UTC según recibo; no fecha de operación. |
| `instalaciones_con_municipio_admitido` | `BIGINT`, obligatorio | IDs presentes en copia principal y con admisión municipal validada en esa versión. |
| `puntos_con_municipio_admitido` | `BIGINT`, obligatorio | Claves distintas instalación/punto de las instalaciones anteriores. |
| `conectores_con_municipio_admitido` | `BIGINT`, obligatorio | Claves distintas instalación/punto/conector, sin multiplicar puntos por conectores. |
| `distintivo_0_por_punto_admitido` | `DOUBLE`, admite nulo | Distintivo 0 / puntos con municipio admitido, solo con numerador informado y denominador positivo. |
| `estado_presion_descriptiva` | `VARCHAR`, obligatorio | `calculable`, `sin_numerador_informado` o `sin_puntos_admitidos`; si coinciden ambas ausencias, prevalece `sin_numerador_informado`. |
| `instalaciones_pendientes_relacionadas` | `BIGINT`, obligatorio | IDs distintos presentes en copia principal vinculados por `asignacion_pendiente` en la tabla 3. Recuento diagnóstico, sin asignación. |
| `instalaciones_ausentes_relacionadas` | `BIGINT`, obligatorio | IDs distintos vinculados por `ausencia_exportacion` en la tabla 3. No se añaden a la oferta principal. |
| `hay_incertidumbre_sin_localizar` | `BOOLEAN`, obligatorio | Verdadero si alguna incertidumbre de la versión carece de todo vínculo municipal disponible; avisa del límite del diagnóstico local. |

### Interpretación y reglas de integración

- La base de la tabla son los 542 municipios. Parque, población y renta se
  seleccionan y comprueban como relaciones de como máximo una fila por municipio
  **antes** de unirlas. Se usan uniones que conservan la base completa.
- Los recuentos de recarga se agregan desde la tabla 2 filtrando
  `presente_copia_principal = true` y `estado_admision = 'admitida_version_principal'`.
  No se construyen uniendo en bruto municipio → instalaciones → puntos → conectores.
- El cero de un recuento significa «ningún registro con municipio admitido en
  esta copia», una vez verificada la cobertura de las entradas. No significa
  ausencia física de recarga. Si falta un bloque requerido, la ejecución falla;
  no se sustituyen tablas ausentes por tablas vacías y ceros.
- La presión es descriptiva y puede calcularse sobre oferta parcial; los dos
  recuentos de incertidumbre deben acompañarla. No usar infinito ni dar máxima
  prioridad automática a un municipio con denominador cero.
- Los recuentos de incertidumbre pueden vincular una instalación con varios
  municipios. **No se suman entre municipios para obtener un total autonómico.**
- Renta y población son contexto. Una renta nula no elimina un municipio ni lo
  penaliza; el parque municipal no se reparte entre POI como demanda observada.
- No se añaden superficie servida, personas cubiertas, distancia desde el
  centroide municipal, puntuación o ranking: aún no se ha definido una medida
  válida de cobertura para esos usos. La oferta municipal no mide accesibilidad.

## 3. `gold_recarga_instalaciones`

Una fila por ID de instalación, no por conector. Para las dos copias comparadas
el universo de diagnóstico esperado es **1.526 IDs**: 1.517 presentes en la
principal seleccionada y nueve conservados solo como ausencia histórica. Esto no
convierte la unión de copias en un inventario de instalaciones activas.

Además de `version_gold`:

| Campo | Tipo / nulos | Origen o regla |
| --- | --- | --- |
| `instalacion_id` | `VARCHAR`, obligatorio | Código MITECO, sin reemplazarlo por nombre o coordenadas. |
| `version_recarga_observada` | `VARCHAR`, obligatorio | Referencia a copia/huella en el manifiesto. Copia principal si está presente; original en los nueve ausentes. |
| `presente_copia_principal` | `BOOLEAN`, obligatorio | Presencia del ID en la exportación seleccionada. No indica apertura, cierre o funcionamiento. |
| `nombre_instalacion` | `VARCHAR`, obligatorio | De la copia observada identificada. |
| `operador_id` | `VARCHAR`, obligatorio | De la misma copia, sin usar operador como clave física. |
| `geometria` | `GEOMETRY('EPSG:25830')`, admite nulo | Geometría admitida por preparación espacial; no usar coordenadas de una ficha comercial como sustituto. |
| `estado_geometria` | `VARCHAR`, obligatorio | Estado de la preparación espacial referenciada. Geometría no admitida queda fuera de distancias. |
| `codigo_municipio_admitido` | `VARCHAR`, admite nulo | Municipio admitido actual o histórico según el estado siguiente; nunca el declarado por defecto. |
| `estado_admision` | `VARCHAR`, obligatorio | `admitida_version_principal`, `admitida_solo_historica` o `pendiente`. |
| `metodo_admision` | `VARCHAR`, admite nulo | Método de la relación validada; nulo si pendiente. La referencia concreta se conserva en el manifiesto. |
| `puntos_registrados` | `BIGINT`, obligatorio | Claves instalación/punto de la copia observada, agregadas por separado. |
| `conectores_registrados` | `BIGINT`, obligatorio | Claves instalación/punto/conector de esa copia. |
| `fecha_adquisicion_observacion` | `TIMESTAMPTZ`, admite nulo | Recibo de la copia principal; nula en registros solo históricos porque se desconoce su adquisición. |

Las 81 admisiones documentales conservan identidad y ubicación y se han
revalidado contra sus evidencias en la entrada diferenciada. No se hereda
una admisión si cambian los atributos
que la sustentan. La geometría histórica solo puede reutilizarse con identidad
de coordenadas, procedencia explícita y controles; no por semejanza espacial.

Reconciliación comprobada en la entrada versionada y en la primera ejecución Gold:

| Estado en la copia principal seleccionada | Instalaciones | Puntos | Conectores |
| --- | ---: | ---: | ---: |
| Con admisión revalidada en la nueva preparación | 1.466 | 4.194 | 5.017 |
| Sin admisión previa | 51 | 165 | 185 |
| **Total presente** | **1.517** | **4.359** | **5.202** |

Fuera del total presente se conservan nueve IDs históricos, con 43 puntos y
43 conectores: ocho con municipio admitido solo históricamente y Exoil Pista
de Silla pendiente. La Silver original conserva sus 52 pendientes; la ausencia
de Exoil no los convierte en 51 conflictos resueltos.

No se suma potencia de conectores para obtener potencia simultánea de una
instalación ni se deduplica por coordenadas compartidas. El estado de municipio
admitido acredita la relación territorial documentada, no operación efectiva.

## 4. `gold_incertidumbre_recarga_municipio`

Tabla de relaciones diagnósticas. Incluye solamente códigos de los 542
municipios y vínculos sustentados por las entradas disponibles. No contiene
recuentos de puntos que puedan sumarse repetidamente en distintos municipios.

Además de `version_gold`:

| Campo | Tipo / nulos | Regla |
| --- | --- | --- |
| `instalacion_id` | `VARCHAR`, obligatorio | Referencia a la tabla 2. |
| `codigo_municipio` | `VARCHAR`, obligatorio | Municipio potencialmente afectado, sin darlo por asignación admitida. |
| `tipo_incertidumbre` | `VARCHAR`, obligatorio | `asignacion_pendiente` o `ausencia_exportacion`. |
| `es_municipio_admitido_historico` | `BOOLEAN`, obligatorio | Vínculo de una instalación ausente con su relación admitida anterior. |
| `es_municipio_declarado` | `BOOLEAN`, obligatorio | Código declarado reconocido por la referencia territorial; no valida la asignación. |
| `es_candidato_espacial` | `BOOLEAN`, obligatorio | Relación de candidato de la capa espacial, no una asignación forzada. |

Reglas de construcción aplicadas:

1. Para las **51 instalaciones presentes pendientes**, relacionar los municipios
   declarados reconocidos y todos los candidatos espaciales conservados, con
   `tipo_incertidumbre = 'asignacion_pendiente'`.
2. Para los **nueve IDs ausentes**, usar `ausencia_exportacion`. Si hay admisión
   histórica, localizar el aviso en ese municipio; si no la hay, usar declarado
   reconocido y candidatos espaciales, manteniendo su condición no admitida.
   Exoil Pista de Silla conserva `estado_admision = 'pendiente'` en la tabla 2.
3. Cuando un municipio tenga varios papeles para la misma instalación y tipo,
   reunirlos en una fila con las banderas correspondientes. Al menos una bandera
   debe ser verdadera. No elegir solo el municipio más próximo.
4. Si no hay ningún vínculo disponible, conservar la instalación y su estado en
   la tabla 2 y declarar incertidumbre sin localizar en el manifiesto y la tabla 1.
   No inventar un municipio ni extender una afectación supuesta a toda la provincia.

Estas relaciones permiten señalar incertidumbre municipal sin asignar allí
vehículos o puntos. No delimitan áreas de influencia, accesibilidad de personas
o localización física de plazas. El futuro mapa distinguirá valor y calidad:
la incertidumbre parcial acompaña al valor; el gris se reserva para la variable
que no pueda evaluarse. No hay penalización numérica automática por incertidumbre.

## 5. Manifiesto y trazabilidad

Un `manifiesto.json` por ejecución, junto a un informe de controles, es suficiente
para esta primera etapa. Contendrá:

- `version_gold`, versión de este contrato y fecha/hora de proceso UTC.
- Tabla y archivo de cada entrada, ejecución Silver, bytes y SHA-256; copias
  de recarga, recibo, evidencia de comparación y referencia de la admisión municipal.
- Reglas y filtros por variable, unidades, periodos reales y adquisición conocida;
  consulta territorial separada de fecha de vigencia de los límites.
- Fuente del código y parámetros efectivos, incluidas versiones principales e
  históricas. Fecha de proceso separada de todas las fechas de observación.
- Por tabla: claves, columnas, tipos, filas, huellas de salida y controles.
  Por incertidumbre: instalaciones distintas, vínculos y casos sin localizar.

Las rutas serán relativas al proyecto. El manifiesto no contendrá credenciales
o rutas particulares de un equipo. No se actualizará el indicador de ejecución
vigente si falla un control; una ejecución nueva no sobrescribirá otra validada.

## 6. Controles de aceptación de la materialización

| Control | Condición de aceptación |
| --- | --- |
| Identidad de las entradas | Coinciden con sus huellas y reportes; preparación de recarga principal y admisiones verificadas. |
| Base municipal | Exactamente 542 claves únicas y todas las referencias reconocidas, sin pérdida por uniones. |
| Unicidad tras selección | Una fila por municipio para parque, población Total y renta municipal elegida. Duplicados no se resuelven escogiendo la primera fila. |
| Periodos y ausencias | Parque 2025-12-31, población 2025, renta 2023; ocho rentas nulas conservadas para estas entradas. Ningún año o valor imputado silenciosamente. |
| Valores de demanda | Recuentos no negativos, Distintivo 0 no superior al parque; proporción solo con denominador válido. |
| Recarga por entidad | Puntos y conectores se cuentan por sus claves; cada ID aparece una vez en la tabla 2. Reconciliación de presentes y ausentes por separado. |
| Oferta municipal | Sumas municipales iguales a las entidades presentes con admisión validada; ningún pendiente o ausente incluido por defecto. |
| Presión descriptiva | Cociente solo con denominador positivo; nunca infinito; nulos y estados concordantes, con avisos de parcialidad accesibles. |
| Incertidumbre | Clave compuesta única, referencias válidas, tipos coherentes con presencia y admisión; banderas justificadas. No duplicar una instalación al contarla dentro del mismo municipio. |
| Geometría | Recintos válidos en EPSG:25830; no se pierde el CRS. Geometrías de recarga no admitidas no participan en distancias. |
| Conservación | No modificar Fuentes, las copias comparadas ni las ejecuciones Silver históricas. |

Los recuentos esperados pertenecen a estas copias, no son una cuota a alcanzar
forzando asignaciones. Ante una diferencia, se investiga y documenta antes de
declarar una ejecución válida.

## 7. Etapa posterior: candidatos y cobertura

El [contrato de candidatos y proximidad](CONTRATO_CANDIDATOS_GOLD.md) define
la siguiente etapa: `gold_candidatos`, vínculos municipales, correspondencias y
proximidad por escenarios. Está materializado y validado. No se presupone que cada
POI Silver sea un lugar distinto o un emplazamiento instalable.

Su contrato necesitará: identificador del candidato y referencias OSM,
geometría y método de representación, estado de revisión/elegibilidad, vínculo
municipal admitido o pendiente, distancia geométrica a recarga registrada
admitida y estado de esa distancia. También la identificación del vecino usado
y sensibilidad a recarga pendiente o ausente; las alternativas no se suman a la
oferta confirmada. Una posición interior de un área no acredita su acceso.

El municipio aportará contexto, sin convertir su parque o población en demanda
observada de cada POI. La comparación de distancias deberá poder incluir oferta
al otro lado de límites municipales y declarar que el inventario actual solo
cubre CV, con posible sesgo de borde frente a otras comunidades. No se usarán
tiempos por carretera sin validar una red apta para enrutamiento.

Tráfico, capacidad i-DE y características del lugar se incorporarán cuando
haya una definición de uso concreta; la renta municipal ya forma parte del
contexto de la primera etapa. i-DE respondería solo a la tercera pregunta,
opcional, como contexto orientativo de red publicada, sin garantía de conexión
ni suma de capacidades de un municipio. Su ausencia no acredita imposibilidad
de instalación ni debe bloquear la comparación por demanda y cobertura.
No se añaden columnas vacías para datos o métricas que aún no se han definido.

## Próximo trabajo

La primera etapa municipal está materializada y validada. Sus indicadores y
límites se han revisado y el contrato de candidatos está materializado. Las
[variables y normalización](VARIABLES_NORMALIZACION_GOLD.md) cuentan con un
bloque propio que conserva los diagnósticos espaciales. La
[comparación de sensibilidad](SENSIBILIDAD_GOLD.md) está completada; siguiente
trabajo analítico: ensayar ponderaciones.
No cambia las fórmulas de este contrato.
Radios y pesos se definirán antes de sus respectivos cálculos.

La definición se apoya en el [planteamiento de Gold](PLANTEAMIENTO_GOLD.md), el
[inventario Silver](TABLAS_Y_COLUMNAS_SILVER.md) y la
[comparación temporal](COMPARACION_RECARGA_MITECO.md). Se han comprobado esquemas,
etiquetas y cobertura de las selecciones, y se han materializado las tres tablas
según el [informe de ejecución](GOLD_MUNICIPAL.md).
