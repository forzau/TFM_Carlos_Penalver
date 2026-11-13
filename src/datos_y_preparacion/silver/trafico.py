"""Silver: aforos por año y red viaria provincial."""

from contextlib import closing
import csv
import sqlite3

from src.datos_y_preparacion.comunes import (
    comprobar_clave,
    consultar,
    gpkg_gpkg_wkb,
    identificador_sql,
    texto_sql,
)


TRAFICO_GVA = 'Fuentes/Trafico.gpkg'


TRAFICO_ROADS = {'03': 'Fuentes/RT_ALICANTE_ALACANT_gpkg',
         '12': 'Fuentes/RT_CASTELLON_CASTELLO_gpkg', '46': 'Fuentes/RT_VALENCIA_gpkg'}


TRAFICO_TRAFFIC_FIELDS = ['id', 'clau_tramo', 'carretera', 'titular', 'tipo_calzada', 'tipo_medida_trafico',
                  'pk_inicio', 'pk_estacion', 'pk_fin', 'imd', 'vehiculo_pesados_zp', 'label2_planos']


TRAFICO_ROAD_FIELDS = ['id_tramo', 'id_vial', 'tipo_tramo', 'tipo_tramd', 'codigo', 'nombre', 'tipo_vial', 'tipo_viald']


TRAFICO_MEASURES = {'1a': 'Primaria', '2a': 'Secundaria', 'C': 'Cobertura', 'Est': 'Estimada',
            'P': 'Permanente', 'R': 'Reforzada', 'Eix': 'Salida', 'Dip': 'Diputación'}


TRAFICO_KEYS = {'aforos_tramo_anio': ['tramo_aforo_id', 'anio'],
        'red_tramos': ['provincia_origen', 'tramo_id'],
        'red_tramo_vial': ['provincia_origen', 'tramo_id', 'vial_id']}


TRAFICO_NULL = '\x1eNULL_SILVER\x1e'


def trafico_read_layer(connection, path, layer, srs, fields, temporary):
    """SQLite conserva fid y WKB de la misma fila; CSV temporal evita inserciones individuales."""
    staging = temporary / 'entrada.csv'
    schema = {'fid_origen': 'BIGINT', **dict.fromkeys(fields, 'VARCHAR'), 'wkb_hex': 'VARCHAR'}
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as source:
        geo = source.execute('SELECT column_name,srs_id,m FROM gpkg_geometry_columns WHERE table_name=?', [layer]).fetchall()
        if len(geo) != 1 or geo[0][1:] != (srs, 0):
            raise ValueError(f'Geometría/CRS/M no admitidos: {layer}')
        reference = source.execute('SELECT organization,organization_coordsys_id FROM gpkg_spatial_ref_sys WHERE srs_id=?', [srs]).fetchone()
        if reference != ('EPSG', srs):
            raise ValueError(f'Autoridad CRS no acreditada: {layer}')
        columns = {r[1] for r in source.execute(f'PRAGMA table_info({identificador_sql(layer)})')}
        if not {'fid', geo[0][0], *fields}.issubset(columns):
            raise ValueError(f'Campos de entrada ausentes: {layer}')
        with staging.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(schema)
            rows = source.execute(f'SELECT fid,{",".join(identificador_sql(f) for f in fields)},{identificador_sql(geo[0][0])} FROM {identificador_sql(layer)} ORDER BY fid')
            count = 0
            for fid, *values in rows:
                blob = values.pop()
                if type(fid) is not int or any(v is not None and str(v) == TRAFICO_NULL for v in values):
                    raise ValueError(f'Identificador o marcador reservado no admitido: {layer}/{fid}')
                wkb = gpkg_gpkg_wkb(blob, srs).hex() if blob is not None else None
                writer.writerow([fid, *(TRAFICO_NULL if v is None else str(v) for v in values), TRAFICO_NULL if wkb is None else wkb])
                count += 1
    connection.execute('DROP TABLE IF EXISTS entrada')
    connection.execute('''CREATE TEMP TABLE entrada AS SELECT * FROM read_csv(?,columns=?,nullstr=?,
        header=true,delim=',',quote='"',escape='"',auto_detect=false,strict_mode=true,ignore_errors=false)''',
        [str(staging), schema, TRAFICO_NULL])
    if connection.execute('SELECT count(*) FROM entrada').fetchone()[0] != count:
        raise ValueError(f'Pérdida al cargar: {layer}')
    comprobar_clave(connection, 'entrada', ['fid_origen'])
    staging.unlink()
    return count


