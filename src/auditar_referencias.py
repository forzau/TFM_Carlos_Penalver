"""Contrasta códigos territoriales y la cobertura de las referencias Bronze, sin unir datos."""

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from xml.etree import ElementTree

from openpyxl import load_workbook

from catalogar_bronze import ROOT
from auditar_dgt_municipal import audit_workbook

PROVINCES = ('03', '12', '46')


def municipal_reference(path):
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
                if province not in PROVINCES:
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


def geometry_reference(path, hits_path, expected):
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
            if code[:2] not in PROVINCES or national_code[4:6] != code[:2]:
                raise ValueError('Código nacional IGN incoherente con su municipio')
            codes.append(code)
    if len(set(codes)) != len(codes):
        raise ValueError('Códigos municipales repetidos en la cartografía')
    if set(codes) != set(expected):
        raise ValueError(f'Cobertura IGN/INE distinta: faltan {sorted(set(expected) - set(codes))}; adicionales {sorted(set(codes) - set(expected))}')
    return {'unidades': len(features), 'recuento_proveedor': matched, 'niveles': dict(levels),
            'geometrias': dict(geometries), 'municipios': len(codes),
            'faltan': [], 'adicionales': [], 'validacion_topologica': False}


def inspect_income(path, expected):
    codes, focus = set(), {}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter=';')
        for row in reader:
            code = row['Municipios'][:5]
            if code[:2] in PROVINCES:
                codes.add(code)
            if code not in ('12066', '46902'):
                continue
            group = focus.setdefault(code, {'filas': 0, 'periodos': set(), 'valores': Counter(),
                                            'niveles': Counter(), 'indicadores': set()})
            group['filas'] += 1
            group['periodos'].add(row['Periodo'])
            group['indicadores'].add(row['Indicadores de renta media'])
            value = row['Total'].strip()
            group['valores']['ausentes_o_protegidos' if value in ('', '..', '.', '...') else 'informados'] += 1
            group['niveles']['seccion' if row['Secciones'] else 'distrito' if row['Distritos'] else 'municipio'] += 1
    for group in focus.values():
        group['periodos'] = sorted(group['periodos'])
        group['indicadores'] = sorted(group['indicadores'])
        group['valores'] = dict(group['valores'])
        group['niveles'] = dict(group['niveles'])
    return {'codigos_cv': len(codes), 'faltan': sorted(set(expected) - codes),
            'no_vigentes_en_referencia_2025': sorted(codes - set(expected)), 'gatova': focus}


def main():
    reference = ROOT / 'datos/bronze/ine_municipios/2025/25codmun.xlsx'
    directory = ROOT / 'datos/bronze/ign_unidades_cv/2026-10-15'
    codes, national_count = municipal_reference(reference)
    with (ROOT / 'Fuentes/Poblacion.csv').open(encoding='utf-8-sig', newline='') as stream:
        population = {row['Municipios'][:5] for row in csv.DictReader(stream, delimiter=';')
                      if row['Municipios'][:2] in PROVINCES}
    if population != set(codes):
        raise ValueError('Códigos de población distintos de la referencia municipal oficial')
    municipal = audit_workbook(ROOT / 'datos/bronze/dgt_municipal/2025/DatosMunicipalesGeneral_2025.xlsx', ROOT / 'Fuentes/Poblacion.csv')
    if municipal['faltan'] or municipal['adicionales'] or municipal['codigos_duplicados']:
        raise ValueError('Cobertura municipal DGT incoherente con la referencia')
    result = {'fecha_comprobacion_utc': datetime.now(timezone.utc).isoformat(),
              'ine': {'municipios_nacionales': national_count, 'municipios_cv': len(codes),
                      'por_provincia': dict(Counter(code[:2] for code in codes)),
                      '12066_vigente': '12066' in codes, '46902': codes.get('46902')},
              'ign': geometry_reference(directory / 'unidades_cv.geojson', directory / 'recuento.xml', codes),
              'poblacion_codigos_coinciden': True, 'dgt_municipios': municipal['municipios_cv'],
              'renta': inspect_income(ROOT / 'Fuentes/Renta.csv', codes)}
    output = ROOT / 'resultados/referencias_territoriales'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'perfil.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
