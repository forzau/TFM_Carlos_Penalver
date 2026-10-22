"""Controles del script independiente: lectores, exportación y recorrido Gold."""

import ast
import builtins
import csv
import json
import math
import symtable
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import preparar_dataset as flujo
from test_recarga import export, row
import test_gold_candidatos as candidatos
import test_capacidad_demanda as capacidad


class PreparacionUnicaTests(unittest.TestCase):
    def test_archivo_independiente_y_referencias_definidas(self):
        source = Path(flujo.__file__).read_text(encoding='utf-8')
        modules = {node.module for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)}
        scripts = {p.stem for p in Path(flujo.__file__).parent.glob('*.py')}
        self.assertFalse(modules & scripts)
        symbols = symtable.symtable(source, flujo.__file__, 'exec')
        defined = {s.get_name() for s in symbols.get_symbols() if s.is_assigned() or s.is_imported()}
        defined.update(dir(builtins))
        defined.update(('__file__', '__name__', '__doc__'))
        pending, missing = [symbols], set()
        while pending:
            table = pending.pop()
            pending.extend(table.get_children())
            missing.update(s.get_name() for s in table.get_symbols()
                           if s.is_global() and s.is_referenced() and s.get_name() not in defined)
        self.assertEqual(missing, set())

    def test_lector_recarga_conserva_texto_y_separa_entidades(self):
        with tempfile.TemporaryDirectory() as folder, duckdb.connect() as c:
            path = Path(folder) / 'recarga.csv'
            first, second = row(), row()
            second[19] = '02'
            export(path, [first, second])
            flujo.recarga_prepare(c, path, Path(folder))
            flujo.recarga_validate(c)
            self.assertEqual(c.execute('SELECT count(*) FROM recarga_instalaciones').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM recarga_puntos').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM recarga_conectores').fetchone()[0], 2)
            self.assertEqual(c.execute('SELECT nombre_instalacion,direccion,codigo_postal '
                                       'FROM recarga_instalaciones').fetchone(), (first[5], first[6], first[7]))

    def test_renta_ausente_no_se_convierte_en_cero(self):
        self.assertEqual(flujo.demografia_ine_number('..'), (None, 'no_informado'))
        self.assertEqual(flujo.demografia_ine_number('0', integer=True), (0, 'informado'))
        self.assertEqual(flujo.demografia_ine_number('1.234,56')[0], flujo.Decimal('1234.56'))
        self.assertEqual(flujo.demografia_ine_number('=1+1'), (None, 'error_conversion'))

    def test_capacidad_conserva_cero_ausencia_y_banderas(self):
        with tempfile.TemporaryDirectory() as folder, duckdb.connect() as c:
            path = Path(folder) / 'entrada.csv'
            with path.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.writer(stream, delimiter=';')
                writer.writerow(flujo.CAPACIDAD_RAW.values())
                writer.writerow(capacidad.row())
            flujo.capacidad_prepare(c, path, Path(folder), 'ide:prueba')
            flujo.capacidad_validate(c)
            self.assertEqual(c.execute('''SELECT capacidad_firme_disponible_mw,posiciones_libres,
                compromiso_regulatorio,nudo_0_asterisco FROM capacidad_demanda''').fetchone(),
                (flujo.Decimal(0), None, False, True))

    def test_huella_detecta_cambio_y_rechaza_ruta_exterior(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'copia.csv'
            path.write_bytes(b'original')
            expected = flujo.comprobar_archivo(root, path)
            path.write_bytes(b'cambiado')
            with self.assertRaisesRegex(ValueError, 'distinta'):
                flujo.comprobar_archivo(root, path, expected)
            with self.assertRaisesRegex(ValueError, 'fuera'):
                flujo.comprobar_archivo(root / 'otra', path)

    def test_exportacion_preserva_nulos_y_dos_geometrias(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with flujo.conectar(root) as c, patch.object(flujo, 'RAIZ', root):
                c.execute('''CREATE TABLE ejemplo AS SELECT 1 id,NULL::VARCHAR desconocido,
                    ST_Point(1,2)::GEOMETRY('EPSG:25830') geometria,
                    ST_Point(3,4)::GEOMETRY('EPSG:25830') punto_representativo''')
                output = flujo.exportar_tablas(c, root / 'salida', {'ejemplo': ['id']})['ejemplo']
                path = root / output['ruta']
                self.assertEqual(output['filas'], 1)
                self.assertIsNone(c.execute('SELECT desconocido FROM read_parquet(?)', [str(path)]).fetchone()[0])
                metadata = dict(c.execute('SELECT decode(key),decode(value) FROM parquet_kv_metadata(?)', [str(path)]).fetchall())
                self.assertEqual(set(json.loads(metadata['geo'])['columns']), {'geometria', 'punto_representativo'})
                with self.assertRaises(FileExistsError):
                    flujo.exportar_tablas(c, root / 'salida', {'ejemplo': ['id']})

    def test_exportacion_rechaza_clave_duplicada(self):
        with tempfile.TemporaryDirectory() as folder, duckdb.connect() as c:
            c.execute('CREATE TABLE ejemplo AS SELECT 1 id UNION ALL SELECT 1')
            with self.assertRaisesRegex(ValueError, 'repetida'):
                flujo.exportar_tablas(c, Path(folder) / 'salida', {'ejemplo': ['id']})

    def test_gold_conserva_areas_contextos_multiples_y_escalas_fijas(self):
        fixture = candidatos.CandidateGoldTests('test_empty_offer_is_explicit_and_keeps_candidates')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        c = fixture.c
        c.execute("ALTER TABLE gold_municipios ADD COLUMN geometria GEOMETRY('EPSG:25830')")
        c.execute('UPDATE gold_municipios m SET geometria=r.geometria FROM recintos_municipales r '
                  'WHERE m.codigo_municipio=r.codigo_municipio')
        c.execute('ALTER TABLE gold_municipios ADD COLUMN vehiculos_distintivo_0 BIGINT')
        c.execute("UPDATE gold_municipios SET vehiculos_distintivo_0=CASE WHEN codigo_municipio='03001' THEN 10 ELSE 30 END")
        flujo.gold_candidatos_prepare(c, 'sintesis')
        flujo.gold_candidatos_proximity(c, 'sintesis')
        flujo.gold_candidatos_validate(c, 'sintesis')
        c.execute('DROP TABLE ambito_cv')
        flujo.gold_controles_prepare(c, 'sintesis')
        flujo.gold_controles_validate(c, 'sintesis')
        c.execute('DROP TABLE escenarios')
        c.execute('DROP TABLE oferta')
        flujo.gold_variables_prepare(c, 'sintesis')
        flujo.gold_variables_validate(c, 'sintesis')
        area = c.execute('''SELECT v.codigo_municipio_contexto,v.distancia_minima_geometria_m
            FROM gold_variables_candidato v JOIN gold_candidatos USING(candidato_id)
            WHERE fid_origen=2 AND escenario='principal_admitida' ''').fetchone()
        self.assertEqual(area, (None, 0.0))
        self.assertEqual(c.execute("SELECT maximo FROM gold_referencias_normalizacion WHERE dimension='demanda'").fetchone()[0], 30)
        self.assertAlmostEqual(c.execute("SELECT demanda_normalizada_log FROM gold_variables_municipio WHERE codigo_municipio='03001'").fetchone()[0], math.log1p(10) / math.log1p(30))


if __name__ == '__main__':
    unittest.main()
