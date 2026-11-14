"""Controles del piloto: ámbito, cardinalidad, denominador cero y selección sin oferta."""

import unittest
from pathlib import Path

from src.modelado.historico.comprobar_utilidad_segmentacion import unir_oferta, validar_desarrollo, vecinos


def municipio(codigo, z=0, grupo=0, puntos=0):
    return dict(codigo_municipio=codigo, version_gold='v', grupo=grupo,
                vehiculos_distintivo_0=4, proporcion_distintivo_0=.01,
                renta_modelado_2023_eur='14000', z_log1p_volumen=z,
                z_proporcion=0, z_renta=0, instalaciones=puntos, puntos=puntos,
                conectores=puntos, pendientes=0, ausentes=0, presion=4/puntos if puntos else None)


class UtilidadTest(unittest.TestCase):
    def test_no_admite_prueba_ni_duplicados(self):
        particiones = [dict(codigo_municipio='a', conjunto='desarrollo'),
                       dict(codigo_municipio='b', conjunto='prueba_final')]
        validar_desarrollo([municipio('a')], particiones)
        for filas in ([municipio('a'), municipio('a')], [municipio('a'), municipio('b')], []):
            with self.assertRaises(AssertionError):
                validar_desarrollo(filas, particiones)

    def test_join_rechaza_duplicados_ausencias_y_version_distinta(self):
        base = municipio('a')
        for oferta in ([], [base, base], [{**base, 'version_gold': 'otra'}]):
            with self.assertRaises(AssertionError):
                unir_oferta([base], oferta)

    def test_presion_cero_puntos_conserva_nulo(self):
        base = municipio('a')
        self.assertIsNone(unir_oferta([base], [base])[0]['presion'])
        for presion in (0, float('inf')):
            with self.assertRaises(AssertionError):
                unir_oferta([base], [{**base, 'presion': presion}])
        con_puntos = municipio('a', puntos=2)
        self.assertEqual(unir_oferta([con_puntos], [con_puntos])[0]['presion'], 2)

    def test_vecinos_excluye_ancla_y_otro_grupo_y_desempata_por_codigo(self):
        ancla = municipio('a')
        filas = [ancla, municipio('c', z=1), municipio('b', z=-1), municipio('d', grupo=1)]
        self.assertEqual([f['codigo_municipio'] for _, f in vecinos(ancla, filas)], ['b', 'c'])

    def test_oferta_no_cambia_seleccion(self):
        ancla, b, c = municipio('a'), municipio('b', z=.1), municipio('c', z=.2)
        antes = [f['codigo_municipio'] for _, f in vecinos(ancla, [ancla, b, c])]
        b['puntos'], c['puntos'] = 1000, 0
        self.assertEqual(antes, [f['codigo_municipio'] for _, f in vecinos(ancla, [ancla, b, c])])


if __name__ == '__main__':
    unittest.main()
