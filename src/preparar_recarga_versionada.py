"""Prepara la copia MITECO fechada para Gold sin sustituir las ejecuciones históricas."""

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from auditar_fuentes import ident, query
from catalogar_bronze import ROOT, fingerprint
from comparar_recarga import NEW, read_json
from georreferenciar_recarga import checked, KEYS as GEO_KEYS, validate as validate_geo
from preparar_demografia_parque import check_key
from preparar_recarga import KEYS as TABULAR_KEYS, prepare, validate as validate_tabular
from validar_silver import provider_evidence, review_charging, OUTPUT_KEYS, require_zero


KEYS = {**TABULAR_KEYS, 'incidencias': None, **GEO_KEYS, 'incidencias_espaciales': None,
        'revision_recarga': OUTPUT_KEYS['revision_recarga'],
        'recarga_municipio_validado': OUTPUT_KEYS['recarga_municipio_validado'],
        'recarga_ausentes': ['instalacion_id'],
        'recarga_ausentes_municipios_candidatos': ['instalacion_id', 'codigo_municipio']}


def load_previous(c, root, comparison):
    files = [checked(root, root / x['ruta'], x) for x in comparison['entradas_verificadas']]
    joint = next(x for x in files if x['ruta'].startswith('resultados/silver/validacion_conjunta/')
                 and x['ruta'].endswith('/informe.json'))
    joint_report = read_json(root / joint['ruta'])
    expected = {x['ruta']: x for x in joint_report['entradas_verificadas']}
    for block, tables in (
        ('base_territorial', {'municipios': 'municipios', 'recintos_municipales': 'recintos'}),
        ('recarga', {name: 'anterior_' + name for name in TABULAR_KEYS}),
        ('recarga_espacial', {'recarga_instalaciones_geo': 'geometria_anterior',
                             'recarga_municipios_candidatos': 'candidatos_anteriores'}),
        ('validacion_conjunta', {'recarga_municipio_validado': 'admisiones_anteriores'})):
        directory = root / 'resultados/silver' / block
        pointer_path = directory / 'actual.json'
        if block == 'validacion_conjunta':
            pointer_expected = next(x for x in files if x['ruta'] == pointer_path.relative_to(root).as_posix())
        else:
            pointer_expected = expected[pointer_path.relative_to(root).as_posix()]
        files.append(checked(root, pointer_path, pointer_expected))
        report_path = directory / read_json(pointer_path)['informe']
        report_expected = joint if block == 'validacion_conjunta' else expected[report_path.relative_to(root).as_posix()]
        files.append(checked(root, report_path, report_expected))
        report = read_json(report_path)
        for name, alias in tables.items():
            output = next(x for x in report['salidas'] if x['archivo'] == name + '.parquet')
            path = report_path.parent / output['archivo']
            files.append(checked(root, path, output))
            c.execute(f'CREATE TEMP TABLE {ident(alias)} AS SELECT * FROM read_parquet(?)', [str(path)])
            expected_count = output.get('filas', 542 if block == 'base_territorial' else None)
            if c.execute(f'SELECT count(*) FROM {ident(alias)}').fetchone()[0] != expected_count:
                raise ValueError(f'Recuento histórico distinto del informe: {name}')
            keys = (TABULAR_KEYS.get(name) or GEO_KEYS.get(name) or
                    OUTPUT_KEYS.get(name) or ['codigo_municipio'])
            check_key(c, alias, keys)
    for entry in files:
        if entry['ruta'] in expected:
            checked(root, root / entry['ruta'], expected[entry['ruta']])
    return files, joint_report


