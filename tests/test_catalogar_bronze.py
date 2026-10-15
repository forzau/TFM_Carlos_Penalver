import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from catalogar_bronze import build_manifest, fingerprint, registered_files, verify_manifest


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'Fuentes').mkdir()
        self.path = self.root / 'Fuentes/ejemplo.txt'
        self.path.write_bytes(b'datos originales')
        self.catalog = {'recursos': [{'id': 'ejemplo', 'fecha_descarga': None,
                                    'entradas': [{'patron': 'Fuentes/ejemplo.txt', 'rol': 'datos'}]}]}

    def test_register_and_verify_without_changing_original_or_unknown_date(self):
        before = self.path.stat()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('No cargar archivos completos')):
            manifest = build_manifest(self.root, self.catalog)
            self.assertEqual(verify_manifest(self.root, manifest), 1)
        record = manifest['archivos'][0]
        self.assertEqual(record['sha256'], hashlib.sha256(b'datos originales').hexdigest())
        self.assertIsNone(manifest['catalogo']['recursos'][0]['fecha_descarga'])
        self.assertEqual((before.st_size, before.st_mtime_ns), (self.path.stat().st_size, self.path.stat().st_mtime_ns))

    def test_detect_same_size_change_and_missing_original(self):
        manifest = build_manifest(self.root, self.catalog)
        self.path.write_bytes(b'otros originales')
        with self.assertRaisesRegex(ValueError, 'Integridad'):
            verify_manifest(self.root, manifest)
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, 'Número de archivos'):
            verify_manifest(self.root, manifest)

    def test_reject_unregistered_duplicate_and_incomplete_files(self):
        (self.root / 'Fuentes/no_registrado.txt').touch()
        with self.assertRaisesRegex(ValueError, 'sin catalogar'):
            registered_files(self.root, self.catalog)
        (self.root / 'Fuentes/no_registrado.txt').unlink()
        self.catalog['recursos'][0]['entradas'] *= 2
        with self.assertRaisesRegex(ValueError, 'repetida'):
            registered_files(self.root, self.catalog)
        self.catalog['recursos'][0]['entradas'] = [{'patron': 'Fuentes/*.txt', 'rol': 'datos', 'cantidad': 2}]
        with self.assertRaisesRegex(ValueError, 'Número de archivos'):
            registered_files(self.root, self.catalog)

    def test_reject_escape_and_inconsistent_manifest(self):
        for pattern in ('../ajeno.txt', 'Fuentes/../../ajeno.txt', 'C:/ajeno.txt', '/ajeno.txt'):
            catalog = copy.deepcopy(self.catalog)
            catalog['recursos'][0]['entradas'][0]['patron'] = pattern
            with self.subTest(pattern=pattern), self.assertRaises(ValueError):
                registered_files(self.root, catalog)
        manifest = build_manifest(self.root, self.catalog)
        manifest['archivos'][0]['ruta'] = '../ajeno.txt'
        with self.assertRaisesRegex(ValueError, 'no coinciden'):
            verify_manifest(self.root, manifest)

    def test_detect_changes_during_hash(self):
        real_stat = self.path.stat
        calls = 0
        def changed_stat(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.path.write_bytes(b'cambio')
            return real_stat(*args, **kwargs)
        with patch.object(Path, 'stat', side_effect=changed_stat):
            with self.assertRaisesRegex(RuntimeError, 'cambió'):
                fingerprint(self.path)


if __name__ == '__main__':
    unittest.main()
