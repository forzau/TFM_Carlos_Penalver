# Recarga MITECO versionada para la entrada de Gold

Fecha: **20-10-2026**. Estado: **preparada y validada con limitaciones**.
Se adopta la copia adquirida el 18-10-2026 como entrada principal de recarga
para la primera Gold. Se conservan la Silver histórica y sus referencias de
ejecución, la copia original y todas las evidencias. Esta entrada se consume
después en la [primera Gold municipal](GOLD_MUNICIPAL.md).

## Versión seleccionada y procedencia

La [comparación completa](COMPARACION_RECARGA_MITECO.md) identifica la copia,
las diferencias y los límites de interpretación. La exportación conservada
en `resultados/revision_recarga/20261018_ampliacion/miteco_exportacion_actual.csv`
tiene 44.122.108 bytes y SHA-256
`cbea60310fff28d2eb6f3969e1dfff0f2ac371de28f9747ecc7b9f6d46b9df35`.
Su recibo acredita adquisición **18-10-2026, 18:38:01.029767 UTC**, mediante
POST con `soloConsolidado=true`. No se descarga de nuevo ni se sustituye el
catálogo o el manifiesto Bronze original: la instantánea y su recibo son
entradas preservadas explícitamente en el informe de esta preparación.

No se conoce la fecha común de operación de sus elementos ni la causa de las
nueve ausencias. Los parámetros de adquisición originales siguen desconocidos;
no se atribuyen todas las diferencias al paso del tiempo.

## Salidas

Ejecución: **`20261020T150602650091Z`**, bajo
`resultados/silver/recarga_versionada/`. Su `actual.json` apunta a la ejecución
validada, con doce Parquet/GeoParquet y un informe. No cambia ningún indicador
de ejecución de los nueve bloques históricos.

| Tabla | Filas | Función |
| --- | ---: | --- |
| `recarga_instalaciones` | 1.517 | Atributos tabulares de instalaciones presentes. |
| `recarga_puntos` | 4.359 | Puntos presentes con clave instalación/punto. |
| `recarga_conectores` | 5.202 | Conectores presentes, valores tipados y textos originales. |
| `incidencias` | 0 | Incidencias de conversión tabular. |
| `recarga_instalaciones_geo` | 1.517 | Capa EPSG:25830 y contraste municipal básico. |
| `recarga_municipios_candidatos` | 1.517 | Intersecciones territoriales, sin asignación forzada. |
| `entidad_municipio` | 1.385 | Relaciones admitidas por intersección única y nombre oficial. |
| `incidencias_espaciales` | 132 | Discrepancias del contraste básico, antes de la revisión documental. |
| `revision_recarga` | 132 | 81 casos resueltos documentalmente y 51 pendientes. |
| `recarga_municipio_validado` | 1.466 | Relación admitida final para la copia principal. Es la que consumirá Gold. |
| `recarga_ausentes` | 9 | Instalaciones solo históricas, geometría, recuentos y admisión anterior. |
| `recarga_ausentes_municipios_candidatos` | 9 | Vínculos espaciales históricos de las ausencias. |

`recarga_instalaciones_geo.admitida_asignacion_municipal` y `entidad_municipio`
mantienen el significado del contraste básico. Las 81 resoluciones se añaden
en `recarga_municipio_validado`; no se reescribe el contraste para ocultar las
discrepancias. Las 132 filas de incidencia básica no son 132 pendientes finales.

| Entidad presente | Total | Municipio admitido | Asignación pendiente |
| --- | ---: | ---: | ---: |
| Instalaciones | 1.517 | 1.466 | 51 |
| Puntos | 4.359 | 4.194 | 165 |
| Conectores | 5.202 | 5.017 | 185 |

Los nueve IDs ausentes reúnen 43 puntos y 43 conectores históricos: ocho tenían
municipio admitido y Exoil Pista de Silla seguía pendiente. Se guardan con
`estado_presencia = 'ausente_exportacion_sin_cierre_acreditado'`. No entran en
los totales presentes ni se presentan como cierres. Los 52 pendientes de la
Silver histórica siguen conservados; la ausencia de un ID no resuelve su caso.

## Comprobaciones realizadas

- Lector y validaciones tabulares existentes: 42.772 filas nacionales, 5.202
  conectores de CV, claves completas y únicas, relaciones padre/hijo y cero
  incidencias de conversión. Textos y variantes se conservan.
- Igualdad exacta de todos los atributos tabulares de las instalaciones con
  la capa histórica, incluidas coordenadas. Un cambio o un ID desconocido
  detendría esta ruta de reutilización, sin corregir por cercanía.
- Geometrías históricas conservadas en EPSG:25830, válidas y finitas. Se
  recalculan sus intersecciones con los recintos verificados y se comprueba
  igualdad con las relaciones anteriores. También se comprueba la vuelta de
  proyección mediante la validación espacial existente.
- No se atribuye una nueva declaración de datum al exportador: la reutilización
  procede de coordenadas idénticas y geometrías históricas verificadas, cuya
  declaración original era EPSG:4258. La procedencia se registra en el informe.
- Las 83 decisiones conservadas se vuelven a contrastar con sus copias, recibos,
  atributos y relaciones espaciales: 81 admisiones y dos revisiones no concluyentes.
  No se realiza nueva investigación externa ni se admite otro caso pendiente.
- Las 1.466 relaciones admitidas coinciden exactamente con el subconjunto
  compatible de las admisiones anteriores, incluidos métodos y referencias.
- Reapertura de los doce archivos: esquemas, valores, claves, recuentos y CRS
  GeoParquet comprobados. Huellas de las 175 entradas distintas y doce salidas
  verificadas; las entradas se comprueban de nuevo antes de publicar el indicador.
- Suite completa: **129 pruebas aprobadas, sin omisiones**. Incluye cinco nuevas
  sobre identidad/coordenadas, relaciones territoriales, conservación de ausencias
  y exportación sin sobrescritura. Sin nuevas dependencias.

La comprobación documental valida la evidencia conservada y su aplicabilidad;
no certifica funcionamiento actual, exhaustividad o exactitud de cada plaza.

## Reproducción

```powershell
.venv\Scripts\python.exe src/preparar_recarga_versionada.py --comparacion resultados/comparacion_recarga/20261020T143417939020Z/informe.json --evidencias-recarga resultados/revision_recarga/20261018_revision_manual/decisiones.json
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Requiere las entradas referenciadas y `spatial` instalada según README.
Funciona sin red, sin procesar el TXT DGT y con memoria del motor limitada a
1 GB y dos hilos. Cada ejecución escribe en una carpeta nueva. Una comprobación
fallida no sustituye el indicador de la última ejecución válida.

El informe identifica las copias, recibos, ejecución histórica, código, reglas,
entorno y huellas. Los archivos pesados y evidencias continúan fuera de Git.
La preparación no cambia el alcance del producto: asignación municipal no
equivale a suficiencia de oferta ni a operación acreditada.

Las tres tablas del [contrato inicial Gold](CONTRATO_GOLD.md) ya se han
materializado usando esta entrada, conservando las ausencias y los pendientes
como incertidumbres distintas. Su [informe de ejecución](GOLD_MUNICIPAL.md)
documenta resultados y siguiente etapa.
