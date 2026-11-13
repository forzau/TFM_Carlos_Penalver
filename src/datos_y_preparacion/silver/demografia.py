"""Silver: población, renta y parque de vehículos; DGT se lee en disco."""

from collections import Counter
from datetime import date
from decimal import Decimal
from openpyxl import load_workbook
import csv
import math
import re

from src.datos_y_preparacion.comunes import comprobar_clave, consultar, identificador_sql


DEMOGRAFIA_TXT = 'Fuentes/parque_vehiculos_202512.txt'


DEMOGRAFIA_XLSX = 'datos/bronze/dgt_municipal/2025/DatosMunicipalesGeneral_2025.xlsx'


DEMOGRAFIA_POP = 'Fuentes/Poblacion.csv'


DEMOGRAFIA_INCOME = 'Fuentes/Renta.csv'


DEMOGRAFIA_PROVINCES = ('03', '12', '46')


DEMOGRAFIA_SCHEMAS = {
    'poblacion_municipal': {'codigo_municipio': 'VARCHAR', 'sexo': 'VARCHAR', 'anio': 'SMALLINT',
        'poblacion': 'BIGINT', 'estado_valor': 'VARCHAR', 'valor_origen': 'VARCHAR', 'registro_origen': 'BIGINT'},
    'renta_territorial': {'nivel_territorial': 'VARCHAR', 'codigo_territorio': 'VARCHAR',
        'codigo_municipio': 'VARCHAR', 'codigo_distrito': 'VARCHAR', 'codigo_seccion': 'VARCHAR',
        'indicador': 'VARCHAR', 'anio': 'SMALLINT', 'valor_eur': 'DECIMAL(18,2)',
        'estado_valor': 'VARCHAR', 'valor_origen': 'VARCHAR', 'registro_origen': 'BIGINT'},
    'incidencias': {'tabla': 'VARCHAR', 'origen_id': 'VARCHAR', 'registro_origen': 'BIGINT',
        'codigo_municipio': 'VARCHAR', 'campo': 'VARCHAR', 'valor_origen': 'VARCHAR', 'motivo': 'VARCHAR'},
}


DEMOGRAFIA_SCHEMAS['renta_codigos_historicos'] = {**DEMOGRAFIA_SCHEMAS['renta_territorial'], 'motivo_separacion': 'VARCHAR'}


DEMOGRAFIA_KEYS = {'parque_municipal': ['codigo_municipio', 'fecha_referencia'],
        'parque_sin_municipio': ['codigo_agrupacion_origen', 'fecha_referencia'],
        'parque_detalle_observado': ['origen_id', 'registro_origen'],
        'poblacion_municipal': ['codigo_municipio', 'sexo', 'anio'],
        'renta_territorial': ['nivel_territorial', 'codigo_territorio', 'indicador', 'anio'],
        'renta_codigos_historicos': ['nivel_territorial', 'codigo_territorio', 'indicador', 'anio']}


def demografia_ine_number(raw, integer=False):
    text = raw.strip()
    if text in ('', '.', '..', '...'):
        return None, 'no_informado'
    if not re.fullmatch(r'-?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)(?:,[0-9]+)?', text):
        return None, 'error_conversion'
    value = Decimal(text.replace('.', '').replace(',', '.'))
    if integer:
        if value != value.to_integral_value() or not 0 <= value <= 2**63 - 1:
            return None, 'error_conversion'
        return int(value), 'informado'
    if (',' in text and len(text.split(',')[1]) > 2) or abs(value) >= Decimal('10000000000000000'):
        return None, 'error_conversion'
    return value, 'informado'


def demografia_territory_code(raw, width):
    match = re.match(r'^([0-9]{' + str(width) + r'})(?:\s|$)', raw)
    if not match:
        raise ValueError(f'Código territorial de longitud {width} no válido: {raw!r}')
    return match[1]


def demografia_csv_rows(path, headers):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, delimiter=';', strict=True)
        if next(reader) != headers:
            raise ValueError(f'Cabecera inesperada: {path.name}')
        for ordinal, values in enumerate(reader, 1):
            if len(values) != len(headers):
                raise ValueError(f'{path.name}: ancho inesperado en registro {ordinal}')
            yield ordinal, dict(zip(headers, values))


