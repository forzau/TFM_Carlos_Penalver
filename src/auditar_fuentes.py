"""Auditoría de lectura: originales intactos, resultados agregados fuera de Git."""

import csv
import json
import sqlite3
import struct
import tempfile
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CV = ('03', '12', '46')


def ident(name):
    return '"' + name.replace('"', '""') + '"'


def sql_string(value):
    return "'" + str(value).replace("'", "''") + "'"


def query(connection, sql):
    cursor = connection.execute(sql)
    return [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]


def text_profile(connection, path, encoding, delimiter, categories, keys, csv_strict=True):
    # UTF-16LE sin BOM no es una entrada CSV nativa de DuckDB: lectura secuencial.
    if encoding == 'utf-16-le':
        with tempfile.TemporaryDirectory() as folder:
            decoded = Path(folder) / 'entrada.csv'
            with path.open(encoding=encoding, newline='') as stream, decoded.open('w', encoding='utf-8', newline='') as target:
                reader = csv.reader(stream, delimiter=delimiter, strict=csv_strict)
                columns = next(reader)
                writer = csv.writer(target, delimiter=delimiter)
                writer.writerow(columns)
                for number, row in enumerate(reader, 2):
                    if len(row) != len(columns):
                        raise ValueError(f'{path.name}: registro {number}, ancho inesperado')
                    writer.writerow(row)
            connection.execute('CREATE TEMP TABLE entrada AS SELECT * FROM read_csv(' + sql_string(decoded) + ', delim=' + sql_string(delimiter) + ', header=true, all_varchar=true, strict_mode=true, ignore_errors=false)')
    else:
        connection.execute('CREATE TEMP VIEW entrada AS SELECT * FROM read_csv(' + sql_string(path) +
                           ', delim=' + sql_string(delimiter) + ', encoding=' + sql_string(encoding) +
                           ', header=true, all_varchar=true, strict_mode=true, ignore_errors=false)')
        columns = [r[0] for r in connection.execute('DESCRIBE entrada').fetchall()]
    missing = ','.join(f"count(*) FILTER (WHERE {ident(c)} IS NULL OR trim({ident(c)}) = '')" for c in columns)
    aggregates = [f'histogram({ident(c)})' for c in categories]
    dgt = path.name == 'parque_vehiculos_202512.txt'
    if dgt:
        for province in CV:
            aggregates.extend([f"count(*) FILTER (WHERE PROVINCIA='{province}')", f"histogram(MUNICIPIO) FILTER (WHERE PROVINCIA='{province}')", f"count(*) FILTER (WHERE PROVINCIA='{province}' AND (MUNICIPIO IS NULL OR trim(MUNICIPIO)=''))"])
        aggregates.append("histogram(length(MUNICIPIO)) FILTER (WHERE PROVINCIA IN ('03','12','46'))")
    counts = connection.execute('SELECT count(*),' + missing + (',' + ','.join(aggregates) if aggregates else '') + ' FROM entrada').fetchone()
    result = {'filas': counts[0], 'columnas': columns, 'tipos_lectura': 'VARCHAR (sin convertir originales)',
              'vacios': dict(zip(columns, counts[1:1 + len(columns)])), 'codificacion_lectura': encoding, 'separador': delimiter,
              'categorias': {}, 'claves': {}, 'lector_csv_estricto': csv_strict}
    for c, histogram in zip(categories, counts[1 + len(columns):]):
        values = dict(histogram or {})
        # histogram no incluye NULL; los vacíos se informan aparte.
        result['categorias'][c] = [{'valor': value, 'filas': n} for value, n in sorted(values.items(), key=lambda pair: (-pair[1], str(pair[0])))]
    if dgt:
        extra = counts[1 + len(columns) + len(categories):]
        result['territorio_cv'] = []
        for i, province in enumerate(CV):
            total, municipalities, empty = extra[i * 3:i * 3 + 3]
            municipalities = municipalities or {}
            result['territorio_cv'].append({'PROVINCIA': province, 'filas': total, 'municipios_no_vacios': len(municipalities), 'municipio_vacio': empty, 'municipio_min': min(municipalities, default=None), 'municipio_max': max(municipalities, default=None)})
        result['anchos_municipio_cv'] = [{'ancho': width, 'filas': n} for width, n in (extra[-1] or {}).items()]
    for group in keys:
        cols = ','.join(ident(c) for c in group)
        result['claves'][' + '.join(group)] = query(connection, f'SELECT count(*) AS claves_distintas,coalesce(sum(n-1),0) AS repeticiones FROM (SELECT {cols},count(*) n FROM entrada GROUP BY {cols})')[0]
    # shortcut: duplicados exactos solo en las primeras 10000 filas; ampliar en Silver.
    result['duplicados_muestra_inicial'] = query(connection, 'SELECT count(*) AS filas, count(*) - count(DISTINCT row(' + ','.join(ident(c) for c in columns) + ')) AS duplicados FROM (SELECT * FROM entrada LIMIT 10000)')[0]
    return result


