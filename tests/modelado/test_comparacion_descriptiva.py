"""Contrato de dos entradas y ajuste descriptivo, también con ceros repetidos."""

import unittest
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from src.modelado.ejecutar_comparacion_descriptiva import ajustar, matriz, Z


def datos():
    posiciones = [(0., 0.)] * 12 + [(i / 100, 0.) for i in range(1, 8)] + [(2. + i / 100, 2.) for i in range(12)]
    return [dict(codigo_municipio=str(i), renta=999, **dict(zip(Z, p))) for i, p in enumerate(posiciones)]


class ComparacionTest(unittest.TestCase):
    def test_dos_entradas_cobertura_reproduccion_y_probabilidades(self):
        filas = datos()
        with threadpool_limits(limits=2):
            for metodo in ('kmeans', 'gmm'):
                m, e, info = ajustar(metodo, 2, 42, filas, filas)
                _, otras, _ = ajustar(metodo, 2, 42, filas, filas)
                self.assertEqual(e, otras)
                self.assertEqual(len(e), len(filas))
                self.assertEqual(m.n_features_in_, 2)
                self.assertEqual(info['k_observado_ajuste'], 2)
                if metodo == 'gmm':
                    self.assertTrue(info['convergencia'])
                    self.assertGreaterEqual(info['menor_autovalor_covarianza'], 1e-6 - 1e-12)
                    self.assertTrue(np.allclose(m.predict_proba(matriz(filas)).sum(axis=1), 1))
                self.assertEqual(m.predict(matriz(filas[:1]))[0], m.predict(matriz(filas))[0])

    def test_reasigna_tambien_los_omitidos_sin_usarlos_en_el_ajuste(self):
        filas = datos()
        with threadpool_limits(limits=2):
            _, etiquetas, info = ajustar('kmeans', 2, 42, filas[1:], filas)
        self.assertEqual(info['n_ajuste'], len(filas) - 1)
        self.assertIn('0', etiquetas)
        self.assertEqual(info['n_descripcion'], len(filas))

    def test_rechaza_codigos_ajenos_y_representaciones_incompatibles(self):
        filas = datos()
        for muestra in ([dict(filas[0], codigo_municipio='ajeno')], [dict(filas[0], **{Z[0]: 999})]):
            with self.assertRaises(AssertionError): ajustar('gmm', 2, 42, muestra, filas)
        for fs in ([filas[0], filas[0]], [dict(filas[0], **{Z[0]: float('nan')})]):
            with self.assertRaises(AssertionError): matriz(fs)

    def test_respeta_metodos_rango_y_posiciones_minimas(self):
        for metodo, k in (('otro', 2), ('kmeans', 1), ('gmm', 7)):
            with self.assertRaises(ValueError): ajustar(metodo, k, 42, datos(), datos())
        with self.assertRaises(AssertionError): ajustar('gmm', 2, 42, datos()[:10], datos()[:10])


if __name__ == '__main__':
    unittest.main()
