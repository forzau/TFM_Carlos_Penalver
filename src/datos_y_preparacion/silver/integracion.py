"""Silver: revisión documental, relaciones y versiones de recarga."""

from html import unescape
from urllib.parse import parse_qs, urlparse
import json
import re
import unicodedata

from src.datos_y_preparacion.comunes import (
    comprobar_archivo,
    comprobar_clave,
    consultar,
    exigir_cero,
    identificador_sql,
    integracion_scalar,
    texto_sql,
)
from src.datos_y_preparacion.silver.capacidad import CAPACIDAD_GEO_HISTORICAL
from src.datos_y_preparacion.silver.recarga import RECARGA_GEO_KEYS, RECARGA_KEYS


INTEGRACION_SPATIAL = (
    ('poi_osm', 'poi_elementos', ['origen_id', 'fid_origen'], 'POI'),
    ('trafico_red', 'aforos_tramo_anio', ['tramo_aforo_id', 'anio'], 'LINEA'),
    ('trafico_red', 'red_tramos', ['provincia_origen', 'tramo_id'], 'LINEA'),
    ('capacidad_demanda_espacial', 'capacidad_demanda_geo', ['punto_conexion_id'], 'PUNTO'),
)


INTEGRACION_OUTPUT_KEYS = {
    'revision_recarga': ['instalacion_id'],
    'recarga_municipio_validado': ['instalacion_id'],
    'relaciones_espaciales': ['tabla_entidad', 'clave_entidad', 'codigo_municipio'],
    'estado_relaciones_espaciales': ['tabla_entidad', 'clave_entidad'],
    'cobertura_estadistica': ['tabla_entidad', 'periodo', 'segmento', 'codigo_municipio'],
    'estado_fuentes': ['bloque'],
}


def integracion_table(block, name):
    return identificador_sql(block + '__' + name)


def integracion_normalized(value):
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in
        unicodedata.normalize('NFKD', (value or '').casefold()) if not unicodedata.combining(c)).split())


def integracion_within(directory, relative):
    path = (directory / relative).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError('Ruta fuera de la carpeta esperada')
    return path


