"""Silver: entidades de recarga y contraste espacial municipal."""

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import csv
import io
import json
import re
import unicodedata

from src.datos_y_preparacion.comunes import (
    comprobar_archivo,
    comprobar_clave,
    consultar,
    identificador_sql,
)


RECARGA_SOURCE = 'Fuentes/instalaciones_actuales.csv'


RECARGA_HEADERS = ['COMUNIDAD AUTONOMA', 'PROVINCIA', 'MUNICIPIO', 'LATITUD', 'LONGITUD',
           'NOMBRE INSTALACION', 'DIRECCIÓN', 'CODIGO POSTAL', 'LOCALIZACION',
           'TIPO HORARIO APERTURA', 'HORARIO APERTURA', 'NOMBRE OPERADOR', 'COD.OPERADOR',
           'TIPOS DE SERVICIOS', 'COD.INSTALACION', 'ID. PUNTO DE RECARGA', 'ACCESIBILIDAD',
           'METODOS DE PAGOS', 'COD. PUNTO DE RECARGA', 'ID. CONECTOR', 'TIPO CONECTOR',
           'TIPO DE CARGA', 'FORMATO', 'POTENCIA MAXIMA', 'VOLTAJE', 'INTENSIDAD',
           'FECHA DE ULTIMA MODIFICACION']


RECARGA_INSTALL = {'instalacion_id': 14, 'nombre_instalacion': 5, 'operador_id': 12,
           'nombre_operador': 11, 'provincia_nombre_origen': 1, 'municipio_nombre_origen': 2,
           'direccion': 6, 'codigo_postal': 7, 'latitud_origen': 3, 'longitud_origen': 4,
           'localizacion_origen': 8, 'tipo_horario_origen': 9}


RECARGA_POINT = {'instalacion_id': 14, 'punto_id': 15, 'codigo_punto_origen': 18, 'accesibilidad_origen': 16}


RECARGA_CONNECTOR = {'instalacion_id': 14, 'punto_id': 15, 'conector_id': 19, 'tipo_conector': 20,
             'tipo_carga': 21, 'formato_conector': 22, 'potencia_maxima_origen': 23,
             'fecha_ultima_modificacion_origen': 26, 'horario_apertura_origen': 10,
             'servicios_origen': 13, 'metodos_pago_origen': 17,
             'voltaje_origen': 24, 'intensidad_origen': 25}


RECARGA_KEYS = {'recarga_instalaciones': ['instalacion_id'],
        'recarga_puntos': ['instalacion_id', 'punto_id'],
        'recarga_conectores': ['instalacion_id', 'punto_id', 'conector_id']}


RECARGA_PROVINCES = {'Alicante/Alacant', 'Castellón/Castelló', 'Valencia/València'}


RECARGA_UNKNOWN = {'', 'DESCONOCIDO', 'NODISPONIBLE'}


RECARGA_FIELD = re.compile(r'(=?)"(.*?)"(?=;|\r?\n|\Z)', re.S)


def recarga_export_rows(path):
    # shortcut: dialecto de esta exportación de hasta 64 MiB; revisar si cambia el exportador.
    with path.open('rb') as stream:
        raw = stream.read(64 * 1024**2 + 1)
    if len(raw) > 64 * 1024**2:
        raise ValueError('Exportación mayor que el límite de lectura de 64 MiB')
    text = raw.decode('utf-16-le')
    header, separator, _ = text.partition('\n')
    if not separator or header.rstrip('\r').split(';') != RECARGA_HEADERS:
        raise ValueError('Cabecera MITECO inesperada')
    pos, ordinal = len(header) + 1, 0
    while pos < len(text):
        start, values, wrappers = pos, [], []
        for column in range(len(RECARGA_HEADERS)):
            match = RECARGA_FIELD.match(text, pos)
            if not match or (match[1] and column not in (3, 4, 7, 8)):
                raise ValueError(f'Dialecto MITECO no admitido: registro {ordinal + 1}, columna {column + 1}')
            wrappers.append(match[1])
            values.append(match[2])
            pos = match.end()
            if column < len(RECARGA_HEADERS) - 1:
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


