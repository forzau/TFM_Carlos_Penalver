"""Compara las dos copias MITECO conservadas, sin red ni sustitución de Silver."""

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

import duckdb

from catalogar_bronze import ROOT
from georreferenciar_recarga import checked
from preparar_recarga import (HEADERS, INSTALL, POINT, PROVINCES, SOURCE,
                              coordinate, export_rows, modified, parent, power)


NEW = 'resultados/revision_recarga/20261018_ampliacion/miteco_exportacion_actual.csv'
IDENTITY = ('nombre_instalacion', 'operador_id', 'nombre_operador',
            'provincia_nombre_origen', 'municipio_nombre_origen', 'direccion',
            'codigo_postal', 'latitud_origen', 'longitud_origen')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def snapshot(path):
    installs, points, rows, national = {}, {}, {}, Counter()
    national_ids, dates = set(), []
    quality, blanks = Counter(), Counter()
    for ordinal, row, differs in export_rows(path):
        key = tuple(row[i] for i in (14, 15, 19))
        if any(not value.strip() for value in key):
            raise ValueError(f'Clave incompleta: registro {ordinal}')
        national[key] += 1
        national_ids.add(key[0])
        if (row[0] == 'Comunitat Valenciana') != (row[1] in PROVINCES):
            raise ValueError(f'Comunidad/provincia incoherentes: registro {ordinal}')
        if row[0] != 'Comunitat Valenciana':
            continue
        if key in rows:
            raise ValueError(f'Clave de conector repetida en CV: {key}')
        rows[key] = tuple(row)
        parent(installs, key[0], tuple(row[i] for i in INSTALL.values()), 'instalación')
        parent(points, key[:2], tuple(row[i] for i in POINT.values()), 'punto')
        quality['textos_preservados_frente_csv_permisivo'] += differs
        for i, value in enumerate(row):
            blanks[HEADERS[i]] += not value.strip()
        date, date_state = modified(row[26])
        quality['fecha_' + date_state] += 1
        if date:
            dates.append(date.isoformat())
        quality['potencia_' + power(row[23])[1]] += 1
        for index, latitude in ((3, True), (4, False)):
            quality[HEADERS[index] + '_' + coordinate(row[index], latitude)[1]] += 1
    if not rows:
        raise ValueError('La copia no contiene recarga de Comunitat Valenciana')
    return {'instalaciones': installs, 'puntos': points, 'conectores': rows,
            'ids_nacionales': national_ids,
            'perfil': {'filas_nacionales': national.total(),
                       'claves_repetidas_nacionales': sum(n > 1 for n in national.values()),
                       'filas_cv': len(rows), 'instalaciones': len(installs),
                       'puntos': len(points), 'conectores': len(rows),
                       'provincias_filas': dict(Counter(r[1] for r in rows.values())),
                       'fecha_modificacion_min': min(dates) if dates else None,
                       'fecha_modificacion_max': max(dates) if dates else None,
                       'calidad': dict(quality), 'vacios_por_campo': dict(blanks)}}


def compare(old, new, fields):
    before, after = set(old), set(new)
    changes, counts = [], Counter()
    for key in sorted(before & after):
        differences = {field: {'original': a, 'adquirida_18_10': b}
                       for field, a, b in zip(fields, old[key], new[key]) if a != b}
        if differences:
            counts.update(differences.keys())
            changes.append({'clave': key, 'campos': differences})
    added, removed = sorted(after - before), sorted(before - after)
    summary = {'original': len(old), 'adquirida_18_10': len(new),
               'comunes': len(before & after), 'sin_cambios': len(before & after) - len(changes),
               'modificadas': len(changes), 'solo_original': len(removed),
               'solo_adquirida_18_10': len(added), 'cambios_por_campo': dict(counts)}
    assert summary['original'] == summary['comunes'] + len(removed)
    assert summary['adquirida_18_10'] == summary['comunes'] + len(added)
    return summary, {'solo_original': removed, 'solo_adquirida_18_10': added,
                     'modificadas': changes}


def impact(old, new, admitted, documentary):
    fields = list(INSTALL)
    result = []
    for key in sorted(old['instalaciones']):
        previous = dict(zip(fields, old['instalaciones'][key]))
        current = dict(zip(fields, new['instalaciones'].get(key, ())))
        changed = [f for f in IDENTITY if previous.get(f) != current.get(f)]
        if not current:
            state = ('fuera_cv_en_nueva' if key in new['ids_nacionales']
                     else 'ausente_exportacion_nacional')
        else:
            state = 'revisar_identidad_o_ubicacion' if changed else 'identidad_y_ubicacion_iguales'
        result.append({'instalacion_id': key, 'estado': state,
                       'campos_identidad_cambiados': changed,
                       'codigo_municipio_admitido_original': admitted.get(key),
                       'revision_documental_original': key in documentary})
    return result


def missing_matches(old, new):
    by_position, by_point = defaultdict(set), defaultdict(set)
    for key, values in new['instalaciones'].items():
        attributes = dict(zip(INSTALL, values))
        by_position[(attributes['latitud_origen'], attributes['longitud_origen'])].add(key)
    for install, point in new['puntos']:
        by_point[point].add(install)
    result = []
    for key in sorted(set(old['instalaciones']) - set(new['instalaciones'])):
        attributes = dict(zip(INSTALL, old['instalaciones'][key]))
        point_ids = {p for i, p in old['puntos'] if i == key}
        position = (attributes['latitud_origen'], attributes['longitud_origen'])
        matches = Counter(i for p in point_ids for i in by_point[p])
        result.append({'original': attributes, 'puntos_originales': len(point_ids),
                       'conectores_originales': sum(k[0] == key for k in old['conectores']),
                       'otras_instalaciones_misma_coordenada_literal': sorted(by_position[position]),
                       'puntos_id_compartidos_con_nueva': dict(matches)})
    return result