def integracion_integrity(c):
    m = integracion_table('base_territorial', 'municipios')
    r = integracion_table('base_territorial', 'recintos_municipales')
    if integracion_scalar(c, f'SELECT count(*) FROM {m}') != 542:
        raise ValueError('Referencia municipal incompleta')
    exigir_cero(c, f'SELECT count(*) FROM {m} ANTI JOIN {r} USING(codigo_municipio)', 'Municipio sin recinto')
    for name in ('parque_municipal','parque_detalle_observado','poblacion_municipal','renta_territorial'):
        source = integracion_table('demografia_parque', name)
        exigir_cero(c, f'SELECT count(*) FROM {source} s ANTI JOIN {m} m USING(codigo_municipio) WHERE s.codigo_municipio IS NOT NULL', 'Código municipal sin referencia')
        before = integracion_scalar(c, f'SELECT count(*) FROM {source}')
        after = integracion_scalar(c, f'SELECT count(*) FROM {source} LEFT JOIN {m} USING(codigo_municipio)')
        if before != after:
            raise ValueError('Multiplicación en relación estadística')
    hist = integracion_table('demografia_parque', 'renta_codigos_historicos')
    exigir_cero(c, f'SELECT count(*) FROM {hist} JOIN {m} USING(codigo_municipio)', 'Código histórico incorporado al ámbito vigente')
    i, p, k = [integracion_table('recarga', t) for t in ('recarga_instalaciones','recarga_puntos','recarga_conectores')]
    exigir_cero(c, f'SELECT count(*) FROM {p} ANTI JOIN {i} USING(instalacion_id)', 'Punto sin instalación')
    exigir_cero(c, f'SELECT count(*) FROM {k} ANTI JOIN {p} USING(instalacion_id,punto_id)', 'Conector sin punto')
    g=integracion_table('recarga_espacial','recarga_instalaciones_geo')
    exigir_cero(c, f'SELECT count(*) FROM {i} FULL JOIN {g} USING(instalacion_id) WHERE {i}.instalacion_id IS NULL OR {g}.instalacion_id IS NULL', 'Instalaciones espaciales sin correspondencia')
    fields = ','.join(identificador_sql(r[0]) for r in c.execute(f'DESCRIBE {i}').fetchall())
    exigir_cero(c, f'SELECT count(*) FROM ((SELECT {fields} FROM {i} EXCEPT ALL SELECT {fields} FROM {g}) UNION ALL (SELECT {fields} FROM {g} EXCEPT ALL SELECT {fields} FROM {i}))', 'Atributos de recarga cambiados')
    tr, tv = integracion_table('trafico_red','red_tramos'), integracion_table('trafico_red','red_tramo_vial')
    exigir_cero(c, f'SELECT count(*) FROM {tv} ANTI JOIN {tr} USING(provincia_origen,tramo_id)', 'Asociación viaria huérfana')
    o, pairs = integracion_table('poi_osm','poi_elementos'), integracion_table('poi_osm','poi_correspondencias')
    for side in ('punto','area'):
        exigir_cero(c, f'SELECT count(*) FROM {pairs} x ANTI JOIN {o} o ON x.origen_{side}=o.origen_id AND x.fid_{side}=o.fid_origen', 'Correspondencia OSM huérfana')
    capacity = integracion_capacity_integrity(c)
    return {'integridad_referencial':'correcta', 'conservacion_atributos_recarga':'correcta',
            'capacidad_demanda':capacity,
            'detalle_dgt_sin_municipio':integracion_scalar(c, f"SELECT count(*) FROM {integracion_table('demografia_parque','parque_detalle_observado')} WHERE codigo_municipio IS NULL"),
            'renta_historica_separada':integracion_scalar(c, f'SELECT count(*) FROM {hist}')}


