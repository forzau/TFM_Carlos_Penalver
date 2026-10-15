# Fuentes de datos

Fuentes previstas para estudiar la localización de nuevos puntos de recarga en
la Comunitat Valenciana:

| Bloque | Referencia | Uso previsto |
| --- | --- | --- |
| Parque de vehículos | DGT | Demanda potencial y distribución territorial de vehículos eléctricos. |
| Tráfico | Generalitat Valenciana | Intensidad Media Diaria y flujos por tramos de la red autonómica. |
| Población | INE, censo anual | Demanda residencial e indicadores demográficos. |
| Recarga existente | MITECO | Cobertura, potencia instalada y déficit relativo de infraestructura. |
| Renta | INE, Atlas de Distribución de Renta de los Hogares | Indicadores socioeconómicos. |
| Capacidad eléctrica | i-DE; CNMC como posible contraste | Viabilidad eléctrica relativa de las ubicaciones. |
| Red viaria | IGN/CNIG, Redes de Transporte | Accesibilidad y relaciones espaciales. |
| Ubicaciones candidatas | OpenStreetMap, distribución Geofabrik | Aparcamientos, servicios y otros puntos de interés. |
| Referencias territoriales | INE e IGN/CNIG | Relación oficial de municipios y recintos administrativos para validar códigos y preparar la integración espacial. |

La disponibilidad se ha comprobado preliminarmente durante la preparación del
proyecto. Las referencias de acceso y la revisión de condiciones de uso del
2026-10-14 se documentan en la [Entrega 02](entregas/02_datos_y_preparacion.md).
La [auditoría técnica](AUDITORIA_FUENTES.md) identifica esquemas, recuentos y
problemas de las copias locales. DGT corresponde al parque mensual provisional
de diciembre de 2025, con municipios pequeños suprimidos; renta contiene 2015–2023.
Quedan pendientes algunas versiones exactas y la integración espacial y temporal. La reutilización
de i-DE necesita aclaración; la versión de CC BY de aforos no consta en los
metadatos revisados y OSM requiere atender las obligaciones de ODbL al publicar.

El [catálogo de Bronze](CATALOGO_BRONZE.md), formalizado y ampliado el 15-10-2026,
registra once recursos en nueve bloques, incluidos el complemento municipal DGT
y las referencias territoriales oficiales. La definición pública recoge
procedencia, periodos, condiciones y pendientes; el manifiesto ampliado identifica
39 archivos con SHA-256. El [informe de referencias](REFERENCIAS_TERRITORIALES.md)
confirma los 542 códigos del ámbito y explica el código histórico 12066 de renta.
Se identifican las tablas INE 68065 y 30824; población coincide con el descargable
actual, mientras que renta conserva una copia diferente, documentada por su huella.

La capacidad eléctrica publicada es orientativa y no constituye una garantía
de acceso o conexión a la red.

El 2026-10-15 se ha verificado una [tabla municipal complementaria de DGT](DGT_COBERTURA_MUNICIPAL.md)
con los 542 municipios del ámbito. Se adopta Distintivo 0 como aproximación
documentada, sin equipararlo a BEV + PHEV ni imputar el detalle suprimido del TXT.
Las condiciones del nuevo recurso deben asociarse a esa descarga concreta.

Los originales previos se conservan en `Fuentes/` y los complementos DGT y
territoriales en `datos/bronze/`, fuera de Git. La documentación de preparación
y las instrucciones de ejecución están en el README, el catálogo y la auditoría.
