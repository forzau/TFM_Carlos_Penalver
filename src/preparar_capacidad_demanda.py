"""Fase 7 Silver: capacidad de demanda i-DE, sin atribuir un CRS o fecha a la copia."""

import argparse
import csv
import json
import re
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb

from auditar_fuentes import query
from catalogar_bronze import ROOT, fingerprint
from preparar_base_territorial import verify_inputs
from preparar_demografia_parque import check_key, csv_rows

SOURCE = 'Fuentes/Demanda_energetica.csv'
INPUTS = {SOURCE: 'ide_capacidad_demanda'}
PAGE = 'https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo'
PROVINCES = {'Alicante/Alacant': '03', 'Castellón/Castelló': '12', 'Valencia/València': '46'}
NULL = '\x1eNULL_SILVER\x1e'
RAW = {
    'gestor_red': 'Gestor de red', 'provincia_nombre_origen': 'Provincia',
    'municipio_nombre_origen': 'Municipio', 'x_utm_origen': 'Coordenada UTM X',
    'y_utm_origen': 'Coordenada UTM Y', 'subestacion_origen': 'Subestación',
    'nivel_tension_kv_origen': 'Nivel de Tensión (kV)',
    'capacidad_firme_disponible_mw_origen': 'Capacidad firme disponible (MW)',
    'compromiso_regulatorio_origen': 'Capacidad comprometida por cuestiones regulatorias',
    'capacidad_ocupada_mw_origen': 'Capacidad de acceso firme de demanda ocupada (MW)',
    'capacidad_admitida_no_evaluada_mw_origen': 'Capacidad de acceso firme admitida y no evaluada (MW)',
    'posiciones_ocupadas_origen': 'Posiciones ocupadas', 'posiciones_libres_origen': 'Posiciones libres',
    'nudo_0_asterisco_origen': 'Nudo 0*', 'comentarios_origen': 'Comentarios',
    'nombre_punto_conexion': 'Denominación del Punto de Conexión',
    'punto_conexion_id': 'Identificador del Punto de Conexión',
}
TYPED = {**dict.fromkeys(('nivel_tension_kv', 'capacidad_firme_disponible_mw',
    'capacidad_ocupada_mw', 'capacidad_admitida_no_evaluada_mw'), 'DECIMAL(18,2)'),
    'posiciones_ocupadas': 'BIGINT', 'posiciones_libres': 'BIGINT',
    'compromiso_regulatorio': 'BOOLEAN', 'nudo_0_asterisco': 'BOOLEAN'}
SCHEMA = {**dict.fromkeys(RAW, 'VARCHAR'), 'origen_id': 'VARCHAR', 'registro_origen': 'BIGINT',
    'codigo_provincia': 'VARCHAR', 'fecha_referencia': 'DATE', 'estado_fecha': 'VARCHAR',
    'estado_coordenadas': 'VARCHAR'}
for field, datatype in TYPED.items():
    SCHEMA.update({field: datatype, 'estado_' + field: 'VARCHAR'})
INC_SCHEMA = dict.fromkeys(('origen_id', 'punto_conexion_id', 'campo', 'valor_origen', 'motivo'), 'VARCHAR')
INC_SCHEMA['registro_origen'] = 'BIGINT'


def typed_value(raw, datatype, positive=False):
    text = raw.strip()
    if not text:
        return None, 'no_informado'
    if datatype == 'BOOLEAN':
        return (text == '1', 'informado') if text in ('0', '1') else (None, 'error_conversion')
    pattern = r'[0-9]+' if datatype == 'BIGINT' else r'[0-9]+(?:,[0-9]{1,2})?'
    if len(text) > 64 or not re.fullmatch(pattern, text):
        return None, 'error_conversion'
    value = Decimal(text.replace(',', '.'))
    limit = Decimal(2**63) if datatype == 'BIGINT' else Decimal('10000000000000000')
    if value >= limit or (positive and value <= 0):
        return None, 'error_conversion'
    return (int(value) if datatype == 'BIGINT' else value), 'informado'


def coordinate_state(x, y):
    if not x.strip() or not y.strip():
        return 'no_informadas'
    if any(len(v.strip()) > 64 or not re.fullmatch(r'[0-9]+(?:,[0-9]+)?', v.strip()) for v in (x, y)):
        return 'error_formato'
    # shortcut: no crear geometría hasta acreditar huso y datum de esta copia.
    return 'pendiente_crs'


