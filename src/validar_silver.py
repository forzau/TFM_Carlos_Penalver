"""Fase 8: revisión trazable de recarga y relaciones/calidad conjunta de Silver.

Lee las ejecuciones vigentes sin rehacer Bronze ni el TXT DGT. No produce Gold.
Las relaciones espaciales son intersecciones, no repartos de indicadores.
"""

import argparse
import json
import re
import sys
import tempfile
import unicodedata
from html import unescape
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import duckdb

from auditar_fuentes import ident, sql_string, query
from catalogar_bronze import ROOT, fingerprint
from georreferenciar_recarga import checked
from preparar_demografia_parque import KEYS as DEMOGRAPHIC_KEYS, check_key
from preparar_recarga import KEYS as CHARGING_KEYS
from preparar_trafico_red import KEYS as ROAD_KEYS
from preparar_poi_osm import KEYS as OSM_KEYS
from georreferenciar_recarga import KEYS as GEO_KEYS
from georreferenciar_capacidad_demanda import KEYS as CAPACITY_GEO_KEYS, HISTORICAL
from verificar_metadatos_ide import verify as verify_capacity_metadata


BLOCKS = ('base_territorial', 'demografia_parque', 'recarga', 'trafico_red',
          'poi_osm', 'capacidad_demanda', 'recarga_espacial', 'capacidad_demanda_espacial')
PRIMARY_KEYS = {
    **{('base_territorial', t): ['codigo_municipio'] for t in ('municipios', 'recintos_municipales')},
    **{('demografia_parque', t): k for t, k in DEMOGRAPHIC_KEYS.items()},
    **{('recarga', t): k for t, k in CHARGING_KEYS.items()},
    **{('trafico_red', t): k for t, k in ROAD_KEYS.items()},
    **{('poi_osm', t): k for t, k in OSM_KEYS.items()},
    **{('recarga_espacial', t): k for t, k in GEO_KEYS.items()},
    **{('capacidad_demanda_espacial', t): k for t, k in CAPACITY_GEO_KEYS.items()},
    ('capacidad_demanda', 'capacidad_demanda'): ['punto_conexion_id'],
}
SPATIAL = (
    ('poi_osm', 'poi_elementos', ['origen_id', 'fid_origen'], 'POI'),
    ('trafico_red', 'aforos_tramo_anio', ['tramo_aforo_id', 'anio'], 'LINEA'),
    ('trafico_red', 'red_tramos', ['provincia_origen', 'tramo_id'], 'LINEA'),
    ('capacidad_demanda_espacial', 'capacidad_demanda_geo', ['punto_conexion_id'], 'PUNTO'),
)
OUTPUT_KEYS = {
    'revision_recarga': ['instalacion_id'],
    'recarga_municipio_validado': ['instalacion_id'],
    'relaciones_espaciales': ['tabla_entidad', 'clave_entidad', 'codigo_municipio'],
    'estado_relaciones_espaciales': ['tabla_entidad', 'clave_entidad'],
    'cobertura_estadistica': ['tabla_entidad', 'periodo', 'segmento', 'codigo_municipio'],
    'estado_fuentes': ['bloque'],
}


def table(block, name):
    return ident(block + '__' + name)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def normalized(value):
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in
        unicodedata.normalize('NFKD', (value or '').casefold()) if not unicodedata.combining(c)).split())


def within(directory, relative):
    path = (directory / relative).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError('Ruta fuera de la carpeta esperada')
    return path


