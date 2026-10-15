import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from comprobar_entorno_silver import gpkg_wkb


class GeoPackageBinaryTests(unittest.TestCase):
    def test_byte_orders_and_envelopes_preserve_wkb(self):
        for order, flag in [('<', 1), ('>', 0)]:
            wkb = struct.pack(order + 'BI2d', flag, 1, -0.5, 39.0)
            for envelope, size in enumerate((0, 32, 48, 48, 64)):
                header = b'GP\x00' + bytes([flag | envelope << 1]) + struct.pack(order + 'i', 100000)
                self.assertEqual(gpkg_wkb(header + bytes(size) + wkb, 100000), wkb)

    def test_rejects_bad_headers_extended_truncation_and_srs_mismatch(self):
        wkb = struct.pack('<BI2d', 1, 1, -0.5, 39.0)
        valid = b'GP\x00\x01' + struct.pack('<i', 4258) + wkb
        for bad in [None, b'', b'XX' + valid[2:], valid[:2] + b'\x01' + valid[3:],
                    valid[:3] + b'\x21' + valid[4:], valid[:3] + b'\x0b' + valid[4:],
                    valid[:3] + b'\x03' + valid[4:], valid[:9]]:
            with self.subTest(blob=bad), self.assertRaises(ValueError):
                gpkg_wkb(bad, 4258)
        with self.assertRaisesRegex(ValueError, 'SRS'):
            gpkg_wkb(valid, 25830)


if __name__ == '__main__':
    unittest.main()
