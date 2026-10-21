# Primera etapa Gold: contexto municipal

Fecha: **20-10-2026**. Estado: **materializada y validada con limitaciones**.
Implementa las tres tablas del [contrato inicial Gold](CONTRATO_GOLD.md).
No constituye todavía la priorización de zonas, el conjunto de candidatos o
una evaluación de suficiencia operativa de la oferta.

## Ejecución y entradas

Ejecución vigente: **`20261020T153200478279Z`**, bajo
`resultados/gold/contexto_municipal/`. Su `actual.json` referencia los archivos
`manifiesto.json` e `informe.json` de esa ejecución. Las tablas están en archivos
Parquet/GeoParquet; no se requiere una base de datos con servidor.

| Bloque de entrada | Ejecución Silver | Selección |
| --- | --- | --- |
| Base territorial | `20261015T164603584512Z` | Los 542 municipios y sus recintos EPSG:25830. |
| Demografía y parque | `20261016T105307373142Z` | Parque 31-12-2025, población Total 2025 y renta neta media por persona municipal 2023. |
| Recarga versionada | `20261020T150602650091Z` | Copia adquirida el 18-10, admisiones revalidadas y ausencias históricas separadas. |

Los periodos se conservan por variable. La adquisición de recarga no se presenta
como fecha de funcionamiento de cada instalación. La consulta de recintos de
2026 tampoco acredita una edición histórica de los límites de 2025.

## Tablas materializadas

| Tabla | Filas | Columnas | Contenido |
| --- | ---: | ---: | --- |
| `gold_municipios` | 542 | 24 | Contexto, proporción Distintivo 0, oferta con municipio admitido, presión descriptiva y avisos. |
| `gold_recarga_instalaciones` | 1.526 | 14 | 1.517 IDs presentes y nueve ausentes históricos, con presencia y admisión diferenciadas. |
| `gold_incertidumbre_recarga_municipio` | 112 | 7 | Vínculos diagnósticos por instalación, municipio y tipo de incertidumbre. |

Los campos, tipos, nulabilidad y fórmulas coinciden en nombre y orden con el
contrato. `version_gold` identifica la ejecución y participa en las claves
compuestas. El manifiesto incluye los tres esquemas y huellas de salida.

### Contexto y oferta municipal

- Se conservan los **542 municipios**. Parque municipal: 4.124.317 vehículos,
  de los que 78.180 tienen Distintivo 0, como aproximación acordada de demanda.
  No se utiliza ni se vuelve a procesar el TXT nacional DGT.
- Población selecciona únicamente Total de 2025. Renta selecciona municipio,
  indicador exacto y 2023; permanecen **ocho nulos**, con `estado_renta='no_informado'`.
  No se sustituyen por cero, por un año anterior o por medias de otros niveles.
- La oferta principal suma **1.466 instalaciones, 4.194 puntos y 5.017 conectores**
  con municipio admitido. Se agregan las entidades por separado, sin multiplicar
  puntos al unirlos con sus conectores.
- En **285 municipios** no hay puntos con asignación admitida en esta copia.
  Su presión queda nula con `estado_presion_descriptiva='sin_puntos_admitidos'`.
  No es un diagnóstico de ausencia física o prioridad máxima automática.
- En los otros 257 municipios se calcula Distintivo 0/puntos admitidos como
  descripción, acompañada de los avisos que correspondan. No mide sesiones,
  ocupación, rentabilidad ni suficiencia operativa.

### Presencia, histórico e incertidumbre

La tabla por instalación conserva 1.466 admisiones presentes, 51 pendientes
presentes, ocho admisiones solo históricas y una pendiente solo histórica.
Las nueve ausencias no entran en la oferta principal ni significan cierres.

| Tipo de incertidumbre | Instalaciones distintas | Vínculos municipales | Municipios relacionados |
| --- | ---: | ---: | ---: |
| Asignación pendiente de instalaciones presentes | 51 | 102 | 55 |
| Ausencia entre exportaciones | 9 | 10 | 10 |

En conjunto hay **63 municipios** relacionados con algún aviso; los grupos se
solapan. Ni los vínculos ni los recuentos de incertidumbre se suman entre
municipios para contar instalaciones de toda la comunidad. Los 60 IDs con aviso
tienen al menos un vínculo reconocido: no hay incertidumbre sin localizar en
esta ejecución. No se asignan puntos a los municipios potencialmente afectados.

En una ausencia con admisión histórica, el aviso se localiza en ese municipio.
Si no existe admisión, se conservan el declarado reconocido y los candidatos
espaciales. Cuando un vínculo tiene varios papeles, sus banderas se reúnen en
una fila. No se inventan radios ni se fuerza un candidato por proximidad.

## Verificación y trazabilidad

- Huellas, estados preparados, referencias coherentes de ejecución y recuentos
  de las entradas comprobados; se rechazan referencias fuera del bloque o a
  un informe de otra ejecución. Las
  selecciones de parque/población/renta son únicas y cubren los mismos códigos;
  una observación faltante o duplicada detendría la preparación.
- Claves, campos obligatorios, referencias, estados de presencia/admisión,
  conservación de observaciones y separación del histórico validados.
- Cocientes y estados recalculados como control; denominador cero da nulo,
  nunca infinito. Recuentos municipales reconciliados de forma independiente
  con las claves de las entidades Silver y sus admisiones.
- Tres salidas reabiertas con igualdad de esquema y valores, incluidas geometrías
  y nulos. CRS GeoParquet EPSG:25830 conservado.
- **196 archivos de entrada y código** registrados y verificados de nuevo antes
  de publicar la referencia de ejecución. Manifiesto con periodos, reglas,
  unidades, fuentes, versiones Silver y entorno; informe de controles separado.
- Suite completa: **140 pruebas aprobadas, sin omisiones**. Once nuevas cubren
  agregación sin duplicaciones, separación histórica, nulos, denominadores cero,
  selección temporal/territorial, unicidad, huérfanos, avisos, referencias de
  ejecución y exportación segura.

Se reutiliza el exportador comprobado de la preparación versionada, añadiendo
el mapa de tablas como argumento. Su llamada anterior y su comportamiento por
defecto se mantienen y están cubiertos por la suite. Los datos y los indicadores
de ejecución Silver no cambian al materializar Gold.

## Reproducción

Con las entradas Silver y sus evidencias conservadas, y `spatial` disponible:

```powershell
.venv\Scripts\python.exe src/preparar_gold_municipal.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Sin red, sin dependencias nuevas, memoria del motor de 1 GB y dos hilos. Cada
ejecución se escribe en una carpeta nueva; una comprobación fallida no sustituye
la referencia de la última válida. Fuentes, Bronze y Silver se conservan.
Los datos y manifiestos permanecen fuera de Git.

## Siguiente etapa

Se han revisado la utilidad y los límites de estos indicadores y se ha definido
el [contrato de candidatos y proximidad](CONTRATO_CANDIDATOS_GOLD.md), con
preselección de destino, correspondencias sin fusión, representación espacial
y tres escenarios de oferta. Sus [cuatro tablas ya están materializadas](CANDIDATOS_GOLD.md).
La [revisión de ejemplos territoriales y sensibilidad](REVISION_EJEMPLOS_GOLD.md)
propuso controles de áreas con recarga, solapamientos e influencia exterior,
[ya materializados](CONTROLES_ESPACIALES_GOLD.md). Siguiente: definir la comparación
de zonas. Esta tabla municipal no se modifica.
Pesos, priorización, optimización y aplicación siguen pendientes;
los cocientes actuales no sustituyen ese trabajo.
