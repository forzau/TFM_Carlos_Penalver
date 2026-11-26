# Visor municipal de recarga

Prototipo navegable de consulta de los perfiles municipales de oferta de recarga y
demanda potencial de la Comunitat Valenciana.

## Ejecutar la versión de la entrega

Descarga o clona la rama `desarrollo/frontal`. Con Python 3 disponible, ejecuta
este comando desde la raíz del repositorio:

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory desarrollo/frontal
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000). El JSON incluido en
`desarrollo/frontal/datos/municipios.json` contiene los recintos, indicadores
municipales y perfiles que muestra el visor. La ejecución utiliza la biblioteca
estándar de Python y los archivos incluidos en la rama. Para detener el servidor,
pulsa Ctrl+C.

Si el navegador muestra una versión anterior del visor, abre la dirección
del servidor y pulsa Ctrl+F5 una vez para renovar los archivos en caché.

## Prueba rápida

| Buscar | Ficha esperada |
| --- | --- |
| `Hondon de las Nieves` | Parque intermedio y pocos puntos · 77 vehículos · 2 puntos · 2.775 habitantes. |
| `Albatera` | Parque elevado y muchos puntos · aviso de una instalación con asignación municipal pendiente. |
| `Puebla de San Miguel` | Sin perfil · 65 vehículos · 0 puntos · 53 habitantes · aviso de exclusión. |

Prueba también a pasar el ratón por un recinto del mapa, pulsar «Ver municipios
de este perfil», combinar filtros de provincia y perfil, restablecerlos y mover
o acercar el mapa. Las sugerencias se abren en el buscador y respetan los filtros.
Usa las flechas para recorrerlas, Intro para elegir y Esc para cerrar el
desplegable. El botón «Modo oscuro» está en la cabecera y guarda la elección
en el navegador.

## Datos

El exportador conserva los 542 municipios de Gold `20261020T153200478279Z` y
añade las 541 asignaciones de K-means k6 de la ejecución
`20261111T161605225327Z` por código municipal. Comprueba cobertura, claves y
coincidencia de ambos recuentos. La etiqueta de cada grupo procede del apartado
5 de la Entrega 03. El mapa usa el plano EPSG:25830 de Gold y conserva los
recintos, sus partes y sus huecos en trazados con resolución de un metro.

El indicador de vehículos aproxima demanda potencial. El de recarga cuenta
puntos de la copia registrada cuya instalación tiene una asignación municipal
admitida. Los perfiles describen similitudes en ambos recuentos y sirven para
elegir municipios que estudiar con más detalle.

## Regenerar los datos del visor

La [preparación de datos](../../docs/entregas/02_datos_y_preparacion.md) y el
[modelado](../../docs/entregas/03_machine_learning.md) se ejecutan por separado.
Para regenerar el JSON hay que disponer de las dos salidas versionadas
identificadas arriba y tener DuckDB 1.5.0 en el entorno del proyecto. Desde la
raíz, con el entorno activado, ejecuta:

```powershell
python desarrollo/frontal/exportar.py
```

## Procedencia de la copia incluida

Los datos se ofrecen agregados por municipio. Los recintos se han seleccionado,
proyectado y convertido en trazados SVG. Las cifras se han unido por código
municipal y se han añadido los perfiles calculados en el proyecto.

- Recintos del [IGN](https://www.ign.es/web/es/ign/portal/ide-area-nodo-ide-ign),
  copia del 15 de octubre de 2026. Obra derivada de BDLJE CC-BY 4.0 ign.es.
  [Licencia y reconocimiento del producto](https://centrodedescargas.cnig.es/CentroDescargas/detalleArchivo?sec=12408588).
- Vehículos con Distintivo 0 de los
  [datos municipales de la DGT de 2025](https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Datos-municipales-informacion-general-2025/).
- Puntos de recarga del [inventario público del MITECO](https://catalogo.datosabiertos.miteco.gob.es/catalogo/api/3/action/package_show?id=6ee8d46f-93bd-478f-8e29-3ba4f6d8405c),
  copia del 18 de octubre de 2026, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.es).
- Población municipal del [Censo anual de población del INE](https://ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176992&idp=1254735572981&menu=resultados),
  año 2025, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.es).
