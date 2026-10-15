"""Construye y valida municipios INE y recintos IGN de Silver desde copias Bronze."""

import argparse
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

from auditar_fuentes import query
from auditar_referencias import municipal_reference, geometry_reference
from catalogar_bronze import ROOT, fingerprint, raw_path

INE = 'datos/bronze/ine_municipios/2025/25codmun.xlsx'
IGN = 'datos/bronze/ign_unidades_cv/2026-10-15/unidades_cv.geojson'
HITS = 'datos/bronze/ign_unidades_cv/2026-10-15/recuento.xml'
CAPABILITIES = 'datos/bronze/ign_unidades_cv/2026-10-15/capabilities.xml'
INPUTS = {path + suffix: resource for path, resource in
          [(INE, 'ine_municipios_2025'), (IGN, 'ign_unidades_cv'),
           (HITS, 'ign_unidades_cv'), (CAPABILITIES, 'ign_unidades_cv')]
          for suffix in ('', '.adquisicion.json')}


def verify_inputs(root, manifest):
    if manifest.get('version_manifiesto') != 1:
        raise ValueError('Versión de manifiesto Bronze no admitida')
    verified = []
    for relative, resource in INPUTS.items():
        records = [row for row in manifest['archivos'] if row['ruta'] == relative]
        if len(records) != 1 or records[0]['recurso_id'] != resource:
            raise ValueError(f'Entrada Bronze ausente o incoherente: {relative}')
        observed = fingerprint(raw_path(root, relative))
        if any(observed[key] != records[0][key] for key in ('bytes', 'sha256')):
            raise ValueError(f'Integridad Bronze no válida: {relative}')
        verified.append({'ruta': relative, 'recurso_id': resource, **observed})
    return verified


def build_base(connection, codes, geojson, hits, origin_id):
    profile = geometry_reference(geojson, hits, codes)
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
    invalid = query(connection, """
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
    bad = query(connection, """
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
    coverage = query(connection, """
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
    differences = query(connection, """
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


def write_tables(connection, directory):
    directory.mkdir(parents=True, exist_ok=False)
    outputs = []
    for table in ('municipios', 'recintos_municipales'):
        path = directory / f'{table}.parquet'
        connection.execute(f'COPY (SELECT * FROM {table} ORDER BY codigo_municipio) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)', [str(path)])
        columns = '*,NULL::BLOB geometria_wkb' if table == 'municipios' else '* EXCLUDE(geometria),ST_AsWKB(geometria) geometria_wkb'
        # Comparar también atributos y WKB: un recuento correcto no prueba conservación.
        changed = connection.execute(f"""
            SELECT count(*) FROM (
                (SELECT {columns} FROM {table} EXCEPT ALL SELECT {columns} FROM read_parquet(?))
                UNION ALL
                (SELECT {columns} FROM read_parquet(?) EXCEPT ALL SELECT {columns} FROM {table})
            )
        """, [str(path), str(path)]).fetchone()[0]
        if changed:
            raise ValueError(f'La escritura Parquet cambió valores de {table}')
        schema = connection.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(path)]).fetchall()
        if table == 'recintos_municipales':
            metadata = dict(connection.execute('SELECT decode(key),decode(value) FROM parquet_kv_metadata(?)', [str(path)]).fetchall())
            crs = json.loads(metadata['geo'])['columns']['geometria']['crs']['id']
            if crs != {'authority': 'EPSG', 'code': 25830}:
                raise ValueError('GeoParquet no conserva el CRS proyectado')
        outputs.append({'archivo': path.name, **fingerprint(path),
                        'esquema': [{'campo': row[0], 'tipo': row[1]} for row in schema]})
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifiesto-bronze', type=Path, required=True, help='Manifiesto Bronze contra el que verificar solo las ocho entradas territoriales')
    args = parser.parse_args()
    manifest_path = args.manifiesto_bronze.resolve()
    manifest_relative = manifest_path.relative_to(ROOT.resolve()).as_posix()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest_stamp = fingerprint(manifest_path)
    inputs = verify_inputs(ROOT, manifest)
    codes, national_count = municipal_reference(ROOT / INE)
    if len(codes) != 542 or Counter(code[:2] for code in codes) != {'03': 141, '12': 135, '46': 266}:
        raise ValueError('La referencia no coincide con los 542 municipios previstos')
    origin = 'ign_unidades_cv:' + next(row['sha256'] for row in inputs if row['ruta'] == IGN)
    directory = ROOT / 'resultados/silver/base_territorial'
    directory.mkdir(parents=True, exist_ok=True)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = directory / run
    with duckdb.connect(config={'extension_directory': str(ROOT / '.venv/duckdb_extensions'),
                               'threads': 2, 'memory_limit': '1GB',
                               'temp_directory': str(directory / 'temporales')}) as connection:
        connection.execute('LOAD spatial')
        profile = build_base(connection, codes, ROOT / IGN, ROOT / HITS, origin)
        outputs = write_tables(connection, target)
        runtime = {'duckdb': connection.execute('SELECT version()').fetchone()[0],
                   'spatial': connection.execute("SELECT extension_version FROM duckdb_extensions() WHERE extension_name='spatial'").fetchone()[0]}
    if verify_inputs(ROOT, manifest) != inputs or fingerprint(manifest_path) != manifest_stamp:
        raise RuntimeError('Las entradas cambiaron durante la preparación; no se valida la ejecución')
    resources = [resource for resource in manifest['catalogo']['recursos'] if resource['id'] in INPUTS.values()]
    report = {'version_reglas': 1, 'ejecucion': run, 'estado': 'preparada',
              'fecha_proceso_utc': datetime.now(timezone.utc).isoformat(),
              'manifiesto_bronze': {'ruta': manifest_relative, **manifest_stamp},
              'entradas_verificadas': inputs, 'recursos': resources,
              'origen_id_ign': origin, 'referencia_ine': '2025-01-01',
              'fecha_consulta_ign': '2026-10-15', 'edicion_historica_limites': None,
              'crs_entrada': 'OGC:CRS84', 'crs_salida': 'EPSG:25830', 'always_xy': True,
              'municipios_ine_nacionales': national_count, 'calidad': profile,
              'incidencias_geometricas': [], 'salidas': outputs, 'entorno': runtime,
              'codigo': [{'ruta': 'src/' + name, 'sha256': fingerprint(ROOT / 'src' / name)['sha256']}
                         for name in ('preparar_base_territorial.py', 'auditar_referencias.py',
                                      'auditar_fuentes.py', 'catalogar_bronze.py')],
              'limitaciones': ['Los recintos consultados en 2026 no acreditan límites históricos de 2025.',
                               'Las diferencias nominales se conservan; la correspondencia usa códigos.',
                               'La coherencia entre niveles de una misma fuente no acredita exactitud geodésica independiente.']}
    (target / 'informe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # El indicador solo cambia cuando las tablas y su informe están comprobados.
    pointer = directory / 'actual.tmp'
    pointer.write_text(json.dumps({'ejecucion': run, 'informe': f'{run}/informe.json'}, indent=2) + '\n', encoding='utf-8')
    pointer.replace(directory / 'actual.json')
    print(f'Fase 2 preparada: 542 municipios y recintos. Informe: {target.relative_to(ROOT).as_posix()}/informe.json')


if __name__ == '__main__':
    main()
