# Comparación de las copias de recarga MITECO

Fecha: **20-10-2026**. Comparación finalizada. La recomendación se adopta después
en la [preparación versionada](RECARGA_VERSIONADA_SILVER.md), sin sustituir
Bronze ni las ejecuciones Silver históricas.

La exportación adquirida el 18 de octubre permite identificar una copia fechada.
En Comunitat Valenciana conserva 1.517 instalaciones con los mismos atributos
de instalación y punto de la copia anterior. Faltan nueve IDs que reunían 43
puntos y 43 conectores; se incorpora un conector en un punto ya existente.
**Estas diferencias del registro no acreditan cierres, aperturas o una caída
real de la oferta.**

## Copias y alcance

| Característica | Original utilizada por Silver | Adquirida el 18-10-2026 |
| --- | --- | --- |
| Archivo conservado | `Fuentes/instalaciones_actuales.csv` | `resultados/revision_recarga/20261018_ampliacion/miteco_exportacion_actual.csv` |
| Bytes | 45.116.072 | 44.122.108 |
| SHA-256 | `e1f01a774262e05ffbd012664f068bb4aff951ad443c7916f3a27da1af7090ac` | `cbea60310fff28d2eb6f3969e1dfff0f2ac371de28f9747ecc7b9f6d46b9df35` |
| Adquisición acreditada | Desconocida | 18-10-2026, 18:38:01 UTC, según recibo conservado |
| Solicitud de exportación | Parámetros originales desconocidos | POST `GenerarExcel`, cuerpo `soloConsolidado=true` |
| Nombre declarado por el servidor | No conservado | `InstalacionesPublicas_20261018_203735.csv` |
| Filas nacionales | 43.610 | 42.772 |
| Claves de conector repetidas a escala nacional | 2, fuera de CV | 0 |
| Última modificación máxima de conectores de CV | 12-08-2026, 13:17:48 | 15-10-2026, 10:12:21 |

Las fechas de modificación carecen de zona horaria y no son la fecha de corte
del inventario ni la de instalación. La máxima nacional del original documentada
en Bronze, 09-09-2026, tiene otro ámbito y no contradice la máxima de CV anterior.
El recibo acredita adquisición y respuesta del servidor; no operación de cada
cargador ese día. Al desconocer la solicitud original, tampoco se demuestra que
ambas extracciones tengan exactamente el mismo criterio de consolidación.

Se comprueban las huellas completas de ambas copias contra el informe Silver
original y el recibo de adquisición posterior. Se reutiliza el lector MITECO
de Silver, que exige los mismos 27 campos y conserva comillas interiores,
separadores y saltos de línea. La comparación es literal, por claves compuestas,
sin fusionar entidades ni aplicar correspondencias por semejanza.

## Diferencias de entidades en Comunitat Valenciana

| Entidad | Original | Adquirida 18-10 | Comunes | Solo original | Solo adquirida 18-10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Instalaciones | 1.526 | 1.517 | 1.517 | 9 | 0 |
| Puntos, clave instalación/punto | 4.402 | 4.359 | 4.359 | 43 | 0 |
| Conectores, clave instalación/punto/conector | 5.244 | 5.202 | 5.201 | 43 | 1 |

No cambian nombre, dirección, municipio declarado, operador, coordenadas ni
otros atributos de instalación de las 1.517 instalaciones comunes. Tampoco
cambian los atributos de punto de los 4.359 puntos comunes.

De los 5.201 conectores comunes, 5.195 coinciden en los 27 campos. Los otros
seis se distribuyen entre tres instalaciones:

- `2024004165`: dos textos de horario con distinto orden de los mismos días;
  uno también reordena los mismos métodos de pago.
- `2025000378`: dos textos reordenan los mismos servicios y actualizan la fecha
  de modificación de 15-09-2025 a 15-10-2026. En ese mismo punto aparece el
  conector `1` de 22 kW, además de los conectores `2` y `3` ya presentes.
- `2025000390`: dos textos reordenan los mismos servicios.

No cambian potencia, voltaje, intensidad, tipo de carga, formato ni tipo de
conector de las claves comunes. Se ha revisado el contenido de los seis cambios;
la igualdad de conjuntos de servicios/pagos o franjas horarias no se confunde
con igualdad literal de cadenas. El conector nuevo es una incorporación al
registro, sin fecha de instalación acreditada ni nuevo punto independiente.

No hay claves vacías o repetidas en CV, contradicciones de atributos de
instalación/punto, errores de conversión de potencia/fecha ni coordenadas fuera
del rango geográfico en ninguna copia. Estos controles no certifican precisión
de la ubicación, funcionamiento ni exhaustividad.

## Los nueve IDs ausentes

