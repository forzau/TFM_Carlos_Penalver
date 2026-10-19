"""Aplica metadatos acreditados a i-DE y contrasta municipios sin mover puntos."""

import argparse
import csv
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from auditar_fuentes import ident, sql_string, query
from catalogar_bronze import ROOT, fingerprint
from georreferenciar_recarga import checked, name_key
from preparar_base_territorial import verify_inputs
from preparar_capacidad_demanda import INPUTS, RAW, PROVINCES
from preparar_demografia_parque import check_key
from preparar_poi_osm import territory
from verificar_metadatos_ide import verify

KEYS = {'capacidad_demanda_geo': ['punto_conexion_id'],
        'capacidad_municipios_candidatos': ['punto_conexion_id', 'codigo_municipio'],
        'entidad_municipio': ['punto_conexion_id'],
        'incidencias_espaciales': ['punto_conexion_id']}
HISTORICAL = {'estado_fecha': 'estado_fecha_preparacion',
              'estado_coordenadas': 'estado_coordenadas_preparacion'}


def load_inputs(c, root, metadata_path):
    files = [checked(root, metadata_path)]
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    accreditation = verify(root, metadata)
    files.extend(checked(root, root / entry['ruta'], entry) for entry in metadata['archivos'].values())
    directory = root / 'resultados/silver/capacidad_demanda'
    pointer_path = directory / 'actual.json'
    files.append(checked(root, pointer_path))
    pointer = json.loads(pointer_path.read_text(encoding='utf-8'))
    report_path = (directory / pointer['informe']).resolve()
    run_path = (directory / pointer['ejecucion']).resolve()
    if not run_path.is_relative_to(directory.resolve()) or report_path != run_path / 'informe.json':
        raise ValueError('Informe i-DE fuera de su ejecución')
    files.append(checked(root, report_path))
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if report['ejecucion'] != pointer['ejecucion'] or report['estado_tabular'] != 'preparada':
        raise ValueError('La tabla i-DE no está preparada sin incidencias')
    entry = next(r for r in report['salidas'] if r['archivo'] == 'capacidad_demanda.parquet')
    path = run_path / entry['archivo']
    files.append(checked(root, path, entry))
    c.execute('CREATE TEMP TABLE capacidad_demanda AS SELECT * FROM read_parquet(?)', [str(path)])
    schema = [{'campo': r[0], 'tipo': r[1]} for r in c.execute('DESCRIBE capacidad_demanda').fetchall()]
    if schema != entry['esquema'] or c.execute('SELECT count(*) FROM capacidad_demanda').fetchone()[0] != entry['filas']:
        raise ValueError('Tabla i-DE distinta de su informe')
    check_key(c, 'capacidad_demanda', ['punto_conexion_id'])
    manifest_path = root / report['manifiesto_bronze']['ruta']
    files.append(checked(root, manifest_path, report['manifiesto_bronze']))
    bronze = verify_inputs(root, json.loads(manifest_path.read_text(encoding='utf-8')), INPUTS)
    files.extend(bronze)
    if bronze[0]['sha256'] != accreditation['sha256_original']:
        raise ValueError('La evidencia acredita otra copia Bronze')
    expected = []
    with (root / metadata['archivos']['original']['ruta']).open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream, delimiter=';'):
            if row['Provincia'] in PROVINCES:
                expected.append(tuple(row[header] for header in RAW.values()))
    actual = c.execute('SELECT ' + ','.join(ident(k) for k in RAW) + ' FROM capacidad_demanda').fetchall()
    if sorted(expected) != sorted(actual):
        raise ValueError('Los campos de Silver no coinciden con el CSV acreditado')
    return files, accreditation


