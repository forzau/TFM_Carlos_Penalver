"""Variables Gold y referencias fijas por versión; sin ponderación ni ranking."""

import json
import math
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from auditar_fuentes import ident, query
from catalogar_bronze import ROOT
from georreferenciar_recarga import checked
from preparar_controles_gold import KEYS as CONTROL_KEYS, load_inputs as load_candidate_inputs
from preparar_demografia_parque import check_key
from preparar_gold_candidatos import SCENARIOS
from preparar_recarga_versionada import write_outputs
from validar_silver import require_zero


KEYS = {
    'gold_referencias_normalizacion': ['version_gold', 'dimension'],
    'gold_variables_municipio': ['version_gold', 'codigo_municipio'],
    'gold_variables_candidato': ['version_gold', 'candidato_id', 'escenario']}


def load_inputs(c, root):
    files, reports, candidates = load_candidate_inputs(c, root)
    directory = root/'resultados/gold/controles_espaciales'
    pointer = directory/'actual.json'
    files.append(checked(root, pointer))
    selected = json.loads(pointer.read_text(encoding='utf-8'))
    path = (directory/selected['manifiesto']).resolve()
    if (not path.is_relative_to(directory.resolve()) or path.parent.name != selected['ejecucion']
            or path.name != 'manifiesto.json'):
        raise ValueError('Manifiesto de controles fuera de su ejecución')
    status_path = (directory/selected['informe']).resolve()
    if status_path != path.parent/'informe.json':
        raise ValueError('Informe de controles fuera de su ejecución')
    files.extend([checked(root, path), checked(root, status_path)])
    manifest = json.loads(path.read_text(encoding='utf-8'))
    status = json.loads(status_path.read_text(encoding='utf-8'))
    if (manifest['version_gold'] != selected['ejecucion'] or status['version_gold'] != selected['ejecucion']
            or status['estado'] not in ('preparada', 'preparada_con_limitaciones')):
        raise ValueError('Controles no preparados o de otra ejecución')
    versions = {'contexto_municipal': reports['gold/contexto_municipal']['version_gold'],
                'candidatos': candidates['version_gold']}
    if manifest['versiones_gold'] != versions:
        raise ValueError('Controles y entradas Gold incompatibles')
    for name in CONTROL_KEYS:
        entry = next(x for x in manifest['salidas'] if x['archivo'] == name+'.parquet')
        source = path.parent/entry['archivo']
        files.append(checked(root, source, entry))
        c.execute(f'CREATE TEMP TABLE {ident(name)} AS SELECT * FROM read_parquet(?)', [str(source)])
        if (c.execute(f'SELECT count(*) FROM {name}').fetchone()[0] != entry['filas']
                or c.execute(f'SELECT count(*) FROM {name} WHERE version_gold IS DISTINCT FROM ?',
                             [selected['ejecucion']]).fetchone()[0]):
            raise ValueError('Filas de controles distintas de su manifiesto')
    for entry in manifest['entradas_verificadas']:
        files.append(checked(root, root/entry['ruta'], entry))
    return files, candidates, {**versions, 'controles_espaciales': manifest['version_gold']}


