# Variables y normalización para la comparación territorial

**Definición técnica v1 — 21-10-2026.** Selección y escalas definidas y ensayadas;
la materialización se describe al final, sin ponderación o ranking Gold.
Se mantienen las diez tablas anteriores y sus valores originales. La normalización
organiza la comparación relativa; no estima demanda real, suficiencia o viabilidad.

## 1. Qué decisión y qué nivel describe cada variable

Se mantiene la secuencia **municipios como contexto → candidatos para revisión**.
Una variable municipal no adquiere detalle local por copiarla a cada POI.
Los 542 municipios siguen en el análisis, incluidos los 52 sin candidatos OSM.

| Dimensión principal | Variable y definición | Nivel y dirección de lectura | Uso y límite |
| --- | --- | --- | --- |
| Volumen potencial | `vehiculos_distintivo_0`, parque municipal DGT del 31-12-2025. | Municipio; valor mayor representa mayor volumen registrado de esta aproximación. | Contexto para estudiar oportunidad de recarga; no sesiones, consumo ni BEV+PHEV exacto. Cero registrado no demuestra demanda real nula. |
| Separación geométrica de oferta | `distancia_minima_geometria_m`: mínimo de `ST_Distance(geometria_original_candidato, geometria_instalacion)` entre instalaciones admisibles del escenario. | Elemento candidato; valor mayor representa mayor separación mínima dentro del inventario. | Aproximación espacial, sin recorrido, horario, compatibilidad o disponibilidad. Un área con coordenadas de recarga intersectantes tiene distancia cero, sin acreditar suficiencia. |

Estas son **dos dimensiones**, no un índice de necesidad todavía. Se muestran
con sus valores originales y las escalas siguientes; no se suman euros,
personas, puntos y metros en bruto ni se fija un umbral de «oferta suficiente».

### Contexto y diagnósticos que no reciben otro voto automático

| Variable existente | Papel en esta versión |
| --- | --- |
| Proporción Distintivo 0/parque | Describir composición del parque. No sumarla al volumen como una segunda demanda independiente. |
| Instalaciones, puntos y conectores admitidos | Explicar oferta registrada separando entidades. No sumar las tres cantidades como si midieran capacidad independiente. |
| Distintivo 0/puntos admitidos | Presión descriptiva alternativa; conserva nulo con denominador cero. No sumarla además de demanda y proximidad como un tercer voto independiente. |
| Población y parque total | Contexto y revisión de tamaños; evitar duplicar el efecto de escala territorial. |
| Renta municipal | Contexto socioeconómico y posibles comparaciones posteriores; no premiar renta alta ni penalizar los ocho nulos. |
| Tipo de candidato y revisión local | Elegibilidad y explicación, no una puntuación de demanda inventada por categoría. |
| Coincidencias área–recarga, solapamientos y borde | Avisos y revisión de interpretación. No descuentos numéricos automáticos ni fusión de elementos. |
| Distancia al punto representativo | Sensibilidad a la representación espacial, conservando la tabla anterior y su definición. No otro componente independiente de cobertura. |
| Aforos e i-DE | Contexto posterior si se define un uso pertinente; no requisitos para comparar ahora las dos dimensiones principales. |

## 2. Definición espacial y escenarios

Para puntos se usa su geometría original. Para áreas, la superficie original
completa. El mínimo al área es cero cuando una coordenada de instalación cae
dentro o sobre su borde; cuando está fuera mide la separación mínima a esa
superficie. Puede favorecer áreas extensas frente a puntos: se mostrará la
representación y se conservará la distancia desde el representante como contraste.
Ninguna de las dos distancias identifica el acceso real o el lugar de instalación.

No se elige un centroide municipal, no se calcula accesibilidad de habitantes
mediante una mediana de POI y no se reparten vehículos entre candidatos. Los
elementos OSM no son una muestra representativa de localización de población.

