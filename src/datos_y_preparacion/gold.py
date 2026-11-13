"""Gold: contexto municipal, candidatos, controles y variables."""

import math

from src.datos_y_preparacion.comunes import (
    comprobar_clave,
    consultar,
    exigir_cero,
    identificador_sql,
)
from src.datos_y_preparacion.silver.osm import OSM_CATEGORIES


GOLD_MUNICIPAL_KEYS = {
    'gold_municipios': ['version_gold', 'codigo_municipio'],
    'gold_recarga_instalaciones': ['version_gold', 'instalacion_id'],
    'gold_incertidumbre_recarga_municipio': ['version_gold', 'instalacion_id', 'codigo_municipio', 'tipo_incertidumbre']}


GOLD_MUNICIPAL_BLOCKS = {
    'base_territorial': ['municipios', 'recintos_municipales'],
    'demografia_parque': ['parque_municipal', 'poblacion_municipal', 'renta_territorial'],
    'recarga_versionada': ['recarga_instalaciones_geo', 'recarga_puntos', 'recarga_conectores',
                          'recarga_municipio_validado', 'recarga_municipios_candidatos',
                          'recarga_ausentes', 'recarga_ausentes_municipios_candidatos']}


def gold_municipal_select_inputs(c):
    c.execute("CREATE TEMP TABLE parque_elegido AS SELECT * FROM parque_municipal WHERE fecha_referencia=DATE '2025-12-31'")
    c.execute("CREATE TEMP TABLE poblacion_elegida AS SELECT * FROM poblacion_municipal WHERE sexo='Total' AND anio=2025")
    c.execute("""CREATE TEMP TABLE renta_elegida AS SELECT * FROM renta_territorial
        WHERE nivel_territorial='municipio' AND indicador='Renta neta media por persona' AND anio=2023""")
    for name in ('municipios', 'recintos_municipales', 'parque_elegido', 'poblacion_elegida', 'renta_elegida'):
        comprobar_clave(c, name, ['codigo_municipio'])
        exigir_cero(c, f'''SELECT count(*) FROM (
            (SELECT codigo_municipio FROM municipios EXCEPT SELECT codigo_municipio FROM {name}) UNION ALL
            (SELECT codigo_municipio FROM {name} EXCEPT SELECT codigo_municipio FROM municipios))''',
            f'Cobertura municipal incompleta o ajena a la referencia: {name}')
    for name, keys in (
        ('recarga_instalaciones_geo', ['instalacion_id']), ('recarga_ausentes', ['instalacion_id']),
        ('recarga_puntos', ['instalacion_id', 'punto_id']),
        ('recarga_conectores', ['instalacion_id', 'punto_id', 'conector_id']),
        ('recarga_municipio_validado', ['instalacion_id']),
        ('recarga_municipios_candidatos', ['instalacion_id', 'codigo_municipio']),
        ('recarga_ausentes_municipios_candidatos', ['instalacion_id', 'codigo_municipio'])):
        comprobar_clave(c, name, keys)
    for child, parent, columns in (
        ('recarga_puntos', 'recarga_instalaciones_geo', 'instalacion_id'),
        ('recarga_conectores', 'recarga_puntos', 'instalacion_id,punto_id')):
        exigir_cero(c, f'SELECT count(*) FROM {child} ANTI JOIN {parent} USING({columns})', 'Detalle de recarga huérfano')
        exigir_cero(c, f'SELECT count(*) FROM {parent} ANTI JOIN {child} USING({columns})', 'Instalación o punto sin detalle')
    for name, parent in (('recarga_municipio_validado', 'recarga_instalaciones_geo'),
                         ('recarga_municipios_candidatos', 'recarga_instalaciones_geo'),
                         ('recarga_ausentes_municipios_candidatos', 'recarga_ausentes')):
        exigir_cero(c, f'SELECT count(*) FROM {name} ANTI JOIN {parent} USING(instalacion_id)', 'Relación de recarga huérfana')
        exigir_cero(c, f'SELECT count(*) FROM {name} ANTI JOIN municipios USING(codigo_municipio)', 'Municipio de recarga no reconocido')
    exigir_cero(c, '''SELECT count(*) FROM recarga_ausentes a
        JOIN recarga_instalaciones_geo n USING(instalacion_id)''', 'Un ID figura como presente y ausente')
    exigir_cero(c, '''SELECT count(*) FROM recarga_ausentes a ANTI JOIN municipios m
        ON a.codigo_municipio_admitido_historico=m.codigo_municipio
        WHERE a.codigo_municipio_admitido_historico IS NOT NULL''', 'Admisión histórica fuera de la referencia')


def gold_municipal_prepare(c, version, acquisition, main_origin, historical_origin):
    gold_municipal_select_inputs(c)
    c.execute('''CREATE TABLE gold_recarga_instalaciones AS WITH
        puntos AS (SELECT instalacion_id,count(*)::BIGINT n FROM recarga_puntos GROUP BY 1),
        conectores AS (SELECT instalacion_id,count(*)::BIGINT n FROM recarga_conectores GROUP BY 1)
        SELECT ?::VARCHAR version_gold,g.instalacion_id,?::VARCHAR version_recarga_observada,
            true presente_copia_principal,g.nombre_instalacion,g.operador_id,g.geometria,g.estado_geometria,
            v.codigo_municipio codigo_municipio_admitido,
            CASE WHEN v.instalacion_id IS NULL THEN 'pendiente' ELSE 'admitida_version_principal' END estado_admision,
            v.metodo metodo_admision,p.n puntos_registrados,c.n conectores_registrados,
            ?::TIMESTAMPTZ fecha_adquisicion_observacion
        FROM recarga_instalaciones_geo g LEFT JOIN recarga_municipio_validado v USING(instalacion_id)
        LEFT JOIN puntos p USING(instalacion_id) LEFT JOIN conectores c USING(instalacion_id)
        UNION ALL SELECT ?::VARCHAR,a.instalacion_id,?::VARCHAR,false,a.nombre_instalacion,a.operador_id,
            a.geometria,a.estado_geometria,a.codigo_municipio_admitido_historico,
            CASE WHEN a.codigo_municipio_admitido_historico IS NULL THEN 'pendiente' ELSE 'admitida_solo_historica' END,
            a.metodo_admision_historica,a.puntos_registrados_historicos,a.conectores_registrados_historicos,
            NULL::TIMESTAMPTZ FROM recarga_ausentes a''',
        [version, main_origin, acquisition, version, historical_origin])
    c.execute('''CREATE TEMP TABLE avisos_recarga AS
        SELECT g.instalacion_id,'asignacion_pendiente'::VARCHAR tipo_incertidumbre,
            g.codigo_municipio_declarado,NULL::VARCHAR codigo_historico
        FROM recarga_instalaciones_geo g ANTI JOIN recarga_municipio_validado v USING(instalacion_id)
        UNION ALL SELECT instalacion_id,'ausencia_exportacion',codigo_municipio_declarado,
            codigo_municipio_admitido_historico FROM recarga_ausentes''')
    c.execute('''CREATE TABLE gold_incertidumbre_recarga_municipio AS WITH roles AS (
        SELECT instalacion_id,tipo_incertidumbre,codigo_historico codigo_municipio,
            true historico,false declarado,false espacial FROM avisos_recarga WHERE codigo_historico IS NOT NULL
        UNION ALL SELECT instalacion_id,tipo_incertidumbre,codigo_municipio_declarado,
            false,true,false FROM avisos_recarga WHERE codigo_municipio_declarado IS NOT NULL
        UNION ALL SELECT a.instalacion_id,a.tipo_incertidumbre,c.codigo_municipio,false,false,true
            FROM avisos_recarga a JOIN recarga_municipios_candidatos c USING(instalacion_id)
            WHERE tipo_incertidumbre='asignacion_pendiente'
        UNION ALL SELECT a.instalacion_id,a.tipo_incertidumbre,c.codigo_municipio,false,false,true
            FROM avisos_recarga a JOIN recarga_ausentes_municipios_candidatos c USING(instalacion_id)
            WHERE tipo_incertidumbre='ausencia_exportacion')
        SELECT ?::VARCHAR version_gold,r.instalacion_id,r.codigo_municipio,r.tipo_incertidumbre,
            bool_or(historico) es_municipio_admitido_historico,bool_or(declarado) es_municipio_declarado,
            bool_or(espacial) es_candidato_espacial FROM roles r JOIN municipios m USING(codigo_municipio)
            JOIN avisos_recarga a USING(instalacion_id,tipo_incertidumbre)
        WHERE a.codigo_historico IS NULL OR r.codigo_municipio=a.codigo_historico GROUP BY 2,3,4''', [version])
    c.execute('''CREATE TABLE gold_municipios AS WITH oferta AS (
        SELECT codigo_municipio_admitido codigo_municipio,count(*)::BIGINT instalaciones,
            sum(puntos_registrados)::BIGINT puntos,sum(conectores_registrados)::BIGINT conectores
        FROM gold_recarga_instalaciones WHERE presente_copia_principal AND estado_admision='admitida_version_principal'
        GROUP BY 1), incertidumbre AS (
        SELECT codigo_municipio,count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='asignacion_pendiente') pendientes,
            count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='ausencia_exportacion') ausentes
        FROM gold_incertidumbre_recarga_municipio GROUP BY 1)
        SELECT ?::VARCHAR version_gold,m.codigo_municipio,m.codigo_provincia,m.nombre_municipio,r.geometria,
            p.fecha_referencia fecha_referencia_parque,p.parque_total,p.vehiculos_distintivo_0,
            p.vehiculos_distintivo_0::DOUBLE/nullif(p.parque_total,0) proporcion_distintivo_0,
            b.anio anio_poblacion,b.poblacion poblacion_total,b.estado_valor estado_poblacion,
            i.anio anio_renta,i.valor_eur renta_neta_media_persona_eur,i.estado_valor estado_renta,
            ?::TIMESTAMPTZ fecha_adquisicion_recarga,
            coalesce(o.instalaciones,0)::BIGINT instalaciones_con_municipio_admitido,
            coalesce(o.puntos,0)::BIGINT puntos_con_municipio_admitido,
            coalesce(o.conectores,0)::BIGINT conectores_con_municipio_admitido,
            p.vehiculos_distintivo_0::DOUBLE/nullif(o.puntos,0) distintivo_0_por_punto_admitido,
            CASE WHEN p.vehiculos_distintivo_0 IS NULL THEN 'sin_numerador_informado'
                WHEN coalesce(o.puntos,0)=0 THEN 'sin_puntos_admitidos' ELSE 'calculable' END estado_presion_descriptiva,
            coalesce(u.pendientes,0)::BIGINT instalaciones_pendientes_relacionadas,
            coalesce(u.ausentes,0)::BIGINT instalaciones_ausentes_relacionadas,
            EXISTS(SELECT 1 FROM avisos_recarga a ANTI JOIN gold_incertidumbre_recarga_municipio v
                USING(instalacion_id,tipo_incertidumbre)) hay_incertidumbre_sin_localizar
        FROM municipios m LEFT JOIN recintos_municipales r USING(codigo_municipio)
        LEFT JOIN parque_elegido p USING(codigo_municipio) LEFT JOIN poblacion_elegida b USING(codigo_municipio)
        LEFT JOIN renta_elegida i USING(codigo_municipio) LEFT JOIN oferta o USING(codigo_municipio)
        LEFT JOIN incertidumbre u USING(codigo_municipio)''', [version, acquisition])


