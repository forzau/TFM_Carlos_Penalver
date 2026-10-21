# Revisión territorial de los ejemplos Gold

**20-10-2026. Apta para exploración con reservas; faltan controles antes de priorizar.**
La revisión de contrastes está completada en el alcance indicado. No se observan
discrepancias en los valores recalculados de la muestra. Los indicadores permiten
distinguir situaciones útiles, pero proximidad al punto representativo, oferta
municipal y demanda potencial no deben convertirse directamente en una puntuación.

## Alcance y evidencia

Se revisan doce municipios elegidos por contraste: cuatro grandes núcleos,
casos de baja población, oferta municipal nula, entorno de municipios vecinos,
incertidumbre y cambios entre exportaciones. «Baja población» describe los
casos, no una clasificación rural oficial. La muestra es deliberada, no aleatoria:
no estima el comportamiento de todos los emplazamientos de CV.

Se utilizan la [Gold municipal](GOLD_MUNICIPAL.md), ejecución
`20261020T153200478279Z`, y [candidatos](CANDIDATOS_GOLD.md), ejecución
`20261020T160709239795Z`. No se cambian tablas, versiones, filtros, pesos o fuentes.
Parque 31-12-2025, población Total 2025, renta municipal 2023, OSM 09-09-2026
y adquisición MITECO 18-10-2026: no se presume simultaneidad ni operación actual.

`src/revisar_ejemplos_gold.py` conserva consultas, selección, resultados,
huellas y comprobaciones en `resultados/revision_gold/20261020T162951363910Z/informe.json`.
Se verifican 215 entradas y el código de revisión. Los operandos de parque,
Distintivo 0, población y puntos de los doce municipios se contrastan con Silver.
Se recalculan sus cocientes, manteniendo nulos cuando el denominador es cero.
Para 56 elementos se contrastan las tres distancias, vecinos y empates con
`math.hypot` sobre coordenadas, sin reutilizar el cálculo espacial de distancias
del preparador: **168 comprobaciones coinciden**. Esto es una muestra, no una
revalidación independiente de las 49.131 distancias.

Los recuentos de intersecciones entre áreas, recarga y categorías OSM se calculan
para toda la preselección. Constituyen diagnósticos cartográficos; no son una
visita de campo ni una prueba de identidad de establecimientos o acceso público.

## 1. Contrastes municipales

Distancias planas en metros al inventario principal admitido, sin limitar la
búsqueda al municipio. Solo se agregan elementos con **contexto municipal
exclusivo**; los 106 con varios municipios permanecen fuera de este resumen,
sin borrarlos de Gold. La mediana no pondera población, vehículos ni negocios
únicos: no mide la accesibilidad de los habitantes ni es un indicador de prioridad.

| Municipio | Población 2025 | Distintivo 0 | Puntos admitidos | Elementos con contexto exclusivo | Distancia mínima / mediana / máxima, m |
| --- | ---: | ---: | ---: | ---: | --- |
| València | 841.558 | 10.246 | 655 | 1.043 | 2,7 / 240,9 / 8.261,5 |
| Alacant/Alicante | 365.586 | 6.083 | 252 | 533 | 0,6 / 345,5 / 6.567,5 |
| Elx/Elche | 245.575 | 3.164 | 245 | 476 | 7,6 / 483,6 / 4.469,6 |
| Castelló de la Plana/Castellón de la Plana | 183.709 | 2.246 | 180 | 359 | 3,3 / 373,0 / 4.112,6 |
| Sedaví | 10.862 | 377 | 0 | 14 | 137,7 / 303,9 / 614,3 |
| Quartell | 1.805 | 30 | 0 | 2 | 307,2 / 460,7 / 614,3 |
| Alfafar | 22.266 | 449 | 76 | 70 | 11,2 / 279,6 / 3.666,3 |
| Alcalà de Xivert | 7.489 | 72 | 1 | 103 | 25,2 / 6.433,3 / 7.707,7 |
| Chiva | 18.122 | 439 | 16 | 26 | 12,5 / 463,3 / 4.916,0 |
| Palanques | 34 | 0 | 0 | 1 | 35.783,3 / 35.783,3 / 35.783,3 |
| Zorita del Maestrazgo | 120 | 1 | 0 | 4 | 36.457,5 / 36.521,8 / 36.639,6 |
| Puebla de San Miguel | 53 | 65 | 0 | 2 | 9.991,5 / 10.210,0 / 10.428,5 |

Los núcleos grandes muestran dispersión local: una mediana pequeña puede
convivir con elementos bastante más alejados. Eso permite revisar situaciones
dentro del municipio, pero no demuestra una bolsa de población sin servicio.

