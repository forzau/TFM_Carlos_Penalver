# TFM de Carlos Peñalver

Trabajo de Fin de Máster del Máster de Ciencia de Datos e IA.
El trabajo se organiza mediante entregas y no incluye una memoria.
Repositorio: [forzau/TFM_Carlos_Penalver](https://github.com/forzau/TFM_Carlos_Penalver).

Tema elegido: **localización óptima de nuevos puntos de recarga para vehículos
eléctricos en la Comunitat Valenciana**. El objetivo es apoyar decisiones sobre
dónde ampliar la infraestructura pública de recarga utilizando datos reales y públicos.

La auditoría técnica de las copias locales se documenta en
[Auditoría de fuentes](docs/AUDITORIA_FUENTES.md). La granularidad y la integración
se definirán después de resolver sus hallazgos.

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

[Fuentes de datos](docs/FUENTES.md).

[Catálogo de Bronze](docs/CATALOGO_BRONZE.md): once recursos de nueve bloques,
incluidas las referencias territoriales oficiales, con un manifiesto local de
integridad para 39 archivos de datos y documentación.

[Plan de trabajo de Silver](docs/PLAN_SILVER.md): ocho fases con salidas y
condiciones de cierre. Las fases 1 y 2 están cerradas: convenciones aceptadas, un
[diccionario de campos y claves](docs/DICCIONARIO_SILVER.md) y la
[configuración técnica comprobada](docs/CONFIGURACION_SILVER.md).
La [base territorial Silver](docs/BASE_TERRITORIAL_SILVER.md) contiene los 542
municipios y sus recintos verificados. Las restantes fuentes aún no se han transformado.

## Reproducción

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
El siguiente bloque es la fase 3 de Silver: parque DGT, población y renta.
