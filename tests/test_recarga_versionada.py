import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preparar_recarga_versionada import ROOT, inherit_geometry, preserve_absences, write_outputs
from preparar_recarga import prepare, KEYS
from georreferenciar_recarga import prepare as georeference, validate as validate_geo
from validar_silver import review_charging
from test_recarga import export, row


class VersionedChargingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.c = duckdb.connect(str(self.root / 'test.duckdb'), config={
            'extension_directory': str(ROOT / '.venv/duckdb_extensions'),
            'storage_compatibility_version': 'v1.5.0'})
        self.addCleanup(self.c.close)
        self.c.execute('LOAD spatial')
        self.c.execute("CREATE TABLE municipios AS SELECT '03001' codigo_municipio,'Alpha' nombre_municipio")
        self.c.execute('''CREATE TABLE recintos AS SELECT *,nombre_municipio nombre_municipio_ign,
            ST_Transform(ST_GeomFromText('POLYGON ((-1 38,0 38,0 39,-1 39,-1 38))'),
            'EPSG:4258','EPSG:25830',always_xy:=true)::GEOMETRY('EPSG:25830') geometria FROM municipios''')

    def build(self):
        present = row(); present[2] = 'Alpha'; present[14] = 'presente'
        absent = present.copy(); absent[14] = 'ausente'
        path = self.root / 'old.csv'
        export(path, [present, absent])
        prepare(self.c, path, self.root)
        georeference(self.c, self.root)
        self.c.execute('ALTER TABLE recarga_instalaciones_geo RENAME TO geometria_anterior')
        self.c.execute('ALTER TABLE recarga_municipios_candidatos RENAME TO candidatos_anteriores')
        self.c.execute('''CREATE TABLE admisiones_anteriores AS SELECT instalacion_id,
            codigo_municipio_espacial codigo_municipio,'interseccion_unica_y_nombre_oficial'::VARCHAR metodo,
            NULL::VARCHAR url_evidencia FROM geometria_anterior''')
        for name in KEYS:
            self.c.execute(f'ALTER TABLE {name} RENAME TO anterior_{name}')
        for name in ('incidencias', 'entidad_municipio', 'incidencias_espaciales'):
            self.c.execute('DROP TABLE ' + name)
        path = self.root / 'new.csv'
        export(path, [present])
        prepare(self.c, path, self.root)

    def test_exact_identity_preserves_geometry_and_rechecks_municipality(self):
        self.build()
        inherit_geometry(self.c)
        validate_geo(self.c)
        self.assertEqual(self.c.execute('SELECT instalacion_id FROM recarga_instalaciones_geo').fetchall(), [('presente',)])
        self.assertTrue(self.c.execute('''SELECT ST_AsWKB(n.geometria)=ST_AsWKB(a.geometria)
            FROM recarga_instalaciones_geo n JOIN geometria_anterior a USING(instalacion_id)''').fetchone()[0])
        self.assertEqual(self.c.execute('SELECT codigo_municipio FROM entidad_municipio').fetchall(), [('03001',)])

    def test_changed_coordinates_or_identity_blocks_inheritance(self):
        self.build()
        for field, value in [('latitud_origen', '38.4'), ('nombre_instalacion', 'Otra estación')]:
            with self.subTest(field=field):
                previous = self.c.execute(f'SELECT {field} FROM recarga_instalaciones').fetchone()[0]
                self.c.execute(f'UPDATE recarga_instalaciones SET {field}=?', [value])
                with self.assertRaisesRegex(ValueError, 'Identidad o coordenadas distintas'):
                    inherit_geometry(self.c)
                self.c.execute(f'UPDATE recarga_instalaciones SET {field}=?', [previous])

    def test_changed_territorial_relations_blocks_inheritance(self):
        self.build()
        self.c.execute('DELETE FROM candidatos_anteriores')
        with self.assertRaisesRegex(ValueError, 'municipios intersectados difieren'):
            inherit_geometry(self.c)

    def test_absences_keep_history_without_entering_present_tables(self):
        self.build()
        inherit_geometry(self.c)
        preserve_absences(self.c)
        self.assertEqual(self.c.execute('''SELECT instalacion_id,puntos_registrados_historicos,
            conectores_registrados_historicos,codigo_municipio_admitido_historico FROM recarga_ausentes''').fetchall(),
            [('ausente', 1, 1, '03001')])
        self.assertEqual(self.c.execute('SELECT * FROM recarga_ausentes_municipios_candidatos').fetchall(), [('ausente', '03001')])
        self.assertEqual(self.c.execute('SELECT instalacion_id FROM recarga_instalaciones').fetchall(), [('presente',)])

    def test_export_reopens_all_tables_and_preserves_geometry_without_overwrite(self):
        self.build()
        inherit_geometry(self.c)
        preserve_absences(self.c)
        for name in KEYS:
            self.c.execute(f'CREATE TEMP VIEW recarga__{name} AS SELECT * FROM {name}')
        self.c.execute('CREATE TEMP VIEW recarga_espacial__recarga_instalaciones_geo AS SELECT * FROM recarga_instalaciones_geo')
        review_charging(self.c, {})
        target = self.root / 'salida'
        outputs = write_outputs(self.c, target)
        self.assertEqual(len(outputs), 12)
        self.assertEqual(next(x['filas'] for x in outputs if x['archivo'] == 'recarga_ausentes.parquet'), 1)
        with self.assertRaises(FileExistsError):
            write_outputs(self.c, target)


if __name__ == '__main__':
    unittest.main()