**Sedaví y Quartell muestran por qué cero puntos admitidos en el municipio
no significa mala proximidad a toda la oferta.** No procede asignarles prioridad
máxima por ese cero. La presión municipal queda nula, con su estado explícito;
las distancias vecinas aportan una dimensión distinta, sin demostrar suficiencia.

**Palanques y Zorita muestran la tensión entre baja demanda registrada y
distancia elevada.** Palanques tiene Distintivo 0 igual a cero en la fuente,
no demanda de recarga demostrada igual a cero. Accesibilidad territorial y
volumen potencial son objetivos distintos: su importancia requiere una decisión
explícita, no un peso deducido de esos dos ejemplos.

Puebla de San Miguel tiene 65 vehículos Distintivo 0 y 53 habitantes. Los
valores coinciden con Silver; vehículos registrados y personas son poblaciones
distintas. No se demuestra un error por superar un recuento al otro, ni se
puede afirmar por ello una adopción residencial extraordinaria. Su renta nula
se conserva: no debe excluirse o penalizarse el municipio.

## 2. Sensibilidad a pendientes y ausencias

En **Consum de Alcalà de Xivert**, la distancia principal es **6.795,6 m**.
Al añadir las posiciones publicadas de pendientes baja a **29,9 m**, con vecino
`2024005420`. Su presencia en la copia no resuelve su asignación o posición
física. La diferencia es demasiado relevante para ocultar el escenario alternativo
o describir esa ubicación como claramente alejada de toda recarga.

En **Ignacio, Chiva**, la distancia con todas las instalaciones presentes es
**1.253,9 m**. Añadir el registro histórico ausente `2024003909` la reduce a
**67,5 m**. El escenario no acredita que el cargador haya cerrado o siga operativo.
No se suma a la oferta principal. En ambos casos deben mostrarse los vecinos
y estados que explican la diferencia, sin convertirla en probabilidad o penalización.

## 3. Un área puede intersectar recarga aunque su punto esté alejado

En **292 áreas** de la preselección intersecta al menos una coordenada de
instalación presente y admitida. La distancia desde el representante sigue
siendo positiva; el máximo es **206,7 m**. No es un error de cálculo: el punto
interior resume una superficie y no tiene por qué coincidir con el cargador.

El área **Centro Comercial Bonaire**, de unos 356.622 m², intersecta dos
coordenadas de instalación admitida; su representante queda a 206,7 m de la
instalación más cercana. La intersección no certifica plazas o acceso compartidos,
pero impide leer esa distancia como «el centro comercial no tiene recarga».

**Antes de usar proximidad como carencia se necesita un diagnóstico de
intersección área–recarga**, con IDs y escenario. Una distancia mínima al área
puede acompañarlo como sensibilidad geométrica, conservando la distancia al
punto y sin confundir ninguna de ellas con acceso real.

## 4. Varias representaciones y municipios

En **El Corte Inglés de Elx/Elche**, un punto y un área con indicios de
correspondencia tienen representantes separados 85,0 m. Sus distancias a recarga
principal son 245,2 y 307,7 m. Contarlos como dos negocios o elegir ambos como
emplazamientos independientes carece de respaldo; fusionarlos automáticamente
tampoco está justificado por los indicios disponibles.

La revisión añade **483 pares de intersección entre categorías distintas**:
467 elementos de aparcamiento y 337 de comercio o alojamiento. No aparecen en
los 75 pares actuales porque estos comparan punto y área de la misma categoría.
Los 483 pares no se restan de los elementos para obtener lugares únicos; una
intersección no acredita pertenencia, acceso o identidad.

También hay dos áreas `mall` de nombres Bonaire y Centro Comercial Bonaire:
la mayor cubre completamente a la menor, de unos 65.628 m². El cruce punto–área
no detecta este caso área–área. Puede representar objetos relacionados de distinta
extensión; no se declara duplicado ni se elimina una geometría.

Ambas áreas intersectan **Aldaia y Quart de Poblet**. Conservar los dos vínculos
y dejar nulo el municipio exclusivo es correcto. No procede asignarlas por
el municipio del punto interior o repartir entre ellas el parque de los municipios.

**Antes de seleccionar lugares físicos se necesitan relaciones de solapamiento
entre categorías y representaciones**, manteniendo los elementos y una revisión
posterior de identidad. No basta con descontar los pares punto–área existentes.

## 5. Borde del inventario y ausencia de POI