def gold_municipal_validate(c, version):
    nullable = {
        'gold_municipios': {'parque_total', 'vehiculos_distintivo_0', 'proporcion_distintivo_0',
                           'poblacion_total', 'renta_neta_media_persona_eur', 'distintivo_0_por_punto_admitido'},
        'gold_recarga_instalaciones': {'geometria', 'codigo_municipio_admitido', 'metodo_admision', 'fecha_adquisicion_observacion'},
        'gold_incertidumbre_recarga_municipio': set()}
    for name, keys in GOLD_MUNICIPAL_KEYS.items():
        comprobar_clave(c, name, keys)
        required = [r[0] for r in c.execute('DESCRIBE ' + name).fetchall() if r[0] not in nullable[name]]
        exigir_cero(c, 'SELECT count(*) FROM ' + name + ' WHERE ' +
                     ' OR '.join(identificador_sql(f) + ' IS NULL' for f in required), 'Campo obligatorio Gold nulo')
        if c.execute(f'SELECT count(*) FROM {name} WHERE version_gold IS DISTINCT FROM ?', [version]).fetchone()[0]:
            raise ValueError('Versión Gold incoherente')
    exigir_cero(c, '''SELECT count(*) FROM (
        (SELECT codigo_municipio FROM municipios EXCEPT SELECT codigo_municipio FROM gold_municipios) UNION ALL
        (SELECT codigo_municipio FROM gold_municipios EXCEPT SELECT codigo_municipio FROM municipios))''', 'Se altera la cobertura municipal')
    exigir_cero(c, '''SELECT count(*) FROM gold_municipios WHERE geometria IS NULL OR NOT ST_IsValid(geometria)
        OR parque_total<0 OR vehiculos_distintivo_0<0 OR vehiculos_distintivo_0>parque_total
        OR poblacion_total<0 OR instalaciones_con_municipio_admitido<0 OR puntos_con_municipio_admitido<0
        OR conectores_con_municipio_admitido<0 OR instalaciones_pendientes_relacionadas<0
        OR instalaciones_ausentes_relacionadas<0''', 'Valor municipal fuera del contrato')
    exigir_cero(c, '''SELECT count(*) FROM gold_municipios WHERE
        proporcion_distintivo_0 IS DISTINCT FROM vehiculos_distintivo_0::DOUBLE/nullif(parque_total,0)
        OR distintivo_0_por_punto_admitido IS DISTINCT FROM vehiculos_distintivo_0::DOUBLE/nullif(puntos_con_municipio_admitido,0)
        OR (distintivo_0_por_punto_admitido IS NOT NULL AND NOT isfinite(distintivo_0_por_punto_admitido))
        OR estado_presion_descriptiva IS DISTINCT FROM CASE WHEN vehiculos_distintivo_0 IS NULL
            THEN 'sin_numerador_informado' WHEN puntos_con_municipio_admitido=0 THEN 'sin_puntos_admitidos'
            ELSE 'calculable' END''', 'Cociente o estado de presión incorrecto')
    exigir_cero(c, '''SELECT count(*) FROM gold_municipios m JOIN parque_elegido p USING(codigo_municipio)
        JOIN poblacion_elegida b USING(codigo_municipio) JOIN renta_elegida r USING(codigo_municipio) WHERE
        m.parque_total IS DISTINCT FROM p.parque_total OR m.vehiculos_distintivo_0 IS DISTINCT FROM p.vehiculos_distintivo_0
        OR m.fecha_referencia_parque IS DISTINCT FROM p.fecha_referencia
        OR m.poblacion_total IS DISTINCT FROM b.poblacion OR m.estado_poblacion IS DISTINCT FROM b.estado_valor
        OR m.anio_poblacion IS DISTINCT FROM b.anio OR m.renta_neta_media_persona_eur IS DISTINCT FROM r.valor_eur
        OR m.estado_renta IS DISTINCT FROM r.estado_valor OR m.anio_renta IS DISTINCT FROM r.anio''', 'Se altera una observación demográfica')
    exigir_cero(c, '''SELECT count(*) FROM gold_recarga_instalaciones WHERE puntos_registrados IS NULL
        OR conectores_registrados IS NULL OR puntos_registrados<=0 OR conectores_registrados<puntos_registrados
        OR estado_admision NOT IN ('pendiente','admitida_version_principal','admitida_solo_historica')
        OR (estado_admision='pendiente' AND (codigo_municipio_admitido IS NOT NULL OR metodo_admision IS NOT NULL))
        OR (estado_admision<>'pendiente' AND (codigo_municipio_admitido IS NULL OR metodo_admision IS NULL))
        OR (presente_copia_principal AND (fecha_adquisicion_observacion IS NULL OR estado_admision='admitida_solo_historica'))
        OR (NOT presente_copia_principal AND (fecha_adquisicion_observacion IS NOT NULL OR estado_admision='admitida_version_principal'))''',
        'Presencia, recuento o admisión de recarga incoherente')
    exigir_cero(c, '''SELECT count(*) FROM gold_recarga_instalaciones g ANTI JOIN municipios m
        ON g.codigo_municipio_admitido=m.codigo_municipio WHERE g.codigo_municipio_admitido IS NOT NULL''', 'Admisión fuera de la referencia municipal')
    exigir_cero(c, '''SELECT count(*) FROM (
        (SELECT instalacion_id,presente_copia_principal FROM gold_recarga_instalaciones EXCEPT ALL
         (SELECT instalacion_id,true FROM recarga_instalaciones_geo UNION ALL SELECT instalacion_id,false FROM recarga_ausentes))
        UNION ALL
        ((SELECT instalacion_id,true FROM recarga_instalaciones_geo UNION ALL SELECT instalacion_id,false FROM recarga_ausentes)
         EXCEPT ALL SELECT instalacion_id,presente_copia_principal FROM gold_recarga_instalaciones))''', 'Se altera el universo presente o histórico')
    exigir_cero(c, '''SELECT count(*) FROM gold_incertidumbre_recarga_municipio u
        ANTI JOIN municipios m USING(codigo_municipio)''', 'Incertidumbre para municipio inexistente')
    exigir_cero(c, '''SELECT count(*) FROM gold_incertidumbre_recarga_municipio u
        LEFT JOIN gold_recarga_instalaciones g USING(instalacion_id) WHERE g.instalacion_id IS NULL
        OR NOT (es_municipio_admitido_historico OR es_municipio_declarado OR es_candidato_espacial)
        OR tipo_incertidumbre NOT IN ('asignacion_pendiente','ausencia_exportacion')
        OR (tipo_incertidumbre='asignacion_pendiente' AND (NOT presente_copia_principal OR estado_admision<>'pendiente'))
        OR (tipo_incertidumbre='ausencia_exportacion' AND presente_copia_principal)''', 'Vínculo de incertidumbre incoherente')
    exigir_cero(c, '''SELECT count(*) FROM gold_municipios m LEFT JOIN (
        SELECT codigo_municipio,count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='asignacion_pendiente') pendientes,
            count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='ausencia_exportacion') ausentes
        FROM gold_incertidumbre_recarga_municipio GROUP BY 1) u USING(codigo_municipio)
        WHERE m.instalaciones_pendientes_relacionadas<>coalesce(u.pendientes,0)
        OR m.instalaciones_ausentes_relacionadas<>coalesce(u.ausentes,0)
        OR m.hay_incertidumbre_sin_localizar IS DISTINCT FROM EXISTS(
            SELECT 1 FROM avisos_recarga ANTI JOIN gold_incertidumbre_recarga_municipio
            USING(instalacion_id,tipo_incertidumbre))''', 'Avisos municipales no reconciliados')
    exigir_cero(c, '''SELECT count(*) FROM gold_municipios m LEFT JOIN (
        SELECT v.codigo_municipio,count(DISTINCT g.instalacion_id) instalaciones,
            count(DISTINCT (p.instalacion_id,p.punto_id)) puntos,
            count(DISTINCT (c.instalacion_id,c.punto_id,c.conector_id)) conectores
        FROM recarga_instalaciones_geo g JOIN recarga_municipio_validado v USING(instalacion_id)
        JOIN recarga_puntos p USING(instalacion_id) JOIN recarga_conectores c USING(instalacion_id,punto_id)
        GROUP BY 1) o USING(codigo_municipio) WHERE
        m.instalaciones_con_municipio_admitido<>coalesce(o.instalaciones,0)
        OR m.puntos_con_municipio_admitido<>coalesce(o.puntos,0)
        OR m.conectores_con_municipio_admitido<>coalesce(o.conectores,0)''', 'Recuento de oferta no reconciliado con Silver')
    return {'tablas': {name: c.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in GOLD_MUNICIPAL_KEYS},
        'municipios_sin_puntos_admitidos': c.execute('SELECT count(*) FROM gold_municipios WHERE puntos_con_municipio_admitido=0').fetchone()[0],
        'renta_no_informada': c.execute('SELECT count(*) FROM gold_municipios WHERE renta_neta_media_persona_eur IS NULL').fetchone()[0],
        'oferta_principal': consultar(c, '''SELECT sum(instalaciones_con_municipio_admitido) instalaciones,
            sum(puntos_con_municipio_admitido) puntos,sum(conectores_con_municipio_admitido) conectores FROM gold_municipios''')[0],
        'estados_admision': consultar(c, 'SELECT presente_copia_principal,estado_admision,count(*) instalaciones FROM gold_recarga_instalaciones GROUP BY ALL ORDER BY 1,2'),
        'incertidumbre': consultar(c, '''SELECT tipo_incertidumbre,count(*) vinculos,count(DISTINCT instalacion_id) instalaciones,
            count(DISTINCT codigo_municipio) municipios FROM gold_incertidumbre_recarga_municipio GROUP BY 1 ORDER BY 1'''),
        'incertidumbre_sin_localizar': c.execute('''SELECT count(*) FROM avisos_recarga
            ANTI JOIN gold_incertidumbre_recarga_municipio USING(instalacion_id,tipo_incertidumbre)''').fetchone()[0]}