def inherit_geometry(c):
    fields = [row[0] for row in c.execute('DESCRIBE recarga_instalaciones').fetchall()]
    different = ' OR '.join(f'n.{ident(f)} IS DISTINCT FROM a.{ident(f)}' for f in fields)
    require_zero(c, f'''SELECT count(*) FROM recarga_instalaciones n
        LEFT JOIN geometria_anterior a USING(instalacion_id)
        WHERE a.instalacion_id IS NULL OR {different}''',
        'Identidad o coordenadas distintas: no se puede heredar geometría ni admisión')
    c.execute('''CREATE TABLE recarga_instalaciones_geo AS SELECT a.*
        FROM geometria_anterior a JOIN recarga_instalaciones n USING(instalacion_id)''')
    # Se repite la relación espacial para detectar cambios de recintos o candidatos.
    c.execute('''CREATE TABLE recarga_municipios_candidatos AS
        SELECT p.instalacion_id,r.codigo_municipio FROM recarga_instalaciones_geo p
        JOIN recintos r ON ST_Intersects(p.geometria,r.geometria)''')
    require_zero(c, '''SELECT count(*) FROM (
        (SELECT * FROM recarga_municipios_candidatos EXCEPT ALL
         SELECT a.* FROM candidatos_anteriores a JOIN recarga_instalaciones n USING(instalacion_id))
        UNION ALL
        (SELECT a.* FROM candidatos_anteriores a JOIN recarga_instalaciones n USING(instalacion_id)
         EXCEPT ALL SELECT * FROM recarga_municipios_candidatos))''',
        'Los municipios intersectados difieren del contraste histórico')
    require_zero(c, '''SELECT count(*) FROM recarga_instalaciones_geo WHERE
        estado_geometria IS DISTINCT FROM 'admitida' OR geometria IS NULL OR
        ST_IsEmpty(geometria) OR NOT ST_IsValid(geometria) OR
        NOT isfinite(ST_X(geometria)) OR NOT isfinite(ST_Y(geometria))''',
        'Geometría histórica no admitida para reutilización')
    if c.execute('SELECT DISTINCT typeof(geometria) FROM recarga_instalaciones_geo').fetchall() != [("GEOMETRY('EPSG:25830')",)]:
        raise ValueError('CRS histórico no admitido')
    c.execute('''CREATE TABLE entidad_municipio AS SELECT 'recarga_instalaciones_geo'::VARCHAR tabla_entidad,
        instalacion_id clave_entidad,codigo_municipio_espacial codigo_municipio,
        'interseccion_unica_y_nombre_oficial'::VARCHAR metodo_asignacion,
        'contrastada'::VARCHAR estado_asignacion FROM recarga_instalaciones_geo
        WHERE admitida_asignacion_municipal''')
    c.execute('''CREATE TABLE incidencias_espaciales AS SELECT instalacion_id,
        'contraste_territorial'::VARCHAR campo,estado_contraste_territorial motivo
        FROM recarga_instalaciones_geo WHERE NOT admitida_asignacion_municipal''')


def preserve_absences(c):
    c.execute('''CREATE TABLE recarga_ausentes AS SELECT g.*,
        p.puntos_registrados_historicos,c.conectores_registrados_historicos,
        a.codigo_municipio codigo_municipio_admitido_historico,a.metodo metodo_admision_historica,
        'ausente_exportacion_sin_cierre_acreditado'::VARCHAR estado_presencia
        FROM geometria_anterior g
        JOIN (SELECT instalacion_id,count(*)::BIGINT puntos_registrados_historicos
              FROM anterior_recarga_puntos GROUP BY 1) p USING(instalacion_id)
        JOIN (SELECT instalacion_id,count(*)::BIGINT conectores_registrados_historicos
              FROM anterior_recarga_conectores GROUP BY 1) c USING(instalacion_id)
        LEFT JOIN admisiones_anteriores a USING(instalacion_id)
        ANTI JOIN recarga_instalaciones n USING(instalacion_id)''')
    c.execute('''CREATE TABLE recarga_ausentes_municipios_candidatos AS SELECT a.*
        FROM candidatos_anteriores a JOIN recarga_ausentes h USING(instalacion_id)''')
    for name in ('recarga_ausentes', 'recarga_ausentes_municipios_candidatos'):
        check_key(c, name, KEYS[name])
    require_zero(c, '''SELECT count(*) FROM recarga_ausentes h
        JOIN recarga_instalaciones n USING(instalacion_id)''', 'Ausente incluido en oferta principal')
    require_zero(c, '''SELECT count(*) FROM (
        (SELECT instalacion_id FROM geometria_anterior EXCEPT
         (SELECT instalacion_id FROM recarga_instalaciones UNION ALL SELECT instalacion_id FROM recarga_ausentes))
        UNION ALL
        ((SELECT instalacion_id FROM recarga_instalaciones UNION ALL SELECT instalacion_id FROM recarga_ausentes)
         EXCEPT SELECT instalacion_id FROM geometria_anterior))''',
        'No se conserva el universo de IDs históricos')