def prepare(connection, path, temporary, origin):
    national, selected, seen = Counter(), Counter(), set()
    count = 0
    with (temporary / 'capacidad.csv').open('w', encoding='utf-8', newline='') as out, \
            (temporary / 'incidencias.csv').open('w', encoding='utf-8', newline='') as incidents:
        writer, incident_writer = csv.writer(out), csv.writer(incidents)
        writer.writerow(SCHEMA)
        incident_writer.writerow(INC_SCHEMA)
        for ordinal, row in csv_rows(path, list(RAW.values())):
            if any(NULL in v for v in row.values()):
                raise ValueError('El texto de entrada contiene el marcador reservado de NULL')
            key = row[RAW['punto_conexion_id']]
            if not key.strip() or key != key.strip() or key in seen:
                raise ValueError(f'Identificador nacional vacío, con espacios exteriores o repetido: registro {ordinal}')
            seen.add(key)
            province = row['Provincia']
            national[province] += 1
            if province not in PROVINCES:
                continue
            selected[province] += 1
            count += 1
            result = {field: row[header] for field, header in RAW.items()}
            result.update(origen_id=origin, registro_origen=ordinal, codigo_provincia=PROVINCES[province],
                fecha_referencia=None, estado_fecha='no_acreditada',
                estado_coordenadas=coordinate_state(result['x_utm_origen'], result['y_utm_origen']))

            def incidence(field, value, reason):
                entry = {'origen_id': origin, 'punto_conexion_id': key, 'campo': field,
                         'valor_origen': value, 'motivo': reason, 'registro_origen': ordinal}
                incident_writer.writerow([entry[k] for k in INC_SCHEMA])

            for field, datatype in TYPED.items():
                raw = result[field + '_origen']
                value, state = typed_value(raw, datatype, positive=(field == 'nivel_tension_kv'))
                result[field], result['estado_' + field] = value, state
                if state == 'error_conversion':
                    incidence(field, raw, state)
            if result['estado_coordenadas'] != 'pendiente_crs':
                incidence('coordenadas', json.dumps([result['x_utm_origen'], result['y_utm_origen']]), result['estado_coordenadas'])
            for field in ('gestor_red', 'municipio_nombre_origen', 'subestacion_origen', 'nombre_punto_conexion'):
                if not result[field].strip():
                    incidence(field, result[field], 'no_informado')
            if result['nudo_0_asterisco'] is True and result['capacidad_firme_disponible_mw'] not in (None, Decimal(0)):
                incidence('nudo_0_asterisco', result['nudo_0_asterisco_origen'], 'capacidad_disponible_no_cero')
            writer.writerow([NULL if result[k] is None else result[k] for k in SCHEMA])
    if not count:
        raise ValueError('No hay puntos de conexión de las tres provincias previstas')
    for table, filename, schema in [('capacidad_demanda', 'capacidad.csv', SCHEMA),
                                    ('incidencias', 'incidencias.csv', INC_SCHEMA)]:
        connection.execute(f'''CREATE TABLE {table} AS SELECT * FROM read_csv(?,columns=?,
            header=true,delim=',',quote='"',escape='"',auto_detect=false,nullstr=?,
            strict_mode=true,ignore_errors=false)''', [str(temporary / filename), schema, NULL])
    check_key(connection, 'capacidad_demanda', ['punto_conexion_id'])
    check_key(connection, 'capacidad_demanda', ['origen_id', 'registro_origen'])
    if connection.execute('SELECT count(*) FROM capacidad_demanda').fetchone()[0] != count:
        raise ValueError('Pérdida de registros CV al preparar i-DE')
    observed = dict(connection.execute('SELECT provincia_nombre_origen,count(*) FROM capacidad_demanda GROUP BY 1').fetchall())
    if observed != dict(selected):
        raise ValueError('Recuentos provinciales no reconciliados')
    if connection.execute('''SELECT count(*) FROM incidencias i ANTI JOIN capacidad_demanda c
            USING(origen_id,registro_origen,punto_conexion_id)''').fetchone()[0]:
        raise ValueError('Incidencia sin registro de origen')
    return {'filas_nacionales': sum(national.values()), 'filas_cv': count,
        'fuera_cv_en_bronze': sum(national.values()) - count, 'filas_cv_eliminadas': 0,
        'claves_nacionales_unicas': True, 'provincias_nacionales': dict(sorted(national.items()))}


def validate(connection):
    return {'por_provincia': query(connection, '''SELECT codigo_provincia,provincia_nombre_origen,
        count(*) puntos,count(DISTINCT subestacion_origen) codigos_subestacion,
        count(DISTINCT municipio_nombre_origen) etiquetas_municipales
        FROM capacidad_demanda GROUP BY 1,2 ORDER BY 1'''),
        'medidas': {field: query(connection, f'''SELECT estado_{field} estado,count(*) filas,
            min({field})::VARCHAR minimo,max({field})::VARCHAR maximo
            FROM capacidad_demanda GROUP BY 1 ORDER BY 1''') for field in TYPED},
        'banderas': query(connection, '''SELECT compromiso_regulatorio,nudo_0_asterisco,
            count(*) puntos FROM capacidad_demanda GROUP BY 1,2 ORDER BY 1,2'''),
        'capacidad_disponible': query(connection, '''SELECT CASE WHEN capacidad_firme_disponible_mw IS NULL
            THEN 'no_evaluable' WHEN capacidad_firme_disponible_mw=0 THEN 'cero' ELSE 'positiva' END estado,
            count(*) puntos FROM capacidad_demanda GROUP BY 1 ORDER BY 1'''),
        'coordenadas': query(connection, 'SELECT estado_coordenadas,count(*) puntos FROM capacidad_demanda GROUP BY 1'),
        'fechas': query(connection, 'SELECT estado_fecha,count(*) puntos FROM capacidad_demanda GROUP BY 1'),
        'incidencias': query(connection, 'SELECT campo,motivo,count(*) filas FROM incidencias GROUP BY 1,2 ORDER BY 1,2'),
        'numero_incidencias': connection.execute('SELECT count(*) FROM incidencias').fetchone()[0]}