def load_inputs(c, root):
    """Verifica huellas, esquemas y recuentos de las salidas y sus referencias."""
    files, reports, profiles, outputs_by_path = [], {}, [], {}
    for block in BLOCKS:
        directory = root / 'resultados/silver' / block
        pointer_path = directory / 'actual.json'
        files.append(checked(root, pointer_path))
        pointer = json.loads(pointer_path.read_text(encoding='utf-8'))
        report_path = within(directory, pointer['informe'])
        run_path = within(directory, pointer['ejecucion'])
        if report_path != run_path / 'informe.json':
            raise ValueError('Informe y ejecución no coinciden')
        files.append(checked(root, report_path))
        report = json.loads(report_path.read_text(encoding='utf-8'))
        if report['ejecucion'] != pointer['ejecucion'] or not report['estado'].startswith('preparada'):
            raise ValueError(f'Ejecución no preparada: {block}')
        reports[block] = report
        seen = set()
        for output in report['salidas']:
            path = within(run_path, output['archivo'])
            if path.parent != run_path or path.suffix != '.parquet' or path.stem in seen:
                raise ValueError('Salida repetida o fuera de la ejecución')
            seen.add(path.stem)
            stamp = checked(root, path, output)
            files.append(stamp)
            outputs_by_path[stamp['ruta']] = stamp
            name = table(block, path.stem)
            c.execute(f'CREATE VIEW {name} AS SELECT * FROM read_parquet({sql_string(str(path))})')
            schema = [{'campo': r[0], 'tipo': r[1]} for r in c.execute(f'DESCRIBE {name}').fetchall()]
            if schema != output['esquema']:
                raise ValueError(f'Esquema distinto del informe: {block}/{path.name}')
            count = c.execute(f'SELECT count(*) FROM {name}').fetchone()[0]
            expected_count = output.get('filas', 542 if block == 'base_territorial' else None)
            if count != expected_count:
                raise ValueError(f'Recuento distinto del informe: {block}/{path.name}')
            key = PRIMARY_KEYS.get((block, path.stem))
            if key:
                check_key(c, block + '__' + path.stem, key)
            if 'geometria' in {r['campo'] for r in schema}:
                if dict((r['campo'], r['tipo']) for r in schema)['geometria'] != "GEOMETRY('EPSG:25830')":
                    raise ValueError('CRS espacial no admitido')
                meta = dict(c.execute('SELECT decode(key),decode(value) FROM parquet_kv_metadata(?)', [str(path)]).fetchall())
                if json.loads(meta['geo'])['columns']['geometria']['crs']['id'] != {'authority':'EPSG','code':25830}:
                    raise ValueError('Metadato GeoParquet distinto del tipo')
            fields = [r['campo'] for r in schema]
            nulls = c.execute(f"SELECT {','.join('count(*) FILTER(WHERE '+ident(f)+' IS NULL)' for f in fields)} FROM {name}").fetchone()
            temporal = {}
            for field in ('anio', 'periodo', 'fecha_referencia', 'fecha_ultima_modificacion',
                          'fecha_publicacion', 'periodo_referencia'):
                if field in fields:
                    temporal[field] = query(c, f'SELECT {ident(field)} valor,count(*) registros FROM {name} GROUP BY 1 ORDER BY 1')
            profiles.append({'bloque':block, 'tabla':path.stem, 'filas':count, 'clave':key,
                             'nulos':dict(zip(fields,nulls)), 'periodos':temporal})
        expected_tables = {t for b, t in PRIMARY_KEYS if b == block}
        if not expected_tables.issubset(seen):
            raise ValueError(f'Faltan entidades previstas en {block}')
    # Comprobar las dependencias históricas por contenido, no por fecha local ni hash del helper actual.
    def lineage(value):
        if isinstance(value, dict):
            path = value.get('ruta', value.get('tabla'))
            if isinstance(path, str) and path.startswith('resultados/silver/') and path.endswith('.parquet'):
                if path not in outputs_by_path or any(value.get(k) != outputs_by_path[path][k] for k in ('bytes','sha256')):
                    raise ValueError(f'Dependencia Silver no coincide con la vigente: {path}')
            for child in value.values():
                lineage(child)
        elif isinstance(value, list):
            for child in value:
                lineage(child)
    for report in reports.values():
        lineage({k:v for k,v in report.items() if k not in ('salidas', 'calidad')})
        if 'manifiesto_bronze' in report:
            entry = report['manifiesto_bronze']
            files.append(checked(root, root / entry['ruta'], entry))
    # La capa i-DE hereda la tabla histórica y evidencia posterior: no recorrer DGT.
    if 'capacidad_demanda_espacial' in reports:
        capacity_report = reports['capacidad_demanda_espacial']
        for entry in capacity_report['entradas_verificadas']:
            relative = entry.get('ruta', entry.get('tabla'))
            files.append(checked(root, within(root, relative), entry))
        entry = capacity_report['metadatos_evidencias']
        path = within(root, entry['ruta'])
        files.append(checked(root, path, entry))
        accredited = verify_capacity_metadata(root, json.loads(path.read_text(encoding='utf-8')))
        for field in ('fecha_publicacion','periodo_referencia','crs_cv','sha256_original'):
            if capacity_report['metadatos_acreditados'][field] != accredited[field]:
                raise ValueError('La capa i-DE declara metadatos distintos de su evidencia')
        geo = table('capacidad_demanda_espacial','capacidad_demanda_geo')
        if c.execute(f'''SELECT count(*) FROM {geo} WHERE fecha_publicacion IS DISTINCT FROM ?::DATE
            OR periodo_referencia IS DISTINCT FROM ? OR crs_origen IS DISTINCT FROM ?''',
            [accredited['fecha_publicacion'],accredited['periodo_referencia'],accredited['crs_cv']]).fetchone()[0]:
            raise ValueError('Fechas o CRS de las filas i-DE distintos de su evidencia')
    return files, reports, profiles


def scalar(c, sql):
    return c.execute(sql).fetchone()[0]


def require_zero(c, sql, message):
    if scalar(c, sql):
        raise ValueError(message)