| ID original | Nombre original | Municipio de la relación admitida anterior | Puntos / conectores |
| --- | --- | --- | ---: |
| `2024003909` | Hotel Ignacio | Chiva | 6 / 6 |
| `2024004024` | E.S. Exoil Pista de Silla | Pendiente; Alfafar declarado y Sedaví como candidato espacial | 6 / 6 |
| `2024004039` | Rest. Río Verde | Massalavés | 4 / 4 |
| `2024004051` | E.S. Exoil Manises | Manises | 7 / 7 |
| `2024004158` | E.S. Cirugeda Xàtiva | Xàtiva | 4 / 4 |
| `2024004182` | Llosa de Ranes | la Llosa de Ranes | 4 / 4 |
| `2024004269` | Rest. El Polígon | Carlet | 4 / 4 |
| `2024004278` | Hotel Miramar | Torreblanca | 4 / 4 |
| `2024004286` | Rest. El Carcau | la Llosa | 4 / 4 |

Los nueve declaraban operador `ES*WEN`. No aparecen bajo esos IDs en ninguna
comunidad de la exportación nacional nueva. Tampoco se encuentran coincidencias
literales de sus coordenadas o IDs de punto con instalaciones de CV conservadas
en la nueva copia. Esto no descarta reidentificación o cambios de coordenadas:
no se ha investigado la causa de las ausencias ni su operación actual.

Las 43 claves de conector ausentes pertenecen íntegramente a esos nueve IDs;
no se pierden conectores de instalaciones comunes. No se borran los registros
históricos ni se admiten los pendientes por su ausencia en otra exportación.

## Compatibilidad con la evidencia municipal

Las tablas vigentes de revisión y admisión municipal se leen tras comprobar
sus huellas contra la validación conjunta Silver del 19 de octubre.

- Las **81 admisiones documentales** siguen presentes y conservan los atributos
  de identidad y ubicación contrastados. No hay motivos detectados por esta
  comparación para invalidarlas; no se han rehecho ni transferido automáticamente.
- De 1.474 instalaciones con municipio admitido, 1.466 siguen presentes con los
  mismos atributos y ocho están ausentes en la copia nueva.
- De 52 instalaciones pendientes, 51 siguen presentes sin corrección municipal;
  la otra es Exoil Pista de Silla. Su ausencia no resuelve el conflicto.

Si se prepara una versión diferenciada a partir de la copia del 18-10, la
compatibilidad con admisiones previas sería de 1.466 instalaciones, 4.194 puntos
y 5.017 conectores. Quedarían sin admisión previa 51 instalaciones, 165 puntos
y 185 conectores. Son recuentos de compatibilidad, **no una nueva Silver validada**.
Los 52 pendientes y las admisiones de la Silver original permanecen intactos.

## Recomendación temporal para Gold

La entrega no impone restricciones respecto a las fechas, según confirmación
del 20-10-2026. La selección se basa en trazabilidad y adecuación analítica;
los periodos reales y sus desfases se conservarán sin imponer un año común.

Se recomienda la exportación adquirida el **18-10-2026** como base de una versión
analítica diferenciada, porque permite fechar la observación del registro,
documentar su solicitud y conservar la identidad de todas las instalaciones
comunes y las 81 admisiones documentales. La fecha debe llamarse **fecha de
adquisición/observación del registro**, sin atribuirla como medición simultánea
o acreditar operación de todos sus elementos.

Esta elección requiere conservar las nueve ausencias como incertidumbre de
comparación entre versiones, y mantener la copia anterior para contrastar la
sensibilidad de la oferta/cobertura. No sumar ambas copias, dar por cerradas las
nueve instalaciones ni convertir su ausencia en déficit real confirmado.
La incertidumbre por ausencia del registro es distinta de la asignación
municipal pendiente y necesita su propio estado en el diseño de Gold.

La comparación no sustituyó Silver. La adopción y preparación diferenciada
se han completado posteriormente por encargo expreso; véase la
[recarga versionada](RECARGA_VERSIONADA_SILVER.md). El
[contrato inicial de Gold](CONTRATO_GOLD.md), definido después de la comparación,
detalla las tablas e indicadores que consumirían esa entrada.

## Reproducción y verificación

Con ambas copias, su recibo y las ejecuciones Silver vigentes disponibles:

```powershell
.venv\Scripts\python.exe src/comparar_recarga.py
.venv\Scripts\python.exe -m unittest discover -s tests -p test_comparar_recarga.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -p test_recarga.py -v
```

El comparador funciona sin red ni dependencias adicionales. Genera una carpeta
nueva bajo `resultados/comparacion_recarga/`, con `informe.json` y
`diferencias.json`; no actualiza ningún `actual.json`. La ejecución de referencia
es `20261020T143417939020Z`. Conserva huellas de las entradas, perfiles por copia,
cambios de los 27 campos, IDs exclusivos, diagnóstico exacto de correspondencias
y compatibilidad municipal por instalación. Las entradas se verifican de nuevo
al terminar la lectura. El lector existente limita cada exportación a 64 MiB.

Cuatro pruebas específicas comprueban altas/ausencias/cambios, claves y ámbito,
alteraciones que impiden reutilizar evidencia y coincidencias diagnósticas sin
fusión. También se han aprobado las siete pruebas del lector y preparación
tabular existente. No se ha repetido la validación completa de Silver.