def number_checks(connection, column, european=False):
    c = ident(column)
    expression = f"replace(replace({c}, '.', ''), ',', '.')" if european else f"replace({c}, ',', '.')"
    return query(connection, f"SELECT count(*) FILTER (WHERE {c} IS NOT NULL AND trim({c})<>'' AND try_cast({expression} AS DOUBLE) IS NULL) AS no_numericos, min(try_cast({expression} AS DOUBLE)) AS minimo, max(try_cast({expression} AS DOUBLE)) AS maximo FROM entrada")[0]


def audit_text(connection, path):
    name = path.name
    configurations = {
        'Poblacion.csv': ('utf-8', ';', ['Periodo', 'Sexo'], [['Municipios', 'Sexo', 'Periodo']]),
        'Renta.csv': ('utf-8', ';', ['Periodo', 'Indicadores de renta media'], [['Municipios', 'Distritos', 'Secciones', 'Indicadores de renta media', 'Periodo']]),
        'instalaciones_actuales.csv': ('utf-16-le', ';', ['COMUNIDAD AUTONOMA', 'TIPO CONECTOR', 'TIPO DE CARGA'], [['COD.INSTALACION'], ['ID. PUNTO DE RECARGA'], ['COD.INSTALACION', 'ID. PUNTO DE RECARGA'], ['COD.INSTALACION', 'ID. PUNTO DE RECARGA', 'ID. CONECTOR']]),
        'Demanda_energetica.csv': ('utf-8', ';', ['Gestor de red', 'Provincia'], [['Identificador del Punto de Conexión']]),
        'parque_vehiculos_202512.txt': ('latin-1', '|', ['PROVINCIA', 'PROPULSION', 'CATELECT', 'TIPO_DGT'], []),
    }
    result = text_profile(connection, path, *configurations[name], csv_strict=name != 'instalaciones_actuales.csv')
    if name in ('Poblacion.csv', 'Renta.csv'):
        result['total_numerico'] = number_checks(connection, 'Total', european=True)
        result['filas_cv'] = query(connection, "SELECT count(*) filas, count(DISTINCT substr(Municipios,1,5)) municipios FROM entrada WHERE substr(Municipios,1,2) IN ('03','12','46')")[0]
        result['codigos_municipales_cv'] = [r[0] for r in connection.execute("SELECT DISTINCT substr(Municipios,1,5) FROM entrada WHERE regexp_matches(Municipios, '^[0-9]{5} ') AND substr(Municipios,1,2) IN ('03','12','46') ORDER BY 1").fetchall()]
        if name == 'Renta.csv':
            result['niveles'] = query(connection, "SELECT CASE WHEN coalesce(Secciones,'')<>'' THEN 'seccion' WHEN coalesce(Distritos,'')<>'' THEN 'distrito' ELSE 'municipio' END nivel, count(*) filas,count(*) FILTER (WHERE Total IS NULL OR Total IN ('','..','.')) sin_total FROM entrada GROUP BY 1")
            result['marcadores_total'] = query(connection, "SELECT Total valor,count(*) filas FROM entrada WHERE Total IS NULL OR try_cast(replace(replace(Total,'.',''),',','.') AS DOUBLE) IS NULL GROUP BY 1 ORDER BY 2 DESC")
            result['codigo_adicional_12066'] = query(connection, "SELECT count(*) filas,count(*) FILTER (WHERE try_cast(replace(replace(Total,'.',''),',','.') AS DOUBLE) IS NOT NULL) valores_numericos FROM entrada WHERE substr(Municipios,1,5)='12066'")[0]
    elif name == 'instalaciones_actuales.csv':
        # La exportación tiene comillas no RFC; el perfil permisivo exige 27 campos.
        # shortcut: revisar semántica de registros con comillas antes de crear Silver.
        with path.open(encoding='utf-16-le', newline='') as stream:
            reader = csv.reader(stream, delimiter=';', strict=True)
            try:
                for row in reader:
                    pass
            except csv.Error as error:
                result['primer_error_csv_estricto'] = {'linea_fisica': reader.line_num, 'error': str(error)}
        result['cv'] = query(connection, "SELECT count(*) filas,count(DISTINCT \"COD.INSTALACION\") instalaciones,count(DISTINCT \"ID. PUNTO DE RECARGA\") puntos FROM entrada WHERE \"COMUNIDAD AUTONOMA\"='Comunitat Valenciana'")[0]
        result['numericos'] = {c: number_checks(connection, c) for c in ['LATITUD', 'LONGITUD', 'POTENCIA MAXIMA']}
        # Expresiones diagnósticas: no se guardan columnas limpiadas ni registros.
        lat = 'try_cast(replace(replace(LATITUD, \'="\', \'\'), \'"\', \'\') AS DOUBLE)'
        lon = 'try_cast(replace(replace(LONGITUD, \'="\', \'\'), \'"\', \'\') AS DOUBLE)'
        power = 'try_cast(replace(replace("POTENCIA MAXIMA", \' kW\', \'\'), \',\', \'.\') AS DOUBLE)'
        result['diagnostico_formato_numerico'] = {}
        for c, expression in [('LATITUD', lat), ('LONGITUD', lon), ('POTENCIA MAXIMA', power)]:
            result['diagnostico_formato_numerico'][c] = query(connection, f'SELECT count(*) FILTER (WHERE {expression} IS NULL) no_interpretables,min({expression}) minimo,max({expression}) maximo FROM entrada')[0]
        result['coordenadas'] = query(connection, f'SELECT count(*) FILTER (WHERE {lat} IS NULL OR {lon} IS NULL) incompletas,count(*) FILTER (WHERE abs({lat})>90 OR abs({lon})>180) fuera_dominio,count(*) FILTER (WHERE {lat}=0 AND {lon}=0) cero_cero FROM entrada')[0]
        result['fechas_modificacion'] = query(connection, 'SELECT min(try_strptime("FECHA DE ULTIMA MODIFICACION", \'%d/%m/%Y %H:%M:%S\'))::VARCHAR minimo,max(try_strptime("FECHA DE ULTIMA MODIFICACION", \'%d/%m/%Y %H:%M:%S\'))::VARCHAR maximo,count(*) FILTER (WHERE try_strptime("FECHA DE ULTIMA MODIFICACION", \'%d/%m/%Y %H:%M:%S\') IS NULL) no_interpretables FROM entrada')[0]
        result['marcadores'] = {c: query(connection, f"SELECT {ident(c)} valor,count(*) filas FROM entrada WHERE upper({ident(c)}) IN ('DESCONOCIDO','NODISPONIBLE') GROUP BY 1") for c in result['columnas']}
    elif name == 'Demanda_energetica.csv':
        result['numericos'] = {c: number_checks(connection, c) for c in ['Coordenada UTM X', 'Coordenada UTM Y', 'Capacidad firme disponible (MW)']}
    connection.execute('DROP VIEW entrada' if name != 'instalaciones_actuales.csv' else 'DROP TABLE entrada')
    return result


