import json
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from preparar_gold_candidatos import ROOT, KEYS, prepare, proximity, validate, validate_exports, load_inputs
from preparar_recarga_versionada import write_outputs


class CandidateGoldTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.c = duckdb.connect(config={'extension_directory':str(ROOT/'.venv/duckdb_extensions')})
        self.addCleanup(self.c.close)
        c = self.c
        c.execute('LOAD spatial')
        c.execute('''CREATE TABLE recintos_municipales AS SELECT codigo_municipio,
            ST_GeomFromText(wkt)::GEOMETRY('EPSG:25830') geometria FROM (VALUES
            ('03001','POLYGON ((0 0,10 0,10 10,0 10,0 0))'),
            ('03002','POLYGON ((10 0,20 0,20 10,10 10,10 0))')) v(codigo_municipio,wkt)''')
        c.execute("CREATE TABLE gold_municipios AS SELECT 'municipal'::VARCHAR version_gold,codigo_municipio FROM recintos_municipales")
        c.execute('''CREATE TABLE poi_elementos AS SELECT 'osm:hash:layer'::VARCHAR origen_id,
            'layer'::VARCHAR capa_origen,id::BIGINT fid_origen,cast(id AS VARCHAR) osm_id,NULL::VARCHAR nombre_origen,
            code categoria_codigo_origen,category categoria_origen,representation representacion,grp grupo_uso,
            'seleccionada'::VARCHAR estado_categoria,ST_GeomFromText(wkt)::GEOMETRY('EPSG:25830') geometria,
            'admitida'::VARCHAR estado_geometria,'intersecta_cv'::VARCHAR estado_ambito,true interes_para_revision
            FROM (VALUES
            (1,'5260','parking','punto','aparcamiento','POINT (9 5)'),
            (2,'5260','parking','area','aparcamiento','POLYGON ((8 4,12 4,12 6,8 6,8 4))'),
            (3,'2501','supermarket','punto','comercio','POINT (2 2)'),
            (4,'2401','hotel','area','alojamiento','MULTIPOLYGON (((1 1,3 1,3 3,1 3,1 1)),((15 1,17 1,17 3,15 3,15 1)))'),
            (5,'5250','fuel','punto','parada_viaria','POINT (5 5)'),
            (6,'5260','parking','area','aparcamiento','POLYGON ((20 2,22 2,22 4,20 4,20 2))'))
            v(id,code,category,representation,grp,wkt)''')
        c.execute('''CREATE TABLE relaciones_espaciales AS SELECT 'poi_elementos'::VARCHAR tabla_entidad,
            to_json(list_value(p.origen_id,cast(p.fid_origen AS VARCHAR)))::VARCHAR clave_entidad,r.codigo_municipio,
            ST_Dimension(ST_Intersection(p.geometria,r.geometria))::SMALLINT dimension_interseccion,
            CASE WHEN ST_Dimension(ST_Intersection(p.geometria,r.geometria))=2
                THEN ST_Area(ST_Intersection(p.geometria,r.geometria)) END superficie_interseccion_m2
            FROM poi_elementos p JOIN recintos_municipales r ON ST_Intersects(p.geometria,r.geometria)''')
        c.execute('''CREATE TABLE poi_correspondencias AS SELECT origen_id origen_punto,1::BIGINT fid_punto,
            origen_id origen_area,2::BIGINT fid_area,true punto_intersecta_area,false coincide_id_publicado,
            false coincide_nombre_normalizado,0::DOUBLE distancia_plana_m,
            'posible_correspondencia_sin_fusion'::VARCHAR estado FROM poi_elementos LIMIT 1''')
        c.execute('''CREATE TABLE gold_recarga_instalaciones AS SELECT 'municipal'::VARCHAR version_gold,
            id instalacion_id,present presente_copia_principal,admission estado_admision,
            'admitida'::VARCHAR estado_geometria,ST_GeomFromText(wkt)::GEOMETRY('EPSG:25830') geometria,
            code codigo_municipio_admitido FROM (VALUES
            ('A',true,'admitida_version_principal','POINT (11 5)','03002'),
            ('B',true,'admitida_version_principal','POINT (11 5)','03002'),
            ('C',true,'admitida_version_principal','POINT (1 5)','03001'),
            ('P',true,'pendiente','POINT (9 6)',NULL),
            ('H',false,'admitida_solo_historica','POINT (9 5)','03001')) v(id,present,admission,wkt,code)''')

    def build(self):
        prepare(self.c,'prueba')
        proximity(self.c,'prueba')
        return validate(self.c,'prueba')

    def test_destinations_keep_unknown_name_and_do_not_merge_point_area(self):
        self.build()
        self.assertEqual(self.c.execute('SELECT count(*),count(nombre_origen) FROM gold_candidatos').fetchone(),(5,0))
        self.assertEqual(self.c.execute('SELECT count(*) FROM gold_correspondencias_candidatos').fetchone()[0],1)
        self.assertEqual(self.c.execute("SELECT tipo_preseleccion FROM gold_candidatos WHERE fid_origen=3").fetchone()[0],
                         'destino_sin_aparcamiento_acreditado')

    def test_multiple_municipalities_preserve_all_links_and_no_exclusive_context(self):
        self.build()
        self.assertEqual(self.c.execute('''SELECT codigo_municipio_contexto,numero_municipios_relacionados
            FROM gold_candidatos WHERE fid_origen=2''').fetchone(),(None,2))

    def test_multipart_area_point_is_inside_original_and_cv(self):
        self.build()
        self.assertEqual(self.c.execute('''SELECT ST_Intersects(geometria,punto_representativo),
            ST_GeometryType(punto_representativo) FROM gold_candidatos WHERE fid_origen=4''').fetchone(),(True,'POINT'))

    def test_boundary_only_area_retains_null_position_and_three_states(self):
        self.build()
        self.assertEqual(self.c.execute('SELECT punto_representativo,metodo_representacion FROM gold_candidatos WHERE fid_origen=6').fetchone(),
                         (None,'sin_superficie_en_cv'))
        self.assertEqual(self.c.execute('''SELECT count(*) FROM gold_proximidad_candidato_recarga p
            JOIN gold_candidatos c USING(candidato_id) WHERE c.fid_origen=6
            AND estado_distancia='sin_posicion_representativa' AND distancia_plana_m IS NULL''').fetchone()[0],3)

    def test_neighbor_across_municipal_border_exact_tie_and_nested_scenarios(self):
        self.build()
        rows=self.c.execute('''SELECT escenario,instalacion_id_mas_cercana,distancia_plana_m,
            numero_instalaciones_a_distancia_minima FROM gold_proximidad_candidato_recarga
            JOIN gold_candidatos USING(candidato_id) WHERE fid_origen=1 ORDER BY distancia_plana_m DESC''').fetchall()
        self.assertEqual(rows,[('principal_admitida','A',2.0,2),('incluye_pendientes','P',1.0,1),('incluye_ausentes_historicas','H',0.0,1)])

    def test_empty_offer_is_explicit_and_keeps_candidates(self):
        self.c.execute('DELETE FROM gold_recarga_instalaciones')
        self.build()
        self.assertEqual(self.c.execute("SELECT count(*) FROM gold_proximidad_candidato_recarga WHERE estado_distancia='sin_recarga_admisible'").fetchone()[0],12)

    def test_non_admitted_charger_geometry_excluded_from_all_scenarios(self):
        self.c.execute("UPDATE gold_recarga_instalaciones SET estado_geometria='no_admitida' WHERE instalacion_id='H'")
        self.build()
        self.assertEqual(self.c.execute("SELECT count(*) FROM gold_proximidad_candidato_recarga WHERE instalacion_id_mas_cercana='H'").fetchone()[0],0)

    def test_duplicate_relation_and_missing_municipal_link_rejected(self):
        self.c.execute('INSERT INTO relaciones_espaciales SELECT * FROM relaciones_espaciales LIMIT 1')
        with self.assertRaises(ValueError): self.build()

    def test_no_municipal_link_rejected_instead_of_dropping_element(self):
        self.c.execute("DELETE FROM relaciones_espaciales WHERE clave_entidad LIKE '%\"1\"%'")
        with self.assertRaisesRegex(ValueError,'Contexto municipal'): self.build()

    def test_validation_rejects_wrong_exact_tie_count(self):
        self.build()
        self.c.execute('UPDATE gold_proximidad_candidato_recarga SET numero_instalaciones_a_distancia_minima=99 WHERE estado_distancia=\'calculable\'')
        with self.assertRaisesRegex(ValueError,'empates'): validate(self.c,'prueba')

    def test_validation_rejects_farther_valid_neighbor(self):
        self.build()
        self.c.execute('''UPDATE gold_proximidad_candidato_recarga SET instalacion_id_mas_cercana='C',
            distancia_plana_m=8,numero_instalaciones_a_distancia_minima=1 WHERE escenario='principal_admitida'
            AND candidato_id IN (SELECT candidato_id FROM gold_candidatos WHERE fid_origen=1)''')
        with self.assertRaisesRegex(ValueError,'Mínimo'): validate(self.c,'prueba')

    def test_validation_rejects_wrong_tie_break_id(self):
        self.build()
        self.c.execute("UPDATE gold_proximidad_candidato_recarga SET instalacion_id_mas_cercana='B' WHERE instalacion_id_mas_cercana='A'")
        with self.assertRaisesRegex(ValueError,'desempate'): validate(self.c,'prueba')

    def test_category_code_disagreement_is_rejected(self):
        self.c.execute("UPDATE poi_elementos SET categoria_codigo_origen='5250' WHERE fid_origen=1")
        with self.assertRaisesRegex(ValueError,'Preselección OSM'): self.build()

    def test_validation_rejects_altered_correspondence_evidence(self):
        self.build()
        self.c.execute('UPDATE gold_correspondencias_candidatos SET coincide_nombre_normalizado=true')
        with self.assertRaisesRegex(ValueError,'Relaciones Silver'): validate(self.c,'prueba')

    def test_both_geometry_columns_round_trip_and_cannot_overwrite(self):
        self.build()
        target=self.root/'salida'
        outputs=write_outputs(self.c,target,KEYS)
        validate_exports(self.c,target)
        self.assertEqual(len(outputs),4)
        with self.assertRaises(FileExistsError): write_outputs(self.c,target,KEYS)

    def test_pointer_outside_block_is_rejected_before_read(self):
        directory=self.root/'resultados/silver/poi_osm';directory.mkdir(parents=True)
        (directory/'actual.json').write_text(json.dumps({'ejecucion':'otro','informe':'../../fuera/informe.json'}),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Referencia de entrada'): load_inputs(self.c,self.root)


if __name__=='__main__':
    unittest.main()
