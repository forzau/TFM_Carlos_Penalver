# Tablas y columnas de Silver

Fecha de comprobación: **19 de octubre de 2026**. Inventario de los **36 archivos
Parquet/GeoParquet vigentes**, con **376 columnas en total**
(contadas por tabla, incluidas las que se repiten en varias tablas).

Los esquemas y recuentos se han leído directamente con DuckDB y coinciden
con los informes de las ejecuciones señaladas por `actual.json`. Solo se
incluyen tablas materializadas de Silver; Bronze y Gold quedan fuera.

En este proyecto las tablas están almacenadas en archivos. El identificador
`bloque/tabla` de este inventario sirve para distinguirlas: **no presupone
que existan esquemas o vistas SQL registrados con ese nombre**. Cada tabla
corresponde a un archivo `<tabla>.parquet` bajo
`resultados/silver/<bloque>/<ejecucion>/`.

Para el significado de los campos, claves, unidades y restricciones, consultar
el [diccionario Silver](DICCIONARIO_SILVER.md) y el
[informe de validación conjunta](VALIDACION_CONJUNTA_SILVER.md).

## Inventario

Las columnas aparecen en su orden físico. `GEOMETRY('EPSG:25830')` indica
una geometría con referencia espacial explícita; los campos con sufijo
`_origen` conservan el contenido publicado cuando así lo define el diccionario.
Los tipos no expresan por sí solos si un campo es obligatorio o admite nulos.