def write_outputs(c, target, keys_by_table=KEYS):
    target.mkdir(exist_ok=False)
    outputs = []
    for name, keys in keys_by_table.items():
        if keys:
            check_key(c, name, keys)
        path = target / (name + '.parquet')
        c.execute(f'COPY {ident(name)} TO ? (FORMAT PARQUET,COMPRESSION ZSTD)', [str(path)])
        schema = [{'campo': r[0], 'tipo': r[1]} for r in c.execute('DESCRIBE ' + ident(name)).fetchall()]
        restored = [{'campo': r[0], 'tipo': r[1]} for r in c.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(path)]).fetchall()]
        fields = ','.join('ST_AsWKB(geometria) AS geometria' if r['campo'] == 'geometria'
                          else ident(r['campo']) for r in schema)
        if schema != restored or c.execute(f'''SELECT count(*) FROM (
            (SELECT {fields} FROM {ident(name)} EXCEPT ALL SELECT {fields} FROM read_parquet(?)) UNION ALL
            (SELECT {fields} FROM read_parquet(?) EXCEPT ALL SELECT {fields} FROM {ident(name)}))''',
            [str(path), str(path)]).fetchone()[0]:
            raise ValueError(f'Exportación alterada: {name}')
        if any(r['campo'] == 'geometria' for r in schema):
            meta = dict(c.execute('SELECT decode(key),decode(value) FROM parquet_kv_metadata(?)', [str(path)]).fetchall())
            if json.loads(meta['geo'])['columns']['geometria']['crs']['id'] != {'authority': 'EPSG', 'code': 25830}:
                raise ValueError('CRS GeoParquet incorrecto')
        outputs.append({'archivo': path.name, 'clave': keys, 'esquema': schema,
                        'filas': c.execute('SELECT count(*) FROM ' + ident(name)).fetchone()[0], **fingerprint(path)})
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comparacion', type=Path, required=True)
    parser.add_argument('--evidencias-recarga', type=Path, required=True)
    args = parser.parse_args()
    files = [checked(ROOT, args.comparacion.resolve())]
    comparison = read_json(args.comparacion)
    source = ROOT / NEW
    receipt_path = source.with_suffix('.csv.adquisicion.json')
    files.append(checked(ROOT, receipt_path))
    receipt = read_json(receipt_path)
    source_stamp = checked(ROOT, source, receipt)
    expected_source = next(x for x in comparison['entradas_verificadas'] if x['ruta'] == NEW)
    checked(ROOT, source, expected_source)
    if receipt['fecha_utc'] != comparison['adquisicion_nueva_utc']:
        raise ValueError('La adquisición no coincide con la comparación')
    files.append(source_stamp)
    codes = [checked(ROOT, ROOT / 'src' / name) for name in (
        'preparar_recarga_versionada.py', 'preparar_recarga.py', 'georreferenciar_recarga.py',
        'validar_silver.py', 'preparar_demografia_parque.py', 'catalogar_bronze.py',
        'auditar_fuentes.py', 'comparar_recarga.py')]
    directory = ROOT / 'resultados/silver/recarga_versionada'
    directory.mkdir(parents=True, exist_ok=True)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = directory / run
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        temporary = Path(tmp)
        with duckdb.connect(str(temporary / 'trabajo.duckdb'), config={
            'threads': 2, 'memory_limit': '1GB', 'storage_compatibility_version': 'v1.5.0',
            'temp_directory': str(temporary / 'desborde'),
            'extension_directory': str(ROOT / '.venv/duckdb_extensions')}) as c:
            c.execute('LOAD spatial')
            previous_files, joint_report = load_previous(c, ROOT, comparison)
            files.extend(previous_files)
            print('Preparando entidades y comprobando identidad de instalaciones...', flush=True)
            reading = prepare(c, source, temporary)
            tabular = validate_tabular(c)
            if tabular['incidencias']:
                raise ValueError('Incidencias tabulares: revisar antes de publicar la nueva entrada')
            for name in TABULAR_KEYS:
                check_key(c, 'anterior_' + name, TABULAR_KEYS[name])
            inherit_geometry(c)
            spatial = validate_geo(c)
            for name in TABULAR_KEYS:
                c.execute(f'CREATE TEMP VIEW {ident("recarga__" + name)} AS SELECT * FROM {ident(name)}')
            c.execute('CREATE TEMP VIEW recarga_espacial__recarga_instalaciones_geo AS SELECT * FROM recarga_instalaciones_geo')
            c.execute('CREATE TEMP VIEW base_territorial__recintos_municipales AS SELECT * FROM recintos')
            evidence_expected = next(x for x in joint_report['entradas_verificadas']
                                     if x['ruta'] == args.evidencias_recarga.resolve().relative_to(ROOT).as_posix())
            files.append(checked(ROOT, args.evidencias_recarga.resolve(), evidence_expected))
            print('Revalidando decisiones y copias documentales conservadas...', flush=True)
            decisions, evidence_files = provider_evidence(ROOT, args.evidencias_recarga.resolve(), c)
            files.extend(evidence_files)
            review = review_charging(c, decisions)
            require_zero(c, '''SELECT count(*) FROM (
                (SELECT * FROM recarga_municipio_validado EXCEPT ALL
                 SELECT a.* FROM admisiones_anteriores a JOIN recarga_instalaciones n USING(instalacion_id))
                UNION ALL
                (SELECT a.* FROM admisiones_anteriores a JOIN recarga_instalaciones n USING(instalacion_id)
                 EXCEPT ALL SELECT * FROM recarga_municipio_validado))''',
                'Las admisiones revalidadas difieren de las anteriores compatibles')
            preserve_absences(c)
            for name, summary in comparison['comparacion'].items():
                if name in ('instalaciones', 'puntos', 'conectores'):
                    if c.execute('SELECT count(*) FROM recarga_' + name).fetchone()[0] != summary['adquirida_18_10']:
                        raise ValueError(f'Entidades distintas de la comparación: {name}')
            absent_ids = [r[0] for r in c.execute('SELECT instalacion_id FROM recarga_ausentes ORDER BY 1').fetchall()]
            if len(absent_ids) != comparison['comparacion']['instalaciones']['solo_original']:
                raise ValueError('Ausencias distintas de la comparación')
            outputs = write_outputs(c, target)
            environment = {'duckdb': duckdb.__version__, 'spatial': c.execute(
                "SELECT extension_version FROM duckdb_extensions() WHERE extension_name='spatial'").fetchone()[0],
                'memoria_motor': '1GB', 'hilos': 2}
            absent_profile = query(c, '''SELECT count(*) instalaciones,
                sum(puntos_registrados_historicos) puntos,sum(conectores_registrados_historicos) conectores,
                count(codigo_municipio_admitido_historico) con_admision_historica FROM recarga_ausentes''')[0]
    unique = {}
    for entry in [*files, *codes]:
        if entry['ruta'] in unique and any(entry[k] != unique[entry['ruta']][k] for k in ('bytes', 'sha256')):
            raise ValueError('Una entrada cambió entre lecturas')
        unique[entry['ruta']] = entry
        checked(ROOT, ROOT / entry['ruta'], entry)
    report = {'version_reglas': 1, 'ejecucion': run, 'estado': 'preparada_con_limitaciones',
        'fecha_proceso_utc': datetime.now(timezone.utc).isoformat(),
        'entrada_seleccionada': source_stamp, 'fecha_adquisicion_utc': receipt['fecha_utc'],
        'solicitud': {'metodo': receipt['metodo'], 'cuerpo': receipt['cuerpo']},
        'entradas_verificadas': list({x['ruta']: x for x in files}.values()),
        'codigo': codes, 'lectura': reading, 'calidad_tabular': tabular, 'calidad_espacial': spatial,
        'revision_municipal': review, 'ausencias_historicas': absent_profile, 'ids_ausentes': absent_ids,
        'geometria': {'metodo': 'reutilizacion_por_identidad_exacta_y_recontraste_territorial',
                     'crs_salida': 'EPSG:25830', 'crs_origen_historico': 'EPSG:4258',
                     'nueva_declaracion_crs_exportador': None},
        'salidas': outputs, 'entorno': environment,
        'limitaciones': ['Adquisición no acredita operación simultánea ni fecha de instalación.',
            'Ausencias del registro no acreditan cierres; datos históricos excluidos de oferta principal.',
            'Asignación municipal documentada no certifica precisión de cada plaza o disponibilidad.',
            'Sin nueva declaración de datum: geometrías históricas reutilizadas solo con igualdad exacta.',
            'No modifica otras ejecuciones Silver ni materializa tablas Gold.']}
    (target / 'informe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    pointer = directory / 'actual.tmp'
    pointer.write_text(json.dumps({'ejecucion': run, 'informe': f'{run}/informe.json'}, indent=2) + '\n', encoding='utf-8')
    pointer.replace(directory / 'actual.json')
    print(json.dumps({'revision': review, 'ausencias': absent_profile}, ensure_ascii=False, indent=2))
    print('Informe:', (target / 'informe.json').relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
