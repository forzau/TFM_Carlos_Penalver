"""Revisión reproducible de contrastes Gold; no modifica datos ni prioriza zonas."""

import json
import math
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from auditar_fuentes import query
from catalogar_bronze import ROOT
from georreferenciar_recarga import checked


CASES = ('46250','03014','03065','12040','46223','46103','12087','12141','12004','46111','46022','46201')
QUERIES = {
    'resumen': '''SELECT count(*) municipios,
        count(*) FILTER(WHERE puntos_con_municipio_admitido=0) sin_puntos_admitidos,
        count(*) FILTER(WHERE renta_neta_media_persona_eur IS NULL) renta_no_informada
        FROM gold_municipios''',
    'municipios': '''WITH proximidad AS (SELECT c.codigo_municipio_contexto codigo_municipio,
        count(*) elementos_contexto_exclusivo,min(p.distancia_plana_m) minima_m,
        median(p.distancia_plana_m) mediana_m,max(p.distancia_plana_m) maxima_m
        FROM gold_candidatos c JOIN gold_proximidad_candidato_recarga p USING(candidato_id)
        WHERE p.escenario='principal_admitida' AND c.codigo_municipio_contexto IS NOT NULL GROUP BY 1)
        SELECT m.codigo_municipio,m.nombre_municipio,m.poblacion_total,m.parque_total,m.vehiculos_distintivo_0,
        m.puntos_con_municipio_admitido,m.distintivo_0_por_punto_admitido,m.estado_presion_descriptiva,
        m.renta_neta_media_persona_eur,m.instalaciones_pendientes_relacionadas,m.instalaciones_ausentes_relacionadas,
        coalesce(p.elementos_contexto_exclusivo,0) elementos_contexto_exclusivo,p.minima_m,p.mediana_m,p.maxima_m
        FROM gold_municipios m LEFT JOIN proximidad p USING(codigo_municipio)
        WHERE m.codigo_municipio IN (SELECT codigo FROM casos) ORDER BY m.codigo_municipio''',
    'sin_poi': '''SELECT m.codigo_municipio,m.nombre_municipio,m.poblacion_total,m.vehiculos_distintivo_0,
        m.puntos_con_municipio_admitido FROM gold_municipios m ANTI JOIN gold_candidato_municipio USING(codigo_municipio)
        ORDER BY m.vehiculos_distintivo_0 DESC,m.codigo_municipio''',
    'sensibilidad': '''SELECT c.candidato_id,c.nombre_origen,c.categoria_origen,c.codigo_municipio_contexto,
        a.distancia_plana_m principal_m,p.distancia_plana_m pendientes_m,h.distancia_plana_m historicas_m,
        a.instalacion_id_mas_cercana id_principal,p.instalacion_id_mas_cercana id_pendiente,h.instalacion_id_mas_cercana id_historico
        FROM gold_candidatos c JOIN gold_proximidad_candidato_recarga a USING(candidato_id)
        JOIN gold_proximidad_candidato_recarga p USING(candidato_id) JOIN gold_proximidad_candidato_recarga h USING(candidato_id)
        WHERE a.escenario='principal_admitida' AND p.escenario='incluye_pendientes' AND h.escenario='incluye_ausentes_historicas'
        ORDER BY a.distancia_plana_m-h.distancia_plana_m DESC,c.candidato_id LIMIT 5''',
    'ausentes': '''SELECT c.candidato_id,c.nombre_origen,c.codigo_municipio_contexto,p.distancia_plana_m presentes_m,
        h.distancia_plana_m historicas_m,h.instalacion_id_mas_cercana id_historico FROM gold_candidatos c
        JOIN gold_proximidad_candidato_recarga p USING(candidato_id) JOIN gold_proximidad_candidato_recarga h USING(candidato_id)
        WHERE p.escenario='incluye_pendientes' AND h.escenario='incluye_ausentes_historicas'
        ORDER BY p.distancia_plana_m-h.distancia_plana_m DESC,c.candidato_id LIMIT 4''',
    'correspondencias': '''SELECT p.candidato_id punto_id,a.candidato_id area_id,p.nombre_origen,p.categoria_origen,
        p.codigo_municipio_contexto,ST_Area(a.geometria) area_m2,
        ST_Distance(p.punto_representativo,a.punto_representativo) distancia_representantes_m,
        dp.distancia_plana_m distancia_punto_recarga_m,da.distancia_plana_m distancia_area_representante_recarga_m
        FROM gold_correspondencias_candidatos r JOIN gold_candidatos p ON p.candidato_id=r.candidato_punto_id
        JOIN gold_candidatos a ON a.candidato_id=r.candidato_area_id
        JOIN gold_proximidad_candidato_recarga dp ON dp.candidato_id=p.candidato_id AND dp.escenario='principal_admitida'
        JOIN gold_proximidad_candidato_recarga da ON da.candidato_id=a.candidato_id AND da.escenario='principal_admitida'
        WHERE r.coincide_nombre_normalizado ORDER BY distancia_representantes_m DESC,p.candidato_id LIMIT 4''',
    'areas_con_recarga': '''SELECT count(*) areas_con_coincidencia,
        min(p.distancia_plana_m) minima_representante_m,max(p.distancia_plana_m) maxima_representante_m
        FROM (SELECT DISTINCT candidato_id FROM coincidencias_area_recarga) x
        JOIN gold_proximidad_candidato_recarga p USING(candidato_id) WHERE p.escenario='principal_admitida' ''',
    'ejemplos_area': '''SELECT c.candidato_id,c.nombre_origen,c.categoria_origen,ST_Area(c.geometria) area_m2,
        c.numero_municipios_relacionados,p.distancia_plana_m representante_m,
        count(*) instalaciones_coincidentes FROM coincidencias_area_recarga x JOIN gold_candidatos c USING(candidato_id)
        JOIN gold_proximidad_candidato_recarga p USING(candidato_id) WHERE p.escenario='principal_admitida'
        GROUP BY ALL ORDER BY p.distancia_plana_m DESC,c.candidato_id LIMIT 5''',
    'bonaire': '''SELECT c.candidato_id,c.nombre_origen,c.categoria_origen,c.numero_municipios_relacionados,
        m.nombre_municipio,r.dimension_interseccion,r.superficie_interseccion_m2,p.distancia_plana_m
        FROM gold_candidatos c JOIN gold_candidato_municipio r USING(candidato_id)
        JOIN gold_municipios m USING(codigo_municipio) JOIN gold_proximidad_candidato_recarga p USING(candidato_id)
        WHERE lower(c.nombre_origen) LIKE '%bonaire%' AND c.categoria_origen='mall' AND p.escenario='principal_admitida'
        ORDER BY c.candidato_id,m.codigo_municipio''',
    'solapamientos_categorias': '''SELECT count(*) pares,
        count(DISTINCT parking_id) aparcamientos,count(DISTINCT destino_id) destinos FROM solapamientos''',
    'borde_casos': '''SELECT c.candidato_id,c.codigo_municipio_contexto,
        ST_Distance(c.punto_representativo,b.geometria) distancia_borde_cv_m,p.distancia_plana_m recarga_inventario_m
        FROM gold_candidatos c CROSS JOIN borde_cv b JOIN gold_proximidad_candidato_recarga p USING(candidato_id)
        WHERE c.codigo_municipio_contexto IN ('12141','12087') AND p.escenario='principal_admitida'
        ORDER BY c.codigo_municipio_contexto,c.candidato_id''',
    'bonaire_areas': '''SELECT a.candidato_id area_menor,b.candidato_id area_mayor,
        ST_Area(ST_Intersection(a.geometria,b.geometria)) interseccion_m2,
        ST_Covers(b.geometria,a.geometria) mayor_cubre_menor FROM gold_candidatos a JOIN gold_candidatos b
        ON ST_Intersects(a.geometria,b.geometria) WHERE a.categoria_origen='mall' AND b.categoria_origen='mall'
        AND a.nombre_origen='Bonaire' AND b.nombre_origen='Centro Comercial Bonaire' ''',
    'ejemplos_solapamientos': '''SELECT p.candidato_id parking_id,d.candidato_id destino_id,d.nombre_origen,d.categoria_origen,
        p.representacion representacion_aparcamiento,d.codigo_municipio_contexto
        FROM solapamientos s JOIN gold_candidatos p ON p.candidato_id=s.parking_id
        JOIN gold_candidatos d ON d.candidato_id=s.destino_id ORDER BY d.nombre_origen,d.candidato_id,p.candidato_id LIMIT 5''',
    'multiples': '''SELECT c.candidato_id,c.nombre_origen,c.numero_municipios_relacionados,
        string_agg(m.nombre_municipio,' / ' ORDER BY m.codigo_municipio) municipios
        FROM gold_candidatos c JOIN gold_candidato_municipio r USING(candidato_id) JOIN gold_municipios m USING(codigo_municipio)
        WHERE c.numero_municipios_relacionados>1 GROUP BY ALL ORDER BY c.numero_municipios_relacionados DESC,c.candidato_id LIMIT 3''',
}