def geometry_header(blob):
    if blob is None:
        return 'nula'
    if len(blob) < 8 or blob[:2] != b'GP':
        return 'cabecera_invalida'
    order = '<' if blob[3] & 1 else '>'
    return {'srs_id': struct.unpack(order + 'i', blob[4:8])[0], 'vacia': bool(blob[3] & 16)}


def audit_gpkg(path):
    # mode=ro impide modificar los originales incluso si una consulta fuera errónea.
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
        result = {'integridad': connection.execute('PRAGMA quick_check').fetchall(),
                  'sistemas_referencia': query(connection, 'SELECT srs_name,srs_id,organization,organization_coordsys_id,definition FROM gpkg_spatial_ref_sys'), 'capas': []}
        for metadata in query(connection, 'SELECT * FROM gpkg_contents ORDER BY table_name'):
            name = metadata['table_name']
            table = ident(name)
            columns = query(connection, f'PRAGMA table_info({table})')
            geometry = query(connection, 'SELECT * FROM gpkg_geometry_columns WHERE table_name=' + sql_string(name))
            expressions = ','.join(f'count(*) FILTER (WHERE {ident(c["name"])} IS NULL)' for c in columns)
            counts = connection.execute(f'SELECT count(*),{expressions} FROM {table}').fetchone()
            layer = {'metadatos': metadata, 'filas': counts[0], 'columnas': columns,
                     'nulos': dict(zip([c['name'] for c in columns], counts[1:])), 'geometria': geometry}
            for c in ['fclass', 'tipo_medida_trafico', 'titular', 'tipovehicd']:
                if c in layer['nulos']:
                    layer.setdefault('categorias', {})[c] = query(connection, f'SELECT {ident(c)} valor,count(*) filas FROM {table} GROUP BY 1 ORDER BY 2 DESC')
            for keys in [('osm_id',), ('id_tramo',), ('id_tramo', 'id_vial'), ('clau_tramo',)]:
                if all(c in layer['nulos'] for c in keys):
                    cols = ','.join(ident(c) for c in keys)
                    layer.setdefault('claves', {})[' + '.join(keys)] = query(connection, f'SELECT count(*) claves_distintas,coalesce(sum(n-1),0) repeticiones FROM (SELECT {cols},count(*) n FROM {table} GROUP BY {cols})')[0]
            if geometry:
                geom = ident(geometry[0]['column_name'])
                sample = [geometry_header(row[0]) for row in connection.execute(f'SELECT {geom} FROM {table} ORDER BY fid LIMIT 1000')]
                layer['cabeceras_geometria_muestra'] = {'filas': len(sample), 'estados': dict(Counter(json.dumps(x, sort_keys=True) for x in sample))}
            if 'imd' in layer['nulos']:
                imd = Counter(row[0] for row in connection.execute(f'SELECT imd FROM {table}'))
                parsed = []
                invalid = 0
                for value, n in imd.items():
                    if value is None or not str(value).strip():
                        continue
                    try:
                        parsed.append(float(str(value).replace(',', '.')))
                    except ValueError:
                        invalid += n
                layer['imd'] = {'minimo': min(parsed, default=None), 'maximo': max(parsed, default=None), 'no_numericos': invalid, 'vacios': sum(n for value,n in imd.items() if value is None or not str(value).strip())}
                layer['imd_valores'] = [{'valor': value, 'filas': n} for value, n in imd.most_common(10)]
            if 'alta_db' in layer['nulos']:
                layer['alta_db_texto'] = query(connection, f'SELECT min(alta_db) minimo,max(alta_db) maximo FROM {table}')[0]
            result['capas'].append(layer)
    return result


