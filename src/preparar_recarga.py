"""Fase 4 Silver: instalaciones, puntos y conectores MITECO, sin red ni geometrías supuestas."""

import argparse
import csv
import io
import json
import re
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb

from auditar_fuentes import ident, query
from catalogar_bronze import ROOT, fingerprint
from preparar_base_territorial import verify_inputs
from preparar_demografia_parque import check_key

SOURCE = 'Fuentes/instalaciones_actuales.csv'
INPUTS = {SOURCE: 'miteco_recarga'}
HEADERS = ['COMUNIDAD AUTONOMA', 'PROVINCIA', 'MUNICIPIO', 'LATITUD', 'LONGITUD',
           'NOMBRE INSTALACION', 'DIRECCIÓN', 'CODIGO POSTAL', 'LOCALIZACION',
           'TIPO HORARIO APERTURA', 'HORARIO APERTURA', 'NOMBRE OPERADOR', 'COD.OPERADOR',
           'TIPOS DE SERVICIOS', 'COD.INSTALACION', 'ID. PUNTO DE RECARGA', 'ACCESIBILIDAD',
           'METODOS DE PAGOS', 'COD. PUNTO DE RECARGA', 'ID. CONECTOR', 'TIPO CONECTOR',
           'TIPO DE CARGA', 'FORMATO', 'POTENCIA MAXIMA', 'VOLTAJE', 'INTENSIDAD',
           'FECHA DE ULTIMA MODIFICACION']
INSTALL = {'instalacion_id': 14, 'nombre_instalacion': 5, 'operador_id': 12,
           'nombre_operador': 11, 'provincia_nombre_origen': 1, 'municipio_nombre_origen': 2,
           'direccion': 6, 'codigo_postal': 7, 'latitud_origen': 3, 'longitud_origen': 4,
           'localizacion_origen': 8, 'tipo_horario_origen': 9}
POINT = {'instalacion_id': 14, 'punto_id': 15, 'codigo_punto_origen': 18, 'accesibilidad_origen': 16}
CONNECTOR = {'instalacion_id': 14, 'punto_id': 15, 'conector_id': 19, 'tipo_conector': 20,
             'tipo_carga': 21, 'formato_conector': 22, 'potencia_maxima_origen': 23,
             'fecha_ultima_modificacion_origen': 26, 'horario_apertura_origen': 10,
             'servicios_origen': 13, 'metodos_pago_origen': 17,
             'voltaje_origen': 24, 'intensidad_origen': 25}
KEYS = {'recarga_instalaciones': ['instalacion_id'],
        'recarga_puntos': ['instalacion_id', 'punto_id'],
        'recarga_conectores': ['instalacion_id', 'punto_id', 'conector_id']}
PROVINCES = {'Alicante/Alacant', 'Castellón/Castelló', 'Valencia/València'}
UNKNOWN = {'', 'DESCONOCIDO', 'NODISPONIBLE'}
FIELD = re.compile(r'(=?)"(.*?)"(?=;|\r?\n|\Z)', re.S)


def export_rows(path):
    # shortcut: dialecto de esta exportación de hasta 64 MiB; revisar si cambia el exportador.
    with path.open('rb') as stream:
        raw = stream.read(64 * 1024**2 + 1)
    if len(raw) > 64 * 1024**2:
        raise ValueError('Exportación mayor que el límite de lectura de 64 MiB')
    text = raw.decode('utf-16-le')
    header, separator, _ = text.partition('\n')
    if not separator or header.rstrip('\r').split(';') != HEADERS:
        raise ValueError('Cabecera MITECO inesperada')
    pos, ordinal = len(header) + 1, 0
    while pos < len(text):
        start, values, wrappers = pos, [], []
        for column in range(len(HEADERS)):
            match = FIELD.match(text, pos)
            if not match or (match[1] and column not in (3, 4, 7, 8)):
                raise ValueError(f'Dialecto MITECO no admitido: registro {ordinal + 1}, columna {column + 1}')
            wrappers.append(match[1])
            values.append(match[2])
            pos = match.end()
            if column < len(HEADERS) - 1:
                if text[pos:pos + 1] != ';':
                    raise ValueError(f'Fila incompleta MITECO: registro {ordinal + 1}')
                pos += 1
            elif pos != len(text):
                if text[pos:pos + 2] == '\r\n':
                    pos += 2
                elif text[pos:pos + 1] == '\n':
                    pos += 1
                else:
                    raise ValueError(f'Fila demasiado ancha MITECO: registro {ordinal + 1}')
        ordinal += 1
        # Solo se retiran envoltorios: los caracteres interiores, incluidos CR/LF, son literales.
        reconstructed = ';'.join(w + '"' + v + '"' for w, v in zip(wrappers, values))
        if reconstructed != text[start:match.end()]:
            raise ValueError(f'Lectura no reversible: registro {ordinal}')
        standard = next(csv.reader(io.StringIO(text[start:pos]), delimiter=';'))
        standard = [v[2:-1] if v.startswith('="') and v.endswith('"') else v for v in standard]
        yield ordinal, values, values != standard