GOLD_CANDIDATOS_KEYS = {
    'gold_candidatos': ['version_gold', 'candidato_id'],
    'gold_candidato_municipio': ['version_gold', 'candidato_id', 'codigo_municipio'],
    'gold_correspondencias_candidatos': ['version_gold', 'candidato_punto_id', 'candidato_area_id'],
    'gold_proximidad_candidato_recarga': ['version_gold', 'candidato_id', 'escenario']}


GOLD_CANDIDATOS_SCENARIOS = ('principal_admitida', 'incluye_pendientes', 'incluye_ausentes_historicas')


GOLD_CANDIDATOS_SOURCES = {
    'silver/poi_osm': ['poi_elementos', 'poi_correspondencias'],
    'silver/base_territorial': ['recintos_municipales'],
    'silver/validacion_conjunta': ['relaciones_espaciales'],
    'gold/contexto_municipal': ['gold_municipios', 'gold_recarga_instalaciones']}


def gold_candidatos_prepare(c, version):
    for table, keys in (
        ('poi_elementos', ['origen_id', 'fid_origen']),
        ('poi_correspondencias', ['origen_punto', 'fid_punto', 'origen_area', 'fid_area']),
        ('recintos_municipales', ['codigo_municipio']), ('gold_municipios', ['codigo_municipio']),
        ('gold_recarga_instalaciones', ['instalacion_id']),
        ('relaciones_espaciales', ['tabla_entidad', 'clave_entidad', 'codigo_municipio'])):
        comprobar_clave(c, table, keys)
    exigir_cero(c, '''SELECT count(*) FROM ((SELECT codigo_municipio FROM recintos_municipales EXCEPT
        SELECT codigo_municipio FROM gold_municipios) UNION ALL (SELECT codigo_municipio FROM gold_municipios
        EXCEPT SELECT codigo_municipio FROM recintos_municipales))''', 'Bases municipales diferentes')
    c.execute('''CREATE TEMP TABLE seleccion AS SELECT *,
        to_json(list_value(origen_id,cast(fid_origen AS VARCHAR)))::VARCHAR candidato_id
        FROM poi_elementos WHERE interes_para_revision AND grupo_uso IN ('aparcamiento','comercio','alojamiento')''')
    c.execute('CREATE TEMP TABLE reglas(categoria VARCHAR,codigo VARCHAR,grupo VARCHAR)')
    c.executemany('INSERT INTO reglas VALUES (?,?,?)', [(k, *v) for k, v in OSM_CATEGORIES.items()])
    exigir_cero(c, '''SELECT count(*) FROM seleccion s LEFT JOIN reglas r ON s.categoria_origen=r.categoria
        WHERE r.categoria IS NULL OR s.categoria_codigo_origen IS DISTINCT FROM r.codigo
        OR s.grupo_uso IS DISTINCT FROM r.grupo OR estado_geometria<>'admitida'
        OR estado_categoria<>'seleccionada' OR estado_ambito<>'intersecta_cv'
        OR geometria IS NULL OR NOT ST_IsValid(geometria) OR ST_IsEmpty(geometria)
        OR (representacion='punto' AND ST_GeometryType(geometria)<>'POINT')
        OR (representacion='area' AND ST_Dimension(geometria)<>2)
        OR representacion NOT IN ('punto','area')''', 'Preselección OSM incoherente')
    for name in ('seleccion', 'recintos_municipales', 'gold_recarga_instalaciones'):
        schema = {r[0]:r[1] for r in c.execute('DESCRIBE ' + name).fetchall()}
        if schema['geometria'] != "GEOMETRY('EPSG:25830')":
            raise ValueError('CRS de entrada no admitido')
    c.execute('CREATE TEMP TABLE ambito_cv AS SELECT ST_Union_Agg(geometria) geometria FROM recintos_municipales')
    print('Preparando puntos interiores y conservando áreas originales...', flush=True)
    c.execute('''CREATE TEMP TABLE representaciones AS SELECT s.*,
        CASE WHEN representacion='punto' THEN s.geometria ELSE ST_Intersection(s.geometria,a.geometria) END area_analisis
        FROM seleccion s CROSS JOIN ambito_cv a''')
    c.execute('''CREATE TABLE gold_candidato_municipio AS SELECT ?::VARCHAR version_gold,s.candidato_id,
        r.codigo_municipio,r.dimension_interseccion,r.superficie_interseccion_m2
        FROM seleccion s JOIN relaciones_espaciales r ON s.candidato_id=r.clave_entidad
        WHERE r.tabla_entidad='poi_elementos' ''', [version])
    c.execute('''CREATE TABLE gold_correspondencias_candidatos AS SELECT ?::VARCHAR version_gold,
        p.candidato_id candidato_punto_id,a.candidato_id candidato_area_id,
        r.punto_intersecta_area,r.coincide_id_publicado,r.coincide_nombre_normalizado,r.distancia_plana_m,r.estado
        FROM poi_correspondencias r JOIN seleccion p ON p.origen_id=r.origen_punto AND p.fid_origen=r.fid_punto
        JOIN seleccion a ON a.origen_id=r.origen_area AND a.fid_origen=r.fid_area''', [version])
    c.execute('''CREATE TABLE gold_candidatos AS WITH municipios AS (
        SELECT candidato_id,count(*)::BIGINT n,min(codigo_municipio) codigo FROM gold_candidato_municipio GROUP BY 1),
        pares AS (SELECT candidato_id,count(*)::BIGINT n FROM (
            SELECT candidato_punto_id candidato_id FROM gold_correspondencias_candidatos
            UNION ALL SELECT candidato_area_id FROM gold_correspondencias_candidatos) GROUP BY 1)
        SELECT ?::VARCHAR version_gold,s.candidato_id,s.origen_id,s.capa_origen,s.fid_origen,s.osm_id,s.nombre_origen,
        s.categoria_origen,s.grupo_uso,s.representacion,
        CASE WHEN s.grupo_uso='aparcamiento' THEN 'aparcamiento_mapeado'
            ELSE 'destino_sin_aparcamiento_acreditado' END tipo_preseleccion,
        'pendiente_comprobacion_local'::VARCHAR estado_revision,s.geometria,
        CASE WHEN s.representacion='punto' THEN s.geometria
            WHEN ST_Dimension(s.area_analisis)=2 THEN ST_PointOnSurface(s.area_analisis) ELSE NULL END punto_representativo,
        CASE WHEN s.representacion='punto' THEN 'punto_original'
            WHEN ST_Dimension(s.area_analisis)=2 THEN 'punto_interior_interseccion_cv'
            ELSE 'sin_superficie_en_cv' END metodo_representacion,
        CASE WHEN m.n=1 THEN m.codigo ELSE NULL END codigo_municipio_contexto,
        coalesce(m.n,0)::BIGINT numero_municipios_relacionados,
        CASE WHEN m.n=1 THEN 'interseccion_unica' ELSE 'interseccion_multiple' END estado_relacion_municipal,
        coalesce(p.n,0)::BIGINT numero_correspondencias FROM representaciones s
        LEFT JOIN municipios m USING(candidato_id) LEFT JOIN pares p USING(candidato_id)''', [version])
    c.execute('''CREATE TEMP TABLE oferta_escenarios AS SELECT s.escenario,r.* FROM gold_recarga_instalaciones r
        CROSS JOIN (VALUES ('principal_admitida'),('incluye_pendientes'),('incluye_ausentes_historicas')) s(escenario)
        WHERE s.escenario='incluye_ausentes_historicas' OR
            (r.presente_copia_principal AND (s.escenario='incluye_pendientes' OR r.estado_admision='admitida_version_principal'))''')
    c.execute('''CREATE TEMP TABLE oferta_admisible AS SELECT * FROM oferta_escenarios
        WHERE estado_geometria='admitida' AND geometria IS NOT NULL AND ST_IsValid(geometria) AND NOT ST_IsEmpty(geometria)''')


