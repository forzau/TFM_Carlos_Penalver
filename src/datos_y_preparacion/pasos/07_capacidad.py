"""Silver: capacidad i-DE, acreditación de metadatos y geometrías."""

from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
import csv
import json
import re
import unicodedata

from src.datos_y_preparacion.pasos.comunes import (
    comprobar_clave,
    consultar,
    huella,
    identificador_sql,
    texto_sql,
)
from src.datos_y_preparacion.pasos import demografia as _demografia
from src.datos_y_preparacion.pasos import recarga as _recarga


CAPACIDAD_SOURCE = 'Fuentes/Demanda_energetica.csv'


CAPACIDAD_PROVINCES = {'Alicante/Alacant': '03', 'Castellón/Castelló': '12', 'Valencia/València': '46'}


CAPACIDAD_NULL = '\x1eNULL_SILVER\x1e'


CAPACIDAD_RAW = {
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


CAPACIDAD_TYPED = {**dict.fromkeys(('nivel_tension_kv', 'capacidad_firme_disponible_mw',
    'capacidad_ocupada_mw', 'capacidad_admitida_no_evaluada_mw'), 'DECIMAL(18,2)'),
    'posiciones_ocupadas': 'BIGINT', 'posiciones_libres': 'BIGINT',
    'compromiso_regulatorio': 'BOOLEAN', 'nudo_0_asterisco': 'BOOLEAN'}


CAPACIDAD_SCHEMA = {**dict.fromkeys(CAPACIDAD_RAW, 'VARCHAR'), 'origen_id': 'VARCHAR', 'registro_origen': 'BIGINT',
    'codigo_provincia': 'VARCHAR', 'fecha_referencia': 'DATE', 'estado_fecha': 'VARCHAR',
    'estado_coordenadas': 'VARCHAR'}

for field, datatype in CAPACIDAD_TYPED.items():
    CAPACIDAD_SCHEMA.update({field: datatype, 'estado_' + field: 'VARCHAR'})


CAPACIDAD_INC_SCHEMA = dict.fromkeys(('origen_id', 'punto_conexion_id', 'campo', 'valor_origen', 'motivo'), 'VARCHAR')


CAPACIDAD_INC_SCHEMA['registro_origen'] = 'BIGINT'


def capacidad_typed_value(raw, datatype, positive=False):
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


def capacidad_coordinate_state(x, y):
    if not x.strip() or not y.strip():
        return 'no_informadas'
    if any(len(v.strip()) > 64 or not re.fullmatch(r'[0-9]+(?:,[0-9]+)?', v.strip()) for v in (x, y)):
        return 'error_formato'
    # shortcut: no crear geometría hasta acreditar huso y datum de esta copia.
    return 'pendiente_crs'


def capacidad_prepare(connection, path, temporary, origin):
    national, selected, seen = Counter(), Counter(), set()
    count = 0
    with (temporary / 'capacidad.csv').open('w', encoding='utf-8', newline='') as out, \
            (temporary / 'incidencias.csv').open('w', encoding='utf-8', newline='') as incidents:
        writer, incident_writer = csv.writer(out), csv.writer(incidents)
        writer.writerow(CAPACIDAD_SCHEMA)
        incident_writer.writerow(CAPACIDAD_INC_SCHEMA)
        for ordinal, row in _demografia.demografia_csv_rows(path, list(CAPACIDAD_RAW.values())):
            if any(CAPACIDAD_NULL in v for v in row.values()):
                raise ValueError('El texto de entrada contiene el marcador reservado de NULL')
            key = row[CAPACIDAD_RAW['punto_conexion_id']]
            if not key.strip() or key != key.strip() or key in seen:
                raise ValueError(f'Identificador nacional vacío, con espacios exteriores o repetido: registro {ordinal}')
            seen.add(key)
            province = row['Provincia']
            national[province] += 1
            if province not in CAPACIDAD_PROVINCES:
                continue
            selected[province] += 1
            count += 1
            result = {field: row[header] for field, header in CAPACIDAD_RAW.items()}
            result.update(origen_id=origin, registro_origen=ordinal, codigo_provincia=CAPACIDAD_PROVINCES[province],
                fecha_referencia=None, estado_fecha='no_acreditada',
                estado_coordenadas=capacidad_coordinate_state(result['x_utm_origen'], result['y_utm_origen']))

            def incidence(field, value, reason):
                entry = {'origen_id': origin, 'punto_conexion_id': key, 'campo': field,
                         'valor_origen': value, 'motivo': reason, 'registro_origen': ordinal}
                incident_writer.writerow([entry[k] for k in CAPACIDAD_INC_SCHEMA])

            for field, datatype in CAPACIDAD_TYPED.items():
                raw = result[field + '_origen']
                value, state = capacidad_typed_value(raw, datatype, positive=(field == 'nivel_tension_kv'))
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
            writer.writerow([CAPACIDAD_NULL if result[k] is None else result[k] for k in CAPACIDAD_SCHEMA])
    if not count:
        raise ValueError('No hay puntos de conexión de las tres provincias previstas')
    for table, filename, schema in [('capacidad_demanda', 'capacidad.csv', CAPACIDAD_SCHEMA),
                                    ('incidencias', 'incidencias.csv', CAPACIDAD_INC_SCHEMA)]:
        connection.execute(f'''CREATE TABLE {table} AS SELECT * FROM read_csv(?,columns=?,
            header=true,delim=',',quote='"',escape='"',auto_detect=false,nullstr=?,
            strict_mode=true,ignore_errors=false)''', [str(temporary / filename), schema, CAPACIDAD_NULL])
    comprobar_clave(connection, 'capacidad_demanda', ['punto_conexion_id'])
    comprobar_clave(connection, 'capacidad_demanda', ['origen_id', 'registro_origen'])
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


def capacidad_validate(connection):
    return {'por_provincia': consultar(connection, '''SELECT codigo_provincia,provincia_nombre_origen,
        count(*) puntos,count(DISTINCT subestacion_origen) codigos_subestacion,
        count(DISTINCT municipio_nombre_origen) etiquetas_municipales
        FROM capacidad_demanda GROUP BY 1,2 ORDER BY 1'''),
        'medidas': {field: consultar(connection, f'''SELECT estado_{field} estado,count(*) filas,
            min({field})::VARCHAR minimo,max({field})::VARCHAR maximo
            FROM capacidad_demanda GROUP BY 1 ORDER BY 1''') for field in CAPACIDAD_TYPED},
        'banderas': consultar(connection, '''SELECT compromiso_regulatorio,nudo_0_asterisco,
            count(*) puntos FROM capacidad_demanda GROUP BY 1,2 ORDER BY 1,2'''),
        'capacidad_disponible': consultar(connection, '''SELECT CASE WHEN capacidad_firme_disponible_mw IS NULL
            THEN 'no_evaluable' WHEN capacidad_firme_disponible_mw=0 THEN 'cero' ELSE 'positiva' END estado,
            count(*) puntos FROM capacidad_demanda GROUP BY 1 ORDER BY 1'''),
        'coordenadas': consultar(connection, 'SELECT estado_coordenadas,count(*) puntos FROM capacidad_demanda GROUP BY 1'),
        'fechas': consultar(connection, 'SELECT estado_fecha,count(*) puntos FROM capacidad_demanda GROUP BY 1'),
        'incidencias': consultar(connection, 'SELECT campo,motivo,count(*) filas FROM incidencias GROUP BY 1,2 ORDER BY 1,2'),
        'numero_incidencias': connection.execute('SELECT count(*) FROM incidencias').fetchone()[0]}


METADATOS_IDE_PAGE = 'https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo'


METADATOS_IDE_BOE = 'https://www.boe.es/buscar/doc.php?id=BOE-A-2025-9913'


def metadatos_ide_normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).split())


