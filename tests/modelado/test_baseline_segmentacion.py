"""Reglas del baseline: medianas exclusivas de entrenamiento y empates juntos."""

import unittest
from pathlib import Path

from src.modelado.ejecutar_baseline_segmentacion import ajustar_medianas, asignar


def fila(codigo, volumen, proporcion, renta):
    return {"codigo_municipio": codigo, "vehiculos_distintivo_0": volumen,
        "proporcion_distintivo_0": proporcion, "renta_modelado_2023_eur": renta}


class BaselineTest(unittest.TestCase):
    def test_empates_y_duplicados_de_valores_quedan_en_inferior(self):
        train = [fila("a", 0, .01, 10000), fila("b", 0, .01, 10000), fila("c", 10, .02, 20000)]
        pred = asignar(train, ajustar_medianas(train))
        self.assertEqual(pred, {"a": "I-I-I", "b": "I-I-I", "c": "S-S-S"})

    def test_mediana_par_y_umbrales_fijos_en_validacion(self):
        cortes = ajustar_medianas([fila("a", 0, 0, 10000), fila("b", 10, .02, 20000)])
        self.assertEqual(list(cortes.values()), [5, .01, 15000])
        antes = cortes.copy()
        self.assertEqual(asignar([fila("c", 5, .01, 15000), fila("d", 10000, .5, 100000)], cortes), {"c": "I-I-I", "d": "S-S-S"})
        self.assertEqual(cortes, antes)

    def test_las_ocho_combinaciones_tienen_identificadores_distintos(self):
        cortes = ajustar_medianas([fila("a", 0, 0, 10000), fila("b", 2, .02, 20000)])
        filas = [fila(str(i*4+j*2+k), i*2, j*.02, 10000+k*10000) for i in (0,1) for j in (0,1) for k in (0,1)]
        self.assertEqual(len(set(asignar(filas, cortes).values())), 8)

    def test_codigos_duplicados_se_rechazan(self):
        rows = [fila("a", 0, .01, 10000), fila("a", 1, .02, 20000)]
        with self.assertRaises(AssertionError):
            asignar(rows, ajustar_medianas(rows))


if __name__ == "__main__":
    unittest.main()
