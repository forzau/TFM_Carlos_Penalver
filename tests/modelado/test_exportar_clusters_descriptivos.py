"""Los gráficos conservan posiciones, ceros, tamaños y límites compartidos."""

import contextlib
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np

from src.modelado.pasos import exportar_imagenes as _exportar_imagenes
from src.modelado.historico.ejecutar_comparacion_con_imagenes import main, ROOT


class GraficasTest(unittest.TestCase):
    def test_no_mueve_ni_pierde_coincidentes_y_comparte_limites(self):
        x = np.asarray([[0., 0.], [0., 0.], [100., 20.], [1000., 200.]])
        z = np.log1p(x)
        filas = [dict(codigo_municipio=str(i), perfil=str(int(i >= 2)),
                      **dict(zip(_exportar_imagenes.VARIABLES, a)), **dict(zip(_exportar_imagenes.Z, b))) for i, (a, b) in enumerate(zip(x, z))]
        rangos = _exportar_imagenes.limites(x), _exportar_imagenes.limites(z)
        for metodo in ('kmeans', 'gmm'):
            centros = (np.asarray([[0, 0], [550, 110]]), np.asarray([z[:2].mean(axis=0), z[2:].mean(axis=0)]))
            fig = _exportar_imagenes.dibujar(filas, {'metodo': metodo, 'k': 2}, *rangos, *centros)
            for ax, esperado, rango in zip(fig.axes, (x, z), rangos):
                self.assertTrue(np.array_equal(np.concatenate([a.get_offsets() for a in ax.collections[:-1]]), esperado))
                self.assertTrue(np.array_equal(ax.collections[-1].get_offsets(), centros[0 if ax is fig.axes[0] else 1]))
                self.assertEqual(ax.get_xlim(), rango[0])
                self.assertEqual(ax.get_ylim(), rango[1])
            salida = io.BytesIO()
            fig.savefig(salida, format='png', dpi=40)
            self.assertTrue(salida.getvalue().startswith(b'\x89PNG\r\n\x1a\n'))
            self.assertIn('n=2', fig.legends[0].get_texts()[0].get_text())
            plt.close(fig)

    def test_rechaza_coordenadas_invalidas_y_codigos_duplicados(self):
        fila = dict(codigo_municipio='a', perfil='0', **dict(zip(_exportar_imagenes.VARIABLES, (0, 0))), **dict(zip(_exportar_imagenes.Z, (0, 0))))
        for filas in ([fila, fila], [dict(fila, z_log1p_puntos=float('nan'))]):
            with self.assertRaises(AssertionError): _exportar_imagenes.dibujar(filas, {'metodo': 'gmm', 'k': 2}, [(0, 1)] * 2, [(0, 1)] * 2, np.zeros((2, 2)), np.zeros((2, 2)))

    def test_seis_grupos_leyenda_no_se_solapa_con_titulos_de_ejes(self):
        filas = [dict(codigo_municipio=str(i), perfil=str(i),
                      **dict(zip(_exportar_imagenes.VARIABLES, (i, i))), **dict(zip(_exportar_imagenes.Z, (i, i)))) for i in range(6)]
        centros = np.asarray([(i, i) for i in range(6)])
        fig = _exportar_imagenes.dibujar(filas, {'metodo': 'gmm', 'k': 6}, [(0, 6)] * 2, [(0, 6)] * 2, centros, centros)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        leyenda = fig.legends[0].get_window_extent(renderer)
        for ax in fig.axes:
            self.assertFalse(leyenda.overlaps(ax.xaxis.label.get_window_extent(renderer)))
        plt.close(fig)

    def test_centros_guardados_e_inversa_no_sustituidos_por_medias_originales(self):
        media, escala = np.array([1., 2.]), np.array([.5, 2.])
        esperados = np.array([[1., 9.], [9., 25.]])
        centros = (np.log1p(esperados) - media) / escala
        for metodo in ('kmeans', 'gmm'):
            modelo = SimpleNamespace(n_features_in_=2, cluster_centers_=centros, means_=centros[::-1])
            paquete = dict(modelo=modelo, variables=_exportar_imagenes.VARIABLES, z=_exportar_imagenes.Z,
                           preparacion={'media_log1p': media, 'escala': escala})
            originales, transformados = _exportar_imagenes.centros_del_modelo(paquete, {'metodo': metodo, 'k': 2})
            self.assertTrue(np.allclose(originales, esperados if metodo == 'kmeans' else esperados[::-1]))
            self.assertTrue(np.array_equal(transformados, centros if metodo == 'kmeans' else centros[::-1]))
            paquete['preparacion']['escala'] = [0, 1]
            with self.assertRaises(AssertionError): _exportar_imagenes.centros_del_modelo(paquete, {'metodo': metodo, 'k': 2})

    def test_nueva_ejecucion_exporta_solo_carpeta_devuelta_por_productor(self):
        carpeta = 'resultados/modelado/comparacion_descriptiva/prueba'
        respuesta = type('Proceso', (), {'stdout': 'progreso\n' + json.dumps({'carpeta': carpeta}) + '\n', 'stderr': ''})()
        with patch('src.modelado.historico.ejecutar_comparacion_con_imagenes.subprocess.run', return_value=respuesta) as correr, \
             patch('src.modelado.pasos.exportar_imagenes.exportar', return_value=ROOT / carpeta / 'imagenes_clusters') as exportar, \
             contextlib.redirect_stdout(io.StringIO()):
            main()
        self.assertTrue(correr.call_args.kwargs['check'])
        exportar.assert_called_once_with(ROOT / carpeta)


if __name__ == '__main__':
    unittest.main()
