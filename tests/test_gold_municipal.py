import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preparar_gold_municipal import ROOT, KEYS, prepare, validate, load_inputs
from preparar_recarga_versionada import write_outputs


class MunicipalGoldTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.c = duckdb.connect(str(self.root / 'prueba.duckdb'), config={
            'extension_directory': str(ROOT / '.venv/duckdb_extensions'),
            'storage_compatibility_version': 'v1.5.0'})
        self.addCleanup(self.c.close)
        c = self.c
        c.execute('LOAD spatial')
        c.execute("SET TimeZone='UTC'")
        c.execute("""CREATE TABLE municipios AS SELECT * FROM (VALUES
            ('03001','03','Alpha'),('03002','03','Beta'),('03003','03','Gamma'))
            v(codigo_municipio,codigo_provincia,nombre_municipio)""")
        c.execute("""CREATE TABLE recintos_municipales AS SELECT codigo_municipio,
            ST_GeomFromText('POLYGON ((0 0,100 0,100 100,0 100,0 0))')
                ::GEOMETRY('EPSG:25830') geometria FROM municipios""")
        c.execute("""CREATE TABLE parque_municipal AS SELECT codigo_municipio,
            DATE '2025-12-31' fecha_referencia,100::BIGINT parque_total,
            CASE codigo_municipio WHEN '03001' THEN 10 WHEN '03002' THEN 0 ELSE 9 END::BIGINT vehiculos_distintivo_0
            FROM municipios""")
        c.execute("""CREATE TABLE poblacion_municipal AS SELECT codigo_municipio,
            'Total'::VARCHAR sexo,2025::SMALLINT anio,500::BIGINT poblacion,
            'informado'::VARCHAR estado_valor FROM municipios""")
        c.execute("""CREATE TABLE renta_territorial AS SELECT codigo_municipio,
            'municipio'::VARCHAR nivel_territorial,'Renta neta media por persona'::VARCHAR indicador,
            2023::SMALLINT anio,CASE WHEN codigo_municipio='03002' THEN NULL ELSE 10000 END::DECIMAL(18,2) valor_eur,
            CASE WHEN codigo_municipio='03002' THEN 'no_informado' ELSE 'informado' END estado_valor FROM municipios""")
        c.execute("""CREATE TABLE recarga_instalaciones_geo AS SELECT *,
            ST_Point(10,20)::GEOMETRY('EPSG:25830') geometria,'admitida'::VARCHAR estado_geometria FROM (VALUES
            ('i1','Estación admitida','operador','03001'),('p1','Estación pendiente','operador','03002'))
            v(instalacion_id,nombre_instalacion,operador_id,codigo_municipio_declarado)""")
        c.execute("""CREATE TABLE recarga_puntos AS SELECT * FROM (VALUES
            ('i1','P1'),('i1','P2'),('p1','P1')) v(instalacion_id,punto_id)""")
        c.execute("""CREATE TABLE recarga_conectores AS SELECT * FROM (VALUES
            ('i1','P1','C1'),('i1','P1','C2'),('i1','P2','C1'),('p1','P1','C1'))
            v(instalacion_id,punto_id,conector_id)""")
        c.execute("""CREATE TABLE recarga_municipio_validado AS SELECT 'i1'::VARCHAR instalacion_id,
            '03001'::VARCHAR codigo_municipio,'interseccion'::VARCHAR metodo""")
        c.execute("""CREATE TABLE recarga_municipios_candidatos AS SELECT * FROM (VALUES
            ('i1','03001'),('p1','03001')) v(instalacion_id,codigo_municipio)""")
        c.execute("""CREATE TABLE recarga_ausentes AS SELECT *,ST_Point(30,40)::GEOMETRY('EPSG:25830') geometria,
            'admitida'::VARCHAR estado_geometria FROM (VALUES
            ('h1','Histórica','operador','03002','03003','interseccion',4::BIGINT,4::BIGINT),
            ('h2','Histórica sin municipio','operador',NULL,NULL,NULL,1::BIGINT,1::BIGINT))
            v(instalacion_id,nombre_instalacion,operador_id,codigo_municipio_declarado,
              codigo_municipio_admitido_historico,metodo_admision_historica,
              puntos_registrados_historicos,conectores_registrados_historicos)""")
        c.execute("""CREATE TABLE recarga_ausentes_municipios_candidatos AS
            SELECT 'h1'::VARCHAR instalacion_id,'03003'::VARCHAR codigo_municipio""")

    def build(self):
        prepare(self.c, 'prueba', datetime(2026, 10, 18, 18, 38, tzinfo=timezone.utc), 'principal', 'historica')
        return validate(self.c, 'prueba')

    def test_entities_are_counted_without_connector_fanout_and_history_is_separate(self):
        profile = self.build()
        self.assertEqual(profile['oferta_principal'], {'instalaciones': 1, 'puntos': 2, 'conectores': 3})
        self.assertEqual(self.c.execute("SELECT distintivo_0_por_punto_admitido FROM gold_municipios WHERE codigo_municipio='03001'").fetchone()[0], 5.0)
        self.assertEqual(self.c.execute('SELECT count(*) FROM gold_recarga_instalaciones').fetchone()[0], 4)
        self.assertEqual(self.c.execute("SELECT estado_admision,fecha_adquisicion_observacion FROM gold_recarga_instalaciones WHERE instalacion_id='h1'").fetchone(), ('admitida_solo_historica', None))
        self.assertEqual(self.c.execute("SELECT puntos_con_municipio_admitido FROM gold_municipios WHERE codigo_municipio='03003'").fetchone()[0], 0)

    def test_zero_denominator_and_missing_income_keep_municipality_and_explicit_nulls(self):
        self.build()
        rows = self.c.execute("""SELECT codigo_municipio,distintivo_0_por_punto_admitido,
            estado_presion_descriptiva FROM gold_municipios WHERE codigo_municipio<>'03001' ORDER BY 1""").fetchall()
        self.assertEqual(rows, [('03002', None, 'sin_puntos_admitidos'), ('03003', None, 'sin_puntos_admitidos')])
        self.assertEqual(self.c.execute("SELECT renta_neta_media_persona_eur,estado_renta FROM gold_municipios WHERE codigo_municipio='03002'").fetchone(), (None, 'no_informado'))

    def test_uncertainty_roles_do_not_assign_pending_points_or_expand_historical_admission(self):
        profile = self.build()
        rows = self.c.execute('''SELECT instalacion_id,codigo_municipio,tipo_incertidumbre,
            es_municipio_admitido_historico,es_municipio_declarado,es_candidato_espacial
            FROM gold_incertidumbre_recarga_municipio ORDER BY 1,2''').fetchall()
        self.assertEqual(rows, [('h1','03003','ausencia_exportacion',True,False,True),
                                ('p1','03001','asignacion_pendiente',False,False,True),
                                ('p1','03002','asignacion_pendiente',False,True,False)])
        self.assertEqual(profile['incertidumbre_sin_localizar'], 1)
        self.assertTrue(all(x[0] for x in self.c.execute('SELECT hay_incertidumbre_sin_localizar FROM gold_municipios').fetchall()))

    def test_period_and_level_selection_do_not_mix_sexes_years_or_income_grains(self):
        self.c.execute("INSERT INTO poblacion_municipal VALUES ('03001','Hombres',2025,999,'informado'),('03001','Total',2024,888,'informado')")
        self.c.execute("INSERT INTO renta_territorial VALUES ('03001','distrito','Renta neta media por persona',2023,999999,'informado'),('03001','municipio','Renta neta media por persona',2022,7777,'informado')")
        self.build()
        self.assertEqual(self.c.execute("SELECT poblacion_total,renta_neta_media_persona_eur FROM gold_municipios WHERE codigo_municipio='03001'").fetchone(), (500,10000))

    def test_duplicate_selected_observation_stops_instead_of_choosing_a_row(self):
        self.c.execute("INSERT INTO poblacion_municipal SELECT * FROM poblacion_municipal WHERE codigo_municipio='03001'")
        with self.assertRaises(ValueError):
            self.build()

    def test_missing_selected_observation_stops_instead_of_imputing(self):
        self.c.execute("DELETE FROM renta_territorial WHERE codigo_municipio='03003'")
        with self.assertRaisesRegex(ValueError, 'Cobertura municipal incompleta'):
            self.build()

    def test_orphan_charging_detail_is_rejected(self):
        self.c.execute("INSERT INTO recarga_conectores VALUES ('inexistente','P1','C1')")
        with self.assertRaisesRegex(ValueError, 'huérfano'):
            self.build()

    def test_validation_rejects_tampered_ratios_and_uncertainty_counts(self):
        self.build()
        self.c.execute("UPDATE gold_municipios SET distintivo_0_por_punto_admitido=999 WHERE codigo_municipio='03001'")
        with self.assertRaisesRegex(ValueError, 'Cociente'):
            validate(self.c, 'prueba')
        self.c.execute("UPDATE gold_municipios SET distintivo_0_por_punto_admitido=5 WHERE codigo_municipio='03001'")
        self.c.execute('UPDATE gold_municipios SET instalaciones_pendientes_relacionadas=99')
        with self.assertRaisesRegex(ValueError, 'Avisos municipales'):
            validate(self.c, 'prueba')

    def test_export_preserves_nulls_geometry_schema_and_does_not_overwrite(self):
        self.build()
        outputs = write_outputs(self.c, self.root/'salida', KEYS)
        self.assertEqual(len(outputs), 3)
        restored = self.c.execute('SELECT renta_neta_media_persona_eur FROM read_parquet(?) WHERE codigo_municipio=?',
            [str(self.root/'salida/gold_municipios.parquet'), '03002']).fetchone()[0]
        self.assertIsNone(restored)
        with self.assertRaises(FileExistsError):
            write_outputs(self.c, self.root/'salida', KEYS)

    def test_loader_rejects_pointer_outside_block_or_another_execution(self):
        directory = self.root/'resultados/silver/base_territorial'
        directory.mkdir(parents=True)
        for target in ('../informe.json', 'otra/informe.json'):
            with self.subTest(target=target):
                (directory/'actual.json').write_text(json.dumps({'ejecucion':'elegida', 'informe':target}), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'Referencia de ejecución Silver'):
                    load_inputs(self.c, self.root)

    def test_loader_rejects_report_with_inconsistent_execution_identity(self):
        directory = self.root/'resultados/silver/base_territorial'
        (directory/'elegida').mkdir(parents=True)
        (directory/'actual.json').write_text(json.dumps({'ejecucion':'elegida', 'informe':'elegida/informe.json'}), encoding='utf-8')
        (directory/'elegida/informe.json').write_text(json.dumps({'ejecucion':'otra'}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'informe no corresponde'):
            load_inputs(self.c, self.root)


if __name__ == '__main__':
    unittest.main()