Un aparcamiento de **Zorita del Maestrazgo** está a **41,5 m del borde de la
referencia CV**, mientras su vecino más cercano del inventario principal queda
a **36.639,6 m**. Puede existir oferta más cercana fuera de CV: esta revisión
no la ha comprobado. Es un mínimo del inventario preparado, no la distancia
acreditada al cargador más cercano de cualquier territorio. El extremo no debe
liderar una prioridad por cobertura sin resolver o señalar ese límite.

Se propone un aviso geométrico de posible influencia exterior cuando la
distancia a recarga del inventario exceda la distancia al borde de CV. Es una
condición conservadora de posible omisión, no prueba de un cargador exterior;
también puede activarse cerca de costa. Para confirmar accesibilidad en esos
casos habrá que ampliar y validar la oferta de referencia pertinente.

Hay **52 municipios sin elementos OSM preseleccionados**, pero conservan su
contexto municipal. Por ejemplo, **Cañada** tiene 52 vehículos Distintivo 0 y
dos puntos admitidos; **Polinyà de Xúquer**, 32 vehículos y cero puntos admitidos.
Ninguno tiene un candidato de las categorías elegidas en esta copia. No deben
desaparecer de la comparación de zonas ni recibir una distancia cero o infinita.
Necesitarían buscar y comprobar emplazamientos por otra vía si la zona resultase
de interés; ausencia de POI no es ausencia real de sitios.

## Resultado y siguiente paso

La estructura de siete tablas y sus indicadores se mantiene. Esta revisión
añade evidencia e interpretación, sin modificar Gold ni corregir fórmulas que
han resultado coherentes en la muestra. Los límites encontrados impiden tratar
el mínimo geométrico como un déficit de servicio o como un ranking listo.

Antes de normalizar y ponderar conviene preparar tres controles:

1. Coincidencia de coordenadas de recarga con las áreas candidatas, por escenario.
2. Relaciones de solapamiento relevantes entre candidatos, incluidas categorías
   distintas y área–área, sin fusión automática.
3. Posible influencia de oferta exterior al inventario, manteniendo visible
   la sensibilidad ya calculada a pendientes y ausencias.

Después se puede definir la comparación de zonas separando demanda potencial
y proximidad, conservando todos los municipios y su incertidumbre. No se fijan
pesos, radios o una regla de suficiencia por esta revisión.

## Cobertura de la revisión

Inventario acotado a los siete bloques anteriores. Los totales siguientes son
unidades de revisión, no porcentajes de exactitud ni garantía de validación
física. **0/N significa que no se observaron errores pendientes en ese alcance**;
las reservas de adecuación para priorizar se explican arriba. Se mantiene un
registro local de cobertura generado con la evidencia y las consultas.

Calidad y utilidad del documento de revisión:

| Categoría | Defectos observados | Valoración |
| --- | --- | --- |
| Utilidad y completitud | 0/2 | Se responde si sirven para explorar y qué falta para priorizar; no se entrega un ranking. |
| Claridad analítica | 0/7 | Cada bloque distingue cálculo, interpretación y límite. Muestra deliberada y periodos explícitos. |
| Interacción y coherencia visual | N/A | Documento técnico sin dashboard, controles interactivos o figuras. |

Corrección y robustez:

| Categoría | Defectos observados | Valoración |
| --- | --- | --- |
| Autoridad y confianza de las fuentes | 0/7 | Copias y versiones fijadas; autoridad limitada a registros e indicios cartográficos, sin comprobación física. |
| Exactitud de valores | 0/7 | Doce municipios contrastados con Silver; 168 distancias de 56 elementos recalculadas independientemente; diagnósticos por consulta. |
| Coherencia dentro de gráficos | N/A | No hay gráficos. |
| Detalle de fuentes | 0/7 | Consultas, selección, huellas y resultados conservados por bloque; fuentes y periodos identificados. |
| Consistencia entre componentes | 0/7 | Ejemplos y recuentos concordantes con las Gold utilizadas; no se suman entidades solapadas. |
| Controles de calidad | 0/7 | Nulos, pendientes, ausencias, representación y límite territorial interpretados explícitamente. |
| Soporte de conclusiones | 0/7 | Se concluye utilidad exploratoria y necesidad de controles; no suficiencia, operación o aptitud. |

No se comprueban oferta exterior a CV, visitas, acceso, suelo, permisos,
conexión, demanda observada o tiempos por red. No se ha repetido la suite previa
de 156 pruebas porque no se modifica el código de los preparadores; el nuevo
script ejecuta las comprobaciones específicas de esta revisión.

Reproducción desde las copias conservadas, sin red o nuevas dependencias:

```powershell
.venv\Scripts\python.exe src/revisar_ejemplos_gold.py
```

Los resultados y la cobertura quedan fuera de Git; código y documentación
están guardados localmente, todavía sin commit ni publicación en GitHub.
