import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from comparar_recarga import INSTALL, compare, impact, missing_matches, snapshot
from test_recarga import export, row


class CompareChargingTests(unittest.TestCase):
    def test_changes_additions_removals_and_order(self):
        summary, detail = compare({'a': ('igual',), 'b': ('antes',), 'c': ('sale',)},
                                  {'d': ('entra',), 'b': ('ahora',), 'a': ('igual',)}, ['campo'])
        self.assertEqual((summary['comunes'], summary['sin_cambios'], summary['modificadas']), (2, 1, 1))
        self.assertEqual(summary['cambios_por_campo'], {'campo': 1})
        self.assertEqual(detail['solo_original'], ['c'])
        self.assertEqual(detail['solo_adquirida_18_10'], ['d'])
        self.assertEqual(detail['modificadas'][0]['campos']['campo']['original'], 'antes')

    def test_scope_preserves_national_presence_and_rejects_duplicate_cv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'raw.csv'
            outside = row(); outside[0:3] = ['Comunidad de Madrid', 'Madrid', 'Madrid']
            outside[14] = 'fuera'
            export(path, [row(), outside, outside])
            result = snapshot(path)
            self.assertEqual(result['perfil']['filas_nacionales'], 3)
            self.assertEqual(result['perfil']['claves_repetidas_nacionales'], 1)
            self.assertEqual(result['perfil']['conectores'], 1)
            self.assertIn('fuera', result['ids_nacionales'])
            export(path, [row(), row()])
            with self.assertRaisesRegex(ValueError, 'repetida en CV'):
                snapshot(path)
            bad = row(); bad[1] = 'Madrid'
            export(path, [bad])
            with self.assertRaisesRegex(ValueError, 'incoherentes'):
                snapshot(path)

    def test_identity_change_blocks_reuse_but_schedule_alone_does_not(self):
        values = tuple(row()[i] for i in INSTALL.values())
        old = {'instalaciones': {'a': values, 'b': values, 'c': values, 'd': values}}
        changed = list(values); changed[list(INSTALL).index('latitud_origen')] = '38.4'
        schedule = list(values); schedule[list(INSTALL).index('tipo_horario_origen')] = 'otro'
        new = {'instalaciones': {'a': tuple(changed), 'b': tuple(schedule)}, 'ids_nacionales': {'a', 'b', 'c'}}
        result = {r['instalacion_id']: r for r in impact(old, new, {'a': '03014'}, {'a'})}
        self.assertEqual(result['a']['estado'], 'revisar_identidad_o_ubicacion')
        self.assertTrue(result['a']['revision_documental_original'])
        self.assertEqual(result['b']['estado'], 'identidad_y_ubicacion_iguales')
        self.assertEqual(result['c']['estado'], 'fuera_cv_en_nueva')
        self.assertEqual(result['d']['estado'], 'ausente_exportacion_nacional')

    def test_missing_matches_are_exact_diagnostics_without_merging(self):
        values = tuple(row()[i] for i in INSTALL.values())
        old = {'instalaciones': {'a': values}, 'puntos': {('a', 'p'): ()},
               'conectores': {('a', 'p', '1'): ()}}
        new = {'instalaciones': {'b': values}, 'puntos': {('b', 'p'): ()}}
        result = missing_matches(old, new)[0]
        self.assertEqual(result['otras_instalaciones_misma_coordenada_literal'], ['b'])
        self.assertEqual(result['puntos_id_compartidos_con_nueva'], {'b': 1})
        self.assertEqual(result['conectores_originales'], 1)


if __name__ == '__main__':
    unittest.main()