def write_outputs(connection, target, origin):
    target.mkdir(exist_ok=False)
    outputs = []
    for table, keys in [('capacidad_demanda', ['punto_conexion_id']), ('incidencias', None)]:
        path = target / f'{table}.parquet'
        connection.execute(f'COPY {table} TO ? (FORMAT PARQUET,COMPRESSION ZSTD)', [str(path)])
        schema = [(r[0], r[1]) for r in connection.execute(f'DESCRIBE {table}').fetchall()]
        restored = [(r[0], r[1]) for r in connection.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(path)]).fetchall()]
        if schema != restored or connection.execute(f'''SELECT count(*) FROM (
            (SELECT * FROM {table} EXCEPT ALL SELECT * FROM read_parquet(?)) UNION ALL
            (SELECT * FROM read_parquet(?) EXCEPT ALL SELECT * FROM {table}))''', [str(path), str(path)]).fetchone()[0]:
            raise ValueError(f'Exportación i-DE alterada: {table}')
        outputs.append({'archivo': path.name, 'origen_id': origin, 'clave': keys,
            'filas': connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0],
            'esquema': [{'campo': k, 'tipo': v} for k, v in schema], **fingerprint(path)})
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifiesto-bronze', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.manifiesto_bronze.resolve()
    stamp = fingerprint(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    inputs = verify_inputs(ROOT, manifest, INPUTS)
    origin = 'ide_capacidad_demanda:' + inputs[0]['sha256']
    directory = ROOT / 'resultados/silver/capacidad_demanda'
    directory.mkdir(parents=True, exist_ok=True)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = directory / run
    print('Preparando i-DE: claves, unidades, estados y conservación...', flush=True)
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        temporary = Path(temporary)
        with duckdb.connect(str(temporary / 'trabajo.duckdb'), config={'threads': 2, 'memory_limit': '1GB',
                'temp_directory': str(temporary / 'desborde')}) as connection:
            reading = prepare(connection, ROOT / SOURCE, temporary, origin)
            quality = validate(connection)
            outputs = write_outputs(connection, target, origin)
            runtime = connection.execute('SELECT version()').fetchone()[0]
    if verify_inputs(ROOT, manifest, INPUTS) != inputs or fingerprint(manifest_path) != stamp:
        raise RuntimeError('Las entradas i-DE cambiaron durante el proceso')
    report = {'version_reglas': 1, 'ejecucion': run, 'estado': 'preparada_pendiente_integracion_espacial',
        'estado_tabular': 'preparada_con_incidencias' if quality['numero_incidencias'] else 'preparada',
        'fecha_proceso_utc': datetime.now(timezone.utc).isoformat(), 'fecha_referencia': None,
        'manifiesto_bronze': {'ruta': manifest_path.relative_to(ROOT).as_posix(), **stamp},
        'entradas_verificadas': inputs, 'lectura': reading, 'calidad': quality, 'salidas': outputs,
        'duckdb': runtime, 'crs_origen': None, 'integracion_espacial_admitida': False,
        'documentacion_interpretativa': {'url': PAGE, 'consulta': '2026-10-16',
            'alcance': 'Unidades y banderas; la página actual no acredita fecha ni CRS de la copia local.'},
        'codigo': [{'ruta': 'src/' + name, 'sha256': fingerprint(ROOT / 'src' / name)['sha256']} for name in
            ('preparar_capacidad_demanda.py', 'preparar_demografia_parque.py',
             'preparar_base_territorial.py', 'catalogar_bronze.py', 'auditar_fuentes.py')],
        'limitaciones': ['Huso y datum no acreditados para la copia: sin geometría ni municipio asignado.',
            'Fecha de referencia desconocida; no se hereda de la web actual o de la modificación local.',
            'Selección por provincia declarada; etiquetas de municipio no son correspondencias INE verificadas.',
            'Cobertura de i-DE, no inventario completo de red ni municipios.',
            'Capacidad informativa de demanda en MW, no energía consumida ni garantía de conexión.',
            'No sumar capacidades de puntos, tensiones o subestaciones como independientes.',
            'Nudo 0* no se convierte en capacidad positiva ni en viabilidad confirmada.',
            'Los valores por punto permanecen en resultados locales excluidos de Git.']}
    (target / 'informe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    pointer = directory / 'actual.tmp'
    pointer.write_text(json.dumps({'ejecucion': run, 'informe': f'{run}/informe.json'}, indent=2) + '\n', encoding='utf-8')
    pointer.replace(directory / 'actual.json')
    print(f'Fase 7: {report["estado"]}. Informe: {target.relative_to(ROOT).as_posix()}/informe.json')


if __name__ == '__main__':
    main()
