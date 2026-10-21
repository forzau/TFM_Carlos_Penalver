import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from comparar_sensibilidad_gold import SCENARIOS, prepare, load_inputs


class SensitivityGoldTests(unittest.TestCase):
    def setUp(self):
        self.c=duckdb.connect()
        self.addCleanup(self.c.close)
        self.c.execute('''CREATE TABLE gold_variables_municipio AS SELECT codigo codigo_municipio,
            x::BIGINT vehiculos_distintivo_0,ln(1+x)/ln(11) demanda_normalizada_log,
            x/10.0 demanda_normalizada_lineal FROM (VALUES ('03014',0),('46250',10)) t(codigo,x)''')
        self.c.execute("CREATE TABLE gold_municipios AS SELECT codigo_municipio,'Municipio'::VARCHAR nombre_municipio FROM gold_variables_municipio")
        self.c.execute('''CREATE TABLE gold_candidatos AS SELECT id candidato_id,nombre nombre_origen,representacion,
            'aparcamiento'::VARCHAR grupo_uso,codigo codigo_municipio_contexto FROM
            (VALUES ('A','Sitio A','punto','03014'),('B','Sitio B','area',NULL),
                ('C','Sitio C','punto','46250'),('D','Sitio D','area','46250')) t(id,nombre,representacion,codigo)''')
        self.c.execute('''CREATE TABLE gold_variables_candidato(candidato_id VARCHAR,escenario VARCHAR,
            distancia_minima_geometria_m DOUBLE,proximidad_normalizada_log DOUBLE,proximidad_normalizada_lineal DOUBLE)''')
        values=[(10,10,5,0),(10,4,5,0),(10,4,1,0)]
        for scenario, distances in zip(SCENARIOS,values):
            self.c.executemany('INSERT INTO gold_variables_candidato VALUES (?,?,?,?,?)',
                [(id,scenario,d,math.log1p(d)/math.log1p(10),d/10) for id,d in zip('ABCD',distances)])

    def transition(self, results, base=SCENARIOS[0], alternative=SCENARIOS[1]):
        return next(x for x in results['cambios_escenario'] if x['escenario_base']==base and x['escenario_alternativo']==alternative)

    def test_monotonic_scales_keep_order(self):
        results=prepare(self.c)
        self.assertTrue(all(x['puestos_distintos']==0 for x in results['orden_entre_escalas']))
        row=next(x for x in results['distribuciones'] if x['dimension']=='demanda')
        self.assertEqual(row['observaciones'],2)
        self.assertEqual(row['ceros'],1)

    def test_paired_reductions_keep_zero_denominators(self):
        results=prepare(self.c);row=self.transition(results)
        self.assertEqual((row['candidatos'],row['pares_conocidos'],row['distancias_cambian'],row['reduccion_maxima_m']),(4,4,1,6.0))
        self.assertEqual(row['reduccion_mediana_todos_m'],0.0)
        self.assertEqual(row['reduccion_mediana_afectados_m'],6.0)
        example=next(x for x in results['ejemplos'] if x['escenario_base']==SCENARIOS[0] and x['escenario_alternativo']==SCENARIOS[1])
        self.assertEqual(example['fraccion_reduccion_distancia'],0.6)
        self.assertIsNone(example['nombre_municipio'])

    def test_ties_are_included_without_breaking_by_id(self):
        row=self.transition(prepare(self.c))
        self.assertEqual((row['grupo_superior_base'],row['grupo_superior_alternativo'],row['interseccion_grupos']),(2,1,1))
        self.assertEqual(row['jaccard_grupos'],0.5)
        self.assertEqual(row['puestos_cambian'],3)
        self.assertAlmostEqual(row['spearman'],3/math.sqrt(22.5))

    def test_incremental_and_total_scenarios_separate(self):
        results=prepare(self.c)
        self.assertEqual(self.transition(results,SCENARIOS[1],SCENARIOS[2])['distancias_cambian'],1)
        self.assertEqual(self.transition(results,SCENARIOS[0],SCENARIOS[2])['distancias_cambian'],2)

    def test_constant_data_has_unknown_correlation(self):
        self.c.execute('''UPDATE gold_variables_candidato SET distancia_minima_geometria_m=0,
            proximidad_normalizada_log=0,proximidad_normalizada_lineal=0''')
        row=self.transition(prepare(self.c))
        self.assertIsNone(row['spearman'])
        self.assertEqual(row['jaccard_grupos'],1.0)
        self.assertEqual(row['distancias_cambian'],0)

    def test_unknown_pairs_not_imputed_or_ranked(self):
        self.c.execute('''UPDATE gold_variables_candidato SET distancia_minima_geometria_m=NULL,
            proximidad_normalizada_log=NULL,proximidad_normalizada_lineal=NULL WHERE candidato_id='B' ''')
        row=self.transition(prepare(self.c))
        self.assertEqual((row['pares_conocidos'],row['pares_desconocidos']),(3,1))
        self.assertEqual(row['distancias_cambian'],0)

    def test_all_unknown_has_no_artificial_zero_effect(self):
        self.c.execute('''UPDATE gold_variables_candidato SET distancia_minima_geometria_m=NULL,
            proximidad_normalizada_log=NULL,proximidad_normalizada_lineal=NULL''')
        row=self.transition(prepare(self.c))
        self.assertEqual(row['pares_conocidos'],0)
        self.assertIsNone(row['reduccion_mediana_todos_m'])
        self.assertIsNone(row['jaccard_grupos'])
        self.assertIsNone(row['spearman'])

    def test_missing_scenario_is_rejected(self):
        self.c.execute("DELETE FROM gold_variables_candidato WHERE candidato_id='A' AND escenario=?",[SCENARIOS[0]])
        with self.assertRaisesRegex(ValueError,'Cohorte'):prepare(self.c)

    def test_invalid_values_rejected(self):
        self.c.execute('UPDATE gold_variables_candidato SET proximidad_normalizada_log=2')
        with self.assertRaisesRegex(ValueError,'no admisible'):prepare(self.c)

    def test_amplification_cannot_increase_distance(self):
        self.c.execute('UPDATE gold_variables_candidato SET distancia_minima_geometria_m=9 WHERE candidato_id=? AND escenario=?',['C',SCENARIOS[1]])
        with self.assertRaisesRegex(ValueError,'ampliación'):prepare(self.c)

    def test_loader_rejects_manifest_outside_block(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);directory=root/'resultados/gold/contexto_municipal';directory.mkdir(parents=True)
            (directory/'actual.json').write_text(json.dumps({'ejecucion':'run','manifiesto':'../../fuera/manifiesto.json'}),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'fuera del bloque'):load_inputs(self.c,root)


if __name__=='__main__':
    unittest.main()
