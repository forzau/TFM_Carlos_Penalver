"""Pruebas pequeñas de formatos y lectores; no construye las salidas Silver."""

import argparse
import json
import sqlite3
import struct
import tempfile
from contextlib import closing
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb

from auditar_fuentes import ROOT, ident


def gpkg_wkb(blob, expected_srs):
    """Extrae el WKB estándar sin perder el fid que se lee con SQLite."""
    if not isinstance(blob, bytes) or len(blob) < 8 or blob[:3] != b'GP\x00':
        raise ValueError('Cabecera GeoPackage no admitida')
    flags = blob[3]
    envelope = (flags >> 1) & 7
    if flags & 0xE0 or envelope > 4:
        raise ValueError('Geometría extendida o indicadores GeoPackage no admitidos')
    order = '<' if flags & 1 else '>'
    if struct.unpack(order + 'i', blob[4:8])[0] != expected_srs:
        raise ValueError('SRS de geometría distinto del declarado en su capa')
    offset = 8 + (0, 32, 48, 48, 64)[envelope]
    if len(blob) < offset + 5 or blob[offset] not in (0, 1):
        raise ValueError('Contenido WKB ausente o truncado')
    return blob[offset:]


def check_roundtrip(connection, directory):
    connection.execute("""
        CREATE TEMP TABLE prueba AS SELECT
            '03001'::VARCHAR codigo, 12345.67::DECIMAL(18,2) valor,
            NULL::BIGINT ausente, 0::BIGINT cero, DATE '2025-12-31' fecha,
            TIMESTAMPTZ '2026-10-15 12:00:00+00' instante,
            ST_Transform(ST_GeomFromText('POINT Z (0 0 100)'),
                'EPSG:4258', 'EPSG:25830', always_xy := true)
                ::GEOMETRY('EPSG:25830') geom
    """)
    path = str(directory / 'prueba.parquet')
    connection.execute('COPY prueba TO ? (FORMAT PARQUET, COMPRESSION ZSTD)', [path])
    row = connection.execute('SELECT codigo,valor,ausente,cero,fecha,epoch_us(instante) FROM read_parquet(?)', [path]).fetchone()
    assert row == ('03001', Decimal('12345.67'), None, 0, date(2025, 12, 31),
                   int(datetime(2026, 10, 15, 12, tzinfo=timezone.utc).timestamp() * 1000000)), row
    assert connection.execute('SELECT typeof(instante) FROM read_parquet(?)', [path]).fetchone()[0] == 'TIMESTAMP WITH TIME ZONE'
    geometry = connection.execute('SELECT ST_X(geom),ST_Y(geom),ST_Z(geom),typeof(geom) FROM read_parquet(?)', [path]).fetchone()
    # En el ecuador y a tres grados del meridiano central: control de ejes y unidades.
    assert abs(geometry[0] - 833978.5569) < 0.01 and abs(geometry[1]) < 0.01, geometry
    assert geometry[2:] == (100.0, "GEOMETRY('EPSG:25830')"), geometry
    back = connection.execute("SELECT ST_AsText(ST_Transform(geom,'EPSG:25830','EPSG:4258',always_xy:=true)) FROM read_parquet(?)", [path]).fetchone()[0]
    assert connection.execute("SELECT ST_Distance(ST_Force2D(ST_GeomFromText(?)),ST_Point(0,0)) < 1e-9", [back]).fetchone()[0]
    metadata = dict(connection.execute('SELECT decode(key),decode(value) FROM parquet_kv_metadata(?)', [path]).fetchall())
    geo = json.loads(metadata['geo'])
    assert geo['columns']['geom']['crs']['id'] == {'authority': 'EPSG', 'code': 25830}
    assert geo['columns']['geom']['encoding'] == 'WKB'
    connection.execute('DROP TABLE prueba')
    return {'tipos_y_valores': 'correctos', 'geoparquet': geo['version'],
            'crs': 'EPSG:25830', 'z_conservada': True, 'ejes_y_retorno': 'correctos'}


