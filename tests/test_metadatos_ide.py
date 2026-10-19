import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from catalogar_bronze import fingerprint
from preparar_capacidad_demanda import RAW
from verificar_metadatos_ide import verify


class MetadatosIdeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.url = 'https://www.i-de.es/documents/d/guest/2026_09_04_r1-001_demanda-1-'
        row = dict.fromkeys(RAW.values(), '')
        row.update({'Provincia': 'Alicante/Alacant', 'Identificador del Punto de Conexión': '0001'})
        for name in ('original.csv', 'oficial.csv'):
            with (self.root / name).open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.writer(stream, delimiter=';')
                writer.writerow(RAW.values())
                writer.writerow(row.values())
        (self.root / 'pagina.json').write_text(json.dumps({
            'texto': 'Formato de la resolución de 30 de abril de 2025',
            'enlaces': [{'url': self.url}]}), encoding='utf-8')
        self.norm = ('dentro de los cinco primeros días del mes siguiente al que se refiere la información '
                     '1. Formato para la publicación de las capacidades de acceso para instalaciones de demanda ')
        for field in ('X', 'Y'):
            self.norm += f'Coordenada UTM {field}. Coordenadas de la ubicación de la subestación, en el sistema ETRS89 UTM referidas al huso 30 para la península '
        self.norm += '2. Formato para la publicación de las capacidades de acceso para instalaciones de generación'
        (self.root / 'norma.html').write_text('<p>' + self.norm + '</p>', encoding='utf-8')
        self.evidence = {'version': 1, 'recurso_id': 'ide_capacidad_demanda',
                         'archivos': {}, 'filas_nacionales': 1,
                         'filas_cv_provincia': {'Alicante/Alacant': 1},
                         'fecha_publicacion': '2026-09-04', 'url_csv_oficial': self.url,
                         'periodo_referencia': '2026-08', 'crs_cv': 'EPSG:25830',
                         'fecha_corte_exacta': None}
        for name, filename in [('original', 'original.csv'), ('csv_oficial', 'oficial.csv'),
                               ('pagina_ide', 'pagina.json'), ('norma', 'norma.html')]:
            self.pin(name, filename)

    def pin(self, name, filename):
        self.evidence['archivos'][name] = {'ruta': filename, **fingerprint(self.root / filename)}

    def test_exact_copy_period_and_crs_without_modifying_inputs(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = verify(self.root, self.evidence)
        self.assertEqual(result['filas_cv'], 1)
        self.assertEqual(result['periodo_referencia'], '2026-08')
        self.assertIsNone(result['fecha_corte_exacta'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_changed_evidence_is_rejected(self):
        with (self.root / 'original.csv').open('ab') as stream:
            stream.write(b'\n')
        with self.assertRaisesRegex(ValueError, 'Huella distinta'):
            verify(self.root, self.evidence)

    def test_different_official_copy_is_rejected_even_with_its_updated_hash(self):
        with (self.root / 'oficial.csv').open('ab') as stream:
            stream.write(b'\n')
        self.pin('csv_oficial', 'oficial.csv')
        with self.assertRaisesRegex(ValueError, 'no coincide'):
            verify(self.root, self.evidence)

    def test_generation_only_crs_does_not_establish_demand_crs(self):
        demand, generation = self.norm.split('2. Formato', 1)
        demand = demand.replace('ETRS89 UTM', 'UTM sin datum')
        (self.root / 'norma.html').write_text(demand + '2. Formato' + generation + self.norm, encoding='utf-8')
        self.pin('norma', 'norma.html')
        with self.assertRaisesRegex(ValueError, 'apartado de demanda'):
            verify(self.root, self.evidence)

    def test_publication_date_is_not_the_reporting_month(self):
        self.evidence['periodo_referencia'] = '2026-09'
        with self.assertRaisesRegex(ValueError, 'Periodo mensual'):
            verify(self.root, self.evidence)

    def test_exact_cutoff_day_cannot_be_invented(self):
        self.evidence['fecha_corte_exacta'] = '2026-08-31'
        with self.assertRaisesRegex(ValueError, 'alcance acreditado'):
            verify(self.root, self.evidence)

    def test_unlinked_download_does_not_establish_edition(self):
        (self.root / 'pagina.json').write_text(json.dumps({'texto': 'resolución de 30 de abril de 2025',
                                                        'enlaces': []}), encoding='utf-8')
        self.pin('pagina_ide', 'pagina.json')
        with self.assertRaisesRegex(ValueError, 'no enlaza'):
            verify(self.root, self.evidence)


if __name__ == '__main__':
    unittest.main()