def main():
    required = ['Demanda_energetica.csv', 'instalaciones_actuales.csv', 'parque_vehiculos_202512.txt', 'Poblacion.csv', 'Renta.csv', 'Trafico.gpkg', 'ubicaciones_candidatasgpkg/valencia.gpkg']
    required += [f'{folder}/red_viaria.gpkg' for folder in ['RT_ALICANTE_ALACANT_gpkg', 'RT_CASTELLON_CASTELLO_gpkg', 'RT_VALENCIA_gpkg']]
    missing = [name for name in required if not (ROOT / 'Fuentes' / name).is_file()]
    if missing:
        raise FileNotFoundError('Faltan copias originales bajo Fuentes/: ' + ', '.join(missing))
    output = ROOT / 'resultados/auditoria'
    output.mkdir(parents=True, exist_ok=True)
    paths = sorted((ROOT / 'Fuentes').rglob('*'))
    before = {p.relative_to(ROOT).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns) for p in paths if p.is_file()}
    connection = duckdb.connect(config={'memory_limit': '1GB', 'threads': '2', 'temp_directory': str(output / 'temporales')})
    report = {'fecha_utc': datetime.now(timezone.utc).isoformat(), 'duckdb': duckdb.__version__,
              'alcance': 'Lectura completa de tablas; duplicados CSV y cabeceras geométricas muestreados. Sin limpieza, joins ni validación topológica.', 'archivos': []}
    errors = []
    for path in paths:
        if not path.is_file() or path.suffix not in ('.gpkg', '.csv', '.txt') or path.name in ('atributos_gpkg.csv', 'leeme_RT_Prov_gpkg.txt'):
            continue
        relative = path.relative_to(ROOT).as_posix()
        print('Auditando ' + relative, flush=True)
        entry = {'ruta': relative, 'bytes': path.stat().st_size, 'modificacion_utc': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}
        try:
            entry['perfil'] = audit_gpkg(path) if path.suffix == '.gpkg' else audit_text(connection, path)
            if path.suffix == '.gpkg' and entry['perfil']['integridad'] != [('ok',)]:
                raise ValueError('La comprobación de integridad SQLite informa errores')
        except Exception as error:
            entry['error'] = str(error).replace(str(ROOT), '.')
            errors.append(relative)
            connection.execute('DROP VIEW IF EXISTS entrada') if path.name != 'instalaciones_actuales.csv' else connection.execute('DROP TABLE IF EXISTS entrada')
        report['archivos'].append(entry)
        (output / 'perfil.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    profiles = {Path(a['ruta']).name: a['perfil'] for a in report['archivos'] if 'perfil' in a}
    if all(name in profiles for name in ('Poblacion.csv', 'Renta.csv')):
        population = set(profiles['Poblacion.csv']['codigos_municipales_cv'])
        income = set(profiles['Renta.csv']['codigos_municipales_cv'])
        report['comparacion_codigos_cv'] = {'solo_renta': sorted(income-population), 'solo_poblacion': sorted(population-income)}
    connection.close()
    after = {p.relative_to(ROOT).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns) for p in paths if p.is_file()}
    report['originales_tamano_fecha_sin_cambios'] = before == after
    if before != after:
        errors.append('Cambios en tamaño o fecha de los originales durante la ejecución')
    (output / 'perfil.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Finalizado. Errores: ' + str(len(errors)), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