| Bloque / tabla | Filas | N.º de columnas | Columnas y tipos |
| --- | ---: | ---: | --- |
| `base_territorial/municipios` | 542 | 4 | `codigo_municipio` — `VARCHAR`<br>`codigo_provincia` — `VARCHAR`<br>`nombre_municipio` — `VARCHAR`<br>`fecha_referencia` — `DATE` |
| `base_territorial/recintos_municipales` | 542 | 6 | `codigo_municipio` — `VARCHAR`<br>`codigo_nacional_ign` — `VARCHAR`<br>`nombre_municipio_ign` — `VARCHAR`<br>`geometria` — `GEOMETRY('EPSG:25830')`<br>`origen_id` — `VARCHAR`<br>`registro_origen` — `VARCHAR` |
| `demografia_parque/parque_municipal` | 542 | 5 | `codigo_municipio` — `VARCHAR`<br>`fecha_referencia` — `DATE`<br>`parque_total` — `BIGINT`<br>`vehiculos_distintivo_0` — `BIGINT`<br>`electrificado_origen` — `BIGINT` |
| `demografia_parque/parque_sin_municipio` | 3 | 6 | `codigo_agrupacion_origen` — `VARCHAR`<br>`codigo_provincia` — `VARCHAR`<br>`fecha_referencia` — `DATE`<br>`parque_total` — `BIGINT`<br>`vehiculos_distintivo_0` — `BIGINT`<br>`electrificado_origen` — `BIGINT` |
| `demografia_parque/parque_detalle_observado` | 4.124.363 | 9 | `origen_id` — `VARCHAR`<br>`registro_origen` — `BIGINT`<br>`codigo_provincia` — `VARCHAR`<br>`codigo_municipio` — `VARCHAR`<br>`periodo` — `VARCHAR`<br>`tipo_dgt_codigo` — `VARCHAR`<br>`propulsion_codigo` — `VARCHAR`<br>`categoria_electrica_codigo` — `VARCHAR`<br>`distintivo_codigo` — `VARCHAR` |
| `demografia_parque/poblacion_municipal` | 8.130 | 7 | `codigo_municipio` — `VARCHAR`<br>`sexo` — `VARCHAR`<br>`anio` — `SMALLINT`<br>`poblacion` — `BIGINT`<br>`estado_valor` — `VARCHAR`<br>`valor_origen` — `VARCHAR`<br>`registro_origen` — `BIGINT` |
| `demografia_parque/renta_territorial` | 262.710 | 11 | `nivel_territorial` — `VARCHAR`<br>`codigo_territorio` — `VARCHAR`<br>`codigo_municipio` — `VARCHAR`<br>`codigo_distrito` — `VARCHAR`<br>`codigo_seccion` — `VARCHAR`<br>`indicador` — `VARCHAR`<br>`anio` — `SMALLINT`<br>`valor_eur` — `DECIMAL(18,2)`<br>`estado_valor` — `VARCHAR`<br>`valor_origen` — `VARCHAR`<br>`registro_origen` — `BIGINT` |
| `demografia_parque/renta_codigos_historicos` | 54 | 12 | `nivel_territorial` — `VARCHAR`<br>`codigo_territorio` — `VARCHAR`<br>`codigo_municipio` — `VARCHAR`<br>`codigo_distrito` — `VARCHAR`<br>`codigo_seccion` — `VARCHAR`<br>`indicador` — `VARCHAR`<br>`anio` — `SMALLINT`<br>`valor_eur` — `DECIMAL(18,2)`<br>`estado_valor` — `VARCHAR`<br>`valor_origen` — `VARCHAR`<br>`registro_origen` — `BIGINT`<br>`motivo_separacion` — `VARCHAR` |
| `demografia_parque/incidencias` | 0 | 7 | `tabla` — `VARCHAR`<br>`origen_id` — `VARCHAR`<br>`registro_origen` — `BIGINT`<br>`codigo_municipio` — `VARCHAR`<br>`campo` — `VARCHAR`<br>`valor_origen` — `VARCHAR`<br>`motivo` — `VARCHAR` |
| `recarga/recarga_instalaciones` | 1.526 | 15 | `instalacion_id` — `VARCHAR`<br>`nombre_instalacion` — `VARCHAR`<br>`operador_id` — `VARCHAR`<br>`nombre_operador` — `VARCHAR`<br>`provincia_nombre_origen` — `VARCHAR`<br>`municipio_nombre_origen` — `VARCHAR`<br>`direccion` — `VARCHAR`<br>`codigo_postal` — `VARCHAR`<br>`latitud_origen` — `VARCHAR`<br>`longitud_origen` — `VARCHAR`<br>`localizacion_origen` — `VARCHAR`<br>`tipo_horario_origen` — `VARCHAR`<br>`latitud` — `DOUBLE`<br>`longitud` — `DOUBLE`<br>`estado_coordenadas` — `VARCHAR` |
| `recarga/recarga_puntos` | 4.402 | 4 | `instalacion_id` — `VARCHAR`<br>`punto_id` — `VARCHAR`<br>`codigo_punto_origen` — `VARCHAR`<br>`accesibilidad_origen` — `VARCHAR` |
| `recarga/recarga_conectores` | 5.244 | 18 | `instalacion_id` — `VARCHAR`<br>`punto_id` — `VARCHAR`<br>`conector_id` — `VARCHAR`<br>`tipo_conector` — `VARCHAR`<br>`tipo_carga` — `VARCHAR`<br>`formato_conector` — `VARCHAR`<br>`potencia_maxima_origen` — `VARCHAR`<br>`fecha_ultima_modificacion_origen` — `VARCHAR`<br>`horario_apertura_origen` — `VARCHAR`<br>`servicios_origen` — `VARCHAR`<br>`metodos_pago_origen` — `VARCHAR`<br>`voltaje_origen` — `VARCHAR`<br>`intensidad_origen` — `VARCHAR`<br>`registro_origen` — `BIGINT`<br>`potencia_maxima_kw` — `DECIMAL(18,2)`<br>`estado_potencia` — `VARCHAR`<br>`fecha_ultima_modificacion` — `TIMESTAMP`<br>`estado_fecha` — `VARCHAR` |
| `recarga/incidencias` | 0 | 5 | `tabla` — `VARCHAR`<br>`registro_origen` — `BIGINT`<br>`campo` — `VARCHAR`<br>`valor_origen` — `VARCHAR`<br>`motivo` — `VARCHAR` |
| `trafico_red/aforos_tramo_anio` | 9.041 | 24 | `tramo_aforo_id` — `VARCHAR`<br>`anio` — `SMALLINT`<br>`carretera` — `VARCHAR`<br>`titular_origen` — `VARCHAR`<br>`tipo_calzada_origen` — `VARCHAR`<br>`tipo_medida_trafico` — `VARCHAR`<br>`tipo_medida_descripcion` — `VARCHAR`<br>`pk_inicio` — `VARCHAR`<br>`pk_estacion` — `VARCHAR`<br>`pk_fin` — `VARCHAR`<br>`imd_origen` — `VARCHAR`<br>`pesados_origen` — `VARCHAR`<br>`imd_vehiculos_dia` — `DECIMAL(18,2)`<br>`porcentaje_pesados` — `DECIMAL(18,2)`<br>`etiqueta_plano_origen` — `VARCHAR`<br>`identificador_origen` — `VARCHAR`<br>`origen_id` — `VARCHAR`<br>`capa_origen` — `VARCHAR`<br>`fid_origen` — `BIGINT`<br>`geometria` — `GEOMETRY('EPSG:25830')`<br>`estado_imd` — `VARCHAR`<br>`estado_pesados` — `VARCHAR`<br>`estado_tipo_medida` — `VARCHAR`<br>`estado_geometria` — `VARCHAR` |
| `trafico_red/red_tramos` | 1.118.309 | 9 | `provincia_origen` — `VARCHAR`<br>`tramo_id` — `VARCHAR`<br>`tipo_tramo_codigo` — `VARCHAR`<br>`tipo_tramo_descripcion` — `VARCHAR`<br>`origen_id` — `VARCHAR`<br>`capa_origen` — `VARCHAR`<br>`fid_referencia` — `BIGINT`<br>`geometria` — `GEOMETRY('EPSG:25830')`<br>`estado_geometria` — `VARCHAR` |
| `trafico_red/red_tramo_vial` | 1.197.446 | 10 | `provincia_origen` — `VARCHAR`<br>`tramo_id` — `VARCHAR`<br>`vial_id` — `VARCHAR`<br>`codigo_vial` — `VARCHAR`<br>`nombre_vial` — `VARCHAR`<br>`tipo_vial_codigo` — `VARCHAR`<br>`tipo_vial_descripcion` — `VARCHAR`<br>`origen_id` — `VARCHAR`<br>`capa_origen` — `VARCHAR`<br>`fid_origen` — `BIGINT` |
| `trafico_red/incidencias` | 107 | 8 | `tabla` — `VARCHAR`<br>`provincia_origen` — `VARCHAR`<br>`capa_origen` — `VARCHAR`<br>`fid_origen` — `BIGINT`<br>`entidad_id` — `VARCHAR`<br>`campo` — `VARCHAR`<br>`valor_origen` — `VARCHAR`<br>`motivo` — `VARCHAR` |
| `poi_osm/poi_elementos` | 269.287 | 16 | `origen_id` — `VARCHAR`<br>`capa_origen` — `VARCHAR`<br>`fid_origen` — `BIGINT`<br>`osm_id` — `VARCHAR`<br>`categoria_codigo_origen` — `VARCHAR`<br>`categoria_origen` — `VARCHAR`<br>`nombre_origen` — `VARCHAR`<br>`representacion` — `VARCHAR`<br>`grupo_uso` — `VARCHAR`<br>`estado_categoria` — `VARCHAR`<br>`geometria_origen_no_admitida_wkb` — `BLOB`<br>`geometria` — `GEOMETRY('EPSG:25830')`<br>`estado_geometria` — `VARCHAR`<br>`estado_ambito` — `VARCHAR`<br>`distancia_ambito_m` — `DOUBLE`<br>`interes_para_revision` — `BOOLEAN` |
| `poi_osm/poi_correspondencias` | 77 | 12 | `origen_punto` — `VARCHAR`<br>`fid_punto` — `BIGINT`<br>`origen_area` — `VARCHAR`<br>`fid_area` — `BIGINT`<br>`osm_id_punto` — `VARCHAR`<br>`osm_id_area` — `VARCHAR`<br>`categoria_origen` — `VARCHAR`<br>`punto_intersecta_area` — `BOOLEAN`<br>`coincide_id_publicado` — `BOOLEAN`<br>`coincide_nombre_normalizado` — `BOOLEAN`<br>`distancia_plana_m` — `DOUBLE`<br>`estado` — `VARCHAR` |
| `poi_osm/incidencias` | 0 | 6 | `origen_id` — `VARCHAR`<br>`capa_origen` — `VARCHAR`<br>`fid_origen` — `BIGINT`<br>`osm_id` — `VARCHAR`<br>`campo` — `VARCHAR`<br>`motivo` — `VARCHAR` |
| `capacidad_demanda/capacidad_demanda` | 423 | 39 | `gestor_red` — `VARCHAR`<br>`provincia_nombre_origen` — `VARCHAR`<br>`municipio_nombre_origen` — `VARCHAR`<br>`x_utm_origen` — `VARCHAR`<br>`y_utm_origen` — `VARCHAR`<br>`subestacion_origen` — `VARCHAR`<br>`nivel_tension_kv_origen` — `VARCHAR`<br>`capacidad_firme_disponible_mw_origen` — `VARCHAR`<br>`compromiso_regulatorio_origen` — `VARCHAR`<br>`capacidad_ocupada_mw_origen` — `VARCHAR`<br>`capacidad_admitida_no_evaluada_mw_origen` — `VARCHAR`<br>`posiciones_ocupadas_origen` — `VARCHAR`<br>`posiciones_libres_origen` — `VARCHAR`<br>`nudo_0_asterisco_origen` — `VARCHAR`<br>`comentarios_origen` — `VARCHAR`<br>`nombre_punto_conexion` — `VARCHAR`<br>`punto_conexion_id` — `VARCHAR`<br>`origen_id` — `VARCHAR`<br>`registro_origen` — `BIGINT`<br>`codigo_provincia` — `VARCHAR`<br>`fecha_referencia` — `DATE`<br>`estado_fecha` — `VARCHAR`<br>`estado_coordenadas` — `VARCHAR`<br>`nivel_tension_kv` — `DECIMAL(18,2)`<br>`estado_nivel_tension_kv` — `VARCHAR`<br>`capacidad_firme_disponible_mw` — `DECIMAL(18,2)`<br>`estado_capacidad_firme_disponible_mw` — `VARCHAR`<br>`capacidad_ocupada_mw` — `DECIMAL(18,2)`<br>`estado_capacidad_ocupada_mw` — `VARCHAR`<br>`capacidad_admitida_no_evaluada_mw` — `DECIMAL(18,2)`<br>`estado_capacidad_admitida_no_evaluada_mw` — `VARCHAR`<br>`posiciones_ocupadas` — `BIGINT`<br>`estado_posiciones_ocupadas` — `VARCHAR`<br>`posiciones_libres` — `BIGINT`<br>`estado_posiciones_libres` — `VARCHAR`<br>`compromiso_regulatorio` — `BOOLEAN`<br>`estado_compromiso_regulatorio` — `VARCHAR`<br>`nudo_0_asterisco` — `BOOLEAN`<br>`estado_nudo_0_asterisco` — `VARCHAR` |
| `capacidad_demanda/incidencias` | 0 | 6 | `origen_id` — `VARCHAR`<br>`punto_conexion_id` — `VARCHAR`<br>`campo` — `VARCHAR`<br>`valor_origen` — `VARCHAR`<br>`motivo` — `VARCHAR`<br>`registro_origen` — `BIGINT` |
| `recarga_espacial/recarga_instalaciones_geo` | 1.526 | 25 | `instalacion_id` — `VARCHAR`<br>`nombre_instalacion` — `VARCHAR`<br>`operador_id` — `VARCHAR`<br>`nombre_operador` — `VARCHAR`<br>`provincia_nombre_origen` — `VARCHAR`<br>`municipio_nombre_origen` — `VARCHAR`<br>`direccion` — `VARCHAR`<br>`codigo_postal` — `VARCHAR`<br>`latitud_origen` — `VARCHAR`<br>`longitud_origen` — `VARCHAR`<br>`localizacion_origen` — `VARCHAR`<br>`tipo_horario_origen` — `VARCHAR`<br>`latitud` — `DOUBLE`<br>`longitud` — `DOUBLE`<br>`estado_coordenadas` — `VARCHAR`<br>`codigo_provincia_declarada` — `VARCHAR`<br>`geometria` — `GEOMETRY('EPSG:25830')`<br>`estado_geometria` — `VARCHAR`<br>`numero_municipios_intersectados` — `BIGINT`<br>`codigo_municipio_espacial` — `VARCHAR`<br>`codigo_municipio_declarado` — `VARCHAR`<br>`nombre_municipio_espacial` — `VARCHAR`<br>`estado_contraste_territorial` — `VARCHAR`<br>`distancia_municipio_declarado_m` — `DOUBLE`<br>`admitida_asignacion_municipal` — `BOOLEAN` |
| `recarga_espacial/recarga_municipios_candidatos` | 1.526 | 2 | `instalacion_id` — `VARCHAR`<br>`codigo_municipio` — `VARCHAR` |
| `recarga_espacial/entidad_municipio` | 1.393 | 5 | `tabla_entidad` — `VARCHAR`<br>`clave_entidad` — `VARCHAR`<br>`codigo_municipio` — `VARCHAR`<br>`metodo_asignacion` — `VARCHAR`<br>`estado_asignacion` — `VARCHAR` |
| `recarga_espacial/incidencias_espaciales` | 133 | 3 | `instalacion_id` — `VARCHAR`<br>`campo` — `VARCHAR`<br>`motivo` — `VARCHAR` |
| `capacidad_demanda_espacial/capacidad_demanda_geo` | 423 | 55 | `gestor_red` — `VARCHAR`<br>`provincia_nombre_origen` — `VARCHAR`<br>`municipio_nombre_origen` — `VARCHAR`<br>`x_utm_origen` — `VARCHAR`<br>`y_utm_origen` — `VARCHAR`<br>`subestacion_origen` — `VARCHAR`<br>`nivel_tension_kv_origen` — `VARCHAR`<br>`capacidad_firme_disponible_mw_origen` — `VARCHAR`<br>`compromiso_regulatorio_origen` — `VARCHAR`<br>`capacidad_ocupada_mw_origen` — `VARCHAR`<br>`capacidad_admitida_no_evaluada_mw_origen` — `VARCHAR`<br>`posiciones_ocupadas_origen` — `VARCHAR`<br>`posiciones_libres_origen` — `VARCHAR`<br>`nudo_0_asterisco_origen` — `VARCHAR`<br>`comentarios_origen` — `VARCHAR`<br>`nombre_punto_conexion` — `VARCHAR`<br>`punto_conexion_id` — `VARCHAR`<br>`origen_id` — `VARCHAR`<br>`registro_origen` — `BIGINT`<br>`codigo_provincia` — `VARCHAR`<br>`fecha_referencia` — `DATE`<br>`estado_fecha_preparacion` — `VARCHAR`<br>`estado_coordenadas_preparacion` — `VARCHAR`<br>`nivel_tension_kv` — `DECIMAL(18,2)`<br>`estado_nivel_tension_kv` — `VARCHAR`<br>`capacidad_firme_disponible_mw` — `DECIMAL(18,2)`<br>`estado_capacidad_firme_disponible_mw` — `VARCHAR`<br>`capacidad_ocupada_mw` — `DECIMAL(18,2)`<br>`estado_capacidad_ocupada_mw` — `VARCHAR`<br>`capacidad_admitida_no_evaluada_mw` — `DECIMAL(18,2)`<br>`estado_capacidad_admitida_no_evaluada_mw` — `VARCHAR`<br>`posiciones_ocupadas` — `BIGINT`<br>`estado_posiciones_ocupadas` — `VARCHAR`<br>`posiciones_libres` — `BIGINT`<br>`estado_posiciones_libres` — `VARCHAR`<br>`compromiso_regulatorio` — `BOOLEAN`<br>`estado_compromiso_regulatorio` — `VARCHAR`<br>`nudo_0_asterisco` — `BOOLEAN`<br>`estado_nudo_0_asterisco` — `VARCHAR`<br>`fecha_publicacion` — `DATE`<br>`periodo_referencia` — `VARCHAR`<br>`estado_fecha` — `VARCHAR`<br>`estado_coordenadas` — `VARCHAR`<br>`crs_origen` — `VARCHAR`<br>`x_utm` — `DOUBLE`<br>`y_utm` — `DOUBLE`<br>`geometria` — `GEOMETRY('EPSG:25830')`<br>`estado_geometria` — `VARCHAR`<br>`numero_municipios_intersectados` — `BIGINT`<br>`codigo_municipio_espacial` — `VARCHAR`<br>`codigo_municipio_declarado` — `VARCHAR`<br>`nombre_municipio_espacial` — `VARCHAR`<br>`estado_contraste_territorial` — `VARCHAR`<br>`distancia_municipio_declarado_m` — `DOUBLE`<br>`admitida_asignacion_municipal` — `BOOLEAN` |
| `capacidad_demanda_espacial/capacidad_municipios_candidatos` | 423 | 2 | `punto_conexion_id` — `VARCHAR`<br>`codigo_municipio` — `VARCHAR` |
| `capacidad_demanda_espacial/entidad_municipio` | 423 | 3 | `punto_conexion_id` — `VARCHAR`<br>`codigo_municipio` — `VARCHAR`<br>`metodo_asignacion` — `VARCHAR` |
| `capacidad_demanda_espacial/incidencias_espaciales` | 0 | 2 | `punto_conexion_id` — `VARCHAR`<br>`motivo` — `VARCHAR` |
| `validacion_conjunta/revision_recarga` | 133 | 13 | `instalacion_id` — `VARCHAR`<br>`nombre_instalacion` — `VARCHAR`<br>`direccion` — `VARCHAR`<br>`municipio_declarado` — `VARCHAR`<br>`municipio_espacial` — `VARCHAR`<br>`codigo_municipio_declarado` — `VARCHAR`<br>`codigo_municipio_espacial` — `VARCHAR`<br>`distancia_recinto_declarado_m` — `DOUBLE`<br>`indicio_textual` — `VARCHAR`<br>`estado_revision` — `VARCHAR`<br>`codigo_municipio_validado` — `VARCHAR`<br>`url_evidencia` — `VARCHAR`<br>`motivo` — `VARCHAR` |
| `validacion_conjunta/recarga_municipio_validado` | 1.474 | 4 | `instalacion_id` — `VARCHAR`<br>`codigo_municipio` — `VARCHAR`<br>`metodo` — `VARCHAR`<br>`url_evidencia` — `VARCHAR` |
| `validacion_conjunta/relaciones_espaciales` | 1.430.940 | 7 | `tabla_entidad` — `VARCHAR`<br>`clave_entidad` — `VARCHAR`<br>`codigo_municipio` — `VARCHAR`<br>`metodo` — `VARCHAR`<br>`dimension_interseccion` — `SMALLINT`<br>`longitud_interseccion_m` — `DOUBLE`<br>`superficie_interseccion_m2` — `DOUBLE` |
| `validacion_conjunta/estado_relaciones_espaciales` | 1.397.060 | 5 | `tabla_entidad` — `VARCHAR`<br>`clave_entidad` — `VARCHAR`<br>`estado_geometria` — `VARCHAR`<br>`numero_municipios` — `BIGINT`<br>`estado_relacion` — `VARCHAR` |
| `validacion_conjunta/cobertura_estadistica` | 96.476 | 7 | `tabla_entidad` — `VARCHAR`<br>`periodo` — `VARCHAR`<br>`segmento` — `VARCHAR`<br>`codigo_municipio` — `VARCHAR`<br>`registros` — `BIGINT`<br>`valores_informados` — `BIGINT`<br>`valores_ausentes` — `BIGINT` |
| `validacion_conjunta/estado_fuentes` | 8 | 4 | `bloque` — `VARCHAR`<br>`estado` — `VARCHAR`<br>`integracion_municipal` — `VARCHAR`<br>`limitacion` — `VARCHAR` |

