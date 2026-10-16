import csv
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import duckdb
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preparar_demografia_parque import (POP, INCOME, ine_number, territory_code,
    prepare_ine, prepare_municipal_park, prepare_detail, validate, write_outputs, municipal_base, check_key)


def write_csv(path, header, rows, delimiter=';', encoding='utf-8'):
    with path.open('w', encoding=encoding, newline='') as stream:
        writer = csv.writer(stream, delimiter=delimiter)
        writer.writerow(header)
        writer.writerows(rows)


class INENumberTests(unittest.TestCase):
    def test_exact_decimal_thousands_nulls_zero_and_original_precision(self):
        self.assertEqual(ine_number('1.234,56'), (Decimal('1234.56'), 'informado'))
        self.assertEqual(ine_number('-12,50'), (Decimal('-12.50'), 'informado'))
        self.assertEqual(ine_number('0', integer=True), (0, 'informado'))
        for value in ('', '.', '..', '...'):
            self.assertEqual(ine_number(value), (None, 'no_informado'))
        for value in ('1.2', '1,234', 'NaN', '10000000000000000'):
            self.assertEqual(ine_number(value), (None, 'error_conversion'))
        for value in ('-1', '2,5', str(2**63)):
            self.assertEqual(ine_number(value, integer=True), (None, 'error_conversion'))

    def test_territory_code_does_not_truncate_district_or_guess_leading_zero(self):
        self.assertEqual(territory_code('03001 Municipio', 5), '03001')
        for text in ('3001 Municipio', '0300101 Distrito', ''):
            with self.assertRaises(ValueError):
                territory_code(text, 5)


class DemographyParkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.connection = duckdb.connect()
        self.addCleanup(self.connection.close)
        self.codes = {'03001', '46902'}
        self.connection.execute("CREATE TABLE municipios AS SELECT unnest(['03001','46902']) codigo_municipio")
        self.population = self.root / 'poblacion.csv'
        self.income = self.root / 'renta.csv'
        self.population_rows = [['', code + ' Nombre', sex, '2025', value]
            for code, numbers in [('03001', ['10', '4', '6']), ('46902', ['3', '1', '2'])]
            for sex, value in zip(('Total', 'Hombres', 'Mujeres'), numbers)]
        self.income_rows = [
            ['03001 A', '', '', 'Renta neta media por persona', '2023', '0'],
            ['03001 A', '0300101 A', '', 'Renta neta media por persona', '2023', '.'],
            ['03001 A', '0300101 A', '0300101001 A', 'Renta neta media por persona', '2023', '..'],
            ['46902 Gátova', '', '', 'Renta neta media por persona', '2023', '1.234'],
            ['12066 Gátova', '', '', 'Renta neta media por persona', '2023', ''],
        ]

    def prepare_ine(self):
        write_csv(self.population, ['Total Nacional', 'Municipios', 'Sexo', 'Periodo', 'Total'], self.population_rows)
        write_csv(self.income, ['Municipios', 'Distritos', 'Secciones', 'Indicadores de renta media', 'Periodo', 'Total'], self.income_rows)
        return prepare_ine(self.connection, self.population, self.income, self.codes, self.root, {POP: 'pop', INCOME: 'income'})

    def prepare_park(self, invalid=False):
        book = Workbook()
        sheet = book.active
        sheet.title = 'DatosMunicipalesGeneral_2025'
        sheet.append(['Código INE', 'Parque Total', 'Distintivo 0', 'Electrificado'])
        for row in [('03001', 2, 1, 1), ('46902', 1, 0, 0), ('03000', 1, 0, 0), ('46000', 1, 0, 0)]:
            sheet.append(row)
        if invalid:
            sheet['B2'] = True
        path = self.root / 'parque.xlsx'
        book.save(path)
        book.close()
        return prepare_municipal_park(self.connection, path, self.codes)

    def prepare_detail(self):
        path = self.root / 'parque.txt'
        write_csv(path, ['PROVINCIA', 'MUNICIPIO', 'TIPO_DGT', 'PROPULSION', 'CATELECT', 'TIPO_DISTINTIVO'],
            [('01', '', 'TURISMOS', '0', '', 'DISTINTIVO B'),
             ('03', '03001', 'TURISMOS', '2', 'BEV', 'DISTINTIVO 0'),
             ('03', '03001', 'TURISMOS', '2', 'BEV', 'DISTINTIVO 0'),
             ('03', '', 'TURISMOS', '0', '', 'DISTINTIVO B'),
             ('46', '46902', 'TURISMOS', '1', 'PHEV', 'DISTINTIVO 0'),
             ('46', '', 'TURISMOS', '0', '', 'DISTINTIVO B')], delimiter='|', encoding='latin-1')
        return prepare_detail(self.connection, path, 'original_txt')

    def test_full_flow_preserves_duplicate_attributes_nulls_hierarchy_and_historic_code(self):
        ine = self.prepare_ine()
        self.prepare_park()
        detail = self.prepare_detail()
        profile = validate(self.connection, self.codes)
        self.assertEqual((ine['renta_cv_vigente'], ine['renta_historica']), (4, 1))
        self.assertEqual(detail['filas_nacionales'], 6)
        self.assertEqual(profile['incidencias_conversion'], 0)
        self.assertEqual(self.connection.execute('SELECT registro_origen FROM parque_detalle_observado ORDER BY 1').fetchall(), [(2,), (3,), (4,), (5,), (6,)])
        self.assertEqual(self.connection.execute("SELECT count(*) FROM parque_detalle_observado WHERE codigo_municipio IS NULL").fetchone()[0], 2)
        self.assertEqual(self.connection.execute("SELECT codigo_municipio FROM renta_codigos_historicos").fetchone()[0], '12066')
        self.assertEqual(self.connection.execute("SELECT valor_eur,estado_valor,valor_origen FROM renta_territorial WHERE codigo_territorio='03001'").fetchone(), (Decimal('0.00'), 'informado', '0'))
        self.assertEqual(self.connection.execute("SELECT valor_eur,valor_origen FROM renta_territorial WHERE nivel_territorial='seccion'").fetchone(), (None, '..'))
        outputs = write_outputs(self.connection, self.root / 'salidas', {})
        self.assertEqual(len(outputs), 7)
        with self.assertRaises(FileExistsError):
            write_outputs(self.connection, self.root / 'salidas', {})

    def test_invalid_value_is_retained_as_null_with_incident_instead_of_rounded(self):
        self.income_rows[0][-1] = '1,234'
        self.prepare_ine()
        self.assertEqual(self.connection.execute("SELECT valor_eur,estado_valor FROM renta_territorial WHERE codigo_territorio='03001'").fetchone(), (None, 'error_conversion'))
        self.assertEqual(self.connection.execute('SELECT count(*) FROM incidencias').fetchone()[0], 1)

    def test_inconsistent_hierarchy_is_rejected(self):
        self.income_rows[2][1] = '4690201 Otro distrito'
        with self.assertRaisesRegex(ValueError, 'Jerarquía territorial'):
            self.prepare_ine()

    def test_duplicate_population_key_is_rejected(self):
        self.population_rows.append(self.population_rows[0])
        self.prepare_ine()
        with self.assertRaisesRegex(ValueError, 'Clave repetida'):
            check_key(self.connection, 'poblacion_municipal', ['codigo_municipio', 'sexo', 'anio'])

    def test_boolean_park_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Recuentos DGT'):
            self.prepare_park(invalid=True)

    def test_reference_pointer_cannot_escape_its_directory(self):
        directory = self.root / 'resultados/silver/base_territorial'
        directory.mkdir(parents=True)
        (directory / 'actual.json').write_text(json.dumps({'informe': '../../../ajeno.json'}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'fuera de su carpeta'):
            municipal_base(self.connection, self.root)


if __name__ == '__main__':
    unittest.main()
