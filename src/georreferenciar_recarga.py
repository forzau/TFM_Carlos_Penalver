"""Fase 8 parcial: capa MITECO y contraste municipal, sin corregir posiciones o nombres."""

import argparse
import csv
import json
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from auditar_fuentes import ident, query
from catalogar_bronze import ROOT, fingerprint
from preparar_base_territorial import verify_inputs
from preparar_demografia_parque import check_key
from preparar_poi_osm import territory
from preparar_recarga import INPUTS, KEYS as SOURCE_KEYS, validate as validate_recarga

RESOURCE = '047c1f64-7552-44da-a639-2291292e650d'
ENDPOINT = 'https://energia.serviciosmin.gob.es/Ripree/ExportarInstalaciones/Export'
KEYS = {'recarga_instalaciones_geo': ['instalacion_id'],
        'recarga_municipios_candidatos': ['instalacion_id', 'codigo_municipio'],
        'entidad_municipio': ['tabla_entidad', 'clave_entidad', 'codigo_municipio']}


def checked(root, path, expected=None):
    path = path.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Entrada fuera del proyecto')
    stamp = fingerprint(path)
    if expected and any(stamp[k] != expected[k] for k in ('bytes', 'sha256')):
        raise ValueError(f'Entrada distinta de su informe o recibo: {path.name}')
    return {'ruta': path.relative_to(root.resolve()).as_posix(), **stamp}


def evidence(root, path):
    stamp = checked(root, path)
    receipt_path = path.with_suffix(path.suffix + '.adquisicion.json')
    receipt_stamp = checked(root, receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if any(stamp[k] != receipt[k] for k in ('bytes', 'sha256')):
        raise ValueError('El catálogo MITECO difiere del recibo conservado')
    catalog = json.loads(path.read_text(encoding='utf-8'))
    resources = [r for r in catalog['result']['resources'] if r['id'] == RESOURCE]
    if not catalog.get('success') or len(resources) != 1:
        raise ValueError('Recurso CSV MITECO no identificado de forma única')
    resource = resources[0]
    if (resource['format'] != 'CSV' or resource['url'] != ENDPOINT or
            resource['reference_system'] != 'http://www.opengis.net/def/crs/EPSG/0/4258'):
        raise ValueError('Declaración espacial o endpoint MITECO distintos de los investigados')
    return {'catalogo': stamp, 'recibo': receipt_stamp, 'recurso': RESOURCE,
            'url': receipt['url_solicitada'], 'crs_declarado': 'EPSG:4258'}


def load_recarga(connection, root):
    directory = root / 'resultados/silver/recarga'
    pointer_path = directory / 'actual.json'
    pointer = json.loads(pointer_path.read_text(encoding='utf-8'))
    report_path = (directory / pointer['informe']).resolve()
    if not report_path.is_relative_to(directory.resolve()):
        raise ValueError('Informe de recarga fuera de su carpeta')
    files = [checked(root, pointer_path), checked(root, report_path)]
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if report['estado_tabular'] != 'preparada':
        raise ValueError('Revisar incidencias tabulares antes de preparar la capa')
    for table in [*SOURCE_KEYS, 'incidencias']:
        entries = [r for r in report['salidas'] if r['archivo'] == table + '.parquet']
        if len(entries) != 1:
            raise ValueError(f'Salida tabular no identificada: {table}')
        path = report_path.parent / entries[0]['archivo']
        files.append(checked(root, path, entries[0]))
        connection.execute(f'CREATE TEMP TABLE {table} AS SELECT * FROM read_parquet(?)', [str(path)])
        if connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0] != entries[0]['filas']:
            raise ValueError('Recuento tabular distinto del informe')
    validate_recarga(connection)
    manifest_path = root / report['manifiesto_bronze']['ruta']
    files.append(checked(root, manifest_path, report['manifiesto_bronze']))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    bronze = verify_inputs(root, manifest, INPUTS)
    fields = ('ruta', 'recurso_id', 'bytes', 'sha256')
    if ([{k: r[k] for k in fields} for r in bronze] !=
            [{k: r[k] for k in fields} for r in report['entradas_verificadas']]):
        raise ValueError('La copia Bronze no coincide con la utilizada en fase 4')
    files.extend(bronze)
    return files


