# Estructura y ejecución del proyecto

El código se organiza por responsabilidad. La preparación completa tiene un
único punto de entrada que llama a módulos pequeños; los experimentos y sus
verificadores se mantienen separados de las transformaciones de datos.

```text
config/                              Catálogo y exclusiones documentadas
docs/entregas/                       Documentos académicos
src/
  rutas.py                           Raíz común y versiones de productores
  exportar_resultados.py              Selección de informes y figuras para Git
  preparar_dataset.py                Entrada compatible con la Entrega 2
  datos_y_preparacion/
    __main__.py                      Entrada: python -m src.datos_y_preparacion
    flujo.py                         Orden de etapas y manifiesto final
    comunes.py                       SQL, huellas, conexión y exportación
    bronze.py                        Catálogo, originales y evidencias
    silver/
      territorio.py                  Referencia INE y recintos IGN
      demografia.py                  Población, renta y parque DGT
      recarga.py                     Instalaciones, puntos y conectores
      trafico.py                     Aforos y red viaria
      osm.py                         Puntos, áreas y correspondencias
      capacidad.py                   Capacidad i-DE y sus metadatos
      integracion.py                 Relaciones y versiones de recarga
    gold.py                          Contexto, candidatos, controles y variables
    historico/                       Implementaciones y auditorías anteriores
  modelado/                          Experimentos, verificadores e imágenes
tests/
  datos_y_preparacion/
    test_flujo.py                    Controles de los módulos del flujo completo
    historico/                       Pruebas de preparaciones y auditorías previas
  modelado/                          Pruebas de experimentos e imágenes
  test_trazabilidad.py                Comprobación de versiones de productores
  test_exportar_resultados.py         Selección visible y conservación ante errores
resultados/
  README.md                          Índice de resultados vigentes y salidas locales
  informes/                          Esquemas, métricas y figuras incluidos en Git
  apoyo/                             Auditorías, diseños, exploraciones y registros locales
```

## Preparación

Desde la raíz y con las dependencias de `requirements.txt` instaladas:

```console
python -m src.datos_y_preparacion --help
python -m src.datos_y_preparacion --comprobar-entradas
python -m src.datos_y_preparacion
```

La instalación del entorno y de la extensión `spatial` se describe en
[README](../README.md). `--comprobar-entradas` verifica las copias y las
evidencias locales; no las descarga. La ejecución completa genera una carpeta
nueva en `resultados/entrega02/`, sin sustituir resultados previos.

Bronze comprueba la identidad de los originales. Silver conserva entidades,
periodos, geometrías e incidencias, y se divide por fuente porque reúne la mayor
parte del código. Gold reúne las tablas finales. Cada módulo contiene también
los controles propios de sus transformaciones. `comunes.py` concentra solo las
operaciones compartidas; `flujo.py` mantiene visible el recorrido completo.

Se conserva `python src/preparar_dataset.py` como entrada compatible con la
Entrega 2. La implementación ya no está en ese archivo. Para los demás módulos
se utiliza `python -m` desde la raíz, sin modificar manualmente la ruta de Python
ni instalar el proyecto como paquete.

## Modelado

Los experimentos tienen protocolos diferentes. Conservar sus nombres evita
confundir sus resultados o ejecutar un diseño anterior por error.

| Estado | Módulos de `src/modelado/` |
| --- | --- |
| Baseline vigente, descriptivo sin separación | `ejecutar_baseline_descriptivo`, `verificar_baseline_descriptivo` |
| Comparación vigente de K-means y GMM | `ejecutar_comparacion_descriptiva`, `verificar_comparacion_descriptiva` |
| Imágenes desde resultados guardados | `exportar_clusters_descriptivos` |
| Nueva comparación seguida de imágenes | `ejecutar_comparacion_con_imagenes` |
| Antecedentes con separación y funciones reutilizadas | `preparar_particiones_segmentacion`, `preparar_experimento_segmentacion`, `ejecutar_baseline_segmentacion`, `ejecutar_comparacion_segmentacion`, `verificar_comparacion_segmentacion`, `comprobar_utilidad_segmentacion`, `ejecutar_baseline_demanda_oferta`, `verificar_baseline_demanda_oferta` |

Por ejemplo, para exportar imágenes de una comparación existente:

```console
python -m src.modelado.exportar_clusters_descriptivos resultados/modelado/comparacion_descriptiva/<ejecucion>
```

Para verificar sus resultados sin repetir ajustes:

```console
python -m src.modelado.verificar_comparacion_descriptiva resultados/modelado/comparacion_descriptiva/<ejecucion>
```

El verificador escribe su informe en esa carpeta. Los productores vigentes
siguen usando las versiones concretas de Gold, bloques y baseline declaradas
en sus módulos. La reorganización no cambia esas entradas, el protocolo, los
modelos elegidos ni las métricas. Varias funciones reutilizadas proceden de los
módulos anteriores; conservarlas evita duplicar implementaciones.

## Pruebas y trazabilidad

```console
python -m unittest discover -s tests -t .
python -m unittest tests.datos_y_preparacion.test_flujo
python -m unittest discover -s tests/modelado -t .
```

Las pruebas están incluidas en Git y utilizan datos sintéticos y carpetas
temporales. Las pruebas espaciales necesitan la extensión `spatial` instalada.
El primer comando descubre también las subcarpetas y comprueba los antecedentes.

Los manifiestos nuevos de preparación registran todos los módulos del flujo.
Los manifiestos antiguos conservan las rutas y huellas de sus productores; no
se reescriben para atribuirles el código reorganizado. Sus originales se guardan
por SHA-256 en `resultados/codigo_historico/<sha256>.py`, fuera de Git. Al
verificar código de un manifiesto, `src/rutas.py` permite localizar esa versión
y el verificador exige su huella original. Esta búsqueda solo se aplica a
archivos Python de `src/`; los datos siguen exigiendo su archivo original.

La selección visible de [resultados](../resultados/README.md) incluye los
esquemas y recuentos de preparación, las métricas agregadas, los informes de
verificación y las diez figuras actuales. Se regenera mediante
`python -m src.exportar_resultados`. Solo esas salidas están incluidas en Git;
las bases, modelos y evidencias completas permanecen locales.

Las auditorías, diseños, exploraciones y copias de mantenimiento se agrupan en
`resultados/apoyo/`. Se mantienen las rutas de las ejecuciones, evidencias y
entradas utilizadas por los productores para conservar sus referencias.

Para verificar esas ejecuciones en otro equipo hacen falta también las copias
de código histórico, además de los datos, modelos y manifiestos. Un clon de Git
contiene el código reorganizado y las pruebas, pero no esos artefactos locales.

## Base para MLOps y Docker

La estructura aporta puntos de entrada reproducibles, dependencias fijadas,
pruebas visibles, separación entre preparación y modelado, y resultados
versionados con huellas. Las rutas se calculan desde la ubicación del proyecto,
sin rutas personales de un ordenador.

Docker se incorporará cuando se concrete esa fase. Será necesario instalar
Python, las dependencias y la extensión espacial para el sistema del contenedor,
y proporcionar originales y evidencias como entradas, con salidas persistentes
fuera de la imagen. Todavía no se añaden `Dockerfile`, servicios, orquestadores
ni plataformas de seguimiento de experimentos.

Las entregas existentes se conservan como documentos académicos de cada fase.
Este mapa recoge las rutas actuales del código tras su reorganización.