def gold_candidatos_proximity(c, version):
    c.execute('''CREATE TABLE gold_proximidad_candidato_recarga(version_gold VARCHAR,candidato_id VARCHAR,
        escenario VARCHAR,instalacion_id_mas_cercana VARCHAR,distancia_plana_m DOUBLE,
        numero_instalaciones_a_distancia_minima BIGINT,estado_distancia VARCHAR)''')
    c.execute('''CREATE TEMP TABLE posiciones AS SELECT row_number() OVER(ORDER BY candidato_id) indice,
        candidato_id,punto_representativo FROM gold_candidatos''')
    total = c.execute('SELECT count(*) FROM posiciones').fetchone()[0]
    # Acotar el producto de distancias evita retener millones de claves largas en memoria.
    for start in range(1, total + 1, 512):
        c.execute('CREATE OR REPLACE TEMP TABLE lote AS SELECT * FROM posiciones WHERE indice>=? AND indice<?', [start, start+512])
        c.execute('''CREATE OR REPLACE TEMP TABLE distancias AS SELECT p.indice,r.instalacion_id,
            ST_Distance(p.punto_representativo,r.geometria) d FROM lote p CROSS JOIN
            (SELECT DISTINCT instalacion_id,geometria FROM oferta_admisible) r
            WHERE p.punto_representativo IS NOT NULL''')
        for scenario in GOLD_CANDIDATOS_SCENARIOS:
            c.execute('''INSERT INTO gold_proximidad_candidato_recarga WITH
                admitidas AS (SELECT d.* FROM distancias d JOIN oferta_admisible o USING(instalacion_id) WHERE o.escenario=?),
                minimos AS (SELECT indice,min(d) d FROM admitidas GROUP BY 1),
                vecinos AS (SELECT a.indice,m.d,min(a.instalacion_id) id,count(*)::BIGINT n
                    FROM admitidas a JOIN minimos m ON a.indice=m.indice AND a.d=m.d GROUP BY 1,2)
                SELECT ?::VARCHAR,p.candidato_id,?::VARCHAR,v.id,v.d,coalesce(v.n,0)::BIGINT,
                    CASE WHEN p.punto_representativo IS NULL THEN 'sin_posicion_representativa'
                         WHEN v.id IS NULL THEN 'sin_recarga_admisible' ELSE 'calculable' END
                    FROM lote p LEFT JOIN vecinos v USING(indice)''', [scenario, version, scenario])
        if start == 1 or start % 4096 == 1:
            print(f'Proximidad: {min(start+511,total)}/{total} elementos...', flush=True)


def gold_candidatos_validate(c, version):
    nullable = {'osm_id','nombre_origen','punto_representativo','codigo_municipio_contexto',
                'superficie_interseccion_m2','instalacion_id_mas_cercana','distancia_plana_m'}
    for name, keys in GOLD_CANDIDATOS_KEYS.items():
        comprobar_clave(c, name, keys)
        columns = [r[0] for r in c.execute('DESCRIBE ' + name).fetchall()]
        required = [x for x in columns if x not in nullable or (name=='gold_correspondencias_candidatos' and x=='distancia_plana_m')]
        exigir_cero(c, f'SELECT count(*) FROM {name} WHERE ' + ' OR '.join(identificador_sql(x)+' IS NULL' for x in required), 'Campo obligatorio nulo')
        if c.execute(f'SELECT count(*) FROM {name} WHERE version_gold<>?', [version]).fetchone()[0]:
            raise ValueError('Versión de salida incorrecta')
    exigir_cero(c, '''SELECT count(*) FROM ((SELECT candidato_id FROM seleccion EXCEPT SELECT candidato_id FROM gold_candidatos)
        UNION ALL (SELECT candidato_id FROM gold_candidatos EXCEPT SELECT candidato_id FROM seleccion))''', 'Selección de candidatos alterada')
    source_fields = ('origen_id','capa_origen','fid_origen','osm_id','nombre_origen','categoria_origen','grupo_uso','representacion')
    exigir_cero(c, '''SELECT count(*) FROM gold_candidatos c JOIN seleccion s USING(candidato_id) WHERE ''' +
        ' OR '.join(f'c.{x} IS DISTINCT FROM s.{x}' for x in source_fields) + '''
        OR c.estado_revision<>'pendiente_comprobacion_local'
        OR c.tipo_preseleccion<>CASE WHEN s.grupo_uso='aparcamiento' THEN 'aparcamiento_mapeado'
            ELSE 'destino_sin_aparcamiento_acreditado' END''', 'Atributos OSM alterados')
    for name, expected in (
        ('gold_candidato_municipio', '''SELECT s.candidato_id,r.codigo_municipio,r.dimension_interseccion,r.superficie_interseccion_m2
            FROM seleccion s JOIN relaciones_espaciales r ON s.candidato_id=r.clave_entidad WHERE r.tabla_entidad='poi_elementos' '''),
        ('gold_correspondencias_candidatos', '''SELECT p.candidato_id candidato_punto_id,a.candidato_id candidato_area_id,
            r.punto_intersecta_area,r.coincide_id_publicado,r.coincide_nombre_normalizado,r.distancia_plana_m,r.estado
            FROM poi_correspondencias r JOIN seleccion p ON p.origen_id=r.origen_punto AND p.fid_origen=r.fid_punto
            JOIN seleccion a ON a.origen_id=r.origen_area AND a.fid_origen=r.fid_area''')):
        fields = ','.join(identificador_sql(r[0]) for r in c.execute('DESCRIBE ' + name).fetchall() if r[0]!='version_gold')
        exigir_cero(c, f'''SELECT count(*) FROM (({expected} EXCEPT ALL SELECT {fields} FROM {name})
            UNION ALL (SELECT {fields} FROM {name} EXCEPT ALL {expected}))''', 'Relaciones Silver alteradas')
    for name, field in (('gold_candidato_municipio','candidato_id'), ('gold_correspondencias_candidatos','candidato_punto_id'),
                        ('gold_correspondencias_candidatos','candidato_area_id'), ('gold_proximidad_candidato_recarga','candidato_id')):
        exigir_cero(c, f'SELECT count(*) FROM {name} x ANTI JOIN gold_candidatos c ON x.{field}=c.candidato_id', 'Candidato huérfano')
    exigir_cero(c, '''SELECT count(*) FROM gold_candidato_municipio ANTI JOIN gold_municipios USING(codigo_municipio)''', 'Municipio huérfano')
    exigir_cero(c, '''SELECT count(*) FROM gold_candidatos c LEFT JOIN (
        SELECT candidato_id,count(*) n,min(codigo_municipio) codigo FROM gold_candidato_municipio GROUP BY 1) m USING(candidato_id)
        WHERE m.n IS NULL OR c.numero_municipios_relacionados<>m.n
        OR c.codigo_municipio_contexto IS DISTINCT FROM CASE WHEN m.n=1 THEN m.codigo END
        OR c.estado_relacion_municipal<>CASE WHEN m.n=1 THEN 'interseccion_unica' ELSE 'interseccion_multiple' END''', 'Contexto municipal incoherente')
    exigir_cero(c, '''SELECT count(*) FROM gold_candidatos c LEFT JOIN (
        SELECT candidato_id,count(*) n FROM (SELECT candidato_punto_id candidato_id FROM gold_correspondencias_candidatos
        UNION ALL SELECT candidato_area_id FROM gold_correspondencias_candidatos) GROUP BY 1) p USING(candidato_id)
        WHERE c.numero_correspondencias<>coalesce(p.n,0)''', 'Recuento de correspondencias incoherente')
    exigir_cero(c, '''SELECT count(*) FROM gold_correspondencias_candidatos r
        JOIN gold_candidatos p ON p.candidato_id=r.candidato_punto_id JOIN gold_candidatos a ON a.candidato_id=r.candidato_area_id
        WHERE p.representacion<>'punto' OR a.representacion<>'area' OR p.categoria_origen<>a.categoria_origen
        OR r.estado<>'posible_correspondencia_sin_fusion' OR NOT isfinite(r.distancia_plana_m) OR r.distancia_plana_m<0''', 'Correspondencia incoherente')
    exigir_cero(c, '''SELECT count(*) FROM gold_candidatos c JOIN representaciones s USING(candidato_id)
        WHERE ST_AsWKB(c.geometria)<>ST_AsWKB(s.geometria)
        OR (c.punto_representativo IS NULL)<>(c.metodo_representacion='sin_superficie_en_cv')
        OR (c.punto_representativo IS NOT NULL AND (NOT ST_IsValid(c.punto_representativo)
            OR ST_IsEmpty(c.punto_representativo) OR ST_GeometryType(c.punto_representativo)<>'POINT'
            OR NOT ST_Intersects(c.punto_representativo,s.area_analisis)
            OR NOT ST_Intersects(c.punto_representativo,c.geometria)))''', 'Representación geométrica incoherente')
    exigir_cero(c, '''SELECT count(*) FROM (SELECT c.candidato_id FROM gold_candidatos c
        LEFT JOIN gold_proximidad_candidato_recarga p USING(candidato_id)
        GROUP BY c.candidato_id HAVING count(p.escenario)<>3 OR count(DISTINCT p.escenario)<>3)''', 'Deben existir tres escenarios por candidato')
    exigir_cero(c, '''SELECT count(*) FROM gold_proximidad_candidato_recarga p JOIN gold_candidatos c USING(candidato_id)
        LEFT JOIN oferta_admisible r ON p.instalacion_id_mas_cercana=r.instalacion_id AND p.escenario=r.escenario
        WHERE p.escenario NOT IN ('principal_admitida','incluye_pendientes','incluye_ausentes_historicas')
        OR p.estado_distancia<>CASE WHEN c.punto_representativo IS NULL THEN 'sin_posicion_representativa'
            WHEN NOT EXISTS(SELECT 1 FROM oferta_admisible o WHERE o.escenario=p.escenario) THEN 'sin_recarga_admisible' ELSE 'calculable' END
        OR (p.estado_distancia='calculable' AND (r.instalacion_id IS NULL OR p.distancia_plana_m IS NULL
            OR NOT isfinite(p.distancia_plana_m) OR p.distancia_plana_m<0 OR p.numero_instalaciones_a_distancia_minima<1
            OR p.distancia_plana_m<>ST_Distance(c.punto_representativo,r.geometria)))
        OR (p.estado_distancia<>'calculable' AND (p.distancia_plana_m IS NOT NULL
            OR p.instalacion_id_mas_cercana IS NOT NULL OR p.numero_instalaciones_a_distancia_minima<>0))''', 'Distancia, vecino o estado incoherente')
    exigir_cero(c, '''SELECT count(*) FROM gold_proximidad_candidato_recarga a JOIN gold_proximidad_candidato_recarga b USING(candidato_id)
        WHERE ((a.escenario='principal_admitida' AND b.escenario='incluye_pendientes') OR
            (a.escenario='incluye_pendientes' AND b.escenario='incluye_ausentes_historicas')) AND a.distancia_plana_m<b.distancia_plana_m''', 'Escenarios no monótonos')
    # Volver a contrastar cada mínimo y todos sus empates contra la oferta completa, por lotes.
    total = c.execute('SELECT count(*) FROM posiciones').fetchone()[0]
    for start in range(1,total+1,512):
        bad = c.execute('''WITH contraste AS (
            SELECT p.candidato_id,g.escenario,g.distancia_plana_m,g.instalacion_id_mas_cercana,
                g.numero_instalaciones_a_distancia_minima,r.instalacion_id,
                ST_Distance(p.punto_representativo,r.geometria) d
            FROM posiciones p JOIN gold_proximidad_candidato_recarga g USING(candidato_id)
            JOIN oferta_admisible r USING(escenario) WHERE p.indice>=? AND p.indice<? AND g.estado_distancia='calculable')
            SELECT count(*) FROM (SELECT candidato_id,escenario FROM contraste
            GROUP BY candidato_id,escenario,distancia_plana_m,instalacion_id_mas_cercana,numero_instalaciones_a_distancia_minima
            HAVING min(d)<>distancia_plana_m
                OR min(instalacion_id) FILTER(WHERE d=distancia_plana_m)<>instalacion_id_mas_cercana
                OR count(*) FILTER(WHERE d=distancia_plana_m)<>numero_instalaciones_a_distancia_minima)''',[start,start+512]).fetchone()[0]
        if bad:
            raise ValueError('Mínimo, desempate o número de empates incorrectos')
    return {'tablas': {n:c.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in GOLD_CANDIDATOS_KEYS},
        'categorias': consultar(c,'SELECT grupo_uso,representacion,count(*) elementos FROM gold_candidatos GROUP BY 1,2 ORDER BY 1,2'),
        'municipios_con_elementos': c.execute('SELECT count(DISTINCT codigo_municipio) FROM gold_candidato_municipio').fetchone()[0],
        'relacion_municipal': consultar(c,'SELECT numero_municipios_relacionados,count(*) elementos FROM gold_candidatos GROUP BY 1 ORDER BY 1'),
        'representacion': consultar(c,'SELECT metodo_representacion,count(*) elementos FROM gold_candidatos GROUP BY 1 ORDER BY 1'),
        'oferta': consultar(c,'''SELECT e.escenario,count(*) instalaciones,count(a.instalacion_id) admisibles,
            count(*)-count(a.instalacion_id) excluidas FROM oferta_escenarios e LEFT JOIN oferta_admisible a USING(escenario,instalacion_id) GROUP BY 1 ORDER BY 1'''),
        'proximidad': consultar(c,'''SELECT escenario,estado_distancia,count(*) elementos,min(distancia_plana_m) minimo_m,
            median(distancia_plana_m) mediana_m,max(distancia_plana_m) maximo_m FROM gold_proximidad_candidato_recarga GROUP BY 1,2 ORDER BY 1,2''')}


