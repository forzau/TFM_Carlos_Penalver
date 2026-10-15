import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from incorporar_referencias import download


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'original.json'

    def response(self, content):
        response = io.BytesIO(content)
        response.url = 'https://example.org/recurso'
        response.headers = {'Content-Type': 'application/json'}
        return response

    def test_download_reuse_and_modified_copy(self):
        with patch('incorporar_referencias.urlopen', return_value=self.response(b'{"dato":1}')) as request:
            receipt = download('https://example.org/recurso', self.path)
            self.assertEqual(download('https://example.org/recurso', self.path), receipt)
            self.assertEqual(request.call_count, 1)
        self.assertEqual(receipt['bytes'], len(b'{"dato":1}'))
        self.path.write_bytes(b'{"dato":2}')
        with self.assertRaisesRegex(ValueError, 'difiere'):
            download('https://example.org/recurso', self.path)

    def test_failed_download_leaves_no_original_or_receipt(self):
        with patch('incorporar_referencias.urlopen', return_value=self.response(b'grande')):
            with self.assertRaisesRegex(ValueError, 'límite'):
                download('https://example.org/recurso', self.path, limit=2)
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_never_replace_existing_original_or_partial_download(self):
        self.path.write_bytes(b'original')
        with self.assertRaisesRegex(ValueError, 'sin recibo'):
            download('https://example.org/recurso', self.path)
        self.assertEqual(self.path.read_bytes(), b'original')
        self.path.unlink()
        self.path.with_suffix('.json.part').write_bytes(b'incompleto')
        with self.assertRaises(FileExistsError):
            download('https://example.org/recurso', self.path)
        self.assertEqual(self.path.with_suffix('.json.part').read_bytes(), b'incompleto')


if __name__ == '__main__':
    unittest.main()