def prepare(c, metadata):
    check_key(c, 'capacidad_demanda', ['punto_conexion_id'])
    # Variantes oficiales INE/IGN dentro de la provincia. Sin similitud aproximada.
    labels = c.execute('''SELECT codigo_municipio,nombre_municipio FROM municipios
        UNION SELECT codigo_municipio,nombre_municipio_ign FROM recintos''').fetchall()
    aliases = sorted({(code[:2], name_key(variant), code) for code, label in labels
                      for variant in [label, *label.split('/')] if variant.strip()})
    c.execute('CREATE TEMP TABLE etiquetas(provincia VARCHAR,nombre VARCHAR,codigo_municipio VARCHAR)')
    c.executemany('INSERT INTO etiquetas VALUES (?,?,?)', aliases)
    names = c.execute('SELECT DISTINCT municipio_nombre_origen FROM capacidad_demanda').fetchall()
    c.execute('CREATE TEMP TABLE nombres(texto VARCHAR,clave VARCHAR)')
    c.executemany('INSERT INTO nombres VALUES (?,?)', [(t, name_key(t or '')) for (t,) in names])
    c.execute('''CREATE TEMP TABLE etiquetas_unicas AS SELECT provincia,nombre,min(codigo_municipio) codigo
        FROM etiquetas WHERE nombre<>'' GROUP BY 1,2 HAVING count(DISTINCT codigo_municipio)=1''')
    c.execute(f'''CREATE TABLE capacidad_demanda_geo AS SELECT * RENAME(
        estado_fecha AS estado_fecha_preparacion,estado_coordenadas AS estado_coordenadas_preparacion),
        {sql_string(metadata['fecha_publicacion'])}::DATE fecha_publicacion,
        {sql_string(metadata['periodo_referencia'])}::VARCHAR periodo_referencia,
        'periodo_mensual_acreditado'::VARCHAR estado_fecha,
        'crs_acreditado'::VARCHAR estado_coordenadas,'EPSG:25830'::VARCHAR crs_origen,
        CASE WHEN regexp_full_match(trim(x_utm_origen),'[0-9]+(,[0-9]+)?') AND length(trim(x_utm_origen))<=64
            THEN try_cast(replace(trim(x_utm_origen),',','.') AS DOUBLE) END x_utm,
        CASE WHEN regexp_full_match(trim(y_utm_origen),'[0-9]+(,[0-9]+)?') AND length(trim(y_utm_origen))<=64
            THEN try_cast(replace(trim(y_utm_origen),',','.') AS DOUBLE) END y_utm
        FROM capacidad_demanda''')
    c.execute('''ALTER TABLE capacidad_demanda_geo ADD COLUMN geometria GEOMETRY('EPSG:25830')''')
    c.execute('''UPDATE capacidad_demanda_geo SET geometria=ST_Point(x_utm,y_utm)::GEOMETRY('EPSG:25830')
        WHERE x_utm IS NOT NULL AND y_utm IS NOT NULL AND isfinite(x_utm) AND isfinite(y_utm)
            AND NOT (x_utm=0 AND y_utm=0)''')
    c.execute('ALTER TABLE capacidad_demanda_geo ADD COLUMN estado_geometria VARCHAR')
    c.execute('''UPDATE capacidad_demanda_geo SET estado_geometria=CASE
        WHEN geometria IS NULL THEN 'coordenadas_no_admitidas'
        WHEN ST_IsEmpty(geometria) OR NOT ST_IsValid(geometria) THEN 'geometria_no_admitida'
        ELSE 'admitida' END''')
    # Materializar antes de filtrar atributos: requisito observado con spatial 1.5.0.
    c.execute('''CREATE TABLE capacidad_municipios_candidatos AS SELECT p.punto_conexion_id,r.codigo_municipio
        FROM capacidad_demanda_geo p JOIN recintos r ON ST_Intersects(p.geometria,r.geometria)''')
    c.execute('''DELETE FROM capacidad_municipios_candidatos WHERE punto_conexion_id IN
        (SELECT punto_conexion_id FROM capacidad_demanda_geo WHERE estado_geometria<>'admitida')''')
    c.execute('''CREATE TEMP TABLE contraste AS SELECT p.punto_conexion_id,
        coalesce(x.n,0)::BIGINT numero_municipios_intersectados,
        CASE WHEN x.n=1 THEN x.codigo END codigo_municipio_espacial,e.codigo codigo_municipio_declarado
        FROM capacidad_demanda_geo p LEFT JOIN
        (SELECT punto_conexion_id,count(*) n,min(codigo_municipio) codigo
         FROM capacidad_municipios_candidatos GROUP BY 1) x USING(punto_conexion_id)
        LEFT JOIN nombres n ON p.municipio_nombre_origen=n.texto
        LEFT JOIN etiquetas_unicas e ON p.codigo_provincia=e.provincia AND n.clave=e.nombre''')
    c.execute('''CREATE TEMP TABLE enriquecida AS SELECT p.*,x.* EXCLUDE(punto_conexion_id),
        m.nombre_municipio nombre_municipio_espacial,
        CASE WHEN p.estado_geometria<>'admitida' THEN 'geometria_no_admitida'
        WHEN x.numero_municipios_intersectados=0 THEN 'fuera_ambito'
        WHEN x.numero_municipios_intersectados>1 THEN 'limite_ambiguo'
        WHEN left(x.codigo_municipio_espacial,2)<>p.codigo_provincia THEN 'provincia_discrepante'
        WHEN x.codigo_municipio_declarado IS NULL THEN 'nombre_no_resuelto'
        WHEN x.codigo_municipio_declarado<>x.codigo_municipio_espacial THEN 'municipio_discrepante'
        ELSE 'concordante' END estado_contraste_territorial,
        CASE WHEN p.estado_geometria='admitida' AND rd.codigo_municipio IS NOT NULL
        THEN ST_Distance(p.geometria,rd.geometria) END distancia_municipio_declarado_m
        FROM capacidad_demanda_geo p JOIN contraste x USING(punto_conexion_id)
        LEFT JOIN municipios m ON x.codigo_municipio_espacial=m.codigo_municipio
        LEFT JOIN recintos rd ON x.codigo_municipio_declarado=rd.codigo_municipio''')
    c.execute('''CREATE OR REPLACE TABLE capacidad_demanda_geo AS SELECT *,
        (estado_contraste_territorial='concordante') admitida_asignacion_municipal FROM enriquecida''')
    c.execute('''CREATE TABLE entidad_municipio AS SELECT punto_conexion_id,codigo_municipio_espacial codigo_municipio,
        'interseccion_unica_y_nombre_oficial'::VARCHAR metodo_asignacion FROM capacidad_demanda_geo
        WHERE admitida_asignacion_municipal''')
    c.execute('''CREATE TABLE incidencias_espaciales AS SELECT punto_conexion_id,
        estado_contraste_territorial motivo FROM capacidad_demanda_geo WHERE NOT admitida_asignacion_municipal''')