Se usan los tres conjuntos existentes, siempre con geometrías de instalación
admitidas, válidas y no vacías, incluyendo oferta de otros municipios:

1. `principal_admitida`: presentes con relación municipal admitida.
2. `incluye_pendientes`: todas las presentes en la copia principal.
3. `incluye_ausentes_historicas`: presentes más los nueve registros históricos ausentes.

Son escenarios de sensibilidad, sin promedio ni probabilidades. Ampliar el
conjunto no puede aumentar el mínimo. No se modifica la presencia, asignación
o situación operativa de un registro por su distancia.

Si falta geometría admisible, no hay superficie del área dentro de CV o falta
oferta admisible, el resultado es nulo con motivo explícito. No usar
cero o infinito para rellenarlo. Los casos de contacto territorial sin superficie
seguirán conservados para revisión, sin convertirlos en un emplazamiento evaluable.
En las copias actuales el ensayo puede calcular los 16.377 elementos por escenario.

### El control de borde debe corresponder a la misma geometría

El control Gold actual compara distancia **del representante** a recarga y al
borde. Conserva ese significado. Para la nueva variable se calcula también:

`distancia_geometria_borde_cv_m = ST_Distance(geometria_original_candidato, borde_union_cv)`

`posible_influencia_exterior_geometria = distancia_minima_geometria_m > distancia_geometria_borde_cv_m`

No se reutilizará el aviso del representante como si estuviera calculado para
la nueva distancia. El nuevo aviso acompaña a las variables materializadas;
el anterior servirá de contraste. Se mantiene la desigualdad estricta y el
desconocido si no se puede comparar. El aviso incluye posibles efectos de costa,
no confirma oferta exterior y no altera el valor normalizado.

Para calcularlo sin comparar cada área con todo el contorno, se reutiliza como
cota la distancia ya verificada del representante al borde. El representante
pertenece al candidato, por lo que el mínimo del área no puede ser mayor.
Se recorta el borde a la envolvente del área ampliada por esa cota más un metro
de margen; ese recorte conserva el punto de borde más cercano. La distancia
sigue siendo exacta a la geometría original, sin simplificarla. Para puntos,
coincide con la distancia del representante. Se comprueban cota finita y no
negativa, pertenencia del representante y recorte no vacío; si fallan, se detiene
la preparación. El margen solo amplía la búsqueda, no se suma a la distancia.

## 3. Normalización base y contraste

La definición base es **logarítmica con cero anclado**, en escala 0–1 para las
observaciones de la versión de referencia:

`N_log(x; M) = ln(1 + x) / ln(1 + M)`

`x` se expresa siempre en **vehículos** para demanda y en **metros** para
distancia; equivale a usar unidades de referencia de un vehículo y un metro.
No cambiar metros a kilómetros dentro del logaritmo sin cambiar la definición:
`log(1+x)` depende de la unidad. La base del logaritmo es irrelevante para este
cociente si se usa la misma en numerador y denominador.

Se conserva además un contraste lineal con los mismos anclajes:

`N_lineal(x; M) = x / M`

Ambas son crecientes y conservan cero y orden. La logarítmica comprime
diferencias absolutas altas y concede más cambio de escala por unidad cuando
los valores son bajos. **Es una elección de preferencias marginales, no una
operación neutral ni una corrección de calidad.** No demuestra que los territorios
pequeños o los primeros metros tengan ese valor social; se ensayará sensibilidad
frente a la lineal antes de fijar ponderaciones.

