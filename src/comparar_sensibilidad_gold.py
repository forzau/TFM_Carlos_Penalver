"""Contrasta escalas y escenarios de Gold sin calcular una prioridad combinada."""

import json
from datetime import datetime, timezone

import duckdb

from auditar_fuentes import ident, query
from catalogar_bronze import ROOT
from georreferenciar_recarga import checked
from preparar_demografia_parque import check_key
from preparar_gold_candidatos import SCENARIOS
from validar_silver import require_zero


SOURCES = {'contexto_municipal': ['gold_municipios'], 'candidatos': ['gold_candidatos'],
           'variables': ['gold_variables_municipio','gold_variables_candidato','gold_referencias_normalizacion']}
QUERIES = {
    'distribuciones': '''SELECT dimension,escenario,count(*) observaciones,count(original) originales_conocidos,
        count(normalizado_log) normalizados_conocidos,count(*) FILTER(WHERE original=0) ceros,
        quantile_cont(original,[0,0.25,0.5,0.75,0.9,0.95,0.99,1]) cuantiles_original,
        quantile_cont(normalizado_log,[0,0.25,0.5,0.75,0.9,0.95,0.99,1]) cuantiles_log,
        quantile_cont(normalizado_lineal,[0,0.25,0.5,0.75,0.9,0.95,0.99,1]) cuantiles_lineal,
        avg(normalizado_log-normalizado_lineal) diferencia_media_entre_escalas
        FROM series GROUP BY 1,2 ORDER BY 1,2''',
    'orden_entre_escalas': '''SELECT a.dimension,a.escenario,a.escala escala_a,b.escala escala_b,count(*) pares,
        count(*) FILTER(WHERE a.rango_promedio<>b.rango_promedio) puestos_distintos,
        max(abs(a.rango_promedio-b.rango_promedio)) maxima_diferencia_puesto,
        CASE WHEN max(a.rango_promedio)>min(a.rango_promedio) AND max(b.rango_promedio)>min(b.rango_promedio)
            THEN corr(a.rango_promedio,b.rango_promedio) END spearman
        FROM ordenes a JOIN ordenes b USING(dimension,escenario,entidad_id)
        WHERE (a.escala='original' AND b.escala IN ('log','lineal')) OR (a.escala='log' AND b.escala='lineal')
        GROUP BY 1,2,3,4 ORDER BY 1,2,3,4''',
    'cambios_escenario': '''SELECT a.escenario_base,a.escenario_alternativo,count(*) candidatos,
        count(*) FILTER(WHERE ambos_conocidos) pares_conocidos,
        count(*) FILTER(WHERE NOT ambos_conocidos) pares_desconocidos,
        count(*) FILTER(WHERE reduccion_m>1e-8) distancias_cambian,
        count(*) FILTER(WHERE base_m>0 AND alternativo_m=0) nuevos_ceros,
        median(reduccion_m) reduccion_mediana_todos_m,
        median(reduccion_m) FILTER(WHERE reduccion_m>1e-8) reduccion_mediana_afectados_m,
        max(reduccion_m) reduccion_maxima_m,
        max(reduccion_log) reduccion_log_maxima,max(reduccion_lineal) reduccion_lineal_maxima,
        count(*) FILTER(WHERE rango_base<>rango_alternativo) puestos_cambian,
        median(abs(rango_base-rango_alternativo)) mediana_cambio_puesto,
        quantile_cont(abs(rango_base-rango_alternativo),0.95) p95_cambio_puesto,
        max(abs(rango_base-rango_alternativo)) maximo_cambio_puesto,
        CASE WHEN max(rango_base)>min(rango_base) AND max(rango_alternativo)>min(rango_alternativo)
            THEN corr(rango_base,rango_alternativo) END spearman,
        count(*) FILTER(WHERE top_base) grupo_superior_base,
        count(*) FILTER(WHERE top_alternativo) grupo_superior_alternativo,
        count(*) FILTER(WHERE top_base AND top_alternativo) interseccion_grupos,
        count(*) FILTER(WHERE top_base AND top_alternativo)::DOUBLE /
            nullif(count(*) FILTER(WHERE top_base OR top_alternativo),0) jaccard_grupos
        FROM pares a LEFT JOIN rangos_pares r USING(escenario_base,escenario_alternativo,entidad_id)
        GROUP BY 1,2 ORDER BY 1,2''',
    'segmentos': '''SELECT escenario_base,escenario_alternativo,c.representacion,c.grupo_uso,
        count(*) candidatos,count(*) FILTER(WHERE reduccion_m>1e-8) distancias_cambian,
        max(reduccion_m) reduccion_maxima_m FROM pares p JOIN gold_candidatos c ON c.candidato_id=p.entidad_id
        GROUP BY 1,2,3,4 ORDER BY 1,2,3,4''',
    'ejemplos': '''WITH orden AS (SELECT p.*,c.nombre_origen,c.representacion,c.codigo_municipio_contexto,
        m.nombre_municipio,row_number() OVER(PARTITION BY escenario_base,escenario_alternativo
            ORDER BY reduccion_m DESC,p.entidad_id) posicion
        FROM pares p JOIN gold_candidatos c ON c.candidato_id=p.entidad_id
        LEFT JOIN gold_municipios m ON m.codigo_municipio=c.codigo_municipio_contexto WHERE reduccion_m>1e-8)
        SELECT escenario_base,escenario_alternativo,entidad_id,nombre_origen,representacion,
        codigo_municipio_contexto,nombre_municipio,base_m,alternativo_m,reduccion_m,
        reduccion_m/nullif(base_m,0) fraccion_reduccion_distancia,reduccion_log,reduccion_lineal
        FROM orden WHERE posicion<=5 ORDER BY escenario_base,escenario_alternativo,posicion''',
    'ejemplos_demanda': '''SELECT m.codigo_municipio,m.nombre_municipio,v.vehiculos_distintivo_0,
        v.demanda_normalizada_log,v.demanda_normalizada_lineal FROM gold_variables_municipio v
        JOIN gold_municipios m USING(codigo_municipio)
        WHERE m.codigo_municipio IN ('46250','03014','46103','12087','12141') ORDER BY m.codigo_municipio'''}