def integrity(c):
    m = table('base_territorial', 'municipios')
    r = table('base_territorial', 'recintos_municipales')
    if scalar(c, f'SELECT count(*) FROM {m}') != 542:
        raise ValueError('Referencia municipal incompleta')
    require_zero(c, f'SELECT count(*) FROM {m} ANTI JOIN {r} USING(codigo_municipio)', 'Municipio sin recinto')
    for name in ('parque_municipal','parque_detalle_observado','poblacion_municipal','renta_territorial'):
        source = table('demografia_parque', name)
        require_zero(c, f'SELECT count(*) FROM {source} s ANTI JOIN {m} m USING(codigo_municipio) WHERE s.codigo_municipio IS NOT NULL', 'Código municipal sin referencia')
        before = scalar(c, f'SELECT count(*) FROM {source}')
        after = scalar(c, f'SELECT count(*) FROM {source} LEFT JOIN {m} USING(codigo_municipio)')
        if before != after:
            raise ValueError('Multiplicación en relación estadística')
    hist = table('demografia_parque', 'renta_codigos_historicos')
    require_zero(c, f'SELECT count(*) FROM {hist} JOIN {m} USING(codigo_municipio)', 'Código histórico incorporado al ámbito vigente')
    i, p, k = [table('recarga', t) for t in ('recarga_instalaciones','recarga_puntos','recarga_conectores')]
    require_zero(c, f'SELECT count(*) FROM {p} ANTI JOIN {i} USING(instalacion_id)', 'Punto sin instalación')
    require_zero(c, f'SELECT count(*) FROM {k} ANTI JOIN {p} USING(instalacion_id,punto_id)', 'Conector sin punto')
    g=table('recarga_espacial','recarga_instalaciones_geo')
    require_zero(c, f'SELECT count(*) FROM {i} FULL JOIN {g} USING(instalacion_id) WHERE {i}.instalacion_id IS NULL OR {g}.instalacion_id IS NULL', 'Instalaciones espaciales sin correspondencia')
    fields = ','.join(ident(r[0]) for r in c.execute(f'DESCRIBE {i}').fetchall())
    require_zero(c, f'SELECT count(*) FROM ((SELECT {fields} FROM {i} EXCEPT ALL SELECT {fields} FROM {g}) UNION ALL (SELECT {fields} FROM {g} EXCEPT ALL SELECT {fields} FROM {i}))', 'Atributos de recarga cambiados')
    tr, tv = table('trafico_red','red_tramos'), table('trafico_red','red_tramo_vial')
    require_zero(c, f'SELECT count(*) FROM {tv} ANTI JOIN {tr} USING(provincia_origen,tramo_id)', 'Asociación viaria huérfana')
    o, pairs = table('poi_osm','poi_elementos'), table('poi_osm','poi_correspondencias')
    for side in ('punto','area'):
        require_zero(c, f'SELECT count(*) FROM {pairs} x ANTI JOIN {o} o ON x.origen_{side}=o.origen_id AND x.fid_{side}=o.fid_origen', 'Correspondencia OSM huérfana')
    capacity = capacity_integrity(c)
    return {'integridad_referencial':'correcta', 'conservacion_atributos_recarga':'correcta',
            'capacidad_demanda':capacity,
            'detalle_dgt_sin_municipio':scalar(c, f"SELECT count(*) FROM {table('demografia_parque','parque_detalle_observado')} WHERE codigo_municipio IS NULL"),
            'renta_historica_separada':scalar(c, f'SELECT count(*) FROM {hist}')}


def capacity_integrity(c):
    source = table('capacidad_demanda', 'capacidad_demanda')
    geo = table('capacidad_demanda_espacial', 'capacidad_demanda_geo')
    relation = table('capacidad_demanda_espacial', 'entidad_municipio')
    fields = [r[0] for r in c.execute(f'DESCRIBE {source}').fetchall()]
    original = ','.join(ident(k) for k in fields)
    restored = ','.join(ident(HISTORICAL.get(k,k))+' AS '+ident(k) for k in fields)
    require_zero(c, f'''SELECT count(*) FROM ((SELECT {original} FROM {source}
        EXCEPT ALL SELECT {restored} FROM {geo}) UNION ALL (SELECT {restored} FROM {geo}
        EXCEPT ALL SELECT {original} FROM {source}))''', 'Atributos i-DE originales cambiados')
    require_zero(c, f'''SELECT count(*) FROM ((SELECT punto_conexion_id,codigo_municipio FROM {relation}
        EXCEPT ALL SELECT punto_conexion_id,codigo_municipio_espacial FROM {geo} WHERE admitida_asignacion_municipal)
        UNION ALL (SELECT punto_conexion_id,codigo_municipio_espacial FROM {geo} WHERE admitida_asignacion_municipal
        EXCEPT ALL SELECT punto_conexion_id,codigo_municipio FROM {relation}))''', 'Relaciones i-DE admitidas incoherentes')
    require_zero(c, f'''SELECT count(*) FROM {geo} WHERE crs_origen IS DISTINCT FROM 'EPSG:25830' OR fecha_referencia IS NOT NULL
        OR estado_fecha IS DISTINCT FROM 'periodo_mensual_acreditado' OR estado_coordenadas IS DISTINCT FROM 'crs_acreditado'
        OR fecha_publicacion IS NULL OR periodo_referencia IS NULL
        OR periodo_referencia<>strftime(fecha_publicacion-INTERVAL 1 MONTH,'%Y-%m')
        OR (estado_geometria='admitida' AND (geometria IS NULL OR x_utm IS NULL OR y_utm IS NULL OR NOT ST_IsValid(geometria)
            OR ST_IsEmpty(geometria) OR ST_X(geometria)<>x_utm OR ST_Y(geometria)<>y_utm))''',
        'Metadatos o coordenadas i-DE incoherentes')
    require_zero(c, f'''SELECT count(*) FROM {geo} WHERE admitida_asignacion_municipal IS NULL
        OR admitida_asignacion_municipal IS DISTINCT FROM (estado_contraste_territorial='concordante')
        OR (admitida_asignacion_municipal AND (estado_geometria IS DISTINCT FROM 'admitida'
            OR numero_municipios_intersectados IS DISTINCT FROM 1
            OR codigo_municipio_espacial IS DISTINCT FROM codigo_municipio_declarado
            OR left(codigo_municipio_espacial,2) IS DISTINCT FROM codigo_provincia))''',
        'Admisión municipal i-DE incompatible con el contraste')
    for name in ('entidad_municipio', 'capacidad_municipios_candidatos'):
        current = table('capacidad_demanda_espacial', name)
        require_zero(c, f'SELECT count(*) FROM {current} ANTI JOIN {table("base_territorial","municipios")} USING(codigo_municipio)', 'Municipio i-DE sin referencia')
        require_zero(c, f'SELECT count(*) FROM {current} ANTI JOIN {geo} USING(punto_conexion_id)', 'Punto i-DE huérfano')
    return {'puntos':scalar(c,f'SELECT count(*) FROM {geo}'),
            'asignaciones_admitidas':scalar(c,f'SELECT count(*) FROM {relation}'),
            'pendientes':scalar(c,f'SELECT count(*) FROM {geo} WHERE NOT admitida_asignacion_municipal')}


