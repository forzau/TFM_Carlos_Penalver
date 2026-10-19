import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from catalogar_bronze import ROOT
from preparar_capacidad_demanda import SCHEMA
from georreferenciar_capacidad_demanda import prepare, validate, write_outputs
from validar_silver import capacity_integrity


class CapacidadEspacialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = duckdb.connect(config={'extension_directory':str(ROOT/'.venv/duckdb_extensions')})
        self.addCleanup(self.c.close)
        self.c.execute('LOAD spatial')
        self.c.execute('CREATE TABLE capacidad_demanda ('+','.join('"'+k+'" '+v for k,v in SCHEMA.items())+')')
        self.c.execute("CREATE TABLE municipios AS SELECT * FROM (VALUES ('03001','Alfa/Alpha'),('03002','Beta')) t(codigo_municipio,nombre_municipio)")
        self.c.execute('''CREATE TABLE recintos AS SELECT codigo_municipio,nombre_municipio nombre_municipio_ign,
            ST_GeomFromText(wkt)::GEOMETRY('EPSG:25830') geometria FROM municipios JOIN (VALUES
            ('03001','POLYGON ((0 0,10 0,10 10,0 10,0 0))'),
            ('03002','POLYGON ((10 0,20 0,20 10,10 10,10 0))')) p(codigo_municipio,wkt) USING(codigo_municipio)''')
        self.metadata={'fecha_publicacion':'2026-09-04','periodo_referencia':'2026-08'}

    def row(self, key='0001', x='2,123456789', y='5', name='Alpha', province='03'):
        row = {k: '' if v=='VARCHAR' else None for k,v in SCHEMA.items()}
        row.update(punto_conexion_id=key, x_utm_origen=x,y_utm_origen=y,
                   municipio_nombre_origen=name,codigo_provincia=province,estado_fecha='no_acreditada',
                   estado_coordenadas='pendiente_crs',origen_id='sintetico',registro_origen=int(key))
        self.c.execute('INSERT INTO capacidad_demanda VALUES ('+','.join('?' for _ in SCHEMA)+')',list(row.values()))

    def build(self):
        prepare(self.c,self.metadata)
        return validate(self.c)

    def test_official_bilingual_variant_and_coincident_points_are_preserved(self):
        self.row();self.row(key='0002')
        result=self.build()
        self.assertEqual((result['puntos_conservados'],result['asignaciones_admitidas']),(2,2))
        self.assertEqual(self.c.execute('SELECT count(DISTINCT ST_AsWKB(geometria)) FROM capacidad_demanda_geo').fetchone()[0],1)
        row=self.c.execute('''SELECT x_utm_origen,ST_X(geometria),estado_fecha_preparacion,
            estado_coordenadas_preparacion,fecha_referencia,periodo_referencia,fecha_publicacion::VARCHAR
            FROM capacidad_demanda_geo LIMIT 1''').fetchone()
        self.assertEqual(row,('2,123456789',2.123456789,'no_acreditada','pendiente_crs',None,'2026-08','2026-09-04'))

    def test_boundary_keeps_both_candidates_without_exclusive_assignment(self):
        self.row(x='10');self.build()
        self.assertEqual(self.c.execute('SELECT count(*) FROM capacidad_municipios_candidatos').fetchone()[0],2)
        self.assertEqual(self.c.execute('SELECT estado_contraste_territorial FROM capacidad_demanda_geo').fetchone()[0],'limite_ambiguo')
        self.assertEqual(self.c.execute('SELECT count(*) FROM entidad_municipio').fetchone()[0],0)

    def test_bad_coordinates_and_outside_points_remain_present(self):
        self.row(x='2.000,0');self.row(key='0002',x='30')
        self.assertEqual(self.build()['pendientes'],2)
        self.assertEqual(self.c.execute('SELECT estado_contraste_territorial FROM capacidad_demanda_geo ORDER BY punto_conexion_id').fetchall(),[('geometria_no_admitida',),('fuera_ambito',)])

    def test_nearby_point_does_not_override_declared_municipality(self):
        self.row(x='10,001',name='Alpha');self.build()
        self.assertEqual(self.c.execute('SELECT estado_contraste_territorial FROM capacidad_demanda_geo').fetchone()[0],'municipio_discrepante')
        self.assertAlmostEqual(self.c.execute('SELECT distancia_municipio_declarado_m FROM capacidad_demanda_geo').fetchone()[0],0.001)

    def test_province_conflict_is_not_admitted(self):
        self.row(province='12');self.build()
        self.assertEqual(self.c.execute('SELECT estado_contraste_territorial FROM capacidad_demanda_geo').fetchone()[0],'provincia_discrepante')

    def test_ambiguous_official_alias_does_not_assign_a_municipality(self):
        self.c.execute("UPDATE municipios SET nombre_municipio='Beta/Alpha' WHERE codigo_municipio='03002'")
        self.row();self.build()
        self.assertEqual(self.c.execute('SELECT estado_contraste_territorial FROM capacidad_demanda_geo').fetchone()[0],'nombre_no_resuelto')

    def test_geoparquet_export_preserves_schema_values_and_crs(self):
        self.row();self.build()
        outputs=write_outputs(self.c,Path(self.tmp.name)/'salidas')
        self.assertEqual(len(outputs),4)
        self.assertIn({'campo':'geometria','tipo':"GEOMETRY('EPSG:25830')"},outputs[0]['esquema'])

    def joint(self):
        for source,target in [('capacidad_demanda','capacidad_demanda__capacidad_demanda'),
                              ('capacidad_demanda_geo','capacidad_demanda_espacial__capacidad_demanda_geo'),
                              ('entidad_municipio','capacidad_demanda_espacial__entidad_municipio'),
                              ('capacidad_municipios_candidatos','capacidad_demanda_espacial__capacidad_municipios_candidatos'),
                              ('municipios','base_territorial__municipios')]:
            self.c.execute(f'CREATE VIEW {target} AS SELECT * FROM {source}')

    def test_joint_checks_conservation_and_rejects_coordinate_shift(self):
        self.row();self.build();self.joint()
        self.assertEqual(capacity_integrity(self.c)['asignaciones_admitidas'],1)
        self.c.execute("UPDATE capacidad_demanda_geo SET geometria=ST_Point(3,5)::GEOMETRY('EPSG:25830')")
        with self.assertRaisesRegex(ValueError,'Metadatos o coordenadas'):
            capacity_integrity(self.c)

    def test_joint_does_not_accept_an_invented_cutoff_date(self):
        self.row();self.build();self.joint()
        self.c.execute("UPDATE capacidad_demanda_geo SET fecha_referencia='2026-08-31'")
        with self.assertRaisesRegex(ValueError,'Atributos i-DE originales'):
            capacity_integrity(self.c)


if __name__=='__main__':
    unittest.main()