def coordinate(raw, latitude):
    if raw.strip() in UNKNOWN:
        return None, 'no_informado'
    if not re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?', raw):
        return None, 'error_conversion'
    value = float(raw)
    limit = 90 if latitude else 180
    return (value, 'rango_valido_datum_pendiente') if -limit <= value <= limit else (None, 'fuera_rango')


def power(raw):
    if raw.strip() in UNKNOWN:
        return None, 'no_informado'
    if not re.fullmatch(r'[0-9]+(?:,[0-9]{1,2})? kW', raw):
        return None, 'error_conversion'
    value = Decimal(raw[:-3].replace(',', '.'))
    if value >= Decimal('10000000000000000'):
        return None, 'error_conversion'
    return value, 'informado'


def modified(raw):
    if raw.strip() in UNKNOWN:
        return None, 'no_informado'
    if not re.fullmatch(r'[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{1,2}:[0-9]{2}:[0-9]{2}', raw):
        return None, 'error_conversion'
    try:
        value = datetime.strptime(raw, '%d/%m/%Y %H:%M:%S')
    except ValueError:
        return None, 'error_conversion'
    return value, 'informado_sin_zona'


def parent(parents, key, values, entity):
    if key in parents and parents[key] != values:
        raise ValueError(f'Atributos contradictorios en {entity}: {key}')
    parents[key] = values


def prepare(connection, path, temporary):
    installs, points, national = {}, {}, defaultdict(list)
    details, incidents, counts = [], [], Counter()
    for ordinal, row, differs in export_rows(path):
        counts['filas_nacionales'] += 1
        counts['textos_preservados_frente_csv_permisivo_nacional'] += differs
        key = tuple(row[i] for i in (14, 15, 19))
        if any(not value.strip() for value in key):
            raise ValueError(f'Clave de conector incompleta: registro {ordinal}')
        national[key].append((ordinal, row))
        if (row[0] == 'Comunitat Valenciana') != (row[1] in PROVINCES):
            raise ValueError(f'Comunidad y provincia incoherentes: registro {ordinal}')
        if row[0] != 'Comunitat Valenciana':
            counts['filas_fuera_ambito'] += 1
            continue
        counts['filas_cv'] += 1
        counts['textos_preservados_frente_csv_permisivo_cv'] += differs
        parent(installs, key[0], tuple(row[i] for i in INSTALL.values()), 'instalación')
        parent(points, key[:2], tuple(row[i] for i in POINT.values()), 'punto')
        kw, kw_state = power(row[23])
        timestamp, date_state = modified(row[26])
        details.append([*(row[i] for i in CONNECTOR.values()), ordinal, kw, kw_state, timestamp, date_state])
        for field, raw, state in [('potencia_maxima_kw', row[23], kw_state),
                                  ('fecha_ultima_modificacion', row[26], date_state)]:
            if state == 'error_conversion':
                incidents.append(['recarga_conectores', ordinal, field, raw, state])
    if not details:
        raise ValueError('No hay conectores de la Comunitat Valenciana')
    for name, fields in [('recarga_instalaciones', INSTALL), ('recarga_puntos', POINT), ('recarga_conectores', CONNECTOR)]:
        columns = ','.join(ident(field) + ' VARCHAR' for field in fields)
        if name == 'recarga_instalaciones':
            columns += ',latitud DOUBLE,longitud DOUBLE,estado_coordenadas VARCHAR'
        elif name == 'recarga_conectores':
            columns += ',registro_origen BIGINT,potencia_maxima_kw DECIMAL(18,2),estado_potencia VARCHAR,fecha_ultima_modificacion TIMESTAMP,estado_fecha VARCHAR'
        connection.execute(f'CREATE TABLE {name} ({columns})')
    installation_rows = []
    for key, values in installs.items():
        lat, lat_state = coordinate(values[8], True)
        lon, lon_state = coordinate(values[9], False)
        state = 'rango_valido_datum_pendiente'
        if lat is None or lon is None:
            state = 'coordenada_no_admitida'
        elif lat == lon == 0:
            state = 'coordenadas_0_0'
        installation_rows.append([*values, lat, lon, state])
        if state != 'rango_valido_datum_pendiente':
            ordinal = next(r[-5] for r in details if r[0] == key)
            incidents.append(['recarga_instalaciones', ordinal, 'coordenadas',
                              json.dumps(values[8:10]), state + ':' + lat_state + ':' + lon_state])
    connection.execute('CREATE TABLE incidencias (tabla VARCHAR,registro_origen BIGINT,campo VARCHAR,valor_origen VARCHAR,motivo VARCHAR)')
    for table, records in [('recarga_instalaciones', installation_rows),
                           ('recarga_puntos', points.values()), ('recarga_conectores', details),
                           ('incidencias', incidents)]:
        schema = {r[0]: r[1] for r in connection.execute(f'DESCRIBE {table}').fetchall()}
        staging = temporary / f'{table}.csv'
        with staging.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(schema)
            writer.writerows(records)
        # Una carga por tabla evita miles de inserciones; restaurar los textos vacíos, no los nulos numéricos.
        columns = ','.join(f"coalesce({ident(k)},'')" if v == 'VARCHAR' else ident(k) for k, v in schema.items())
        connection.execute(f'''INSERT INTO {table} SELECT {columns} FROM read_csv(?,columns=?,
            header=true,delim=',',quote='"',escape='"',auto_detect=false,
            timestampformat='%Y-%m-%d %H:%M:%S',strict_mode=true,ignore_errors=false)''', [str(staging), schema])
    duplicates = []
    for key, rows in national.items():
        if len(rows) > 1:
            duplicates.append({'clave': list(key), 'registros_origen': [n for n, _ in rows],
                'comunidades': sorted({r[0] for _, r in rows}),
                'campos_variables': [HEADERS[i] for i in range(len(HEADERS)) if len({r[i] for _, r in rows}) > 1],
                'filas_identicas': len({tuple(r) for _, r in rows}) == 1})
    return {'recuentos': dict(counts), 'claves_repetidas_nacionales': duplicates,
            'filas_adicionales_por_clave_nacional': sum(len(d['registros_origen']) - 1 for d in duplicates),
            'filas_eliminadas_en_cv': 0, 'atributos_padre_contrastados': True,
            'dialecto': 'UTF-16LE; campos entre comillas exteriores, comillas interiores literales, envoltorios ="texto" sin evaluación; 27 campos; reconstrucción exacta de cada registro'}