def provider_evidence(root, path, c):
    """Decisiones explícitas acotadas, respaldadas por copias y recibos; sin fuzzy."""
    config_stamp = checked(root, path)
    config = json.loads(path.read_text(encoding='utf-8'))
    files, decisions = [config_stamp], {}
    for item in config['decisiones']:
        key = item['instalacion_id']
        if item['decision'] not in ('admitir', 'mantener_pendiente'):
            raise ValueError('Estado de decisión documental desconocido')
        if key in decisions:
            raise ValueError('Decisión documental duplicada')
        source = within(root, item['copia'])
        stamp = checked(root, source, item)
        receipt_path = source.with_suffix(source.suffix+'.adquisicion.json')
        files.extend([stamp,checked(root,receipt_path)])
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt['url_solicitada'] != item['url'] or any(receipt[k]!=stamp[k] for k in ('bytes','sha256')):
            raise ValueError('Evidencia documental distinta del recibo')
        kind = item.get('tipo_evidencia', 'ficha_jsonld')
        geo = None
        if kind == 'ficha_jsonld':
            scripts = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',source.read_text(encoding='utf-8'),re.S)
            structured = [json.loads(s) for s in scripts]
            nodes = [node for obj in structured for node in (obj.get('@graph',[obj]) if isinstance(obj,dict) else [])]
            expected_type = item.get('tipo_jsonld', 'Store')
            if expected_type not in ('Store', 'ParkingFacility', 'GasStation'):
                raise ValueError('Tipo de ficha no admitido')
            stores = [s for s in nodes if isinstance(s,dict) and s.get('@type')==expected_type and s.get('url')==item['url']]
            if len(stores)!=1:
                raise ValueError('Ficha de establecimiento no identificada de forma única')
            address=stores[0]['address']
            if normalized(address['streetAddress'])!=normalized(item['direccion_documentada']) or normalized(address['addressLocality'])!=normalized(item['municipio_documentado']):
                raise ValueError('La ficha no respalda la dirección y municipio revisados')
            geo = stores[0].get('geo')
        elif kind in ('portal_cartociudad', 'via_cartociudad', 'registro_operador_json'):
            records = json.loads(source.read_text(encoding='utf-8'))
            selector = item['selector']
            matches = [r for r in records if isinstance(r,dict) and r.get(selector['campo'])==selector['valor']]
            if len(matches)!=1 or not item['campos_documentados']:
                raise ValueError('Registro documental no identificado de forma única')
            record = matches[0]
            if any(record.get(k)!=v for k,v in item['campos_documentados'].items()):
                raise ValueError('El registro no respalda los campos documentados')
            if kind in ('portal_cartociudad', 'via_cartociudad'):
                # Solo direcciones postales: los POI de recarga de CartoCiudad derivan de MITECO.
                params=parse_qs(urlparse(item['url']).query)
                if (params.get('cod_postal_filter')!=[item['codigo_postal_origen']] or
                        any(k in params for k in ('municipio_filter','poblacion_filter','lon','lat')) or
                        record.get('muniCode')!=item['codigo_municipio'] or record.get('state')!=0):
                    raise ValueError('Consulta postal incompatible con la revisión')
                if kind == 'portal_cartociudad':
                    if (record.get('type')!='portal' or record.get('postalCode')!=item['codigo_postal_origen'] or
                            record.get('portalNumber')!=item['portal_documentado']):
                        raise ValueError('Portal oficial incompatible con la revisión')
                    geo={'longitude':record['lng'],'latitude':record['lat']}
                elif (record.get('type')!='callejero' or
                        {r.get('muniCode') for r in records}!={item['codigo_municipio']} or
                        any(r.get('type')!='callejero' for r in records)):
                    raise ValueError('Vial ambiguo o no admitido')
                # Un vial acredita la referencia municipal de la calle, no un portal ni el cargador.
            else:
                if (record.get('direccion')!=item['direccion_documentada'] or
                        record.get('ciudad')!=item['municipio_documentado']):
                    raise ValueError('Registro del operador sin dirección/localidad concordante')
                geo={'longitude':record['lng'],'latitude':record['lat']}
        elif kind == 'texto_primario_revisado':
            # Extractos de una página primaria revisados explícitamente, nunca búsquedas fuzzy.
            content=source.read_text(encoding='utf-8')
            content=re.sub(r'<(script|style)\b[^>]*>.*?</\1>', ' ', content, flags=re.S|re.I)
            plain=normalized(unescape(re.sub(r'<[^>]*>', ' ', content)))
            fragments=item['fragmentos_documentados']
            if (len(fragments)<3 or any(not normalized(v) or normalized(v) not in plain for v in fragments) or
                    normalized(item['municipio_documentado']) not in plain):
                raise ValueError('El texto primario no respalda la revisión explícita')
        elif kind in ('publicacion_primaria_no_concluyente', 'revision_visual_y_fuente_primaria'):
            scripts=re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',source.read_text(encoding='utf-8'),re.S)
            nodes=[json.loads(s) for s in scripts]
            matches=[n for n in nodes if isinstance(n,dict) and n.get('@type')=='SocialMediaPosting' and n.get('@id')==item['url']]
            if ((kind=='publicacion_primaria_no_concluyente' and item['decision']!='mantener_pendiente') or len(matches)!=1 or
                    matches[0].get('author',{}).get('name')!=item['autor_documentado'] or
                    any(normalized(v) not in normalized(matches[0].get('articleBody','')) for v in item['fragmentos_documentados'])):
                raise ValueError('Publicación no concluyente no identificada o admisión indebida')
            if kind=='revision_visual_y_fuente_primaria':
                # La identificación visual es una revisión explícita, no reconocimiento automático.
                entry=item['revision_visual']
                review_path=within(root,entry['ruta'])
                files.append(checked(root,review_path,entry))
                review=json.loads(review_path.read_text(encoding='utf-8'))
                if (review.get('instalacion_id')!=key or review.get('codigo_municipio')!=item['codigo_municipio'] or
                        review.get('alcance')!='municipio_emplazamiento' or not review.get('motivo') or
                        not review.get('url_visual') or not review.get('evidencias')):
                    raise ValueError('Revisión visual incompleta o para otra instalación/municipio')
                for evidence in review['evidencias']:
                    files.append(checked(root,within(root,evidence['ruta']),evidence))
        else:
            raise ValueError('Tipo de evidencia desconocido')
        rows=c.execute(f'''SELECT nombre_instalacion,direccion,codigo_municipio_espacial,
            codigo_municipio_declarado,numero_municipios_intersectados,estado_geometria,
            codigo_provincia_declarada FROM {table('recarga_espacial','recarga_instalaciones_geo')}
            WHERE instalacion_id=?''',[key]).fetchall()
        if len(rows)!=1 or list(rows[0][:2])!=item['atributos_esperados']:
            raise ValueError('La instalación revisada ha cambiado')
        row=rows[0]
        if (row[2]!=item['codigo_municipio'] or row[2]==row[3] or row[4]!=1 or
                row[5]!='admitida' or row[6]!=row[2][:2]):
            raise ValueError('Decisión incompatible con el contraste espacial')
        if kind in ('portal_cartociudad', 'via_cartociudad'):
            postal=c.execute(f"SELECT codigo_postal FROM {table('recarga_espacial','recarga_instalaciones_geo')} WHERE instalacion_id=?",[key]).fetchone()[0]
            if postal!=item['codigo_postal_origen']:
                raise ValueError('El código postal de origen ha cambiado')
        if geo is not None:
            candidates=c.execute(f'''SELECT codigo_municipio FROM {table('base_territorial','recintos_municipales')}
                WHERE ST_Intersects(geometria,ST_Transform(ST_Point(?,?),
                'EPSG:4326','EPSG:25830',always_xy:=true)) ORDER BY 1''',
                [float(geo['longitude']),float(geo['latitude'])]).fetchall()
            # Contraste diagnóstico de la ficha comercial: solo impide una admisión contradictoria.
            if item['decision']=='admitir' and candidates!=[(item['codigo_municipio'],)]:
                raise ValueError('La propia coordenada de la ficha contradice la admisión municipal')
        # La correspondencia exacta de establecimiento/dirección se revisó explícitamente en la decisión.
        # La coordenada del comercio no certifica el punto de recarga ni se usa como umbral de admisión.
        decisions[key] = item
    return decisions,files