def load_inputs(c, root):
    files, manifests = [], {}
    for block, names in SOURCES.items():
        directory = root/'resultados/gold'/block
        pointer = directory/'actual.json'
        files.append(checked(root,pointer))
        selected = json.loads(pointer.read_text(encoding='utf-8'))
        path = (directory/selected['manifiesto']).resolve()
        if not path.is_relative_to(directory.resolve()) or path.parent.name!=selected['ejecucion'] or path.name!='manifiesto.json':
            raise ValueError('Manifiesto fuera del bloque o ejecución')
        status_path = (directory/selected['informe']).resolve()
        if status_path!=path.parent/'informe.json':raise ValueError('Informe fuera de su ejecución')
        files.extend([checked(root,path),checked(root,status_path)])
        manifest=json.loads(path.read_text(encoding='utf-8'))
        status=json.loads(status_path.read_text(encoding='utf-8'))
        if (manifest['version_gold']!=selected['ejecucion'] or status['version_gold']!=selected['ejecucion']
                or status['estado'] not in ('preparada','preparada_con_limitaciones')):
            raise ValueError('Entrada no preparada o de otra versión')
        manifests[block]=manifest
        for name in names:
            entry=next(x for x in manifest['salidas'] if x['archivo']==name+'.parquet')
            source=path.parent/entry['archivo'];files.append(checked(root,source,entry))
            c.execute(f'CREATE TEMP TABLE {ident(name)} AS SELECT * FROM read_parquet(?)',[str(source)])
            if (c.execute(f'SELECT count(*) FROM {name}').fetchone()[0]!=entry['filas']
                    or c.execute(f'SELECT count(*) FROM {name} WHERE version_gold IS DISTINCT FROM ?',
                        [selected['ejecucion']]).fetchone()[0]):raise ValueError('Filas distintas de su manifiesto')
    versions={k:v['version_gold'] for k,v in manifests.items()}
    if (manifests['candidatos']['ejecuciones']['gold/contexto_municipal']!=versions['contexto_municipal']
            or any(manifests['variables']['versiones_gold'][k]!=versions[k] for k in ('contexto_municipal','candidatos'))):
        raise ValueError('Bloques Gold incompatibles')
    for entry in manifests['variables']['entradas_verificadas']:
        files.append(checked(root,root/entry['ruta'],entry))
    return files,manifests


