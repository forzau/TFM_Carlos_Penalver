"""Tres controles espaciales Gold, sin fusionar candidatos ni inferir oferta exterior."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from auditar_fuentes import ident, query
from catalogar_bronze import ROOT
from georreferenciar_recarga import checked
from preparar_demografia_parque import check_key
from preparar_gold_candidatos import SCENARIOS, KEYS as CANDIDATE_KEYS, load_inputs as load_candidate_inputs
from preparar_recarga_versionada import write_outputs
from validar_silver import require_zero


KEYS = {
    'gold_control_area_recarga': ['version_gold','candidato_id','escenario'],
    'gold_solapamientos_candidatos': ['version_gold','candidato_a_id','candidato_b_id'],
    'gold_control_borde': ['version_gold','candidato_id','escenario']}


def load_inputs(c, root):
    files, reports = load_candidate_inputs(c, root)
    directory = root/'resultados/gold/candidatos'
    pointer = directory/'actual.json'
    files.append(checked(root,pointer))
    selected = json.loads(pointer.read_text(encoding='utf-8'))
    path = (directory/selected['manifiesto']).resolve()
    if (not path.is_relative_to(directory.resolve()) or path.parent.name!=selected['ejecucion']
            or path.name!='manifiesto.json'):
        raise ValueError('Manifiesto de candidatos fuera de su ejecución')
    files.append(checked(root,path))
    manifest = json.loads(path.read_text(encoding='utf-8'))
    status_path = (directory/selected['informe']).resolve()
    if status_path!=path.parent/'informe.json':
        raise ValueError('Informe de candidatos fuera de su ejecución')
    files.append(checked(root,status_path))
    status = json.loads(status_path.read_text(encoding='utf-8'))
    if (manifest['version_gold']!=selected['ejecucion'] or status['version_gold']!=selected['ejecucion']
            or status['estado'] not in ('preparada','preparada_con_limitaciones')):
        raise ValueError('Candidatos no preparados o de otra ejecución')
    if manifest['ejecuciones']['gold/contexto_municipal']!=reports['gold/contexto_municipal']['version_gold']:
        raise ValueError('Candidatos y contexto municipal incompatibles')
    for name in CANDIDATE_KEYS:
        entry = next(x for x in manifest['salidas'] if x['archivo']==name+'.parquet')
        source = path.parent/entry['archivo']
        files.append(checked(root,source,entry))
        c.execute(f'CREATE TEMP TABLE {ident(name)} AS SELECT * FROM read_parquet(?)',[str(source)])
        if c.execute(f'SELECT count(*) FROM {name}').fetchone()[0]!=entry['filas']:
            raise ValueError('Recuento de candidatos distinto de su manifiesto')
        if c.execute(f'SELECT count(*) FROM {name} WHERE version_gold IS DISTINCT FROM ?',
                     [selected['ejecucion']]).fetchone()[0]:
            raise ValueError('Filas de otra versión de candidatos')
    for entry in manifest['entradas_verificadas']:
        files.append(checked(root,root/entry['ruta'],entry))
    return files, reports, manifest


def prepare(c, version):
    for name, keys in (
        ('gold_candidatos',['candidato_id']),('gold_municipios',['codigo_municipio']),
        ('gold_recarga_instalaciones',['instalacion_id']),
        ('gold_proximidad_candidato_recarga',['candidato_id','escenario'])):
        check_key(c,name,keys)
    for name, fields in (('gold_candidatos',('geometria','punto_representativo')),
                         ('gold_municipios',('geometria',)),('gold_recarga_instalaciones',('geometria',))):
        schema = {r[0]:r[1] for r in c.execute('DESCRIBE '+name).fetchall()}
        if any(schema[f]!="GEOMETRY('EPSG:25830')" for f in fields):
            raise ValueError('CRS de entrada no admitido')
    require_zero(c, '''SELECT count(*) FROM gold_candidatos WHERE geometria IS NULL
        OR NOT ST_IsValid(geometria) OR ST_IsEmpty(geometria) OR representacion NOT IN ('punto','area')
        OR (representacion='area' AND ST_Dimension(geometria)<>2)
        OR (representacion='punto' AND ST_GeometryType(geometria)<>'POINT')
        OR (punto_representativo IS NOT NULL AND (NOT ST_IsValid(punto_representativo)
            OR ST_IsEmpty(punto_representativo) OR ST_GeometryType(punto_representativo)<>'POINT'))''', 'Geometría candidata incoherente')
    require_zero(c, '''SELECT count(*) FROM gold_municipios WHERE geometria IS NULL
        OR NOT ST_IsValid(geometria) OR ST_IsEmpty(geometria) OR ST_Dimension(geometria)<>2''', 'Recinto no admitido')
    require_zero(c, '''SELECT count(*) FROM gold_proximidad_candidato_recarga
        ANTI JOIN gold_candidatos USING(candidato_id)''', 'Proximidad huérfana')
    c.execute('CREATE TEMP TABLE escenarios(escenario VARCHAR)')
    c.executemany('INSERT INTO escenarios VALUES (?)',[(x,) for x in SCENARIOS])
    require_zero(c, '''SELECT count(*) FROM ((SELECT candidato_id,escenario FROM gold_candidatos CROSS JOIN escenarios
        EXCEPT SELECT candidato_id,escenario FROM gold_proximidad_candidato_recarga) UNION ALL
        (SELECT candidato_id,escenario FROM gold_proximidad_candidato_recarga EXCEPT
        SELECT candidato_id,escenario FROM gold_candidatos CROSS JOIN escenarios))''', 'Escenarios de proximidad incompletos')
    require_zero(c, '''SELECT count(*) FROM gold_proximidad_candidato_recarga p JOIN gold_candidatos c USING(candidato_id)
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


def validate(c, version):
    optional = {'superficie_interseccion_m2','distancia_borde_cv_m','posible_influencia_exterior'}
    for name,keys in KEYS.items():
        check_key(c,name,keys)
        required = [r[0] for r in c.execute('DESCRIBE '+name).fetchall() if r[0] not in optional]
        require_zero(c,f'SELECT count(*) FROM {name} WHERE '+' OR '.join(ident(x)+' IS NULL' for x in required), 'Campo de control obligatorio nulo')
        if c.execute(f'SELECT count(*) FROM {name} WHERE version_gold<>?',[version]).fetchone()[0]:
            raise ValueError('Versión de control incorrecta')
    require_zero(c, '''SELECT count(*) FROM ((SELECT candidato_id,escenario FROM areas CROSS JOIN escenarios EXCEPT
        SELECT candidato_id,escenario FROM gold_control_area_recarga) UNION ALL
        (SELECT candidato_id,escenario FROM gold_control_area_recarga EXCEPT SELECT candidato_id,escenario FROM areas CROSS JOIN escenarios))''', 'Cobertura de áreas incompleta')
    require_zero(c, '''SELECT count(*) FROM gold_control_area_recarga r WHERE
        r.instalaciones_intersectan<>len(r.instalaciones_ids)
        OR r.instalaciones_ids<>list_sort(list_distinct(r.instalaciones_ids))''', 'Coincidencias de área no reconciliadas')
    c.execute('''CREATE OR REPLACE TEMP TABLE coincidencias_recalculadas AS
        SELECT a.candidato_id,o.escenario,o.instalacion_id FROM areas a
        JOIN oferta o ON ST_Intersects(a.geometria,o.geometria)''')
    require_zero(c, '''SELECT count(*) FROM ((SELECT candidato_id,escenario,unnest(instalaciones_ids) instalacion_id
        FROM gold_control_area_recarga EXCEPT ALL SELECT * FROM coincidencias_recalculadas) UNION ALL
        (SELECT * FROM coincidencias_recalculadas EXCEPT ALL SELECT candidato_id,escenario,unnest(instalaciones_ids)
        FROM gold_control_area_recarga))''', 'Coincidencias de área no reconciliadas')
    require_zero(c, '''SELECT count(*) FROM gold_solapamientos_candidatos x
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
    require_zero(c, '''SELECT count(*) FROM gold_correspondencias_candidatos p WHERE p.punto_intersecta_area
        AND NOT EXISTS(SELECT 1 FROM gold_solapamientos_candidatos s WHERE
        s.candidato_a_id=least(p.candidato_punto_id,p.candidato_area_id)
        AND s.candidato_b_id=greatest(p.candidato_punto_id,p.candidato_area_id))''', 'Correspondencia espacial previa omitida')
    require_zero(c, '''SELECT count(*) FROM ((SELECT candidato_id,escenario FROM gold_proximidad_candidato_recarga EXCEPT
        SELECT candidato_id,escenario FROM gold_control_borde) UNION ALL (SELECT candidato_id,escenario FROM gold_control_borde
        EXCEPT SELECT candidato_id,escenario FROM gold_proximidad_candidato_recarga))''', 'Cobertura de borde incompleta')
    require_zero(c, '''SELECT count(*) FROM gold_control_borde b JOIN gold_proximidad_candidato_recarga p USING(candidato_id,escenario)
        JOIN gold_candidatos c USING(candidato_id) CROSS JOIN ambito_cv a WHERE
        b.estado_control<>p.estado_distancia OR b.distancia_borde_cv_m IS DISTINCT FROM
            CASE WHEN c.punto_representativo IS NOT NULL THEN ST_Distance(c.punto_representativo,ST_Boundary(a.geometria)) END
        OR (b.distancia_borde_cv_m IS NOT NULL AND (NOT isfinite(b.distancia_borde_cv_m) OR b.distancia_borde_cv_m<0))
        OR b.posible_influencia_exterior IS DISTINCT FROM CASE WHEN p.estado_distancia='calculable'
            THEN p.distancia_plana_m>b.distancia_borde_cv_m END''', 'Control de borde incoherente')
    return {'tablas':{n:c.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in KEYS},
        'areas':query(c,'''SELECT escenario,count(*) areas,count(*) FILTER(WHERE instalaciones_intersectan>0) con_coincidencia,
            sum(instalaciones_intersectan) relaciones_area_instalacion FROM gold_control_area_recarga GROUP BY 1 ORDER BY 1'''),
        'solapamientos':query(c,'''SELECT dimension_interseccion,misma_categoria,misma_representacion,count(*) pares
            FROM gold_solapamientos_candidatos GROUP BY 1,2,3 ORDER BY 1,2,3'''),
        'borde':query(c,'''SELECT escenario,estado_control,count(*) elementos,
            count(*) FILTER(WHERE posible_influencia_exterior) avisos FROM gold_control_borde GROUP BY 1,2 ORDER BY 1,2''')}


def main():
    directory = ROOT/'resultados/gold/controles_espaciales'
    directory.mkdir(parents=True,exist_ok=True)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = directory/run
    codes = [checked(ROOT,ROOT/'src'/n) for n in ('preparar_controles_gold.py','preparar_gold_candidatos.py',
        'preparar_recarga_versionada.py','georreferenciar_recarga.py','preparar_demografia_parque.py',
        'catalogar_bronze.py','auditar_fuentes.py','validar_silver.py')]
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        with duckdb.connect(str(Path(tmp)/'trabajo.duckdb'),config={'extension_directory':str(ROOT/'.venv/duckdb_extensions'),
            'storage_compatibility_version':'v1.5.0','threads':2,'memory_limit':'1GB',
            'temp_directory':str(Path(tmp)/'desborde')}) as c:
            c.execute('LOAD spatial')
            files,reports,candidates = load_inputs(c,ROOT)
            prepare(c,run)
            quality = validate(c,run)
            outputs = write_outputs(c,target,KEYS)
            environment = {'duckdb':duckdb.__version__,'spatial':c.execute(
                "SELECT extension_version FROM duckdb_extensions() WHERE extension_name='spatial'").fetchone()[0],
                'memoria_motor':'1GB','hilos':2}
    unique = {}
    for entry in [*files,*codes]:
        if entry['ruta'] in unique and any(entry[k]!=unique[entry['ruta']][k] for k in ('bytes','sha256')):
            raise ValueError('Entrada modificada entre lecturas')
        unique[entry['ruta']] = checked(ROOT,ROOT/entry['ruta'],entry)
    limitations = ['Intersecciones cartográficas, no identidad, acceso público o aptitud física acreditados.',
        'Un par de solapamiento no se fusiona ni se resta de recuentos de sitios únicos.',
        'El aviso de borde compara distancia a recarga y borde CV; puede activarse cerca de costa.',
        'No verifica cargadores exteriores, no completa inventario ni modifica distancias anteriores.',
        'Pendientes e históricos solo en sus escenarios; sin operación confirmada, ranking o pesos.']
    manifest = {'version_contrato':1,'version_gold':run,'fecha_proceso_utc':datetime.now(timezone.utc).isoformat(),
        'versiones_gold':{'contexto_municipal':reports['gold/contexto_municipal']['version_gold'],'candidatos':candidates['version_gold']},
        'entradas_verificadas':list(unique.values()),'periodos':candidates['periodos_gold_municipal'],
        'instantanea_osm':candidates['instantanea_osm'],'codigo':codes,'salidas':outputs,'controles':quality,'entorno':environment,
        'reglas':{'area_recarga':'Todas las áreas, tres escenarios; ST_Intersects con geometrías de instalación admitidas; IDs distintos ordenados.',
            'solapamientos':'Todos los pares que intersectan, A<B; dimensión, superficie cuando es área y ST_Covers en ambas direcciones.',
            'borde':'Distancia plana EPSG:25830 al borde de unión de recintos CV; aviso si distancia a recarga es estrictamente mayor.',
            'unidades':'Metros y metros cuadrados; sin recorridos por red.'},'limitaciones':limitations}
    (target/'manifiesto.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (target/'informe.json').write_text(json.dumps({'version_gold':run,'estado':'preparada_con_limitaciones',
        'calidad':quality,'limitaciones':limitations},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pointer = directory/'actual.tmp'
    pointer.write_text(json.dumps({'ejecucion':run,'manifiesto':f'{run}/manifiesto.json','informe':f'{run}/informe.json'},indent=2)+'\n',encoding='utf-8')
    pointer.replace(directory/'actual.json')
    print(json.dumps(quality,ensure_ascii=False,indent=2))
    print('Informe:',(target/'informe.json').relative_to(ROOT).as_posix())


if __name__=='__main__':
    main()