def trafico_numeric_sql(field):
    name = identificador_sql(field)
    return f"CASE WHEN regexp_full_match(trim({name}),'[0-9]+([.][0-9]{{1,2}})?') THEN try_cast({name} AS DECIMAL(18,2)) END"


def trafico_prepare_traffic(connection, path, temporary, origin, years=range(2009, 2026)):
    summaries = []
    cases = ' '.join(f'WHEN {texto_sql(k)} THEN {texto_sql(v)}' for k, v in TRAFICO_MEASURES.items())
    for year in years:
        layer = f'Aforos{year}'
        count = trafico_read_layer(connection, path, layer, 25830, TRAFICO_TRAFFIC_FIELDS, temporary)
        if not count:
            raise ValueError(f'Capa de aforos vacía: {layer}')
        connection.execute(f'''CREATE OR REPLACE TEMP TABLE aforo_preparado AS
            SELECT clau_tramo tramo_aforo_id,?::SMALLINT anio,carretera,titular titular_origen,
                tipo_calzada tipo_calzada_origen,tipo_medida_trafico,
                CASE tipo_medida_trafico {cases} END tipo_medida_descripcion,
                pk_inicio,pk_estacion,pk_fin,imd imd_origen,vehiculo_pesados_zp pesados_origen,
                {trafico_numeric_sql('imd')} imd_vehiculos_dia,{trafico_numeric_sql('vehiculo_pesados_zp')} porcentaje_pesados,
                label2_planos etiqueta_plano_origen,id identificador_origen,
                ?::VARCHAR origen_id,?::VARCHAR capa_origen,fid_origen,
                ST_GeomFromWKB(from_hex(wkb_hex))::GEOMETRY('EPSG:25830') geometria
            FROM entrada''', [year, origin, layer])
        connection.execute('''CREATE OR REPLACE TEMP TABLE aforo_final AS SELECT *,
            CASE WHEN imd_origen IS NULL OR trim(imd_origen)='' THEN 'no_informado'
                 WHEN imd_vehiculos_dia IS NULL THEN 'error_conversion'
                 WHEN imd_vehiculos_dia=0 THEN 'cero_publicado_revisar_uso' ELSE 'informado' END estado_imd,
            CASE WHEN pesados_origen IS NULL OR trim(pesados_origen)='' THEN 'no_informado'
                 WHEN porcentaje_pesados IS NULL THEN 'error_conversion'
                 WHEN porcentaje_pesados NOT BETWEEN 0 AND 100 THEN 'fuera_rango' ELSE 'informado' END estado_pesados,
            CASE WHEN tipo_medida_descripcion IS NOT NULL THEN 'documentado'
                 WHEN tipo_medida_trafico IS NULL OR trim(tipo_medida_trafico)='' THEN 'no_informado'
                 ELSE 'codigo_no_documentado' END estado_tipo_medida
            FROM aforo_preparado''')
        if connection.execute('SELECT count(*) FROM aforo_final WHERE estado_pesados=\'fuera_rango\'').fetchone()[0]:
            connection.execute("UPDATE aforo_final SET porcentaje_pesados=NULL WHERE estado_pesados='fuera_rango'")
        if not summaries:
            connection.execute('CREATE TABLE aforos_tramo_anio AS SELECT * FROM aforo_final WHERE false')
        connection.execute('INSERT INTO aforos_tramo_anio SELECT * FROM aforo_final')
        summaries.append({'anio': year, 'filas_bronze': count})
    return summaries


