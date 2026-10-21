# Sensibilidad de escalas y escenarios, antes de ponderar

**21-10-2026. Comparación analítica posterior a la preparación de datos.**
Bronze, Silver y la estructura Gold están preparadas; este contraste no es un
requisito pendiente de Entrega 02. Se conservan las trece tablas y sus valores.
No se calculan pesos, una prioridad combinada, predicción de uso o selección de sitios.

## Pregunta y método

Se estudian por separado dos decisiones: cómo cambia la separación entre valores
al usar escala logarítmica o lineal, y cuánto cambia la proximidad al ampliar la
oferta registrada. Son dimensiones distintas: demanda potencial de 542 municipios
y distancia de 16.377 candidatos a la geometría original, en tres escenarios.
La demanda no se distribuye entre POI ni se multiplica para ajustar la referencia.
Los 106 contextos municipales múltiples siguen en la comparación de proximidad.

Se reutilizan las [variables Gold](VARIABLES_NORMALIZACION_GOLD.md) validadas,
con referencias fijas de 10.246 vehículos y 36.628,0631790845 m. Logarítmica:
`ln(1+x)/ln(1+M)`; lineal: `x/M`, con vehículos y metros como unidades explícitas.
No se recalculan distancias, geometrías o referencias por escenario o filtro.

Se usan distribuciones completas, no una muestra: percentiles, cambios pareados
y orden descendente de cada variable. Los empates reciben rango promedio para
Spearman. Para explorar el grupo superior se toma el 10% nominal de mayor
distancia, incluyendo todos los empates del corte; es un diagnóstico de
estabilidad, sin radio de servicio, umbral de necesidad o propuesta de inversión.
Desconocidos se cuentan y excluyen del par, sin imputación; los órdenes de escalas
usan las mismas observaciones con las dos normalizaciones conocidas. En esta
ejecución todos los pares están completos.

## 1. Las escalas conservan el orden, pero cambian las separaciones

Las dos funciones son crecientes. En los datos almacenados no aparece ningún
cambio de puesto entre valor original, logarítmica y lineal: Spearman igual a
1 en demanda y en cada escenario de proximidad. Esto no demuestra que una
transformación sea mejor ni que produzcan la misma prioridad al combinarlas.

| Distribución | Mediana lineal | Mediana logarítmica | Percentil 95 lineal | Percentil 95 logarítmico |
| --- | ---: | ---: | ---: | ---: |
| Demanda, 542 municipios | 0,001952 | 0,329681 | 0,053762 | 0,683644 |
| Distancia principal, 16.377 candidatos | 0,011350 | 0,574051 | 0,151546 | 0,820460 |

La mayoría de observaciones queda cerca del cero en la escala lineal, respecto
a sus máximos de referencia. La logarítmica expande la zona de valores bajos
y comprime diferencias altas. No se comparan las dos medianas de distintas
dimensiones como si procedieran de una misma población: una es municipal y
la otra describe elementos candidatos, con posible solapamiento cartográfico.

Ejemplo de la misma observación: Quartell tiene 30 vehículos Distintivo 0;
su valor lineal es 0,002928 y el logarítmico 0,371855. El municipio no cambia
de posición al transformar la demanda, pero sí cambia su separación respecto
a otros valores. No significa que tenga un 37% de necesidad o cobertura.

**Implicación:** conservar las dos escalas al ensayar ponderaciones. Un peso
60/40 no conserva el mismo valor marginal por vehículo o metro cuando cambia
la transformación. Elegir solo por estabilidad del orden de una dimensión
no resuelve esa preferencia; tampoco hay uso observado para calibrarla como
probabilidad o calidad predictiva.

## 2. Efecto de los conjuntos de oferta

Comparaciones sobre los mismos 16.377 candidatos, sin filtro municipal para el
vecino. Cambio de distancia: reducción mayor de 1e-8 m, tolerancia numérica;
las reducciones son de separación cartográfica, sin intervención real.

| Cambio de escenario | Candidatos cuya distancia cambia | Proporción | Mediana de reducción entre afectados, m | Reducción máxima, m | Nuevas distancias cero |
| --- | ---: | ---: | ---: | ---: | ---: |
| Principal → incluye pendientes | 521 | 3,181% | 459,82 | 6.801,27 | 8 |
| Incluye pendientes → añade ausentes históricas | 33 | 0,202% | 7,33 | 1.213,83 | 0 |
| Principal → incluye pendientes y ausentes | 551 | 3,364% | 364,12 | 6.801,27 | 8 |

Los grupos no son excluyentes: tres candidatos cambian en ambos pasos;
`521 + 33 - 3 = 551`. Al comparar principal con el conjunto más amplio,
15.826 candidatos (96,636%) conservan su distancia dentro de esa tolerancia.
La mediana de reducción sobre **todos** los candidatos es cero en las tres
comparaciones; presentarla sola ocultaría cambios locales importantes.
Los ocho nuevos ceros corresponden a coincidencia con áreas; no certifican
acceso, funcionamiento o suficiencia de la oferta.