GOLD_CONTROLES_KEYS = {
    'gold_control_area_recarga': ['version_gold','candidato_id','escenario'],
    'gold_solapamientos_candidatos': ['version_gold','candidato_a_id','candidato_b_id'],
    'gold_control_borde': ['version_gold','candidato_id','escenario']}


def gold_controles_prepare(c, version):
    for name, keys in (
        ('gold_candidatos',['candidato_id']),('gold_municipios',['codigo_municipio']),
        ('gold_recarga_instalaciones',['instalacion_id']),
        ('gold_proximidad_candidato_recarga',['candidato_id','escenario'])):
        comprobar_clave(c,name,keys)
    for name, fields in (('gold_candidatos',('geometria','punto_representativo')),
                         ('gold_municipios',('geometria',)),('gold_recarga_instalaciones',('geometria',))):
        schema = {r[0]:r[1] for r in c.execute('DESCRIBE '+name).fetchall()}
        if any(schema[f]!="GEOMETRY('EPSG:25830')" for f in fields):
            raise ValueError('CRS de entrada no admitido')
    exigir_cero(c, '''SELECT count(*) FROM gold_candidatos WHERE geometria IS NULL
        OR NOT ST_IsValid(geometria) OR ST_IsEmpty(geometria) OR representacion NOT IN ('punto','area')
        OR (representacion='area' AND ST_Dimension(geometria)<>2)
        OR (representacion='punto' AND ST_GeometryType(geometria)<>'POINT')
        OR (punto_representativo IS NOT NULL AND (NOT ST_IsValid(punto_representativo)
            OR ST_IsEmpty(punto_representativo) OR ST_GeometryType(punto_representativo)<>'POINT'))''', 'Geometría candidata incoherente')
    exigir_cero(c, '''SELECT count(*) FROM gold_municipios WHERE geometria IS NULL
        OR NOT ST_IsValid(geometria) OR ST_IsEmpty(geometria) OR ST_Dimension(geometria)<>2''', 'Recinto no admitido')
    exigir_cero(c, '''SELECT count(*) FROM gold_proximidad_candidato_recarga
        ANTI JOIN gold_candidatos USING(candidato_id)''', 'Proximidad huérfana')
    c.execute('CREATE TEMP TABLE escenarios(escenario VARCHAR)')
    c.executemany('INSERT INTO escenarios VALUES (?)',[(x,) for x in GOLD_CANDIDATOS_SCENARIOS])
    exigir_cero(c, '''SELECT count(*) FROM ((SELECT candidato_id,escenario FROM gold_candidatos CROSS JOIN escenarios
        EXCEPT SELECT candidato_id,escenario FROM gold_proximidad_candidato_recarga) UNION ALL
        (SELECT candidato_id,escenario FROM gold_proximidad_candidato_recarga EXCEPT
        SELECT candidato_id,escenario FROM gold_candidatos CROSS JOIN escenarios))''', 'Escenarios de proximidad incompletos')
    exigir_cero(c, '''SELECT count(*) FROM gold_proximidad_candidato_recarga p JOIN gold_candidatos c USING(candidato_id)
        WHERE estado_distancia IS NULL OR estado_distancia NOT IN ('calculable','sin_posicion_representativa','sin_recarga_admisible')
        OR (estado_distancia='calculable' AND (distancia_plana_m IS NULL OR NOT isfinite(distancia_plana_m)
            OR distancia_plana_m<0 OR c.punto_representativo IS NULL))
        OR (estado_distancia<>'calculable' AND distancia_plana_m IS NOT NULL)
        OR (estado_distancia='sin_posicion_representativa')<>(c.punto_representativo IS NULL)''', 'Estado de proximidad incoherente')
    c.execute('''CREATE TEMP TABLE oferta AS SELECT e.escenario,r.* FROM gold_recarga_instalaciones r CROSS JOIN escenarios e
        WHERE (e.escenario='incluye_ausentes_historicas' OR (r.presente_copia_principal AND
            (e.escenario='incluye_pendientes' OR r.estado_admision='admitida_version_principal')))
        AND r.estado_geometria='admitida' AND r.geometria IS NOT NULL
        AND ST_IsValid(r.geometria) AND NOT ST_IsEmpty(r.geometria)''')
    c.execute("CREATE TEMP TABLE areas AS SELECT * FROM gold_candidatos WHERE representacion='area'")
    print('Contrastando áreas con instalaciones por escenario...',flush=True)
    c.execute('''CREATE TEMP TABLE coincidencias AS SELECT a.candidato_id,o.escenario,o.instalacion_id
        FROM areas a JOIN oferta o ON ST_Intersects(a.geometria,o.geometria)''')
    c.execute('''CREATE TABLE gold_control_area_recarga AS SELECT ?::VARCHAR version_gold,a.candidato_id,e.escenario,
        count(x.instalacion_id)::BIGINT instalaciones_intersectan,
        coalesce(list_sort(list(x.instalacion_id) FILTER(WHERE x.instalacion_id IS NOT NULL)),[]::VARCHAR[]) instalaciones_ids
        FROM areas a CROSS JOIN escenarios e LEFT JOIN coincidencias x USING(candidato_id,escenario)
        GROUP BY a.candidato_id,e.escenario''',[version])
    print('Conservando intersecciones entre candidatos, sin fusión...',flush=True)
    # Materializar antes de filtrar claves evita mezclar el cruce espacial con su ordenación.
    c.execute('''CREATE TEMP TABLE intersecciones AS SELECT a.candidato_id candidato_a_id,b.candidato_id candidato_b_id,
        ST_Intersection(a.geometria,b.geometria) interseccion,ST_Covers(a.geometria,b.geometria) a_cubre_b,
        ST_Covers(b.geometria,a.geometria) b_cubre_a FROM gold_candidatos a
        JOIN gold_candidatos b ON ST_Intersects(a.geometria,b.geometria)''')
    c.execute('''CREATE TABLE gold_solapamientos_candidatos AS SELECT ?::VARCHAR version_gold,
        x.candidato_a_id,x.candidato_b_id,ST_Dimension(x.interseccion)::SMALLINT dimension_interseccion,
        CASE WHEN ST_Dimension(x.interseccion)=2 THEN ST_Area(x.interseccion) END superficie_interseccion_m2,
        x.a_cubre_b,x.b_cubre_a,a.categoria_origen=b.categoria_origen misma_categoria,
        a.representacion=b.representacion misma_representacion FROM intersecciones x
        JOIN gold_candidatos a ON a.candidato_id=x.candidato_a_id JOIN gold_candidatos b ON b.candidato_id=x.candidato_b_id
        WHERE x.candidato_a_id<x.candidato_b_id''',[version])
    print('Calculando distancia al borde de la referencia CV...',flush=True)
    c.execute('CREATE TEMP TABLE ambito_cv AS SELECT ST_Union_Agg(geometria) geometria FROM gold_municipios')
    c.execute('''CREATE TEMP TABLE distancias_borde AS SELECT c.candidato_id,
        CASE WHEN c.punto_representativo IS NOT NULL THEN ST_Distance(c.punto_representativo,ST_Boundary(a.geometria)) END distancia_borde_cv_m
        FROM gold_candidatos c CROSS JOIN ambito_cv a''')
    c.execute('''CREATE TABLE gold_control_borde AS SELECT ?::VARCHAR version_gold,p.candidato_id,p.escenario,d.distancia_borde_cv_m,
        CASE WHEN p.estado_distancia='calculable' THEN p.distancia_plana_m>d.distancia_borde_cv_m ELSE NULL END posible_influencia_exterior,
        p.estado_distancia estado_control FROM gold_proximidad_candidato_recarga p JOIN distancias_borde d USING(candidato_id)''',[version])


