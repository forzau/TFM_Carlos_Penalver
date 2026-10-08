# TFM de Carlos Peñalver

Proyecto local del Trabajo de Fin de Máster, migrado desde un proyecto en la nube.
Repositorio: [forzau/TFM_Carlos_Penalver](https://github.com/forzau/TFM_Carlos_Penalver).

Tema elegido: **localización óptima de nuevos puntos de recarga para vehículos
eléctricos en la Comunitat Valenciana**. El objetivo es apoyar decisiones sobre
dónde ampliar la infraestructura pública de recarga utilizando datos reales y públicos.

Se han incorporado las dos conversaciones anteriores. La investigación y validación
de fuentes está completada preliminarmente según el contexto recibido; todavía no
se han realizado limpieza, integración ni modelado. La siguiente fase, cuando
corresponda, será la auditoría técnica de datasets. Consultar `contexto/PROYECTO.md`
y `contexto/ESTADO.md`.

## Estructura

| Ruta | Uso |
| --- | --- |
| `AGENTS.md` | Instrucciones para los asistentes que trabajen en el proyecto. |
| `contexto/` | Contexto del TFM, estado actual y decisiones. Los originales de `antecedentes/` se conservan localmente mediante OneDrive, fuera de Git. |
| `docs/entregas/` | Entregas y documentos de trabajo existentes. |
| `docs/memoria/` | Redacción de la memoria del TFM. |
| `docs/CONTINUIDAD.md` | Cómo continuar en otro equipo o conversación. |
| `docs/FUENTES.md` | Conservación y disponibilidad de los archivos originales. |
| `src/` | Código del proyecto, cuando se defina la solución. |
| `notebooks/` | Cuadernos de exploración, si se utilizan. |
| `resultados/` | Salidas generadas; se sincronizan con OneDrive y no se suben a Git. |
| `Fuentes/` | Material original existente; se conserva intacto y se sincroniza con OneDrive. |

## Retomar el trabajo

1. Leer `AGENTS.md`, `contexto/PROYECTO.md`, `contexto/ESTADO.md` y
   `contexto/DECISIONES.md`.
2. Consultar `docs/CONTINUIDAD.md` para comprobar la sincronización.
3. Trabajar sobre copias o generar salidas nuevas, conservando `Fuentes/` intacta.
4. Al terminar, actualizar el estado y registrar las decisiones relevantes.

GitHub conserva el historial de los archivos versionados. OneDrive sincroniza
también las fuentes y los resultados pesados. Clonar el repositorio por sí solo
no recupera `Fuentes/` ni las salidas locales.

El repositorio es público: revisar los archivos antes de publicarlos. No subir
credenciales ni datos personales o material cuya publicación no esté autorizada.

Todavía no hay un entorno de ejecución ni dependencias del TFM configurados.
