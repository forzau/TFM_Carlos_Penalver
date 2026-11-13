"""Comportamiento inductivo de los candidatos, sin datos de prueba reales."""

import unittest
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from src.modelado.ejecutar_comparacion_segmentacion import METODOS, Z, ajustar, crear_modelo, predecir


def filas(x, prefijo):
    return [dict(codigo_municipio=f"{prefijo}{i}", **dict(zip(Z, v))) for i, v in enumerate(x)]


class ModelosTest(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(23)
        self.train = filas(np.vstack([rng.normal(-3, .2, (20, 3)), rng.normal(3, .2, (20, 3))]), "t")
        self.val = filas([[-3, -3, -3], [3, 3, 3], [-2.9, -3, -3]], "v")

    def test_asignacion_inductiva_no_depende_del_resto_de_validacion(self):
        with threadpool_limits(limits=2):
            for metodo in METODOS:
                with self.subTest(metodo=metodo):
                    modelo, pred, _ = ajustar(metodo, 2, 31, self.train, self.val)
                    self.assertEqual(pred["v0"], pred["v2"])
                    self.assertNotEqual(pred["v0"], pred["v1"])
                    ampliada = self.val + filas([[1e6, -1e6, 1e6]], "otro")
                    self.assertEqual(pred, {k: v for k, v in predecir(modelo, ampliada).items() if k in pred})

    def test_semilla_reproduce_asignaciones_y_gmm_converge(self):
        with threadpool_limits(limits=2):
            for metodo in METODOS:
                a, p, info = ajustar(metodo, 2, 31, self.train, self.val)
                _, q, _ = ajustar(metodo, 2, 31, self.train, self.val)
                self.assertEqual(p, q)
                if metodo == "gmm":
                    self.assertTrue(info["convergencia_gmm"])
                    self.assertTrue(np.allclose(a.predict_proba(np.array([list(f[z] for z in Z) for f in self.val])).sum(axis=1), 1))

    def test_rechaza_codigo_de_validacion_presente_en_entrenamiento(self):
        with self.assertRaises(AssertionError):
            ajustar("kmeans", 2, 31, self.train, [self.train[0]])

    def test_rechaza_configuracion_no_acordada(self):
        for metodo, k in (("kmeans", 11), ("dbscan", 3)):
            with self.assertRaises(ValueError):
                crear_modelo(metodo, k, 31)


if __name__ == "__main__":
    unittest.main()