def gold_controles_validate(c, version):
    optional = {'superficie_interseccion_m2','distancia_borde_cv_m','posible_influencia_exterior'}
    for name,keys in GOLD_CONTROLES_KEYS.items():
        comprobar_clave(c,name,keys)
        required = [r[0] for r in c.execute('DESCRIBE '+name).fetchall() if r[0] not in optional]
        exigir_cero(c,f'SELECT count(*) FROM {name} WHERE '+' OR '.join(identificador_sql(x)+' IS NULL' for x in required), 'Campo de control obligatorio nulo')
        if c.execute(f'SELECT count(*) FROM {name} WHERE version_gold<>?',[version]).fetchone()[0]:
            raise ValueError('Versión de control incorrecta')
    exigir_cero(c, '''SELECT count(*) FROM ((SELECT candidato_id,escenario FROM areas CROSS JOIN escenarios EXCEPT
        SELECT candidato_id,escenario FROM gold_control_area_recarga) UNION ALL
        (SELECT candidato_id,escenario FROM gold_control_area_recarga EXCEPT SELECT candidato_id,escenario FROM areas CROSS JOIN escenarios))''', 'Cobertura de áreas incompleta')
    exigir_cero(c, '''SELECT count(*) FROM gold_control_area_recarga r WHERE
        r.instalaciones_intersectan<>len(r.instalaciones_ids)
        OR r.instalaciones_ids<>list_sort(list_distinct(r.instalaciones_ids))''', 'Coincidencias de área no reconciliadas')
    c.execute('''CREATE OR REPLACE TEMP TABLE coincidencias_recalculadas AS
        SELECT a.candidato_id,o.escenario,o.instalacion_id FROM areas a
        JOIN oferta o ON ST_Intersects(a.geometria,o.geometria)''')
    exigir_cero(c, '''SELECT count(*) FROM ((SELECT candidato_id,escenario,unnest(instalaciones_ids) instalacion_id
        FROM gold_control_area_recarga EXCEPT ALL SELECT * FROM coincidencias_recalculadas) UNION ALL
        (SELECT * FROM coincidencias_recalculadas EXCEPT ALL SELECT candidato_id,escenario,unnest(instalaciones_ids)
        FROM gold_control_area_recarga))''', 'Coincidencias de área no reconciliadas')
    exigir_cero(c, '''SELECT count(*) FROM gold_solapamientos_candidatos x
        LEFT JOIN gold_candidatos a ON a.candidato_id=x.candidato_a_id LEFT JOIN gold_candidatos b ON b.candidato_id=x.candidato_b_id
        WHERE a.candidato_id IS NULL OR b.candidato_id IS NULL OR x.candidato_a_id>=x.candidato_b_id
        OR NOT ST_Intersects(a.geometria,b.geometria)
        OR x.dimension_interseccion<>ST_Dimension(ST_Intersection(a.geometria,b.geometria))
        OR x.superficie_interseccion_m2 IS DISTINCT FROM CASE WHEN ST_Dimension(ST_Intersection(a.geometria,b.geometria))=2
            THEN ST_Area(ST_Intersection(a.geometria,b.geometria)) END
        OR x.a_cubre_b<>ST_Covers(a.geometria,b.geometria) OR x.b_cubre_a<>ST_Covers(b.geometria,a.geometria)
        OR x.misma_categoria IS DISTINCT FROM (a.categoria_origen=b.categoria_origen)
        OR x.misma_representacion IS DISTINCT FROM (a.representacion=b.representacion)''', 'Solapamiento incoherente')
    expected = c.execute('''SELECT count(*) FROM gold_candidatos a JOIN gold_candidatos b
        ON ST_Intersects(a.geometria,b.geometria) WHERE a.candidato_id<b.candidato_id''').fetchone()[0]
    if expected!=c.execute('SELECT count(*) FROM gold_solapamientos_candidatos').fetchone()[0]:
        raise ValueError('Faltan solapamientos entre candidatos')
    exigir_cero(c, '''SELECT count(*) FROM gold_correspondencias_candidatos p WHERE p.punto_intersecta_area
        AND NOT EXISTS(SELECT 1 FROM gold_solapamientos_candidatos s WHERE
        s.candidato_a_id=least(p.candidato_punto_id,p.candidato_area_id)
        AND s.candidato_b_id=greatest(p.candidato_punto_id,p.candidato_area_id))''', 'Correspondencia espacial previa omitida')
    exigir_cero(c, '''SELECT count(*) FROM ((SELECT candidato_id,escenario FROM gold_proximidad_candidato_recarga EXCEPT
        SELECT candidato_id,escenario FROM gold_control_borde) UNION ALL (SELECT candidato_id,escenario FROM gold_control_borde
        EXCEPT SELECT candidato_id,escenario FROM gold_proximidad_candidato_recarga))''', 'Cobertura de borde incompleta')
    exigir_cero(c, '''SELECT count(*) FROM gold_control_borde b JOIN gold_proximidad_candidato_recarga p USING(candidato_id,escenario)
        JOIN gold_candidatos c USING(candidato_id) CROSS JOIN ambito_cv a WHERE
        b.estado_control<>p.estado_distancia OR b.distancia_borde_cv_m IS DISTINCT FROM
            CASE WHEN c.punto_representativo IS NOT NULL THEN ST_Distance(c.punto_representativo,ST_Boundary(a.geometria)) END
        OR (b.distancia_borde_cv_m IS NOT NULL AND (NOT isfinite(b.distancia_borde_cv_m) OR b.distancia_borde_cv_m<0))
        OR b.posible_influencia_exterior IS DISTINCT FROM CASE WHEN p.estado_distancia='calculable'
            THEN p.distancia_plana_m>b.distancia_borde_cv_m END''', 'Control de borde incoherente')
    return {'tablas':{n:c.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in GOLD_CONTROLES_KEYS},
        'areas':consultar(c,'''SELECT escenario,count(*) areas,count(*) FILTER(WHERE instalaciones_intersectan>0) con_coincidencia,
            sum(instalaciones_intersectan) relaciones_area_instalacion FROM gold_control_area_recarga GROUP BY 1 ORDER BY 1'''),
        'solapamientos':consultar(c,'''SELECT dimension_interseccion,misma_categoria,misma_representacion,count(*) pares
            FROM gold_solapamientos_candidatos GROUP BY 1,2,3 ORDER BY 1,2,3'''),
        'borde':consultar(c,'''SELECT escenario,estado_control,count(*) elementos,
            count(*) FILTER(WHERE posible_influencia_exterior) avisos FROM gold_control_borde GROUP BY 1,2 ORDER BY 1,2''')}