def validate(connection):
    for table, keys in KEYS.items():
        check_key(connection, table, keys)
        for key in keys:
            if connection.execute(f'SELECT count(*) FROM {table} WHERE trim({ident(key)})=\'\'').fetchone()[0]:
                raise ValueError(f'Clave vacía: {table}')
    check_key(connection, 'recarga_conectores', ['registro_origen'])
    for child, target, keys in [('recarga_conectores', 'recarga_puntos', ['instalacion_id', 'punto_id']),
                                 ('recarga_puntos', 'recarga_instalaciones', ['instalacion_id'])]:
        columns = ','.join(keys)
        if connection.execute(f'SELECT count(*) FROM {child} c ANTI JOIN {target} p USING({columns})').fetchone()[0]:
            raise ValueError(f'Relación incompleta: {child}')
        if connection.execute(f'SELECT count(*) FROM {target} p ANTI JOIN {child} c USING({columns})').fetchone()[0]:
            raise ValueError(f'Entidad sin detalle: {target}')
    variation = {}
    for name, keys, field in [('horarios_por_instalacion', 'instalacion_id', 'horario_apertura_origen'),
                              ('servicios_por_instalacion', 'instalacion_id', 'servicios_origen'),
                              ('pagos_por_punto', 'instalacion_id,punto_id', 'metodos_pago_origen')]:
        variation[name] = connection.execute(f'SELECT count(*) FROM (SELECT {keys} FROM recarga_conectores GROUP BY {keys} HAVING count(DISTINCT {field})>1)').fetchone()[0]
    return {'claves_y_relaciones_validas': True, 'variantes_textuales_conservadas': variation,
        'por_provincia': query(connection, '''SELECT provincia_nombre_origen,count(DISTINCT i.instalacion_id) instalaciones,
            count(DISTINCT (p.instalacion_id,p.punto_id)) puntos,count(*) conectores
            FROM recarga_instalaciones i JOIN recarga_puntos p USING(instalacion_id)
            JOIN recarga_conectores c USING(instalacion_id,punto_id) GROUP BY 1 ORDER BY 1'''),
        'coordenadas': query(connection, 'SELECT estado_coordenadas,count(*) instalaciones FROM recarga_instalaciones GROUP BY 1'),
        'potencia': query(connection, 'SELECT estado_potencia,count(*) conectores,min(potencia_maxima_kw)::VARCHAR minimo_kw,max(potencia_maxima_kw)::VARCHAR maximo_kw FROM recarga_conectores GROUP BY 1'),
        'fechas': query(connection, 'SELECT estado_fecha,count(*) conectores,min(fecha_ultima_modificacion)::VARCHAR minima,max(fecha_ultima_modificacion)::VARCHAR maxima FROM recarga_conectores GROUP BY 1'),
        'accesibilidad': query(connection, 'SELECT accesibilidad_origen,count(*) puntos FROM recarga_puntos GROUP BY 1 ORDER BY 1'),
        'incidencias': connection.execute('SELECT count(*) FROM incidencias').fetchone()[0]}


