import hashlib
import csv
import struct
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import duckdb
import auditar_fuentes
from auditar_fuentes import geometry_header, text_profile, audit_text
from unittest.mock import patch


class AuditTests(unittest.TestCase):
    def test_utf16_sin_bom_codigos_y_duplicados(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'prueba.csv'
            path.write_text('codigo;valor\n03001;\n03001;\n12001;4\n', encoding='utf-16-le')
            original = hashlib.sha256(path.read_bytes()).digest()
            with duckdb.connect() as connection:
                result = text_profile(connection, path, 'utf-16-le', ';', ['codigo'], [['codigo']])
            self.assertEqual(result['filas'], 3)
            self.assertEqual(result['vacios']['valor'], 2)
            self.assertEqual(result['claves']['codigo']['repeticiones'], 1)
            self.assertEqual(result['duplicados_muestra_inicial']['duplicados'], 1)
            self.assertEqual(result['categorias']['codigo'][0]['valor'], '03001')
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), original)

    def test_ancho_incorrecto_se_detecta(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mal.csv'
            path.write_text('codigo;valor\n03;1;extra\n', encoding='utf-16-le')
            with duckdb.connect() as connection, self.assertRaises(ValueError):
                text_profile(connection, path, 'utf-16-le', ';', [], [])

    def test_renta_niveles_y_valores_protegidos(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Renta.csv'
            path.write_text('Municipios;Distritos;Secciones;Indicadores de renta media;Periodo;Total\n03001 Test;;;Neta;2023;12.345\n03001 Test;0300101;;Neta;2023;..\n03001 Test;0300101;0300101001;Neta;2023;9.800\n', encoding='utf-8')
            with duckdb.connect() as connection:
                result = audit_text(connection, path)
            self.assertEqual(result['filas_cv']['municipios'], 1)
            self.assertEqual({x['nivel']: x['filas'] for x in result['niveles']}, {'municipio': 1, 'distrito': 1, 'seccion': 1})
            self.assertEqual(result['total_numerico']['maximo'], 12345)
            self.assertEqual(result['total_numerico']['no_numericos'], 1)

    def test_cabecera_geometria(self):
        for flag, order in [(1, '<'), (0, '>')]:
            self.assertEqual(geometry_header(b'GP' + bytes([0, flag]) + struct.pack(order + 'i', 4258)), {'srs_id': 4258, 'vacia': False})
        self.assertEqual(geometry_header(None), 'nula')
        self.assertEqual(geometry_header(b'broken'), 'cabecera_invalida')

    def test_miteco_formato_unidades_y_fecha_real(self):
        columns = ['COMUNIDAD AUTONOMA', 'LATITUD', 'LONGITUD', 'POTENCIA MAXIMA', 'FECHA DE ULTIMA MODIFICACION', 'COD.INSTALACION', 'ID. PUNTO DE RECARGA', 'ID. CONECTOR', 'TIPO CONECTOR', 'TIPO DE CARGA']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'instalaciones_actuales.csv'
            with path.open('w', encoding='utf-16-le', newline='') as stream:
                writer = csv.writer(stream, delimiter=';')
                writer.writerow(columns)
                for date in ['31/12/2023 12:00:00', '01/01/2024 12:00:00']:
                    writer.writerow(['Comunitat Valenciana', '="39.5"', '="-0.4"', '350,00 kW', date, 'i1', 'p1', 'c1', 'tipo', 'DC'])
            with duckdb.connect() as connection:
                result = audit_text(connection, path)
            self.assertEqual(result['diagnostico_formato_numerico']['POTENCIA MAXIMA']['maximo'], 350)
            self.assertEqual(result['diagnostico_formato_numerico']['LATITUD']['minimo'], 39.5)
            self.assertEqual(result['fechas_modificacion']['maximo'], '2024-01-01 12:00:00')
            self.assertEqual(result['cv'], {'filas': 2, 'instalaciones': 1, 'puntos': 1})

    def test_copia_sin_fuentes_no_informa_exito(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(auditar_fuentes, 'ROOT', Path(folder)):
            with self.assertRaises(FileNotFoundError):
                auditar_fuentes.main()


if __name__ == '__main__':
    unittest.main()