def name_key(value):
    # Solo variantes de escritura; nunca buscar el municipio más parecido.
    return '/'.join(sorted(''.join(c for c in unicodedata.normalize('NFKD', part.casefold())
                                  if c.isalnum()) for part in value.split('/')))


def prepare(connection, temporary):
    names = connection.execute('''SELECT nombre_municipio FROM municipios UNION SELECT nombre_municipio_ign
        FROM recintos UNION SELECT municipio_nombre_origen FROM recarga_instalaciones ORDER BY 1''').fetchall()
    path = temporary / 'nombres.csv'
    marker = '\x1eNULL_SILVER\x1e'
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['texto_origen', 'clave'])
        for (text,) in names:
            if text is not None:
                if marker in text:
                    raise ValueError('Nombre contiene marcador reservado de NULL')
                writer.writerow([text, name_key(text)])
    connection.execute('''CREATE TEMP TABLE nombres_normalizados AS SELECT * FROM read_csv(?,
        columns={'texto_origen':'VARCHAR','clave':'VARCHAR'},header=true,delim=',',
        auto_detect=false,nullstr=?,strict_mode=true,ignore_errors=false)''', [str(path), marker])
    connection.execute('''CREATE TEMP TABLE etiquetas AS
        SELECT codigo_municipio,left(codigo_municipio,2) codigo_provincia,n.clave nombre
        FROM municipios m JOIN nombres_normalizados n ON m.nombre_municipio=n.texto_origen
        UNION SELECT codigo_municipio,left(codigo_municipio,2),n.clave FROM recintos r
            JOIN nombres_normalizados n ON r.nombre_municipio_ign=n.texto_origen''')
    connection.execute('''CREATE TEMP TABLE etiquetas_unicas AS SELECT codigo_provincia,nombre,
        min(codigo_municipio) codigo_municipio FROM etiquetas WHERE nombre<>''
        GROUP BY 1,2 HAVING count(DISTINCT codigo_municipio)=1''')
    connection.execute('''CREATE TABLE recarga_instalaciones_geo AS SELECT *,
        CASE provincia_nombre_origen WHEN 'Alicante/Alacant' THEN '03'
            WHEN 'Castellón/Castelló' THEN '12' WHEN 'Valencia/València' THEN '46' END codigo_provincia_declarada,
        CASE WHEN latitud IS NULL OR longitud IS NULL OR NOT isfinite(latitud) OR NOT isfinite(longitud)
            OR abs(latitud)>90 OR abs(longitud)>180 OR (latitud=0 AND longitud=0) THEN NULL
        ELSE TRY(ST_Transform(ST_Point(longitud,latitud),'EPSG:4258','EPSG:25830',always_xy:=true)) END
            ::GEOMETRY('EPSG:25830') geometria
        FROM recarga_instalaciones''')
    connection.execute('''ALTER TABLE recarga_instalaciones_geo ADD COLUMN estado_geometria VARCHAR''')
    connection.execute('''UPDATE recarga_instalaciones_geo SET estado_geometria=CASE
        WHEN geometria IS NULL THEN 'coordenadas_o_proyeccion_no_admitidas'
        WHEN ST_IsEmpty(geometria) OR NOT ST_IsValid(geometria) OR
            NOT isfinite(ST_X(geometria)) OR NOT isfinite(ST_Y(geometria)) THEN 'proyeccion_no_admitida'
        ELSE 'admitida' END''')
    # shortcut: materializar el cruce antes de filtros de atributos por fallo spatial 1.5.0; revisar al actualizar.
    connection.execute('''CREATE TABLE recarga_municipios_candidatos AS
        SELECT p.instalacion_id,r.codigo_municipio FROM recarga_instalaciones_geo p JOIN recintos r
        ON ST_Intersects(p.geometria,r.geometria)''')
    connection.execute('''DELETE FROM recarga_municipios_candidatos WHERE instalacion_id IN
        (SELECT instalacion_id FROM recarga_instalaciones_geo WHERE estado_geometria<>'admitida')''')
    connection.execute('''CREATE TEMP TABLE contraste AS SELECT p.instalacion_id,
        coalesce(c.n,0)::BIGINT numero_municipios_intersectados,
        CASE WHEN c.n=1 THEN c.codigo END codigo_municipio_espacial,
        e.codigo_municipio codigo_municipio_declarado
        FROM recarga_instalaciones_geo p
        LEFT JOIN (SELECT instalacion_id,count(*) n,min(codigo_municipio) codigo
            FROM recarga_municipios_candidatos GROUP BY 1) c USING(instalacion_id)
        LEFT JOIN nombres_normalizados n ON p.municipio_nombre_origen=n.texto_origen
        LEFT JOIN etiquetas_unicas e ON p.codigo_provincia_declarada=e.codigo_provincia AND n.clave=e.nombre''')
    connection.execute('''CREATE TEMP TABLE enriquecida AS SELECT p.*,c.* EXCLUDE(instalacion_id),
        m.nombre_municipio nombre_municipio_espacial,
        CASE WHEN p.estado_geometria<>'admitida' THEN 'geometria_no_admitida'
            WHEN c.numero_municipios_intersectados=0 THEN 'fuera_ambito'
            WHEN c.numero_municipios_intersectados>1 THEN 'limite_ambiguo'
            WHEN p.codigo_provincia_declarada IS NULL THEN 'provincia_no_reconocida'
            WHEN left(c.codigo_municipio_espacial,2)<>p.codigo_provincia_declarada THEN 'provincia_discrepante'
            WHEN c.codigo_municipio_declarado IS NULL THEN 'nombre_no_resuelto'
            WHEN c.codigo_municipio_declarado<>c.codigo_municipio_espacial THEN 'municipio_discrepante'
            ELSE 'concordante' END estado_contraste_territorial,
        CASE WHEN p.estado_geometria='admitida' AND rd.codigo_municipio IS NOT NULL
            THEN ST_Distance(p.geometria,rd.geometria) ELSE NULL END distancia_municipio_declarado_m
        FROM recarga_instalaciones_geo p JOIN contraste c USING(instalacion_id)
        LEFT JOIN municipios m ON c.codigo_municipio_espacial=m.codigo_municipio
        LEFT JOIN recintos rd ON c.codigo_municipio_declarado=rd.codigo_municipio''')
    connection.execute('''CREATE OR REPLACE TABLE recarga_instalaciones_geo AS SELECT *,
        (estado_contraste_territorial='concordante') admitida_asignacion_municipal FROM enriquecida''')
    connection.execute('''CREATE TABLE entidad_municipio AS SELECT 'recarga_instalaciones_geo'::VARCHAR tabla_entidad,
        instalacion_id clave_entidad,codigo_municipio_espacial codigo_municipio,
        'interseccion_unica_y_nombre_oficial'::VARCHAR metodo_asignacion,'contrastada'::VARCHAR estado_asignacion
        FROM recarga_instalaciones_geo WHERE admitida_asignacion_municipal''')
    connection.execute('''CREATE TABLE incidencias_espaciales AS SELECT instalacion_id,
        'contraste_territorial'::VARCHAR campo,estado_contraste_territorial motivo
        FROM recarga_instalaciones_geo WHERE NOT admitida_asignacion_municipal''')


