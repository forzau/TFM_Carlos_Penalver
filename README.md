# TFM de Carlos Peñalver

Trabajo de Fin de Máster del Máster de Ciencia de Datos e IA.
El trabajo se organiza mediante entregas y no incluye una memoria.
Repositorio: [forzau/TFM_Carlos_Penalver](https://github.com/forzau/TFM_Carlos_Penalver).

Tema elegido: **localización óptima de nuevos puntos de recarga para vehículos
eléctricos en la Comunitat Valenciana**. El objetivo es apoyar decisiones sobre
dónde ampliar la infraestructura pública de recarga utilizando datos reales y públicos.

**Estado a 21-10-2026:** datos y preparación completados hasta Gold, con la
Entrega 02 redactada. El diseño del modelo queda en pausa, pendiente de
orientación académica antes de concretar reglas de combinación y ponderaciones.
Las comparaciones de sensibilidad se conservan como evidencia; no hay pesos
definitivos, prioridad combinada o aplicación web implementados.

La auditoría técnica de las copias locales se documenta en
[Auditoría de fuentes](docs/AUDITORIA_FUENTES.md). Sus hallazgos y la preparación
hasta Gold se recogen en la [Entrega 02](docs/entregas/02_datos_y_preparacion.md).

## Estructura

| Ruta | Uso |
| --- | --- |
| `docs/entregas/` | Entregas y documentos de trabajo existentes. |
| `docs/FUENTES.md` | Fuentes de datos previstas y limitaciones pendientes de revisar. |
| `config/catalogo_bronze.json` | Registro de procedencia, periodos, condiciones y entradas de Bronze. |
| `datos/bronze/` | Copias complementarias preservadas, fuera de Git. |
| `src/` | Descarga de referencias, auditoría y registro reproducibles. |
| `notebooks/` | Cuadernos de exploración, si se utilizan. |
| `resultados/` | Salidas generadas; los archivos pesados no se versionan. |
| `Fuentes/` | Datos originales locales, excluidos del repositorio por su volumen. |

## Documentación

[Entrega 1: propuesta inicial de ideas de producto](docs/entregas/01_ideas_producto.md).
Recoge las tres propuestas iniciales; posteriormente se ha seleccionado la
planificación de infraestructura de recarga.

[Entrega 2: datos y preparación](docs/entregas/02_datos_y_preparacion.md).
Cinco apartados actualizados al 21-10-2026: fuentes, condiciones de uso,
flujo reproducible, trece tablas Gold preparadas y limitaciones. No requiere
entrenamiento o un ranking para esta entrega.

[Fuentes de datos](docs/FUENTES.md).

[Inventario de tablas y columnas Silver](docs/TABLAS_Y_COLUMNAS_SILVER.md):
48 tablas materializadas, incluidas las doce de recarga versionada, con sus
columnas, tipos y recuentos comprobados. Las versiones de oferta no se suman.

[Catálogo de Bronze](docs/CATALOGO_BRONZE.md): once recursos de nueve bloques,
incluidas las referencias territoriales oficiales, con un manifiesto local de
integridad para 39 archivos de datos y documentación.

[Plan de trabajo de Silver](docs/PLAN_SILVER.md): ocho fases con salidas y
condiciones de cierre. Las fases 1–3 están cerradas: convenciones aceptadas, un
[diccionario de campos y claves](docs/DICCIONARIO_SILVER.md) y la
[configuración técnica comprobada](docs/CONFIGURACION_SILVER.md).
La [base territorial Silver](docs/BASE_TERRITORIAL_SILVER.md) contiene los 542
municipios y sus recintos verificados. También están preparados
[parque DGT, población y renta](docs/DEMOGRAFIA_PARQUE_SILVER.md).
La [recarga MITECO](docs/RECARGA_SILVER.md) tiene sus entidades tabulares
preparadas. Su [capa y contraste municipal](docs/RECARGA_ESPACIAL_SILVER.md)
conservan las 1.526 instalaciones, con 1.393 asignaciones admitidas y 133
discrepancias en la ejecución inicial; la revisión posterior deja 52 pendientes,
como se detalla en la fase 8.
La [fase 5, aforos y red viaria](docs/TRAFICO_RED_SILVER.md), está preparada con
sus incidencias señaladas. La [fase 6, POI de OSM](docs/POI_OSM_SILVER.md), conserva
elementos, clasificación de interés y posibles correspondencias sin fusionarlos.
La [fase 7, capacidad de demanda i-DE](docs/CAPACIDAD_DEMANDA_SILVER.md), está
preparada como tabla y capa EPSG:25830, con 423 relaciones municipales admitidas
en 116 municipios. Publicación 04-09-2026 y periodo agosto según formato CNMC;
el día exacto de corte sigue desconocido.
La [fase 8, relaciones y validación conjunta](docs/VALIDACION_CONJUNTA_SILVER.md),
está cerrada operativamente con limitaciones: 1.430.940 relaciones espaciales,
las 133 discrepancias de recarga revisadas y 81 resueltas documentalmente.
Quedan 52 asignaciones municipales de recarga pendientes; i-DE ya está
integrada espacialmente. Silver queda preparada con estas restricciones; la
primera etapa municipal Gold ya está materializada con los límites descritos abajo.

Se conservan las cinco geometrías IGN señaladas y excluidas de cálculos métricos,
y las 52 asignaciones de recarga pendientes de la versión histórica. La Gold
municipal comunica la incertidumbre de la entrada seleccionada y sus ausencias
entre exportaciones, sin interpretarlas como ausencia física de cargadores.

[Planteamiento inicial de Gold](docs/PLANTEAMIENTO_GOLD.md): punto de partida,
finalidad de la capa y orientación acordada: recarga de destino primero,
combinando demanda y cobertura, con la secuencia zonas → candidatos. Incluye
indicadores, método y evaluación aceptados como dirección de trabajo; versión
temporal resuelta para la entrada de recarga y parámetros finales pendientes.
La [preparación versionada](docs/RECARGA_VERSIONADA_SILVER.md) utiliza la copia
adquirida el 18-10, con 1.466 asignaciones municipales admitidas y 51 pendientes,
conservando nueve ausencias históricas por separado. El [contrato inicial de tablas
Gold](docs/CONTRATO_GOLD.md) define contexto municipal, resumen de instalaciones
y relaciones de incertidumbre, con campos, fórmulas, periodos y controles.
La [primera etapa Gold municipal](docs/GOLD_MUNICIPAL.md) está materializada:
542 municipios, 1.526 registros de instalación y 112 vínculos de incertidumbre.
El [contrato de candidatos y proximidad](docs/CONTRATO_CANDIDATOS_GOLD.md)
define la segunda etapa: 16.377 elementos OSM preseleccionados para revisión,
sus vínculos municipales, correspondencias y proximidad por escenarios.
La [segunda etapa Gold](docs/CANDIDATOS_GOLD.md) ya materializa esas cuatro
tablas: 16.377 elementos, 16.484 vínculos, 75 correspondencias y 49.131 filas
de proximidad. Estas dos etapas reúnen siete tablas; cobertura de personas, priorización
y aplicación siguen pendientes.

La [revisión de ejemplos territoriales](docs/REVISION_EJEMPLOS_GOLD.md)
contrasta doce municipios y una muestra de distancias. Los indicadores son
útiles para explorar, pero antes de priorizar se necesitan diagnósticos de
recarga que intersecta áreas, solapamientos entre candidatos y posible oferta
exterior al inventario CV. La revisión conserva las siete tablas sin cambios.
Los [tres controles espaciales](docs/CONTROLES_ESPACIALES_GOLD.md) ya están
materializados en un bloque propio: coincidencias de áreas con recarga,
intersecciones entre candidatos y avisos de posible influencia exterior.
Estas etapas reúnen diez tablas; estos diagnósticos no fusionan lugares ni acreditan
funcionamiento, acceso o suficiencia.

La [definición de variables y normalización](docs/VARIABLES_NORMALIZACION_GOLD.md)
selecciona volumen potencial municipal y distancia mínima a la geometría del
candidato, con escala logarítmica y contraste lineal sobre referencias fijas.
La etapa de variables añade tres tablas: referencias, demanda municipal y
separación por candidato/escenario, incluido el aviso de borde adaptado a la
geometría. Se conservan las diez anteriores; Gold reúne trece tablas.
No hay puntuación combinada o ranking calculado.

La [comparación de sensibilidad](docs/SENSIBILIDAD_GOLD.md), posterior al cierre
de datos y preparación, contrasta escalas y escenarios sin aplicar pesos ni
modificar Gold. Se conservan ambas escalas para el siguiente ensayo de ponderación.
La entrega de preparación ya está documentada; revisión y publicación se gestionan
por separado del desarrollo analítico posterior.

```powershell
.venv\Scripts\python.exe src/preparar_gold_municipal.py
.venv\Scripts\python.exe src/preparar_gold_candidatos.py
.venv\Scripts\python.exe src/preparar_controles_gold.py
.venv\Scripts\python.exe src/preparar_variables_gold.py
```

[Comparación de versiones MITECO](docs/COMPARACION_RECARGA_MITECO.md): contraste
completo de la copia original y la adquirida el 18-10-2026, compatibilidad de la
evidencia municipal y recomendación temporal para Gold, sin sustituir Silver.

La preparación versionada se reproduce con:

```powershell
.venv\Scripts\python.exe src/preparar_recarga_versionada.py --comparacion resultados/comparacion_recarga/20261020T143417939020Z/informe.json --evidencias-recarga resultados/revision_recarga/20261018_revision_manual/decisiones.json
```

## Reproducción

### Script único para la Entrega 02

[preparar_dataset.py](src/preparar_dataset.py) reúne en un solo archivo las
transformaciones Bronze → Silver → Gold y sus controles. `main()` muestra el
recorrido completo; las secciones por fuente contienen los lectores y las
transformaciones. Es independiente de los demás scripts, que se conservan.

Con el entorno indicado abajo y la extensión `spatial` instalada, ejecutar
desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe src/preparar_dataset.py --comprobar-entradas
.\.venv\Scripts\python.exe src/preparar_dataset.py
```

Si falta la extensión, se instala una vez con conexión a Internet:

```powershell
.\.venv\Scripts\python.exe -c "import duckdb; c=duckdb.connect(config={'extension_directory':'.venv/duckdb_extensions'}); c.execute('INSTALL spatial'); c.close()"
```

La primera orden comprueba archivos, huellas y metadatos sin transformar tablas.
El bloque `ENTRADAS` del script identifica el catálogo y cuatro entradas
complementarias: exportación principal MITECO con su recibo, metadatos MITECO,
metadatos i-DE y decisiones municipales con sus evidencias. Esas copias deben
estar disponibles junto con los originales; no se descargan al clonar el código.
Las rutas son relativas y pueden ajustarse a la ubicación de las copias conservadas.

Cada ejecución genera su propio `resultados/entrega02/<ejecución>/`: manifiesto
Bronze, 48 tablas Silver, 13 tablas Gold y `manifiesto.json` con entradas,
esquemas, claves, recuentos y controles. La ejecución lee las fuentes y sus
evidencias, sin utilizar Silver/Gold anteriores ni modificar sus `actual.json`.
El TXT DGT se procesa secuencialmente, con almacenamiento temporal en disco.
El manifiesto final identifica una ejecución completada; una carpeta sin él
corresponde a una preparación interrumpida o fallida.

Validado el 22-10-2026 con Python 3.12.14 y DuckDB 1.5.0: las 61 tablas
reproducen los esquemas y el contenido de la preparación anterior, comparando
también todas las geometrías como WKB y excluyendo únicamente el identificador
de ejecución `version_gold`. La suite completa pasa 213 pruebas, ocho del
nuevo script. No se requieren dependencias adicionales.

Los apartados siguientes conservan la reproducción histórica por etapas.

Se utiliza Python 3.12 y DuckDB 1.5.0, sin servidor de base de datos. En la raíz
del proyecto, con Python instalado, preparar el entorno y ejecutar:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src/auditar_fuentes.py
```

Los originales no están incluidos al clonar el repositorio. Los accesos están en
[Fuentes](docs/FUENTES.md); la correspondencia de archivos y las versiones
comprobadas se detallan en la auditoría. El script espera esas copias bajo
`Fuentes/`, las lee sin modificarlas y guarda perfiles agregados en
`resultados/auditoria/perfil.json`, fuera de Git. No publica registros originales.
Las descargas actuales pueden diferir de las versiones auditadas.

DuckDB está limitado a 1 GB de memoria de su motor y dos hilos; esto no limita
todo el proceso Python. Utiliza disco temporal en `resultados/auditoria/temporales/`
si lo necesita. La lectura del CSV UTF-16 de MITECO genera una copia temporal
decodificada que se elimina al cerrar esa lectura. La auditoría recorre el TXT
nacional de DGT completo y vuelve a leer una muestra; necesita acceso a los originales.
No requiere extensiones de DuckDB: los GeoPackages se inspeccionan con SQLite
en modo de solo lectura. Todavía no ejecuta el flujo Silver/Gold.

### Comprobación municipal de DGT

La [alternativa municipal verificada](docs/DGT_COBERTURA_MUNICIPAL.md) cubre los
542 municipios del proyecto. Se adopta Distintivo 0 como aproximación de demanda
potencial, conservando el detalle BEV/PHEV donde esté observado.

```powershell
.\.venv\Scripts\python.exe src/auditar_dgt_municipal.py
```

Este script utiliza openpyxl 3.1.5 para leer el Excel oficial. Lo descarga si falta
en `datos/bronze/dgt_municipal/2025/` y guarda el perfil en
`resultados/auditoria_dgt/`, sin tocar `Fuentes/`. Ambas ubicaciones quedan fuera
de Git. La descarga requiere conexión a Internet; no genera Silver ni Gold.

### Registro de Bronze

Con las entradas del catálogo disponibles, incluida la ficha PDF municipal:

```powershell
.\.venv\Scripts\python.exe src/catalogar_bronze.py
```

Se genera un manifiesto nuevo en `resultados/bronze/` con metadatos, tamaños y
SHA-256, leyendo por bloques sin modificar los originales. Para volver a comprobar
su integridad, ejecutar el mismo script con `--verificar` y la ruta del manifiesto.
El [catálogo](docs/CATALOGO_BRONZE.md) explica las entradas, la conservación y los
metadatos pendientes. No se presume que una descarga actual sea idéntica.

### Referencias territoriales y procedencia

Se incorporan la relación oficial de municipios INE de 2025 y la respuesta WFS
de unidades administrativas del IGN para Comunitat Valenciana:

```powershell
.\.venv\Scripts\python.exe src/incorporar_referencias.py
.\.venv\Scripts\python.exe src/auditar_referencias.py
```

La primera descarga requiere Internet; las copias existentes se verifican contra
sus recibos y se reutilizan sin red. La auditoría posterior contrasta los 542
códigos municipales de INE, IGN, población y DGT, y documenta el código histórico
12066 de renta sin cambiar los originales. El perfil queda en
`resultados/referencias_territoriales/perfil.json`.
El [informe de referencias y procedencia](docs/REFERENCIAS_TERRITORIALES.md)
recoge además las tablas INE identificadas y las limitaciones de versión.

### Compatibilidad técnica de Silver

Se usarán Parquet para tablas y GeoParquet para capas, con EPSG:25830 en las
operaciones métricas admitidas. La extensión espacial oficial de DuckDB se instala
en el entorno local con la primera ejecución:

```powershell
.\.venv\Scripts\python.exe src/comprobar_entorno_silver.py --instalar-spatial
```

Después puede repetirse sin red omitiendo `--instalar-spatial`. Comprueba tipos,
metadatos CRS y muestras de los originales; requiere las copias Bronze, no genera
tablas Silver y guarda su resumen en `resultados/diseno_silver/entorno.json`.
La [configuración](docs/CONFIGURACION_SILVER.md) documenta precisión, lectores y
límites pendientes. La auditoría inicial sigue sin necesitar esta extensión.

### Preparación de la base territorial Silver

Con las ocho copias territoriales y un manifiesto Bronze que las identifique:

```powershell
.\.venv\Scripts\python.exe src/preparar_base_territorial.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
```

Ajustar la ruta al manifiesto disponible en ese equipo. El proceso verifica esas
entradas, prepara y comprueba 542 municipios y recintos, y guarda una ejecución
nueva bajo `resultados/silver/base_territorial/`, sin red. `actual.json` señala la
última ejecución validada; una ejecución fallida no sustituye la anterior.
El [informe de fase 2](docs/BASE_TERRITORIAL_SILVER.md) recoge resultados y límites.

### Preparación de parque, población y renta

Con la base territorial validada y las copias Bronze disponibles:

```powershell
.\.venv\Scripts\python.exe src/preparar_demografia_parque.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
```

El proceso verifica las cinco entradas implicadas y prepara las tablas por
entidad, conservando años, ausencias y códigos históricos separados. El TXT DGT
se procesa secuencialmente con atributos seleccionados en una base temporal en
disco y límite de memoria del motor de 1 GB; necesita espacio temporal libre.
Las salidas Parquet y el informe quedan bajo `resultados/silver/demografia_parque/`,
con `actual.json` como indicador de la última ejecución validada. No descarga
datos ni requiere nuevas dependencias. El [informe de fase 3](docs/DEMOGRAFIA_PARQUE_SILVER.md)
recoge controles y limitaciones. La fase 4 posterior prepara la recarga MITECO.

### Preparación de recarga existente

```powershell
.\.venv\Scripts\python.exe src/preparar_recarga.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
```

Se comprueba la copia Bronze, se conservan las comillas interiores del exportador
y se separan instalaciones, puntos y conectores, sin perder los atributos variables
del detalle. Las salidas Parquet y su informe quedan en `resultados/silver/recarga/`,
con `actual.json` tras validar. El [informe de fase 4](docs/RECARGA_SILVER.md)
documenta recuentos y límites, además de la identificación posterior del CRS
declarado EPSG:4258. El script reproduce las tablas originales sin geometría;
la fase 8 incorporará la capa y su contraste territorial. Funciona sin red ni
nuevas dependencias. La fase 5 posterior prepara tráfico y red.

### Preparación de aforos y red viaria

```powershell
.\.venv\Scripts\python.exe src/preparar_trafico_red.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
```

Con `spatial` instalado, prepara las 17 capas anuales GVA y separa geometrías de
tramo IGN de sus asociaciones con viales. Las capas conservan EPSG:25830 explícito;
IGN se transforma desde EPSG:4258 manteniendo Z. La base temporal usa almacenamiento
v1.5.0, memoria del motor de 1 GB y dos hilos; necesita espacio temporal libre.
Guarda salidas e informe en `resultados/silver/trafico_red/`, con `actual.json`
solo tras validar. El [informe de fase 5](docs/TRAFICO_RED_SILVER.md) recoge las
incidencias conservadas, la cobertura y los límites para usar estos datos.
La fase 6 posterior prepara los puntos de interés OSM.

### Preparación de puntos de interés OSM

```powershell
.\.venv\Scripts\python.exe src/preparar_poi_osm.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
```

Con la base territorial y `spatial` disponibles, conserva seis capas de puntos y
áreas, marca su relación con el ámbito y selecciona categorías para revisión.
Los objetos exteriores y las posibles correspondencias se conservan; no se
deduplican establecimientos. El [informe de fase 6](docs/POI_OSM_SILVER.md)
detalla reglas y límites. Salidas e informe quedan en `resultados/silver/poi_osm/`,
con `actual.json` tras validar. Siguiente bloque: fase 7, capacidad de demanda i-DE.

### Preparación de capacidad de demanda i-DE

```powershell
.\.venv\Scripts\python.exe src/preparar_capacidad_demanda.py --manifiesto-bronze resultados/bronze/manifiesto_20261015T151441821178Z.json
```

Conserva los 17 campos de los puntos publicados en las tres provincias, con
medidas y banderas tipadas, estados y procedencia. Las salidas Parquet y su
informe quedan en `resultados/silver/capacidad_demanda/`, con `actual.json`
tras validar. El [informe de fase 7](docs/CAPACIDAD_DEMANDA_SILVER.md) explica
las ausencias y los límites de uso. Funciona sin red ni nuevas dependencias;
reproduce la preparación tabular histórica. La capa complementaria se genera,
sin red, después de verificar los metadatos acreditados:

```powershell
.\.venv\Scripts\python.exe src/georreferenciar_capacidad_demanda.py --metadatos-ide resultados/investigacion_ide/20261019/metadatos.json
```

Conserva los 423 puntos y todas sus medidas, sin fusionar coordenadas compartidas
ni sumar capacidades. Las 423 relaciones municipales están contrastadas; el
informe de fase 7 distingue publicación, periodo mensual y corte desconocido.
La validación conjunta de fase 8 incorpora esta capa y verifica sus relaciones.

### Capa y contraste municipal de recarga

```powershell
.\.venv\Scripts\python.exe src/georreferenciar_recarga.py --metadatos-miteco resultados/investigacion_datum_miteco/20261016/catalogo.json
```

Requiere las tablas de recarga, la base territorial y la copia de metadatos
con su recibo conservados en la investigación del datum. Prepara GeoParquet
EPSG:25830 desde el CRS declarado EPSG:4258, conserva todas las instalaciones y
separa relaciones admitidas de discrepantes. El [informe espacial](docs/RECARGA_ESPACIAL_SILVER.md)
documenta reglas y controles. Resultados e informe quedan en
`resultados/silver/recarga_espacial/`, con `actual.json` después de validar.
No altera las tablas de fase 4 ni utiliza red o dependencias adicionales.

### Relaciones y validación conjunta de Silver

```powershell
.\.venv\Scripts\python.exe src/validar_silver.py --evidencias-recarga resultados/revision_recarga/20261018_revision_manual/decisiones.json
```

Verifica las 30 salidas vigentes de ocho bloques y sus informes/manifiestos,
comprueba integridad y periodos, conserva las decisiones documentales de recarga
y relaciona POI, aforos y tramos con los recintos, sin asignación exclusiva ni
reparto de indicadores. Las seis salidas e informe quedan en
`resultados/silver/validacion_conjunta/`; `actual.json` solo cambia después de
validar y cerrar la ejecución. El [informe de fase 8](docs/VALIDACION_CONJUNTA_SILVER.md)
explica los insumos de evidencia que se deben conservar, los lotes provinciales,
las incidencias y las 120 pruebas aprobadas. No requiere nuevas dependencias ni
vuelve a procesar el TXT nacional DGT.

La [revisión ampliada de recarga](docs/REVISION_RECARGA_SILVER.md) documenta las
80 asignaciones adicionales admitidas, sus fuentes y los 52 casos pendientes.