def check_gpkg(connection, path, layer, expected_crs):
    layers = connection.execute('SELECT layers FROM ST_Read_Meta(?)', [str(path)]).fetchone()[0]
    metadata = next(item for item in layers if item['name'] == layer)
    crs = metadata['geometry_fields'][0]['crs']
    resolved = crs['auth_name'] + ':' + crs['auth_code']
    if resolved != expected_crs:
        raise ValueError(f'CRS inesperado en {path.name}/{layer}: {resolved}')
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as source:
        column, srs = source.execute('SELECT column_name,srs_id FROM gpkg_geometry_columns WHERE table_name=?', [layer]).fetchone()
        fid, blob = source.execute(f'SELECT fid,{ident(column)} FROM {ident(layer)} WHERE {ident(column)} IS NOT NULL ORDER BY fid LIMIT 1').fetchone()
    wkb = gpkg_wkb(blob, srs)
    info = connection.execute('SELECT ST_GeometryType(g),ST_HasZ(g),ST_IsEmpty(g) FROM (SELECT ST_GeomFromWKB(?) g)', [wkb]).fetchone()
    assert type(fid) is int and not info[2], (layer, fid, info)
    # El tipo real puede ser múltiple aunque los metadatos declaren una línea simple.
    return {'archivo': path.relative_to(ROOT).as_posix(), 'capa': layer,
            'crs': resolved, 'srs_id_interno': srs, 'fid_conservado': True,
            'tipo_muestra': info[0], 'tiene_z_muestra': info[1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instalar-spatial', action='store_true', help='Descarga inicial desde el repositorio oficial; requiere Internet')
    args = parser.parse_args()
    output = ROOT / 'resultados/diseno_silver'
    output.mkdir(parents=True, exist_ok=True)
    cache = ROOT / '.venv/duckdb_extensions'
    cache.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(config={'extension_directory': str(cache), 'threads': 2, 'memory_limit': '1GB'}) as connection:
        if args.instalar_spatial:
            connection.execute("INSTALL spatial FROM 'https://extensions.duckdb.org'")
        connection.execute('LOAD spatial')
        connection.execute("SET TimeZone='UTC'")
        report = {'fecha_proceso_utc': datetime.now(timezone.utc).isoformat(),
                  'duckdb': connection.execute('SELECT version()').fetchone()[0],
                  'spatial': connection.execute("SELECT extension_version FROM duckdb_extensions() WHERE extension_name='spatial'").fetchone()[0]}
        with tempfile.TemporaryDirectory(dir=output) as temporary:
            report['formatos'] = check_roundtrip(connection, Path(temporary))
        inputs = [('Trafico.gpkg', 'Aforos2025', 'EPSG:25830')]
        inputs += [(f'{folder}/red_viaria.gpkg', 'rt_tramo_vial', 'EPSG:4258') for folder in
                   ('RT_ALICANTE_ALACANT_gpkg', 'RT_CASTELLON_CASTELLO_gpkg', 'RT_VALENCIA_gpkg')]
        inputs += [('ubicaciones_candidatasgpkg/valencia.gpkg', layer, 'OGC:CRS84') for layer in
                   ('gis_osm_pois_free', 'gis_osm_pois_a_free', 'gis_osm_traffic_free', 'gis_osm_traffic_a_free')]
        report['muestras_gpkg'] = [check_gpkg(connection, ROOT / 'Fuentes' / path, layer, crs) for path, layer, crs in inputs]
        geojson = ROOT / 'datos/bronze/ign_unidades_cv/2026-10-15/unidades_cv.geojson'
        types = connection.execute('SELECT ST_GeometryType(geom),typeof(geom) FROM ST_Read(?) LIMIT 1', [str(geojson)]).fetchone()
        assert types == ('MULTIPOLYGON', "GEOMETRY('EPSG:4326')"), types
        report['geojson_ign'] = {'tipo_muestra': types[0], 'crs_interpretado_por_lector': types[1]}
    (output / 'entorno.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Formatos, ejes, Z y muestras de ocho capas GeoPackage y un GeoJSON comprobados. Perfil: resultados/diseno_silver/entorno.json')


if __name__ == '__main__':
    main()