def integracion_capacity_integrity(c):
    source = integracion_table('capacidad_demanda', 'capacidad_demanda')
    geo = integracion_table('capacidad_demanda_espacial', 'capacidad_demanda_geo')
    relation = integracion_table('capacidad_demanda_espacial', 'entidad_municipio')
    fields = [r[0] for r in c.execute(f'DESCRIBE {source}').fetchall()]
    original = ','.join(identificador_sql(k) for k in fields)
    restored = ','.join(identificador_sql(CAPACIDAD_GEO_HISTORICAL.get(k,k))+' AS '+identificador_sql(k) for k in fields)
    exigir_cero(c, f'''SELECT count(*) FROM ((SELECT {original} FROM {source}
        EXCEPT ALL SELECT {restored} FROM {geo}) UNION ALL (SELECT {restored} FROM {geo}
        EXCEPT ALL SELECT {original} FROM {source}))''', 'Atributos i-DE originales cambiados')
    exigir_cero(c, f'''SELECT count(*) FROM ((SELECT punto_conexion_id,codigo_municipio FROM {relation}
        EXCEPT ALL SELECT punto_conexion_id,codigo_municipio_espacial FROM {geo} WHERE admitida_asignacion_municipal)
        UNION ALL (SELECT punto_conexion_id,codigo_municipio_espacial FROM {geo} WHERE admitida_asignacion_municipal
        EXCEPT ALL SELECT punto_conexion_id,codigo_municipio FROM {relation}))''', 'Relaciones i-DE admitidas incoherentes')
    exigir_cero(c, f'''SELECT count(*) FROM {geo} WHERE crs_origen IS DISTINCT FROM 'EPSG:25830' OR fecha_referencia IS NOT NULL
        OR estado_fecha IS DISTINCT FROM 'periodo_mensual_acreditado' OR estado_coordenadas IS DISTINCT FROM 'crs_acreditado'
        OR fecha_publicacion IS NULL OR periodo_referencia IS NULL
        OR periodo_referencia<>strftime(fecha_publicacion-INTERVAL 1 MONTH,'%Y-%m')
        OR (estado_geometria='admitida' AND (geometria IS NULL OR x_utm IS NULL OR y_utm IS NULL OR NOT ST_IsValid(geometria)
            OR ST_IsEmpty(geometria) OR ST_X(geometria)<>x_utm OR ST_Y(geometria)<>y_utm))''',
        'Metadatos o coordenadas i-DE incoherentes')
    exigir_cero(c, f'''SELECT count(*) FROM {geo} WHERE admitida_asignacion_municipal IS NULL
        OR admitida_asignacion_municipal IS DISTINCT FROM (estado_contraste_territorial='concordante')
        OR (admitida_asignacion_municipal AND (estado_geometria IS DISTINCT FROM 'admitida'
            OR numero_municipios_intersectados IS DISTINCT FROM 1
            OR codigo_municipio_espacial IS DISTINCT FROM codigo_municipio_declarado
            OR left(codigo_municipio_espacial,2) IS DISTINCT FROM codigo_provincia))''',
        'Admisión municipal i-DE incompatible con el contraste')
    for name in ('entidad_municipio', 'capacidad_municipios_candidatos'):
        current = integracion_table('capacidad_demanda_espacial', name)
        exigir_cero(c, f'SELECT count(*) FROM {current} ANTI JOIN {integracion_table("base_territorial","municipios")} USING(codigo_municipio)', 'Municipio i-DE sin referencia')
        exigir_cero(c, f'SELECT count(*) FROM {current} ANTI JOIN {geo} USING(punto_conexion_id)', 'Punto i-DE huérfano')
    return {'puntos':integracion_scalar(c,f'SELECT count(*) FROM {geo}'),
            'asignaciones_admitidas':integracion_scalar(c,f'SELECT count(*) FROM {relation}'),
            'pendientes':integracion_scalar(c,f'SELECT count(*) FROM {geo} WHERE NOT admitida_asignacion_municipal')}