def prepare(c):
    for name,keys in (('gold_variables_municipio',['codigo_municipio']),
            ('gold_variables_candidato',['candidato_id','escenario']),('gold_candidatos',['candidato_id'])):
        check_key(c,name,keys)
    c.execute('''CREATE TEMP TABLE series AS SELECT 'demanda'::VARCHAR dimension,codigo_municipio entidad_id,
        'no_aplica'::VARCHAR escenario,vehiculos_distintivo_0::DOUBLE original,
        demanda_normalizada_log normalizado_log,demanda_normalizada_lineal normalizado_lineal FROM gold_variables_municipio
        UNION ALL SELECT 'proximidad',candidato_id,escenario,distancia_minima_geometria_m,
            proximidad_normalizada_log,proximidad_normalizada_lineal FROM gold_variables_candidato''')
    require_zero(c, '''SELECT count(*) FROM series WHERE (original IS NOT NULL AND (NOT isfinite(original) OR original<0))
        OR (normalizado_log IS NOT NULL AND (NOT isfinite(normalizado_log) OR normalizado_log NOT BETWEEN 0 AND 1))
        OR (normalizado_lineal IS NOT NULL AND (NOT isfinite(normalizado_lineal) OR normalizado_lineal NOT BETWEEN 0 AND 1))
        OR (normalizado_log IS NULL)<>(normalizado_lineal IS NULL)
        OR (original IS NULL AND normalizado_log IS NOT NULL)''', 'Valor no admisible para sensibilidad')
    c.execute('CREATE TEMP TABLE escenarios(escenario VARCHAR)')
    c.executemany('INSERT INTO escenarios VALUES (?)',[(x,) for x in SCENARIOS])
    require_zero(c, '''SELECT count(*) FROM ((SELECT candidato_id,escenario FROM gold_candidatos CROSS JOIN escenarios
        EXCEPT SELECT candidato_id,escenario FROM gold_variables_candidato) UNION ALL
        (SELECT candidato_id,escenario FROM gold_variables_candidato EXCEPT SELECT candidato_id,escenario
            FROM gold_candidatos CROSS JOIN escenarios))''', 'Cohorte de escenarios incompleta')
    c.execute('''CREATE TEMP TABLE ordenes AS SELECT dimension,escenario,entidad_id,escala,
        rank() OVER(PARTITION BY dimension,escenario,escala ORDER BY valor DESC)
        +(count(*) OVER(PARTITION BY dimension,escenario,escala,valor)-1)/2.0 rango_promedio
        FROM series CROSS JOIN LATERAL (VALUES ('original',original),('log',normalizado_log),('lineal',normalizado_lineal))
        e(escala,valor) WHERE original IS NOT NULL AND normalizado_log IS NOT NULL AND normalizado_lineal IS NOT NULL''')
    c.execute('''CREATE TEMP TABLE pares AS SELECT a.entidad_id,a.escenario escenario_base,b.escenario escenario_alternativo,
        a.original base_m,b.original alternativo_m,a.original-b.original reduccion_m,
        a.original IS NOT NULL AND b.original IS NOT NULL ambos_conocidos,
        a.normalizado_log-b.normalizado_log reduccion_log,a.normalizado_lineal-b.normalizado_lineal reduccion_lineal
        FROM series a JOIN series b USING(dimension,entidad_id) WHERE a.dimension='proximidad' AND
        ((a.escenario='principal_admitida' AND b.escenario IN ('incluye_pendientes','incluye_ausentes_historicas')) OR
            (a.escenario='incluye_pendientes' AND b.escenario='incluye_ausentes_historicas'))''')
    require_zero(c, 'SELECT count(*) FROM pares WHERE reduccion_m < -1e-8', 'La ampliación aumenta una distancia')
    c.execute('''CREATE TEMP TABLE rangos_pares AS WITH rangos AS (SELECT *,
        rank() OVER(PARTITION BY escenario_base,escenario_alternativo ORDER BY base_m DESC) rango_min_base,
        rank() OVER(PARTITION BY escenario_base,escenario_alternativo ORDER BY alternativo_m DESC) rango_min_alternativo,
        count(*) OVER(PARTITION BY escenario_base,escenario_alternativo,base_m) empates_base,
        count(*) OVER(PARTITION BY escenario_base,escenario_alternativo,alternativo_m) empates_alternativo,
        count(*) OVER(PARTITION BY escenario_base,escenario_alternativo) n FROM pares WHERE ambos_conocidos)
        SELECT escenario_base,escenario_alternativo,entidad_id,
        rango_min_base+(empates_base-1)/2.0 rango_base,
        rango_min_alternativo+(empates_alternativo-1)/2.0 rango_alternativo,
        rango_min_base<=ceil(n*0.1) top_base,rango_min_alternativo<=ceil(n*0.1) top_alternativo FROM rangos''')
    return {k:query(c,sql) for k,sql in QUERIES.items()}