Ejemplos de la misma geometría y copias conservadas:

| Candidato | Comparación | Distancia base, m | Distancia ampliada, m | Diferencia entre valores normalizados: log / lineal |
| --- | --- | ---: | ---: | ---: |
| Área de aparcamiento sin nombre, Alcalà de Xivert, fid 5602 de la capa de tráfico/áreas | Principal → pendientes | 6.848,15 | 46,88 | 0,472301 / 0,185685 |
| Área Consum, Alcalà de Xivert, fid 7875 de POI/áreas | Principal → pendientes | 6.769,54 | 5,43 | 0,662238 / 0,184670 |
| Área de aparcamiento sin nombre, Chiva, fid 4304 de tráfico/áreas | Pendientes → ausentes | 1.216,52 | 2,69 | 0,551856 / 0,033139 |

Son elementos OSM, no negocios distintos acreditados. Los ejemplos se seleccionan
por grandes reducciones, no aleatoriamente; el informe conserva los IDs completos.
La ausencia histórica no confirma un cierre, y añadir pendientes no resuelve su
asignación municipal. Se mantienen como escenarios, sin promediarlos o asignarles
probabilidades. Las cifras de esta sección utilizan geometría original: no deben
confundirse con las distancias previas desde el representante.

## 3. Orden de proximidad y estabilidad local

El orden es de **mayor separación**, sin demanda o pesos. No es un ranking de
prioridad de instalación.

| Comparación | Spearman | Mediana de cambio absoluto de puesto | Máximo cambio de puesto | Coincidencia en grupo superior |
| --- | ---: | ---: | ---: | ---: |
| Principal → pendientes | 0,981492 | 127 | 15.383 | 1.525 de 1.638 (93,101%) |
| Pendientes → ausentes | 0,999605 | 2 | 12.542 | 1.638 de 1.638 (100%) |
| Principal → conjunto más amplio | 0,981096 | 128 | 15.381 | 1.525 de 1.638 (93,101%) |

El grupo superior contiene 1.638 elementos en cada escenario en esta ejecución.
El Jaccard de sus conjuntos es 0,870931 entre principal y ampliados, y 1 entre
los dos ampliados. Coincidencia respecto al grupo base y Jaccard tienen distintos
denominadores; no se presentan como la misma medida.

15.994 posiciones cambian al añadir pendientes, aunque solo 521 distancias
se modifican. Un cambio de distancia desplaza también a elementos que pasan
a quedar por delante o detrás: **puesto cambiado no equivale a dato cambiado**.
Los grandes máximos locales pueden coexistir con correlación global alta.
La estabilidad de este grupo no se traslada automáticamente a una futura
prioridad combinada o a la elección conjunta de emplazamientos.

## Reproducción, comprobaciones y siguiente paso

```powershell
.\.venv\Scripts\python.exe src/comparar_sensibilidad_gold.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_sensibilidad_gold.py -v
```

El script comprueba estado, versiones y huellas antes de leer, y vuelve a
comprobarlas al cerrar. Usa DuckDB y la biblioteca estándar, sin nuevas
dependencias. Escribe una ejecución bajo `resultados/sensibilidad_gold/`, con
informe JSON, consultas, referencias, ejemplos y metodología. No cambia Gold
ni sus selectores. Las tablas exactas de comparación bastan para este contraste;
no se añade una aplicación o una dependencia de gráficos.

Ejecución: `20261021T184721005132Z`; entrada Gold variables
`20261021T181301489920Z`, contexto municipal `20261020T153200478279Z` y candidatos
`20261020T160709239795Z`. Se verifican 230 archivos de entrada y código.
El contraste independiente en Python se conserva en
`resultados/sensibilidad_gold/revision_20261021/`: reproduce sobre todos los
pares conocidos los cambios de distancia, rangos promedio, Spearman y grupos
superiores, y comprueba los tres casos compartidos. Las pruebas incluyen
empates, constantes, nulos, ausencia total, escenarios incompletos, valores
inválidos y ampliaciones que aumentarían una distancia.
La suite completa pasa **205 pruebas, sin omisiones**, en 117,287 segundos,
incluidas once de esta comparación.

Conclusión de trabajo: las variaciones globales de inventario afectan a una
minoría de distancias, con casos locales que requieren revisión; la elección
de escala cambia mucho los valores que entrarían en una combinación. Se
mantienen la logarítmica como base de ensayo y la lineal como contraste,
sin declararlas validadas por uso real ni fijar pesos definitivos.
Continuación propuesta, pendiente de orientación académica: concretar las reglas
de combinación y después ensayar 50/50, 60/40 y 70/30 en ambas escalas y los tres escenarios,
con estados explícitos para candidatos sin contexto municipal exclusivo y sin
convertir elementos OSM en emplazamientos viables confirmados.
