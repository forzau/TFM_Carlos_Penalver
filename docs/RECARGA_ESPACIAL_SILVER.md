# Recarga MITECO: capa y contraste municipal

Fecha: **16 de octubre de 2026**. Bloque espacial MITECO de la fase 8, preparado
con incidencias. La validación conjunta de todas las fuentes sigue pendiente.

## Referencia y reglas

Se utilizan las tablas verificadas de la [fase 4](RECARGA_SILVER.md), la
[base territorial Silver](BASE_TERRITORIAL_SILVER.md) y el catálogo oficial que
declara **EPSG:4258** para el CSV. El informe de recarga documenta la evidencia
y la salvedad WGS84/OCPI. Se verifican huellas, recibo, recurso y endpoint, sin
descargar nuevas instalaciones ni modificar los originales.

Se crean puntos con **X=longitud/Y=latitud**, transformados de EPSG:4258 a
EPSG:25830 con `always_xy=true`. Coordenadas y atributos originales permanecen.
Se comprueban rango, finitud, geometría y vuelta de proyección. El error máximo
de vuelta es **2,13 × 10⁻¹⁴ grados**, control numérico que no acredita precisión
posicional real.

Se intersectan los puntos con los 542 recintos. Se conservan todos los candidatos
si hay límites compartidos; ningún candidato se escoge por orden. Los puntos
exteriores o no admitidos también permanecen, con estado y sin asignación forzada.

El municipio declarado se busca por provincia y nombres oficiales INE o IGN.
Se eliminan diacríticos, puntuación y espacios para comparar y se admite distinto
orden de variantes separadas por `/`; los originales no cambian. Una clave
compartida por varios municipios no se resuelve. No se utilizan similitud
aproximada, código postal o municipio más cercano.

La asignación municipal automática exige **geometría admitida, intersección única,
provincia coincidente y nombre declarado resuelto al mismo municipio**. El código
espacial y el resuelto desde la etiqueta se conservan separados. Una discrepancia
no demuestra si falla la coordenada, la etiqueta o la cartografía: no se desplazan
puntos ni se sustituye el municipio publicado.

## Resultado

Las **1.526 geometrías** son válidas, intersectan un único recinto valenciano y
coinciden en provincia. No hay puntos exteriores o sobre límites ambiguos en
esta ejecución. El contraste municipal sí detecta incidencias:

| Provincia declarada | Conservadas | Asignación municipal admitida | Municipio discrepante |
| --- | ---: | ---: | ---: |
| Alicante/Alacant | 663 | 614 | 49 |
| Castellón/Castelló | 155 | 138 | 17 |
| Valencia/València | 708 | 641 | 67 |
| Total | **1.526** | **1.393** | **133** |

Hay **235 municipios** con alguna instalación de asignación admitida; no implica
que los demás carezcan de recarga. Los 133 conflictos —**8,72 %**— permanecen con
geometría y ambos códigos. No se cuentan como relaciones municipales contrastadas.

La distancia mínima al recinto del municipio declarado va de **4,37 m a 74,41 km**,
con mediana **1,63 km**. Es distancia plana diagnóstica al recinto, no a su centro,
un recorrido o un error posicional demostrado. No se usa un umbral para admitir
o corregir puntos.

Se inspeccionaron nombres, direcciones y coordenadas de los extremos. Varias
instalaciones declaradas en Benicarló se sitúan en Borriana/Burriana y sus nombres
o direcciones también apuntan a Burriana. Otras declaradas en Moixent/Mogente se
sitúan en València con nombres y direcciones que apuntan a València. Son indicios
de problemas de etiqueta en esos casos, sin corrección general ni certificación
de las 133 posiciones.

## Conservación de entidades

| Entidad | Originales | Tras relacionar con la capa | Con asignación municipal admitida |
| --- | ---: | ---: | ---: |
| Instalaciones | 1.526 | 1.526 | 1.393 |
| Puntos | 4.402 | 4.402 | 3.965 |
| Conectores | 5.244 | 5.244 | 4.751 |

Los 437 puntos y 493 conectores vinculados a instalaciones discrepantes siguen
conservados. Las entidades se relacionan con su instalación única: los candidatos
territoriales no se cruzan directamente con conectores para sumar infraestructura.
La suma de potencias no acredita capacidad simultánea.

## Salidas y reproducción

Con tablas anteriores, metadatos y `spatial` disponibles, desde la raíz:

```powershell
.\.venv\Scripts\python.exe src/georreferenciar_recarga.py --metadatos-miteco resultados/investigacion_datum_miteco/20261016/catalogo.json
```

La copia JSON debe conservar su recibo de adquisición. Un CRS, endpoint, recurso
o huella distintos exigen revisión. Sin red ni nuevas dependencias; DuckDB utiliza
dos hilos, 1 GB para su motor y almacenamiento temporal v1.5.0.

Salidas en `resultados/silver/recarga_espacial/<ejecucion>/`, fuera de Git:

- `recarga_instalaciones_geo.parquet`: **1.526 filas**, atributos originales,
  GeoParquet EPSG:25830 y campos de contraste/admisión.
- `recarga_municipios_candidatos.parquet`: **1.526 relaciones geométricas**,
  incluidas discrepantes; no son todas asignaciones admitidas.
- `entidad_municipio.parquet`: **1.393 relaciones contrastadas**.
- `incidencias_espaciales.parquet`: **133 filas**, con instalación, campo y motivo.
- `informe.json`: entradas, huellas, evidencia, reglas, controles, grupos de
  discrepancias, versiones y límites.

Ejecución validada: **`20261016T135403818794Z`**, estado
`preparada_con_incidencias`; `actual.json` se actualiza después de validar.
Todos los atributos originales se comparan antes/después; tipos, valores y WKB
se comparan al releer Parquet y se comprueba su CRS. Las entradas y las cuatro
salidas tabulares previas conservan sus huellas. El `actual.json` de fase 4 y sus
estados históricos no cambian. Los temporales se eliminan.

La suite completa pasa **77 pruebas, sin omisiones**. Las ocho nuevas cubren
ejes/proyección, nombres, conflictos, límites compartidos, coordenadas no admitidas,
provincia, ambigüedad de etiquetas, metadatos, cardinalidad y exportación.

## Revisión complementaria de fase 8 (18-10-2026)

La [validación conjunta](VALIDACION_CONJUNTA_SILVER.md) revisa los 133 conflictos y
admite 81 relaciones municipales mediante revisión explícita de establecimientos
y direcciones oficiales; véase la [ampliación de recarga](REVISION_RECARGA_SILVER.md). La
salida complementaria `recarga_municipio_validado` contiene 1.474 instalaciones,
con 4.231 puntos y 5.053 conectores asociados; 52/171/191 mantienen pendiente
su asignación. Se conservan las 1.526/4.402/5.244 entidades y todos sus atributos.
Este resultado no sobrescribe la capa ni las 1.393 relaciones del informe del
16-10-2026. Para usos municipales posteriores se empleará la relación vigente
de la validación conjunta y sus restricciones. El resto de Silver queda validado
operativamente con limitaciones; la suite de cierre pasa 104 pruebas.

Quedan 52 asignaciones pendientes antes de admitirlas en agregaciones municipales
automáticas. No se certifica precisión fina, exhaustividad u operatividad.
La ampliación del 19-10 incorpora i-DE espacial y eleva la suite a 120 pruebas;
véase la validación conjunta vigente. Gold sigue sin materializar.