def integracion_provider_evidence(root, path, c):
    """Decisiones explícitas acotadas, respaldadas por copias y recibos; sin fuzzy."""
    config_stamp = comprobar_archivo(root, path)
    config = json.loads(path.read_text(encoding='utf-8'))
    files, decisions = [config_stamp], {}
    for item in config['decisiones']:
        key = item['instalacion_id']
        if item['decision'] not in ('admitir', 'mantener_pendiente'):
            raise ValueError('Estado de decisión documental desconocido')
        if key in decisions:
            raise ValueError('Decisión documental duplicada')
        source = integracion_within(root, item['copia'])
        stamp = comprobar_archivo(root, source, item)
        receipt_path = source.with_suffix(source.suffix+'.adquisicion.json')
        files.extend([stamp,comprobar_archivo(root,receipt_path)])
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
            if integracion_normalized(address['streetAddress'])!=integracion_normalized(item['direccion_documentada']) or integracion_normalized(address['addressLocality'])!=integracion_normalized(item['municipio_documentado']):
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
            plain=integracion_normalized(unescape(re.sub(r'<[^>]*>', ' ', content)))
            fragments=item['fragmentos_documentados']
            if (len(fragments)<3 or any(not integracion_normalized(v) or integracion_normalized(v) not in plain for v in fragments) or
                    integracion_normalized(item['municipio_documentado']) not in plain):
                raise ValueError('El texto primario no respalda la revisión explícita')
        elif kind in ('publicacion_primaria_no_concluyente', 'revision_visual_y_fuente_primaria'):
            scripts=re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',source.read_text(encoding='utf-8'),re.S)
            nodes=[json.loads(s) for s in scripts]
            matches=[n for n in nodes if isinstance(n,dict) and n.get('@type')=='SocialMediaPosting' and n.get('@id')==item['url']]
            if ((kind=='publicacion_primaria_no_concluyente' and item['decision']!='mantener_pendiente') or len(matches)!=1 or
                    matches[0].get('author',{}).get('name')!=item['autor_documentado'] or
                    any(integracion_normalized(v) not in integracion_normalized(matches[0].get('articleBody','')) for v in item['fragmentos_documentados'])):
                raise ValueError('Publicación no concluyente no identificada o admisión indebida')
            if kind=='revision_visual_y_fuente_primaria':
                # La identificación visual es una revisión explícita, no reconocimiento automático.
                entry=item['revision_visual']
                review_path=integracion_within(root,entry['ruta'])
                files.append(comprobar_archivo(root,review_path,entry))
                review=json.loads(review_path.read_text(encoding='utf-8'))
                if (review.get('instalacion_id')!=key or review.get('codigo_municipio')!=item['codigo_municipio'] or
                        review.get('alcance')!='municipio_emplazamiento' or not review.get('motivo') or
                        not review.get('url_visual') or not review.get('evidencias')):
                    raise ValueError('Revisión visual incompleta o para otra instalación/municipio')
                for evidence in review['evidencias']:
                    files.append(comprobar_archivo(root,integracion_within(root,evidence['ruta']),evidence))
        else:
            raise ValueError('Tipo de evidencia desconocido')
        rows=c.execute(f'''SELECT nombre_instalacion,direccion,codigo_municipio_espacial,
            codigo_municipio_declarado,numero_municipios_intersectados,estado_geometria,
            codigo_provincia_declarada FROM {integracion_table('recarga_espacial','recarga_instalaciones_geo')}
            WHERE instalacion_id=?''',[key]).fetchall()
        if len(rows)!=1 or list(rows[0][:2])!=item['atributos_esperados']:
            raise ValueError('La instalación revisada ha cambiado')
        row=rows[0]
        if (row[2]!=item['codigo_municipio'] or row[2]==row[3] or row[4]!=1 or
                row[5]!='admitida' or row[6]!=row[2][:2]):
            raise ValueError('Decisión incompatible con el contraste espacial')
        if kind in ('portal_cartociudad', 'via_cartociudad'):
            postal=c.execute(f"SELECT codigo_postal FROM {integracion_table('recarga_espacial','recarga_instalaciones_geo')} WHERE instalacion_id=?",[key]).fetchone()[0]
            if postal!=item['codigo_postal_origen']:
                raise ValueError('El código postal de origen ha cambiado')
        if geo is not None:
            candidates=c.execute(f'''SELECT codigo_municipio FROM {integracion_table('base_territorial','recintos_municipales')}
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


def integracion_review_charging(c, decisions):
    g=integracion_table('recarga_espacial','recarga_instalaciones_geo')
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
        text=integracion_normalized(name+' '+address)
        def mentioned(label):
            return any(len(integracion_normalized(p))>=4 and (' '+integracion_normalized(p)+' ') in (' '+text+' ') for p in label.split('/'))
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
        comprobar_clave(c,name,INTEGRACION_OUTPUT_KEYS[name])
    controls={}
    for name in RECARGA_KEYS:
        source=integracion_table('recarga',name)
        total,admitted=c.execute(f'''SELECT count(*),count(v.instalacion_id) FROM {source} s
            LEFT JOIN recarga_municipio_validado v USING(instalacion_id)''').fetchone()
        if total!=integracion_scalar(c,f'SELECT count(*) FROM {source}'):
            raise ValueError('Multiplicación de entidades de recarga')
        controls[name]={'conservadas':total,'asignacion_municipal_admitida':admitted,'pendiente':total-admitted}
    return {'estados_revision':consultar(c,'SELECT estado_revision,count(*) instalaciones FROM revision_recarga GROUP BY 1 ORDER BY 1'),
            'metodos_admision':consultar(c,'SELECT metodo,count(*) instalaciones FROM recarga_municipio_validado GROUP BY 1 ORDER BY 1'),
            'indicios_textuales':consultar(c,'SELECT indicio_textual,count(*) instalaciones FROM revision_recarga GROUP BY 1 ORDER BY 1'),
            'entidades':controls}


def integracion_spatial_relations(c, source, key_fields, label, kind):
    """Materializa el cruce antes de filtrar atributos (limitación spatial 1.5.0).

    Los contactos de dimensión inferior se conservan sin asignación exclusiva.
    Medidas de intersección solo diagnósticas, sin reparto de IMD ni otros valores.
    """
    comprobar_clave(c,source,key_fields)
    key='to_json(list_value('+','.join('cast('+identificador_sql(k)+' AS VARCHAR)' for k in key_fields)+'))::VARCHAR'
    geom='ST_Force2D(geometria)'
    c.execute(f'''CREATE OR REPLACE TEMP TABLE espacial_entrada AS SELECT {key} clave_entidad,
        {geom} geometria,estado_geometria FROM {identificador_sql(source)}''')
    c.execute('''CREATE OR REPLACE TEMP TABLE espacial_admitida AS SELECT * FROM espacial_entrada
        WHERE estado_geometria='admitida' AND geometria IS NOT NULL''')
    exigir_cero(c, '''SELECT count(*) FROM espacial_admitida WHERE ST_IsEmpty(geometria)
        OR NOT ST_IsValid(geometria)''', 'Geometría marcada admitida que no es válida')
    c.execute(f'''CREATE OR REPLACE TEMP TABLE cruce_municipal AS SELECT p.clave_entidad,r.codigo_municipio,
        ST_Intersection(p.geometria,r.geometria) interseccion FROM espacial_admitida p
        JOIN {integracion_table('base_territorial','recintos_municipales')} r ON ST_Intersects(p.geometria,r.geometria)''')
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
    result = consultar(c,f'''SELECT estado_relacion,count(*) entidades,sum(numero_municipios) relaciones
        FROM estado_relaciones_espaciales WHERE tabla_entidad={texto_sql(label)} GROUP BY 1 ORDER BY 1''')
    # Solo se necesitan las relaciones; liberar cada lote antes del siguiente.
    for name in ('cruce_municipal','espacial_admitida','espacial_entrada'):
        c.execute(f'DROP TABLE {identificador_sql(name)}')
    return result


def integracion_coverage(c):
    c.execute('''CREATE TABLE cobertura_estadistica(tabla_entidad VARCHAR,periodo VARCHAR,segmento VARCHAR,
        codigo_municipio VARCHAR,registros BIGINT,valores_informados BIGINT,valores_ausentes BIGINT)''')
    for name,period,segment,value in (
        ('parque_municipal','fecha_referencia',"'distintivo_0'",'vehiculos_distintivo_0'),
        ('poblacion_municipal','anio','sexo','poblacion'),
        ('renta_territorial','anio',"to_json(list_value(nivel_territorial,indicador))::VARCHAR",'valor_eur')):
        source=integracion_table('demografia_parque',name)
        c.execute(f'''INSERT INTO cobertura_estadistica SELECT ?,cast({period} AS VARCHAR),{segment},
            codigo_municipio,count(*),count({value}),count(*)-count({value}) FROM {source} GROUP BY 2,3,4''',[name])
    return consultar(c,'''SELECT tabla_entidad,periodo,segmento,count(*) municipios,sum(registros) registros,
        sum(valores_ausentes) valores_ausentes FROM cobertura_estadistica GROUP BY 1,2,3 ORDER BY 1,2,3''')


RECARGA_VERSIONADA_KEYS = {**RECARGA_KEYS, 'incidencias': None, **RECARGA_GEO_KEYS, 'incidencias_espaciales': None,
        'revision_recarga': INTEGRACION_OUTPUT_KEYS['revision_recarga'],
        'recarga_municipio_validado': INTEGRACION_OUTPUT_KEYS['recarga_municipio_validado'],
        'recarga_ausentes': ['instalacion_id'],
        'recarga_ausentes_municipios_candidatos': ['instalacion_id', 'codigo_municipio']}


def recarga_versionada_inherit_geometry(c):
    fields = [row[0] for row in c.execute('DESCRIBE recarga_instalaciones').fetchall()]
    different = ' OR '.join(f'n.{identificador_sql(f)} IS DISTINCT FROM a.{identificador_sql(f)}' for f in fields)
    exigir_cero(c, f'''SELECT count(*) FROM recarga_instalaciones n
        LEFT JOIN geometria_anterior a USING(instalacion_id)
        WHERE a.instalacion_id IS NULL OR {different}''',
        'Identidad o coordenadas distintas: no se puede heredar geometría ni admisión')
    c.execute('''CREATE TABLE recarga_instalaciones_geo AS SELECT a.*
        FROM geometria_anterior a JOIN recarga_instalaciones n USING(instalacion_id)''')
    # Se repite la relación espacial para detectar cambios de recintos o candidatos.
    c.execute('''CREATE TABLE recarga_municipios_candidatos AS
        SELECT p.instalacion_id,r.codigo_municipio FROM recarga_instalaciones_geo p
        JOIN recintos r ON ST_Intersects(p.geometria,r.geometria)''')
    exigir_cero(c, '''SELECT count(*) FROM (
        (SELECT * FROM recarga_municipios_candidatos EXCEPT ALL
         SELECT a.* FROM candidatos_anteriores a JOIN recarga_instalaciones n USING(instalacion_id))
        UNION ALL
        (SELECT a.* FROM candidatos_anteriores a JOIN recarga_instalaciones n USING(instalacion_id)
         EXCEPT ALL SELECT * FROM recarga_municipios_candidatos))''',
        'Los municipios intersectados difieren del contraste histórico')
    exigir_cero(c, '''SELECT count(*) FROM recarga_instalaciones_geo WHERE
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


def recarga_versionada_preserve_absences(c):
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
        comprobar_clave(c, name, RECARGA_VERSIONADA_KEYS[name])
    exigir_cero(c, '''SELECT count(*) FROM recarga_ausentes h
        JOIN recarga_instalaciones n USING(instalacion_id)''', 'Ausente incluido en oferta principal')
    exigir_cero(c, '''SELECT count(*) FROM (
        (SELECT instalacion_id FROM geometria_anterior EXCEPT
         (SELECT instalacion_id FROM recarga_instalaciones UNION ALL SELECT instalacion_id FROM recarga_ausentes))
        UNION ALL
        ((SELECT instalacion_id FROM recarga_instalaciones UNION ALL SELECT instalacion_id FROM recarga_ausentes)
         EXCEPT SELECT instalacion_id FROM geometria_anterior))''',
        'No se conserva el universo de IDs históricos')


def crear_vistas_revision(c):
    for nombre in RECARGA_KEYS:
        c.execute(f'CREATE TEMP VIEW {identificador_sql("recarga__" + nombre)} AS SELECT * FROM {identificador_sql(nombre)}')
    c.execute('CREATE TEMP VIEW recarga_espacial__recarga_instalaciones_geo AS SELECT * FROM recarga_instalaciones_geo')
    c.execute('CREATE TEMP VIEW base_territorial__recintos_municipales AS SELECT * FROM recintos')


def integrar_relaciones(c):
    c.execute('''CREATE TABLE relaciones_espaciales(tabla_entidad VARCHAR,clave_entidad VARCHAR,
        codigo_municipio VARCHAR,metodo VARCHAR,dimension_interseccion SMALLINT,
        longitud_interseccion_m DOUBLE,superficie_interseccion_m2 DOUBLE)''')
    c.execute('''CREATE TABLE estado_relaciones_espaciales(tabla_entidad VARCHAR,clave_entidad VARCHAR,
        estado_geometria VARCHAR,numero_municipios BIGINT,estado_relacion VARCHAR)''')
    calidad = {}
    for bloque, nombre, clave, tipo in INTEGRACION_SPATIAL:
        fuente = bloque + '__' + nombre
        print(f'  Relaciones municipales de {nombre}...', flush=True)
        if nombre == 'red_tramos':
            # Lotes provinciales: acotan temporales y evitan la caída nativa observada al cerrar DuckDB.
            for (provincia,) in c.execute(f'SELECT DISTINCT provincia_origen FROM {identificador_sql(fuente)} ORDER BY 1').fetchall():
                c.execute(f'CREATE OR REPLACE TEMP VIEW lote_red AS SELECT * FROM {identificador_sql(fuente)} '
                          f'WHERE provincia_origen={texto_sql(provincia)}')
                integracion_spatial_relations(c, 'lote_red', clave, nombre, tipo)
            c.execute('DROP VIEW lote_red')
        else:
            integracion_spatial_relations(c, fuente, clave, nombre, tipo)
        if c.execute('SELECT count(*) FROM ' + identificador_sql(fuente)).fetchone()[0] != c.execute(
                'SELECT count(*) FROM estado_relaciones_espaciales WHERE tabla_entidad=?', [nombre]).fetchone()[0]:
            raise ValueError('Se pierden entidades entre lotes espaciales')
        calidad[nombre] = consultar(c, 'SELECT estado_relacion,count(*) entidades,sum(numero_municipios) relaciones '
            f'FROM estado_relaciones_espaciales WHERE tabla_entidad={texto_sql(nombre)} GROUP BY 1 ORDER BY 1')
    for nombre in ('relaciones_espaciales', 'estado_relaciones_espaciales'):
        comprobar_clave(c, nombre, INTEGRACION_OUTPUT_KEYS[nombre])
    exigir_cero(c, '''SELECT count(*) FROM relaciones_espaciales ANTI JOIN
        base_territorial__municipios USING(codigo_municipio)''', 'Relación con municipio desconocido')
    return calidad


def crear_estado_fuentes(c):
    c.execute('''CREATE TABLE estado_fuentes(bloque VARCHAR,estado VARCHAR,
        integracion_municipal VARCHAR,limitacion VARCHAR)''')
    limitaciones = {
        'base_territorial': ('admitida', 'INE 2025 y recintos consultados 2026; sin acreditación de límites históricos.'),
        'demografia_parque': ('admitida_por_codigo', 'Periodos separados; 12066 y PP000 aparte; DGT sin municipio conservado; Distintivo 0 aproximado.'),
        'recarga': ('por_instalacion_validada', 'Sin suma de potencias como capacidad simultánea; fecha modificación no es adquisición.'),
        'recarga_espacial': ('parcial_con_incidencias', 'Conflictos documentados pendientes; admisión documental no certifica posición fina.'),
        'trafico_red': ('intersecciones_no_exclusivas', 'Cinco geometrías no admitidas; contactos/límites no reparten IMD/longitud; red no enrutable acreditada.'),
        'poi_osm': ('intersecciones_no_exclusivas', 'Sin fusión de punto/área; objetos exteriores conservados; POI no acredita disponibilidad.'),
        'capacidad_demanda': ('complementada_por_capa_espacial', 'Tabla histórica conservada; fecha/CRS posteriores en capacidad_demanda_espacial; capacidad no aditiva ni garantía de conexión.'),
        'capacidad_demanda_espacial': ('por_punto_validado', 'Publicación y periodo mensual separados; corte exacto desconocido; solo relaciones concordantes admitidas; capacidad orientativa y no aditiva.'),
    }
    c.executemany('INSERT INTO estado_fuentes VALUES (?,?,?,?)',
                  [(b, 'preparada_con_limitaciones', *valores) for b, valores in limitaciones.items()])