def review_charging(c, decisions):
    g=table('recarga_espacial','recarga_instalaciones_geo')
    rows=c.execute(f'''SELECT instalacion_id,nombre_instalacion,direccion,municipio_nombre_origen,
        nombre_municipio_espacial,codigo_municipio_declarado,codigo_municipio_espacial,
        distancia_municipio_declarado_m FROM {g} WHERE NOT admitida_asignacion_municipal ORDER BY instalacion_id''').fetchall()
    c.execute('''CREATE TABLE revision_recarga(instalacion_id VARCHAR,nombre_instalacion VARCHAR,
        direccion VARCHAR,municipio_declarado VARCHAR,municipio_espacial VARCHAR,
        codigo_municipio_declarado VARCHAR,codigo_municipio_espacial VARCHAR,distancia_recinto_declarado_m DOUBLE,
        indicio_textual VARCHAR,estado_revision VARCHAR,codigo_municipio_validado VARCHAR,
        url_evidencia VARCHAR,motivo VARCHAR)''')
    for row in rows:
        key,name,address,declared,spatial,*_=row
        # Solo indicios: un nombre municipal puede ser una calle o parte de una marca.
        text=normalized(name+' '+address)
        def mentioned(label):
            return any(len(normalized(p))>=4 and (' '+normalized(p)+' ') in (' '+text+' ') for p in label.split('/'))
        a,b=mentioned(declared),mentioned(spatial)
        hint='ambos' if a and b else 'espacial' if b else 'declarado' if a else 'sin_mencion_literal'
        decision=decisions.get(key)
        admitted=decision is not None and decision['decision']=='admitir'
        c.execute('INSERT INTO revision_recarga VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', [*row,hint,
            'resuelta_documentalmente' if admitted else 'pendiente_evidencia_documental_no_concluyente' if decision else 'pendiente_contraste_externo',
            decision['codigo_municipio'] if admitted else None,decision['url'] if decision else None,
            decision['motivo'] if decision else 'Revisados nombre, dirección y contraste; indicios internos insuficientes para decidir qué atributo falla.'])
    if set(decisions)-{r[0] for r in rows}:
        raise ValueError('Decisión para instalación que no es un conflicto vigente')
    c.execute(f'''CREATE TABLE recarga_municipio_validado AS SELECT instalacion_id,
        codigo_municipio_espacial codigo_municipio,'interseccion_unica_y_nombre_oficial'::VARCHAR metodo,
        NULL::VARCHAR url_evidencia FROM {g} WHERE admitida_asignacion_municipal
        UNION ALL SELECT instalacion_id,codigo_municipio_validado,'revision_documental_establecimiento',
        url_evidencia FROM revision_recarga WHERE estado_revision='resuelta_documentalmente' ''')
    for key, decision in decisions.items():
        if decision['decision']=='admitir' and decision.get('tipo_evidencia') in ('portal_cartociudad','via_cartociudad','revision_visual_y_fuente_primaria'):
            c.execute('UPDATE recarga_municipio_validado SET metodo=? WHERE instalacion_id=?',
                ['revision_visual_y_documental' if decision['tipo_evidencia']=='revision_visual_y_fuente_primaria' else 'revision_cartografica_'+decision['tipo_evidencia'],key])
    for name in ('revision_recarga','recarga_municipio_validado'):
        check_key(c,name,OUTPUT_KEYS[name])
    controls={}
    for name in CHARGING_KEYS:
        source=table('recarga',name)
        total,admitted=c.execute(f'''SELECT count(*),count(v.instalacion_id) FROM {source} s
            LEFT JOIN recarga_municipio_validado v USING(instalacion_id)''').fetchone()
        if total!=scalar(c,f'SELECT count(*) FROM {source}'):
            raise ValueError('Multiplicación de entidades de recarga')
        controls[name]={'conservadas':total,'asignacion_municipal_admitida':admitted,'pendiente':total-admitted}
    return {'estados_revision':query(c,'SELECT estado_revision,count(*) instalaciones FROM revision_recarga GROUP BY 1 ORDER BY 1'),
            'metodos_admision':query(c,'SELECT metodo,count(*) instalaciones FROM recarga_municipio_validado GROUP BY 1 ORDER BY 1'),
            'indicios_textuales':query(c,'SELECT indicio_textual,count(*) instalaciones FROM revision_recarga GROUP BY 1 ORDER BY 1'),
            'entidades':controls}


