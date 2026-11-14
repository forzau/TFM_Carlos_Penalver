# Resultados del proyecto

La carpeta `informes/` contiene la selección incluida en Git: esquemas,
recuentos, métricas agregadas y figuras de las ejecuciones vigentes. Permite
revisar los resultados sin descargar las bases completas ni ejecutar los modelos.

## Preparación de datos

Ejecución `20261022T150925140929Z`: 48 tablas Silver y 13 Gold.

- [Inventario de tablas](informes/preparacion/resumen_tablas.csv): capa,
  bloque, filas, número de columnas y claves.
- [Esquemas y claves](informes/preparacion/esquemas.json).
- [Estado, entorno y limitaciones](informes/preparacion/resumen.json).

Los informes describen las tablas preparadas; no incluyen sus registros,
coordenadas ni geometrías. Las tablas completas permanecen en las carpetas
locales de datos.

## Segmentación descriptiva vigente

El [informe de resultados de la Entrega 3](informes/modelado/RESULTADOS.md) reúne
las métricas de las once soluciones, la comparación con el baseline, la elección
provisional de K-means k6 y el análisis de los casos fronterizos y limitaciones.
Es el punto de lectura principal, junto con la
[entrega académica](../docs/entregas/03_machine_learning.md).

Las evidencias descargables se conservan por su función:

| Archivos | Función |
| --- | --- |
| [Comparación](informes/modelado/comparacion.csv) | Valores numéricos completos de las diez configuraciones ML. |
| Perfiles del [baseline](informes/modelado/perfiles_baseline.csv) y [modelos](informes/modelado/perfiles_modelos.csv) | Tamaños, medianas y avisos por grupo. |
| [Protocolo](informes/modelado/protocolo.json) | Diseño y parámetros del experimento. |
| [Resumen de datos](informes/modelado/resumen.json) | Métricas del baseline, decisión posterior y límites en formato reutilizable. |
| Verificaciones del [baseline](informes/modelado/verificacion_baseline.json) y [ML](informes/modelado/verificacion_comparacion.json) | Comprobaciones numéricas independientes. |

La síntesis interpreta estas evidencias; no sustituye sus valores completos ni
reescribe los manifiestos originales. Las métricas describen 541 municipios y
miden geometría interna y robustez, sin acreditar generalización o necesidad real.

### Figuras con centros

Copias exactas de la exportación `20261111T170051625718Z`, realizada a partir de
asignaciones y modelos guardados. No se han repetido los ajustes. Las dos vistas
muestran recuentos originales y la representación utilizada por el modelo.

| Grupos | K-means | GMM |
| --- | --- | --- |
| 2 | [Figura](informes/modelado/imagenes/kmeans_k2.png) | [Figura](informes/modelado/imagenes/gmm_k2.png) |
| 3 | [Figura](informes/modelado/imagenes/kmeans_k3.png) | [Figura](informes/modelado/imagenes/gmm_k3.png) |
| 4 | [Figura](informes/modelado/imagenes/kmeans_k4.png) | [Figura](informes/modelado/imagenes/gmm_k4.png) |
| 5 | [Figura](informes/modelado/imagenes/kmeans_k5.png) | [Figura](informes/modelado/imagenes/gmm_k5.png) |
| 6 | [Figura](informes/modelado/imagenes/kmeans_k6.png) | [Figura](informes/modelado/imagenes/gmm_k6.png) |

Los números y colores son propios de cada configuración. Los centros de GMM
son medias de componentes; la transformación inversa de un centro no equivale
a la media aritmética de los recuentos de sus miembros.

**Fuentes de las figuras y métricas:** DGT, datos municipales de 2025, y MITECO,
registro de recarga pública, copia adquirida el 18-10-2026. Elaboración propia.
Acceso, versiones, atribuciones y transformaciones documentados en el
[catálogo de fuentes](../config/catalogo_bronze.json) y la
[Entrega 2](../docs/entregas/02_datos_y_preparacion.md).

## Organización de las salidas locales

Las siguientes carpetas conservan sus rutas porque las utilizan los productores
o aparecen en manifiestos de ejecuciones anteriores:

| Ruta | Contenido local |
| --- | --- |
| `bronze/`, `silver/`, `gold/` | Manifiestos y preparaciones por etapa. |
| `entrega02/` | Ejecuciones completas del flujo de preparación. |
| `modelado/` | Experimentos vigentes y antecedentes, con sus modelos y asignaciones. |
| `revision_recarga/` | Evidencias y decisiones utilizadas en la preparación. |
| `investigacion_datum_miteco/`, `investigacion_ide/` | Acreditación de metadatos utilizada por el flujo. |
| `diseno_particiones/` | Recuentos utilizados para definir bloques espaciales conservados. |
| `codigo_historico/` | Versiones exactas de productores anteriores, identificadas por huella. |

El material auxiliar se agrupa en `apoyo/`: `auditorias/`, `diseno/`,
`investigacion/`, `preparacion/`, `mantenimiento/` y `registros/`. Se conserva
localmente, sin incorporar a Git las descargas, bases de trabajo, registros
de ejecución o copias de mantenimiento.

## Reproducir la selección visible

Desde la raíz del proyecto:

```console
python -m src.exportar_resultados
```

El exportador usa una lista cerrada de archivos y extrae únicamente los campos
de los resúmenes. No copia bases completas, asignaciones municipales ni modelos.
Necesita las ejecuciones locales identificadas más arriba.

[procedencia.json](informes/procedencia.json) registra las rutas relativas y
huellas SHA-256 de los insumos y los informes, además de la versión del exportador.
Los CSV de métricas y las figuras son copias exactas; los esquemas, el protocolo
resumido y los resúmenes JSON se extraen de los manifiestos y resultados guardados.
La selección provisional se registra como decisión posterior explícita.
`informes/modelado/RESULTADOS.md` es una síntesis revisada manualmente, enlazada
a esas evidencias; no la regenera el exportador ni forma parte de sus salidas
enumeradas en `procedencia.json`.