class metadatos_ide_Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = set()
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'a':
            self.links.update(v for k, v in attrs if k == 'href')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


def metadatos_ide_verify(root, evidence):
    if evidence['version'] != 1 or evidence['recurso_id'] != 'ide_capacidad_demanda':
        raise ValueError('Contrato de evidencia i-DE no admitido')

    def checked(entry):
        path = (root / entry['ruta']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Evidencia fuera del proyecto')
        stamp = huella(path)
        if any(stamp[k] != entry[k] for k in ('bytes', 'sha256')):
            raise ValueError(f"Huella distinta: {entry['ruta']}")
        return path

    paths = {name: checked(entry) for name, entry in evidence['archivos'].items()}
    source, official = paths['original'], paths['csv_oficial']
    if evidence['archivos']['original']['sha256'] != evidence['archivos']['csv_oficial']['sha256']:
        raise ValueError('El CSV oficial no coincide con el original')
    with source.open('rb') as a, official.open('rb') as b:
        while True:
            left, right = a.read(1024 * 1024), b.read(1024 * 1024)
            if left != right:
                raise ValueError('Los CSV no son idénticos byte por byte')
            if not left:
                break
    with source.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, delimiter=';')
        if next(reader) != list(CAPACIDAD_RAW.values()):
            raise ValueError('Cabecera ajena al formato comprobado')
        rows = list(reader)
    if any(len(row) != len(CAPACIDAD_RAW) for row in rows):
        raise ValueError('Ancho de registro i-DE incorrecto')
    if len({r[-1] for r in rows}) != len(rows) or any(not r[-1].strip() for r in rows):
        raise ValueError('Identificadores vacíos o repetidos')
    provinces = Counter(r[1] for r in rows if r[1] in CAPACIDAD_PROVINCES)
    if len(rows) != evidence['filas_nacionales'] or dict(provinces) != evidence['filas_cv_provincia']:
        raise ValueError('Recuentos diferentes de la edición acreditada')

    published = date.fromisoformat(evidence['fecha_publicacion'])
    url = evidence['url_csv_oficial']
    if not url.startswith('https://www.i-de.es/documents/') or published.strftime('%Y_%m_%d') not in url:
        raise ValueError('Fecha y enlace de edición incoherentes')
    page = json.loads(paths['pagina_ide'].read_text(encoding='utf-8'))
    regulation = metadatos_ide_Document()
    regulation.feed(paths['norma'].read_text(encoding='utf-8'))
    if url not in {entry['url'] for entry in page['enlaces']}:
        raise ValueError('El histórico conservado no enlaza el CSV')
    text = metadatos_ide_normalized(page['texto'])
    if 'resolución de 30 de abril de 2025' not in text:
        raise ValueError('No consta la declaración de formato del proveedor')
    text = metadatos_ide_normalized(' '.join(regulation.text))
    start = '1. Formato para la publicación de las capacidades de acceso para instalaciones de demanda'
    end = '2. Formato para la publicación de las capacidades de acceso para instalaciones de generación'
    if start not in text or end not in text:
        raise ValueError('No se identifica el apartado de demanda de la norma')
    demand = text.split(start, 1)[1].split(end, 1)[0]
    for field in ('X', 'Y'):
        fragment = f'Coordenada UTM {field}. Coordenadas de la ubicación de la subestación, en el sistema ETRS89 UTM referidas al huso 30 para la península'
        if fragment not in demand:
            raise ValueError('La norma conservada no acredita CRS en el apartado de demanda')
    rule = 'dentro de los cinco primeros días del mes siguiente al que se refiere la información'
    if rule not in text or not 1 <= published.day <= 5:
        raise ValueError('No se acredita la regla del periodo mensual')
    month = date(published.year - (published.month == 1), 12 if published.month == 1 else published.month - 1, 1)
    if evidence['periodo_referencia'] != month.strftime('%Y-%m'):
        raise ValueError('Periodo mensual incoherente con la publicación')
    if evidence['crs_cv'] != 'EPSG:25830' or evidence['fecha_corte_exacta'] is not None:
        raise ValueError('Metadatos incompatibles con el alcance acreditado')

    # Comprobar de nuevo las evidencias tras la lectura; no se modifica ningún insumo.
    for entry in evidence['archivos'].values():
        checked(entry)
    return {'estado': 'fecha_y_crs_acreditados_documentalmente',
            'comprobado_utc': datetime.now(timezone.utc).isoformat(),
            'identidad_csv': 'igualdad_binaria_completa', 'sha256_original': evidence['archivos']['original']['sha256'],
            'filas_nacionales': len(rows), 'filas_cv': sum(provinces.values()),
            'fecha_publicacion': published.isoformat(), 'periodo_referencia': evidence['periodo_referencia'],
            'criterio_periodo': 'mes_anterior_segun_formato_publicacion_CNMC',
            'fecha_corte_exacta': None, 'crs_cv': 'EPSG:25830',
            'referencia_crs': 'declaracion_de_formato_ide_y_anexo_demanda_BOE_A_2025_9913',
            'pagina': METADATOS_IDE_PAGE, 'norma': METADATOS_IDE_BOE,
            'alcance': 'Acreditación de metadatos; no genera capas, asignaciones municipales o una nueva ejecución Silver.'}