def spatial_relations(c, source, key_fields, label, kind):
    """Materializa el cruce antes de filtrar atributos (limitación spatial 1.5.0).

    Los contactos de dimensión inferior se conservan sin asignación exclusiva.
    Medidas de intersección solo diagnósticas, sin reparto de IMD ni otros valores.
    """
    check_key(c,source,key_fields)
    key='to_json(list_value('+','.join('cast('+ident(k)+' AS VARCHAR)' for k in key_fields)+'))::VARCHAR'
    geom='ST_Force2D(geometria)'
    c.execute(f'''CREATE OR REPLACE TEMP TABLE espacial_entrada AS SELECT {key} clave_entidad,
        {geom} geometria,estado_geometria FROM {ident(source)}''')
    c.execute('''CREATE OR REPLACE TEMP TABLE espacial_admitida AS SELECT * FROM espacial_entrada
        WHERE estado_geometria='admitida' AND geometria IS NOT NULL''')
    require_zero(c, '''SELECT count(*) FROM espacial_admitida WHERE ST_IsEmpty(geometria)
        OR NOT ST_IsValid(geometria)''', 'Geometría marcada admitida que no es válida')
    c.execute(f'''CREATE OR REPLACE TEMP TABLE cruce_municipal AS SELECT p.clave_entidad,r.codigo_municipio,
        ST_Intersection(p.geometria,r.geometria) interseccion FROM espacial_admitida p
        JOIN {table('base_territorial','recintos_municipales')} r ON ST_Intersects(p.geometria,r.geometria)''')
    c.execute('''INSERT INTO relaciones_espaciales SELECT ?,clave_entidad,codigo_municipio,
        'interseccion'::VARCHAR,ST_Dimension(interseccion)::SMALLINT,
        CASE WHEN ST_Dimension(interseccion)=1 THEN ST_Length(interseccion) END,
        CASE WHEN ST_Dimension(interseccion)=2 THEN ST_Area(interseccion) END
        FROM cruce_municipal''',[label])
    c.execute('''INSERT INTO estado_relaciones_espaciales SELECT ?,p.clave_entidad,p.estado_geometria,
        coalesce(n,0)::BIGINT,CASE WHEN p.estado_geometria<>'admitida' OR p.geometria IS NULL THEN 'geometria_no_admitida'
        WHEN n IS NULL THEN 'sin_interseccion_cv' WHEN n=1 THEN 'interseccion_unica'
        ELSE 'interseccion_multiple' END FROM espacial_entrada p LEFT JOIN
        (SELECT clave_entidad,count(*) n FROM cruce_municipal GROUP BY 1) x USING(clave_entidad)''',[label])
    result = query(c,f'''SELECT estado_relacion,count(*) entidades,sum(numero_municipios) relaciones
        FROM estado_relaciones_espaciales WHERE tabla_entidad={sql_string(label)} GROUP BY 1 ORDER BY 1''')
    # Solo se necesitan las relaciones; liberar cada lote antes del siguiente.
    for name in ('cruce_municipal','espacial_admitida','espacial_entrada'):
        c.execute(f'DROP TABLE {ident(name)}')
    return result


