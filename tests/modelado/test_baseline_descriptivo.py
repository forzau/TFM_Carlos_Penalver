"""Inclusión sin reparto y robustez interna sobre el mismo universo."""

import unittest
from pathlib import Path

import numpy as np

from src.modelado.pasos import baseline as _baseline


def fila(codigo, coches=0, puntos=0, bloque=None):
    return dict(codigo_municipio=codigo, nombre_municipio=codigo, bloque_espacial=bloque or codigo,
                vehiculos_distintivo_0=coches, puntos_con_municipio_admitido=puntos,
                instalaciones_pendientes_relacionadas=0, instalaciones_ausentes_relacionadas=0,
                hay_incertidumbre_sin_localizar=False)


class DescriptivoTest(unittest.TestCase):
    def test_incluye_ambos_roles_anteriores_y_solo_excluye_lo_documentado(self):
        filas = [dict(fila('a'), conjunto='desarrollo'), dict(fila('b', 20), conjunto='prueba_final'), fila('x')]
        self.assertEqual([f['codigo_municipio'] for f in _baseline.seleccionar_universo(filas, {'x'})], ['a', 'b'])
        with self.assertRaises(AssertionError): _baseline.seleccionar_universo(filas, {'no_existe'})
        with self.assertRaises(AssertionError): _baseline.seleccionar_universo([filas[0], filas[0]], set())

    def test_ajuste_completo_usa_todas_las_observaciones_y_no_crea_validacion(self):
        universo = [fila('a'), fila('b', 4, 1), fila('c', 100, 10)]
        preparados, p = _baseline.representar(universo, universo)
        self.assertEqual((p['n_ajuste'], p['n_descripcion']), (3, 3))
        self.assertEqual(_baseline.ajustar(universo), 4)
        self.assertTrue(all('rol' not in f for f in preparados))
        self.assertTrue(np.allclose(np.mean([[f['z_log1p_vehiculos'], f['z_log1p_puntos']] for f in preparados], axis=0), 0))
        self.assertEqual(_baseline.asignar(preparados, 4), {'a': 'I-0', 'b': 'I-P', 'c': 'S-P'})

    def test_perturbacion_reasigna_universo_completo_con_corte_de_la_muestra(self):
        universo = [fila('a'), fila('b', 4), fila('c', 100)]
        muestra = universo[:2]
        preparados, p = _baseline.representar(muestra, universo)
        self.assertEqual((p['n_ajuste'], p['n_descripcion']), (2, 3))
        self.assertEqual(_baseline.ajustar(muestra), 2)
        self.assertEqual(set(_baseline.asignar(preparados, 2)), {'a', 'b', 'c'})
        self.assertEqual(p['escala'][1], 1)
        self.assertNotIn('rol', universo[0])

    def test_muestra_debe_pertenecer_al_universo_con_valores_identicos(self):
        universo = [fila('a'), fila('b', 4)]
        for muestra in ([fila('c')], [fila('a', 99)]):
            with self.assertRaises(AssertionError): _baseline.representar(muestra, universo)


if __name__ == '__main__':
    unittest.main()
