import sys
import json
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import test_gold_candidatos as candidate_tests
from preparar_controles_gold import KEYS, prepare, validate, load_inputs
from preparar_recarga_versionada import write_outputs


class SpatialGoldControlsTests(unittest.TestCase):
    def setUp(self):
        base = candidate_tests.CandidateGoldTests('test_empty_offer_is_explicit_and_keeps_candidates')
        base.setUp()
        self.addCleanup(base.doCleanups)
        base.build()
        self.c,self.root = base.c,base.root
        self.c.execute('DROP TABLE ambito_cv')
        self.c.execute("ALTER TABLE gold_municipios ADD COLUMN geometria GEOMETRY('EPSG:25830')")
        self.c.execute('''UPDATE gold_municipios m SET geometria=r.geometria
            FROM recintos_municipales r WHERE m.codigo_municipio=r.codigo_municipio''')

    def build(self):
        prepare(self.c,'control')
        return validate(self.c,'control')

    def area(self,candidate,wkt,px,py):
        self.c.execute('''INSERT INTO gold_candidatos SELECT * REPLACE (?::VARCHAR AS candidato_id,
            ST_GeomFromText(?)::GEOMETRY('EPSG:25830') AS geometria,
            ST_Point(?,?)::GEOMETRY('EPSG:25830') AS punto_representativo) FROM gold_candidatos WHERE fid_origen=2''',[candidate,wkt,px,py])
        self.c.execute('''INSERT INTO gold_proximidad_candidato_recarga SELECT * REPLACE (?::VARCHAR AS candidato_id)
            FROM gold_proximidad_candidato_recarga WHERE candidato_id=(SELECT candidato_id FROM gold_candidatos WHERE fid_origen=2 LIMIT 1)''',[candidate])

    def test_area_ids_separate_scenarios_and_count_boundary_contact(self):
        self.build()
        rows=self.c.execute('''SELECT escenario,instalaciones_intersectan,instalaciones_ids FROM gold_control_area_recarga
            JOIN gold_candidatos USING(candidato_id) WHERE fid_origen=2 ORDER BY escenario''').fetchall()
        self.assertEqual(rows,[('incluye_ausentes_historicas',4,['A','B','H','P']),
            ('incluye_pendientes',3,['A','B','P']),('principal_admitida',2,['A','B'])])

    def test_empty_area_lists_and_no_control_rows_for_points(self):
        self.build()
        self.assertEqual(self.c.execute('''SELECT count(*) FROM gold_control_area_recarga r JOIN gold_candidatos c USING(candidato_id)
            WHERE c.fid_origen=6 AND r.instalaciones_intersectan=0 AND r.instalaciones_ids=[]''').fetchone()[0],3)
        self.assertEqual(self.c.execute('''SELECT count(*) FROM gold_control_area_recarga JOIN gold_candidatos USING(candidato_id)
            WHERE representacion='punto' ''').fetchone()[0],0)

    def test_nested_same_category_areas_kept_without_merging(self):
        self.area('nested','POLYGON ((9 4.5,11 4.5,11 5.5,9 5.5,9 4.5))',10,5)
        self.build()
        row=self.c.execute('''SELECT a_cubre_b,b_cubre_a,dimension_interseccion,superficie_interseccion_m2
            FROM gold_solapamientos_candidatos WHERE candidato_a_id='nested'
            OR candidato_b_id='nested' ORDER BY dimension_interseccion DESC LIMIT 1''').fetchone()
        self.assertEqual(row[2:],(2,2.0))
        self.assertEqual(sum(row[:2]),1)
        self.assertEqual(self.c.execute('SELECT count(*) FROM gold_candidatos').fetchone()[0],6)

    def test_area_contact_is_line_not_positive_shared_surface(self):
        self.area('touch','POLYGON ((12 4,14 4,14 6,12 6,12 4))',13,5)
        self.build()
        self.assertEqual(self.c.execute('''SELECT dimension_interseccion,superficie_interseccion_m2,a_cubre_b,b_cubre_a
            FROM gold_solapamientos_candidatos WHERE candidato_a_id='touch' OR candidato_b_id='touch' ''').fetchone(),(1,None,False,False))

    def test_cross_category_point_area_pair_is_included_once(self):
        self.build()
        row=self.c.execute('''SELECT s.misma_categoria,s.dimension_interseccion FROM gold_solapamientos_candidatos s
            JOIN gold_candidatos a ON a.candidato_id=s.candidato_a_id JOIN gold_candidatos b ON b.candidato_id=s.candidato_b_id
            WHERE (a.fid_origen=3 AND b.fid_origen=4) OR (a.fid_origen=4 AND b.fid_origen=3)''').fetchall()
        self.assertEqual(row,[(False,0)])
        self.assertEqual(self.c.execute('SELECT count(*) FROM gold_solapamientos_candidatos WHERE candidato_a_id>=candidato_b_id').fetchone()[0],0)

    def test_union_border_excludes_internal_municipal_boundary(self):
        self.build()
        self.assertEqual(self.c.execute('''SELECT distancia_borde_cv_m,posible_influencia_exterior FROM gold_control_borde
            JOIN gold_candidatos USING(candidato_id) WHERE fid_origen=1 AND escenario='principal_admitida' ''').fetchone(),(5.0,False))

    def test_border_equality_is_not_warning_and_larger_distance_is(self):
        self.c.execute('''UPDATE gold_proximidad_candidato_recarga SET distancia_plana_m=5 WHERE candidato_id IN
            (SELECT candidato_id FROM gold_candidatos WHERE fid_origen=1) AND escenario='principal_admitida' ''')
        self.c.execute('''UPDATE gold_proximidad_candidato_recarga SET distancia_plana_m=6 WHERE candidato_id IN
            (SELECT candidato_id FROM gold_candidatos WHERE fid_origen=1) AND escenario='incluye_pendientes' ''')
        self.build()
        self.assertEqual(self.c.execute('''SELECT escenario,posible_influencia_exterior FROM gold_control_borde JOIN gold_candidatos USING(candidato_id)
            WHERE fid_origen=1 AND escenario<>'incluye_ausentes_historicas' ORDER BY escenario''').fetchall(),[('incluye_pendientes',True),('principal_admitida',False)])

    def test_no_position_retains_null_warning_and_three_states(self):
        self.build()
        self.assertEqual(self.c.execute('''SELECT count(*) FROM gold_control_borde JOIN gold_candidatos USING(candidato_id)
            WHERE fid_origen=6 AND distancia_borde_cv_m IS NULL AND posible_influencia_exterior IS NULL
            AND estado_control='sin_posicion_representativa' ''').fetchone()[0],3)

    def test_empty_offer_does_not_turn_unknown_border_into_false(self):
        self.c.execute('DELETE FROM gold_recarga_instalaciones')
        self.c.execute("UPDATE gold_proximidad_candidato_recarga SET estado_distancia='sin_recarga_admisible',distancia_plana_m=NULL WHERE estado_distancia='calculable'")
        self.build()
        self.assertEqual(self.c.execute('''SELECT count(*) FROM gold_control_borde WHERE estado_control='sin_recarga_admisible'
            AND distancia_borde_cv_m IS NOT NULL AND posible_influencia_exterior IS NULL''').fetchone()[0],12)

    def test_missing_scenario_is_rejected(self):
        self.c.execute("DELETE FROM gold_proximidad_candidato_recarga WHERE escenario='principal_admitida'")
        with self.assertRaisesRegex(ValueError,'Escenarios'):self.build()

    def test_non_admitted_historical_geometry_excluded(self):
        self.c.execute("UPDATE gold_recarga_instalaciones SET estado_geometria='no_admitida' WHERE instalacion_id='H'")
        self.build()
        self.assertEqual(self.c.execute("SELECT count(*) FROM gold_control_area_recarga WHERE list_contains(instalaciones_ids,'H')").fetchone()[0],0)

    def input_files(self,manifest,selected=None):
        directory=self.root/'resultados/gold/candidatos';target=directory/'run';target.mkdir(parents=True)
        (directory/'actual.json').write_text(json.dumps(selected or {'ejecucion':'run','manifiesto':'run/manifiesto.json',
            'informe':'run/informe.json'}),encoding='utf-8')
        (target/'manifiesto.json').write_text(json.dumps(manifest),encoding='utf-8')
        (target/'informe.json').write_text(json.dumps({'version_gold':'run','estado':'preparada_con_limitaciones'}),encoding='utf-8')

    def test_loader_rejects_pointer_outside_its_block(self):
        self.input_files({}, {'ejecucion':'run','manifiesto':'../../otro/manifiesto.json','informe':'run/informe.json'})
        with patch('preparar_controles_gold.load_candidate_inputs',return_value=([],{})):
            with self.assertRaisesRegex(ValueError,'fuera de su ejecución'):load_inputs(self.c,self.root)

    def test_loader_rejects_incompatible_parent_gold(self):
        self.input_files({'version_gold':'run','ejecuciones':{'gold/contexto_municipal':'otro'}})
        with patch('preparar_controles_gold.load_candidate_inputs',return_value=([],{'gold/contexto_municipal':{'version_gold':'ctx'}})):
            with self.assertRaisesRegex(ValueError,'incompatibles'):load_inputs(self.c,self.root)

    def test_loader_checks_output_hash_before_using_data(self):
        self.input_files({'version_gold':'run','ejecuciones':{'gold/contexto_municipal':'ctx'},
            'salidas':[{'archivo':'gold_candidatos.parquet','filas':0,'bytes':3,'sha256':'incorrecta'}]})
        (self.root/'resultados/gold/candidatos/run/gold_candidatos.parquet').write_bytes(b'abc')
        with patch('preparar_controles_gold.load_candidate_inputs',return_value=([],{'gold/contexto_municipal':{'version_gold':'ctx'}})):
            with self.assertRaisesRegex(ValueError,'Entrada distinta'):load_inputs(self.c,self.root)

    def test_validation_rejects_omitted_overlap_and_tampered_area_ids(self):
        self.build()
        self.c.execute('DELETE FROM gold_solapamientos_candidatos')
        with self.assertRaisesRegex(ValueError,'Faltan solapamientos'):validate(self.c,'control')

    def test_validation_rejects_foreign_area_id(self):
        self.build()
        self.c.execute("UPDATE gold_control_area_recarga SET instalaciones_ids=['inexistente'],instalaciones_intersectan=1")
        with self.assertRaisesRegex(ValueError,'Coincidencias de área'):validate(self.c,'control')

    def test_validation_rejects_inverted_border_warning(self):
        self.build()
        self.c.execute("UPDATE gold_control_borde SET posible_influencia_exterior=NOT posible_influencia_exterior WHERE estado_control='calculable'")
        with self.assertRaisesRegex(ValueError,'Control de borde'):validate(self.c,'control')

    def test_export_lists_nulls_and_refuses_overwrite(self):
        self.build()
        target=self.root/'controles'
        self.assertEqual(len(write_outputs(self.c,target,KEYS)),3)
        self.assertEqual(self.c.execute('SELECT count(*) FROM read_parquet(?)',
            [str(target/'gold_control_area_recarga.parquet')]).fetchone()[0],9)
        with self.assertRaises(FileExistsError):write_outputs(self.c,target,KEYS)


if __name__=='__main__':
    unittest.main()