def trafico_prepare_road(connection, path, province, temporary, origin):
    count = trafico_read_layer(connection, path, 'rt_tramo_vial', 4258, TRAFICO_ROAD_FIELDS, temporary)
    connection.execute('''CREATE OR REPLACE TEMP TABLE tramos_candidatos AS
        SELECT id_tramo tramo_id,tipo_tramo tipo_tramo_codigo,tipo_tramd tipo_tramo_descripcion,
            wkb_hex,min(fid_origen)::BIGINT fid_referencia
        FROM entrada GROUP BY id_tramo,tipo_tramo,tipo_tramd,wkb_hex''')
    comprobar_clave(connection, 'tramos_candidatos', ['tramo_id'])
    for field in ('id_tramo', 'id_vial'):
        if connection.execute(f'SELECT count(*) FROM entrada WHERE {identificador_sql(field)} IS NULL OR trim({identificador_sql(field)})=\'\'').fetchone()[0]:
            raise ValueError(f'Clave viaria incompleta: {province}/{field}')
    connection.execute('''CREATE OR REPLACE TEMP TABLE tramos_preparados AS SELECT
        ?::VARCHAR provincia_origen,tramo_id,tipo_tramo_codigo,tipo_tramo_descripcion,
        ?::VARCHAR origen_id,'rt_tramo_vial'::VARCHAR capa_origen,fid_referencia,
        ST_GeomFromWKB(from_hex(wkb_hex)) geometria_origen
        FROM tramos_candidatos''', [province, origin])
    source_invalid = connection.execute('''SELECT count(*) FROM tramos_preparados
        WHERE geometria_origen IS NULL OR ST_IsEmpty(geometria_origen) OR NOT ST_IsValid(geometria_origen)
            OR ST_GeometryType(geometria_origen) NOT IN ('LINESTRING','MULTILINESTRING')''').fetchone()[0]
    if source_invalid:
        raise ValueError(f'Geometrías IGN de origen no admitidas: {province}, {source_invalid}')
    connection.execute('''CREATE OR REPLACE TEMP TABLE tramos_final AS SELECT * EXCLUDE(geometria_origen),
        ST_Transform(geometria_origen,'EPSG:4258','EPSG:25830',always_xy:=true)
            ::GEOMETRY('EPSG:25830') geometria
        FROM tramos_preparados''')
    altered = connection.execute('''SELECT count(*) FROM tramos_preparados a JOIN tramos_final b USING(tramo_id)
        WHERE ST_HasZ(a.geometria_origen) IS DISTINCT FROM ST_HasZ(b.geometria)
        OR ST_NPoints(a.geometria_origen) IS DISTINCT FROM ST_NPoints(b.geometria)
        OR ST_ZMin(a.geometria_origen) IS DISTINCT FROM ST_ZMin(b.geometria)
        OR ST_ZMax(a.geometria_origen) IS DISTINCT FROM ST_ZMax(b.geometria)''').fetchone()[0]
    if altered:
        raise ValueError(f'Cambios de dimensión, vértices o extremos Z: {province}')
    connection.execute('''CREATE OR REPLACE TEMP TABLE relaciones_final AS SELECT
        ?::VARCHAR provincia_origen,id_tramo tramo_id,id_vial vial_id,codigo codigo_vial,
        nombre nombre_vial,tipo_vial tipo_vial_codigo,tipo_viald tipo_vial_descripcion,
        ?::VARCHAR origen_id,'rt_tramo_vial'::VARCHAR capa_origen,fid_origen
        FROM entrada''', [province, origin])
    if not connection.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='red_tramos'").fetchone()[0]:
        connection.execute('CREATE TABLE red_tramos AS SELECT * FROM tramos_final WHERE false')
        connection.execute('CREATE TABLE red_tramo_vial AS SELECT * FROM relaciones_final WHERE false')
        connection.execute('CREATE TABLE control_tramos_origen (provincia_origen VARCHAR,tramo_id VARCHAR,wkb_hex VARCHAR)')
    connection.execute('INSERT INTO red_tramos SELECT * FROM tramos_final')
    connection.execute('INSERT INTO red_tramo_vial SELECT * FROM relaciones_final')
    connection.execute('INSERT INTO control_tramos_origen SELECT ?,tramo_id,wkb_hex FROM tramos_candidatos', [province])
    return {'provincia_origen': province, 'asociaciones_bronze': count,
            'tramos': connection.execute('SELECT count(*) FROM tramos_candidatos').fetchone()[0],
            'geometrias_origen_validas': True, 'dimension_vertices_extremos_z_conservados': True}


