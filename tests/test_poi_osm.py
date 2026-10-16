import json
import sqlite3
import struct
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preparar_poi_osm import (ROOT, CRS84_WKT, prepare, read_osm, classify,
                             correspondences, validate, write_outputs, territory)
from catalogar_bronze import fingerprint


class OsmTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.c = duckdb.connect(str(self.root / 'trabajo.duckdb'), config={
            'extension_directory': str(ROOT / '.venv/duckdb_extensions'), 'storage_compatibility_version': 'v1.5.0'})
        self.addCleanup(self.c.close)
        try:
            self.c.execute('LOAD spatial')
        except duckdb.Error:
            self.skipTest('Instalar spatial oficial antes de las pruebas espaciales')
        self.c.execute('''CREATE TEMP TABLE ambito_cv AS SELECT
            ST_Transform(ST_GeomFromText('POLYGON ((-0.6 38.9,-0.4 38.9,-0.4 39.1,-0.6 39.1,-0.6 38.9))'),
            'OGC:CRS84','EPSG:25830',always_xy:=true)::GEOMETRY('EPSG:25830') geometria''')

    def package(self, points, areas):
        path = self.root / 'osm.gpkg'
        with closing(sqlite3.connect(path)) as c, c:
            c.execute('CREATE TABLE gpkg_geometry_columns (table_name TEXT,column_name TEXT,srs_id INTEGER,z INTEGER,m INTEGER)')
            c.execute('CREATE TABLE gpkg_spatial_ref_sys (srs_id INTEGER,organization TEXT,organization_coordsys_id INTEGER,definition TEXT)')
            c.execute('INSERT INTO gpkg_spatial_ref_sys VALUES (100000,\'NONE\',100000,?)', [CRS84_WKT])
            for layer, rows in [('gis_osm_traffic_free', points), ('gis_osm_traffic_a_free', areas)]:
                c.execute(f'CREATE TABLE {layer} (fid INTEGER PRIMARY KEY,osm_id TEXT,code INTEGER,fclass TEXT,name TEXT,geom BLOB)')
                c.execute('INSERT INTO gpkg_geometry_columns VALUES (?,\'geom\',100000,0,0)', [layer])
                for fid, osm, code, category, name, wkt in rows:
                    wkb = self.c.execute('SELECT ST_AsWKB(ST_GeomFromText(?))', [wkt]).fetchone()[0] if wkt else None
                    blob = b'GP\x00\x01' + struct.pack('<i', 100000) + wkb if wkb else None
                    c.execute(f'INSERT INTO {layer} VALUES (?,?,?,?,?,?)', [fid, osm, code, category, name, blob])
        return path

    def build(self, points=None, areas=None):
        path = self.package(points or [(1, '007', 5260, 'parking', 'Plaza', 'POINT (-0.5 39)'),
                                      (2, '007', 5260, 'parking', '', 'POINT (-0.49 39)')],
                            areas or [(1, '008', 5260, 'parking', ' plaza ',
                                       'POLYGON ((-0.51 38.99,-0.48 38.99,-0.48 39.01,-0.51 39.01,-0.51 38.99))')])
        counts = prepare(self.c, path, self.root, 'osm:hash', ['gis_osm_traffic_free', 'gis_osm_traffic_a_free'])
        classify(self.c)
        correspondences(self.c)
        return validate(self.c, counts)

    def test_repeated_ids_and_point_area_intersections_do_not_merge_elements(self):
        report = self.build()
        self.assertEqual(self.c.execute('SELECT count(*) FROM poi_elementos').fetchone()[0], 3)
        self.assertEqual(self.c.execute('SELECT count(*) FROM poi_correspondencias').fetchone()[0], 2)
        self.assertEqual(report['identificadores_repetidos_por_capa'][0]['filas_adicionales'], 1)
        self.assertEqual(self.c.execute('SELECT coincide_nombre_normalizado FROM poi_correspondencias ORDER BY fid_punto').fetchall(), [(True,), (False,)])
        self.assertEqual(self.c.execute("SELECT osm_id FROM poi_elementos WHERE representacion='punto' ORDER BY fid_origen").fetchall(), [('007',), ('007',)])

    def test_outside_and_unselected_objects_are_kept_and_not_admitted_for_revision(self):
        report = self.build(points=[(1, '1', 5260, 'parking', None, 'POINT (3 36)'),
                                   (2, '2', 5270, 'parking_bicycle', '', 'POINT (-0.5 39)')])
        self.assertEqual(report['filas_eliminadas'], 0)
        self.assertEqual(self.c.execute("SELECT estado_ambito,interes_para_revision FROM poi_elementos WHERE representacion='punto' ORDER BY fid_origen").fetchall(), [('fuera_cv', False), ('intersecta_cv', False)])
        self.assertGreater(self.c.execute("SELECT distancia_ambito_m FROM poi_elementos WHERE osm_id='1'").fetchone()[0], 100000)
        self.assertEqual(self.c.execute("SELECT nombre_origen FROM poi_elementos WHERE representacion='punto' ORDER BY fid_origen").fetchall(), [(None,), ('',)])

    def test_equal_id_far_from_polygon_is_only_an_indication(self):
        self.build(points=[(1, '008', 5260, 'parking', None, 'POINT (3 36)')])
        row = self.c.execute('SELECT punto_intersecta_area,coincide_id_publicado,coincide_nombre_normalizado,estado FROM poi_correspondencias').fetchone()
        self.assertEqual(row, (False, True, False, 'posible_correspondencia_sin_fusion'))

    def test_invalid_source_polygon_is_retained_as_wkb_without_projection(self):
        self.build(areas=[(1, '8', 5260, 'parking', 'Cruce',
                          'POLYGON ((-0.51 38.99,-0.48 39.01,-0.48 38.99,-0.51 39.01,-0.51 38.99))')])
        row = self.c.execute("SELECT estado_geometria,estado_ambito,geometria IS NULL,geometria_origen_no_admitida_wkb IS NOT NULL FROM poi_elementos WHERE representacion='area'").fetchone()
        self.assertEqual(row, ('origen_invalido', 'no_evaluable', True, True))
        self.assertEqual(self.c.execute('SELECT count(*) FROM incidencias').fetchone()[0], 1)

    def test_category_code_conflict_is_flagged_without_silent_selection(self):
        self.build(points=[(1, '7', 5270, 'parking', 'Discordante', 'POINT (-0.5 39)')])
        self.assertEqual(self.c.execute("SELECT estado_categoria,interes_para_revision FROM poi_elementos WHERE representacion='punto'").fetchone(), ('codigo_no_concordante', False))
        self.assertEqual(self.c.execute("SELECT count(*) FROM incidencias WHERE campo='categoria'").fetchone()[0], 1)

    def test_local_srs_identifier_does_not_establish_a_crs(self):
        path = self.package([(1, '1', 5260, 'parking', 'P', 'POINT (-0.5 39)')], [])
        with closing(sqlite3.connect(path)) as c, c:
            c.execute("UPDATE gpkg_spatial_ref_sys SET definition='EPSG:100000'")
        with self.assertRaisesRegex(ValueError, 'definición CRS84'):
            read_osm(self.c, path, 'gis_osm_traffic_free', self.root)

    def test_parquet_preserves_values_geometry_crs_and_previous_outputs(self):
        self.build()
        outputs = write_outputs(self.c, self.root / 'out', 'osm:hash')
        self.assertEqual([r['filas'] for r in outputs], [3, 2, 0])
        self.assertEqual(outputs[0]['geo']['columns']['geometria']['crs']['id']['code'], 25830)
        with self.assertRaises(FileExistsError):
            write_outputs(self.c, self.root / 'out', 'osm:hash')

    def test_territorial_geometry_hash_is_required(self):
        base = self.root / 'resultados/silver/base_territorial/test'
        base.mkdir(parents=True)
        self.c.execute("COPY (SELECT lpad(i::VARCHAR,5,'0') codigo_municipio FROM range(1,543) r(i)) TO ? (FORMAT PARQUET)", [str(base / 'municipios.parquet')])
        (base / 'recintos_municipales.parquet').write_bytes(b'alterado')
        report = {'estado': 'preparada', 'salidas': [
            {'archivo': 'municipios.parquet', **fingerprint(base / 'municipios.parquet')},
            {'archivo': 'recintos_municipales.parquet', 'bytes': 8, 'sha256': '0' * 64}]}
        (base / 'informe.json').write_text(json.dumps(report), encoding='utf-8')
        (base.parent / 'actual.json').write_text(json.dumps({'informe': 'test/informe.json'}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Recintos distintos'):
            territory(self.c, self.root)


if __name__ == '__main__':
    unittest.main()