def validate(connection):
    for table, keys in KEYS.items():
        check_key(connection, table, keys)
    fields = ','.join(ident(r[0]) for r in connection.execute('DESCRIBE recarga_instalaciones').fetchall())
    if connection.execute(f'''SELECT count(*) FROM (
        (SELECT {fields} FROM recarga_instalaciones EXCEPT ALL SELECT {fields} FROM recarga_instalaciones_geo)
        UNION ALL (SELECT {fields} FROM recarga_instalaciones_geo EXCEPT ALL SELECT {fields} FROM recarga_instalaciones))''').fetchone()[0]:
        raise ValueError('Los atributos originales de instalaciones han cambiado')
    for table, field in [('recarga_municipios_candidatos', 'instalacion_id'), ('entidad_municipio', 'clave_entidad'),
                         ('incidencias_espaciales', 'instalacion_id')]:
        if connection.execute(f'''SELECT count(*) FROM {table} x ANTI JOIN recarga_instalaciones_geo p
            ON x.{field}=p.instalacion_id''').fetchone()[0]:
            raise ValueError(f'Referencia huérfana en {table}')
    if connection.execute('''SELECT count(*) FROM entidad_municipio x ANTI JOIN recintos r USING(codigo_municipio)''').fetchone()[0]:
        raise ValueError('Relación con municipio inexistente')
    error = connection.execute('''SELECT max(greatest(abs(ST_X(v)-longitud),abs(ST_Y(v)-latitud))) FROM
        (SELECT *,ST_Transform(geometria,'EPSG:25830','EPSG:4258',always_xy:=true) v
        FROM recarga_instalaciones_geo WHERE estado_geometria='admitida')''').fetchone()[0]
    if error is not None and error > 1e-8:
        raise ValueError('La vuelta de proyección altera las coordenadas')
    controls = {}
    for table in SOURCE_KEYS:
        original = connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
        joined, admitted = connection.execute(f'''SELECT count(*),count(*) FILTER(WHERE g.admitida_asignacion_municipal)
            FROM {table} p JOIN recarga_instalaciones_geo g USING(instalacion_id)''').fetchone()
        if original != joined:
            raise ValueError('Se pierden o multiplican entidades al cruzar instalaciones')
        controls[table] = {'originales': original, 'tras_relacion': joined, 'con_asignacion_admitida': admitted}
    return {'entidades': controls, 'error_vuelta_grados_max': error,
        'por_estado': query(connection, 'SELECT estado_geometria,estado_contraste_territorial,count(*) instalaciones FROM recarga_instalaciones_geo GROUP BY 1,2 ORDER BY 1,2'),
        'municipios_con_instalaciones_admitidas': connection.execute('SELECT count(DISTINCT codigo_municipio) FROM entidad_municipio').fetchone()[0],
        'discrepancias_por_etiqueta': query(connection, '''SELECT provincia_nombre_origen,municipio_nombre_origen,
            codigo_municipio_declarado,codigo_municipio_espacial,nombre_municipio_espacial,count(*) instalaciones,
            max(distancia_municipio_declarado_m) distancia_maxima_m FROM recarga_instalaciones_geo
            WHERE NOT admitida_asignacion_municipal GROUP BY 1,2,3,4,5 ORDER BY instalaciones DESC,1,2,4'''),
        'incidencias': connection.execute('SELECT count(*) FROM incidencias_espaciales').fetchone()[0]}


