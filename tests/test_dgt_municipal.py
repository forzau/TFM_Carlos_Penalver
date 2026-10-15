import hashlib
import tempfile
import unittest
from pathlib import Path
import sys

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from auditar_dgt_municipal import audit_workbook


class MunicipalTests(unittest.TestCase):
    def fixture(self, folder, rows):
        path = Path(folder) / 'municipal.xlsx'
        book = Workbook()
        book.active.title = 'DatosMunicipalesGeneral_2025'
        book.active.append(['Código INE', 'Municipio', 'Parque Total', 'Electrificado', 'Distintivo 0'])
        for row in rows:
            book.active.append(row)
        book.save(path)
        book.close()
        population = Path(folder) / 'poblacion.csv'
        population.write_text('Municipios;Sexo;Periodo;Total\n03001 Test;Total;2025;500\n12001 Otro;Total;2025;800\n', encoding='utf-8')
        return path, population

    def test_separa_no_asignados_y_conserva_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path, population = self.fixture(folder, [['03001', 'Test', 100, 2, 3], ['12001', 'Otro', 200, 0, 1], ['03000', 'Sin especificar', 8, 0, 0]])
            before = hashlib.sha256(path.read_bytes()).digest()
            result = audit_workbook(path, population)
            self.assertEqual(result['municipios_cv'], 2)
            self.assertEqual(result['faltan'], [])
            self.assertEqual(result['indicadores']['Parque Total']['total_municipios'], 300)
            self.assertEqual(len(result['filas_sin_municipio']), 1)
            self.assertEqual(before, hashlib.sha256(path.read_bytes()).digest())

    def test_detecta_faltantes_repetidos_y_valores_no_validos(self):
        with tempfile.TemporaryDirectory() as folder:
            path, population = self.fixture(folder, [['03001', 'Test', 100, None, 3], ['03001', 'Test', -1, 0, 1]])
            result = audit_workbook(path, population)
            self.assertEqual(result['faltan'], ['12001'])
            self.assertEqual(result['codigos_duplicados'], {'03001': 2})
            self.assertEqual(result['indicadores']['Parque Total']['no_validos'], 1)
            self.assertEqual(result['indicadores']['Electrificado']['no_validos'], 1)

    def test_no_completa_ceros_de_codigos_ambiguos(self):
        with tempfile.TemporaryDirectory() as folder:
            path, population = self.fixture(folder, [[3001, 'Test', 100, 2, 3]])
            with self.assertRaises(ValueError):
                audit_workbook(path, population)