GOLD_VARIABLES_KEYS = {
    'gold_referencias_normalizacion': ['version_gold', 'dimension'],
    'gold_variables_municipio': ['version_gold', 'codigo_municipio'],
    'gold_variables_candidato': ['version_gold', 'candidato_id', 'escenario']}


def gold_variables_prepare(c, version):
    for name, keys in (('gold_municipios', ['codigo_municipio']), ('gold_candidatos', ['candidato_id']),
                       ('gold_recarga_instalaciones', ['instalacion_id']),
                       ('gold_proximidad_candidato_recarga', ['candidato_id', 'escenario'])):
        comprobar_clave(c, name, keys)
    for name in ('gold_municipios', 'gold_candidatos', 'gold_recarga_instalaciones'):
        schema = {r[0]:r[1] for r in c.execute('DESCRIBE '+name).fetchall()}
        if schema['geometria'] != "GEOMETRY('EPSG:25830')":
            raise ValueError('CRS de entrada no admitido')
    exigir_cero(c, '''SELECT count(*) FROM gold_municipios WHERE geometria IS NULL
        OR NOT ST_IsValid(geometria) OR ST_IsEmpty(geometria) OR ST_Dimension(geometria)<>2''', 'Recinto no admitido')
    exigir_cero(c, '''SELECT count(*) FROM gold_candidatos x LEFT JOIN gold_municipios m
        ON x.codigo_municipio_contexto=m.codigo_municipio WHERE
        (x.numero_municipios_relacionados=1 AND (x.codigo_municipio_contexto IS NULL OR m.codigo_municipio IS NULL))
        OR (x.numero_municipios_relacionados<>1 AND x.codigo_municipio_contexto IS NOT NULL)''', 'Contexto municipal incoherente')
    c.execute('CREATE TEMP TABLE escenarios(escenario VARCHAR)')
    c.executemany('INSERT INTO escenarios VALUES (?)', [(x,) for x in GOLD_CANDIDATOS_SCENARIOS])
    c.execute('''CREATE TEMP TABLE oferta AS SELECT e.escenario,r.instalacion_id,r.geometria
        FROM gold_recarga_instalaciones r CROSS JOIN escenarios e
        WHERE (e.escenario='incluye_ausentes_historicas' OR (r.presente_copia_principal AND
            (e.escenario='incluye_pendientes' OR r.estado_admision='admitida_version_principal')))
        AND r.estado_geometria='admitida' AND r.geometria IS NOT NULL
        AND ST_IsValid(r.geometria) AND NOT ST_IsEmpty(r.geometria)''')
    c.execute('''CREATE TEMP TABLE evaluables AS SELECT *,CASE
        WHEN geometria IS NULL OR NOT ST_IsValid(geometria) OR ST_IsEmpty(geometria)
            THEN 'sin_geometria_admisible'
        WHEN representacion='area' AND punto_representativo IS NULL THEN 'sin_superficie_en_cv'
        ELSE 'calculable' END estado_geometria_variable FROM gold_candidatos''')
    print('Calculando mínimos a geometría original en tres escenarios...', flush=True)
    c.execute('''CREATE TEMP TABLE minimos AS SELECT x.candidato_id,o.escenario,
        min(ST_Distance(x.geometria,o.geometria)) distancia_minima_geometria_m
        FROM evaluables x CROSS JOIN oferta o WHERE x.estado_geometria_variable='calculable' GROUP BY 1,2''')
    print('Calculando borde CV para la geometría original...', flush=True)
    c.execute('''CREATE TEMP TABLE borde_cv AS SELECT ST_Boundary(ST_Union_Agg(geometria)) geometria FROM gold_municipios''')
    comprobar_clave(c,'gold_control_borde',['candidato_id','escenario'])
    c.execute('''CREATE TEMP TABLE cotas_borde AS SELECT candidato_id,distancia_borde_cv_m cota
        FROM gold_control_borde WHERE escenario='principal_admitida' ''')
    exigir_cero(c, '''SELECT count(*) FROM evaluables x LEFT JOIN cotas_borde b USING(candidato_id)
        WHERE estado_geometria_variable='calculable' AND (b.cota IS NULL OR NOT isfinite(b.cota) OR b.cota<0
            OR x.punto_representativo IS NULL OR NOT ST_Intersects(x.geometria,x.punto_representativo))''', 'Cota de borde no admisible')
    # El representante pertenece al área: su distancia acota el mínimo; el recorte conserva el borde más cercano.
    c.execute('''CREATE TEMP TABLE bordes_recortados AS SELECT x.candidato_id,ST_Intersection(b.geometria,
        ST_MakeEnvelope(ST_XMin(x.geometria)-r.cota-1,ST_YMin(x.geometria)-r.cota-1,
            ST_XMax(x.geometria)+r.cota+1,ST_YMax(x.geometria)+r.cota+1)) geometria
        FROM evaluables x JOIN cotas_borde r USING(candidato_id) CROSS JOIN borde_cv b
        WHERE estado_geometria_variable='calculable' AND representacion='area' ''')
    exigir_cero(c, '''SELECT count(*) FROM bordes_recortados WHERE geometria IS NULL
        OR ST_IsEmpty(geometria) OR NOT ST_IsValid(geometria)''', 'Recorte de borde no admisible')
    c.execute('''CREATE TEMP TABLE distancias_borde_geometria AS SELECT x.candidato_id,
        CASE WHEN estado_geometria_variable='calculable' THEN CASE WHEN representacion='punto' THEN r.cota
            ELSE ST_Distance(x.geometria,b.geometria) END END distancia_geometria_borde_cv_m
        FROM evaluables x LEFT JOIN cotas_borde r USING(candidato_id) LEFT JOIN bordes_recortados b USING(candidato_id)''')
    exigir_cero(c, '''SELECT count(*) FROM distancias_borde_geometria d JOIN evaluables x USING(candidato_id)
        LEFT JOIN cotas_borde r USING(candidato_id) WHERE estado_geometria_variable='calculable'
        AND (distancia_geometria_borde_cv_m IS NULL OR NOT isfinite(distancia_geometria_borde_cv_m)
            OR distancia_geometria_borde_cv_m<0 OR distancia_geometria_borde_cv_m>r.cota+1e-8)''', 'Distancia a borde no admisible')
    c.execute('''CREATE TEMP TABLE valores AS SELECT 'demanda' dimension,vehiculos_distintivo_0::DOUBLE valor FROM gold_municipios
        UNION ALL SELECT 'proximidad',distancia_minima_geometria_m FROM evaluables x
        LEFT JOIN minimos m ON x.candidato_id=m.candidato_id AND m.escenario='principal_admitida' ''')
    c.execute('''CREATE TABLE gold_referencias_normalizacion AS SELECT ?::VARCHAR version_gold,d.dimension,
        CASE WHEN d.dimension='demanda' THEN 'vehiculos_distintivo_0' ELSE 'distancia_minima_geometria_m' END nombre_variable,
        CASE WHEN d.dimension='demanda' THEN 'vehiculos' ELSE 'metros' END unidad,
        CASE WHEN d.dimension='demanda' THEN 'no_aplica' ELSE 'principal_admitida' END escenario_referencia,
        CASE WHEN d.dimension='demanda' THEN 'municipios_cv' ELSE 'candidatos_cv' END universo_referencia,
        count(v.dimension)::BIGINT n_total,
        count(*) FILTER(WHERE isfinite(valor) AND valor>=0)::BIGINT n_validos,
        count(*) FILTER(WHERE v.dimension IS NOT NULL AND valor IS NULL)::BIGINT n_nulos,
        count(*) FILTER(WHERE valor IS NOT NULL AND (NOT isfinite(valor) OR valor<0))::BIGINT n_invalidos,
        min(valor) FILTER(WHERE isfinite(valor) AND valor>=0) minimo,
        max(valor) FILTER(WHERE isfinite(valor) AND valor>=0) maximo,
        CASE WHEN maximo IS NULL THEN 'sin_valores_admisibles' WHEN maximo=0 THEN 'todos_cero'
            WHEN minimo=maximo THEN 'sin_variacion_positiva' ELSE 'con_variacion' END estado_referencia
        FROM (VALUES ('demanda'),('proximidad')) d(dimension) LEFT JOIN valores v USING(dimension)
        GROUP BY d.dimension''', [version])
    c.execute('''CREATE MACRO estado_norm(x,lo,hi) AS CASE WHEN x IS NULL THEN 'sin_valor'
        WHEN NOT isfinite(x) OR x<0 THEN 'valor_no_admisible'
        WHEN lo IS NULL OR hi IS NULL THEN 'sin_referencia'
        WHEN NOT isfinite(lo) OR NOT isfinite(hi) OR lo<0 OR hi<lo THEN 'referencia_no_admisible'
        WHEN x>hi THEN 'fuera_referencia' WHEN hi=0 THEN 'todos_cero'
        WHEN lo=hi THEN 'sin_variacion_positiva' ELSE 'calculable' END''')
    c.execute('''CREATE MACRO norma_log(x,lo,hi) AS CASE
        WHEN estado_norm(x,lo,hi)='todos_cero' THEN 0.0
        WHEN estado_norm(x,lo,hi) IN ('calculable','sin_variacion_positiva') THEN ln(1.0+x)/ln(1.0+hi) END''')
    c.execute('''CREATE MACRO norma_lineal(x,lo,hi) AS CASE
        WHEN estado_norm(x,lo,hi)='todos_cero' THEN 0.0
        WHEN estado_norm(x,lo,hi) IN ('calculable','sin_variacion_positiva') THEN x/hi END''')
    c.execute('''CREATE TABLE gold_variables_municipio AS SELECT ?::VARCHAR version_gold,m.codigo_municipio,
        m.vehiculos_distintivo_0,norma_log(m.vehiculos_distintivo_0,r.minimo,r.maximo) demanda_normalizada_log,
        norma_lineal(m.vehiculos_distintivo_0,r.minimo,r.maximo) demanda_normalizada_lineal,
        estado_norm(m.vehiculos_distintivo_0,r.minimo,r.maximo) estado_normalizacion
        FROM gold_municipios m CROSS JOIN gold_referencias_normalizacion r WHERE r.dimension='demanda' ''', [version])
    c.execute('''CREATE TABLE gold_variables_candidato AS SELECT ?::VARCHAR version_gold,x.candidato_id,e.escenario,
        x.codigo_municipio_contexto,x.estado_relacion_municipal estado_contexto_municipal,m.distancia_minima_geometria_m,
        CASE WHEN x.estado_geometria_variable<>'calculable' THEN x.estado_geometria_variable
            WHEN m.distancia_minima_geometria_m IS NULL THEN 'sin_recarga_admisible' ELSE 'calculable' END estado_distancia,
        b.distancia_geometria_borde_cv_m,
        CASE WHEN estado_distancia='calculable' THEN m.distancia_minima_geometria_m>b.distancia_geometria_borde_cv_m END
            posible_influencia_exterior_geometria,
        norma_log(m.distancia_minima_geometria_m,r.minimo,r.maximo) proximidad_normalizada_log,
        norma_lineal(m.distancia_minima_geometria_m,r.minimo,r.maximo) proximidad_normalizada_lineal,
        estado_norm(m.distancia_minima_geometria_m,r.minimo,r.maximo) estado_normalizacion
        FROM evaluables x CROSS JOIN escenarios e LEFT JOIN minimos m USING(candidato_id,escenario)
        LEFT JOIN distancias_borde_geometria b USING(candidato_id)
        CROSS JOIN gold_referencias_normalizacion r WHERE r.dimension='proximidad' ''', [version])