def recarga_coordinate(raw, latitude):
    if raw.strip() in RECARGA_UNKNOWN:
        return None, 'no_informado'
    if not re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?', raw):
        return None, 'error_conversion'
    value = float(raw)
    limit = 90 if latitude else 180
    return (value, 'rango_valido_datum_pendiente') if -limit <= value <= limit else (None, 'fuera_rango')


def recarga_power(raw):
    if raw.strip() in RECARGA_UNKNOWN:
        return None, 'no_informado'
    if not re.fullmatch(r'[0-9]+(?:,[0-9]{1,2})? kW', raw):
        return None, 'error_conversion'
    value = Decimal(raw[:-3].replace(',', '.'))
    if value >= Decimal('10000000000000000'):
        return None, 'error_conversion'
    return value, 'informado'


def recarga_modified(raw):
    if raw.strip() in RECARGA_UNKNOWN:
        return None, 'no_informado'
    if not re.fullmatch(r'[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{1,2}:[0-9]{2}:[0-9]{2}', raw):
        return None, 'error_conversion'
    try:
        value = datetime.strptime(raw, '%d/%m/%Y %H:%M:%S')
    except ValueError:
        return None, 'error_conversion'
    return value, 'informado_sin_zona'


def recarga_parent(parents, key, values, entity):
    if key in parents and parents[key] != values:
        raise ValueError(f'Atributos contradictorios en {entity}: {key}')
    parents[key] = values


def recarga_prepare(connection, path, temporary):
    installs, points, national = {}, {}, defaultdict(list)
    details, incidents, counts = [], [], Counter()
    for ordinal, row, differs in recarga_export_rows(path):
        counts['filas_nacionales'] += 1
        counts['textos_preservados_frente_csv_permisivo_nacional'] += differs
        key = tuple(row[i] for i in (14, 15, 19))
        if any(not value.strip() for value in key):
            raise ValueError(f'Clave de conector incompleta: registro {ordinal}')
        national[key].append((ordinal, row))
        if (row[0] == 'Comunitat Valenciana') != (row[1] in RECARGA_PROVINCES):
            raise ValueError(f'Comunidad y provincia incoherentes: registro {ordinal}')
        if row[0] != 'Comunitat Valenciana':
            counts['filas_fuera_ambito'] += 1
            continue
        counts['filas_cv'] += 1
        counts['textos_preservados_frente_csv_permisivo_cv'] += differs
        recarga_parent(installs, key[0], tuple(row[i] for i in RECARGA_INSTALL.values()), 'instalación')
        recarga_parent(points, key[:2], tuple(row[i] for i in RECARGA_POINT.values()), 'punto')
        kw, kw_state = recarga_power(row[23])
        timestamp, date_state = recarga_modified(row[26])
        details.append([*(row[i] for i in RECARGA_CONNECTOR.values()), ordinal, kw, kw_state, timestamp, date_state])
        for field, raw, state in [('potencia_maxima_kw', row[23], kw_state),
                                  ('fecha_ultima_modificacion', row[26], date_state)]:
            if state == 'error_conversion':
                incidents.append(['recarga_conectores', ordinal, field, raw, state])
    if not details:
        raise ValueError('No hay conectores de la Comunitat Valenciana')
    for name, fields in [('recarga_instalaciones', RECARGA_INSTALL), ('recarga_puntos', RECARGA_POINT), ('recarga_conectores', RECARGA_CONNECTOR)]:
        columns = ','.join(identificador_sql(field) + ' VARCHAR' for field in fields)
        if name == 'recarga_instalaciones':
            columns += ',latitud DOUBLE,longitud DOUBLE,estado_coordenadas VARCHAR'
        elif name == 'recarga_conectores':
            columns += ',registro_origen BIGINT,potencia_maxima_kw DECIMAL(18,2),estado_potencia VARCHAR,fecha_ultima_modificacion TIMESTAMP,estado_fecha VARCHAR'
        connection.execute(f'CREATE TABLE {name} ({columns})')
    installation_rows = []
    for key, values in installs.items():
        lat, lat_state = recarga_coordinate(values[8], True)
        lon, lon_state = recarga_coordinate(values[9], False)
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
        columns = ','.join(f"coalesce({identificador_sql(k)},'')" if v == 'VARCHAR' else identificador_sql(k) for k, v in schema.items())
        connection.execute(f'''INSERT INTO {table} SELECT {columns} FROM read_csv(?,columns=?,
            header=true,delim=',',quote='"',escape='"',auto_detect=false,
            timestampformat='%Y-%m-%d %H:%M:%S',strict_mode=true,ignore_errors=false)''', [str(staging), schema])
    duplicates = []
    for key, rows in national.items():
        if len(rows) > 1:
            duplicates.append({'clave': list(key), 'registros_origen': [n for n, _ in rows],
                'comunidades': sorted({r[0] for _, r in rows}),
                'campos_variables': [RECARGA_HEADERS[i] for i in range(len(RECARGA_HEADERS)) if len({r[i] for _, r in rows}) > 1],
                'filas_identicas': len({tuple(r) for _, r in rows}) == 1})
    return {'recuentos': dict(counts), 'claves_repetidas_nacionales': duplicates,
            'filas_adicionales_por_clave_nacional': sum(len(d['registros_origen']) - 1 for d in duplicates),
            'filas_eliminadas_en_cv': 0, 'atributos_padre_contrastados': True,
            'dialecto': 'UTF-16LE; campos entre comillas exteriores, comillas interiores literales, envoltorios ="texto" sin evaluación; 27 campos; reconstrucción exacta de cada registro'}