def demografia_prepare_ine(connection, population, income, codes, temporary, origins):
    counts = Counter()
    with (temporary / 'incidencias.csv').open('w', encoding='utf-8', newline='') as inc_stream:
        incidents = csv.writer(inc_stream)
        incidents.writerow(DEMOGRAFIA_SCHEMAS['incidencias'])
        with (temporary / 'poblacion_municipal.csv').open('w', encoding='utf-8', newline='') as target:
            writer = csv.writer(target)
            writer.writerow(DEMOGRAFIA_SCHEMAS['poblacion_municipal'])
            for ordinal, row in demografia_csv_rows(population, ['Total Nacional', 'Municipios', 'Sexo', 'Periodo', 'Total']):
                counts['poblacion_nacional'] += 1
                if row['Municipios'][:2] not in DEMOGRAFIA_PROVINCES:
                    continue
                code = demografia_territory_code(row['Municipios'], 5)
                if code not in codes or row['Sexo'] not in ('Total', 'Hombres', 'Mujeres'):
                    raise ValueError(f'Población: territorio o sexo no admitido en registro {ordinal}')
                if not re.fullmatch(r'[0-9]{4}', row['Periodo']):
                    raise ValueError(f'Periodo de población no válido: registro {ordinal}')
                value, state = demografia_ine_number(row['Total'], integer=True)
                writer.writerow([code, row['Sexo'], int(row['Periodo']), value, state, row['Total'], ordinal])
                counts['poblacion_cv'] += 1
                if state == 'error_conversion':
                    incidents.writerow(['poblacion_municipal', origins[DEMOGRAFIA_POP], ordinal, code, 'poblacion', row['Total'], state])
        with (temporary / 'renta_territorial.csv').open('w', encoding='utf-8', newline='') as target, (temporary / 'renta_codigos_historicos.csv').open('w', encoding='utf-8', newline='') as historic:
            writer, historical_writer = csv.writer(target), csv.writer(historic)
            writer.writerow(DEMOGRAFIA_SCHEMAS['renta_territorial'])
            historical_writer.writerow(DEMOGRAFIA_SCHEMAS['renta_codigos_historicos'])
            headers = ['Municipios', 'Distritos', 'Secciones', 'Indicadores de renta media', 'Periodo', 'Total']
            for ordinal, row in demografia_csv_rows(income, headers):
                counts['renta_nacional'] += 1
                if not any(row[field][:2] in DEMOGRAFIA_PROVINCES for field in ('Municipios', 'Distritos', 'Secciones')):
                    continue
                code = demografia_territory_code(row['Municipios'], 5)
                if code not in codes and code != '12066':
                    raise ValueError(f'Renta: municipio ajeno a la referencia en registro {ordinal}: {code}')
                district = demografia_territory_code(row['Distritos'], 7) if row['Distritos'] else None
                section = demografia_territory_code(row['Secciones'], 10) if row['Secciones'] else None
                if (district and not district.startswith(code)) or (section and (not district or not section.startswith(district))):
                    raise ValueError(f'Jerarquía territorial de renta incoherente: registro {ordinal}')
                if not re.fullmatch(r'[0-9]{4}', row['Periodo']) or not row['Indicadores de renta media'].strip():
                    raise ValueError(f'Clave de renta incompleta: registro {ordinal}')
                level, territory = ('seccion', section) if section else ('distrito', district) if district else ('municipio', code)
                value, state = demografia_ine_number(row['Total'])
                values = [level, territory, code, district, section, row['Indicadores de renta media'],
                          int(row['Periodo']), value, state, row['Total'], ordinal]
                if code == '12066':
                    historical_writer.writerow(values + ['codigo_historico_fuera_de_referencia_2025'])
                    counts['renta_historica'] += 1
                else:
                    writer.writerow(values)
                    counts['renta_cv_vigente'] += 1
                if state == 'error_conversion':
                    incidents.writerow(['renta_codigos_historicos' if code == '12066' else 'renta_territorial',
                                        origins[DEMOGRAFIA_INCOME], ordinal, code, 'valor_eur', row['Total'], state])
    for table, schema in DEMOGRAFIA_SCHEMAS.items():
        # El CSV temporal usa vacío como NULL; el texto original vacío se restaura expresamente.
        connection.execute(f"CREATE TEMP TABLE {identificador_sql(table)} AS SELECT * REPLACE(coalesce(valor_origen,'') AS valor_origen) FROM read_csv(?,columns=?,header=true,delim=',',strict_mode=true,ignore_errors=false)", [str(temporary / f'{table}.csv'), schema])
    for table, counter in [('poblacion_municipal', 'poblacion_cv'),
                           ('renta_territorial', 'renta_cv_vigente'),
                           ('renta_codigos_historicos', 'renta_historica')]:
        if connection.execute(f'SELECT count(*) FROM {identificador_sql(table)}').fetchone()[0] != counts[counter]:
            raise ValueError(f'Pérdida de registros INE: {table}')
    return dict(counts)


