# TFM de Carlos Peñalver

**Localización de nuevos puntos de recarga para vehículos eléctricos en la
Comunitat Valenciana.** Trabajo de Fin de Máster del Máster de Ciencia de Datos
e IA, organizado mediante entregas.

El proyecto apoyará a administraciones y operadores en la decisión de dónde
estudiar nuevas instalaciones públicas. Se preparan demanda potencial municipal,
oferta registrada y candidatos cartográficos, conservando su incertidumbre.

**Estado a 07-11-2026:** preparación de datos completada hasta Gold, baseline
por medianas cerrado y comparación de tres métodos de clustering ejecutada
con k de 2 a 10. Se trabaja con 541 municipios, 433 de desarrollo y 108
reservados para prueba final. GMM con dos grupos y K-means con tres destacan
como candidatos para interpretar; selección y evaluación final pendientes.
Todavía no hay un ranking de prioridad ni aplicación web.

## Entregas

- [Entrega 1: ideas de producto](docs/entregas/01_ideas_producto.md).
- [Entrega 2: datos y preparación](docs/entregas/02_datos_y_preparacion.md).
  Incluye fuentes y acceso, condiciones de uso, transformaciones, estructura
  final de datos y limitaciones.
- [Entrega 3: Machine Learning](docs/entregas/03_machine_learning.md).
  Incluye entradas, tratamiento de rentas, separación espacial, protocolo y
  resultados del baseline y comparación ML; la selección final sigue pendiente.

## Código y datos

[preparar_dataset.py](src/preparar_dataset.py) contiene el flujo completo
Bronze → Silver → Gold en un único archivo. `main()` muestra la secuencia y
las secciones por fuente reúnen las transformaciones y sus controles.

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
.\.venv\Scripts\python.exe src/preparar_dataset.py --comprobar-entradas
.\.venv\Scripts\python.exe src/preparar_dataset.py
```

La instalación inicial requiere Internet. La preparación utiliza las copias
locales, sin modificar los originales. DuckDB trabaja con 1 GB de memoria de
su motor y dos hilos; el procesamiento requiere espacio temporal en disco.

Cada ejecución crea `resultados/entrega02/<ejecución>/`, con las tablas y sus
manifiestos. El manifiesto final se guarda al completar los controles e incluye
procedencia, huellas SHA-256, esquemas, claves y recuentos.

**Verificación:** el script reproduce las 61 tablas Silver/Gold de la preparación
anterior con los mismos esquemas, valores y geometrías, excluyendo únicamente
el identificador de ejecución Gold. La validación acumulada pasa 213 pruebas.

## Archivos de apoyo

- `config/catalogo_bronze.json`: procedencia e identificación de los originales.
- `requirements.txt`: versiones de las dependencias Python.
- `config/exclusiones_segmentacion.json`: exclusión documentada de la primera
  segmentación y su evaluación.

Una descarga actual puede diferir de las copias utilizadas. La preparación
conserva nulos, asignaciones pendientes y versiones de recarga por separado;
su validación técnica no demuestra suficiencia de oferta ni viabilidad de un
emplazamiento.