def main():
    files, versions = [], {}
    with tempfile.TemporaryDirectory(dir=ROOT/'resultados') as tmp:
        with duckdb.connect(str(Path(tmp)/'revision.duckdb'),config={'extension_directory':str(ROOT/'.venv/duckdb_extensions'),
            'threads':2,'memory_limit':'1GB','temp_directory':str(Path(tmp)/'desborde')}) as c:
            c.execute('LOAD spatial')
            for block in ('contexto_municipal','candidatos'):
                directory=ROOT/'resultados/gold'/block
                pointer=directory/'actual.json';files.append(checked(ROOT,pointer))
                selection=json.loads(pointer.read_text(encoding='utf-8'))
                path=(directory/selection['manifiesto']).resolve()
                if not path.is_relative_to(directory.resolve()) or path.parent.name!=selection['ejecucion'] or path.name!='manifiesto.json':
                    raise ValueError('Referencia Gold fuera de su ejecución')
                files.append(checked(ROOT,path));manifest=json.loads(path.read_text(encoding='utf-8'))
                if manifest['version_gold']!=selection['ejecucion']:raise ValueError('Versión Gold incoherente')
                versions[block]=manifest['version_gold']
                files.extend(manifest['entradas_verificadas'])
                for entry in manifest['salidas']:
                    source=path.parent/entry['archivo'];files.append(checked(ROOT,source,entry))
                    name=source.stem
                    c.execute(f'CREATE TEMP TABLE {name} AS SELECT * FROM read_parquet(?)',[str(source)])
            if manifest['ejecuciones']['gold/contexto_municipal']!=versions['contexto_municipal']:
                raise ValueError('Candidatos de otra Gold municipal')
            files=list({e['ruta']:e for e in files}.values())
            for e in files:checked(ROOT,ROOT/e['ruta'],e)
            c.execute('CREATE TEMP TABLE casos(codigo VARCHAR)')
            c.executemany('INSERT INTO casos VALUES (?)',[(x,) for x in CASES])
            assert c.execute('SELECT count(*) FROM casos JOIN gold_municipios ON codigo=codigo_municipio').fetchone()[0]==len(CASES)
            c.execute('''CREATE TEMP TABLE oferta AS SELECT * FROM gold_recarga_instalaciones
                WHERE presente_copia_principal AND estado_admision='admitida_version_principal' AND estado_geometria='admitida' ''')
            c.execute("CREATE TEMP TABLE areas AS SELECT * FROM gold_candidatos WHERE representacion='area'")
            c.execute('''CREATE TEMP TABLE coincidencias_area_recarga AS SELECT a.candidato_id,r.instalacion_id
                FROM areas a JOIN oferta r ON ST_Intersects(a.geometria,r.geometria)''')
            c.execute("CREATE TEMP TABLE aparcamientos AS SELECT * FROM gold_candidatos WHERE grupo_uso='aparcamiento'")
            c.execute("CREATE TEMP TABLE destinos AS SELECT * FROM gold_candidatos WHERE grupo_uso IN ('comercio','alojamiento')")
            c.execute('''CREATE TEMP TABLE solapamientos AS SELECT p.candidato_id parking_id,d.candidato_id destino_id
                FROM aparcamientos p JOIN destinos d ON ST_Intersects(p.geometria,d.geometria)''')
            c.execute('CREATE TEMP TABLE borde_cv AS SELECT ST_Boundary(ST_Union_Agg(geometria)) geometria FROM gold_municipios')
            results={k:query(c,sql) for k,sql in QUERIES.items()}
            for name,block in (('parque_municipal','demografia_parque'),('poblacion_municipal','demografia_parque'),
                               ('recarga_puntos','recarga_versionada'),('recarga_municipio_validado','recarga_versionada')):
                entry=next(e for e in files if e['ruta'].startswith('resultados/silver/'+block+'/') and e['ruta'].endswith('/'+name+'.parquet'))
                c.execute(f'CREATE TEMP TABLE {name} AS SELECT * FROM read_parquet(?)',[str(ROOT/entry['ruta'])])
            silver=query(c,'''SELECT v.codigo_municipio,v.parque_total,v.vehiculos_distintivo_0,p.poblacion,
                coalesce(o.puntos,0) puntos FROM parque_municipal v
                JOIN poblacion_municipal p USING(codigo_municipio) JOIN casos ON codigo=v.codigo_municipio
                LEFT JOIN (SELECT a.codigo_municipio,count(*) puntos FROM recarga_municipio_validado a
                    JOIN recarga_puntos r USING(instalacion_id) GROUP BY 1) o USING(codigo_municipio)
                WHERE v.fecha_referencia=DATE '2025-12-31' AND p.sexo='Total' AND p.anio=2025''')
            assert len(silver)==len(CASES)
            for source in silver:
                gold=next(x for x in results['municipios'] if x['codigo_municipio']==source['codigo_municipio'])
                assert (source['parque_total'],source['vehiculos_distintivo_0'],source['poblacion'],source['puntos'])==(
                    gold['parque_total'],gold['vehiculos_distintivo_0'],gold['poblacion_total'],gold['puntos_con_municipio_admitido'])
            # Muestra contrastiva: mínimos, medianas y máximos por municipio, más excepciones revisadas.
            sample_sql='''WITH orden AS (SELECT g.candidato_id,g.codigo_municipio_contexto,
                row_number() OVER(PARTITION BY g.codigo_municipio_contexto ORDER BY p.distancia_plana_m,g.candidato_id) n,
                count(*) OVER(PARTITION BY g.codigo_municipio_contexto) total
                FROM gold_candidatos g JOIN gold_proximidad_candidato_recarga p USING(candidato_id)
                JOIN casos ON codigo=g.codigo_municipio_contexto WHERE p.escenario='principal_admitida')
                SELECT candidato_id FROM orden WHERE n IN (1,total,cast(ceil(total/2.0) AS BIGINT))'''
            sample={x['candidato_id'] for x in query(c,sample_sql)}
            for key in ('sensibilidad','ausentes','ejemplos_area','bonaire','multiples'):
                sample.update(x['candidato_id'] for x in results[key])
            for row in results['correspondencias']:sample.update((row['punto_id'],row['area_id']))
            chargers=query(c,'''SELECT instalacion_id,presente_copia_principal,estado_admision,
                ST_X(geometria) x,ST_Y(geometria) y FROM gold_recarga_instalaciones
                WHERE estado_geometria='admitida' AND geometria IS NOT NULL''')
            checks=[]
            for candidate in sorted(sample):
                point=c.execute('SELECT ST_X(punto_representativo),ST_Y(punto_representativo) FROM gold_candidatos WHERE candidato_id=?',[candidate]).fetchone()
                for scenario,distance,neighbor,ties in c.execute('''SELECT escenario,distancia_plana_m,
                    instalacion_id_mas_cercana,numero_instalaciones_a_distancia_minima
                    FROM gold_proximidad_candidato_recarga WHERE candidato_id=?''',[candidate]).fetchall():
                    eligible=[x for x in chargers if scenario=='incluye_ausentes_historicas' or
                        (x['presente_copia_principal'] and (scenario=='incluye_pendientes' or x['estado_admision']=='admitida_version_principal'))]
                    distances=[(math.hypot(point[0]-x['x'],point[1]-x['y']),x['instalacion_id']) for x in eligible]
                    minimum=min(x[0] for x in distances)
                    ids=sorted(x[1] for x in distances if x[0]==minimum)
                    assert math.isclose(distance,minimum,rel_tol=1e-12,abs_tol=1e-8),(candidate,scenario)
                    assert neighbor==ids[0] and ties==len(ids),(candidate,scenario,'vecino/empates')
                    checks.append({'candidato_id':candidate,'escenario':scenario,'distancia_m':distance,'distancia_python_m':minimum,'vecino':neighbor})
            # Recalcular la presión municipal desde los operandos, conservando denominadores cero.
            for row in results['municipios']:
                expected=row['vehiculos_distintivo_0']/row['puntos_con_municipio_admitido'] if row['puntos_con_municipio_admitido'] else None
                observed=row['distintivo_0_por_punto_admitido']
                assert (expected is None and observed is None) or math.isclose(expected,observed,rel_tol=1e-12)
    for e in files:checked(ROOT,ROOT/e['ruta'],e)
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=ROOT/'resultados/revision_gold'/run;target.mkdir(parents=True,exist_ok=False)
    report={'ejecucion':run,'versiones_gold':versions,'estado':'revision_contrastiva_sin_modificar_gold',
        'seleccion':'Doce municipios por contrastes demográficos, ausencia de oferta, borde e incertidumbre; no muestra aleatoria.',
        'casos':list(CASES),'consultas_sql':QUERIES,'muestreo_distancias_sql':sample_sql,
        'resultados':results,'contraste_municipal_silver':silver,
        'comprobaciones_distancias':checks,'candidatos_comprobados':len(sample),
        'entradas_verificadas':files,'codigo':checked(ROOT,Path(__file__))}
    (target/'informe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({'ejecucion':run,'candidatos_comprobados':len(sample),'distancias_comprobadas':len(checks),'resultados':results},ensure_ascii=False,indent=2,default=str))


if __name__=='__main__':
    main()
