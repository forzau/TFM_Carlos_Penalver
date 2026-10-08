# Estado y punto de reanudación

Actualizado: 2026-10-08. Migración documental de las dos conversaciones incorporada.

## Estado actual del TFM

- Tema elegido: localización óptima de nuevos puntos de recarga para vehículos
  eléctricos en la Comunitat Valenciana.
- Ámbito inicial: Alicante/Alacant, Castellón/Castelló y Valencia/València.
- Investigación y comprobación de fuentes completadas preliminarmente según
  la segunda conversación: ocho bloques localizados y descargados.
- No hay limpieza, integración, dataset maestro, EDA, variables, modelos,
  optimización ni producto visual final realizados.
- Enfoque considerado: GIS, multicriterio y optimización espacial; metodología,
  granularidad, scoring, herramientas y criterios de evaluación aún abiertos.
- El principal reto previsto es integrar fuentes con granularidades espaciales
  y temporales diferentes. La viabilidad técnica detallada no está validada.

## Migración local preparada

- Estructura para contexto, documentos, código, cuadernos y resultados.
- Repositorio local conectado a `origin`; `main` sigue `origin/main`.
- Ambos adjuntos conservados íntegros en `contexto/antecedentes/`, fuera de Git.
- Contexto, decisiones e instrucciones actualizados con la segunda conversación.
- `Fuentes/` conserva el trabajo original, sin modificaciones en esta migración.
- Inventario local excluido de Git; originales y archivos pesados se conservan
  mediante OneDrive. Su sincronización efectiva no se ha comprobado.
- `docs/entregas/01_ideas_producto.md` contiene las tres propuestas iniciales y
  se conserva sin cambios. Su envío y evaluación no están confirmados.

## Próximo paso

Cuando el usuario o la entrega vigente indique comenzar, realizar la **auditoría
técnica de datasets** descrita en `contexto/PROYECTO.md`. No empezar directamente
por limpieza, elección de granularidad, joins o modelado.

Después de la auditoría: decidir granularidad y preparar el dataset maestro.

## Pendientes de confirmación

- Enunciado vigente, calendario y estado de las entregas académicas.
- Correspondencia de archivos locales con los ocho bloques descritos.
- Esquemas, periodos, cobertura, CRS, claves, calidad y limitaciones reales.
- URLs exactas, versiones y condiciones de uso de las fuentes.
- Entorno de ejecución y dependencias necesarios para la fase autorizada.

## Guardado y sincronización

El setup y los resúmenes de las dos conversaciones se conservan en el historial
de GitHub. Los originales de conversaciones, el inventario de fuentes y los datos
quedan excluidos de Git y se conservan mediante OneDrive.

Consultar `git status` y `git log -1` para conocer el estado real de cada copia;
este documento no sustituye esas comprobaciones.

## Comprobaciones y límites

En esta migración se han leído los dos adjuntos, conservado sus textos íntegros
y contrastado el contexto con el documento actual de la Entrega 1. Se han revisado
las exclusiones y los cambios documentales de Git.

Las aperturas de datos y comprobaciones en QGIS son trabajo previo descrito por
el usuario; no se han repetido. No se ha iniciado una auditoría de datos ni
investigado fuentes externas durante la incorporación del contexto.
