# Catálogo de Bronze

Registro formalizado y ampliado el **15 de octubre de 2026**. Bronze conserva las copias
recibidas, su procedencia y sus limitaciones antes de transformarlas. No requiere
unir las fuentes ni cargarlas todas en una base de datos.

La definición reproducible está en
[`config/catalogo_bronze.json`](../config/catalogo_bronze.json): once recursos
agrupados en nueve bloques, los ocho analíticos anteriores y las referencias
territoriales oficiales. Cada recurso declara
proveedor, página de acceso, descargable cuando se conoce, versión, periodo,
fecha de adquisición, cobertura, unidad original, formato, función, condiciones
revisadas y pendientes. **`null` significa no confirmado**, no inexistente.

## Recursos registrados

| Identificador | Copia y función | Referencia temporal acreditada | Condiciones registradas y pendientes |
| --- | --- | --- | --- |
| `dgt_microdatos_202512` | TXT nacional; detalle disponible del parque. | Diciembre de 2025, provisional. | CC BY 4.0 declarada en la ficha del recurso; adquisición no documentada. |
| `dgt_municipal_2025` | XLSX municipal y ficha PDF; cobertura completa de los 542 municipios mediante Distintivo 0. | Parque a 31-12-2025; descarga realizada el 15-10-2026. | Ficha con aviso legal general; falta asociar condiciones específicas. No heredar la licencia del TXT. |
| `gva_aforos` | GeoPackage de tráfico de la red autonómica. | Capas 2009–2025; descargable WFS identificado. | CC BY sin versión indicada; edición exacta de la copia y adquisición pendientes. |
| `ine_poblacion` | CSV de población, tabla 68065; identidad completa de SHA-256 con descargable oficial comprobada. | 2021–2025; índice publicado el 02-12-2025. | Condiciones generales del INE, CC BY 4.0 salvo excepciones; adquisición original desconocida. |
| `miteco_recarga` | CSV de instalaciones, puntos y conectores. | Fecha de exportación no acreditada. | CC BY 4.0 declarada; versión y adquisición pendientes. La modificación de un registro no fecha la copia. |
| `ine_renta` | CSV de la tabla 30824; el descargable actual difiere de la copia local. | Periodos 2015–2023 observados; edición exacta local desconocida. | Condiciones generales del INE, CC BY 4.0 salvo excepciones; adquisición y edición originales desconocidas. |
| `ide_capacidad_demanda` | CSV de capacidad de acceso para demanda; apoyo orientativo. | Fecha y edición no acreditadas. | Licencia abierta no confirmada y restricciones en el aviso legal; aclarar reutilización y referencia espacial. |
| `ign_red_transporte` | Tres paquetes provinciales: 15 GeoPackages y seis documentos de atributos/lectura. | Edición oficial no acreditada. | Condiciones IGN compatibles con CC BY 4.0; falta año de edición para atribución y adquisición. |
| `osm_valencia` | GeoPackage y README del extracto Geofabrik. | 09-09-2026 a las 20:21:20 UTC, según README. | ODbL 1.0; atribución y obligaciones de bases derivadas. Adquisición y enlace histórico pendientes. |
| `ine_municipios_2025` | Relación oficial de municipios, con 542 códigos valencianos. | 01-01-2025, acreditado dentro del XLSX; descarga 15-10-2026. | Condiciones generales del INE; conservar atribución y edición. |
| `ign_unidades_cv` | GeoJSON WFS: 542 municipios, tres provincias y una comunidad autónoma, más capacidades y recuento. | Consulta y descarga 15-10-2026; no acredita una edición histórica común a todos los límites. | Condiciones IGN compatibles con CC BY 4.0; atribución a producto y consulta. |

Las evidencias y URL de cada condición constan en el JSON, con fecha de revisión
del 14 o 15 de octubre de 2026. El catálogo recoge esa revisión; no supone una
nueva autorización del proveedor ni garantiza redistribución de todas las entradas.
La [Entrega 02](entregas/02_datos_y_preparacion.md) desarrolla las condiciones y
la [auditoría](AUDITORIA_FUENTES.md) documenta los problemas técnicos.

## Conservación física e integridad

- Los 29 archivos anteriores permanecen en `Fuentes/`, sin cambios ni duplicación.
- El Excel municipal y su ficha se conservan en
  `datos/bronze/dgt_municipal/2025/`. Se han copiado desde la descarga auditada,
  comprobando igualdad de SHA-256; se conserva también la descarga previa.
- Las referencias territoriales se preservan bajo `datos/bronze/ine_municipios/`
  y `datos/bronze/ign_unidades_cv/`, con URL, fecha UTC, tamaño y huella en recibos
  de adquisición. No se han reemplazado las copias anteriores.
- Los 39 archivos incluyen datos y documentación acompañante. El catálogo no
  incorpora el libro estadístico alternativo ni la imagen de inspección del PDF:
  son material exploratorio, no entradas del flujo de preparación.