def trafico_validate(connection):
    for table, keys in TRAFICO_KEYS.items():
        comprobar_clave(connection, table, keys)
        for key in keys:
            if key != 'anio' and connection.execute(f"SELECT count(*) FROM {table} WHERE trim({identificador_sql(key)})=''").fetchone()[0]:
                raise ValueError(f'Clave vacía: {table}/{key}')
    for child, parent in [('red_tramo_vial', 'red_tramos'), ('red_tramos', 'red_tramo_vial')]:
        if connection.execute(f'SELECT count(*) FROM {child} ANTI JOIN {parent} USING(provincia_origen,tramo_id)').fetchone()[0]:
            raise ValueError('Relación tramo-vial incompleta')
    connection.execute('''CREATE TABLE incidencias (
        tabla VARCHAR,provincia_origen VARCHAR,capa_origen VARCHAR,fid_origen BIGINT,
        entidad_id VARCHAR,campo VARCHAR,valor_origen VARCHAR,motivo VARCHAR)''')
    for field, raw, state, accepted in [('imd_vehiculos_dia', 'imd_origen', 'estado_imd', 'informado'),
                                        ('porcentaje_pesados', 'pesados_origen', 'estado_pesados', 'informado'),
                                        ('tipo_medida_trafico', 'tipo_medida_trafico', 'estado_tipo_medida', 'documentado')]:
        connection.execute(f'''
            INSERT INTO incidencias SELECT 'aforos_tramo_anio',NULL,capa_origen,fid_origen,
            tramo_aforo_id,?,{identificador_sql(raw)},{identificador_sql(state)} FROM aforos_tramo_anio WHERE {identificador_sql(state)}<>?''', [field, accepted])
    geometry = []
    for table, entity, fid, province in [('aforos_tramo_anio', 'tramo_aforo_id', 'fid_origen', 'NULL::VARCHAR'),
                                         ('red_tramos', 'tramo_id', 'fid_referencia', 'provincia_origen')]:
        connection.execute(f'''ALTER TABLE {table} ADD COLUMN estado_geometria VARCHAR''')
        connection.execute(f'''UPDATE {table} SET estado_geometria=CASE
            WHEN geometria IS NULL THEN 'nula' WHEN ST_IsEmpty(geometria) THEN 'vacia'
            WHEN NOT ST_IsValid(geometria) THEN 'invalida'
            WHEN ST_GeometryType(geometria) NOT IN ('LINESTRING','MULTILINESTRING') THEN 'tipo_no_lineal'
            WHEN NOT isfinite(ST_Length(geometria)) OR ST_Length(geometria)<=0 THEN 'longitud_no_positiva'
            ELSE 'admitida' END''')
        connection.execute(f'''INSERT INTO incidencias SELECT ?,{province},capa_origen,{fid},
            {entity},'geometria',NULL,estado_geometria FROM {table} WHERE estado_geometria<>'admitida' ''', [table])
        geometry.extend(consultar(connection, f'''SELECT {texto_sql(table)} tabla,estado_geometria,count(*) filas,
            sum(ST_Length(geometria)) longitud_plana_m,count(*) FILTER(WHERE ST_HasZ(geometria)) con_z
            FROM {table} GROUP BY 1,2 ORDER BY 2'''))
    temporal = consultar(connection, '''SELECT anio,count(*) filas,count(DISTINCT carretera) carreteras,
        count(*) FILTER(WHERE tipo_medida_trafico='Est') estimados,
        count(*) FILTER(WHERE estado_imd='cero_publicado_revisar_uso') ceros,
        min(imd_vehiculos_dia)::VARCHAR minimo_imd,max(imd_vehiculos_dia)::VARCHAR maximo_imd
        FROM aforos_tramo_anio GROUP BY 1 ORDER BY 1''')
    changes = consultar(connection, '''SELECT a.anio anio_anterior,b.anio anio_siguiente,count(*) claves_comunes,
        count(*) FILTER(WHERE a.carretera IS DISTINCT FROM b.carretera OR a.pk_inicio IS DISTINCT FROM b.pk_inicio
            OR a.pk_fin IS DISTINCT FROM b.pk_fin) atributos_trazado_distintos,
        count(*) FILTER(WHERE ST_AsWKB(a.geometria) IS DISTINCT FROM ST_AsWKB(b.geometria)) wkb_distinto
        FROM aforos_tramo_anio a JOIN aforos_tramo_anio b
        ON a.tramo_aforo_id=b.tramo_aforo_id AND b.anio=a.anio+1 GROUP BY 1,2 ORDER BY 1''')
    cross = consultar(connection, '''SELECT count(*) ids_compartidos,
        count(*) FILTER(WHERE representaciones>1) con_wkb_distinto FROM
        (SELECT tramo_id,count(DISTINCT wkb_hex) representaciones FROM control_tramos_origen
        GROUP BY tramo_id HAVING count(DISTINCT provincia_origen)>1)''')[0]
    return {'claves_y_relaciones_validas': True, 'aforos_por_anio': temporal,
            'comparacion_entre_anios': changes, 'geometrias': geometry,
            'tipos_medida': consultar(connection, 'SELECT tipo_medida_trafico,tipo_medida_descripcion,count(*) filas FROM aforos_tramo_anio GROUP BY 1,2 ORDER BY 1'),
            'tramos_compartidos_entre_paquetes': cross,
            'incidencias_por_motivo': consultar(connection, 'SELECT tabla,campo,motivo,count(*) filas FROM incidencias GROUP BY 1,2,3 ORDER BY 1,2,3')}
