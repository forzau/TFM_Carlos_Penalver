"""Controles de fuga de información y contratos de métricas con datos sintéticos."""

import unittest
from decimal import Decimal
from pathlib import Path

import numpy as np

from src.modelado.historico.preparar_experimento_segmentacion import preparar, geometria, estabilidad_por_codigo


def fila(codigo, volumen, proporcion, renta, bloque):
    return {"codigo_municipio": codigo, "vehiculos_distintivo_0": volumen,
        "proporcion_distintivo_0": proporcion, "renta_modelado_2023_eur": renta,
        "bloque_espacial": bloque}


class PreparacionTest(unittest.TestCase):
    def test_valores_de_validacion_no_modifican_parametros_de_entrenamiento(self):
        train = [fila("12123", 1, .01, Decimal("15747.27"), "a"), fila("46226", 0, 0, None, "b")]
        val = [fila("03068", 8, .02, Decimal("15913.72"), "c")]
        antes = preparar(train, val)
        val[0]["renta_modelado_2023_eur"] = Decimal("9999999")
        val[0]["vehiculos_distintivo_0"] = 1000000
        despues = preparar(train, val)
        self.assertEqual(antes[2], despues[2])
        self.assertEqual(antes[0], despues[0])
        self.assertEqual(antes[2]["renta_sempere"], "15747.27")
        self.assertIsNone(train[1]["renta_modelado_2023_eur"])

    def test_sempere_en_validacion_usa_solo_donantes_de_entrenamiento(self):
        train = [fila("03068", 1, .01, Decimal("15913.72"), "a"), fila("03130", 2, .02, Decimal("15913.72"), "b")]
        _, val, parametros = preparar(train, [fila("46226", 0, 0, Decimal("1"), "c")])
        self.assertEqual(val[0]["renta_modelado_2023_eur"], Decimal("15913.72"))
        self.assertEqual(parametros["renta_sempere"], "15913.72")

    def test_sin_donantes_falla_sin_usar_la_renta_global(self):
        with self.assertRaises(ValueError):
            preparar([fila("00001", 1, .01, Decimal("12000"), "a")], [fila("46226", 0, 0, Decimal("15858.24"), "b")])

    def test_bloque_compartido_se_rechaza(self):
        with self.assertRaises(AssertionError):
            preparar([fila("00001", 1, .01, Decimal("12000"), "a")], [fila("00002", 2, .02, Decimal("13000"), "a")])

    def test_silhouette_no_calculable_no_se_convierte_en_cero(self):
        self.assertIsNone(geometria([[0], [1], [2]], [0, 0, 0])["silhouette"])
        self.assertIsNone(geometria([[0], [1], [2]], [0, 1, 2])["silhouette"])

    def test_silhouette_distingue_grupos_separados_de_mezclados(self):
        x = np.array([[0.0], [.1], [10.0], [10.1]])
        bueno = geometria(x, [0, 0, 1, 1])["silhouette"]
        malo = geometria(x, [0, 1, 0, 1])["silhouette"]
        self.assertGreater(bueno, .98)
        self.assertLess(malo, 0)

    def test_ari_alinea_codigos_y_acepta_renombrado(self):
        a = {"a": 0, "b": 0, "c": 1, "d": 1}
        b = {"d": 8, "c": 8, "b": 9, "a": 9}
        self.assertEqual(estabilidad_por_codigo(a, b), 1)
        with self.assertRaises(AssertionError):
            estabilidad_por_codigo(a, {"otro": 0})


if __name__ == "__main__":
    unittest.main()
