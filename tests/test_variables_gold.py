import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import test_gold_candidatos as candidate_tests
from preparar_controles_gold import prepare as prepare_controls
from preparar_gold_candidatos import prepare as prepare_candidates, proximity
from preparar_recarga_versionada import write_outputs
from preparar_variables_gold import KEYS, load_inputs, prepare, validate


class GoldVariablesTests(unittest.TestCase):
    def setUp(self):
        base = candidate_tests.CandidateGoldTests('test_empty_offer_is_explicit_and_keeps_candidates')
        base.setUp()
        self.addCleanup(base.doCleanups)
        self.c,self.root = base.c,base.root
        self.c.execute("ALTER TABLE gold_municipios ADD COLUMN geometria GEOMETRY('EPSG:25830')")
        self.c.execute('''UPDATE gold_municipios m SET geometria=r.geometria
            FROM recintos_municipales r WHERE m.codigo_municipio=r.codigo_municipio''')
        self.c.execute('ALTER TABLE gold_municipios ADD COLUMN vehiculos_distintivo_0 BIGINT')
        self.c.execute("UPDATE gold_municipios SET vehiculos_distintivo_0=CASE WHEN codigo_municipio='03001' THEN 10 ELSE 30 END")

    def inputs(self):
        prepare_candidates(self.c,'cand')
        proximity(self.c,'cand')
        self.c.execute('DROP TABLE ambito_cv')
        prepare_controls(self.c,'ctrl')
        self.c.execute('DROP TABLE escenarios')
        self.c.execute('DROP TABLE oferta')

    def build(self):
        self.inputs()
        prepare(self.c,'vars')
        return validate(self.c,'vars')

    def test_municipal_reference_is_not_weighted_by_candidates(self):
        self.build()
        self.assertEqual(self.c.execute("SELECT n_total,minimo,maximo FROM gold_referencias_normalizacion WHERE dimension='demanda'").fetchone(),(2,10.0,30.0))
        self.assertEqual(self.c.execute('SELECT count(*) FROM gold_variables_municipio').fetchone()[0],2)
        row = self.c.execute("SELECT demanda_normalizada_log,demanda_normalizada_lineal FROM gold_variables_municipio WHERE codigo_municipio='03001'").fetchone()
        self.assertAlmostEqual(row[0],math.log1p(10)/math.log1p(30))
        self.assertAlmostEqual(row[1],1/3)

    def test_area_minimum_zero_and_original_point_distance(self):
        self.build()
        rows = self.c.execute('''SELECT fid_origen,distancia_minima_geometria_m FROM gold_variables_candidato
            JOIN gold_candidatos USING(candidato_id) WHERE escenario='principal_admitida' ORDER BY fid_origen''').fetchall()
        self.assertEqual(rows,[(1,2.0),(2,0.0),(3,3.1622776601683795),(4,2.0),(6,None)])

    def test_fixed_principal_reference_in_all_scenarios(self):
        self.build()
        self.assertAlmostEqual(self.c.execute("SELECT maximo FROM gold_referencias_normalizacion WHERE dimension='proximidad'").fetchone()[0],math.sqrt(10))
        rows = self.c.execute('''SELECT escenario,proximidad_normalizada_lineal FROM gold_variables_candidato
            JOIN gold_candidatos USING(candidato_id) WHERE fid_origen=1 ORDER BY escenario''').fetchall()
        self.assertEqual([r[0] for r in rows],['incluye_ausentes_historicas','incluye_pendientes','principal_admitida'])
        for actual,expected in zip([r[1] for r in rows],[0,1/math.sqrt(10),2/math.sqrt(10)]):self.assertAlmostEqual(actual,expected)

    def test_multiple_municipal_context_is_null_but_distance_known(self):
        self.build()
        rows = self.c.execute('''SELECT gold_variables_candidato.codigo_municipio_contexto,estado_contexto_municipal,distancia_minima_geometria_m
            FROM gold_variables_candidato JOIN gold_candidatos USING(candidato_id)
            WHERE fid_origen=2 AND escenario='principal_admitida' ''').fetchone()
        self.assertEqual(rows,(None,'interseccion_multiple',0.0))
        self.assertNotIn('vehiculos_distintivo_0',[r[0] for r in self.c.execute('DESCRIBE gold_variables_candidato').fetchall()])

    def test_border_uses_full_geometry_and_excludes_internal_boundaries(self):
        self.build()
        self.assertEqual(self.c.execute('''SELECT distancia_geometria_borde_cv_m,posible_influencia_exterior_geometria
            FROM gold_variables_candidato JOIN gold_candidatos USING(candidato_id)
            WHERE fid_origen=2 AND escenario='principal_admitida' ''').fetchone(),(4.0,False))
        self.assertEqual(self.c.execute('''SELECT distancia_geometria_borde_cv_m FROM gold_variables_candidato
            JOIN gold_candidatos USING(candidato_id) WHERE fid_origen=1 LIMIT 1''').fetchone()[0],5.0)
        self.assertEqual(self.c.execute('''SELECT count(*) FROM gold_variables_candidato v JOIN gold_candidatos x USING(candidato_id)
            CROSS JOIN borde_cv b WHERE estado_distancia='calculable'
            AND abs(distancia_geometria_borde_cv_m-ST_Distance(x.geometria,b.geometria))>1e-8''').fetchone()[0],0)

    def test_missing_border_bound_is_rejected(self):
        self.inputs()
        self.c.execute("UPDATE gold_control_borde SET distancia_borde_cv_m=NULL WHERE escenario='principal_admitida'")
        with self.assertRaisesRegex(ValueError,'Cota de borde'):prepare(self.c,'vars')

    def test_boundary_only_area_retains_nulls(self):
        self.build()
        self.assertEqual(self.c.execute('''SELECT count(*) FROM gold_variables_candidato JOIN gold_candidatos USING(candidato_id)
            WHERE fid_origen=6 AND estado_distancia='sin_superficie_en_cv' AND distancia_minima_geometria_m IS NULL
            AND distancia_geometria_borde_cv_m IS NULL AND posible_influencia_exterior_geometria IS NULL
            AND proximidad_normalizada_log IS NULL AND estado_normalizacion='sin_valor' ''').fetchone()[0],3)

    def test_border_equality_does_not_raise_warning(self):
        self.c.execute("DELETE FROM gold_recarga_instalaciones WHERE instalacion_id IN ('A','B')")
        self.c.execute("UPDATE gold_recarga_instalaciones SET geometria=ST_Point(4,5)::GEOMETRY('EPSG:25830') WHERE instalacion_id='C'")
        self.build()
        self.assertEqual(self.c.execute('''SELECT distancia_minima_geometria_m,distancia_geometria_borde_cv_m,
            posible_influencia_exterior_geometria FROM gold_variables_candidato JOIN gold_candidatos USING(candidato_id)
            WHERE fid_origen=1 AND escenario='principal_admitida' ''').fetchone(),(5.0,5.0,False))

    def test_empty_offer_preserves_border_and_unknown_normalization(self):
        self.c.execute('DELETE FROM gold_recarga_instalaciones')
        self.build()
        self.assertEqual(self.c.execute('''SELECT count(*) FROM gold_variables_candidato WHERE estado_distancia='sin_recarga_admisible'
            AND distancia_geometria_borde_cv_m IS NOT NULL AND posible_influencia_exterior_geometria IS NULL
            AND proximidad_normalizada_log IS NULL''').fetchone()[0],12)
        self.assertEqual(self.c.execute("SELECT n_total,n_validos,n_nulos,estado_referencia FROM gold_referencias_normalizacion WHERE dimension='proximidad'").fetchone(),(5,0,5,'sin_valores_admisibles'))

    def test_zero_and_constant_positive_references_are_explicit(self):
        self.c.execute('UPDATE gold_municipios SET vehiculos_distintivo_0=0')
        self.build()
        self.assertEqual(self.c.execute('SELECT DISTINCT demanda_normalizada_log,demanda_normalizada_lineal,estado_normalizacion FROM gold_variables_municipio').fetchall(),[(0.0,0.0,'todos_cero')])
        self.assertEqual(self.c.execute('SELECT norma_log(5,5,5),norma_lineal(5,5,5),estado_norm(5,5,5)').fetchone(),(1.0,1.0,'sin_variacion_positiva'))

    def test_missing_negative_and_nonfinite_values_do_not_become_zero(self):
        self.c.execute("UPDATE gold_municipios SET vehiculos_distintivo_0=NULL WHERE codigo_municipio='03001'")
        self.build()
        self.assertEqual(self.c.execute("SELECT demanda_normalizada_log,estado_normalizacion FROM gold_variables_municipio WHERE codigo_municipio='03001'").fetchone(),(None,'sin_valor'))
        for value in (-1,float('nan'),float('inf')):
            self.assertEqual(self.c.execute('SELECT norma_log(?,0,30),estado_norm(?,0,30)',[value,value]).fetchone(),(None,'valor_no_admisible'))

    def test_outside_reference_and_absent_reference_are_not_clipped(self):
        self.build()
        self.assertEqual(self.c.execute('SELECT norma_log(31,0,30),norma_lineal(31,0,30),estado_norm(31,0,30)').fetchone(),(None,None,'fuera_referencia'))
        self.assertEqual(self.c.execute('SELECT norma_log(1,NULL,NULL),estado_norm(1,NULL,NULL)').fetchone(),(None,'sin_referencia'))

    def test_non_admitted_offer_geometry_is_excluded(self):
        self.c.execute("UPDATE gold_recarga_instalaciones SET estado_geometria='no_admitida' WHERE instalacion_id='H'")
        self.build()
        self.assertEqual(self.c.execute('''SELECT distancia_minima_geometria_m FROM gold_variables_candidato JOIN gold_candidatos USING(candidato_id)
            WHERE fid_origen=1 AND escenario='incluye_ausentes_historicas' ''').fetchone()[0],1.0)

    def test_tampered_normalization_rejected(self):
        self.build()
        self.c.execute('UPDATE gold_variables_municipio SET demanda_normalizada_log=0.5')
        with self.assertRaisesRegex(ValueError,'Normalización numérica'):validate(self.c,'vars')

    def test_tampered_border_warning_rejected(self):
        self.build()
        self.c.execute('''UPDATE gold_variables_candidato SET posible_influencia_exterior_geometria=NOT posible_influencia_exterior_geometria
            WHERE estado_distancia='calculable' ''')
        with self.assertRaisesRegex(ValueError,'Geometría o contexto'):validate(self.c,'vars')

    def test_tampered_reference_rejected(self):
        self.build()
        self.c.execute("UPDATE gold_referencias_normalizacion SET maximo=99 WHERE dimension='demanda'")
        with self.assertRaisesRegex(ValueError,'Referencia de normalización'):validate(self.c,'vars')

    def test_missing_scenario_rejected(self):
        self.build()
        self.c.execute("DELETE FROM gold_variables_candidato WHERE escenario='principal_admitida'")
        with self.assertRaisesRegex(ValueError,'Cobertura'):validate(self.c,'vars')

    def test_export_roundtrip_and_refuse_overwrite(self):
        self.build()
        target=self.root/'variables'
        self.assertEqual(len(write_outputs(self.c,target,KEYS)),3)
        self.assertEqual(self.c.execute('SELECT count(*) FROM read_parquet(?)',[str(target/'gold_variables_candidato.parquet')]).fetchone()[0],15)
        with self.assertRaises(FileExistsError):write_outputs(self.c,target,KEYS)

    def test_loader_rejects_path_and_incompatible_gold(self):
        directory=self.root/'resultados/gold/controles_espaciales';target=directory/'run';target.mkdir(parents=True)
        pointer={'ejecucion':'run','manifiesto':'../otro/manifiesto.json','informe':'run/informe.json'}
        (directory/'actual.json').write_text(json.dumps(pointer),encoding='utf-8')
        parent=([],{'gold/contexto_municipal':{'version_gold':'ctx'}},{'version_gold':'cand'})
        with patch('preparar_variables_gold.load_candidate_inputs',return_value=parent):
            with self.assertRaisesRegex(ValueError,'fuera de su ejecución'):load_inputs(self.c,self.root)
            pointer['manifiesto']='run/manifiesto.json'
            (directory/'actual.json').write_text(json.dumps(pointer),encoding='utf-8')
            (target/'manifiesto.json').write_text(json.dumps({'version_gold':'run','versiones_gold':{}}),encoding='utf-8')
            (target/'informe.json').write_text(json.dumps({'version_gold':'run','estado':'preparada_con_limitaciones'}),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'incompatibles'):load_inputs(self.c,self.root)

    def test_loader_checks_output_hash_before_reading(self):
        directory=self.root/'resultados/gold/controles_espaciales';target=directory/'run';target.mkdir(parents=True)
        (directory/'actual.json').write_text(json.dumps({'ejecucion':'run','manifiesto':'run/manifiesto.json','informe':'run/informe.json'}),encoding='utf-8')
        manifest={'version_gold':'run','versiones_gold':{'contexto_municipal':'ctx','candidatos':'cand'},
                  'salidas':[{'archivo':'gold_control_area_recarga.parquet','filas':0,'bytes':3,'sha256':'incorrecta'}]}
        (target/'manifiesto.json').write_text(json.dumps(manifest),encoding='utf-8')
        (target/'informe.json').write_text(json.dumps({'version_gold':'run','estado':'preparada_con_limitaciones'}),encoding='utf-8')
        (target/'gold_control_area_recarga.parquet').write_bytes(b'abc')
        with patch('preparar_variables_gold.load_candidate_inputs',return_value=([],
                {'gold/contexto_municipal':{'version_gold':'ctx'}},{'version_gold':'cand'})):
            with self.assertRaisesRegex(ValueError,'Entrada distinta'):load_inputs(self.c,self.root)


if __name__=='__main__':
    unittest.main()
