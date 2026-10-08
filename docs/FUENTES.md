# Fuentes originales

La carpeta local existente se llama `Fuentes/`. Se conserva sin modificaciones y
está excluida de Git. OneDrive es el medio elegido por el usuario para sincronizar
su contenido entre equipos, incluidos los archivos de varios GB.

El inventario inicial local está en `docs/inventario_fuentes.csv`: contiene las rutas
relativas, el tamaño en bytes y la fecha de modificación en UTC observados durante
el setup del 2026-10-08. Es una referencia de disponibilidad, no un análisis de los
datos ni una comprobación criptográfica de su contenido. Se conserva fuera de Git
y se sincroniza con OneDrive; no estará disponible al clonar solamente el repositorio.

Al trabajar en otro equipo, descargar localmente las fuentes necesarias desde
OneDrive. Mantener la estructura y la capitalización `Fuentes/`, también en sistemas
que distingan mayúsculas de minúsculas.

El procesamiento debe leer los originales y escribir sus salidas en `resultados/`.
Los resultados que deban formar parte de una entrega se incorporarán expresamente
a `docs/entregas/` después de revisarlos.

La segunda conversación describe ocho bloques: vehículos DGT, aforos GVA,
población INE, recarga MITECO, renta INE, capacidad eléctrica, red viaria IGN/CNIG
y POI de OpenStreetMap. Sus usos previstos y las observaciones preliminares están
en `contexto/PROYECTO.md`.

Las comprobaciones previas son superficiales y no sustituyen la auditoría técnica.
Quedan pendientes las URLs y versiones exactas, licencias, esquemas y correspondencia
de cada archivo local con su bloque. No inferir su contenido solo por el nombre.