def demografia_prepare_municipal_park(connection, path, codes):
    connection.execute('CREATE TEMP TABLE parque_municipal (codigo_municipio VARCHAR,fecha_referencia DATE,parque_total BIGINT,vehiculos_distintivo_0 BIGINT,electrificado_origen BIGINT)')
    connection.execute('CREATE TEMP TABLE parque_sin_municipio (codigo_agrupacion_origen VARCHAR,codigo_provincia VARCHAR,fecha_referencia DATE,parque_total BIGINT,vehiculos_distintivo_0 BIGINT,electrificado_origen BIGINT)')
    workbook = load_workbook(path, read_only=True, data_only=True)
    municipalities, unspecified, seen = [], [], set()
    try:
        rows = workbook['DatosMunicipalesGeneral_2025'].iter_rows(values_only=True)
        headers = next(rows)
        fields = ('Código INE', 'Parque Total', 'Distintivo 0', 'Electrificado')
        if len(set(headers)) != len(headers) or not set(fields).issubset(headers):
            raise ValueError('Cabecera municipal DGT inesperada')
        for ordinal, values in enumerate(rows, 1):
            if all(value is None for value in values):
                continue
            row = dict(zip(headers, values))
            code = row['Código INE']
            if not isinstance(code, str) or not re.fullmatch('[0-9]{5}', code) or code in seen:
                raise ValueError(f'Código municipal DGT no válido o repetido: registro {ordinal}')
            seen.add(code)
            if code[:2] not in DEMOGRAFIA_PROVINCES:
                continue
            measures = [row[field] for field in fields[1:]]
            if any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 2**63 - 1 or value != int(value) for value in measures):
                raise ValueError(f'Recuentos DGT no admitidos: {code}')
            measures = [int(value) for value in measures]
            if code.endswith('000'):
                unspecified.append([code, code[:2], date(2025, 12, 31), *measures])
            elif code in codes:
                municipalities.append([code, date(2025, 12, 31), *measures])
            else:
                raise ValueError(f'Municipio DGT no vigente en la referencia: {code}')
    finally:
        workbook.close()
    if {row[0] for row in municipalities} != set(codes):
        raise ValueError('Cobertura municipal DGT incompleta')
    if {row[0] for row in unspecified} != {province + '000' for province in {code[:2] for code in codes}}:
        raise ValueError('Agrupaciones provinciales sin municipio DGT inesperadas')
    connection.executemany('INSERT INTO parque_municipal VALUES (?,?,?,?,?)', municipalities)
    connection.executemany('INSERT INTO parque_sin_municipio VALUES (?,?,?,?,?,?)', unspecified)
    return {'filas_nacionales': len(seen), 'municipios': len(municipalities), 'sin_municipio': len(unspecified)}


def demografia_prepare_detail(connection, path, origin):
    # Tabla de trabajo en disco: solo atributos necesarios, sin cargar el TXT en Python.
    connection.execute("""
        CREATE TABLE dgt_entrada AS SELECT PROVINCIA,MUNICIPIO,TIPO_DGT,PROPULSION,CATELECT,TIPO_DISTINTIVO,ordinality
        FROM read_csv(?,header=true,delim='|',encoding='latin-1',all_varchar=true,
            parallel=false,strict_mode=true,ignore_errors=false) WITH ORDINALITY
    """, [str(path)])
    national = connection.execute('SELECT count(*),min(ordinality),max(ordinality) FROM dgt_entrada').fetchone()
    if national[1:] != (1, national[0]):
        raise ValueError('Ordinales nacionales DGT incoherentes')
    connection.execute("""
        CREATE TABLE parque_detalle_observado AS SELECT ?::VARCHAR origen_id,
            ordinality::BIGINT registro_origen,PROVINCIA codigo_provincia,
            nullif(trim(MUNICIPIO),'') codigo_municipio,'2025-12'::VARCHAR periodo,
            TIPO_DGT tipo_dgt_codigo,PROPULSION propulsion_codigo,
            CATELECT categoria_electrica_codigo,TIPO_DISTINTIVO distintivo_codigo
        FROM dgt_entrada WHERE PROVINCIA IN ('03','12','46')
    """, [origin])
    bad = consultar(connection, """
        SELECT registro_origen,codigo_provincia,codigo_municipio FROM parque_detalle_observado
        WHERE codigo_municipio IS NOT NULL AND (substr(codigo_municipio,1,2)<>codigo_provincia
           OR codigo_municipio NOT IN (SELECT codigo_municipio FROM municipios)) LIMIT 10
    """)
    if bad:
        raise ValueError(f'Municipios publicados por DGT no admitidos: {bad}')
    return {'filas_nacionales': national[0], 'filas_fuera_ambito': connection.execute("SELECT count(*) FROM dgt_entrada WHERE PROVINCIA NOT IN ('03','12','46') OR PROVINCIA IS NULL").fetchone()[0]}