def validate(c):
    for name, keys in KEYS.items():
        check_key(c, name, keys)
    original = [r[0] for r in c.execute('DESCRIBE capacidad_demanda').fetchall()]
    fields = ','.join(ident(k) for k in original)
    restored = ','.join(ident(HISTORICAL.get(k, k)) + ' AS ' + ident(k) for k in original)
    if c.execute(f'''SELECT count(*) FROM (
        (SELECT {fields} FROM capacidad_demanda EXCEPT ALL SELECT {restored} FROM capacidad_demanda_geo)
        UNION ALL (SELECT {restored} FROM capacidad_demanda_geo EXCEPT ALL SELECT {fields} FROM capacidad_demanda))''').fetchone()[0]:
        raise ValueError('Se han modificado o perdido atributos de la tabla original')
    if c.execute('''SELECT count(*) FROM capacidad_demanda_geo WHERE estado_geometria='admitida'
        AND (NOT ST_IsValid(geometria) OR ST_IsEmpty(geometria) OR ST_X(geometria)<>x_utm OR ST_Y(geometria)<>y_utm)''').fetchone()[0]:
        raise ValueError('Geometría distinta de las coordenadas publicadas')
    if c.execute('SELECT count(*) FROM entidad_municipio ANTI JOIN municipios USING(codigo_municipio)').fetchone()[0]:
        raise ValueError('Relación municipal sin referencia')
    total, admitted = c.execute('SELECT count(*),count(*) FILTER(WHERE admitida_asignacion_municipal) FROM capacidad_demanda_geo').fetchone()
    if total != c.execute('SELECT count(*) FROM capacidad_demanda').fetchone()[0]:
        raise ValueError('Se pierden puntos al generar la capa')
    for table in ('entidad_municipio', 'incidencias_espaciales', 'capacidad_municipios_candidatos'):
        if c.execute(f'SELECT count(*) FROM {table} ANTI JOIN capacidad_demanda_geo USING(punto_conexion_id)').fetchone()[0]:
            raise ValueError('Referencia espacial i-DE huérfana')
    if admitted != c.execute('SELECT count(*) FROM entidad_municipio').fetchone()[0] or total-admitted != c.execute('SELECT count(*) FROM incidencias_espaciales').fetchone()[0]:
        raise ValueError('Admisiones e incidencias no reconciliadas')
    return {'puntos_conservados': total, 'asignaciones_admitidas': admitted, 'pendientes': total-admitted,
        'municipios_admitidos': c.execute('SELECT count(DISTINCT codigo_municipio) FROM entidad_municipio').fetchone()[0],
        'por_estado': query(c, '''SELECT estado_geometria,estado_contraste_territorial,count(*) puntos
            FROM capacidad_demanda_geo GROUP BY 1,2 ORDER BY 1,2'''),
        'por_provincia': query(c, '''SELECT codigo_provincia,count(*) puntos,
            count(*) FILTER(WHERE admitida_asignacion_municipal) admitidos FROM capacidad_demanda_geo GROUP BY 1 ORDER BY 1'''),
        'atributos_originales': 'conservados_integramente', 'coordenadas': 'sin_desplazamiento_ni_reproyeccion'}


