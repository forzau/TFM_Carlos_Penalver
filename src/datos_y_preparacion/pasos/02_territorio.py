"""Silver: referencia municipal INE y recintos IGN."""

from collections import Counter
from datetime import date
from openpyxl import load_workbook
from xml.etree import ElementTree
import json

from src.datos_y_preparacion.pasos.comunes import consultar


REFERENCIA_PROVINCES = ('03', '12', '46')


def referencia_municipal_reference(path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    codes = {}
    national_count = 0
    try:
        for sheet in workbook:
            rows = sheet.iter_rows(values_only=True)
            next(rows)
            next(rows)
            if tuple(next(rows)) != ('CPRO', 'CMUN', 'DC', 'NOMBRE'):
                raise ValueError(f'Esquema municipal INE inesperado: {sheet.title}')
            for province, municipality, check_digit, name in rows:
                if province is None and municipality is None:
                    continue
                # La edición oficial mezcla texto y un código numérico de tres cifras.
                if type(province) is int:
                    province = str(province)
                if type(municipality) is int:
                    municipality = str(municipality)
                if (not isinstance(province, str) or len(province) != 2 or not province.isdigit()
                        or not isinstance(municipality, str) or len(municipality) != 3 or not municipality.isdigit()):
                    raise ValueError('Códigos INE sin longitud completa')
                national_count += 1
                if province not in REFERENCIA_PROVINCES:
                    continue
                code = province + municipality
                if code in codes or municipality == '000' or not isinstance(name, str) or not name.strip():
                    raise ValueError(f'Municipio repetido o no válido: {code}')
                codes[code] = name
    finally:
        workbook.close()
    if not codes:
        raise ValueError('La referencia INE no contiene municipios valencianos')
    return codes, national_count


def referencia_geometry_reference(path, hits_path, expected):
    collection = json.loads(path.read_text(encoding='utf-8'))
    matched = int(ElementTree.parse(hits_path).getroot().attrib['numberMatched'])
    features = collection['features']
    if collection['type'] != 'FeatureCollection' or len(features) != matched:
        raise ValueError('Respuesta WFS incompleta respecto al recuento del proveedor')
    codes, levels, geometries = [], Counter(), Counter()
    for feature in features:
        properties = feature['properties']
        national_code = properties['nationalCode']
        if not isinstance(national_code, str) or len(national_code) != 11 or not national_code.isdigit() or not national_code.startswith('3410'):
            raise ValueError('Unidad fuera del ámbito territorial solicitado')
        level = properties['nationalLevel']['href'].rsplit('/', 1)[-1]
        levels[level] += 1
        geometry = feature['geometry']
        if not geometry or geometry['type'] not in ('Polygon', 'MultiPolygon') or not geometry['coordinates']:
            raise ValueError('Unidad sin geometría poligonal informada')
        geometries[geometry['type']] += 1
        if level == '4thOrder':
            code = national_code[-5:]
            if code[:2] not in REFERENCIA_PROVINCES or national_code[4:6] != code[:2]:
                raise ValueError('Código nacional IGN incoherente con su municipio')
            codes.append(code)
    if len(set(codes)) != len(codes):
        raise ValueError('Códigos municipales repetidos en la cartografía')
    if set(codes) != set(expected):
        raise ValueError(f'Cobertura IGN/INE distinta: faltan {sorted(set(expected) - set(codes))}; adicionales {sorted(set(codes) - set(expected))}')
    return {'unidades': len(features), 'recuento_proveedor': matched, 'niveles': dict(levels),
            'geometrias': dict(geometries), 'municipios': len(codes),
            'faltan': [], 'adicionales': [], 'validacion_topologica': False}


TERRITORIO_INE = 'datos/bronze/ine_municipios/2025/25codmun.xlsx'


TERRITORIO_IGN = 'datos/bronze/ign_unidades_cv/2026-10-15/unidades_cv.geojson'


TERRITORIO_HITS = 'datos/bronze/ign_unidades_cv/2026-10-15/recuento.xml'


def territorio_build_base(connection, codes, geojson, hits, origin_id):
    profile = referencia_geometry_reference(geojson, hits, codes)
    provinces = Counter(code[:2] for code in codes)
    expected_levels = {'2ndOrder': 1, '3rdOrder': len(provinces), '4thOrder': len(codes)}
    if profile['niveles'] != expected_levels:
        raise ValueError('Niveles administrativos inesperados en la respuesta IGN')
    connection.execute('CREATE TEMP TABLE municipios (codigo_municipio VARCHAR PRIMARY KEY, codigo_provincia VARCHAR, nombre_municipio VARCHAR, fecha_referencia DATE)')
    connection.executemany('INSERT INTO municipios VALUES (?,?,?,?)',
                           [(code, code[:2], name, date(2025, 1, 1)) for code, name in sorted(codes.items())])
    connection.execute("""
        CREATE TEMP TABLE unidades_ign AS SELECT id registro_origen,
            nationalCode codigo_nacional_ign,
            json_extract_string(nationalLevel,'$.href') nivel,
            json_extract_string(name,'$.GeographicalName.spelling.SpellingOfName.text') nombre_municipio_ign,
            geom geometria_origen
        FROM ST_Read(?)
    """, [str(geojson)])
    if connection.execute('SELECT count(*) FROM unidades_ign').fetchone()[0] != profile['unidades']:
        raise ValueError('El lector espacial no conserva el recuento Bronze')
    invalid = consultar(connection, """
        SELECT codigo_nacional_ign FROM unidades_ign
        WHERE geometria_origen IS NULL OR ST_IsEmpty(geometria_origen)
           OR NOT ST_IsValid(geometria_origen)
           OR ST_GeometryType(geometria_origen) NOT IN ('POLYGON','MULTIPOLYGON')
           OR ST_HasZ(geometria_origen) OR ST_HasM(geometria_origen)
           OR ST_XMin(geometria_origen) NOT BETWEEN -2 AND 1
           OR ST_XMax(geometria_origen) NOT BETWEEN -2 AND 1
           OR ST_YMin(geometria_origen) NOT BETWEEN 37 AND 42
           OR ST_YMax(geometria_origen) NOT BETWEEN 37 AND 42
    """)
    if invalid:
        raise ValueError(f'Geometrías IGN no admitidas, sin reparación automática: {invalid}')
    missing = connection.execute("""
        SELECT count(*) FROM unidades_ign WHERE registro_origen IS NULL
            OR trim(registro_origen)='' OR codigo_nacional_ign IS NULL
            OR nombre_municipio_ign IS NULL OR trim(nombre_municipio_ign)=''
    """).fetchone()[0]
    unique = connection.execute('SELECT count(DISTINCT registro_origen),count(DISTINCT codigo_nacional_ign) FROM unidades_ign').fetchone()
    if missing or unique != (profile['unidades'], profile['unidades']):
        raise ValueError('Identificadores o nombres IGN ausentes o repetidos')
    connection.execute("""
        ALTER TABLE unidades_ign ADD COLUMN geometria GEOMETRY('EPSG:25830')
    """)
    connection.execute("""
        UPDATE unidades_ign SET geometria=ST_Transform(geometria_origen,
            'OGC:CRS84','EPSG:25830',always_xy:=true)::GEOMETRY('EPSG:25830')
    """)
    bad = consultar(connection, """
        SELECT codigo_nacional_ign FROM unidades_ign WHERE geometria IS NULL
            OR NOT ST_IsValid(geometria) OR ST_IsEmpty(geometria)
            OR NOT isfinite(ST_Area(geometria)) OR ST_Area(geometria)<=0
    """)
    if bad:
        raise ValueError(f'Geometrías proyectadas no admitidas: {bad}')
    connection.execute("""
        CREATE TEMP TABLE recintos_municipales AS SELECT
            right(codigo_nacional_ign,5) codigo_municipio,
            codigo_nacional_ign,nombre_municipio_ign,geometria,
            ?::VARCHAR origen_id,registro_origen
        FROM unidades_ign WHERE ends_with(nivel,'/4thOrder')
    """, [origin_id])
    observed = connection.execute('SELECT codigo_municipio FROM recintos_municipales').fetchall()
    if len(observed) != len(codes) or {row[0] for row in observed} != set(codes):
        raise ValueError('Correspondencia entre municipios y recintos distinta de uno a uno')
    edges = connection.execute('SELECT ST_CoverageInvalidEdges(list(geometria)) IS NULL FROM recintos_municipales').fetchone()[0]
    if not edges:
        raise ValueError('Los recintos municipales tienen aristas de cobertura incoherentes')
    connection.execute('CREATE TEMP TABLE union_municipal AS SELECT ST_Union_Agg(geometria) geometria FROM recintos_municipales')
    area_sum = connection.execute('SELECT sum(ST_Area(geometria)) FROM recintos_municipales').fetchone()[0]
    area_union = connection.execute('SELECT ST_Area(geometria) FROM union_municipal').fetchone()[0]
    if abs(area_sum - area_union) > 1:
        raise ValueError('Área de solapamiento municipal superior a la tolerancia numérica de 1 m²')
    connection.execute("""
        CREATE TEMP TABLE uniones_provinciales AS SELECT substr(codigo_municipio,1,2) codigo_provincia,
            ST_Union_Agg(geometria) geometria FROM recintos_municipales GROUP BY 1
    """)
    coverage = consultar(connection, """
        SELECT 'comunidad' nivel,b.codigo_nacional_ign,
            ST_Area(ST_Difference(a.geometria,b.geometria)) fuera_del_padre_m2,
            ST_Area(ST_Difference(b.geometria,a.geometria)) no_cubierto_m2
        FROM union_municipal a,unidades_ign b WHERE ends_with(b.nivel,'/2ndOrder')
        UNION ALL
        SELECT 'provincia',b.codigo_nacional_ign,
            ST_Area(ST_Difference(a.geometria,b.geometria)),
            ST_Area(ST_Difference(b.geometria,a.geometria))
        FROM uniones_provinciales a JOIN unidades_ign b
          ON a.codigo_provincia=substr(b.codigo_nacional_ign,5,2)
        WHERE ends_with(b.nivel,'/3rdOrder') ORDER BY 1,2
    """)
    if len(coverage) != len(provinces) + 1 or any(row['fuera_del_padre_m2'] > 1 or row['no_cubierto_m2'] > 1 for row in coverage):
        raise ValueError(f'Cobertura municipal distinta de sus niveles superiores: {coverage}')
    differences = consultar(connection, """
        SELECT codigo_municipio,nombre_municipio,nombre_municipio_ign
        FROM municipios JOIN recintos_municipales USING(codigo_municipio)
        WHERE nombre_municipio<>nombre_municipio_ign ORDER BY codigo_municipio
    """)
    return {'unidades_bronze': profile['unidades'], 'niveles': profile['niveles'],
            'municipios': len(codes), 'por_provincia': dict(sorted(provinces.items())),
            'claves_y_correspondencia_uno_a_uno': True,
            'geometrias_validas_origen': len(codes), 'geometrias_validas_salida': len(codes),
            'geometrias_nulas': 0, 'geometrias_vacias': 0, 'reparaciones': 0,
            'aristas_cobertura_invalidas': False, 'tolerancia_aristas': 0,
            'area_suma_municipios_m2': area_sum, 'area_union_municipios_m2': area_union,
            'diferencia_suma_union_m2': area_sum - area_union,
            'tolerancia_numerica_areas_m2': 1, 'contraste_niveles_superiores': coverage,
            'nombres_distintos': differences}
