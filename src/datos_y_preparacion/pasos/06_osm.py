"""Silver: puntos y áreas OSM conservando geometría y correspondencias."""

from contextlib import closing
import csv
import sqlite3

from src.datos_y_preparacion.pasos.comunes import (
    comprobar_clave,
    consultar,
    gpkg_gpkg_wkb,
    identificador_sql,
)


OSM_SOURCE = 'Fuentes/ubicaciones_candidatasgpkg/valencia.gpkg'


OSM_LAYERS = [f'gis_osm_{family}{suffix}_free' for family in ('pois', 'traffic', 'transport') for suffix in ('', '_a')]


OSM_CRS84_WKT = 'GEOGCS["WGS 84 (CRS84)",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Longitude",EAST],AXIS["Latitude",NORTH],AUTHORITY["OGC","CRS84"]]'


OSM_CATEGORIES = {'parking': ('5260', 'aparcamiento'), 'fuel': ('5250', 'parada_viaria'),
    'service': ('5251', 'parada_viaria'), 'supermarket': ('2501', 'comercio'),
    'mall': ('2504', 'comercio'), 'department_store': ('2505', 'comercio'),
    'hotel': ('2401', 'alojamiento'), 'motel': ('2402', 'alojamiento'),
    'guesthouse': ('2404', 'alojamiento'), 'hostel': ('2405', 'alojamiento'),
    'camp_site': ('2422', 'alojamiento'), 'caravan_site': ('2424', 'alojamiento')}


OSM_KEYS = {'poi_elementos': ['origen_id', 'fid_origen'],
        'poi_correspondencias': ['origen_punto', 'fid_punto', 'origen_area', 'fid_area']}


OSM_NULL = '\x1eNULL_SILVER\x1e'


def osm_read_osm(connection, path, layer, temporary):
    schema = {'fid_origen': 'BIGINT', 'osm_id': 'VARCHAR', 'code': 'VARCHAR',
              'fclass': 'VARCHAR', 'name': 'VARCHAR', 'wkb_hex': 'VARCHAR'}
    staging = temporary / 'entrada_osm.csv'
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as source:
        geo = source.execute('SELECT column_name,srs_id,z,m FROM gpkg_geometry_columns WHERE table_name=?', [layer]).fetchall()
        if geo != [('geom', 100000, 0, 0)]:
            raise ValueError(f'Metadatos geométricos OSM no admitidos: {layer}')
        reference = source.execute('SELECT organization,organization_coordsys_id,definition FROM gpkg_spatial_ref_sys WHERE srs_id=100000').fetchone()
        # El identificador 100000 es local; se exige el WKT CRS84 comprobado, no un EPSG inventado.
        if reference != ('NONE', 100000, OSM_CRS84_WKT):
            raise ValueError('Referencia OSM distinta de la definición CRS84 comprobada')
        with staging.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(schema)
            count = 0
            for fid, osm, code, category, name, blob in source.execute(f'SELECT fid,osm_id,code,fclass,name,geom FROM {identificador_sql(layer)} ORDER BY fid'):
                if type(fid) is not int:
                    raise ValueError(f'fid no entero: {layer}')
                values = [osm, code, category, name, gpkg_gpkg_wkb(blob, 100000).hex() if blob is not None else None]
                if any(v is not None and str(v) == OSM_NULL for v in values):
                    raise ValueError('Marcador de nulo reservado en el original')
                writer.writerow([fid, *(OSM_NULL if v is None else str(v) for v in values)])
                count += 1
    connection.execute('DROP TABLE IF EXISTS entrada_osm')
    connection.execute('''CREATE TEMP TABLE entrada_osm AS SELECT * FROM read_csv(?,columns=?,nullstr=?,
        header=true,delim=',',quote='"',escape='"',auto_detect=false,strict_mode=true,ignore_errors=false)''', [str(staging), schema, OSM_NULL])
    comprobar_clave(connection, 'entrada_osm', ['fid_origen'])
    if not count or connection.execute('SELECT count(*) FROM entrada_osm').fetchone()[0] != count:
        raise ValueError(f'Capa vacía o lectura no reconciliada: {layer}')
    staging.unlink()
    return count


