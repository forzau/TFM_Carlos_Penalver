"""La reorganización conserva las huellas antiguas sin admitir datos alternativos."""

import tempfile
import unittest
from pathlib import Path

from src.datos_y_preparacion.historico.catalogar_bronze import fingerprint
from src.datos_y_preparacion.historico.georreferenciar_recarga import checked


class TrazabilidadTests(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.root = Path(temporal.name)
        self.codigo = self.root / 'src/productor.py'
        self.codigo.parent.mkdir()
        self.codigo.write_bytes(b'original')
        self.sello = fingerprint(self.codigo)
        self.copia = self.root / 'resultados/codigo_historico' / (self.sello['sha256'] + '.py')
        self.copia.parent.mkdir(parents=True)
        self.copia.write_bytes(b'original')

    def test_codigo_movido_o_modificado_conserva_version_verificable(self):
        self.codigo.write_bytes(b'version modular')
        self.assertEqual(checked(self.root, self.codigo, self.sello)['sha256'], self.sello['sha256'])
        self.codigo.unlink()
        self.assertEqual(checked(self.root, self.codigo, self.sello)['ruta'], self.copia.relative_to(self.root).as_posix())

    def test_copia_corrupta_se_rechaza(self):
        self.copia.write_bytes(b'alterado')
        with self.assertRaises(ValueError):
            checked(self.root, self.codigo, self.sello)

    def test_datos_y_huellas_sin_copia_siguen_exigiendo_el_original(self):
        datos = self.root / 'dato.csv'
        datos.write_bytes(b'alterado')
        with self.assertRaises(ValueError):
            checked(self.root, datos, self.sello)
        self.copia.unlink()
        self.codigo.write_bytes(b'alterado')
        with self.assertRaises(ValueError):
            checked(self.root, self.codigo, self.sello)


if __name__ == '__main__':
    unittest.main()