def main():
    stamps = []
    def record(path, expected=None):
        stamp = checked(ROOT, path, expected)
        stamps.append(stamp)
        return stamp

    charging = ROOT / 'resultados/silver/recarga'
    pointer = charging / 'actual.json'
    record(pointer)
    source_report_path = charging / read_json(pointer)['informe']
    record(source_report_path)
    source_report = read_json(source_report_path)
    expected_old = next(x for x in source_report['entradas_verificadas'] if x['ruta'] == SOURCE)
    old_path, new_path = ROOT / SOURCE, ROOT / NEW
    record(old_path, expected_old)
    receipt_path = new_path.with_suffix('.csv.adquisicion.json')
    record(receipt_path)
    receipt = read_json(receipt_path)
    record(new_path, receipt)
    old, new = snapshot(old_path), snapshot(new_path)
    for field in ('instalaciones', 'puntos', 'conectores'):
        output = next(x for x in source_report['salidas'] if x['archivo'] == 'recarga_' + field + '.parquet')
        if old['perfil'][field] != output['filas']:
            raise ValueError(f'Recuento original distinto de Silver: {field}')

    joint = ROOT / 'resultados/silver/validacion_conjunta'
    joint_pointer = joint / 'actual.json'
    record(joint_pointer)
    joint_report_path = joint / read_json(joint_pointer)['informe']
    record(joint_report_path)
    joint_report = read_json(joint_report_path)
    with duckdb.connect() as connection:
        tables = {}
        for name in ('revision_recarga', 'recarga_municipio_validado'):
            output = next(x for x in joint_report['salidas'] if x['archivo'] == name + '.parquet')
            path = joint_report_path.parent / output['archivo']
            record(path, output)
            tables[name] = connection.execute('SELECT * FROM read_parquet(?)', [str(path)]).fetchall()
        admitted = {row[0]: row[1] for row in tables['recarga_municipio_validado']}
        # Las 81 revisiones admitidas se identifican por su estado, sin releer fichas externas.
        documentary = {row[0] for row in tables['revision_recarga'] if row[9] == 'resuelta_documentalmente'}
    if len(admitted) != len(tables['recarga_municipio_validado']) or not set(admitted) <= set(old['instalaciones']):
        raise ValueError('Relaciones municipales duplicadas o ajenas a la copia original')

    summaries, details = {}, {}
    for name, fields in (('instalaciones', list(INSTALL)), ('puntos', list(POINT)),
                         ('conectores', HEADERS)):
        summaries[name], details[name] = compare(old[name], new[name], fields)
    affected = impact(old, new, admitted, documentary)
    for scope, selection in (('todas', affected),
                             ('admitidas', [x for x in affected if x['codigo_municipio_admitido_original']]),
                             ('documentales_admitidas', [x for x in affected if x['revision_documental_original']]),
                             ('pendientes', [x for x in affected if not x['codigo_municipio_admitido_original']])):
        summaries['impacto_' + scope] = dict(Counter(x['estado'] for x in selection))
    summaries['compatibilidad_municipal_sin_transferir'] = {
        name: {'con_admision_previa': sum((key if name == 'instalaciones' else key[0]) in admitted for key in new[name]),
               'sin_admision_previa': sum((key if name == 'instalaciones' else key[0]) not in admitted for key in new[name])}
        for name in ('instalaciones', 'puntos', 'conectores')}
    details['impacto_asignaciones'] = affected
    details['ausentes_detalle'] = missing_matches(old, new)
    details['conectores_nuevos_detalle'] = [dict(zip(HEADERS, new['conectores'][key]))
                                           for key in sorted(set(new['conectores']) - set(old['conectores']))]
    details['entradas_cv_presentes_antes_fuera'] = sorted(
        (set(new['instalaciones']) - set(old['instalaciones'])) & old['ids_nacionales'])
    # No reinterpretar una ausencia como cierre ni un ID nuevo como inauguración.
    for stamp in stamps:
        checked(ROOT, ROOT / stamp['ruta'], stamp)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = ROOT / 'resultados/comparacion_recarga' / run
    target.mkdir(parents=True, exist_ok=False)
    report = {'version_reglas': 1, 'ejecucion': run,
              'fecha_proceso_utc': datetime.now(timezone.utc).isoformat(),
              'ambito': 'Comunitat Valenciana; contraste nacional para ausencias',
              'adquisicion_nueva_utc': receipt['fecha_utc'],
              'nombre_exportacion_declarado': receipt['content_disposition'],
              'solicitud_nueva': {'metodo': receipt['metodo'], 'cuerpo': receipt['cuerpo']},
              'entradas_verificadas': stamps, 'original': old['perfil'],
              'adquirida_18_10': new['perfil'], 'comparacion': summaries,
              'limites': ['Comparación literal; cambio de texto no implica cambio físico.',
                         'Fecha de adquisición no acredita operación o medición simultánea.',
                         'Compatibilidad de identidad no equivale a revalidación documental.',
                         'Solicitud original desconocida; la nueva usa soloConsolidado=true.',
                         'No se sustituye Silver ni se transfieren asignaciones.']}
    for name, value in (('informe.json', report), ('diferencias.json', details)):
        (target / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    print('Informe:', target.relative_to(ROOT).as_posix() + '/informe.json')


if __name__ == '__main__':
    main()