def write_outputs(connection, target):
    target.mkdir(exist_ok=False)
    outputs = []
    for table in [*KEYS, 'incidencias_espaciales']:
        path = target / (table + '.parquet')
        connection.execute(f'COPY {table} TO ? (FORMAT PARQUET,COMPRESSION ZSTD)', [str(path)])
        schema = [(r[0], r[1]) for r in connection.execute(f'DESCRIBE {table}').fetchall()]
        restored = [(r[0], r[1]) for r in connection.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(path)]).fetchall()]
        fields = ','.join('ST_AsWKB(geometria) geometria' if k == 'geometria' else ident(k) for k, _ in schema)
        if schema != restored or connection.execute(f'''SELECT count(*) FROM (
            (SELECT {fields} FROM {table} EXCEPT ALL SELECT {fields} FROM read_parquet(?)) UNION ALL
            (SELECT {fields} FROM read_parquet(?) EXCEPT ALL SELECT {fields} FROM {table}))''', [str(path), str(path)]).fetchone()[0]:
            raise ValueError(f'Exportación espacial alterada: {table}')
        geo = None
        if 'geometria' in dict(schema):
            metadata = dict(connection.execute('SELECT decode(key),decode(value) FROM parquet_kv_metadata(?)', [str(path)]).fetchall())
            geo = json.loads(metadata['geo'])
            if geo['columns']['geometria']['crs']['id'] != {'authority': 'EPSG', 'code': 25830}:
                raise ValueError('CRS de salida de recarga incorrecto')
        outputs.append({'archivo': path.name, 'clave': KEYS.get(table), 'geo': geo,
            'filas': connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0],
            'esquema': [{'campo': k, 'tipo': v} for k, v in schema], **fingerprint(path)})
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadatos-miteco', type=Path, required=True)
    args = parser.parse_args()
    metadata = evidence(ROOT, args.metadatos_miteco.resolve())
    directory = ROOT / 'resultados/silver/recarga_espacial'
    directory.mkdir(parents=True, exist_ok=True)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = directory / run
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        temporary = Path(tmp)
        with duckdb.connect(str(temporary / 'trabajo.duckdb'), config={'threads': 2, 'memory_limit': '1GB',
                'storage_compatibility_version': 'v1.5.0', 'temp_directory': str(temporary / 'desborde'),
                'extension_directory': str(ROOT / '.venv/duckdb_extensions')}) as connection:
            connection.execute('LOAD spatial')
            files = load_recarga(connection, ROOT)
            base = territory(connection, ROOT)
            files.extend([base['municipios'], base['recintos']])
            files.append(checked(ROOT, ROOT / base['municipios']['informe']))
            files.extend([metadata['catalogo'], metadata['recibo']])
            print('Proyectando instalaciones y contrastando municipios declarados y espaciales...', flush=True)
            prepare(connection, temporary)
            quality = validate(connection)
            outputs = write_outputs(connection, target)
            runtime = {'duckdb': connection.execute('SELECT version()').fetchone()[0],
                'spatial': connection.execute("SELECT extension_version FROM duckdb_extensions() WHERE extension_name='spatial'").fetchone()[0]}
    for entry in files:
        checked(ROOT, ROOT / entry.get('ruta', entry.get('tabla')), entry)
    report = {'version_reglas': 1, 'ejecucion': run, 'estado': 'preparada_con_incidencias' if quality['incidencias'] else 'preparada',
        'fecha_proceso_utc': datetime.now(timezone.utc).isoformat(), 'entradas_verificadas': files,
        'evidencia_crs': metadata, 'crs_origen_declarado': 'EPSG:4258', 'crs_salida': 'EPSG:25830', 'always_xy': True,
        'calidad': quality, 'salidas': outputs, 'entorno': runtime,
        'codigo': [{'ruta': 'src/' + n, 'sha256': fingerprint(ROOT / 'src' / n)['sha256']} for n in
            ('georreferenciar_recarga.py', 'preparar_recarga.py', 'preparar_poi_osm.py', 'preparar_demografia_parque.py',
             'preparar_base_territorial.py', 'catalogar_bronze.py', 'auditar_fuentes.py', 'comprobar_entorno_silver.py')],
        'limitaciones': ['El CRS es declaración del catálogo, con salvedad OCPI/WGS84; no prueba geodésica por registro.',
            'Asignación admitida exige intersección única, provincia y nombre oficial concordantes.',
            'Normalización solo elimina diacríticos/puntuación/espacios y orden de variantes separadas por barra; sin fuzzy.',
            'Un conflicto no determina si falla la coordenada, el municipio declarado o el recinto.',
            'No se desplazan puntos, sustituyen etiquetas ni asignan municipios por cercanía.',
            'Distancia al recinto declarado solo diagnóstica; no umbral de admisión o error posicional medido.',
            'No se certifica exhaustividad, operatividad o precisión individual; no suma de potencias.',
            'Solo bloque espacial MITECO de fase8: no validación conjunta completa ni Gold.']}
    (target / 'informe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    pointer = directory / 'actual.tmp'
    pointer.write_text(json.dumps({'ejecucion': run, 'informe': f'{run}/informe.json'}, indent=2) + '\n', encoding='utf-8')
    pointer.replace(directory / 'actual.json')
    print(f'Recarga espacial: {report["estado"]}. Informe: {target.relative_to(ROOT).as_posix()}/informe.json')


if __name__ == '__main__':
    main()
