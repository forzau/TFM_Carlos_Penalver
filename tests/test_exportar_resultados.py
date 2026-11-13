"""La selección pública excluye bases completas y conserva los informes anteriores ante errores."""

import json
import tempfile
import unittest
from pathlib import Path

from src.exportar_resultados import BASELINE, COMPARACION, COPIAS, IMAGENES, PREPARACION, exportar, sello


class ExportarResultadosTests(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.root = Path(temporal.name)
        def escribir(ruta, datos):
            path = self.root / ruta
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(datos), encoding='utf-8')
        entrada = {'filas': 3, 'esquema': [{'campo': 'id', 'tipo': 'VARCHAR'}], 'clave': ['id']}
        escribir(PREPARACION, {'ejecucion': 'ejemplo', 'estado': 'preparada_con_limitaciones',
                              'tablas': {'silver/territorio': {'municipios': entrada}},
                              'entorno': {}, 'limitaciones': ['ejemplo']})
        escribir(BASELINE + '/resultados.json', {'resumen': {'n_municipios': 3}, 'limites': ['ejemplo']})
        escribir(COMPARACION + '/protocolo.json', {
            'diseno': 'descriptivo_sin_separacion', 'n_municipios': 3, 'n_reservados': 0,
            'entradas': ['a', 'b'], 'preparacion': 'log1p', 'metodos': ['kmeans', 'gmm'],
            'k': [2, 3, 4, 5, 6], 'parametros': {}, 'n_ajustes': 160})
        for origen in COPIAS.values():
            path = self.root / origen
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'contenido de ejemplo')
        escribir(IMAGENES + '/manifiesto_imagenes.json', {
            'configuraciones': [{'imagen': {'ruta': ruta, **sello(self.root / ruta)}}
                                for ruta in COPIAS.values() if ruta.endswith('.png')]})
        escribir(COMPARACION + '/datos_restringidos.json', {'privado': True})

    def test_solo_exporta_seleccion_agregada_y_conserva_huellas(self):
        destino = exportar(self.root)
        self.assertFalse((destino / 'datos_restringidos.json').exists())
        self.assertFalse(list(destino.rglob('*.parquet')))
        for relativa, origen in COPIAS.items():
            self.assertEqual((destino / relativa).read_bytes(), (self.root / origen).read_bytes())
        manifiesto = json.loads((destino / 'procedencia.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifiesto['salidas']), len(COPIAS) + 5)
        for entrada in manifiesto['salidas']:
            self.assertEqual(sello(destino / entrada['ruta']), {k: entrada[k] for k in ('bytes', 'sha256')})
        esquema = json.loads((destino / 'preparacion/esquemas.json').read_text(encoding='utf-8'))
        self.assertEqual(esquema[0]['clave'], ['id'])

    def test_imagen_cambiada_se_rechaza_sin_sustituir_informes(self):
        destino = exportar(self.root)
        previo = (destino / 'procedencia.json').read_bytes()
        (self.root / IMAGENES / 'kmeans_k6.png').write_bytes(b'cambiada')
        with self.assertRaises(ValueError):
            exportar(self.root)
        self.assertEqual((destino / 'procedencia.json').read_bytes(), previo)

    def test_fuente_ausente_no_deja_publicacion_parcial(self):
        (self.root / PREPARACION).unlink()
        with self.assertRaises(FileNotFoundError):
            exportar(self.root)
        self.assertFalse((self.root / 'resultados/informes').exists())

    def test_manifiesto_incompleto_no_admite_figuras_sin_verificar(self):
        (self.root / IMAGENES / 'manifiesto_imagenes.json').write_text(
            json.dumps({'configuraciones': []}), encoding='utf-8')
        with self.assertRaises(ValueError):
            exportar(self.root)
        self.assertFalse((self.root / 'resultados/informes').exists())


if __name__ == '__main__':
    unittest.main()