def osm_prepare(connection, path, temporary, origin, layers=OSM_LAYERS):
    connection.execute('CREATE TEMP TABLE categorias (fclass VARCHAR PRIMARY KEY,code VARCHAR,grupo VARCHAR)')
    connection.executemany('INSERT INTO categorias VALUES (?,?,?)', [(k, *v) for k, v in OSM_CATEGORIES.items()])
    counts = []
    for layer in layers:
        count = osm_read_osm(connection, path, layer, temporary)
        area = '_a_free' in layer
        allowed = "('POLYGON','MULTIPOLYGON')" if area else "('POINT')"
        connection.execute(f'''CREATE OR REPLACE TEMP TABLE osm_geometria AS SELECT *,
            CASE WHEN g IS NULL THEN 'origen_nulo' WHEN ST_IsEmpty(g) THEN 'origen_vacio'
                 WHEN NOT ST_IsValid(g) THEN 'origen_invalido'
                 WHEN ST_GeometryType(g) NOT IN {allowed} THEN 'tipo_origen_no_admitido'
                 ELSE 'admitida' END estado_origen
            FROM (SELECT *,ST_GeomFromWKB(from_hex(wkb_hex)) g FROM entrada_osm)''')
        connection.execute('''CREATE OR REPLACE TEMP TABLE osm_preparado AS SELECT
            ?::VARCHAR origen_id,?::VARCHAR capa_origen,fid_origen,osm_id,
            o.code categoria_codigo_origen,o.fclass categoria_origen,name nombre_origen,
            ?::VARCHAR representacion,grupo grupo_uso,
            CASE WHEN c.fclass IS NULL THEN 'sin_seleccion'
                 WHEN o.code IS DISTINCT FROM c.code THEN 'codigo_no_concordante'
                 ELSE 'seleccionada' END estado_categoria,
            CASE WHEN estado_origen<>'admitida' THEN from_hex(wkb_hex) ELSE NULL END geometria_origen_no_admitida_wkb,
            CASE WHEN estado_origen='admitida' THEN
                ST_Transform(g,'OGC:CRS84','EPSG:25830',always_xy:=true) ELSE NULL END
                ::GEOMETRY('EPSG:25830') geometria,estado_origen
            FROM osm_geometria o LEFT JOIN categorias c ON o.fclass=c.fclass''',
            [origin + ':' + layer, layer, 'area' if area else 'punto'])
        connection.execute('''CREATE OR REPLACE TEMP TABLE osm_final AS SELECT * EXCLUDE(estado_origen),
            CASE WHEN estado_origen<>'admitida' THEN estado_origen
                 WHEN geometria IS NULL OR ST_IsEmpty(geometria) OR NOT ST_IsValid(geometria) THEN 'proyeccion_no_admitida'
                 ELSE 'admitida' END estado_geometria
            FROM osm_preparado''')
        if not counts:
            connection.execute('CREATE TABLE poi_elementos AS SELECT * FROM osm_final WHERE false')
        connection.execute('INSERT INTO poi_elementos SELECT * FROM osm_final')
        counts.append({'capa': layer, 'filas_bronze': count})
        print(f'OSM: {layer}, {count} registros conservados.', flush=True)
    comprobar_clave(connection, 'poi_elementos', OSM_KEYS['poi_elementos'])
    return counts


def osm_classify(connection):
    connection.execute('ALTER TABLE poi_elementos ADD COLUMN estado_ambito VARCHAR')
    connection.execute('''UPDATE poi_elementos SET estado_ambito=CASE
        WHEN estado_geometria<>'admitida' THEN 'no_evaluable'
        WHEN ST_Intersects(poi_elementos.geometria,a.geometria) THEN 'intersecta_cv' ELSE 'fuera_cv' END
        FROM ambito_cv a''')
    connection.execute('ALTER TABLE poi_elementos ADD COLUMN distancia_ambito_m DOUBLE')
    connection.execute('''UPDATE poi_elementos SET distancia_ambito_m=CASE
        WHEN estado_ambito='intersecta_cv' THEN 0.0
        WHEN estado_ambito='fuera_cv' THEN ST_Distance(poi_elementos.geometria,a.geometria) ELSE NULL END
        FROM ambito_cv a''')
    connection.execute('ALTER TABLE poi_elementos ADD COLUMN interes_para_revision BOOLEAN')
    connection.execute("UPDATE poi_elementos SET interes_para_revision=(estado_categoria='seleccionada' AND estado_geometria='admitida' AND estado_ambito='intersecta_cv')")