- Los perfiles de auditoría y los manifiestos se generan en `resultados/`.
  `Fuentes/`, `datos/bronze/` y los resultados permanecen fuera de Git.

[`src/catalogar_bronze.py`](../src/catalogar_bronze.py) genera un manifiesto local
por ejecución en `resultados/bronze/manifiesto_<fechaUTC>.json`, sin sobrescribir
los anteriores. Incluye una copia de los metadatos, la huella del fichero de
configuración y, por archivo, ruta relativa, recurso, rol, tamaño, SHA-256 y
modificación local. La fecha de registro y la modificación local **no sustituyen
la fecha de descarga ni la fecha de referencia del dato**.

La lectura se realiza en bloques de 4 MiB, también para el TXT nacional de DGT.
El registro falla si faltan entradas, se repiten, cambia tamaño/modificación
durante la lectura o aparecen archivos sin catalogar en las dos ubicaciones de
originales. La verificación vuelve a calcular las huellas y comprueba el conjunto
registrado, sin reescribir el manifiesto. Un hash permite detectar cambios frente
a esa referencia local; no certifica autoría ni recupera una copia perdida.

El registro inicial y su verificación completa se han ejecutado el 15-10-2026:
**31 archivos, 23 de datos y ocho de documentación, 10.453.967.314 bytes**.
Todas las huellas coincidieron con el manifiesto inicial. En ese registro pasaron
las 14 pruebas disponibles, incluida detección de cambios, ausencias, rutas fuera
de Bronze y entradas sin registrar. El auditor municipal mantuvo cobertura
542/542 al leer la copia preservada.

La ampliación territorial registra **39 archivos: 25 de datos y 14 de
documentación, 10.491.345.592 bytes**. El manifiesto inicial se conserva y las 31
copias anteriores mantienen las mismas huellas y tamaños. La verificación completa
del nuevo manifiesto es correcta y pasan las 20 pruebas disponibles, incluidas
adquisición, reutilización y cobertura territorial. El nuevo registro y las comprobaciones se documentan en
[Referencias territoriales y procedencia](REFERENCIAS_TERRITORIALES.md).

## Reproducción y nuevas copias

1. Preparar Python según el README. Obtener las copias de los proveedores y
   conservarlas en las rutas relativas de `entradas` del JSON. El repositorio no
   incluye los originales; las URL actuales pueden devolver otras versiones.
2. Para DGT municipal, `src/auditar_dgt_municipal.py` descarga el XLSX si falta en
   la ubicación estable. Guardar también la ficha PDF oficial en esa carpeta;
   su enlace está en `documentacion` del recurso. Si ya hay copias locales,
   conservarlas sin sobrescribir y comprobar su identidad antes de registrarlas.
   Para las referencias territoriales, ejecutar `src/incorporar_referencias.py`
   y después `src/auditar_referencias.py`; ambos se describen en el informe de
   referencias y en el README.
3. Ejecutar desde la raíz:

   ```powershell
   .\.venv\Scripts\python.exe src/catalogar_bronze.py
   ```

4. Conservar el manifiesto creado y verificarlo antes de preparar los datos.
   Sustituir el nombre del ejemplo por el que indique el registro:

   ```powershell
   .\.venv\Scripts\python.exe src/catalogar_bronze.py --verificar "resultados/bronze/manifiesto_<fechaUTC>.json"
   ```

Una descarga distinta necesita su propia ubicación, metadatos y nuevo manifiesto;
no debe reemplazar la copia de referencia. Si se añade o retira un archivo,
actualizar primero el catálogo de forma explícita. Conservar las copias y sus
manifiestos juntos en el respaldo; la sincronización efectiva no se ha verificado.

## Cierre para la preparación académica

Para el alcance académico del TFM se da por concluida la revisión de condiciones
como paso preparatorio y se continúa con el trabajo, manteniendo las atribuciones
y las evidencias recogidas. Los estados de licencia del catálogo conservan lo
efectivamente encontrado; este criterio de avance no aporta una licencia nueva.

La Bronze actual queda preparada para comenzar Silver: copias conservadas,
catálogo, perfiles de auditoría y manifiesto de integridad verificado. Las fechas
históricas o ediciones no recuperadas permanecen como limitaciones documentadas,
sin inventarlas ni impedir el avance con las copias identificadas.

Ya se incorporaron la relación oficial de municipios y la cartografía de límites,
registrando nuevas entradas y un manifiesto ampliado, con conservación del anterior.
Se recuperaron las tablas INE y el descargable de aforos. Las ediciones y fechas
no demostrables permanecen como desconocidas, incluido el hecho de que el CSV
actual de renta no es idéntico al conservado.
La comprobación del respaldo sigue pendiente. La limpieza, normalización y
unión de fuentes corresponden a Silver; todavía no hay un conjunto listo para ML.
