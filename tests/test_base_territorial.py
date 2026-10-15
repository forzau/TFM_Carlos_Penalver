import json
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preparar_base_territorial import INPUTS, ROOT, build_base, verify_inputs, write_tables
from catalogar_bronze import fingerprint


def polygon(left, right):
    return {'type': 'MultiPolygon', 'coordinates': [[[[left, 39], [right, 39],
                [right, 39.01], [left, 39.01], [left, 39]]]]}


def feature(code, level, geometry, name='Nombre IGN'):
    return {'type': 'Feature', 'id': 'AU_' + code,
            'properties': {'nationalCode': code,
                           'nationalLevel': {'href': 'https://inspire.ec.europa.eu/codelist/AdministrativeHierarchyLevel/' + level},
                           'name': {'GeographicalName': {'spelling': {'SpellingOfName': {'text': name}}}}},
            'geometry': geometry}


class TerritorialBaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.connection = duckdb.connect(config={'extension_directory': str(ROOT / '.venv/duckdb_extensions')})
        self.addCleanup(self.connection.close)
        try:
            self.connection.execute('LOAD spatial')
        except duckdb.Error:
            self.skipTest('Instalar la extensión oficial spatial antes de estas pruebas')
        self.codes = {'03001': 'Nombre INE 1', '03002': 'Nombre INE 2'}
        # Los niveles comparten vértices: la proyección no conserva paralelos rectos.
        parent = {'type': 'MultiPolygon', 'coordinates': [[[[-0.5, 39], [-0.49, 39],
                    [-0.48, 39], [-0.48, 39.01], [-0.49, 39.01], [-0.5, 39.01], [-0.5, 39]]]]}
        self.features = [feature('34100303001', '4thOrder', polygon(-0.5, -0.49)),
                         feature('34100303002', '4thOrder', polygon(-0.49, -0.48)),
                         feature('34100300000', '3rdOrder', parent),
                         feature('34100000000', '2ndOrder', parent)]

    def build(self):
        geojson = self.root / 'unidades.geojson'
        hits = self.root / 'recuento.xml'
        geojson.write_text(json.dumps({'type': 'FeatureCollection', 'features': self.features}), encoding='utf-8')
        hits.write_text(f'<FeatureCollection numberMatched="{len(self.features)}"/>', encoding='utf-8')
        return build_base(self.connection, self.codes, geojson, hits, 'origen_prueba')

    def test_outputs_keep_codes_names_lineage_and_crs_without_mixing_levels(self):
        profile = self.build()
        self.assertEqual(profile['municipios'], 2)
        self.assertEqual(profile['niveles'], {'4thOrder': 2, '3rdOrder': 1, '2ndOrder': 1})
        self.assertEqual(len(profile['nombres_distintos']), 2)
        self.assertEqual(profile['reparaciones'], 0)
        outputs = write_tables(self.connection, self.root / 'salidas')
        self.assertEqual(len(outputs), 2)
        rows = self.connection.execute('SELECT codigo_municipio,nombre_municipio FROM read_parquet(?) ORDER BY 1', [str(self.root / 'salidas/municipios.parquet')]).fetchall()
        self.assertEqual(rows, list(self.codes.items()))
        rows = self.connection.execute("SELECT codigo_municipio,origen_id,registro_origen,typeof(geometria) FROM read_parquet(?) ORDER BY 1", [str(self.root / 'salidas/recintos_municipales.parquet')]).fetchall()
        self.assertEqual(rows[0], ('03001', 'origen_prueba', 'AU_34100303001', "GEOMETRY('EPSG:25830')"))

    def test_invalid_geometry_stops_instead_of_repairing_or_losing_a_municipality(self):
        self.features[0]['geometry']['coordinates'] = [[[[-0.5, 39], [-0.49, 39.01],
            [-0.5, 39.01], [-0.49, 39], [-0.5, 39]]]]
        with self.assertRaisesRegex(ValueError, 'sin reparación automática'):
            self.build()

    def test_overlapping_municipalities_are_rejected(self):
        self.features[1]['geometry'] = polygon(-0.495, -0.48)
        with self.assertRaisesRegex(ValueError, 'aristas de cobertura'):
            self.build()

    def test_missing_municipal_code_is_rejected(self):
        self.features.pop(1)
        with self.assertRaisesRegex(ValueError, 'Cobertura IGN/INE distinta'):
            self.build()

    def test_wrong_parent_coverage_is_rejected(self):
        self.features[2]['geometry'] = polygon(-0.5, -0.47)
        with self.assertRaisesRegex(ValueError, 'niveles superiores'):
            self.build()

    def test_existing_output_is_never_overwritten(self):
        target = self.root / 'existente'
        target.mkdir()
        original = target / 'municipios.parquet'
        original.write_bytes(b'conservar')
        with self.assertRaises(FileExistsError):
            write_tables(self.connection, target)
        self.assertEqual(original.read_bytes(), b'conservar')


class TerritorialInputTests(unittest.TestCase):
    def test_only_registered_inputs_with_matching_hashes_are_admitted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {'version_manifiesto': 1, 'archivos': []}
            for relative, resource in INPUTS.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'original')
                manifest['archivos'].append({'ruta': relative, 'recurso_id': resource, **fingerprint(path)})
            self.assertEqual(len(verify_inputs(root, manifest)), 8)
            path.write_bytes(b'modified')
            with self.assertRaisesRegex(ValueError, 'Integridad Bronze'):
                verify_inputs(root, manifest)


if __name__ == '__main__':
    unittest.main()
