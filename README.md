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
| `src/` | Código del proyecto, cuando se defina la solución. |
| `notebooks/` | Cuadernos de exploración, si se utilizan. |
| `resultados/` | Salidas generadas; los archivos pesados no se versionan. |
| `Fuentes/` | Datos originales locales, excluidos del repositorio por su volumen. |

## Documentación

[Entrega 1: propuesta inicial de ideas de producto](docs/entregas/01_ideas_producto.md).
Recoge las tres propuestas iniciales; posteriormente se ha seleccionado la
planificación de infraestructura de recarga.

[Fuentes de datos](docs/FUENTES.md).

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