def write_outputs(c, target):
    target.mkdir(exist_ok=False)
    outputs = []
    for name, keys in KEYS.items():
        path = target / (name + '.parquet')
        c.execute(f'COPY (SELECT * FROM {name} ORDER BY {",".join(keys)}) TO ? (FORMAT PARQUET,COMPRESSION ZSTD)', [str(path)])
        schema = [{'campo': r[0], 'tipo': r[1]} for r in c.execute('DESCRIBE ' + name).fetchall()]
        restored = [{'campo': r[0], 'tipo': r[1]} for r in c.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(path)]).fetchall()]
        fields = ','.join('ST_AsWKB(geometria) AS geometria' if r['campo']=='geometria' else ident(r['campo']) for r in schema)
        if schema != restored or c.execute(f'''SELECT count(*) FROM (
            (SELECT {fields} FROM {name} EXCEPT ALL SELECT {fields} FROM read_parquet(?)) UNION ALL
            (SELECT {fields} FROM read_parquet(?) EXCEPT ALL SELECT {fields} FROM {name}))''', [str(path), str(path)]).fetchone()[0]:
            raise ValueError('Exportación i-DE espacial alterada')
        if any(r['campo']=='geometria' for r in schema):
            meta = dict(c.execute('SELECT decode(key),decode(value) FROM parquet_kv_metadata(?)', [str(path)]).fetchall())
            if json.loads(meta['geo'])['columns']['geometria']['crs']['id'] != {'authority':'EPSG','code':25830}:
                raise ValueError('CRS GeoParquet i-DE incorrecto')
        outputs.append({'archivo': path.name, 'clave': keys, 'esquema': schema,
                        'filas': c.execute('SELECT count(*) FROM ' + name).fetchone()[0], **fingerprint(path)})
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadatos-ide', type=Path, required=True)
    args = parser.parse_args()
    directory = ROOT / 'resultados/silver/capacidad_demanda_espacial'
    directory.mkdir(parents=True, exist_ok=True)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = directory / run
    codes = [checked(ROOT, ROOT/'src'/name) for name in ('georreferenciar_capacidad_demanda.py',
        'verificar_metadatos_ide.py', 'georreferenciar_recarga.py', 'preparar_capacidad_demanda.py',
        'preparar_poi_osm.py', 'preparar_demografia_parque.py', 'preparar_base_territorial.py',
        'catalogar_bronze.py', 'auditar_fuentes.py')]
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        temp = Path(tmp)
        with duckdb.connect(str(temp/'trabajo.duckdb'), config={'threads':2, 'memory_limit':'1GB',
            'storage_compatibility_version':'v1.5.0', 'temp_directory':str(temp/'desborde'),
            'extension_directory':str(ROOT/'.venv/duckdb_extensions')}) as c:
            c.execute('LOAD spatial')
            files, metadata = load_inputs(c, ROOT, args.metadatos_ide.resolve())
            base = territory(c, ROOT)
            files.extend([base['municipios'], base['recintos'],
                          checked(ROOT, ROOT/base['municipios']['informe']),
                          checked(ROOT, ROOT/'resultados/silver/base_territorial/actual.json')])
            print('Aplicando metadatos y contrastando puntos i-DE con recintos municipales...', flush=True)
            prepare(c, metadata)
            quality = validate(c)
            outputs = write_outputs(c, target)
            environment = {'duckdb':duckdb.__version__, 'spatial':c.execute("SELECT extension_version FROM duckdb_extensions() WHERE extension_name='spatial'").fetchone()[0],
                           'memoria_motor':'1GB', 'hilos':2}
    for entry in [*files, *codes]:
        checked(ROOT, ROOT/entry.get('ruta', entry.get('tabla')), entry)
    report = {'version_reglas':1, 'ejecucion':run,
        'estado':'preparada_con_incidencias' if quality['pendientes'] else 'preparada',
        'fecha_proceso_utc':datetime.now(timezone.utc).isoformat(), 'entradas_verificadas':files,
        'metadatos_evidencias':files[0],
        'metadatos_acreditados':metadata, 'crs_origen':'EPSG:25830', 'crs_salida':'EPSG:25830',
        'integracion_espacial_admitida':True, 'calidad':quality, 'salidas':outputs, 'entorno':environment, 'codigo':codes,
        'limitaciones':['Periodo mensual derivado del formato CNMC; día/hora exactos de corte desconocidos.',
            'CRS declarado: no acredita precisión posicional de cada subestación.',
            'Admisión municipal exige intersección única, provincia y nombre oficial concordantes; candidatos aparte.',
            'No mover puntos, resolver por cercanía ni fusionar puntos coincidentes de una subestación.',
            'Capacidad informativa, no aditiva ni garantía de conexión; cobertura solo de la red publicada por i-DE.',
            'Preparación tabular histórica y originales conservados; datos por punto fuera de Git.']}
    (target/'informe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')
    pointer = directory/'actual.tmp'
    pointer.write_text(json.dumps({'ejecucion':run, 'informe':f'{run}/informe.json'}, indent=2)+'\n', encoding='utf-8')
    pointer.replace(directory/'actual.json')
    print(json.dumps(quality, ensure_ascii=False, indent=2))
    print(f'Informe: {target.relative_to(ROOT).as_posix()}/informe.json')


if __name__ == '__main__':
    main()