def coverage(c):
    c.execute('''CREATE TABLE cobertura_estadistica(tabla_entidad VARCHAR,periodo VARCHAR,segmento VARCHAR,
        codigo_municipio VARCHAR,registros BIGINT,valores_informados BIGINT,valores_ausentes BIGINT)''')
    for name,period,segment,value in (
        ('parque_municipal','fecha_referencia',"'distintivo_0'",'vehiculos_distintivo_0'),
        ('poblacion_municipal','anio','sexo','poblacion'),
        ('renta_territorial','anio',"to_json(list_value(nivel_territorial,indicador))::VARCHAR",'valor_eur')):
        source=table('demografia_parque',name)
        c.execute(f'''INSERT INTO cobertura_estadistica SELECT ?,cast({period} AS VARCHAR),{segment},
            codigo_municipio,count(*),count({value}),count(*)-count({value}) FROM {source} GROUP BY 2,3,4''',[name])
    return query(c,'''SELECT tabla_entidad,periodo,segmento,count(*) municipios,sum(registros) registros,
        sum(valores_ausentes) valores_ausentes FROM cobertura_estadistica GROUP BY 1,2,3 ORDER BY 1,2,3''')


def write_outputs(c,target):
    target.mkdir(exist_ok=False)
    outputs=[]
    for name,keys in OUTPUT_KEYS.items():
        print(f'Exportando y verificando {name}...',flush=True)
        check_key(c,name,keys)
        path=target/(name+'.parquet')
        c.execute(f'COPY (SELECT * FROM {ident(name)} ORDER BY {",".join(ident(k) for k in keys)}) TO ? (FORMAT PARQUET,COMPRESSION ZSTD)',[str(path)])
        schema=[{'campo':r[0],'tipo':r[1]} for r in c.execute(f'DESCRIBE {ident(name)}').fetchall()]
        restored=[{'campo':r[0],'tipo':r[1]} for r in c.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(path)]).fetchall()]
        if schema!=restored:
            raise ValueError('Esquema de salida alterado')
        require_zero(c,f'''SELECT count(*) FROM ((SELECT * FROM {ident(name)} EXCEPT ALL SELECT * FROM read_parquet({sql_string(str(path))}))
            UNION ALL (SELECT * FROM read_parquet({sql_string(str(path))}) EXCEPT ALL SELECT * FROM {ident(name)}))''','Valores de salida alterados')
        outputs.append({'archivo':path.name,'filas':scalar(c,f'SELECT count(*) FROM {ident(name)}'),
                        'clave':keys,'esquema':schema,**fingerprint(path)})
    return outputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidencias-recarga',type=Path,required=True)
    args=parser.parse_args()
    directory=ROOT/'resultados/silver/validacion_conjunta'
    directory.mkdir(parents=True,exist_ok=True)
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=directory/run
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        with duckdb.connect(str(Path(temporary)/'trabajo.duckdb'),config={'threads':2,'memory_limit':'1GB',
            'storage_compatibility_version':'v1.5.0','temp_directory':str(Path(temporary)/'desborde'),
            'extension_directory':str(ROOT/'.venv/duckdb_extensions')}) as c:
            c.execute('LOAD spatial')
            c.execute("SET TimeZone='UTC'")
            print('Verificando salidas Silver, esquemas, claves y procedencia...',flush=True)
            files,reports,profiles=load_inputs(c,ROOT)
            quality=integrity(c)
            decisions,evidence_files=provider_evidence(ROOT,args.evidencias_recarga.resolve(),c)
            files.extend(evidence_files)
            quality['recarga']=review_charging(c,decisions)
            c.execute('''CREATE TABLE relaciones_espaciales(tabla_entidad VARCHAR,clave_entidad VARCHAR,
                codigo_municipio VARCHAR,metodo VARCHAR,dimension_interseccion SMALLINT,
                longitud_interseccion_m DOUBLE,superficie_interseccion_m2 DOUBLE)''')
            c.execute('''CREATE TABLE estado_relaciones_espaciales(tabla_entidad VARCHAR,clave_entidad VARCHAR,
                estado_geometria VARCHAR,numero_municipios BIGINT,estado_relacion VARCHAR)''')
            quality['relaciones_espaciales']={}
            for block,name,key,kind in SPATIAL:
                print(f'Contrastando territorio: {name}...',flush=True)
                source=block+'__'+name
                if name=='red_tramos':
                    # Acotar temporales: el cruce nacionalizado en un único lote terminaba las
                    # exportaciones pero provocaba una caída nativa al cerrar DuckDB en Windows.
                    # Se preservan las claves por copia y el mismo predicado espacial por provincia.
                    provinces=c.execute(f'SELECT DISTINCT provincia_origen FROM {ident(source)} ORDER BY 1').fetchall()
                    for (province,) in provinces:
                        print(f'  Lote viario provincial {province}...',flush=True)
                        c.execute(f'''CREATE OR REPLACE TEMP VIEW lote_red AS SELECT * FROM {ident(source)}
                            WHERE provincia_origen={sql_string(province)}''')
                        quality['relaciones_espaciales'][name]=spatial_relations(c,'lote_red',key,name,kind)
                    c.execute('DROP VIEW lote_red')
                else:
                    quality['relaciones_espaciales'][name]=spatial_relations(c,source,key,name,kind)
                if scalar(c,f'SELECT count(*) FROM {ident(source)}')!=scalar(c,f'''SELECT count(*) FROM
                    estado_relaciones_espaciales WHERE tabla_entidad={sql_string(name)}'''):
                    raise ValueError('Se pierden entidades entre lotes espaciales')
            check_key(c,'relaciones_espaciales',OUTPUT_KEYS['relaciones_espaciales'])
            check_key(c,'estado_relaciones_espaciales',OUTPUT_KEYS['estado_relaciones_espaciales'])
            require_zero(c,f'''SELECT count(*) FROM relaciones_espaciales ANTI JOIN
                {table('base_territorial','municipios')} USING(codigo_municipio)''','Relación con municipio desconocido')
            quality['cobertura_estadistica']=coverage(c)
            c.execute('''CREATE TABLE estado_fuentes(bloque VARCHAR,estado VARCHAR,
                integracion_municipal VARCHAR,limitacion VARCHAR)''')
            limitations={
                'base_territorial':('admitida','INE 2025 y recintos consultados 2026; sin acreditación de límites históricos.'),
                'demografia_parque':('admitida_por_codigo','Periodos separados; 12066 y PP000 aparte; DGT sin municipio conservado; Distintivo 0 aproximado.'),
                'recarga':('por_instalacion_validada','Sin suma de potencias como capacidad simultánea; fecha modificación no es adquisición.'),
                'recarga_espacial':('parcial_con_incidencias','Conflictos documentados pendientes; admisión documental no certifica posición fina.'),
                'trafico_red':('intersecciones_no_exclusivas','Cinco geometrías no admitidas; contactos/límites no reparten IMD/longitud; red no enrutable acreditada.'),
                'poi_osm':('intersecciones_no_exclusivas','Sin fusión de punto/área; objetos exteriores conservados; POI no acredita disponibilidad.'),
                'capacidad_demanda':('complementada_por_capa_espacial','Tabla histórica conservada; fecha/CRS posteriores en capacidad_demanda_espacial; capacidad no aditiva ni garantía de conexión.'),
                'capacidad_demanda_espacial':('por_punto_validado','Publicación y periodo mensual separados; corte exacto desconocido; solo relaciones concordantes admitidas; capacidad orientativa y no aditiva.'),
            }
            for block in BLOCKS:
                relation,limitation=limitations[block]
                c.execute('INSERT INTO estado_fuentes VALUES (?,?,?,?)',[block,'preparada_con_limitaciones',relation,limitation])
            print('Escribiendo y releyendo relaciones e informes de cierre...',flush=True)
            outputs=write_outputs(c,target)
            print('Consultando versión del entorno...',flush=True)
            environment={'python':sys.version.split()[0],'duckdb':duckdb.__version__,
                'spatial':scalar(c,"SELECT extension_version FROM duckdb_extensions() WHERE extension_name='spatial'"),
                'memoria_motor':'1GB','hilos':2}
            print('Entorno obtenido; cerrando conexión temporal...',flush=True)
        print('Conexión cerrada; eliminando temporales...',flush=True)
    print('Temporales eliminados; reverificando entradas...',flush=True)
    for file in files:
        checked(ROOT,ROOT/file['ruta'],file)
    report={'version_reglas':4,'ejecucion':run,'estado':'preparada_con_limitaciones',
        'alcance':'Cierre operativo Silver por entidades; integraciones pendientes explícitas, sin Gold.',
        'fecha_proceso_utc':datetime.now(timezone.utc).isoformat(),'entradas_verificadas':files,
        'perfiles':profiles,'calidad':quality,'salidas':outputs,'entorno':environment,
        'bronze':'Trazabilidad heredada y manifiestos verificados; no se recorre de nuevo el TXT nacional.',
        'codigo':[{'ruta':'src/'+name,**fingerprint(ROOT/'src'/name)} for name in
            ('validar_silver.py','auditar_fuentes.py','catalogar_bronze.py','georreferenciar_recarga.py',
             'preparar_demografia_parque.py','preparar_trafico_red.py','preparar_recarga.py','preparar_poi_osm.py',
             'georreferenciar_capacidad_demanda.py','verificar_metadatos_ide.py','preparar_capacidad_demanda.py')],
        'limitaciones':[v[1] for v in limitations.values()]+[
            'Intersecciones son relaciones múltiples, no asignación exclusiva ni reparto de indicadores.',
            'Longitudes/áreas diagnósticas 2D: contactos en límites y solapamientos impiden sumar sin una regla posterior.',
            'No se fija año común ni unidad Gold; no se imputa demanda de recarga ni se entrena un modelo.',
            'La evidencia primaria actual corrobora establecimiento o dirección municipal según el método; un vial no acredita portal, operación histórica ni datum de cada fila.']}
    (target/'informe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    pointer=directory/'actual.tmp'
    pointer.write_text(json.dumps({'ejecucion':run,'informe':f'{run}/informe.json'},indent=2)+'\n',encoding='utf-8')
    pointer.replace(directory/'actual.json')
    print(f'Silver preparada con limitaciones. Informe: {target.relative_to(ROOT).as_posix()}/informe.json',flush=True)


if __name__=='__main__':
    main()
