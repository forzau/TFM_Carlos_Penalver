# DGT: cobertura municipal y alternativa adoptada

Comprobación realizada el **15 de octubre de 2026**. Se resuelve la cobertura
territorial del indicador de parque mediante una tabla agregada municipal de DGT.
Se adopta **Distintivo 0 como aproximación de demanda potencial**, conservando el
desglose BEV/PHEV donde esté observado. No se afirma disponer de BEV/PHEV separados
para todos los municipios ni de demanda real de recarga.

## Recurso comprobado

- [Datos municipales – información general 2025, DGT](https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Datos-municipales-informacion-general-2025/).
- [Libro Excel oficial](https://www.dgt.es/export/sites/web-DGT/.galleries/downloads/dgt-en-cifras/informacion_municipal/Datos-municipales-general/DatosMunicipalesGeneral_2025.xlsx): una hoja, 57 columnas y 8.184 registros nacionales.
- [Ficha de contenido](https://www.dgt.es/export/sites/web-DGT/.galleries/downloads/dgt-en-cifras/informacion_municipal/Datos-municipales-general/ContenidoFichasGeneral2025.pdf): referencia del parque a **31 de diciembre de 2025**; población a 1 de enero. No confundir ambas fechas.

La copia inspeccionada tiene 2.982.931 bytes y SHA-256
`7507441f2eb4943d5dfe132285b28eb9cfcb717088ba932f51193cfa76c1e055`.
La URL del proveedor podría sustituir el archivo; el hash identifica esta copia.
Se conserva junto a la ficha PDF fuera de Git, en
`datos/bronze/dgt_municipal/2025/`, sin modificar el contenido de `Fuentes/`.
El [catálogo de Bronze](CATALOGO_BRONZE.md) registra ambas copias y sus huellas;
la descarga previa de auditoría también se conserva.

## Cobertura verificada contra población

Se comparan códigos INE de cinco dígitos con los códigos valencianos de
`Fuentes/Poblacion.csv`; no se unen indicadores ni se construye Silver.

| Provincia | Municipios de población | Municipios presentes en DGT | Ausentes |
| --- | ---: | ---: | ---: |
| Alicante/Alacant, 03 | 141 | 141 | 0 |
| Castellón/Castelló, 12 | 135 | 135 | 0 |
| Valencia/València, 46 | 266 | 266 | 0 |
| **Total** | **542** | **542** | **0** |

No hay códigos duplicados en el libro nacional. Para los 542 municipios, `Parque
Total`, `Electrificado` y `Distintivo 0` están completos y contienen recuentos
enteros no negativos. Esto acredita estructura y cobertura, no ausencia de todo
error en el registro administrativo.

Además hay tres filas provinciales **sin municipio especificado**:
`03000`, `12000` y `46000`, con 8, 3 y 35 vehículos respectivamente. No son tres
municipios adicionales, ni totales provinciales; se conservarán separadas.

| Indicador publicado | Suma de los 542 municipios |
| --- | ---: |
| Parque Total | 4.124.317 |
| Electrificado | 50.729 |
| Distintivo 0 | 78.180 |

El parque municipal más los 46 vehículos sin municipio suma **4.124.363**,
coincidiendo con el recuento provincial conjunto del TXT auditado. La coincidencia
del total no demuestra identidad de registros o de todos los indicadores.

## Qué significa Distintivo 0

La [descripción oficial de DGT](https://www.dgt.es/nuestros-servicios/tu-vehiculo/tus-vehiculos/distintivo-ambiental/etiqueta-cero)
incluye eléctricos de batería, autonomía extendida, híbridos enchufables con el
umbral de autonomía indicado y vehículos de pila de combustible. Por tanto:

- No equivale exactamente a BEV + PHEV ni los separa.
- No debe sumarse a `Electrificado`: ambos indicadores pueden solaparse.
- No se puede obtener PHEV restando `Electrificado` a `Distintivo 0`.
- La etiqueta `Electrificado` no se reinterpretará como BEV, PHEV o HEV sin una
  definición específica del recurso. Se conserva su nombre original.
- Un recuento municipal de vehículos registrados aproxima presencia potencial;
  no mide sesiones, energía demandada ni necesidad de carga pública. La titularidad
  empresarial y la movilidad entre municipios requieren cautela al interpretarlo.

El detalle del TXT se conserva con su cobertura real. Los municipios suprimidos
no reciben ceros ni estimaciones de BEV/PHEV presentadas como observaciones.

## Alternativas revisadas

El [panel oficial del parque](https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Panel-de-datos-del-parque-de-vehiculos/)
permite consultar categoría eléctrica. Se comprobó en el navegador el año 2025 y
Comunitat Valenciana: el selector municipal incluye «Municipio con menos de
10.000 habitantes». Por tanto, no evita la agrupación de las localidades pequeñas.

También se inspeccionó el [libro de tablas estadísticas de 2025](https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Parque-de-vehiculos-Tablas-Estadisticas-2025/):
sus 21 hojas publican agregados nacionales, autonómicos o provinciales; no se encontró
un desglose BEV/PHEV de todos los municipios. No se afirma que esa información no
pueda existir en otros recursos; no es necesaria para la aproximación adoptada.

## Reproducción y límites

Con el entorno del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/auditar_dgt_municipal.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

El script descarga el XLSX si falta, lee la copia en modo de solo lectura,
comprueba esquema/códigos/recuentos, compara cobertura y guarda
`resultados/auditoria_dgt/perfil_municipal_2025.json`, fuera de Git. Registra URL,
hash y fecha de inspección. Si la descarga se hizo previamente, no inventa una
fecha de adquisición a partir de la modificación del archivo.

Esta comprobación no modifica el auditor original ni vuelve a recorrer el TXT
nacional. Tres pruebas nuevas verifican separación de no asignados, conservación
del archivo, detección de repetidos/faltantes/valores inválidos y rechazo de códigos
ambiguos. Las nueve pruebas del proyecto pasan.

La [ficha del nuevo recurso](https://datos.gob.es/es/catalogo/e00130502-datos-municipales-informacion-general-2025)
remite al aviso legal general. No se traslada automáticamente la declaración
CC BY 4.0 del recurso de microdatos a este Excel. Se conserva la atribución a DGT;
las condiciones concretas deberán quedar asociadas antes de redistribuir la copia
o el dataset derivado. No se publica aquí el fichero descargado.

La cobertura queda resuelta para el indicador municipal adoptado. Faltan las
transformaciones de Silver, la validación de integración y la definición final de
Gold; no se ha entrenado un modelo ni contactado con DGT.
