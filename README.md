# TFM de Carlos Peñalver

**Localización de nuevos puntos de recarga para vehículos eléctricos en la
Comunitat Valenciana.** Trabajo de Fin de Máster del Máster de Ciencia de Datos
e IA, organizado mediante entregas.

El proyecto apoyará a administraciones y operadores en la decisión de dónde
estudiar nuevas instalaciones públicas. Se preparan demanda potencial municipal,
oferta registrada y candidatos cartográficos, conservando su incertidumbre.

**Estado a 13-11-2026:** preparación de datos completada hasta Gold. La Entrega 03
se replantea para segmentar conjuntamente demanda potencial y oferta registrada
de recarga. La entrega utiliza dos entradas: vehículos con Distintivo 0 y
puntos de recarga con municipio admitido. Baseline descriptivo ejecutado y
verificado sobre los 541 municipios incluidos, sin separación de datos, con
cuatro perfiles y cobertura completa. Comparación ML ejecutada: K-means y GMM,
de dos a seis grupos, con 160 ajustes y comprobación independiente. Se adopta
K-means con seis grupos como solución de trabajo provisional, pendiente de
comprobar la comprensión y utilidad de sus perfiles para el MVP.
El enfoque, el reparto 433/108 y los resultados anteriores se conservan como
históricos. La evaluación vigente es interna y de robustez; no acredita
generalización a municipios o periodos nuevos.
Todavía no hay un ranking de prioridad ni aplicación web.

## Entregas

- [Entrega 1: ideas de producto](docs/entregas/01_ideas_producto.md).
- [Entrega 2: datos y preparación](docs/entregas/02_datos_y_preparacion.md).
  Incluye fuentes y acceso, condiciones de uso, transformaciones, estructura
  final de datos y limitaciones.
- [Entrega 3: perfiles de demanda y oferta](docs/entregas/03_machine_learning_demanda_y_oferta.md).
  Redacción completa de los cinco apartados: enfoque descriptivo, baseline,
  comparación de K-means y GMM y exportación de imágenes con centros.
  El apartado 5 documenta la elección provisional de seis grupos, sus etiquetas
  de trabajo, la salida para el frontal y la comprobación de utilidad pendiente.
- [Entrega 3: versión anterior conservada](docs/entregas/03_machine_learning.md).
  Recoge la segmentación sin oferta en las entradas, sus experimentos y el
  piloto de contraste posterior con recarga.

## Código y datos

La preparación está en [src/datos_y_preparacion/](src/datos_y_preparacion/).
[flujo.py](src/datos_y_preparacion/flujo.py) muestra la secuencia Bronze →
Silver → Gold; los módulos separan las transformaciones y sus controles.
Silver se divide por fuente para evitar otro archivo excesivamente grande.

| Ruta | Responsabilidad |
| --- | --- |
| `src/datos_y_preparacion/bronze.py` | Originales, catálogo y comprobación de entradas. |
| `src/datos_y_preparacion/silver/` | Territorio, demografía, recarga, tráfico, OSM, capacidad e integración. |
| `src/datos_y_preparacion/gold.py` | Contexto municipal, candidatos, controles y variables. |
| `src/datos_y_preparacion/comunes.py` | SQL, integridad, conexión y exportación compartidos. |
| `src/datos_y_preparacion/historico/` | Preparaciones y auditorías anteriores; algunas funciones siguen reutilizándose. |
| `src/modelado/` | Preparación de experimentos, baseline, comparación, verificadores e imágenes. |
| `tests/` | Pruebas organizadas por preparación y modelado, incluidas en Git. |

El [mapa de estructura](docs/ESTRUCTURA.md) explica los puntos de entrada y
distingue los experimentos vigentes de sus antecedentes. La entrada
[preparar_dataset.py](src/preparar_dataset.py) conserva los comandos de la
Entrega 2 y delega en el flujo modular.

| Capa | Contenido |
| --- | --- |
| Bronze | Identificación y verificación de las copias originales. |
| Silver | 48 tablas de datos preparados, con claves, tipos, geometrías e incidencias. |
| Gold | 13 tablas de contexto municipal, oferta, candidatos, diagnósticos y variables normalizadas. |

Los originales y las salidas de datos están excluidos del repositorio. Los
enlaces de acceso están en la segunda entrega. Para repetir exactamente la
preparación se necesitan también las copias y evidencias documentales indicadas
en el bloque `ENTRADAS` del script; clonar el repositorio no las descarga.

## Reproducción

Con Python 3.12 instalado, desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import duckdb; c=duckdb.connect(config={'extension_directory':'.venv/duckdb_extensions'}); c.execute('INSTALL spatial'); c.close()"
.\.venv\Scripts\python.exe -m src.datos_y_preparacion --comprobar-entradas
.\.venv\Scripts\python.exe -m src.datos_y_preparacion
```

La instalación inicial requiere Internet. La preparación utiliza las copias
locales, sin modificar los originales. DuckDB trabaja con 1 GB de memoria de
su motor y dos hilos; el procesamiento requiere espacio temporal en disco.

Cada ejecución crea `resultados/entrega02/<ejecución>/`, con las tablas y sus
manifiestos. El manifiesto final se guarda al completar los controles e incluye
procedencia, huellas SHA-256 de las entradas y los módulos utilizados,
esquemas, claves y recuentos.

**Verificación:** antes de modularizar, el flujo reprodujo las 61 tablas
Silver/Gold con los mismos esquemas, valores y geometrías, excluyendo únicamente
el identificador de ejecución Gold. La reorganización conserva las funciones
de transformación y sus esquemas; no se ha repetido la preparación completa.
Para ejecutar las pruebas desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t .
```

Las copias originales, las salidas y las versiones antiguas de código asociadas
a sus huellas permanecen fuera de Git. Docker queda pendiente; todavía no hay
contenedor ni despliegue automatizado.

## Archivos de apoyo

- `config/catalogo_bronze.json`: procedencia e identificación de los originales.
- `requirements.txt`: versiones de las dependencias Python.
- `config/exclusiones_segmentacion.json`: exclusión documentada de la primera
  segmentación y su evaluación.

Una descarga actual puede diferir de las copias utilizadas. La preparación
conserva nulos, asignaciones pendientes y versiones de recarga por separado;
su validación técnica no demuestra suficiencia de oferta ni viabilidad de un
emplazamiento.