El [JRC, paso 5 de normalización](https://knowledge4policy.ec.europa.eu/composite-indicators/toolkit_en/navigation-page/10-step-guide_en/step-5-normalisation_en),
relaciona la elección de escala con los datos y el objetivo, explica el efecto
de transformaciones cóncavas y advierte de la influencia de extremos. La elección
concreta de fórmula, unidades y referencias de este documento es del proyecto.

### Referencias fijas para la versión

| Dimensión | Universo usado para fijar `M` | Referencia del ensayo |
| --- | --- | ---: |
| Demanda | Los 542 municipios, una observación municipal por código; no multiplicar por número de POI. | `M_D = 10.246` vehículos Distintivo 0. |
| Distancia | Los 16.377 elementos con distancia a geometría evaluable en `principal_admitida`. | `M_P = 36.628,0631790845` m. |

El cero es un anclaje semántico, no el mínimo que se vuelva a buscar al filtrar.
Para estas copias, ambos mínimos observados son cero y la fórmula coincide con
reescalado de `log(1+x)` entre mínimo y máximo. El máximo es una referencia del
inventario, no una meta de política ni un radio de servicio. Sigue siendo sensible
a valores extremos y al inventario limitado a CV; no se eliminan ni recortan esos datos.

Las mismas referencias se aplican a los tres escenarios. No reajustar por
provincia, municipio, selección del mapa o escenario: cambiaría la escala y
podría hacer incomparables resultados que se pretendían contrastar. No se ajustan
coeficientes sobre un ranking deseado.

Un cambio de copias o periodos genera otra versión con referencias identificadas;
para comparar versiones se recalculará una referencia común explícita. Un valor
nuevo por encima de `M` se señala como fuera de referencia; no se recorta a uno
silenciosamente ni se mezcla con la comparación vigente.

### Nulos y casos degenerados

- Valor ausente, negativo no admisible, no finito o falta de referencia: resultado
  nulo con estado, sin imputación por cero o media. Un dato inválido debe revisarse.
- Referencia observada completamente cero (`M=0`): los valores observados cero
  se representan como cero y estado `todos_cero`, sin división por cero.
- Referencia sin variación y positiva: las fórmulas dan uno, con aviso
  `sin_variacion_positiva`; la dimensión no discrimina y no debe incorporarse
  silenciosamente a una combinación ponderada.
- Un componente ausente no se compensa aumentando automáticamente el peso del
  otro. Se conserva el resultado parcial y su motivo.
- El cero de renta no se inventa; la renta no interviene en estas dos escalas.
  Presión con cero puntos sigue nula, sin convertirse en prioridad máxima.

## 4. Qué cambia numéricamente

El perfil real de demanda tiene mediana **20**, percentil 95 **550,85** y máximo
10.246; hay 21 ceros registrados. El máximo y la mediana son muy distintos.
La escala logarítmica evita que casi todos los municipios queden próximos al
cero lineal, pero cambia mucho sus distancias relativas: esa diferencia debe
quedar visible al interpretar pesos futuros.

| Ejemplo de demanda | Distintivo 0 | `N_log` | `N_lineal` |
| --- | ---: | ---: | ---: |
| Palanques | 0 | 0,0000 | 0,0000 |
| Zorita del Maestrazgo | 1 | 0,0751 | 0,0001 |
| Quartell | 30 | 0,3719 | 0,0029 |
| Alacant/Alicante | 6.083 | 0,9435 | 0,5937 |
| València | 10.246 | 1,0000 | 1,0000 |

| Distancia ilustrativa, m | `N_log` | `N_lineal` |
| ---: | ---: | ---: |
| 0 | 0,0000 | 0,0000 |
| 100 | 0,4392 | 0,0027 |
| 500 | 0,5916 | 0,0137 |
| 1.000 | 0,6574 | 0,0273 |
| 5.000 | 0,8105 | 0,1365 |
| 10.000 | 0,8765 | 0,2730 |

Estos números no son porcentajes de demanda o cobertura, probabilidades,
umbrales o prioridades finales. Por ejemplo, 500 m no significa «59 % de déficit».
Las distancias de la tabla ilustran la transformación; no son casos inventados
presentados como observaciones.

El ensayo de geometrías conserva las tres ejecuciones Gold actuales y calcula
49.131 mínimos experimentales. En el principal, la mediana resulta **415,7430 m**
frente a 434,8157 m del representante, con 292 ceros. Los escenarios ampliados
tienen 300 ceros y medianas de 406,4281 y 406,1568 m. Para los puntos no cambia
la medida; las 13.444 áreas cambian su distancia. La máxima reducción respecto
al representante es 943,1311 m. La ventaja geométrica de áreas extensas exige
conservar el contraste y revisar lugares físicos antes de elegirlos.

## 5. Unión de niveles y condiciones antes de ponderar

La demanda normalizada se calcula primero una vez por municipio. Un candidato
con municipio de contexto exclusivo podrá mostrar esa demanda como **contexto
municipal**, sin asignársela como demanda propia ni dividirla entre candidatos.
Los 106 elementos con varios municipios conservan todos los vínculos y no
reciben un valor municipal único por elegir el mayor, el más próximo o repartir área.
La proximidad puede ser evaluable aunque el contexto municipal exclusivo falte.

No se construirá un índice municipal de cobertura promediando POI. Los 52
municipios sin POI mantienen su demanda y contexto; su proximidad de candidatos
no existe en esta selección y no se rellena con cero, infinito o una mediana ajena.
Para comparar zonas se mostrará el contexto municipal junto a los candidatos
observados, con cobertura de la muestra explícita.

Los avisos de pendientes/ausencias, coincidencia de recarga, solapamientos,
geometría y posible influencia exterior acompañan a los valores. No suponen
un descuento fijo o exclusión silenciosa. Una coincidencia de recarga no elimina
la posibilidad de ampliación, cuya necesidad exigiría información adicional.

Después de materializar y verificar las variables, se podrán ensayar pesos
demanda/proximidad 50/50, 60/40 y 70/30, conservando ambas normalizaciones y
escenarios. No hay pesos definitivos o puntuación calculada en este documento.
Una combinación futura a nivel candidato tendrá que explicar el contexto
municipal heredado y la elegibilidad, sin presentar representaciones OSM como
sitios físicos únicos ni la suma como beneficio económico previsto.

## Evidencia, alcance ejecutado y continuación

Ensayo local en `resultados/diseno_variables/20261021/`: `perfil.py`,
`informe.json` y `ensayo_distancias_geometria.parquet`, fuera de Git.
Contiene huellas, SQL del mínimo, distribuciones, referencias y ejemplos de
normalización. Se verifican límites 0–1, ceros/nulos y entradas inválidas,
coincidencia con controles de áreas, mínimos no superiores al representante
y monotonicidad al ampliar oferta. El ensayo se conserva como contraste
independiente de la materialización siguiente.

## Materialización reproducible de las variables

Código: `src/preparar_variables_gold.py`; pruebas: `tests/test_variables_gold.py`.
Lee las selecciones vigentes de contexto municipal, candidatos y controles;
comprueba huellas, versiones compatibles, claves y CRS. No modifica las tablas
de entrada. Reutiliza el exportador existente y verifica esquema y valores
tras volver a leer cada Parquet.

```powershell
.venv\Scripts\python.exe src/preparar_variables_gold.py
```

Salidas en una ejecución nueva de `resultados/gold/variables/`, con
`manifiesto.json`, `informe.json` y selector `actual.json`. El selector se
actualiza al terminar las comprobaciones; una carpeta existente no se sobrescribe.
Manifiesto con entradas, código, versiones, periodos, fórmulas, unidades,
limitaciones y entorno. Motor DuckDB con dos hilos, límite de memoria de 1 GB
y desborde temporal en disco; no se añaden dependencias.

### Contrato de las tres tablas nuevas

`gold_referencias_normalizacion`: una fila por dimensión, clave
`(version_gold, dimension)`. Dos dimensiones: `demanda` y `proximidad`.

| Campo | Tipo | Significado |
| --- | --- | --- |
| `version_gold` | VARCHAR | Ejecución del bloque de variables. |
| `dimension` | VARCHAR | Dimensión a la que se aplica la referencia. |
| `nombre_variable` | VARCHAR | Nombre de la variable original. |
| `unidad` | VARCHAR | Vehículos o metros. |
| `escenario_referencia` | VARCHAR | `no_aplica` para demanda; `principal_admitida` para proximidad. |
| `universo_referencia` | VARCHAR | Municipios CV o candidatos CV, sin filtrar por vista. |
| `n_total` | BIGINT | Observaciones del universo, incluidas las no evaluables. |
| `n_validos` | BIGINT | Observaciones finitas y no negativas. |
| `n_nulos` | BIGINT | Observaciones ausentes. |
| `n_invalidos` | BIGINT | Observaciones presentes no admisibles; se mantienen identificadas. |
| `minimo` | DOUBLE | Mínimo admisible, nulo si no existe. Informa sobre variación; no sustituye el anclaje cero. |
| `maximo` | DOUBLE | Referencia M admisible, nula si no existe. |
| `estado_referencia` | VARCHAR | `con_variacion`, `todos_cero`, `sin_variacion_positiva` o `sin_valores_admisibles`. |

`gold_variables_municipio`: una fila por municipio, clave
`(version_gold, codigo_municipio)`. Se conservan todos los municipios de entrada,
incluidos los que no tienen candidatos. Seis columnas:

| Campo | Tipo | Significado |
| --- | --- | --- |
| `version_gold`, `codigo_municipio` | VARCHAR | Ejecución y enlace al contexto municipal de la versión del manifiesto. |
| `vehiculos_distintivo_0` | BIGINT | Valor original conservado. |
| `demanda_normalizada_log` | DOUBLE | Nlog con referencia municipal común. |
| `demanda_normalizada_lineal` | DOUBLE | Contraste lineal con la misma referencia. |
| `estado_normalizacion` | VARCHAR | Estado de cálculo; no sustituye un nulo por cero. |

`gold_variables_candidato`: una fila por candidato y escenario, clave
`(version_gold, candidato_id, escenario)`. Doce columnas:

| Campo | Tipo | Significado |
| --- | --- | --- |
| `version_gold`, `candidato_id`, `escenario` | VARCHAR | Ejecución, identidad OSM conservada y conjunto de oferta. |
| `codigo_municipio_contexto` | VARCHAR | Enlace exclusivo a demanda municipal; nulo en relaciones múltiples. |
| `estado_contexto_municipal` | VARCHAR | Estado de relación heredado de candidatos. |
| `distancia_minima_geometria_m` | DOUBLE | Mínimo desde la geometría original a oferta admisible del escenario. |
| `estado_distancia` | VARCHAR | `calculable`, `sin_superficie_en_cv`, `sin_geometria_admisible` o `sin_recarga_admisible`. |
| `distancia_geometria_borde_cv_m` | DOUBLE | Distancia de la misma geometría al borde de la unión CV; se conserva si falta oferta, nula si el candidato no es evaluable. |
| `posible_influencia_exterior_geometria` | BOOLEAN | Comparación estricta entre las dos distancias; nula si no es posible. |
| `proximidad_normalizada_log` | DOUBLE | Nlog de separación geométrica, mayor valor implica mayor separación, no mejor cobertura. |
| `proximidad_normalizada_lineal` | DOUBLE | Contraste lineal con la misma referencia principal. |
| `estado_normalizacion` | VARCHAR | Estado de cálculo, independiente del aviso de borde. |

Los estados de normalización son `calculable`, `todos_cero`,
`sin_variacion_positiva`, `sin_valor`, `valor_no_admisible`, `sin_referencia`,
`referencia_no_admisible` y `fuera_referencia`. Los tres primeros permiten
valores; los restantes conservan nulos en ambas escalas. Fuera de referencia
no se recorta ni se reajusta M. Los contadores de referencia hacen visibles
las ausencias o entradas inválidas, sin ocultarlas tras un máximo calculable.

La demanda no se duplica en la tabla de candidatos: se consulta mediante
`codigo_municipio_contexto` y la versión municipal del manifiesto. Los vínculos
múltiples siguen disponibles en `gold_candidato_municipio`. Coincidencias,
solapamientos y el aviso del representante se consultan en las tablas anteriores
enlazando con sus versiones declaradas, sin aplicar penalizaciones numéricas.

### Ejecución validada del 21-10-2026

Selector `resultados/gold/variables/actual.json`, ejecución
`20261021T181301489920Z`. Entradas compatibles: contexto municipal
`20261020T153200478279Z`, candidatos `20261020T160709239795Z` y controles
`20261021T154333431064Z`. Se verifican **223 archivos de entrada y código**.

| Tabla | Filas | Columnas |
| --- | ---: | ---: |
| `gold_referencias_normalizacion` | 2 | 13 |
| `gold_variables_municipio` | 542 | 6 |
| `gold_variables_candidato` | 49.131 | 12 |

El bloque añade 31 columnas distribuidas entre tres tablas. Gold reúne
**trece tablas y 135 columnas**, sin sustituir las diez anteriores. Las
referencias verificadas son 10.246 vehículos y 36.628,0631790845 m; ninguna
observación de referencia falta o es inválida en esta ejecución. Se mantienen
los 106 candidatos con contexto múltiple nulo y los 16.271 con contexto exclusivo.

| Escenario | Elementos evaluables | Distancias cero | Mediana, m | Avisos de borde geométrico |
| --- | ---: | ---: | ---: | ---: |
| Principal admitida | 16.377 | 292 | 415,7430 | 3.055 |
| Incluye pendientes | 16.377 | 300 | 406,4281 | 3.017 |
| Incluye ausentes históricas | 16.377 | 300 | 406,1568 | 3.017 |

Suite completa: **194 pruebas correctas, sin omisiones**, en 108,543 segundos,
incluidas veinte de esta etapa. Cubren referencias fijas, ceros, constantes,
nulos, entradas inválidas, falta de oferta, contacto territorial sin superficie,
contexto múltiple, igualdad de borde, cotas inválidas, datos alterados,
compatibilidad de versiones y exportación sin sobrescritura.

Contraste conservado en `resultados/revision_gold/20261021_variables/`:
`comprobar.py` y `comprobacion.json`. Las **49.131 distancias coinciden exactamente
con el ensayo**. Treinta áreas, seleccionadas por orden de ID, se contrastan
además contra distancia al borde completo sin recorte, sin diferencias mayores
de 1e-8 m. Se comprueban cotas respecto al representante y monotonicidad de
avisos al ampliar oferta; se conserva la revisión histórica y su huella.

En el principal, el aviso de borde cambia en 42 elementos respecto al del
representante: 3.055 avisos frente a 3.069. En los otros escenarios cambian
42 y 41, respectivamente. Las dos definiciones se conservan separadas; estos
avisos no prueban presencia de cargadores exteriores. El recorte exacto evita
el coste del cálculo directo del borde para todas las áreas; se mantiene un
contraste directo de muestra y pruebas con geometrías conocidas.

No se altera ninguna fuente, ejecución anterior ni el documento de entrega.
La [comparación de sensibilidad de escalas y escenarios](SENSIBILIDAD_GOLD.md)
ya está completada como trabajo analítico posterior a la preparación.
El diseño del modelo queda pendiente de orientación académica antes de concretar
reglas de combinación y ensayar ponderaciones en ambas escalas y tres escenarios.
El documento de entrega ya describe la preparación vigente; su revisión y envío
se gestionan aparte. El repositorio conserva código, pruebas y documentación;
los datos y los informes detallados permanecen fuera de Git.
