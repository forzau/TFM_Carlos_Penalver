"""Controles del flujo modular: lectores, exportación y recorrido Gold."""

import builtins
from contextlib import nullcontext
import csv
import json
import math
import symtable
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

from src.datos_y_preparacion.pasos import bronze, comunes, gold, recarga, demografia, capacidad
from decimal import Decimal
from tests.datos_y_preparacion.historico.test_recarga import export, row
import tests.datos_y_preparacion.historico.test_gold_candidatos as candidatos
import tests.datos_y_preparacion.historico.test_capacidad_demanda as capacidad_fixtures


class FlujoModularTests(unittest.TestCase):
    def test_entradas_registran_todos_los_modulos_y_excluyen_el_historico(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            codigo = {'src/__init__.py', 'src/rutas.py', 'src/preparar_dataset.py',
                      'src/datos_y_preparacion/__init__.py', 'src/datos_y_preparacion/__main__.py',
                      'src/datos_y_preparacion/pasos/01_bronze.py', 'src/datos_y_preparacion/pasos/09_gold.py',
                      'src/datos_y_preparacion/flujo.py',
                      'src/datos_y_preparacion/pasos/__init__.py',
                      'src/datos_y_preparacion/pasos/02_territorio.py'}
            historico = 'src/datos_y_preparacion/historico/anterior.py'
            for ruta in codigo | {historico}:
                path = root / ruta
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('# ejemplo\n', encoding='utf-8')
            entradas = {'catalogo': 'catalogo.json', 'recarga_principal': 'recarga.csv',
                        'metadatos_recarga': 'recarga.json', 'metadatos_capacidad': 'capacidad.json'}
            documentos = {ruta: {} for ruta in entradas.values()}
            documentos.update({'capacidad.json': {'archivos': {}},
                               'recarga.json.adquisicion.json': {},
                               'recarga.csv.adquisicion.json': {
                                   'fecha_utc': '2026-11-13T00:00:00+00:00'}})
            for ruta, contenido in documentos.items():
                (root / ruta).write_text(json.dumps(contenido), encoding='utf-8')
            recibo = documentos['recarga.csv.adquisicion.json'] | comunes.huella(root / 'recarga.csv')
            (root / 'recarga.csv.adquisicion.json').write_text(json.dumps(recibo), encoding='utf-8')
            with patch.object(bronze, 'RAIZ', root), \
                 patch.object(bronze, '__file__', str(root / 'src/datos_y_preparacion/pasos/01_bronze.py')), \
                 patch.object(bronze, 'ENTRADAS', entradas), \
                 patch.object(bronze, 'conectar', return_value=nullcontext()), \
                 patch.object(bronze, 'bronze_build_manifest', return_value={'archivos': []}), \
                 patch.object(recarga, 'recarga_geo_evidence'), \
                 patch.object(capacidad, 'metadatos_ide_verify', return_value={}):
                _, archivos, _, _, _ = bronze.comprobar_entradas()
            registrados = {e['ruta'] for e in archivos if e['ruta'].startswith('src/')}
            self.assertEqual(registrados, codigo)
            self.assertTrue(all(len(e['sha256']) == 64 for e in archivos))

    def test_modulos_con_referencias_definidas(self):
        for path in (comunes.RAIZ / 'src/datos_y_preparacion').rglob('*.py'):
            if 'historico' in path.parts:
                continue
            with self.subTest(modulo=path.name):
                source = path.read_text(encoding='utf-8')
                symbols = symtable.symtable(source, str(path), 'exec')
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
            recarga.recarga_prepare(c, path, Path(folder))
            recarga.recarga_validate(c)
            self.assertEqual(c.execute('SELECT count(*) FROM recarga_instalaciones').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM recarga_puntos').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM recarga_conectores').fetchone()[0], 2)
            self.assertEqual(c.execute('SELECT nombre_instalacion,direccion,codigo_postal '
                                       'FROM recarga_instalaciones').fetchone(), (first[5], first[6], first[7]))

    def test_renta_ausente_no_se_convierte_en_cero(self):
        self.assertEqual(demografia.demografia_ine_number('..'), (None, 'no_informado'))
        self.assertEqual(demografia.demografia_ine_number('0', integer=True), (0, 'informado'))
        self.assertEqual(demografia.demografia_ine_number('1.234,56')[0], Decimal('1234.56'))
        self.assertEqual(demografia.demografia_ine_number('=1+1'), (None, 'error_conversion'))

    def test_capacidad_conserva_cero_ausencia_y_banderas(self):
        with tempfile.TemporaryDirectory() as folder, duckdb.connect() as c:
            path = Path(folder) / 'entrada.csv'
            with path.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.writer(stream, delimiter=';')
                writer.writerow(capacidad.CAPACIDAD_RAW.values())
                writer.writerow(capacidad_fixtures.row())
            capacidad.capacidad_prepare(c, path, Path(folder), 'ide:prueba')
            capacidad.capacidad_validate(c)
            self.assertEqual(c.execute('''SELECT capacidad_firme_disponible_mw,posiciones_libres,
                compromiso_regulatorio,nudo_0_asterisco FROM capacidad_demanda''').fetchone(),
                (Decimal(0), None, False, True))

    def test_huella_detecta_cambio_y_rechaza_ruta_exterior(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'copia.csv'
            path.write_bytes(b'original')
            expected = comunes.comprobar_archivo(root, path)
            path.write_bytes(b'cambiado')
            with self.assertRaisesRegex(ValueError, 'distinta'):
                comunes.comprobar_archivo(root, path, expected)
            with self.assertRaisesRegex(ValueError, 'fuera'):
                comunes.comprobar_archivo(root / 'otra', path)

    def test_exportacion_preserva_nulos_y_dos_geometrias(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with comunes.conectar(root) as c, patch.object(comunes, 'RAIZ', root):
                c.execute('''CREATE TABLE ejemplo AS SELECT 1 id,NULL::VARCHAR desconocido,
                    ST_Point(1,2)::GEOMETRY('EPSG:25830') geometria,
                    ST_Point(3,4)::GEOMETRY('EPSG:25830') punto_representativo''')
                output = comunes.exportar_tablas(c, root / 'salida', {'ejemplo': ['id']})['ejemplo']
                path = root / output['ruta']
                self.assertEqual(output['filas'], 1)
                self.assertIsNone(c.execute('SELECT desconocido FROM read_parquet(?)', [str(path)]).fetchone()[0])
                metadata = dict(c.execute('SELECT decode(key),decode(value) FROM parquet_kv_metadata(?)', [str(path)]).fetchall())
                self.assertEqual(set(json.loads(metadata['geo'])['columns']), {'geometria', 'punto_representativo'})
                with self.assertRaises(FileExistsError):
                    comunes.exportar_tablas(c, root / 'salida', {'ejemplo': ['id']})

    def test_exportacion_rechaza_clave_duplicada(self):
        with tempfile.TemporaryDirectory() as folder, duckdb.connect() as c:
            c.execute('CREATE TABLE ejemplo AS SELECT 1 id UNION ALL SELECT 1')
            with self.assertRaisesRegex(ValueError, 'repetida'):
                comunes.exportar_tablas(c, Path(folder) / 'salida', {'ejemplo': ['id']})

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
        gold.gold_candidatos_prepare(c, 'sintesis')
        gold.gold_candidatos_proximity(c, 'sintesis')
        gold.gold_candidatos_validate(c, 'sintesis')
        c.execute('DROP TABLE ambito_cv')
        gold.gold_controles_prepare(c, 'sintesis')
        gold.gold_controles_validate(c, 'sintesis')
        c.execute('DROP TABLE escenarios')
        c.execute('DROP TABLE oferta')
        gold.gold_variables_prepare(c, 'sintesis')
        gold.gold_variables_validate(c, 'sintesis')
        area = c.execute('''SELECT v.codigo_municipio_contexto,v.distancia_minima_geometria_m
            FROM gold_variables_candidato v JOIN gold_candidatos USING(candidato_id)
            WHERE fid_origen=2 AND escenario='principal_admitida' ''').fetchone()
        self.assertEqual(area, (None, 0.0))
        self.assertEqual(c.execute("SELECT maximo FROM gold_referencias_normalizacion WHERE dimension='demanda'").fetchone()[0], 30)
        self.assertAlmostEqual(c.execute("SELECT demanda_normalizada_log FROM gold_variables_municipio WHERE codigo_municipio='03001'").fetchone()[0], math.log1p(10) / math.log1p(30))


if __name__ == '__main__':
    unittest.main()