def recarga_validate(connection):
    for table, keys in RECARGA_KEYS.items():
        comprobar_clave(connection, table, keys)
        for key in keys:
            if connection.execute(f'SELECT count(*) FROM {table} WHERE trim({identificador_sql(key)})=\'\'').fetchone()[0]:
                raise ValueError(f'Clave vacía: {table}')
    comprobar_clave(connection, 'recarga_conectores', ['registro_origen'])
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
        'por_provincia': consultar(connection, '''SELECT provincia_nombre_origen,count(DISTINCT i.instalacion_id) instalaciones,
            count(DISTINCT (p.instalacion_id,p.punto_id)) puntos,count(*) conectores
            FROM recarga_instalaciones i JOIN recarga_puntos p USING(instalacion_id)
            JOIN recarga_conectores c USING(instalacion_id,punto_id) GROUP BY 1 ORDER BY 1'''),
        'coordenadas': consultar(connection, 'SELECT estado_coordenadas,count(*) instalaciones FROM recarga_instalaciones GROUP BY 1'),
        'potencia': consultar(connection, 'SELECT estado_potencia,count(*) conectores,min(potencia_maxima_kw)::VARCHAR minimo_kw,max(potencia_maxima_kw)::VARCHAR maximo_kw FROM recarga_conectores GROUP BY 1'),
        'fechas': consultar(connection, 'SELECT estado_fecha,count(*) conectores,min(fecha_ultima_modificacion)::VARCHAR minima,max(fecha_ultima_modificacion)::VARCHAR maxima FROM recarga_conectores GROUP BY 1'),
        'accesibilidad': consultar(connection, 'SELECT accesibilidad_origen,count(*) puntos FROM recarga_puntos GROUP BY 1 ORDER BY 1'),
        'incidencias': connection.execute('SELECT count(*) FROM incidencias').fetchone()[0]}


RECARGA_GEO_RESOURCE = '047c1f64-7552-44da-a639-2291292e650d'


