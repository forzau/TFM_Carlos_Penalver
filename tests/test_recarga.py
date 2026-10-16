import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preparar_recarga import (HEADERS, coordinate, export_rows, modified, parent,
                             power, prepare, validate, write_outputs)


def row():
    return ['Comunitat Valenciana', 'Alicante/Alacant', 'Alicante/Alacant',
            '38.3', '-0.5', 'Estación "Centro"', 'Calle; número 1\r\nBajo', '03001',
            'DESCONOCIDO', ' 24/7', 'Lunes', 'Operador', 'ES*AAA', '', '001',
            'P01', 'NODISPONIBLE', 'RFID', 'C01', '01', 'T2', 'AC', 'Cable',
            '22,17 kW', '400 V', '32,00 A', '09/09/2026 13:04:05']


def export(path, rows):
    records = [';'.join(('=' if i in (3, 4, 7, 8) else '') + '"' + v + '"'
                        for i, v in enumerate(r)) for r in rows]
    path.write_bytes((';'.join(HEADERS) + '\r\n' + '\r\n'.join(records) + '\r\n').encode('utf-16-le'))


class RecargaTests(unittest.TestCase):
    def test_literal_quotes_semicolon_multiline_and_wrappers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'raw.csv'
            export(path, [row(), row()])
            records = list(export_rows(path))
            self.assertEqual([r[0] for r in records], [1, 2])
            self.assertEqual(records[0][1], row())
            self.assertTrue(records[0][2])
            self.assertEqual(records[0][1][7], '03001')

    def test_changed_header_width_and_formula_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'raw.csv'
            for values in [row()[:-1], row() + ['extra']]:
                export(path, [values])
                with self.assertRaises(ValueError):
                    list(export_rows(path))
            export(path, [row()])
            original = path.read_bytes().decode('utf-16-le')
            for bad in [original.replace('PROVINCIA', 'OTRA', 1),
                        original.replace('"Operador"', '="Operador"', 1),
                        original[:-5]]:
                path.write_bytes(bad.encode('utf-16-le'))
                with self.assertRaises(ValueError):
                    list(export_rows(path))

    def test_typed_values_do_not_round_or_execute(self):
        self.assertEqual(str(power('22,17 kW')[0]), '22.17')
        self.assertEqual(power('0,00 kW')[0], 0)
        self.assertEqual(power('DESCONOCIDO'), (None, 'no_informado'))
        for value in ['22,171 kW', '-1 kW', '22.17 kW', '10000000000000000 kW', '=1+1']:
            self.assertEqual(power(value)[1], 'error_conversion')
        self.assertEqual(coordinate('-0.5000001', False)[0], -0.5000001)
        self.assertEqual(coordinate('91', True), (None, 'fuera_rango'))
        for value in ['NaN', '1,1', '=1+1']:
            self.assertEqual(coordinate(value, True)[1], 'error_conversion')
        self.assertEqual(modified('09/09/2026 13:04:05')[0].hour, 13)
        self.assertEqual(modified('23/04/2025 9:35:26')[0].hour, 9)
        self.assertIsNone(modified('23/04/2025 9:5:26')[0])
        self.assertIsNone(modified('31/02/2026 13:04:05')[0])

    def test_parent_conflicts_never_choose_first(self):
        parents = {}
        parent(parents, '01', ('igual',), 'instalación')
        parent(parents, '01', ('igual',), 'instalación')
        with self.assertRaises(ValueError):
            parent(parents, '01', ('otra',), 'instalación')

    def test_entities_variants_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, duckdb.connect() as connection:
            path = Path(tmp) / 'raw.csv'
            second = row(); second[19] = '02'; second[10] = 'Martes'; second[17] = 'Tarjeta'
            export(path, [row(), second])
            reading = prepare(connection, path, Path(tmp))
            quality = validate(connection)
            self.assertEqual(reading['recuentos']['filas_cv'], 2)
            self.assertEqual(quality['variantes_textuales_conservadas']['horarios_por_instalacion'], 1)
            self.assertEqual(quality['variantes_textuales_conservadas']['pagos_por_punto'], 1)
            outputs = write_outputs(connection, Path(tmp) / 'out', 'origen:hash')
            self.assertEqual([r['filas'] for r in outputs], [1, 1, 2, 0])
            self.assertEqual(connection.execute('SELECT nombre_instalacion FROM recarga_instalaciones').fetchone()[0], row()[5])
            with self.assertRaises(FileExistsError):
                write_outputs(connection, Path(tmp) / 'out', 'origen:hash')
            connection.execute('DELETE FROM recarga_puntos')
            with self.assertRaisesRegex(ValueError, 'Relación incompleta'):
                validate(connection)

    def test_repeated_cv_key_fails_and_national_variants_are_described(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'raw.csv'
            export(path, [row(), row()])
            with duckdb.connect() as connection:
                prepare(connection, path, Path(tmp))
                with self.assertRaisesRegex(ValueError, 'Clave repetida'):
                    validate(connection)
            outsider = row(); outsider[0] = 'Extremadura'; outsider[1] = 'Badajoz'; outsider[14] = '002'
            variant = outsider.copy(); variant[10] = 'Martes'
            export(path, [outsider, variant, row()])
            with duckdb.connect() as connection:
                result = prepare(connection, path, Path(tmp))
                self.assertEqual(result['filas_adicionales_por_clave_nacional'], 1)
                self.assertEqual(result['claves_repetidas_nacionales'][0]['campos_variables'], ['HORARIO APERTURA'])
                self.assertEqual(connection.execute('SELECT count(*) FROM recarga_conectores').fetchone()[0], 1)

    def test_conversion_incidents_and_zero_coordinates_are_retained(self):
        with tempfile.TemporaryDirectory() as tmp, duckdb.connect() as connection:
            path = Path(tmp) / 'raw.csv'
            bad = row(); bad[3:5] = ['0', '0']; bad[23] = '22,171 kW'; bad[26] = 'ayer'
            export(path, [bad])
            prepare(connection, path, Path(tmp))
            quality = validate(connection)
            self.assertEqual(quality['incidencias'], 3)
            self.assertEqual(connection.execute('SELECT potencia_maxima_kw,fecha_ultima_modificacion FROM recarga_conectores').fetchone(), (None, None))
            self.assertEqual(connection.execute('SELECT potencia_maxima_origen FROM recarga_conectores').fetchone()[0], bad[23])
            self.assertEqual(connection.execute('SELECT estado_coordenadas FROM recarga_instalaciones').fetchone()[0], 'coordenadas_0_0')


if __name__ == '__main__':
    unittest.main()