def prepare(c, version):
    for name, keys in (('gold_municipios', ['codigo_municipio']), ('gold_candidatos', ['candidato_id']),
                       ('gold_recarga_instalaciones', ['instalacion_id']),
                       ('gold_proximidad_candidato_recarga', ['candidato_id', 'escenario'])):
        check_key(c, name, keys)
    for name in ('gold_municipios', 'gold_candidatos', 'gold_recarga_instalaciones'):
        schema = {r[0]:r[1] for r in c.execute('DESCRIBE '+name).fetchall()}
        if schema['geometria'] != "GEOMETRY('EPSG:25830')":
            raise ValueError('CRS de entrada no admitido')
    require_zero(c, '''SELECT count(*) FROM gold_municipios WHERE geometria IS NULL
        OR NOT ST_IsValid(geometria) OR ST_IsEmpty(geometria) OR ST_Dimension(geometria)<>2''', 'Recinto no admitido')
    require_zero(c, '''SELECT count(*) FROM gold_candidatos x LEFT JOIN gold_municipios m
        ON x.codigo_municipio_contexto=m.codigo_municipio WHERE
        (x.numero_municipios_relacionados=1 AND (x.codigo_municipio_contexto IS NULL OR m.codigo_municipio IS NULL))
        OR (x.numero_municipios_relacionados<>1 AND x.codigo_municipio_contexto IS NOT NULL)''', 'Contexto municipal incoherente')
    c.execute('CREATE TEMP TABLE escenarios(escenario VARCHAR)')
    c.executemany('INSERT INTO escenarios VALUES (?)', [(x,) for x in SCENARIOS])
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
    check_key(c,'gold_control_borde',['candidato_id','escenario'])
    c.execute('''CREATE TEMP TABLE cotas_borde AS SELECT candidato_id,distancia_borde_cv_m cota
        FROM gold_control_borde WHERE escenario='principal_admitida' ''')
    require_zero(c, '''SELECT count(*) FROM evaluables x LEFT JOIN cotas_borde b USING(candidato_id)
        WHERE estado_geometria_variable='calculable' AND (b.cota IS NULL OR NOT isfinite(b.cota) OR b.cota<0
            OR x.punto_representativo IS NULL OR NOT ST_Intersects(x.geometria,x.punto_representativo))''', 'Cota de borde no admisible')
    # El representante pertenece al área: su distancia acota el mínimo; el recorte conserva el borde más cercano.
    c.execute('''CREATE TEMP TABLE bordes_recortados AS SELECT x.candidato_id,ST_Intersection(b.geometria,
        ST_MakeEnvelope(ST_XMin(x.geometria)-r.cota-1,ST_YMin(x.geometria)-r.cota-1,
            ST_XMax(x.geometria)+r.cota+1,ST_YMax(x.geometria)+r.cota+1)) geometria
        FROM evaluables x JOIN cotas_borde r USING(candidato_id) CROSS JOIN borde_cv b
        WHERE estado_geometria_variable='calculable' AND representacion='area' ''')
    require_zero(c, '''SELECT count(*) FROM bordes_recortados WHERE geometria IS NULL
        OR ST_IsEmpty(geometria) OR NOT ST_IsValid(geometria)''', 'Recorte de borde no admisible')
    c.execute('''CREATE TEMP TABLE distancias_borde_geometria AS SELECT x.candidato_id,
        CASE WHEN estado_geometria_variable='calculable' THEN CASE WHEN representacion='punto' THEN r.cota
            ELSE ST_Distance(x.geometria,b.geometria) END END distancia_geometria_borde_cv_m
        FROM evaluables x LEFT JOIN cotas_borde r USING(candidato_id) LEFT JOIN bordes_recortados b USING(candidato_id)''')
    require_zero(c, '''SELECT count(*) FROM distancias_borde_geometria d JOIN evaluables x USING(candidato_id)
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


def validate(c, version):
    for name, keys in KEYS.items():
        check_key(c, name, keys)
        if c.execute(f'SELECT count(*) FROM {name} WHERE version_gold IS DISTINCT FROM ?', [version]).fetchone()[0]:
            raise ValueError('Versión de variables distinta')
    for source, target, fields in (('gold_municipios','gold_variables_municipio','codigo_municipio'),
            ('gold_proximidad_candidato_recarga','gold_variables_candidato','candidato_id,escenario')):
        require_zero(c, f'''SELECT count(*) FROM ((SELECT {fields} FROM {source} EXCEPT SELECT {fields} FROM {target})
            UNION ALL (SELECT {fields} FROM {target} EXCEPT SELECT {fields} FROM {source}))''', 'Cobertura de variables incompleta')
    require_zero(c, '''SELECT count(*) FROM gold_variables_municipio v JOIN gold_municipios m USING(codigo_municipio)
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
    require_zero(c, '''SELECT count(*) FROM gold_variables_candidato v JOIN gold_candidatos x USING(candidato_id)
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
    require_zero(c, '''SELECT count(*) FROM gold_variables_candidato a JOIN gold_variables_candidato b USING(candidato_id)
        WHERE ((a.escenario='principal_admitida' AND b.escenario='incluye_pendientes') OR
            (a.escenario='incluye_pendientes' AND b.escenario='incluye_ausentes_historicas'))
        AND a.distancia_minima_geometria_m<b.distancia_minima_geometria_m''', 'Distancias no monótonas por escenario')
    return {'tablas': {n:c.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in KEYS},
        'referencias': query(c,'SELECT * EXCLUDE(version_gold) FROM gold_referencias_normalizacion ORDER BY dimension'),
        'distancias': query(c,'''SELECT escenario,estado_distancia,count(*) elementos,
            count(*) FILTER(WHERE distancia_minima_geometria_m=0) ceros,median(distancia_minima_geometria_m) mediana_m,
            max(distancia_minima_geometria_m) maximo_m,count(*) FILTER(WHERE posible_influencia_exterior_geometria) avisos_borde
            FROM gold_variables_candidato GROUP BY 1,2 ORDER BY 1,2''')}


def main():
    directory = ROOT/'resultados/gold/variables'
    directory.mkdir(parents=True, exist_ok=True)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = directory/run
    codes = [checked(ROOT,ROOT/'src'/n) for n in ('preparar_variables_gold.py','preparar_controles_gold.py',
        'preparar_gold_candidatos.py','preparar_recarga_versionada.py','georreferenciar_recarga.py',
        'preparar_demografia_parque.py','catalogar_bronze.py','auditar_fuentes.py','validar_silver.py')]
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        with duckdb.connect(str(Path(tmp)/'trabajo.duckdb'), config={'extension_directory':str(ROOT/'.venv/duckdb_extensions'),
                'storage_compatibility_version':'v1.5.0','threads':2,'memory_limit':'1GB',
                'temp_directory':str(Path(tmp)/'desborde')}) as c:
            c.execute('LOAD spatial')
            files, candidates, versions = load_inputs(c,ROOT)
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
    limitations = ['Distintivo 0 municipal no acredita demanda real ni se reparte entre POI.',
        'Distancias planas a geometría original, no acceso, recorridos o suficiencia; áreas extensas pueden resultar favorecidas.',
        'Borde geométrico incluye costa y no verifica oferta exterior; no equivale al aviso del representante.',
        'Log1p usa vehículos y metros; elección de escala con sensibilidad lineal, no porcentaje de déficit.',
        'Sin ponderación, ranking, predicción de uso o aptitud física de emplazamientos.']
    manifest = {'version_contrato':1,'version_gold':run,'fecha_proceso_utc':datetime.now(timezone.utc).isoformat(),
        'versiones_gold':versions,'entradas_verificadas':list(unique.values()),'codigo':codes,
        'periodos':candidates['periodos_gold_municipal'],'instantanea_osm':candidates['instantanea_osm'],
        'salidas':outputs,'controles':quality,'entorno':environment,
        'reglas':{'normalizacion_log':'ln(1+x)/ln(1+M), x en vehículos o metros',
            'normalizacion_lineal':'x/M','referencias':'Universo CV completo, demanda municipal y distancia principal; mismas M en todos los escenarios.',
            'fuera_referencia':'Nulo con estado, sin recorte ni reajuste.',
            'borde':'distancia_minima_geometria_m > distancia_geometria_borde_cv_m; igualdad sin aviso.',
            'contexto':'Demanda almacenada una vez por municipio; unión solo mediante contexto municipal exclusivo.'},
        'limitaciones':limitations}
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
