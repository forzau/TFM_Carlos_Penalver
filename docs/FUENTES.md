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

La disponibilidad se ha comprobado preliminarmente durante la preparación del
proyecto. Las referencias de acceso y la revisión de condiciones de uso del
2026-10-14 se documentan en la [Entrega 02](entregas/02_datos_y_preparacion.md).
La [auditoría técnica](AUDITORIA_FUENTES.md) identifica esquemas, recuentos y
problemas de las copias locales. DGT corresponde al parque mensual provisional
de diciembre de 2025, con municipios pequeños suprimidos; renta contiene 2015–2023.
Quedan pendientes algunas versiones exactas y la integración espacial y temporal. La reutilización
de i-DE necesita aclaración; la versión de CC BY de aforos no consta en los
metadatos revisados y OSM requiere atender las obligaciones de ODbL al publicar.

La capacidad eléctrica publicada es orientativa y no constituye una garantía
de acceso o conexión a la red.

Los datos originales se conservan en `Fuentes/`, fuera de Git. La documentación
de preparación y las instrucciones de ejecución están en el README y la auditoría.
