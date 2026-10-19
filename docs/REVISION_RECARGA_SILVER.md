# Revisión de las asignaciones municipales de recarga

Fecha: **18-10-2026**. Ampliación de la revisión de Silver antes de Gold.

Se resuelven **80 de las 132 asignaciones que estaban pendientes** (60,6 %),
correspondientes a **264 de 435 puntos** (60,7 %) y **300 de 491 conectores**
(61,1 %). Junto con el caso anterior de Consum Ángel Guimerá, hay **81 de
133 conflictos originales resueltos**. Permanecen **52 instalaciones, 171 puntos
y 191 conectores** con asignación municipal pendiente.

| Entidad | Conservadas | Relación municipal admitida | Pendiente |
| --- | ---: | ---: | ---: |
| Instalaciones | 1.526 | 1.474 | 52 |
| Puntos | 4.402 | 4.231 | 171 |
| Conectores | 5.244 | 5.053 | 191 |

La relación vigente es `validacion_conjunta/recarga_municipio_validado`.
La capa espacial y sus 1.393 admisiones iniciales conservan su estado histórico.
No se mueve ninguna coordenada, se sustituye ningún municipio de origen ni se
eliminan los registros pendientes. No se suman potencias como capacidad simultánea.

## Tratamiento de los pendientes al plantear Gold

Desde el 19-10-2026 se mantiene la revisión de los **52 casos pendientes** en
espera, con sus atributos, candidatos municipales y evidencia disponibles.
Se conserva la relación de 1.474 instalaciones admitidas, separada de los casos
sin asignación municipal confirmada. No se fuerza una resolución para avanzar.

En Gold se prevé hacer visible esta limitación, por ejemplo con una etiqueta
**«Zona con incertidumbre en la asignación de puntos de recarga»**. La incidencia
es la correspondencia municipal pendiente: existen registros de instalaciones
y cargadores, aunque no esté confirmado a qué municipio deben atribuirse.
No equivale a ausencia de recarga ni a falta general de datos en toda la zona.

La unidad territorial, la regla para señalar zonas afectadas y el efecto sobre
indicadores o comparaciones se definirán al diseñar Gold. Se distinguirán datos
confirmados y pendientes, sin convertir estos últimos en cero ni presentar
un recuento municipal admitido como inventario completo. La etiqueta es una
propuesta de comunicación; todavía no constituye una variable Gold implementada.

## Fuentes y criterio de revisión

Se han consultado fichas primarias de APK2, Interparking, Repsol y Consum,
el mapa propio de Iberdrola | bp pulse y las páginas de contacto de La Galiana
Golf Resort y Ferrero Tennis Academy. Se revisa explícitamente la correspondencia
de nombre, dirección, establecimiento y municipio; las variantes de acceso o
numeración permanecen visibles en el registro de decisiones y no se normalizan
como si se hubiera acreditado un portal exacto.

