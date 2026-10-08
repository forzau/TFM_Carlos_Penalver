# Instrucciones de trabajo

## Al comenzar

- Leer `README.md`, `contexto/PROYECTO.md`, `contexto/ESTADO.md` y
  `contexto/DECISIONES.md`. Consultar `docs/CONTINUIDAD.md` al cambiar de equipo.
- Responder y mantener la documentación en español.
- Comprobar el estado de Git antes de editar; conservar los cambios del usuario.
- No deducir el tema ni los objetivos del TFM únicamente de los nombres de archivo.
- Las dos conversaciones anteriores están incorporadas. La segunda establece el
  estado más reciente: localización de nuevos puntos de recarga en la Comunitat
  Valenciana, con investigación de fuentes completada preliminarmente.
  La primera recoge la ideación histórica. Sus originales locales están en
  `contexto/antecedentes/01_conversacion.md` y `02_conversacion.md`.
- Trabajar según el enunciado vigente de cada entrega. Priorizar el problema real,
  el usuario del producto y la decisión que se quiere mejorar.
- Diferenciar datos encontrados, datos cuya existencia se supone y datos pendientes
  de comprobar. La experiencia del usuario con una herramienta no implica que se
  haya seleccionado para el TFM.
- No iniciar limpieza, joins, EDA, elección de CRS o granularidad, scoring, modelos
  ni dashboards por el mero hecho de incorporar el contexto. La auditoría técnica
  es el siguiente paso previsto cuando el usuario o la entrega vigente lo requiera.
- El TXT nacional de DGT debe procesarse sin cargarlo entero en memoria. No
  eliminar nulos de renta sin comprender los niveles territoriales; no descartar
  puntos OSM alejados sin inspeccionarlos. La capacidad eléctrica es orientativa,
  no una garantía de conexión. No forzar ML supervisado sin un objetivo adecuado.

## Material y cambios

- Conservar `Fuentes/` intacta: no editar, renombrar, mover ni borrar su contenido
  sin una instrucción explícita del usuario.
- OneDrive sincroniza los originales y los archivos pesados. `Fuentes/` y las
  salidas de `resultados/` están excluidas de Git; no forzar su incorporación.
- Los originales de conversaciones de `contexto/antecedentes/` se conservan fuera
  de Git mediante OneDrive; los resúmenes mantenidos están en `contexto/`.
- Mantener los documentos existentes de `docs/entregas/` salvo que el trabajo
  solicitado requiera modificarlos.
- Usar rutas relativas a la raíz del proyecto; no guardar rutas particulares de
  un ordenador dentro de código o documentación compartida.
- Hacer el cambio más pequeño que resuelva la tarea. No añadir dependencias,
  infraestructura ni herramientas sin una necesidad concreta.
- No publicar credenciales ni material privado. Revisar el diff y los archivos
  incluidos antes de subir cambios al repositorio público.
- Verificar los cambios de forma proporcional e indicar qué se ha comprobado.

## Al terminar

- Actualizar `contexto/ESTADO.md` con lo realizado, los pendientes y el próximo paso.
- Actualizar `contexto/PROYECTO.md` cuando se confirme información del TFM.
- Registrar en `contexto/DECISIONES.md` las decisiones duraderas y su motivo.
- El contexto necesario para continuar debe estar en estos archivos, no depender
  únicamente de la conversación ni de la memoria del asistente.
- Distinguir los cambios locales de los que ya están guardados en GitHub.