def osm_correspondences(connection):
    for representation in ('punto', 'area'):
        connection.execute(f'''CREATE TEMP TABLE {representation}s_revision AS SELECT * FROM poi_elementos
            WHERE estado_categoria='seleccionada' AND estado_geometria='admitida' AND representacion=?''', [representation])
    # shortcut: cruce separado por fallo de poda en spatial 1.5.0; revisar al actualizar el motor.
    connection.execute('''CREATE TEMP TABLE intersecciones AS
        SELECT p.origen_id origen_punto,p.fid_origen fid_punto,a.origen_id origen_area,a.fid_origen fid_area,
            p.categoria_origen categoria_punto,a.categoria_origen categoria_area
        FROM puntos_revision p JOIN areas_revision a ON ST_Intersects(p.geometria,a.geometria)''')
    connection.execute('''CREATE TEMP TABLE indicios AS
        SELECT origen_punto,fid_punto,origen_area,fid_area FROM intersecciones WHERE categoria_punto=categoria_area
        UNION
        SELECT p.origen_id origen_punto,p.fid_origen fid_punto,a.origen_id origen_area,a.fid_origen fid_area
        FROM puntos_revision p JOIN areas_revision a
        ON p.osm_id=a.osm_id AND p.categoria_origen=a.categoria_origen
        WHERE p.osm_id IS NOT NULL AND trim(p.osm_id)<>'' ''')
    connection.execute('''CREATE TABLE poi_correspondencias AS
        SELECT i.*,p.osm_id osm_id_punto,a.osm_id osm_id_area,p.categoria_origen,
            ST_Intersects(p.geometria,a.geometria) punto_intersecta_area,
            (coalesce(p.osm_id=a.osm_id,false) AND coalesce(trim(p.osm_id),'')<>'') coincide_id_publicado,
            (coalesce(trim(p.nombre_origen),'')<>'' AND
                lower(coalesce(trim(p.nombre_origen),''))=lower(coalesce(trim(a.nombre_origen),''))) coincide_nombre_normalizado,
            ST_Distance(p.geometria,a.geometria) distancia_plana_m,
            'posible_correspondencia_sin_fusion'::VARCHAR estado
        FROM indicios i JOIN puntos_revision p ON i.origen_punto=p.origen_id AND i.fid_punto=p.fid_origen
        JOIN areas_revision a ON i.origen_area=a.origen_id AND i.fid_area=a.fid_origen''')
    comprobar_clave(connection, 'poi_correspondencias', OSM_KEYS['poi_correspondencias'])
    for rep in ('punto', 'area'):
        if connection.execute(f'''SELECT count(*) FROM poi_correspondencias r ANTI JOIN poi_elementos p
            ON r.origen_{rep}=p.origen_id AND r.fid_{rep}=p.fid_origen''').fetchone()[0]:
            raise ValueError('Correspondencias sin elemento de origen')


def osm_validate(connection, counts):
    expected = sum(r['filas_bronze'] for r in counts)
    if connection.execute('SELECT count(*) FROM poi_elementos').fetchone()[0] != expected:
        raise ValueError('No se conservan todos los elementos OSM leídos')
    connection.execute('''CREATE TABLE incidencias AS
        SELECT origen_id,capa_origen,fid_origen,osm_id,'geometria'::VARCHAR campo,estado_geometria motivo
        FROM poi_elementos WHERE estado_geometria<>'admitida'
        UNION ALL SELECT origen_id,capa_origen,fid_origen,osm_id,'categoria',estado_categoria
        FROM poi_elementos WHERE estado_categoria='codigo_no_concordante'
        UNION ALL SELECT origen_id,capa_origen,fid_origen,osm_id,'osm_id','identificador_no_informado'
        FROM poi_elementos WHERE osm_id IS NULL OR trim(osm_id)='' ''')
    return {'filas_conservadas': expected, 'filas_eliminadas': 0,
        'por_capa': consultar(connection, '''SELECT capa_origen,count(*) filas,count(DISTINCT osm_id) ids_distintos,
            count(*) FILTER(WHERE interes_para_revision) para_revision FROM poi_elementos GROUP BY 1 ORDER BY 1'''),
        'por_categoria_seleccionada': consultar(connection, '''SELECT categoria_origen,grupo_uso,representacion,
            count(*) elementos,count(*) FILTER(WHERE interes_para_revision) para_revision
            FROM poi_elementos WHERE estado_categoria='seleccionada' GROUP BY 1,2,3 ORDER BY 2,1,3'''),
        'por_estado': consultar(connection, 'SELECT estado_geometria,estado_ambito,count(*) filas FROM poi_elementos GROUP BY 1,2 ORDER BY 1,2'),
        'fuera_ambito_mas_distantes': consultar(connection, '''SELECT capa_origen,fid_origen,osm_id,categoria_origen,nombre_origen,
            distancia_ambito_m FROM poi_elementos WHERE estado_ambito='fuera_cv' ORDER BY distancia_ambito_m DESC LIMIT 20'''),
        'identificadores_repetidos_por_capa': consultar(connection, '''SELECT capa_origen,count(*) ids_repetidos,sum(n-1) filas_adicionales
            FROM (SELECT capa_origen,osm_id,count(*) n FROM poi_elementos GROUP BY 1,2 HAVING count(*)>1) GROUP BY 1 ORDER BY 1'''),
        'correspondencias': consultar(connection, '''SELECT punto_intersecta_area,coincide_id_publicado,
            coincide_nombre_normalizado,count(*) pares FROM poi_correspondencias GROUP BY 1,2,3 ORDER BY 1,2,3'''),
        'incidencias': consultar(connection, 'SELECT campo,motivo,count(*) filas FROM incidencias GROUP BY 1,2 ORDER BY 1,2')}