def gold_variables_validate(c, version):
    for name, keys in GOLD_VARIABLES_KEYS.items():
        comprobar_clave(c, name, keys)
        if c.execute(f'SELECT count(*) FROM {name} WHERE version_gold IS DISTINCT FROM ?', [version]).fetchone()[0]:
            raise ValueError('Versión de variables distinta')
    for source, target, fields in (('gold_municipios','gold_variables_municipio','codigo_municipio'),
            ('gold_proximidad_candidato_recarga','gold_variables_candidato','candidato_id,escenario')):
        exigir_cero(c, f'''SELECT count(*) FROM ((SELECT {fields} FROM {source} EXCEPT SELECT {fields} FROM {target})
            UNION ALL (SELECT {fields} FROM {target} EXCEPT SELECT {fields} FROM {source}))''', 'Cobertura de variables incompleta')
    exigir_cero(c, '''SELECT count(*) FROM gold_variables_municipio v JOIN gold_municipios m USING(codigo_municipio)
        WHERE v.vehiculos_distintivo_0 IS DISTINCT FROM m.vehiculos_distintivo_0''', 'Demanda original alterada')
    for dimension in ('demanda','proximidad'):
        observed = [r[0] for r in c.execute('SELECT valor FROM valores WHERE dimension=?',[dimension]).fetchall()]
        valid = [x for x in observed if x is not None and math.isfinite(x) and x>=0]
        lo,hi = (min(valid),max(valid)) if valid else (None,None)
        state = ('sin_valores_admisibles' if hi is None else 'todos_cero' if hi==0
                 else 'sin_variacion_positiva' if lo==hi else 'con_variacion')
        expected = (len(observed),len(valid),observed.count(None),len(observed)-len(valid)-observed.count(None),lo,hi,state)
        row = c.execute('''SELECT n_total,n_validos,n_nulos,n_invalidos,minimo,maximo,estado_referencia
            FROM gold_referencias_normalizacion WHERE dimension=?''',[dimension]).fetchone()
        if row != expected:
            raise ValueError('Referencia de normalización incoherente')
    if c.execute('SELECT count(*) FROM gold_referencias_normalizacion').fetchone()[0]!=2:
        raise ValueError('Dimensiones de referencia distintas')
    for table, raw, prefix, dimension in (('gold_variables_municipio','vehiculos_distintivo_0','demanda','demanda'),
            ('gold_variables_candidato','distancia_minima_geometria_m','proximidad','proximidad')):
        ref = c.execute('SELECT minimo,maximo FROM gold_referencias_normalizacion WHERE dimension=?', [dimension]).fetchone()
        for x, log, linear, state in c.execute(f'SELECT {raw},{prefix}_normalizada_log,{prefix}_normalizada_lineal,estado_normalizacion FROM {table}').fetchall():
            expected = ('sin_valor' if x is None else 'valor_no_admisible' if not math.isfinite(x) or x<0
                else 'sin_referencia' if ref[1] is None else 'fuera_referencia' if x>ref[1]
                else 'todos_cero' if ref[1]==0 else 'sin_variacion_positiva' if ref[0]==ref[1] else 'calculable')
            if state != expected:
                raise ValueError('Estado de normalización incoherente')
            if expected in ('calculable','todos_cero','sin_variacion_positiva'):
                a,b = (math.log1p(x)/math.log1p(ref[1]),x/ref[1]) if ref[1] else (0.0,0.0)
                if (log is None or linear is None or not math.isclose(log,a,rel_tol=1e-12,abs_tol=1e-12)
                        or not math.isclose(linear,b,rel_tol=1e-12,abs_tol=1e-12) or not 0<=log<=1 or not 0<=linear<=1):
                    raise ValueError('Normalización numérica incoherente')
            elif log is not None or linear is not None:
                raise ValueError('Normalización desconocida rellenada')
    exigir_cero(c, '''SELECT count(*) FROM gold_variables_candidato v JOIN gold_candidatos x USING(candidato_id)
        JOIN gold_proximidad_candidato_recarga p USING(candidato_id,escenario)
        LEFT JOIN gold_control_area_recarga a USING(candidato_id,escenario)
        JOIN distancias_borde_geometria b USING(candidato_id)
        JOIN evaluables e USING(candidato_id) LEFT JOIN minimos m USING(candidato_id,escenario) WHERE
        v.codigo_municipio_contexto IS DISTINCT FROM x.codigo_municipio_contexto
        OR v.estado_contexto_municipal IS DISTINCT FROM x.estado_relacion_municipal
        OR v.estado_distancia IS DISTINCT FROM CASE WHEN e.estado_geometria_variable<>'calculable' THEN e.estado_geometria_variable
            WHEN m.distancia_minima_geometria_m IS NULL THEN 'sin_recarga_admisible' ELSE 'calculable' END
        OR v.distancia_minima_geometria_m IS DISTINCT FROM m.distancia_minima_geometria_m
        OR (v.estado_distancia='calculable' AND (v.distancia_minima_geometria_m IS NULL
            OR NOT isfinite(v.distancia_minima_geometria_m) OR v.distancia_minima_geometria_m<0
            OR v.distancia_minima_geometria_m>p.distancia_plana_m+1e-8))
        OR (v.estado_distancia<>'calculable' AND v.distancia_minima_geometria_m IS NOT NULL)
        OR (x.representacion='punto' AND v.estado_distancia='calculable'
            AND v.distancia_minima_geometria_m IS DISTINCT FROM p.distancia_plana_m)
        OR (v.estado_distancia='calculable' AND x.representacion='area' AND
            (a.candidato_id IS NULL OR (v.distancia_minima_geometria_m=0)<>(a.instalaciones_intersectan>0)))
        OR v.posible_influencia_exterior_geometria IS DISTINCT FROM CASE WHEN v.estado_distancia='calculable'
            THEN v.distancia_minima_geometria_m>v.distancia_geometria_borde_cv_m END
        OR v.distancia_geometria_borde_cv_m IS DISTINCT FROM b.distancia_geometria_borde_cv_m''', 'Geometría o contexto de variables incoherente')
    exigir_cero(c, '''SELECT count(*) FROM gold_variables_candidato a JOIN gold_variables_candidato b USING(candidato_id)
        WHERE ((a.escenario='principal_admitida' AND b.escenario='incluye_pendientes') OR
            (a.escenario='incluye_pendientes' AND b.escenario='incluye_ausentes_historicas'))
        AND a.distancia_minima_geometria_m<b.distancia_minima_geometria_m''', 'Distancias no monótonas por escenario')
    return {'tablas': {n:c.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in GOLD_VARIABLES_KEYS},
        'referencias': consultar(c,'SELECT * EXCLUDE(version_gold) FROM gold_referencias_normalizacion ORDER BY dimension'),
        'distancias': consultar(c,'''SELECT escenario,estado_distancia,count(*) elementos,
            count(*) FILTER(WHERE distancia_minima_geometria_m=0) ceros,median(distancia_minima_geometria_m) mediana_m,
            max(distancia_minima_geometria_m) maximo_m,count(*) FILTER(WHERE posible_influencia_exterior_geometria) avisos_borde
            FROM gold_variables_candidato GROUP BY 1,2 ORDER BY 1,2''')}
