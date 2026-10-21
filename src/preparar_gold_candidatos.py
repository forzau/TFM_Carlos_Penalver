"""Materializa candidatos OSM y proximidad por escenarios, sin ranking ni red."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from auditar_fuentes import ident, query
from catalogar_bronze import ROOT
from georreferenciar_recarga import checked
from preparar_demografia_parque import check_key
from preparar_poi_osm import CATEGORIES
from preparar_recarga_versionada import write_outputs
from validar_silver import require_zero


KEYS = {
    'gold_candidatos': ['version_gold', 'candidato_id'],
    'gold_candidato_municipio': ['version_gold', 'candidato_id', 'codigo_municipio'],
    'gold_correspondencias_candidatos': ['version_gold', 'candidato_punto_id', 'candidato_area_id'],
    'gold_proximidad_candidato_recarga': ['version_gold', 'candidato_id', 'escenario']}
SCENARIOS = ('principal_admitida', 'incluye_pendientes', 'incluye_ausentes_historicas')
SOURCES = {
    'silver/poi_osm': ['poi_elementos', 'poi_correspondencias'],
    'silver/base_territorial': ['recintos_municipales'],
    'silver/validacion_conjunta': ['relaciones_espaciales'],
    'gold/contexto_municipal': ['gold_municipios', 'gold_recarga_instalaciones']}


def load_inputs(c, root):
    files, reports = [], {}
    for block, names in SOURCES.items():
        directory = root / 'resultados' / block
        pointer = directory / 'actual.json'
        files.append(checked(root, pointer))
        selection = json.loads(pointer.read_text(encoding='utf-8'))
        field = 'manifiesto' if block.startswith('gold/') else 'informe'
        path = (directory / selection[field]).resolve()
        if (not path.is_relative_to(directory.resolve()) or path.parent.name != selection['ejecucion']
                or path.name != field + '.json'):
            raise ValueError('Referencia de entrada fuera del bloque o de su ejecución')
        files.append(checked(root, path))
        report = json.loads(path.read_text(encoding='utf-8'))
        if report.get('ejecucion', report.get('version_gold')) != selection['ejecucion']:
            raise ValueError('El informe no corresponde a la ejecución seleccionada')
        if block.startswith('gold/'):
            status_path = (directory / selection['informe']).resolve()
            if status_path != path.parent / 'informe.json':
                raise ValueError('Informe Gold fuera de la ejecución seleccionada')
            files.append(checked(root, status_path))
            status = json.loads(status_path.read_text(encoding='utf-8'))
            if status['version_gold'] != selection['ejecucion']:
                raise ValueError('Informe Gold de otra ejecución')
        else:
            status = report
        if status['estado'] not in ('preparada', 'preparada_con_limitaciones'):
            raise ValueError('Entrada no preparada')
        reports[block] = report
        for name in names:
            entry = next(x for x in report['salidas'] if x['archivo'] == name + '.parquet')
            if Path(entry['archivo']).name != entry['archivo']:
                raise ValueError('Salida de entrada fuera de su carpeta')
            table_path = path.parent / entry['archivo']
            files.append(checked(root, table_path, entry))
            where = " WHERE tabla_entidad='poi_elementos'" if name == 'relaciones_espaciales' else ''
            c.execute(f'CREATE TEMP TABLE {ident(name)} AS SELECT * FROM read_parquet(?)' + where, [str(table_path)])
            if not where and 'filas' in entry:
                if c.execute('SELECT count(*) FROM ' + ident(name)).fetchone()[0] != entry['filas']:
                    raise ValueError('Recuento distinto de la entrada declarada')
            if block.startswith('gold/'):
                if c.execute(f'SELECT count(*) FROM {name} WHERE version_gold IS DISTINCT FROM ?', [selection['ejecucion']]).fetchone()[0]:
                    raise ValueError('Filas Gold de otra ejecución')
    joint = reports['silver/validacion_conjunta']['entradas_verificadas']
    for entry in files:
        if entry['ruta'].startswith(('resultados/silver/poi_osm/', 'resultados/silver/base_territorial/')):
            historical = next((x for x in joint if x['ruta'] == entry['ruta']), None)
            if historical is None or any(historical[k] != entry[k] for k in ('bytes', 'sha256')):
                raise ValueError('Relaciones OSM de una versión territorial o POI distinta')
    gold = reports['gold/contexto_municipal']
    if gold['ejecuciones_silver']['base_territorial'] != reports['silver/base_territorial']['ejecucion']:
        raise ValueError('Gold municipal de otra base territorial')
    for entry in gold['entradas_verificadas']:
        files.append(checked(root, root / entry['ruta'], entry))
    return files, reports


def prepare(c, version):
    for table, keys in (
        ('poi_elementos', ['origen_id', 'fid_origen']),
        ('poi_correspondencias', ['origen_punto', 'fid_punto', 'origen_area', 'fid_area']),
        ('recintos_municipales', ['codigo_municipio']), ('gold_municipios', ['codigo_municipio']),
        ('gold_recarga_instalaciones', ['instalacion_id']),
        ('relaciones_espaciales', ['tabla_entidad', 'clave_entidad', 'codigo_municipio'])):
        check_key(c, table, keys)
    require_zero(c, '''SELECT count(*) FROM ((SELECT codigo_municipio FROM recintos_municipales EXCEPT
        SELECT codigo_municipio FROM gold_municipios) UNION ALL (SELECT codigo_municipio FROM gold_municipios
        EXCEPT SELECT codigo_municipio FROM recintos_municipales))''', 'Bases municipales diferentes')
    c.execute('''CREATE TEMP TABLE seleccion AS SELECT *,
        to_json(list_value(origen_id,cast(fid_origen AS VARCHAR)))::VARCHAR candidato_id
        FROM poi_elementos WHERE interes_para_revision AND grupo_uso IN ('aparcamiento','comercio','alojamiento')''')
    c.execute('CREATE TEMP TABLE reglas(categoria VARCHAR,codigo VARCHAR,grupo VARCHAR)')
    c.executemany('INSERT INTO reglas VALUES (?,?,?)', [(k, *v) for k, v in CATEGORIES.items()])
    require_zero(c, '''SELECT count(*) FROM seleccion s LEFT JOIN reglas r ON s.categoria_origen=r.categoria
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


def proximity(c, version):
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
        for scenario in SCENARIOS:
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


def validate(c, version):
    nullable = {'osm_id','nombre_origen','punto_representativo','codigo_municipio_contexto',
                'superficie_interseccion_m2','instalacion_id_mas_cercana','distancia_plana_m'}
    for name, keys in KEYS.items():
        check_key(c, name, keys)
        columns = [r[0] for r in c.execute('DESCRIBE ' + name).fetchall()]
        required = [x for x in columns if x not in nullable or (name=='gold_correspondencias_candidatos' and x=='distancia_plana_m')]
        require_zero(c, f'SELECT count(*) FROM {name} WHERE ' + ' OR '.join(ident(x)+' IS NULL' for x in required), 'Campo obligatorio nulo')
        if c.execute(f'SELECT count(*) FROM {name} WHERE version_gold<>?', [version]).fetchone()[0]:
            raise ValueError('Versión de salida incorrecta')
    require_zero(c, '''SELECT count(*) FROM ((SELECT candidato_id FROM seleccion EXCEPT SELECT candidato_id FROM gold_candidatos)
        UNION ALL (SELECT candidato_id FROM gold_candidatos EXCEPT SELECT candidato_id FROM seleccion))''', 'Selección de candidatos alterada')
    source_fields = ('origen_id','capa_origen','fid_origen','osm_id','nombre_origen','categoria_origen','grupo_uso','representacion')
    require_zero(c, '''SELECT count(*) FROM gold_candidatos c JOIN seleccion s USING(candidato_id) WHERE ''' +
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
        fields = ','.join(ident(r[0]) for r in c.execute('DESCRIBE ' + name).fetchall() if r[0]!='version_gold')
        require_zero(c, f'''SELECT count(*) FROM (({expected} EXCEPT ALL SELECT {fields} FROM {name})
            UNION ALL (SELECT {fields} FROM {name} EXCEPT ALL {expected}))''', 'Relaciones Silver alteradas')
    for name, field in (('gold_candidato_municipio','candidato_id'), ('gold_correspondencias_candidatos','candidato_punto_id'),
                        ('gold_correspondencias_candidatos','candidato_area_id'), ('gold_proximidad_candidato_recarga','candidato_id')):
        require_zero(c, f'SELECT count(*) FROM {name} x ANTI JOIN gold_candidatos c ON x.{field}=c.candidato_id', 'Candidato huérfano')
    require_zero(c, '''SELECT count(*) FROM gold_candidato_municipio ANTI JOIN gold_municipios USING(codigo_municipio)''', 'Municipio huérfano')
    require_zero(c, '''SELECT count(*) FROM gold_candidatos c LEFT JOIN (
        SELECT candidato_id,count(*) n,min(codigo_municipio) codigo FROM gold_candidato_municipio GROUP BY 1) m USING(candidato_id)
        WHERE m.n IS NULL OR c.numero_municipios_relacionados<>m.n
        OR c.codigo_municipio_contexto IS DISTINCT FROM CASE WHEN m.n=1 THEN m.codigo END
        OR c.estado_relacion_municipal<>CASE WHEN m.n=1 THEN 'interseccion_unica' ELSE 'interseccion_multiple' END''', 'Contexto municipal incoherente')
    require_zero(c, '''SELECT count(*) FROM gold_candidatos c LEFT JOIN (
        SELECT candidato_id,count(*) n FROM (SELECT candidato_punto_id candidato_id FROM gold_correspondencias_candidatos
        UNION ALL SELECT candidato_area_id FROM gold_correspondencias_candidatos) GROUP BY 1) p USING(candidato_id)
        WHERE c.numero_correspondencias<>coalesce(p.n,0)''', 'Recuento de correspondencias incoherente')
    require_zero(c, '''SELECT count(*) FROM gold_correspondencias_candidatos r
        JOIN gold_candidatos p ON p.candidato_id=r.candidato_punto_id JOIN gold_candidatos a ON a.candidato_id=r.candidato_area_id
        WHERE p.representacion<>'punto' OR a.representacion<>'area' OR p.categoria_origen<>a.categoria_origen
        OR r.estado<>'posible_correspondencia_sin_fusion' OR NOT isfinite(r.distancia_plana_m) OR r.distancia_plana_m<0''', 'Correspondencia incoherente')
    require_zero(c, '''SELECT count(*) FROM gold_candidatos c JOIN representaciones s USING(candidato_id)
        WHERE ST_AsWKB(c.geometria)<>ST_AsWKB(s.geometria)
        OR (c.punto_representativo IS NULL)<>(c.metodo_representacion='sin_superficie_en_cv')
        OR (c.punto_representativo IS NOT NULL AND (NOT ST_IsValid(c.punto_representativo)
            OR ST_IsEmpty(c.punto_representativo) OR ST_GeometryType(c.punto_representativo)<>'POINT'
            OR NOT ST_Intersects(c.punto_representativo,s.area_analisis)
            OR NOT ST_Intersects(c.punto_representativo,c.geometria)))''', 'Representación geométrica incoherente')
    require_zero(c, '''SELECT count(*) FROM (SELECT c.candidato_id FROM gold_candidatos c
        LEFT JOIN gold_proximidad_candidato_recarga p USING(candidato_id)
        GROUP BY c.candidato_id HAVING count(p.escenario)<>3 OR count(DISTINCT p.escenario)<>3)''', 'Deben existir tres escenarios por candidato')
    require_zero(c, '''SELECT count(*) FROM gold_proximidad_candidato_recarga p JOIN gold_candidatos c USING(candidato_id)
        LEFT JOIN oferta_admisible r ON p.instalacion_id_mas_cercana=r.instalacion_id AND p.escenario=r.escenario
        WHERE p.escenario NOT IN ('principal_admitida','incluye_pendientes','incluye_ausentes_historicas')
        OR p.estado_distancia<>CASE WHEN c.punto_representativo IS NULL THEN 'sin_posicion_representativa'
            WHEN NOT EXISTS(SELECT 1 FROM oferta_admisible o WHERE o.escenario=p.escenario) THEN 'sin_recarga_admisible' ELSE 'calculable' END
        OR (p.estado_distancia='calculable' AND (r.instalacion_id IS NULL OR p.distancia_plana_m IS NULL
            OR NOT isfinite(p.distancia_plana_m) OR p.distancia_plana_m<0 OR p.numero_instalaciones_a_distancia_minima<1
            OR p.distancia_plana_m<>ST_Distance(c.punto_representativo,r.geometria)))
        OR (p.estado_distancia<>'calculable' AND (p.distancia_plana_m IS NOT NULL
            OR p.instalacion_id_mas_cercana IS NOT NULL OR p.numero_instalaciones_a_distancia_minima<>0))''', 'Distancia, vecino o estado incoherente')
    require_zero(c, '''SELECT count(*) FROM gold_proximidad_candidato_recarga a JOIN gold_proximidad_candidato_recarga b USING(candidato_id)
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
    return {'tablas': {n:c.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in KEYS},
        'categorias': query(c,'SELECT grupo_uso,representacion,count(*) elementos FROM gold_candidatos GROUP BY 1,2 ORDER BY 1,2'),
        'municipios_con_elementos': c.execute('SELECT count(DISTINCT codigo_municipio) FROM gold_candidato_municipio').fetchone()[0],
        'relacion_municipal': query(c,'SELECT numero_municipios_relacionados,count(*) elementos FROM gold_candidatos GROUP BY 1 ORDER BY 1'),
        'representacion': query(c,'SELECT metodo_representacion,count(*) elementos FROM gold_candidatos GROUP BY 1 ORDER BY 1'),
        'oferta': query(c,'''SELECT e.escenario,count(*) instalaciones,count(a.instalacion_id) admisibles,
            count(*)-count(a.instalacion_id) excluidas FROM oferta_escenarios e LEFT JOIN oferta_admisible a USING(escenario,instalacion_id) GROUP BY 1 ORDER BY 1'''),
        'proximidad': query(c,'''SELECT escenario,estado_distancia,count(*) elementos,min(distancia_plana_m) minimo_m,
            median(distancia_plana_m) mediana_m,max(distancia_plana_m) maximo_m FROM gold_proximidad_candidato_recarga GROUP BY 1,2 ORDER BY 1,2''')}


def validate_exports(c, target):
    for name in KEYS:
        path = target / (name + '.parquet')
        schema = c.execute('DESCRIBE ' + name).fetchall()
        geom = [r[0] for r in schema if r[1].startswith('GEOMETRY')]
        if geom:
            metadata = dict(c.execute('SELECT decode(key),decode(value) FROM parquet_kv_metadata(?)', [str(path)]).fetchall())
            for field in geom:
                if json.loads(metadata['geo'])['columns'][field]['crs']['id'] != {'authority':'EPSG','code':25830}:
                    raise ValueError('CRS de salida incorrecto')
            fields = ','.join(f'ST_AsWKB({ident(r[0])})' if r[0] in geom else ident(r[0]) for r in schema)
            if c.execute(f'''SELECT count(*) FROM ((SELECT {fields} FROM {name} EXCEPT ALL
                SELECT {fields} FROM read_parquet(?)) UNION ALL
                (SELECT {fields} FROM read_parquet(?) EXCEPT ALL SELECT {fields} FROM {name}))''',
                [str(path),str(path)]).fetchone()[0]:
                raise ValueError('Geometrías exportadas alteradas')


def main():
    directory = ROOT / 'resultados/gold/candidatos'
    directory.mkdir(parents=True, exist_ok=True)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = directory / run
    codes = [checked(ROOT, ROOT/'src'/n) for n in ('preparar_gold_candidatos.py','preparar_poi_osm.py',
        'preparar_recarga_versionada.py','preparar_demografia_parque.py','georreferenciar_recarga.py',
        'auditar_fuentes.py','catalogar_bronze.py','validar_silver.py')]
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        with duckdb.connect(str(Path(tmp)/'trabajo.duckdb'),config={'threads':2,'memory_limit':'1GB',
            'storage_compatibility_version':'v1.5.0','temp_directory':str(Path(tmp)/'desborde'),
            'extension_directory':str(ROOT/'.venv/duckdb_extensions')}) as c:
            c.execute('LOAD spatial')
            files, reports = load_inputs(c, ROOT)
            prepare(c, run)
            proximity(c, run)
            quality = validate(c, run)
            outputs = write_outputs(c, target, KEYS)
            validate_exports(c, target)
            environment = {'duckdb':duckdb.__version__,'spatial':c.execute("SELECT extension_version FROM duckdb_extensions() WHERE extension_name='spatial'").fetchone()[0],
                           'memoria_motor':'1GB','hilos':2}
    unique = {}
    for entry in [*files,*codes]:
        if entry['ruta'] in unique and any(entry[k]!=unique[entry['ruta']][k] for k in ('bytes','sha256')):
            raise ValueError('Entrada modificada entre lecturas')
        unique[entry['ruta']] = checked(ROOT, ROOT/entry['ruta'], entry)
    manifest = {'version_contrato':1,'version_gold':run,'fecha_proceso_utc':datetime.now(timezone.utc).isoformat(),
        'entradas_verificadas':list(unique.values()),'ejecuciones':{k:v.get('ejecucion',v.get('version_gold')) for k,v in reports.items()},
        'periodos_gold_municipal':reports['gold/contexto_municipal']['periodos'],
        'instantanea_osm':reports['silver/poi_osm']['instantanea_osm'],
        'reglas':{'seleccion':"interes_para_revision AND grupo_uso IN ('aparcamiento','comercio','alojamiento')",
            'representacion':'Punto original o ST_PointOnSurface(intersección área/CV); conservar original y municipios múltiples.',
            'correspondencias':'Sin fusión; ambos extremos preseleccionados.',
            'escenarios':list(SCENARIOS),'distancia':'Mínima plana EPSG:25830 a instalación admisible en toda CV, sin redondear; empates por ID lexicográfico.'},
        'codigo':codes,'salidas':outputs,'controles':quality,'entorno':environment}
    limitations = ['Elementos OSM preseleccionados, no lugares únicos ni aptitud o acceso público acreditados.',
        'Distancia geométrica en metros, no recorrido, cobertura de personas o suficiencia operativa.',
        'Inventario de recarga limitado a CV: puede faltar oferta más próxima de otras comunidades.',
        'Pendientes y ausentes solo como sensibilidad, sin confirmar operación; periodos distintos.',
        'Sin reparto de demanda municipal entre POI, radios, ranking o pesos.']
    manifest['limitaciones'] = limitations
    (target/'manifiesto.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (target/'informe.json').write_text(json.dumps({'version_gold':run,'estado':'preparada_con_limitaciones',
        'calidad':quality,'limitaciones':limitations},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pointer = directory/'actual.tmp'
    pointer.write_text(json.dumps({'ejecucion':run,'manifiesto':f'{run}/manifiesto.json','informe':f'{run}/informe.json'},indent=2)+'\n',encoding='utf-8')
    pointer.replace(directory/'actual.json')
    print(json.dumps(quality,ensure_ascii=False,indent=2))
    print('Informe:',(target/'informe.json').relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