def write_outputs(connection, target, origin):
    target.mkdir(exist_ok=False)
    outputs = []
    for table in [*KEYS, 'incidencias']:
        path = target / f'{table}.parquet'
        connection.execute(f'COPY {table} TO ? (FORMAT PARQUET,COMPRESSION ZSTD)', [str(path)])
        schema = [(r[0], r[1]) for r in connection.execute(f'DESCRIBE {table}').fetchall()]
        restored = [(r[0], r[1]) for r in connection.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(path)]).fetchall()]
        if schema != restored or connection.execute(f'''SELECT count(*) FROM (
            (SELECT * FROM {table} EXCEPT ALL SELECT * FROM read_parquet(?)) UNION ALL
            (SELECT * FROM read_parquet(?) EXCEPT ALL SELECT * FROM {table}))''', [str(path), str(path)]).fetchone()[0]:
            raise ValueError(f'Exportación alterada: {table}')
        outputs.append({'archivo': path.name, 'origen_id': origin,
                        'filas': connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0],
                        'clave': KEYS.get(table), 'esquema': [{'campo': k, 'tipo': v} for k, v in schema], **fingerprint(path)})
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifiesto-bronze', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.manifiesto_bronze.resolve()
    stamp = fingerprint(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    inputs = verify_inputs(ROOT, manifest, INPUTS)
    origin = 'miteco_recarga:' + inputs[0]['sha256']
    directory = ROOT / 'resultados/silver/recarga'
    directory.mkdir(parents=True, exist_ok=True)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = directory / run
    print('Leyendo MITECO y comprobando entidades, claves y valores...', flush=True)
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        with duckdb.connect(str(Path(temporary) / 'trabajo.duckdb'), config={'threads': 2, 'memory_limit': '1GB'}) as connection:
            connection.execute('BEGIN TRANSACTION')
            reading = prepare(connection, ROOT / SOURCE, Path(temporary))
            profile = validate(connection)
            if connection.execute('SELECT count(*) FROM recarga_conectores').fetchone()[0] != reading['recuentos']['filas_cv']:
                raise ValueError('Recuento de conectores no reconciliado con Bronze')
            connection.execute('COMMIT')
            outputs = write_outputs(connection, target, origin)
            runtime = connection.execute('SELECT version()').fetchone()[0]
    if verify_inputs(ROOT, manifest, INPUTS) != inputs or fingerprint(manifest_path) != stamp:
        raise RuntimeError('Las entradas cambiaron durante el proceso')
    report = {'version_reglas': 1, 'ejecucion': run, 'estado': 'preparada_pendiente_integracion_espacial',
              'estado_tabular': 'preparada_con_incidencias' if profile['incidencias'] else 'preparada',
              'fecha_proceso_utc': datetime.now(timezone.utc).isoformat(),
              'manifiesto_bronze': {'ruta': manifest_path.relative_to(ROOT).as_posix(), **stamp},
              'entradas_verificadas': inputs, 'lectura': reading, 'calidad': profile, 'salidas': outputs,
              'duckdb': runtime, 'crs_origen': None, 'integracion_espacial_admitida': False,
              'codigo': [{'ruta': 'src/' + name, 'sha256': fingerprint(ROOT / 'src' / name)['sha256']}
                         for name in ('preparar_recarga.py', 'preparar_demografia_parque.py', 'preparar_base_territorial.py', 'catalogar_bronze.py', 'auditar_fuentes.py')],
              'limitaciones': ['Datum no acreditado; no generar geometrías ni asignación municipal espacial.',
                              'CV se selecciona por comunidad declarada y se contrasta su provincia; no prueba posición geográfica.',
                              'Potencia nominal por conector; no sumar como capacidad simultánea de instalación.',
                              'Modificación sin zona horaria; no fecha de instalación ni fecha de exportación.',
                              'Registro público observado; no acredita exhaustividad ni disponibilidad actual.']}
    (target / 'informe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    pointer = directory / 'actual.tmp'
    pointer.write_text(json.dumps({'ejecucion': run, 'informe': f'{run}/informe.json'}, indent=2) + '\n', encoding='utf-8')
    pointer.replace(directory / 'actual.json')
    print(f'Fase 4: {report["estado"]}. Informe: {target.relative_to(ROOT).as_posix()}/informe.json')


if __name__ == '__main__':
    main()
