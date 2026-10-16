import sqlite3
import struct
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preparar_trafico_red import (ROOT, ROAD_FIELDS, TRAFFIC_FIELDS, prepare_road,
                                 prepare_traffic, read_layer, validate, write_outputs)


class TrafficRoadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.c = duckdb.connect(str(self.root / 'trabajo.duckdb'), config={
            'extension_directory': str(ROOT / '.venv/duckdb_extensions'), 'storage_compatibility_version': 'v1.5.0'})
        self.addCleanup(self.c.close)
        try:
            self.c.execute('LOAD spatial')
        except duckdb.Error:
            self.skipTest('Instalar la extensión oficial spatial antes de estas pruebas')

    def package(self, name, srs, layers, fields):
        path = self.root / name
        with closing(sqlite3.connect(path)) as c, c:
            c.execute('CREATE TABLE gpkg_geometry_columns (table_name TEXT,column_name TEXT,srs_id INTEGER,m INTEGER)')
            c.execute('CREATE TABLE gpkg_spatial_ref_sys (srs_id INTEGER,organization TEXT,organization_coordsys_id INTEGER)')
            c.execute('INSERT INTO gpkg_spatial_ref_sys VALUES (?,\'EPSG\',?)', [srs, srs])
            for layer, rows in layers.items():
                c.execute(f'CREATE TABLE "{layer}" (fid INTEGER PRIMARY KEY,geom BLOB,' + ','.join('"'+f+'" TEXT' for f in fields) + ')')
                c.execute('INSERT INTO gpkg_geometry_columns VALUES (?,\'geom\',?,0)', [layer, srs])
                for fid, values, wkt in rows:
                    wkb = self.c.execute('SELECT ST_AsWKB(ST_GeomFromText(?))', [wkt]).fetchone()[0]
                    blob = b'GP\x00\x01' + struct.pack('<i', srs) + wkb
                    c.execute(f'INSERT INTO "{layer}" VALUES ('+','.join('?' for _ in range(len(fields)+2))+')', [fid, blob, *values])
        return path

    def traffic(self, imd='100', percent='19', kind='Est', years=(2024, 2025)):
        values = ['1', '010007', 'CV-10', 'Gva', 'Autovia', kind, '0+000', '0+700', '1+650', imd, percent, 'IMD: 100 18,6%']
        return self.package('traffic.gpkg', 25830,
            {f'Aforos{y}': [(7, values, 'MULTILINESTRING ((700000 4300000,700010 4300010))')] for y in years}, TRAFFIC_FIELDS)

    def road(self, rows=None, name='road.gpkg'):
        values = ['001', '010', '1', 'Troncal', 'CV-10', 'Nombre; con "comillas"\nsegunda línea', '1', 'Carretera']
        second = values.copy(); second[1] = '011'; second[5] = ''
        rows = rows or [(3, values, 'LINESTRING Z (-0.5 39 100,-0.49 39.01 200)'),
                        (8, second, 'LINESTRING Z (-0.5 39 100,-0.49 39.01 200)')]
        return self.package(name, 4258, {'rt_tramo_vial': rows}, ROAD_FIELDS)

    def build(self):
        prepare_traffic(self.c, self.traffic(), self.root, 'gva:hash', years=(2024, 2025))
        prepare_road(self.c, self.road(), '03', self.root, 'ign:hash')

    def test_split_associations_preserve_lineage_z_types_and_crs(self):
        self.build()
        result = validate(self.c)
        self.assertTrue(result['claves_y_relaciones_validas'])
        self.assertEqual(self.c.execute('SELECT count(*) FROM red_tramos').fetchone()[0], 1)
        self.assertEqual(self.c.execute('SELECT count(*) FROM red_tramo_vial').fetchone()[0], 2)
        self.assertEqual(self.c.execute('SELECT fid_origen,nombre_vial FROM red_tramo_vial ORDER BY fid_origen').fetchall(),
                         [(3, 'Nombre; con "comillas"\nsegunda línea'), (8, '')])
        self.assertEqual(self.c.execute('SELECT fid_referencia,ST_ZMin(geometria),ST_ZMax(geometria) FROM red_tramos').fetchone(), (3, 100.0, 200.0))
        self.assertEqual(self.c.execute('SELECT ST_Z(ST_PointN(geometria,1)),ST_Z(ST_PointN(geometria,2)) FROM red_tramos').fetchone(), (100.0, 200.0))
        outputs = write_outputs(self.c, self.root / 'out', {})
        self.assertEqual([o['filas'] for o in outputs], [2, 1, 2, 0])
        self.assertEqual(outputs[1]['geo']['columns']['geometria']['crs']['id']['code'], 25830)
        with self.assertRaises(FileExistsError):
            write_outputs(self.c, self.root / 'out', {})

    def test_zero_unknown_type_and_invalid_percentage_are_preserved_with_incidents(self):
        prepare_traffic(self.c, self.traffic('0', '101', 'F', years=(2025,)), self.root, 'gva:hash', years=(2025,))
        prepare_road(self.c, self.road(), '03', self.root, 'ign:hash')
        validate(self.c)
        self.assertEqual(self.c.execute('SELECT imd_vehiculos_dia,porcentaje_pesados,pesados_origen,tipo_medida_trafico FROM aforos_tramo_anio').fetchone(), (0, None, '101', 'F'))
        self.assertEqual(self.c.execute('SELECT count(*) FROM incidencias').fetchone()[0], 3)

    def test_excess_precision_is_not_rounded(self):
        prepare_traffic(self.c, self.traffic('12.345', '0', years=(2025,)), self.root, 'gva:hash', years=(2025,))
        self.assertEqual(self.c.execute('SELECT imd_vehiculos_dia,estado_imd,imd_origen FROM aforos_tramo_anio').fetchone(), (None, 'error_conversion', '12.345'))

    def test_conflicting_geometry_or_attributes_stop_before_selecting_a_parent(self):
        values = ['001', '010', '1', 'Troncal', 'CV-10', 'Nombre', '1', 'Carretera']
        other = values.copy(); other[1] = '011'
        path = self.road([(1, values, 'LINESTRING Z (-0.5 39 100,-0.49 39.01 200)'),
                          (2, other, 'LINESTRING Z (-0.5 39 100,-0.48 39.01 200)')])
        with self.assertRaisesRegex(ValueError, 'Clave repetida'):
            prepare_road(self.c, path, '03', self.root, 'ign:hash')

    def test_repeated_association_is_not_silently_removed(self):
        values = ['001', '010', '1', 'Troncal', 'CV-10', 'Nombre', '1', 'Carretera']
        path = self.road([(1, values, 'LINESTRING Z (-0.5 39 100,-0.49 39.01 200)'),
                          (2, values, 'LINESTRING Z (-0.5 39 100,-0.49 39.01 200)')])
        prepare_traffic(self.c, self.traffic(), self.root, 'gva:hash', years=(2024, 2025))
        prepare_road(self.c, path, '03', self.root, 'ign:hash')
        with self.assertRaisesRegex(ValueError, 'Clave repetida'):
            validate(self.c)

    def test_wrong_crs_is_rejected(self):
        path = self.road()
        with closing(sqlite3.connect(path)) as c, c:
            c.execute('UPDATE gpkg_spatial_ref_sys SET organization_coordsys_id=4326')
        with self.assertRaisesRegex(ValueError, 'Autoridad CRS'):
            read_layer(self.c, path, 'rt_tramo_vial', 4258, ROAD_FIELDS, self.root)

    def test_same_tramo_in_two_provinces_is_retained_and_reported(self):
        self.build()
        prepare_road(self.c, self.root / 'road.gpkg', '12', self.root, 'ign2:hash')
        quality = validate(self.c)
        self.assertEqual(quality['tramos_compartidos_entre_paquetes'], {'ids_compartidos': 1, 'con_wkb_distinto': 0})
        self.assertEqual(self.c.execute('SELECT count(*) FROM red_tramos').fetchone()[0], 2)

    def test_missing_parent_is_detected(self):
        self.build()
        self.c.execute('DELETE FROM red_tramos')
        with self.assertRaisesRegex(ValueError, 'Relación tramo-vial incompleta'):
            validate(self.c)

    def test_invalid_projected_geometry_is_kept_and_flagged(self):
        self.build()
        self.c.execute("UPDATE red_tramos SET geometria=ST_GeomFromText('LINESTRING Z (1 1 100,1 1 200)')::GEOMETRY('EPSG:25830')")
        validate(self.c)
        self.assertEqual(self.c.execute('SELECT count(*) FROM red_tramos').fetchone()[0], 1)
        self.assertNotEqual(self.c.execute('SELECT estado_geometria FROM red_tramos').fetchone()[0], 'admitida')
        self.assertEqual(self.c.execute("SELECT count(*) FROM incidencias WHERE tabla='red_tramos'").fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
