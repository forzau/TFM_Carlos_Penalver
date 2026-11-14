"""Reglas de dos entradas y controles de entrenamiento, sin datos reales."""

import unittest
from pathlib import Path

import numpy as np

from src.modelado.historico.ejecutar_baseline_demanda_oferta import ajustar, asignar, preparar, planes_estabilidad, perfiles, sin_avisos
from src.modelado.historico.verificar_baseline_demanda_oferta import ari_contingencia, silhouette_directa


def fila(codigo, coches=0, puntos=0, bloque=None):
    return dict(codigo_municipio=codigo, nombre_municipio=codigo, bloque_espacial=bloque or codigo,
                vehiculos_distintivo_0=coches, puntos_con_municipio_admitido=puntos,
                instalaciones_pendientes_relacionadas=0, instalaciones_ausentes_relacionadas=0,
                hay_incertidumbre_sin_localizar=False)


class BaselineOfertaTest(unittest.TestCase):
    def test_verificador_metricas_con_soluciones_conocidas(self):
        x = np.array([[0.0], [.1], [10.0], [10.1]])
        self.assertAlmostEqual(np.mean(silhouette_directa(x, ['a', 'a', 'b', 'b'])), .9899997499937498, places=12)
        self.assertEqual(ari_contingencia(['a', 'a', 'b', 'b'], [8, 8, 9, 9]), 1)
        self.assertAlmostEqual(ari_contingencia(['a', 'a', 'b', 'b'], ['a', 'b', 'a', 'b']), -.5)

    def test_cuatro_reglas_empates_y_oferta_fija(self):
        corte = ajustar([fila('a', 0), fila('b', 10, 999)])
        self.assertEqual(corte, 5)
        datos = [fila('a', 5), fila('b', 5, 1), fila('c', 6), fila('d', 6, 900)]
        self.assertEqual(asignar(datos, corte), {'a': 'I-0', 'b': 'I-P', 'c': 'S-0', 'd': 'S-P'})
        self.assertEqual(ajustar([fila('a', 0, 1000), fila('b', 10)]), corte)

    def test_rechaza_ausencias_negativos_no_finitos_y_duplicados(self):
        for datos in ([], [fila('a'), fila('a')]):
            with self.assertRaises(AssertionError): ajustar(datos)
        for nombre in ('vehiculos_distintivo_0', 'puntos_con_municipio_admitido'):
            for valor in (None, -1, float('inf'), float('nan'), .5):
                f = fila('a'); f[nombre] = valor
                with self.subTest(nombre=nombre, valor=valor), self.assertRaises(AssertionError): ajustar([f])

    def test_validacion_no_cambia_preparacion_o_corte_y_constante_es_finita(self):
        train = [fila('a', 0), fila('b', 10)]
        val = [fila('c', 5, 1)]
        a, _, p = preparar(train, val)
        val[0]['vehiculos_distintivo_0'], val[0]['puntos_con_municipio_admitido'] = 1000000, 1000000
        b, v, q = preparar(train, val)
        self.assertEqual(a, b); self.assertEqual(p, q)
        self.assertEqual(p['escala'][1], 1)
        self.assertEqual(ajustar(a), 5)
        self.assertTrue(np.isfinite(v[0]['z_log1p_puntos']))
        self.assertNotIn('rol', train[0])

    def test_rechaza_filas_o_bloques_compartidos(self):
        for val in ([fila('a')], [fila('c', bloque='a')]):
            with self.assertRaises(AssertionError): preparar([fila('a'), fila('b')], val)

    def test_planes_reproducibles_completos_y_sin_donantes(self):
        train = [fila(str(i)) for i in range(12)]
        p = planes_estabilidad(train, 42)
        self.assertEqual(p, planes_estabilidad(list(reversed(train)), 42))
        self.assertEqual(len({tuple(x['bloques_omitidos']) for x in p}), 10)
        self.assertTrue(all(len(x['bloques_omitidos']) == 2 for x in p))
        with self.assertRaises(ValueError): planes_estabilidad([fila('a')], 42)

    def test_avisos_son_diagnostico_no_entrada_y_perfiles_no_requieren_renta(self):
        train = [fila('a'), fila('b', 10, 5)]
        a, _, p = preparar(train, [])
        train[0]['instalaciones_pendientes_relacionadas'] = 1
        b, _, q = preparar(train, [])
        self.assertEqual(p, q)
        self.assertFalse(sin_avisos(train[0]))
        self.assertEqual(asignar(a, 5), asignar(b, 5))
        self.assertEqual(sum(x['n'] for x in perfiles(b, asignar(b, 5))), 2)


if __name__ == '__main__':
    unittest.main()
