"""El director encadena resultados nuevos y se detiene antes de propagar errores."""

import io
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, call, patch

from src.modelado import flujo


class FlujoModeladoTest(unittest.TestCase):
    def test_comparacion_recibe_baseline_nuevo_y_verifica_antes_de_exportar(self):
        baseline = flujo.RAIZ / 'resultados/modelado/baseline_descriptivo/nuevo'
        comparacion = flujo.RAIZ / 'resultados/modelado/comparacion_descriptiva/nueva'
        imagenes = comparacion / 'imagenes_clusters/nuevas'
        with patch('src.modelado.pasos.baseline.main', return_value=baseline) as base, \
             patch('src.modelado.pasos.comparar_modelos.main', return_value=comparacion) as comparar, \
             patch('src.modelado.pasos.exportar_imagenes.exportar', return_value=imagenes) as exportar, \
             patch.object(flujo, 'verificar') as verificar:
            orden = Mock()
            for nombre, funcion in [('baseline', base), ('verificar', verificar),
                                    ('comparar', comparar), ('exportar', exportar)]:
                orden.attach_mock(funcion, nombre)
            resultado = flujo.reproducir()
        self.assertEqual(orden.mock_calls, [
            call.baseline(), call.verificar('baseline', baseline),
            call.comparar(baseline=baseline.relative_to(flujo.RAIZ).as_posix()),
            call.verificar('comparacion', comparacion), call.exportar(comparacion),
        ])
        self.assertEqual(resultado['imagenes'], imagenes.relative_to(flujo.RAIZ).as_posix())

    def test_verificacion_fallida_impide_comparar_y_exportar(self):
        with patch('src.modelado.pasos.baseline.main', return_value=flujo.RAIZ / 'nuevo'), \
             patch('src.modelado.pasos.comparar_modelos.main') as comparar, \
             patch('src.modelado.pasos.exportar_imagenes.exportar') as exportar, \
             patch.object(flujo, 'verificar', side_effect=subprocess.CalledProcessError(1, 'verificador')):
            with self.assertRaises(subprocess.CalledProcessError):
                flujo.reproducir()
        comparar.assert_not_called()
        exportar.assert_not_called()

    def test_modo_verificar_usa_referencias_sin_reproducir(self):
        with patch.object(flujo, 'reproducir') as reproducir, \
             patch.object(flujo, 'verificar') as verificar, redirect_stdout(io.StringIO()):
            flujo.main(['--verificar'])
        reproducir.assert_not_called()
        self.assertEqual(verificar.call_args_list, [
            call('baseline', flujo.RAIZ / flujo.BASELINE),
            call('comparacion', flujo.RAIZ / flujo.COMPARACION),
        ])

    def test_verificador_usa_interprete_actual_y_raiz_del_proyecto(self):
        carpeta = flujo.RAIZ / 'resultados/ejemplo'
        for tipo, modulo in [('baseline', '02_verificar_baseline'),
                             ('comparacion', '04_verificar_modelos')]:
            with self.subTest(tipo=tipo), patch.object(flujo.subprocess, 'run') as ejecutar:
                flujo.verificar(tipo, carpeta)
                ejecutar.assert_called_once_with(
                    [flujo.sys.executable, '-m', f'src.modelado.pasos.{modulo}', str(carpeta)],
                    cwd=flujo.RAIZ, check=True,
                )


if __name__ == '__main__':
    unittest.main()
