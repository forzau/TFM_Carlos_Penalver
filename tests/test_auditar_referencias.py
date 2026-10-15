import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from auditar_referencias import municipal_reference, geometry_reference, inspect_income


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_ine_text_codes_control_digit_not_part_of_municipality(self):
        book = Workbook()
        sheet = book.active
        for row in [('Referencia 2025',), ('Alicante',), ('CPRO', 'CMUN', 'DC', 'NOMBRE'), ('03', '001', '9', 'Adsubia'), ('03', 902, 1, 'Pilar de la Horadada')]:
            sheet.append(row)
        path = self.root / 'ine.xlsx'
        book.save(path)
        codes, total = municipal_reference(path)
        self.assertEqual(codes, {'03001': 'Adsubia', '03902': 'Pilar de la Horadada'})
        self.assertEqual(total, 2)
        sheet.append(('03', '001', '9', 'Adsubia'))
        book.save(path)
        with self.assertRaisesRegex(ValueError, 'repetido'):
            municipal_reference(path)
        book.close()

    def feature(self, code, level='4thOrder'):
        return {'properties': {'nationalCode': code, 'nationalLevel': {'href': 'https://example.org/' + level}},
                'geometry': {'type': 'Polygon', 'coordinates': [[[0, 38], [1, 38], [0, 39], [0, 38]]]}}

    def test_ign_incomplete_duplicate_and_extra_codes_fail(self):
        path, hits = self.root / 'ign.json', self.root / 'hits.xml'
        feature = self.feature('34100303001')
        valid = {'type': 'FeatureCollection', 'features': [feature]}
        path.write_text(json.dumps(valid))
        hits.write_text('<FeatureCollection numberMatched="1"/>')
        self.assertEqual(geometry_reference(path, hits, {'03001'})['municipios'], 1)
        hits.write_text('<FeatureCollection numberMatched="2"/>')
        with self.assertRaisesRegex(ValueError, 'incompleta'):
            geometry_reference(path, hits, {'03001'})
        valid['features'].append(feature)
        path.write_text(json.dumps(valid))
        with self.assertRaisesRegex(ValueError, 'repetidos'):
            geometry_reference(path, hits, {'03001'})
        hits.write_text('<FeatureCollection numberMatched="1"/>')
        path.write_text(json.dumps({'type': 'FeatureCollection', 'features': [feature]}))
        with self.assertRaisesRegex(ValueError, 'Cobertura'):
            geometry_reference(path, hits, {'03002'})

    def test_historical_income_code_is_reported_without_remapping_or_zero_fill(self):
        path = self.root / 'renta.csv'
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream, delimiter=';')
            writer.writerow(['Municipios', 'Distritos', 'Secciones', 'Indicadores de renta media', 'Periodo', 'Total'])
            writer.writerow(['12066 Gatova', '', '', 'Renta', '2023', '..'])
            writer.writerow(['46902 Gátova', '', '', 'Renta', '2023', '10.000'])
        before = path.read_bytes()
        profile = inspect_income(path, {'46902'})
        self.assertEqual(profile['no_vigentes_en_referencia_2025'], ['12066'])
        self.assertEqual(profile['gatova']['12066']['valores'], {'ausentes_o_protegidos': 1})
        self.assertEqual(profile['gatova']['46902']['valores'], {'informados': 1})
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