def main():
    files=[]
    with duckdb.connect(config={'extension_directory':str(ROOT/'.venv/duckdb_extensions'),
            'threads':2,'memory_limit':'1GB'}) as c:
        c.execute('LOAD spatial')
        files,manifests=load_inputs(c,ROOT)
        results=prepare(c)
        references=query(c,'SELECT * EXCLUDE(version_gold) FROM gold_referencias_normalizacion ORDER BY dimension')
    code=checked(ROOT,ROOT/'src/comparar_sensibilidad_gold.py')
    unique={}
    for entry in [*files,code]:
        if entry['ruta'] in unique and any(entry[k]!=unique[entry['ruta']][k] for k in ('bytes','sha256')):
            raise ValueError('Entrada modificada durante la comparación')
        unique[entry['ruta']]=checked(ROOT,ROOT/entry['ruta'],entry)
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=ROOT/'resultados/sensibilidad_gold'/run;target.mkdir(parents=True,exist_ok=False)
    report={'ejecucion':run,'estado':'comparacion_sin_ponderar_ni_modificar_gold',
        'versiones_gold':{k:v['version_gold'] for k,v in manifests.items()},
        'periodos':manifests['variables']['periodos'],'entradas_verificadas':list(unique.values()),'codigo':code,
        'referencias':references,'consultas_sql':QUERIES,'resultados':results,
        'metodo':{'cuantiles':[0,0.25,0.5,0.75,0.9,0.95,0.99,1],
            'cambio_distancia':'Reducción mayor de 1e-8 metros; desconocidos excluidos del par, no imputados.',
            'rangos':'Descendentes, promedio en empates; correlación de Spearman sobre pares conocidos. Nula si no hay variación.',
            'grupo_superior':'10% nominal de mayor distancia, incluye todos los empates del corte; diagnóstico, no recomendación.',
            'limites':'Candidatos OSM, no sitios únicos; demanda municipal sin reparto; escenarios sin probabilidades. Sin índice combinado.'}}
    (target/'informe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('Informe:',(target/'informe.json').relative_to(ROOT).as_posix())
    print(json.dumps(results['cambios_escenario'],ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