def demografia_validate(connection, codes):
    for table, key in DEMOGRAFIA_KEYS.items():
        comprobar_clave(connection, table, key)
    park = consultar(connection, 'SELECT sum(parque_total) parque_total,sum(vehiculos_distintivo_0) distintivo_0,sum(electrificado_origen) electrificado FROM parque_municipal')[0]
    unspecified = consultar(connection, 'SELECT codigo_provincia,parque_total,vehiculos_distintivo_0,electrificado_origen FROM parque_sin_municipio ORDER BY 1')
    detail = consultar(connection, 'SELECT codigo_provincia,count(*) registros,count(*) FILTER(WHERE codigo_municipio IS NULL) sin_municipio,count(DISTINCT codigo_municipio) municipios_observados FROM parque_detalle_observado GROUP BY 1 ORDER BY 1')
    if sum(row['registros'] for row in detail) != park['parque_total'] + sum(row['parque_total'] for row in unspecified):
        raise ValueError('El detalle DGT no reconcilia con el total municipal y las agrupaciones PP000')
    disagreements = consultar(connection, """
        SELECT codigo_municipio,observados,parque_total FROM
        (SELECT codigo_municipio,count(*) observados FROM parque_detalle_observado
         WHERE codigo_municipio IS NOT NULL GROUP BY 1) d JOIN parque_municipal USING(codigo_municipio)
        WHERE observados<>parque_total
    """)
    if disagreements:
        raise ValueError(f'El detalle observado DGT no coincide con el parque municipal: {disagreements}')
    population = consultar(connection, """
        SELECT anio,sexo,count(*) filas,count(DISTINCT codigo_municipio) municipios,
            count(*) FILTER(WHERE estado_valor<>'informado') sin_valor
        FROM poblacion_municipal GROUP BY 1,2 ORDER BY 1,2
    """)
    if any(row['municipios'] != len(codes) for row in population):
        raise ValueError('Cobertura de población incompleta por año y sexo')
    sex_conflicts = consultar(connection, """
        SELECT codigo_municipio,anio FROM poblacion_municipal GROUP BY 1,2
        HAVING count(*)<>3 OR (count(poblacion)=3 AND
            max(poblacion) FILTER(WHERE sexo='Total')<>
            sum(poblacion) FILTER(WHERE sexo IN ('Hombres','Mujeres')))
    """)
    if sex_conflicts:
        raise ValueError(f'Población: Total no reconcilia con hombres y mujeres: {sex_conflicts[:10]}')
    income = consultar(connection, """
        SELECT nivel_territorial,anio,count(*) filas,count(DISTINCT codigo_municipio) municipios,
            count(*) FILTER(WHERE estado_valor='no_informado') sin_valor,
            count(*) FILTER(WHERE estado_valor='error_conversion') errores
        FROM renta_territorial GROUP BY 1,2 ORDER BY 1,2
    """)
    if any(row['municipios'] != len(codes) for row in income if row['nivel_territorial'] == 'municipio'):
        raise ValueError('Cobertura municipal de renta incompleta')
    return {'parque_municipal_totales': park, 'parque_sin_municipio': unspecified,
            'detalle_por_provincia': detail, 'municipios_detalle_reconciliados': True,
            'poblacion_por_anio_sexo': population, 'poblacion_total_reconciliada': True,
            'renta_por_nivel_anio': income,
            'categorias_electricas_detalle': consultar(connection, 'SELECT categoria_electrica_codigo,count(*) registros FROM parque_detalle_observado GROUP BY 1 ORDER BY 1'),
            'distintivos_detalle': consultar(connection, 'SELECT distintivo_codigo,count(*) registros FROM parque_detalle_observado GROUP BY 1 ORDER BY 1'),
            'incidencias_conversion': connection.execute('SELECT count(*) FROM incidencias').fetchone()[0]}