## Ejecuciones inventariadas

| Bloque | Ejecución | Archivos |
| --- | --- | ---: |
| `base_territorial` | `20261015T164603584512Z` | 2 |
| `demografia_parque` | `20261016T105307373142Z` | 7 |
| `recarga` | `20261016T114013461086Z` | 4 |
| `trafico_red` | `20261016T115524872944Z` | 4 |
| `poi_osm` | `20261016T121902157473Z` | 3 |
| `capacidad_demanda` | `20261016T124247391438Z` | 2 |
| `recarga_espacial` | `20261016T135403818794Z` | 4 |
| `capacidad_demanda_espacial` | `20261019T094517138707Z` | 4 |
| `validacion_conjunta` | `20261019T094606691147Z` | 6 |

## Lectura de las tablas de recarga

Para la asignación municipal admitida después de la revisión, utilizar
`validacion_conjunta/recarga_municipio_validado`: contiene **1.474 instalaciones**.
Las **52 asignaciones pendientes** permanecen identificadas en la revisión.
La capa y las relaciones de `recarga_espacial` conservan su estado histórico
de 1.393 asignaciones admitidas; no se sobrescribieron al añadir la revisión.
La tabla histórica i-DE conserva sus estados del 16-10. Para geometría y
relación municipal actual, utilizar `capacidad_demanda_espacial/capacidad_demanda_geo`
y `capacidad_demanda_espacial/entidad_municipio`: 423 puntos admitidos en
116 municipios. Publicación 04-09-2026 y periodo 2026-08; corte exacto desconocido.

Los archivos de datos y los informes detallados permanecen fuera de Git;
este inventario publica únicamente nombres de tablas, campos, tipos y recuentos.