RECARGA_GEO_ENDPOINT = 'https://energia.serviciosmin.gob.es/Ripree/ExportarInstalaciones/Export'


RECARGA_GEO_KEYS = {'recarga_instalaciones_geo': ['instalacion_id'],
        'recarga_municipios_candidatos': ['instalacion_id', 'codigo_municipio'],
        'entidad_municipio': ['tabla_entidad', 'clave_entidad', 'codigo_municipio']}


def recarga_geo_evidence(root, path):
    stamp = comprobar_archivo(root, path)
    receipt_path = path.with_suffix(path.suffix + '.adquisicion.json')
    receipt_stamp = comprobar_archivo(root, receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if any(stamp[k] != receipt[k] for k in ('bytes', 'sha256')):
        raise ValueError('El catálogo MITECO difiere del recibo conservado')
    catalog = json.loads(path.read_text(encoding='utf-8'))
    resources = [r for r in catalog['result']['resources'] if r['id'] == RECARGA_GEO_RESOURCE]
    if not catalog.get('success') or len(resources) != 1:
        raise ValueError('Recurso CSV MITECO no identificado de forma única')
    resource = resources[0]
    if (resource['format'] != 'CSV' or resource['url'] != RECARGA_GEO_ENDPOINT or
            resource['reference_system'] != 'http://www.opengis.net/def/crs/EPSG/0/4258'):
        raise ValueError('Declaración espacial o endpoint MITECO distintos de los investigados')
    return {'catalogo': stamp, 'recibo': receipt_stamp, 'recurso': RECARGA_GEO_RESOURCE,
            'url': receipt['url_solicitada'], 'crs_declarado': 'EPSG:4258'}


def recarga_geo_name_key(value):
    # Solo variantes de escritura; nunca buscar el municipio más parecido.
    return '/'.join(sorted(''.join(c for c in unicodedata.normalize('NFKD', part.casefold())
                                  if c.isalnum()) for part in value.split('/')))


def recarga_geo_prepare(connection, temporary):
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
                writer.writerow([text, recarga_geo_name_key(text)])
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


def recarga_geo_validate(connection):
    for table, keys in RECARGA_GEO_KEYS.items():
        comprobar_clave(connection, table, keys)
    fields = ','.join(identificador_sql(r[0]) for r in connection.execute('DESCRIBE recarga_instalaciones').fetchall())
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
    for table in RECARGA_KEYS:
        original = connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
        joined, admitted = connection.execute(f'''SELECT count(*),count(*) FILTER(WHERE g.admitida_asignacion_municipal)
            FROM {table} p JOIN recarga_instalaciones_geo g USING(instalacion_id)''').fetchone()
        if original != joined:
            raise ValueError('Se pierden o multiplican entidades al cruzar instalaciones')
        controls[table] = {'originales': original, 'tras_relacion': joined, 'con_asignacion_admitida': admitted}
    return {'entidades': controls, 'error_vuelta_grados_max': error,
        'por_estado': consultar(connection, 'SELECT estado_geometria,estado_contraste_territorial,count(*) instalaciones FROM recarga_instalaciones_geo GROUP BY 1,2 ORDER BY 1,2'),
        'municipios_con_instalaciones_admitidas': connection.execute('SELECT count(DISTINCT codigo_municipio) FROM entidad_municipio').fetchone()[0],
        'discrepancias_por_etiqueta': consultar(connection, '''SELECT provincia_nombre_origen,municipio_nombre_origen,
            codigo_municipio_declarado,codigo_municipio_espacial,nombre_municipio_espacial,count(*) instalaciones,
            max(distancia_municipio_declarado_m) distancia_maxima_m FROM recarga_instalaciones_geo
            WHERE NOT admitida_asignacion_municipal GROUP BY 1,2,3,4,5 ORDER BY instalaciones DESC,1,2,4'''),
        'incidencias': connection.execute('SELECT count(*) FROM incidencias_espaciales').fetchone()[0]}