CAPACIDAD_GEO_KEYS = {'capacidad_demanda_geo': ['punto_conexion_id'],
        'capacidad_municipios_candidatos': ['punto_conexion_id', 'codigo_municipio'],
        'entidad_municipio': ['punto_conexion_id'],
        'incidencias_espaciales': ['punto_conexion_id']}


CAPACIDAD_GEO_HISTORICAL = {'estado_fecha': 'estado_fecha_preparacion',
              'estado_coordenadas': 'estado_coordenadas_preparacion'}


def capacidad_geo_prepare(c, metadata):
    comprobar_clave(c, 'capacidad_demanda', ['punto_conexion_id'])
    # Variantes oficiales INE/IGN dentro de la provincia. Sin similitud aproximada.
    labels = c.execute('''SELECT codigo_municipio,nombre_municipio FROM municipios
        UNION SELECT codigo_municipio,nombre_municipio_ign FROM recintos''').fetchall()
    aliases = sorted({(code[:2], _recarga.recarga_geo_name_key(variant), code) for code, label in labels
                      for variant in [label, *label.split('/')] if variant.strip()})
    c.execute('CREATE TEMP TABLE etiquetas(provincia VARCHAR,nombre VARCHAR,codigo_municipio VARCHAR)')
    c.executemany('INSERT INTO etiquetas VALUES (?,?,?)', aliases)
    names = c.execute('SELECT DISTINCT municipio_nombre_origen FROM capacidad_demanda').fetchall()
    c.execute('CREATE TEMP TABLE nombres(texto VARCHAR,clave VARCHAR)')
    c.executemany('INSERT INTO nombres VALUES (?,?)', [(t, _recarga.recarga_geo_name_key(t or '')) for (t,) in names])
    c.execute('''CREATE TEMP TABLE etiquetas_unicas AS SELECT provincia,nombre,min(codigo_municipio) codigo
        FROM etiquetas WHERE nombre<>'' GROUP BY 1,2 HAVING count(DISTINCT codigo_municipio)=1''')
    c.execute(f'''CREATE TABLE capacidad_demanda_geo AS SELECT * RENAME(
        estado_fecha AS estado_fecha_preparacion,estado_coordenadas AS estado_coordenadas_preparacion),
        {texto_sql(metadata['fecha_publicacion'])}::DATE fecha_publicacion,
        {texto_sql(metadata['periodo_referencia'])}::VARCHAR periodo_referencia,
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


def capacidad_geo_validate(c):
    for name, keys in CAPACIDAD_GEO_KEYS.items():
        comprobar_clave(c, name, keys)
    original = [r[0] for r in c.execute('DESCRIBE capacidad_demanda').fetchall()]
    fields = ','.join(identificador_sql(k) for k in original)
    restored = ','.join(identificador_sql(CAPACIDAD_GEO_HISTORICAL.get(k, k)) + ' AS ' + identificador_sql(k) for k in original)
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
        'por_estado': consultar(c, '''SELECT estado_geometria,estado_contraste_territorial,count(*) puntos
            FROM capacidad_demanda_geo GROUP BY 1,2 ORDER BY 1,2'''),
        'por_provincia': consultar(c, '''SELECT codigo_provincia,count(*) puntos,
            count(*) FILTER(WHERE admitida_asignacion_municipal) admitidos FROM capacidad_demanda_geo GROUP BY 1 ORDER BY 1'''),
        'atributos_originales': 'conservados_integramente', 'coordenadas': 'sin_desplazamiento_ni_reproyeccion'}