También se contrastan direcciones con [CartoCiudad, IGN/CNIG](https://www.cartociudad.es/web/portal/directorio-de-servicios/geoprocesamiento).
Las búsquedas son directas por la dirección y el código postal de MITECO, sin
filtrar por el municipio candidato ni buscar por las coordenadas del cargador.
Se retienen copias de los resultados, consultas y recibos con fecha y SHA-256.
Los portales se revisan por calle, número y, cuando existe, extensión. Los
viales se admiten solo tras revisión textual y sin candidatos en municipios
distintos. No se utilizan los POI de recarga de CartoCiudad como prueba
independiente: su fuente es el Geoportal de Hidrocarburos de MITECO.

Atribución CartoCiudad: **CC BY 4.0 — IGN/CNIG, www.scne.es/productos.html#CartoCiudad**.

| Evidencia de las 81 resoluciones acumuladas | Instalaciones | Alcance |
| --- | ---: | --- |
| Ficha de establecimiento | 19 | Dirección/municipio del establecimiento; precisión del cargador no certificada. |
| Registro del operador | 9 | Dirección/municipio del establecimiento; precisión del cargador no certificada. |
| Contacto del establecimiento | 2 | Dirección/municipio del establecimiento; precisión del cargador no certificada. |
| Portal oficial | 30 | Dirección y número de portal; posición del cargador no certificada. |
| Vial oficial | 20 | Referencia municipal del vial; número de portal no verificado. |
| Revisión visual y fuente primaria | 1 | Municipio del emplazamiento identificado; sin certificación individual de las plazas. |

La admisión es **municipal**. La evidencia actual no acredita operación en una
fecha histórica, exhaustividad del registro, accesibilidad efectiva o precisión
de las plazas. Un vial no equivale a verificar un portal ni el cargador. Los
centroides o coordenadas comerciales no reemplazan las coordenadas MITECO.
Si una ficha o un portal publica coordenadas que contradicen el municipio
propuesto, la admisión se rechaza. La proximidad nunca basta por sí sola.

## Comprobación de una exportación oficial nueva

Se obtuvo una nueva exportación CSV de RIPREE por su [página oficial de descarga](https://energia.serviciosmin.gob.es/Ripree/ExportarInstalaciones/Export).
El 18-10-2026 contiene 42.772 registros de conector nacionales. Se localizan
131 de los 132 identificadores pendientes; **ninguno de esos 131 cambia el
municipio declarado**. La instalación `2024004024` no aparece en esta nueva copia.
Su ausencia no prueba cierre ni se elimina del inventario histórico.
La exportación nueva queda como contraste y no sustituye Bronze ni Silver.
El enlace de catálogo devuelve HTML: el CSV real se obtiene mediante la
petición de exportación que utiliza la propia página, cuyo recibo se conserva.

## WS Alfafar: relación municipal admitida tras revisión visual

El [panorama de Street View](https://maps.app.goo.gl/hyNwBW5QX2itAWHT6), de julio
de 2026, permite identificar el recinto de las dos marquesinas. La correspondencia
del solar se comprobó en vista satélite y en la ortofoto PNOA de mayo de 2024
(resolución publicada de 0,25 m), que aún muestra el solar sin las marquesinas.
La ortofoto sirve para situar el solar, no para verificar los cargadores actuales.

El contraste con los recintos Silver sitúa la cámara de Street View en Alfafar
y la referencia MITECO del interior del recinto en Massanassa, a unos 10,22 m
del límite. La frontera atraviesa la franja frontal del solar; un portal de
acceso puede referirse a Alfafar sin determinar el municipio del emplazamiento.
La [publicación primaria de Wenea](https://es.linkedin.com/posts/wenea_ws-alfafar-activity-7509175029159452672-3dLC)
identifica expresamente WS Alfafar en Massanassa. Esta combinación de identidad
visual, referencia espacial y declaración primaria permite admitir **Massanassa**
para la instalación, con método `revision_visual_y_documental`.

Se conservan los 22 puntos y 22 conectores de MITECO. La observación de 11 equipos
es compatible con dos salidas por equipo, pero no se utiliza como prueba de ese
recuento. La revisión no certifica individualmente la posición municipal de cada
plaza ni cambia coordenadas, dirección o municipio de origen. Las capturas,
metadatos PNOA, contraste y revisión explícita se conservan por huella fuera de Git.

## Casos reservados para revisión manual

- **SEUR Alaquàs** (`QTWJBKDAJQQGEJKRFLFD`), 22 puntos/conectores de 11 kW.
  Dirección: Camí del Mas de Moret. Coordenada: `39.449380, -0.492790`;
  cae en Aldaia a unos 83,49 m de Alaquàs. CartoCiudad registra el vial en
  Aldaia con entidad de población Alaquàs. Falta localizar las plazas dentro
  del aparcamiento SEUR mediante la ficha de Repsol/Waylet o evidencia del recinto.
- **Consum Catadau** (`2024007279`), dos conectores. La dirección oficial dice
  Catadau pero las coordenadas de la tienda caen en Llombai. Se conserva la
  decisión no concluyente de la revisión anterior.

Para la revisión manual:

1. Buscar **SEUR Alaquàs** en Repsol/Waylet o fuentes del propio recinto.
2. Comparar la ubicación y fotos de sus fichas con las posiciones registradas:
   [SEUR Alaquàs](https://www.google.com/maps?q=39.449380,-0.492790).
3. Identificar la zona de las plazas de recarga dentro del aparcamiento,
   distinguiéndola del acceso, edificio o marcador general del negocio.
4. Conservar enlace de la ficha, dirección completa y coordenadas disponibles.
   Una imagen donde se señale la zona de carga también permite contrastarla.
   La información se usará después para comprobar el límite municipal; quien
   revisa no necesita decidir por su cuenta el municipio.

No se debe decidir por el nombre comercial, código postal, localidad postal
o marcador de entrada. La revisión manual debe identificar físicamente la
zona de carga; después se contrasta el municipio con los recintos oficiales.

## Asignaciones adicionales admitidas

Las 80 filas siguientes complementan la resolución anterior de Consum Ángel
Guimerá. «Municipio» es la relación admitida; los textos originales permanecen
en las tablas de origen. Las copias completas y decisiones están en resultados,
excluidos de Git. Los enlaces permiten inspeccionar la fuente pública.

| Instalación / ID | Municipio declarado → admitido | Puntos / conectores | Evidencia |
| --- | --- | ---: | --- |
| WS Alfafar / `GMEXBAT0FY7NUQDR9TGI` | Alfafar → Massanassa | 22 / 22 | [Revisión visual](https://maps.app.goo.gl/hyNwBW5QX2itAWHT6) y fuente primaria Wenea |
| Hospital General Universitario / `KG69BYNPRIPRAQC5IH5T` | Xirivella → València | 14 / 14 | [Ficha de establecimiento](https://apk2gestion.com/es/parking/hospital-general-universitario) |
| Valencia - Santa María Micaela / `6JFUCPFTGCUTTKXS8EXL` | Moixent/Mogente → València | 10 / 10 | [Ficha de establecimiento](https://www.interparking.es/en/parkings/valencia/santa-maria-micaela/) |
| Abastos / `P4M8LQKNSYPIFBSP0FCB` | Moixent/Mogente → València | 9 / 9 | [Ficha de establecimiento](https://apk2gestion.com/es/parking/abastos) |
| V-Valencia-018 / `2024001053` | Xirivella → València | 8 / 8 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Pedrapiquers+14&cod_postal_filter=46014&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-V-Valencia-051 / `2024002136` | Almussafes → València | 8 / 8 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=De+Las+Ferias+1&cod_postal_filter=46035&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-V-Valencia-071 / `GTTHNNEVYGQEKZI3XJ2L` | Moixent/Mogente → València | 8 / 8 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Juan+De+Mena+23&cod_postal_filter=46008&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| La Galiana Golf Resort / `KLBAULZTJAOG5YDHJTJ8` | Alzira → Carcaixent | 8 / 8 | [Contacto del establecimiento](https://lagalianagolfresort.com/contacto/) |
| Vidanova Parc - Norte / `2023002199` | Petrés → Sagunt/Sagunto | 4 / 8 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Avda.+De+Les+Moreres&cod_postal_filter=46500&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-CS-CastellonDeLaPlana-016 / `2024002341` | Alcora, l' → Castelló de la Plana/Castellón de la Plana | 6 / 6 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Ferrandis+Salvador&cod_postal_filter=12100&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-A-SantJoanD'Alacant-005 / `2024002466` | Alacant/Alicante → Sant Joan d'Alacant | 6 / 6 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Benidorm+25&cod_postal_filter=03550&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-CS-ElGrao-moncofa-001 / `UZLB99POJF18DIJDSEM1` | Chilches/Xilxes → Moncofa | 6 / 6 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Cient%C3%ADfic+Avel%C2%B7Li+Corm+8&cod_postal_filter=12593&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| Ferrero Tennis Academy / `YFTGIYQPT115I7QPNGG4` | Cañada → Villena | 6 / 6 | [Contacto del establecimiento](https://ferreroacademy.com/en_en/contacto/) |
| A-SanFulgencio-001 / `2024000942` | Daya Vieja → San Fulgencio | 4 / 6 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Mar+Tirreno&cod_postal_filter=03177&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| JV_DISFRIMUR San Isidro 01 / `2025000470` | Cañada → San Isidro | 4 / 6 | [Registro del operador](https://iberdrola-bppulse.es/mapa-iberdrola/api/puntos.php) |
| CS-Castellondelaplana-005 / `2024000294` | Alcora, l' → Castelló de la Plana/Castellón de la Plana | 4 / 5 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Buenavista&cod_postal_filter=12100&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| CS-Viver-001 / `2024000710` | Navajas → Viver | 4 / 5 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Valencia+16&cod_postal_filter=12460&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| SM Consum - San Joan Av. Muchamiel 141 / `2023002739` | Alacant/Alicante → Sant Joan d'Alacant | 4 / 4 | [Ficha de establecimiento](https://www.consum.es/supermercados/sant-joan-av-mutxamel/) |
| V-VALENCIA-016 / `2024001910` | Moixent/Mogente → València | 4 / 4 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Literato+Gabriel+Miro+61&cod_postal_filter=46008&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-V-SanAntonioDeBenageber-001 / `2024001911` | Vallés → San Antonio de Benagéber | 4 / 4 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Puput+51&cod_postal_filter=46184&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| A-Rojales-002 / `2024002246` | Formentera del Segura → Rojales | 4 / 4 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Quesada+Ballester+1&cod_postal_filter=03170&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| V-SAGUNTO-009 / `2024002300` | Petrés → Sagunt/Sagunto | 4 / 4 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=San+Cristobal+10&cod_postal_filter=46500&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| Mercadona, Alcalde Fernando Alemany, Alicante / `6X0HDBMOUH3CFIHV7UUB` | Dénia → Pego | 4 / 4 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Avda.+Alcalde+Fernando+Alemany&cod_postal_filter=03780&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-V-Benimamet-006 / `FW0C50GG2K2BPELRRC8Z` | Almussafes → València | 4 / 4 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Felipe+Valls+6&cod_postal_filter=46035&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| Repsol, Hotel RH Silene (Parking Público) / `JUQEDAIA0JVHZD9ESBXS` | Alcora, l' → Castelló de la Plana/Castellón de la Plana | 4 / 4 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Santa+Cristina+3&cod_postal_filter=12100&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| 61945052670005 / `2023003988` | Xirivella → València | 3 / 3 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Avinguda+De+Jos%C3%A9+Roca+Coll&cod_postal_filter=46014&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| Consum - Burriana / `2025000654` | Benicarló → Borriana/Burriana | 3 / 3 | [Registro del operador](https://iberdrola-bppulse.es/mapa-iberdrola/api/puntos.php) |
| Consum - Villar del Arzobispo / `1UTZ8GMT81KEAHS0EJTP` | Andilla → Villar del Arzobispo | 2 / 3 | [Registro del operador](https://iberdrola-bppulse.es/mapa-iberdrola/api/puntos.php) |
| A-PilardelaHoradada-005 / `2024000287` | Elx/Elche → Pilar de la Horadada | 2 / 3 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Atenas+3&cod_postal_filter=03191&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| A-Orihuela-006 / `2024000391` | Torrevieja → Orihuela | 2 / 3 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Lago+Ba%C3%B1olas&cod_postal_filter=03186&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| A-Petrer-001 / `2024002115` | Elda → Petrer | 2 / 3 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Mediterraneo+137&cod_postal_filter=03600&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| A-Almoradi-001 / `2024004746` | Algorfa → Almoradí | 2 / 3 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Principe+De+Espa%C3%B1a&cod_postal_filter=03169&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-A-ElVerger-001 / `DL52MCMTKO9ZJG5QXXSG` | Dénia → Verger, el | 2 / 3 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Escoles+20&cod_postal_filter=03770&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| SM Consum - Heroes de la Cabeza 50 / `2023002720` | Xirivella → València | 1 / 3 | [Ficha de establecimiento](https://www.consum.es/supermercados/valencia-heroes-virgen-de-la-cabeza/) |
| Repsol ES, CRED Requena / `68HA53KBLUOO36XAFTCI` | Cofrentes → Requena | 1 / 3 | [Ficha de establecimiento](https://www.repsol.es/buscador-eess-y-puntos-de-recarga/valencia/requena/ctra-n-3-km-2755/) |
| Repsol ES, Onda / `A22P3RPTEJTBBYZYHBVV` | Betxí → Onda | 1 / 3 | [Ficha de establecimiento](https://www.repsol.es/buscador-eess-y-puntos-de-recarga/castellon/onda/cr-cv-20-pk-49/) |
| Repsol ES, Nolasco, S.L / `JLBA42YXOHXPN5TBVXUN` | Ador → Palma de Gandía | 1 / 3 | [Ficha de establecimiento](https://www.repsol.es/buscador-eess-y-puntos-de-recarga/valencia/ador-palma-de-gandia/cr-cv-60-pk-35/) |
| Repsol ES, Mari I Soucase S.L / `KOASNCBAEOBZMCX5H5F0` | Albal → Catarroja | 1 / 3 | [Ficha de establecimiento](https://www.repsol.es/buscador-eess-y-puntos-de-recarga/valencia/catarroja/av-generalidad-valenciana-n-20/) |
| Repsol ES, M. Isabel Belda / `L25MTSFDVZCN6JUIUY0R` | Alcàsser → Picassent | 1 / 3 | [Ficha de establecimiento](https://www.repsol.es/buscador-eess-y-puntos-de-recarga/valencia/picassent/cl-palleter-10/) |
| Repsol ES, CRED Jaime I / `U9TM5TSMF3W5TRNGP9ME` | Benicarló → Borriana/Burriana | 1 / 3 | [Ficha de establecimiento](https://www.repsol.es/buscador-eess-y-puntos-de-recarga/castellon/burriana/cl-avenida-jaime-chicharro-6/) |
| Repsol ES, Combustibles Picassent / `WE4E2SCF9BRR6HLFNLCY` | Alcàsser → Picassent | 1 / 3 | [Ficha de establecimiento](https://www.repsol.es/buscador-eess-y-puntos-de-recarga/valencia/picassent/cl-abadia-13/) |
| Repsol ES, CRED Archiduque Carlos / `XL6KBDQCAEOR5OUKUUGJ` | Xirivella → València | 1 / 3 | [Ficha de establecimiento](https://www.repsol.es/buscador-eess-y-puntos-de-recarga/valencia/valencia/cl-archiduque-carlos-70/) |
| APK2 Pintor Navarro / `2023002285` | Moixent/Mogente → València | 2 / 2 | [Ficha de establecimiento](https://apk2gestion.com/es/parking/abastos) |
| APK2 Hospital General Valencia / `2023002286` | Xirivella → València | 2 / 2 | [Ficha de establecimiento](https://apk2gestion.com/es/parking/hospital-general-universitario) |
| SM Consum - Picassent San Jose 24 / `2023002728` | Alcàsser → Picassent | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Avinguda+De+Cristofol+Aguado+I+Medina&cod_postal_filter=46220&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| SM Consum - Benetússer Camí Nou 415 / `2023002736` | Alfafar → Benetússer | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Avenida+Cam%C3%AD+Nou+150&cod_postal_filter=46910&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| 20XP22T3KK4AL00844 / `2023003148` | Cofrentes → Requena | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=C.+Constituci%C3%B3n&cod_postal_filter=46340&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| 20XP22T3KK4AL00846 / `2023003149` | Cofrentes → Requena | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=C.+Constituci%C3%B3n&cod_postal_filter=46340&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| 61945049570005 / `2023003681` | Formentera del Segura → Rojales | 2 / 2 | [Ficha de establecimiento](https://www.consum.es/supermercados/rojales-guatemala/) |
| 61948051050001 / `2023003684` | Moixent/Mogente → València | 2 / 2 | [Ficha de establecimiento](https://www.consum.es/supermercados/valencia-fernando-el-catolico/) |
| 61945055350006 / `2023003822` | Formentera del Segura → Rojales | 2 / 2 | [Ficha de establecimiento](https://www.consum.es/supermercados/rojales-guatemala/) |
| 61948051050011 / `2023003845` | Petrés → Sagunt/Sagunto | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=C%2F+Los+Huertos+72&cod_postal_filter=46500&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-A-SantJoanD'Alacant-003 / `2024000076` | Alacant/Alicante → Sant Joan d'Alacant | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Rambla+De+La+Llibertat&cod_postal_filter=03550&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-A-PilarDeLaHoradada-001 / `2024000081` | Elx/Elche → Pilar de la Horadada | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Comunidad+Valenciana&cod_postal_filter=03191&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-CS-CastellonDeLaPlana-006 / `2024000085` | Alcora, l' → Castelló de la Plana/Castellón de la Plana | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Del+Golf+2&cod_postal_filter=12100&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-A-SanetYNegrals-001 / `2024000177` | Benimeli → Sanet y Negrals | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Melchor+Mut&cod_postal_filter=03769&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-46-Catarroja-001 / `2024000440` | Albal → Catarroja | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Filiberto+Rodrigo+6&cod_postal_filter=46470&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-A-Tarbena-001 / `2024000693` | Bolulla → Tàrbena | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Constitucion+11&cod_postal_filter=03518&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-A-RafolDeAlmunia-001 / `2024000696` | Benimeli → Ràfol d'Almúnia, el | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Mayor+45&cod_postal_filter=03769&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-CS-Burriana-003 / `2024001875` | Benicarló → Borriana/Burriana | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=D%27onda&cod_postal_filter=12530&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-46-Benetusser-001 / `2024001912` | Alfafar → Benetússer | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Cami+Nou+126&cod_postal_filter=46910&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-A-Pego-002 / `2024002035` | Dénia → Pego | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Franciscanes+Purisima+Concepcio&cod_postal_filter=03780&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-A-Beniarres-001 / `2024002105` | Alfàs del Pi, l' → Beniarrés | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Dr.+Orero+6&cod_postal_filter=03850&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-A-CampoDeMirra-001 / `2024002149` | Beneixama → Camp de Mirra, el/Campo de Mirra | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Parador&cod_postal_filter=03469&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-A-Benimassot-001 / `2024002191` | Balones → Benimassot | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Cooperativa+1&cod_postal_filter=03812&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-V-Benageber-002 / `2024002294` | Losa del Obispo → Benagéber | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Piscina&cod_postal_filter=46173&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| E-A-Benillup-002 / `2024003865` | Almudaina → Benillup | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Trinquet+1&cod_postal_filter=03827&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| A-RAFAL-001 / `2024006843` | Orihuela → Rafal | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Oscar+Espla+10&cod_postal_filter=03369&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-V-Alfafar-003 / `2025000102` | Alfafar → Benetússer | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Cam%C3%AD+Nou+126&cod_postal_filter=46910&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| E-V-Albal-004 / `2025000175` | Albal → Catarroja | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Filiberto+Rodrigo+6&cod_postal_filter=46470&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| JV_BURGER KING - San Fulgencio / `2025000427` | Daya Vieja → San Fulgencio | 2 / 2 | [Registro del operador](https://iberdrola-bppulse.es/mapa-iberdrola/api/puntos.php) |
| ES_BP_CASTILVIEJO / `2025000500` | Xirivella → València | 2 / 2 | [Registro del operador](https://iberdrola-bppulse.es/mapa-iberdrola/api/puntos.php) |
| ES_BP_PICASSENT / `2025000509` | Alcàsser → Picassent | 2 / 2 | [Registro del operador](https://iberdrola-bppulse.es/mapa-iberdrola/api/puntos.php) |
| Popeyes Sagunto - 01 / `2025000560` | Petrés → Sagunt/Sagunto | 2 / 2 | [Registro del operador](https://iberdrola-bppulse.es/mapa-iberdrola/api/puntos.php) |
| Popeyes San Juan de Alicante - 01 / `2025000567` | Alacant/Alicante → Sant Joan d'Alacant | 2 / 2 | [Registro del operador](https://iberdrola-bppulse.es/mapa-iberdrola/api/puntos.php) |
| Burger King Picassent / `2025000591` | Alcàsser → Picassent | 2 / 2 | [Registro del operador](https://iberdrola-bppulse.es/mapa-iberdrola/api/puntos.php) |
| Repsol , GLP-Castellón / `C7TN3FGTWW7T8FIF76YR` | Alcora, l' → Castelló de la Plana/Castellón de la Plana | 2 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Pol%C3%ADgono+Industrial+Serrallo&cod_postal_filter=12100&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| V-Titaguas-001 / `VWCDFYPPUQBII1V6GARF` | Alpuente → Titaguas | 2 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=San+Salvador+7&cod_postal_filter=46178&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |
| Allego RAFAEL ALMENAR S.A. / `2024000790` | Xirivella → València | 1 / 2 | [Vial oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Calle+Fogainers&cod_postal_filter=46014&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Cportal%2Ccarretera) |
| Valencia - Archiduque Carlos / `2024004583` | Xirivella → València | 1 / 2 | [Portal oficial](https://www.cartociudad.es/geocoder/api/geocoder/candidates?q=Cl.+Pedrapiquers+9&cod_postal_filter=46014&limit=20&no_process=municipio%2Cprovincia%2Ccomunidad+autonoma%2Cpoblacion%2Ctoponimo%2Cexpendeduria%2Cpunto_recarga_electrica%2Cngbe%2Ccallejero%2Ccarretera) |

## Pendientes, por número de conectores

Orden de revisión, sin scoring territorial. La tabla no presenta las posiciones
espaciales candidatas como asignaciones aprobadas. Los casos no admitidos
incluyen direcciones insuficientes, candidatos ambiguos, discordancias de
acceso/numeración o evidencia aún no incorporada con trazabilidad suficiente.
No se concluye que todos sean imposibles de resolver.

| Instalación / ID | Declarado → candidato espacial | Puntos / conectores |
| --- | --- | ---: |
| Seur Alaquas / `QTWJBKDAJQQGEJKRFLFD` | Alaquàs → Aldaia | 22 / 22 |
| E-V-Valencia-029 / `2024004719` | Xirivella → València | 8 / 8 |
| Sagunto, Spain / `2024006388` | Petrés → Sagunt/Sagunto | 8 / 8 |
| GALP La Plana - Dirección Valencia / `2023002074` | Benicarló → Borriana/Burriana | 6 / 6 |
| GALP La Plana - Dirección Tarragona / `2023002075` | Benicarló → Borriana/Burriana | 6 / 6 |
| E.S. Exoil Pista de Silla / `2024004024` | Alfafar → Sedaví | 6 / 6 |
| Mercadona, Carretera N-3, Valencia / `777FWFKDJNVM9KCAK5A9` | Cofrentes → Requena | 6 / 6 |
| Mercadona, Clara Campoamor, Valencia / `N3QCP9CEXTFUJENPHVIB` | Alcàsser → Picassent | 6 / 6 |
| Mercadona, Avda. del Mediterráneo, Alicante / `OKSLVGXQ7BLQE7TZZ5QM` | Elda → Petrer | 6 / 6 |
| TotalEnergies - E.S. Exoil Pista de Silla / `SMTF5EK7BXYUROW7SCFL` | Alfafar → Sedaví | 6 / 6 |
| C. C. L'Epicentre / `2023002694` | Petrés → Sagunt/Sagunto | 3 / 6 |
| SM Consum 1098 - El Verger / `2023002759` | Poblets, els → Verger, el | 4 / 4 |
| A-Guadalest-001 / `2024000938` | Beniardà → Castell de Guadalest, el | 4 / 4 |
| E-A-SanFulgencio-001 / `2024001893` | Guardamar del Segura → San Fulgencio | 4 / 4 |
| A-ROJALES-003 / `2024002078` | Formentera del Segura → Rojales | 4 / 4 |
| E-V-Sagunto-004 / `2024002427` | Petrés → Sagunt/Sagunto | 4 / 4 |
| Seur Valencia / `9NEHNXJRCKZDXCRBKBZ9` | Alcàntera de Xúquer → Beneixida | 4 / 4 |
| 61947052800018 / `2023003842` | Albal → Massanassa | 3 / 3 |
| 20XM32T8KK3AR00067 / `2024005040` | Petrés → Sagunt/Sagunto | 3 / 3 |
| 20XM32T8KK4AR00023 / `2024005086` | Formentera del Segura → Rojales | 3 / 3 |
| 20XM32T8KK3AR00063 / `2024005352` | Formentera del Segura → Rojales | 3 / 3 |
| 61942049840001 / `2024005538` | Alcora, l' → Castelló de la Plana/Castellón de la Plana | 3 / 3 |
| Concesionario Ford Movilsa / `2023002053` | Alacant/Alicante → Sant Joan d'Alacant | 2 / 3 |
| V-SAGUNTO-003 / `2024002175` | Petrés → Sagunt/Sagunto | 2 / 3 |
| V-Paterna-007 / `2024004755` | Bétera → Paterna | 2 / 3 |
| SM Consum - S. Antonio de Benageber 420 / `2023002702` | Vallés → San Antonio de Benagéber | 1 / 3 |
| SM Consum - San Antonio de Benageber Poligono 18 662 / `2023002718` | Vallés → San Antonio de Benagéber | 1 / 3 |
| SM Consum - Miramar 658 / `2023002723` | Guardamar de la Safor → Miramar | 1 / 3 |
| Repsol ES, L. GUARDIOLA, S.L / `FAABIZETJKFOHYWXKUTM` | Alacant/Alicante → Callosa d'en Sarrià | 1 / 3 |
| Repsol ES, Mafon 2018 S.L / `O1YH3HDZNNWIYDLSHA1C` | Alcora, l' → Castelló de la Plana/Castellón de la Plana | 1 / 3 |
| Repsol ES, Blanlei S.L. / `W8RLXD1J9IZTCXMPH4LT` | Alacant/Alicante → Sant Joan d'Alacant | 1 / 3 |
| SM Consum - Sedaví 146 / `2023002735` | Alfafar → Sedaví | 2 / 2 |
| 61948051050020 / `2023003647` | Alacant/Alicante → Callosa d'en Sarrià | 2 / 2 |
| E-A-Benillup-001 / `2024000582` | Almudaina → Benillup | 2 / 2 |
| A-SanJuandeAlicante-008 / `2024000694` | Alacant/Alicante → Sant Joan d'Alacant | 2 / 2 |
| E-A-Pego-001 / `2024002200` | Dénia → Pego | 2 / 2 |
| E-A-Orihuela-019 / `2024004720` | Elx/Elche → Orihuela | 2 / 2 |
| E-A-Denia-008 / `2024004758` | Dénia → Pego | 2 / 2 |
| A-SANFULGENCIO-002 / `2024004760` | Daya Vieja → San Fulgencio | 2 / 2 |
| 61936038490005 / `2024005043` | Alzira → Carcaixent | 2 / 2 |
| 20XP22T3KK4AL01120 / `2024005304` | Formentera del Segura → Rojales | 2 / 2 |
| 20XP22T3KK4AL00848 / `2024005420` | Albocàsser → Alcalà de Xivert | 2 / 2 |
| Q8 Gasolinera Hermanos Bou / `3CWTX9P0F5EDNXI9VIHW` | Alcora, l' → Castelló de la Plana/Castellón de la Plana | 2 / 2 |
| Repsol ES,  ABRIL S.A. / `8OIN9RXNVVY7BEOIIN43` | Alacant/Alicante → Sant Joan d'Alacant | 2 / 2 |
| Repsol ES, E.S. La Granadina / `BSJAPWXTFTUTPA9XEIJB` | Albatera → San Isidro | 2 / 2 |
| Mercadona, Blasco Ibáñez, Valencia / `INWPX50WI06UOQ42U8KD` | Albal → Massanassa | 2 / 2 |
| Mercadona, Camino Real, Valencia / `JUWB35JEGTPLJ8P8F7OD` | Albal → Catarroja | 2 / 2 |
| Allego Nissan Dealer MONTALT NIPON, S.L.U. / `2024000811` | Albal → Massanassa | 1 / 2 |
| Supermercado Consum Catadau / `2024007279` | Llombai → Catadau | 1 / 2 |
| US_242_San_Juan_II / `2024006946` | Alacant/Alicante → Sant Joan d'Alacant | 1 / 1 |
| US_244_Massanassa / `2024006947` | Albal → Massanassa | 1 / 1 |
| US_345_San_Juan_III / `2024007477` | Alacant/Alicante → Sant Joan d'Alacant | 1 / 1 |

## Reproducción y verificaciones

La configuración de decisiones vigente se conserva en
`resultados/revision_recarga/20261018_revision_manual/decisiones.json`, junto con
copias y recibos y las referencias a las carpetas anteriores. Incluye 81 admisiones acumuladas y dos revisiones no concluyentes.
La selección de correspondencias es explícita; no hay adjudicación automática
por similitud ni por el resultado más cercano.

```powershell
.venv\Scripts\python.exe src/validar_silver.py --evidencias-recarga resultados/revision_recarga/20261018_revision_manual/decisiones.json
```

El validador comprueba huellas, recibos, identidad de registros, atributos
esperados, códigos postales de origen, consultas sin municipio impuesto y
coherencia espacial. Relee las seis salidas y verifica claves y conservación
de entidades antes de actualizar el indicador vigente. Los estados, relaciones
y coberturas del resto de Silver deben mantenerse sin cambios de contenido.

Véanse la [validación conjunta](VALIDACION_CONJUNTA_SILVER.md) y el
[inventario de tablas](TABLAS_Y_COLUMNAS_SILVER.md). Gold, i-DE espacial y las
cinco geometrías viarias no admitidas quedan fuera de esta ampliación.
