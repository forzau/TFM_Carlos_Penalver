import json
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from georreferenciar_recarga import (ROOT, ENDPOINT, RESOURCE, evidence, name_key,
                                     prepare, validate, write_outputs, checked)
from catalogar_bronze import fingerprint


class RecargaEspacialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.c = duckdb.connect(str(self.root / 'test.duckdb'), config={
            'extension_directory': str(ROOT / '.venv/duckdb_extensions'), 'storage_compatibility_version': 'v1.5.0'})
        self.addCleanup(self.c.close)
        try:
            self.c.execute('LOAD spatial')
        except duckdb.Error:
            self.skipTest('Instalar spatial oficial antes de las pruebas espaciales')
        self.c.execute('CREATE TABLE municipios(codigo_municipio VARCHAR,nombre_municipio VARCHAR)')
        self.c.execute("INSERT INTO municipios VALUES ('03001','Alpha/Alfa'),('03002','Beta'),('12001','Gamma')")
        self.c.execute('''CREATE TABLE recintos AS SELECT *,nombre_municipio nombre_municipio_ign,
            ST_Transform(ST_GeomFromText(wkt),'EPSG:4258','EPSG:25830',always_xy:=true)
                ::GEOMETRY('EPSG:25830') geometria FROM municipios JOIN (VALUES
            ('03001','POLYGON ((-1 38,0 38,0 40,-1 40,-1 38))'),
            ('03002','POLYGON ((0 38,1 38,1 40,0 40,0 38))'),
            ('12001','POLYGON ((1 38,2 38,2 40,1 40,1 38))')) w(codigo_municipio,wkt) USING(codigo_municipio)''')
        self.c.execute('''CREATE TABLE recarga_instalaciones(instalacion_id VARCHAR,
            provincia_nombre_origen VARCHAR,municipio_nombre_origen VARCHAR,latitud DOUBLE,longitud DOUBLE,
            codigo_postal VARCHAR,estado_coordenadas VARCHAR)''')
        self.c.execute('CREATE TABLE recarga_puntos(instalacion_id VARCHAR,punto_id VARCHAR)')
        self.c.execute('CREATE TABLE recarga_conectores(instalacion_id VARCHAR,punto_id VARCHAR,conector_id VARCHAR)')

    def build(self, rows):
        for number, (province, name, lat, lon) in enumerate(rows, 1):
            key = f'{number:03d}'
            self.c.execute('INSERT INTO recarga_instalaciones VALUES (?,?,?,?,?,?,?)',
                [key, province, name, lat, lon, '03001', 'rango_valido_datum_pendiente'])
            self.c.execute('INSERT INTO recarga_puntos VALUES (?,\'P1\'),(?,\'P2\')', [key, key])
            self.c.execute('INSERT INTO recarga_conectores VALUES (?,\'P1\',\'C1\'),(?,\'P1\',\'C2\'),(?,\'P2\',\'C1\')', [key, key, key])
        prepare(self.c, self.root)
        return validate(self.c)

    def test_xy_projection_names_and_multiplicity(self):
        quality = self.build([('Alicante/Alacant', ' álfa / ALPHA ', 39, -0.5)])
        row = self.c.execute('''SELECT codigo_municipio_espacial,codigo_municipio_declarado,
            admitida_asignacion_municipal,ST_X(geometria),ST_Y(geometria) FROM recarga_instalaciones_geo''').fetchone()
        self.assertEqual(row[:3], ('03001', '03001', True))
        self.assertTrue(700000 < row[3] < 750000 and 4300000 < row[4] < 4350000)
        self.assertLess(quality['error_vuelta_grados_max'], 1e-8)
        self.assertEqual(quality['entidades']['recarga_conectores'],
            {'originales': 3, 'tras_relacion': 3, 'con_asignacion_admitida': 3})
        self.assertEqual(name_key('Orxa, l´/Lorcha'), name_key("Orxa, l'/Lorcha"))
        self.assertNotEqual(name_key('Beta'), name_key('Betera'))

    def test_declared_municipality_conflict_is_not_silently_corrected(self):
        quality = self.build([('Alicante/Alacant', 'Beta', 39, -0.5)])
        row = self.c.execute('''SELECT municipio_nombre_origen,codigo_municipio_declarado,
            codigo_municipio_espacial,estado_contraste_territorial,admitida_asignacion_municipal,
            distancia_municipio_declarado_m FROM recarga_instalaciones_geo''').fetchone()
        self.assertEqual(row[:5], ('Beta', '03002', '03001', 'municipio_discrepante', False))
        self.assertGreater(row[5], 10000)
        self.assertEqual(quality['incidencias'], 1)
        self.assertEqual(self.c.execute('SELECT count(*) FROM recarga_municipios_candidatos').fetchone()[0], 1)
        self.assertEqual(self.c.execute('SELECT count(*) FROM entidad_municipio').fetchone()[0], 0)

    def test_shared_boundary_retains_both_candidates_without_forcing_assignment(self):
        self.build([('Alicante/Alacant', 'Beta', 38, 0)])
        self.assertEqual(self.c.execute('''SELECT numero_municipios_intersectados,codigo_municipio_espacial,
            estado_contraste_territorial,admitida_asignacion_municipal FROM recarga_instalaciones_geo''').fetchone(),
            (2, None, 'limite_ambiguo', False))
        self.assertEqual(self.c.execute('SELECT count(*) FROM recarga_municipios_candidatos').fetchone()[0], 2)

    def test_outside_missing_zero_and_invalid_coordinates_remain_in_the_layer(self):
        quality = self.build([('Alicante/Alacant', 'Beta', 39, 3),
            ('Alicante/Alacant', 'Beta', None, 0), ('Alicante/Alacant', 'Beta', 0, 0),
            ('Alicante/Alacant', 'Beta', 91, 0)])
        self.assertEqual(self.c.execute('SELECT count(*) FROM recarga_instalaciones_geo').fetchone()[0], 4)
        self.assertEqual(self.c.execute('SELECT count(*) FROM recarga_instalaciones_geo WHERE geometria IS NULL').fetchone()[0], 3)
        self.assertEqual(quality['incidencias'], 4)
        self.assertEqual(self.c.execute("SELECT estado_contraste_territorial FROM recarga_instalaciones_geo WHERE instalacion_id='001'").fetchone()[0], 'fuera_ambito')

    def test_province_conflict_and_unrecognized_name_are_not_admitted(self):
        self.build([('Alicante/Alacant', 'Gamma', 39, 1.5), ('Alicante/Alacant', 'Alffaa', 39, -0.5)])
        self.assertEqual(self.c.execute('SELECT estado_contraste_territorial FROM recarga_instalaciones_geo ORDER BY instalacion_id').fetchall(),
            [('provincia_discrepante',), ('nombre_no_resuelto',)])
        self.assertEqual(self.c.execute('SELECT count(*) FROM entidad_municipio').fetchone()[0], 0)

    def test_non_unique_official_label_is_not_chosen_arbitrarily(self):
        self.c.execute("UPDATE municipios SET nombre_municipio='Alpha/Alfa' WHERE codigo_municipio='03002'")
        self.build([('Alicante/Alacant', 'Alpha/Alfa', 39, -0.5)])
        self.assertEqual(self.c.execute('SELECT codigo_municipio_declarado,admitida_asignacion_municipal FROM recarga_instalaciones_geo').fetchone(), (None, False))

    def test_metadata_requires_resource_endpoint_crs_and_matching_receipt(self):
        path = self.root / 'catalogo.json'
        resource = {'id': RESOURCE, 'format': 'CSV', 'url': ENDPOINT,
                    'reference_system': 'http://www.opengis.net/def/crs/EPSG/0/4258'}
        def save(record):
            path.write_text(json.dumps({'success': True, 'result': {'resources': [record]}}), encoding='utf-8')
            path.with_suffix('.json.adquisicion.json').write_text(json.dumps({**fingerprint(path), 'url_solicitada': 'https://catalogo.datosabiertos.miteco.gob.es/catalogo/api/3/action/package_show'}), encoding='utf-8')
        save(resource)
        self.assertEqual(evidence(self.root, path)['crs_declarado'], 'EPSG:4258')
        for field, value in [('reference_system', 'EPSG:4326'), ('url', 'https://otro.example'), ('id', 'otro')]:
            save({**resource, field: value})
            with self.assertRaises(ValueError):
                evidence(self.root, path)
        save(resource)
        path.write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            evidence(self.root, path)
        with self.assertRaises(ValueError):
            checked(self.root, Path(__file__))

    def test_export_preserves_attributes_geometry_crs_and_previous_outputs(self):
        self.build([('Alicante/Alacant', 'Alpha/Alfa', 39, -0.5), ('Alicante/Alacant', 'Beta', 39, 3)])
        target = self.root / 'salida'
        outputs = write_outputs(self.c, target)
        self.assertEqual([r['filas'] for r in outputs], [2, 1, 1, 1])
        self.assertEqual(outputs[0]['geo']['columns']['geometria']['crs']['id']['code'], 25830)
        self.assertEqual(self.c.execute('SELECT codigo_postal FROM read_parquet(?) ORDER BY instalacion_id',
            [str(target / 'recarga_instalaciones_geo.parquet')]).fetchall(), [('03001',), ('03001',)])
        with self.assertRaises(FileExistsError):
            write_outputs(self.c, target)


if __name__ == '__main__':
    unittest.main()
