import csv
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preparar_capacidad_demanda import (RAW, SCHEMA, typed_value, coordinate_state,
                                        prepare, validate, write_outputs, NULL)


def row(**values):
    record = dict.fromkeys(RAW, '')
    record.update(gestor_red='R1-001', provincia_nombre_origen='Alicante/Alacant',
        municipio_nombre_origen='Municipio de prueba', x_utm_origen='700000,123456789',
        y_utm_origen='4200000,12345678', subestacion_origen='0001',
        nivel_tension_kv_origen='13,2', capacidad_firme_disponible_mw_origen='0',
        capacidad_ocupada_mw_origen='12,34', capacidad_admitida_no_evaluada_mw_origen='0',
        compromiso_regulatorio_origen='0', nudo_0_asterisco_origen='1',
        nombre_punto_conexion='PUNTO; "PRUEBA"  ', punto_conexion_id='0000000123')
    record.update(values)
    return [record[k] for k in RAW]


class CapacidadDemandaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.c = duckdb.connect()
        self.addCleanup(self.c.close)

    def build(self, rows):
        path = self.root / 'entrada.csv'
        with path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.writer(stream, delimiter=';')
            writer.writerow(RAW.values())
            writer.writerows(rows)
        return prepare(self.c, path, self.root, 'ide:huella')

    def test_exact_decimal_boundaries_and_no_rounding(self):
        self.assertEqual(typed_value('13,2', 'DECIMAL(18,2)'), (Decimal('13.2'), 'informado'))
        self.assertEqual(typed_value('9999999999999999,99', 'DECIMAL(18,2)')[0], Decimal('9999999999999999.99'))
        for raw in ('1,001', '1.234', '1.234,56', '1e2', '-1', 'NaN', '10000000000000000'):
            self.assertEqual(typed_value(raw, 'DECIMAL(18,2)'), (None, 'error_conversion'))
        self.assertEqual(typed_value('0', 'DECIMAL(18,2)', positive=True), (None, 'error_conversion'))
        self.assertEqual(typed_value(str(2**63 - 1), 'BIGINT')[0], 2**63 - 1)
        for raw in ('1,5', '-1', str(2**63)):
            self.assertEqual(typed_value(raw, 'BIGINT'), (None, 'error_conversion'))

    def test_missing_zero_and_boolean_are_distinct(self):
        self.assertEqual(typed_value('', 'BOOLEAN'), (None, 'no_informado'))
        self.assertEqual(typed_value('0', 'BOOLEAN'), (False, 'informado'))
        self.assertEqual(typed_value('1', 'BOOLEAN'), (True, 'informado'))
        self.assertEqual(typed_value('true', 'BOOLEAN'), (None, 'error_conversion'))
        self.build([row()])
        self.assertEqual(self.c.execute('''SELECT capacidad_firme_disponible_mw,posiciones_libres,
            posiciones_libres_origen,estado_posiciones_libres,compromiso_regulatorio,
            nudo_0_asterisco FROM capacidad_demanda''').fetchone(),
            (Decimal(0), None, '', 'no_informado', False, True))

    def test_all_original_fields_ordinal_and_leading_zero_id_survive_export(self):
        original = row(comentarios_origen='Texto\ncon salto', capacidad_ocupada_mw_origen='9999999999999999,99')
        counts = self.build([row(provincia_nombre_origen='Madrid', punto_conexion_id='otra'), original])
        self.assertEqual(counts['filas_nacionales'], 2)
        self.assertEqual(counts['filas_cv'], 1)
        fields = ','.join(RAW)
        self.assertEqual(list(self.c.execute(f'SELECT {fields} FROM capacidad_demanda').fetchone()), original)
        self.assertEqual(self.c.execute('SELECT registro_origen FROM capacidad_demanda').fetchone()[0], 2)
        target = self.root / 'salidas'
        outputs = write_outputs(self.c, target, 'ide:huella')
        self.assertEqual([r['filas'] for r in outputs], [1, 0])
        restored = self.c.execute('SELECT * FROM read_parquet(?)', [str(target / 'capacidad_demanda.parquet')])
        self.assertEqual([c[0] for c in restored.description], list(SCHEMA))
        self.assertEqual(self.c.execute('SELECT capacidad_ocupada_mw FROM read_parquet(?)',
            [str(target / 'capacidad_demanda.parquet')]).fetchone()[0], Decimal('9999999999999999.99'))
        with self.assertRaises(FileExistsError):
            write_outputs(self.c, target, 'ide:huella')

    def test_bad_values_are_retained_with_incidents(self):
        self.build([row(nivel_tension_kv_origen='0', capacidad_ocupada_mw_origen='1,234',
            posiciones_libres_origen='-1', compromiso_regulatorio_origen='2', x_utm_origen='700.000,1')])
        report = validate(self.c)
        self.assertEqual(report['numero_incidencias'], 5)
        self.assertEqual(self.c.execute('SELECT capacidad_ocupada_mw,capacidad_ocupada_mw_origen FROM capacidad_demanda').fetchone(), (None, '1,234'))

    def test_zero_star_with_positive_capacity_is_flagged_without_erasing_values(self):
        self.build([row(capacidad_firme_disponible_mw_origen='2,34')])
        self.assertEqual(validate(self.c)['numero_incidencias'], 1)
        self.assertEqual(self.c.execute('SELECT capacidad_firme_disponible_mw,nudo_0_asterisco FROM capacidad_demanda').fetchone(), (Decimal('2.34'), True))

    def test_no_crs_geometry_or_date_is_invented(self):
        self.assertEqual(coordinate_state('700000,123456789', '4200000,1'), 'pendiente_crs')
        self.assertEqual(coordinate_state('', '4200000,1'), 'no_informadas')
        self.build([row()])
        self.assertEqual(self.c.execute('SELECT estado_coordenadas,fecha_referencia,estado_fecha FROM capacidad_demanda').fetchone(), ('pendiente_crs', None, 'no_acreditada'))
        self.assertNotIn('geometria', SCHEMA)
        self.assertNotIn('codigo_municipio', SCHEMA)

    def test_national_duplicate_and_blank_ids_fail_even_outside_cv(self):
        for rows in ([row(), row(provincia_nombre_origen='Madrid')],
                     [row(punto_conexion_id='')], [row(punto_conexion_id=' 001 ')]):
            with self.assertRaises(ValueError):
                self.build(rows)

    def test_bad_header_width_reserved_null_and_no_cv_fail(self):
        for rows in ([row()[:-1]], [row(comentarios_origen=NULL)], [row(provincia_nombre_origen='Madrid')]):
            with self.assertRaises(ValueError):
                self.build(rows)
        path = self.root / 'otra.csv'
        path.write_text('Provincia;OTRO\nAlicante;texto\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            prepare(self.c, path, self.root, 'ide:huella')


if __name__ == '__main__':
    unittest.main()
