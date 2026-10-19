import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from catalogar_bronze import ROOT, fingerprint
from validar_silver import (within, spatial_relations, review_charging,
                            provider_evidence, OUTPUT_KEYS, write_outputs, load_inputs)


class ValidacionSilverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.c = duckdb.connect(config={'extension_directory': str(ROOT / '.venv/duckdb_extensions')})
        self.addCleanup(self.c.close)
        self.c.execute('LOAD spatial')
        self.c.execute('''CREATE TABLE base_territorial__recintos_municipales AS SELECT codigo_municipio,
            ST_GeomFromText(wkt)::GEOMETRY('EPSG:25830') geometria FROM (VALUES
            ('03001','POLYGON ((0 0,10 0,10 10,0 10,0 0))'),
            ('03002','POLYGON ((10 0,20 0,20 10,10 10,10 0))')) x(codigo_municipio,wkt)''')
        self.c.execute('''CREATE TABLE relaciones_espaciales(tabla_entidad VARCHAR,clave_entidad VARCHAR,
            codigo_municipio VARCHAR,metodo VARCHAR,dimension_interseccion SMALLINT,
            longitud_interseccion_m DOUBLE,superficie_interseccion_m2 DOUBLE)''')
        self.c.execute('''CREATE TABLE estado_relaciones_espaciales(tabla_entidad VARCHAR,clave_entidad VARCHAR,
            estado_geometria VARCHAR,numero_municipios BIGINT,estado_relacion VARCHAR)''')

    def spatial(self, rows):
        self.c.execute("CREATE TABLE entidades(id VARCHAR,otra VARCHAR,geometria GEOMETRY('EPSG:25830'),estado_geometria VARCHAR)")
        for key, other, wkt, state in rows:
            self.c.execute("INSERT INTO entidades VALUES (?,?,ST_GeomFromText(?)::GEOMETRY('EPSG:25830'),?)", [key, other, wkt, state])
        spatial_relations(self.c, 'entidades', ['id', 'otra'], 'ejemplo', 'POI')

    def test_point_on_boundary_keeps_both_municipalities(self):
        self.spatial([('x','1','POINT (10 5)','admitida')])
        self.assertEqual(self.c.execute('SELECT numero_municipios,estado_relacion FROM estado_relaciones_espaciales').fetchone(), (2,'interseccion_multiple'))
        self.assertEqual(self.c.execute('SELECT dimension_interseccion,longitud_interseccion_m,superficie_interseccion_m2 FROM relaciones_espaciales').fetchall(), [(0,None,None),(0,None,None)])

    def test_area_is_not_replaced_by_centroid(self):
        self.spatial([('x','1','POLYGON ((8 2,12 2,12 4,8 4,8 2))','admitida')])
        self.assertEqual(self.c.execute('SELECT codigo_municipio,superficie_interseccion_m2 FROM relaciones_espaciales ORDER BY 1').fetchall(), [('03001',4.0),('03002',4.0)])

    def test_line_crossing_and_boundary_contact_are_distinct(self):
        self.spatial([('linea','1','LINESTRING (5 5,15 5)','admitida'), ('toque','1','LINESTRING (5 4,10 4)','admitida')])
        self.assertEqual(self.c.execute("SELECT dimension_interseccion,longitud_interseccion_m FROM relaciones_espaciales WHERE clave_entidad='[\"toque\",\"1\"]' ORDER BY codigo_municipio").fetchall(), [(1,5.0),(0,None)])

    def test_outside_and_non_admitted_geometry_remain_in_status(self):
        self.spatial([('fuera','1','POINT (30 5)','admitida'), ('mala','1','LINESTRING (5 5,5 5)','proyeccion_no_admitida')])
        self.assertEqual(self.c.execute('SELECT estado_relacion FROM estado_relaciones_espaciales ORDER BY clave_entidad').fetchall(), [('sin_interseccion_cv',),('geometria_no_admitida',)])
        self.assertEqual(self.c.execute('SELECT count(*) FROM relaciones_espaciales').fetchone()[0], 0)

    def test_json_composite_key_has_no_separator_collision(self):
        self.spatial([('a:b','c','POINT (2 2)','admitida'),('a','b:c','POINT (2 2)','admitida')])
        self.assertEqual(self.c.execute('SELECT count(DISTINCT clave_entidad) FROM relaciones_espaciales').fetchone()[0],2)

    def test_duplicate_source_key_stops_relations(self):
        with self.assertRaisesRegex(ValueError, 'Clave repetida'):
            self.spatial([('x','1','POINT (2 2)','admitida'),('x','1','POINT (2 2)','admitida')])

    def test_partitioned_relations_equal_single_batch_without_losing_entities(self):
        self.spatial([('x','1','LINESTRING (5 5,15 5)','admitida'),
            ('x','2','POINT (30 5)','admitida'),('y','2','POINT (10 5)','admitida')])
        expected=self.c.execute('SELECT * FROM relaciones_espaciales ORDER BY clave_entidad,codigo_municipio').fetchall()
        states=self.c.execute('SELECT * FROM estado_relaciones_espaciales ORDER BY clave_entidad').fetchall()
        self.c.execute('DELETE FROM relaciones_espaciales')
        self.c.execute('DELETE FROM estado_relaciones_espaciales')
        for part in ('1','2'):
            self.c.execute(f"CREATE OR REPLACE TEMP VIEW lote AS SELECT * FROM entidades WHERE otra='{part}'")
            spatial_relations(self.c,'lote',['id','otra'],'ejemplo','POI')
        self.assertEqual(self.c.execute('SELECT * FROM relaciones_espaciales ORDER BY clave_entidad,codigo_municipio').fetchall(),expected)
        self.assertEqual(self.c.execute('SELECT * FROM estado_relaciones_espaciales ORDER BY clave_entidad').fetchall(),states)

    def charging(self):
        self.c.execute('''CREATE TABLE recarga_espacial__recarga_instalaciones_geo(
            instalacion_id VARCHAR,nombre_instalacion VARCHAR,direccion VARCHAR,municipio_nombre_origen VARCHAR,
            nombre_municipio_espacial VARCHAR,codigo_municipio_declarado VARCHAR,codigo_municipio_espacial VARCHAR,
            distancia_municipio_declarado_m DOUBLE,admitida_asignacion_municipal BOOLEAN,
            numero_municipios_intersectados BIGINT,estado_geometria VARCHAR,codigo_provincia_declarada VARCHAR)''')
        self.c.execute("INSERT INTO recarga_espacial__recarga_instalaciones_geo VALUES ('x','Consum Beta','Calle 1','Alpha','Beta','03001','03002',1,false,1,'admitida','03')")
        for name in ('recarga_instalaciones','recarga_puntos','recarga_conectores'):
            self.c.execute(f'CREATE TABLE recarga__{name}(instalacion_id VARCHAR)')
            self.c.execute(f"INSERT INTO recarga__{name} VALUES ('x')")

    def test_name_and_one_metre_distance_do_not_resolve_conflict(self):
        self.charging()
        result=review_charging(self.c,{})
        self.assertEqual(self.c.execute('SELECT indicio_textual,estado_revision,codigo_municipio_validado FROM revision_recarga').fetchone(),('espacial','pendiente_contraste_externo',None))
        self.assertEqual(result['entidades']['recarga_conectores']['pendiente'],1)

    def evidence(self):
        path=self.root/'fuente.html'
        path.write_text('<script type="application/ld+json">'+json.dumps({'@graph':[{'@type':'Store','url':'https://example.org/store','address':{'streetAddress':'Calle 1','addressLocality':'Beta'}}]})+'</script>',encoding='utf-8')
        stamp=fingerprint(path)
        path.with_suffix('.html.adquisicion.json').write_text(json.dumps({'url_solicitada':'https://example.org/store',**stamp}),encoding='utf-8')
        item={'instalacion_id':'x','decision':'admitir','copia':'fuente.html',**stamp,'url':'https://example.org/store','direccion_documentada':'Calle 1','municipio_documentado':'Beta',
            'codigo_municipio':'03002','atributos_esperados':['Consum Beta','Calle 1'],'motivo':'Mismo establecimiento y dirección en ficha primaria.'}
        config=self.root/'decisiones.json'
        config.write_text(json.dumps({'decisiones':[item]}),encoding='utf-8')
        return config,path,item

    def test_documented_resolution_is_complementary_and_preserves_original(self):
        self.charging()
        config,_,_=self.evidence()
        decisions,files=provider_evidence(self.root,config,self.c)
        review_charging(self.c,decisions)
        self.assertEqual(len(files),3)
        self.assertEqual(self.c.execute('SELECT codigo_municipio FROM recarga_municipio_validado').fetchone()[0],'03002')
        self.assertEqual(self.c.execute('SELECT codigo_municipio_declarado,admitida_asignacion_municipal FROM recarga_espacial__recarga_instalaciones_geo').fetchone(),('03001',False))

    def test_changed_source_or_changed_installation_invalidates_resolution(self):
        self.charging()
        config,path,_=self.evidence()
        self.c.execute("UPDATE recarga_espacial__recarga_instalaciones_geo SET direccion='Otra calle'")
        with self.assertRaisesRegex(ValueError,'instalación revisada ha cambiado'):
            provider_evidence(self.root,config,self.c)
        path.write_text('contenido distinto',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Entrada distinta'):
            provider_evidence(self.root,config,self.c)

    def test_inconclusive_provider_evidence_does_not_admit_municipality(self):
        self.charging()
        config,_,item=self.evidence()
        item['decision']='mantener_pendiente'
        config.write_text(json.dumps({'decisiones':[item]}),encoding='utf-8')
        decisions,_=provider_evidence(self.root,config,self.c)
        review_charging(self.c,decisions)
        self.assertEqual(self.c.execute('SELECT count(*) FROM recarga_municipio_validado').fetchone()[0],0)
        self.assertEqual(self.c.execute('SELECT estado_revision,url_evidencia FROM revision_recarga').fetchone(),
            ('pendiente_evidencia_documental_no_concluyente','https://example.org/store'))

    def json_evidence(self, kind, records):
        self.charging()
        self.c.execute("ALTER TABLE recarga_espacial__recarga_instalaciones_geo ADD COLUMN codigo_postal VARCHAR DEFAULT '03000'")
        path=self.root/'fuente.json'
        path.write_text(json.dumps(records),encoding='utf-8')
        url='https://example.org/candidates?q=Calle+1&cod_postal_filter=03000'
        stamp=fingerprint(path)
        path.with_suffix('.json.adquisicion.json').write_text(json.dumps({'url_solicitada':url,**stamp}),encoding='utf-8')
        record=records[0]
        item={'instalacion_id':'x','decision':'admitir','copia':'fuente.json',**stamp,'url':url,
            'tipo_evidencia':kind,'selector':{'campo':'id','valor':record['id']},
            'campos_documentados':record,'codigo_postal_origen':'03000','portal_documentado':1,
            'codigo_municipio':'03002','atributos_esperados':['Consum Beta','Calle 1'],
            'direccion_documentada':record.get('direccion','Calle 1'),'municipio_documentado':record.get('ciudad','Beta'),
            'motivo':'Correspondencia explícita revisada.'}
        config=self.root/'decisiones.json'
        config.write_text(json.dumps({'decisiones':[item]}),encoding='utf-8')
        return config,path,item

    def test_parking_jsonld_supports_explicit_address_review(self):
        self.charging()
        config,path,item=self.evidence()
        path.write_text(path.read_text(encoding='utf-8').replace('"Store"','"ParkingFacility"'),encoding='utf-8')
        stamp=fingerprint(path)
        item.update(stamp,tipo_jsonld='ParkingFacility')
        path.with_suffix('.html.adquisicion.json').write_text(json.dumps({'url_solicitada':item['url'],**stamp}),encoding='utf-8')
        config.write_text(json.dumps({'decisiones':[item]}),encoding='utf-8')
        self.assertIn('x',provider_evidence(self.root,config,self.c)[0])

    def test_official_street_review_is_municipal_without_inventing_portal(self):
        config,_,_=self.json_evidence('via_cartociudad',[{'id':'v','type':'callejero','muniCode':'03002','state':0}])
        decisions,_=provider_evidence(self.root,config,self.c)
        review_charging(self.c,decisions)
        self.assertEqual(self.c.execute('SELECT metodo FROM recarga_municipio_validado').fetchone()[0],
            'revision_cartografica_via_cartociudad')

    def test_street_with_candidates_in_two_municipalities_is_not_admitted(self):
        config,_,_=self.json_evidence('via_cartociudad',[
            {'id':'v','type':'callejero','muniCode':'03002','state':0},
            {'id':'w','type':'callejero','muniCode':'03001','state':0}])
        with self.assertRaisesRegex(ValueError,'Vial ambiguo'):
            provider_evidence(self.root,config,self.c)

    def test_charging_poi_mirrored_from_miteco_is_not_address_evidence(self):
        config,_,_=self.json_evidence('via_cartociudad',[{'id':'p','type':'punto_recarga_electrica','muniCode':'03002','state':0}])
        with self.assertRaisesRegex(ValueError,'Vial ambiguo'):
            provider_evidence(self.root,config,self.c)

    def test_portal_checks_number_and_does_not_accept_nearest_other_number(self):
        config,_,_=self.json_evidence('portal_cartociudad',[
            {'id':'p','type':'portal','muniCode':'03002','state':0,'postalCode':'03000','portalNumber':2,'lat':0,'lng':0}])
        with self.assertRaisesRegex(ValueError,'Portal oficial incompatible'):
            provider_evidence(self.root,config,self.c)

    def test_postal_query_cannot_be_forced_to_candidate_municipality(self):
        config,path,item=self.json_evidence('via_cartociudad',[{'id':'v','type':'callejero','muniCode':'03002','state':0}])
        item['url']+='&municipio_filter=Beta'
        path.with_suffix('.json.adquisicion.json').write_text(json.dumps({'url_solicitada':item['url'],**fingerprint(path)}),encoding='utf-8')
        config.write_text(json.dumps({'decisiones':[item]}),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Consulta postal incompatible'):
            provider_evidence(self.root,config,self.c)

    def test_operator_record_requires_unique_identity_and_expected_fields(self):
        record={'id':'a','direccion':'Calle 1','ciudad':'Beta','lat':0,'lng':0}
        config,_,_=self.json_evidence('registro_operador_json',[record,record])
        with self.assertRaisesRegex(ValueError,'Registro documental no identificado'):
            provider_evidence(self.root,config,self.c)

    def test_primary_text_requires_visible_fragments_not_script_contents(self):
        self.charging()
        config,path,item=self.evidence()
        path.write_text('<p>Establecimiento Calle 1 Beta</p><script>SoloJavascript</script>',encoding='utf-8')
        item.update(fingerprint(path),tipo_evidencia='texto_primario_revisado',
            fragmentos_documentados=['Establecimiento','Calle 1','Beta'])
        def save():
            path.with_suffix('.html.adquisicion.json').write_text(json.dumps({'url_solicitada':item['url'],**fingerprint(path)}),encoding='utf-8')
            config.write_text(json.dumps({'decisiones':[item]}),encoding='utf-8')
        save()
        self.assertIn('x',provider_evidence(self.root,config,self.c)[0])
        item['fragmentos_documentados'].append('SoloJavascript')
        save()
        with self.assertRaisesRegex(ValueError,'texto primario no respalda'):
            provider_evidence(self.root,config,self.c)

    def test_inconclusive_social_post_cannot_be_used_for_admission(self):
        self.charging()
        config,path,item=self.evidence()
        node={'@type':'SocialMediaPosting','@id':item['url'],'author':{'name':'Operador'},'articleBody':'Estación Beta'}
        path.write_text('<script type="application/ld+json">'+json.dumps(node)+'</script>',encoding='utf-8')
        item.update(fingerprint(path),tipo_evidencia='publicacion_primaria_no_concluyente',
            autor_documentado='Operador',fragmentos_documentados=['Estación Beta'])
        path.with_suffix('.html.adquisicion.json').write_text(json.dumps({'url_solicitada':item['url'],**fingerprint(path)}),encoding='utf-8')
        config.write_text(json.dumps({'decisiones':[item]}),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'admisión indebida'):
            provider_evidence(self.root,config,self.c)
        item['decision']='mantener_pendiente'
        config.write_text(json.dumps({'decisiones':[item]}),encoding='utf-8')
        self.assertEqual(provider_evidence(self.root,config,self.c)[0]['x']['decision'],'mantener_pendiente')

    def visual_review(self):
        self.charging()
        config,path,item=self.evidence()
        node={'@type':'SocialMediaPosting','@id':item['url'],'author':{'name':'Operador'},'articleBody':'Estación Beta'}
        path.write_text('<script type="application/ld+json">'+json.dumps(node)+'</script>',encoding='utf-8')
        capture=self.root/'captura.png'
        capture.write_bytes(b'captura de prueba')
        review=self.root/'revision.json'
        review.write_text(json.dumps({'instalacion_id':'x','codigo_municipio':'03002',
            'alcance':'municipio_emplazamiento','motivo':'Recinto identificado explícitamente.',
            'url_visual':'https://example.org/panorama','evidencias':[{'ruta':'captura.png',**fingerprint(capture)}]}),encoding='utf-8')
        item.update(fingerprint(path),tipo_evidencia='revision_visual_y_fuente_primaria',
            autor_documentado='Operador',fragmentos_documentados=['Estación Beta'],
            revision_visual={'ruta':'revision.json',**fingerprint(review)})
        path.with_suffix('.html.adquisicion.json').write_text(json.dumps({'url_solicitada':item['url'],**fingerprint(path)}),encoding='utf-8')
        config.write_text(json.dumps({'decisiones':[item]}),encoding='utf-8')
        return config,capture

    def test_visual_review_complements_primary_source_without_changing_original(self):
        config,_=self.visual_review()
        decisions,files=provider_evidence(self.root,config,self.c)
        review_charging(self.c,decisions)
        self.assertEqual(len(files),5)
        self.assertEqual(self.c.execute('SELECT codigo_municipio,metodo FROM recarga_municipio_validado').fetchone(),
            ('03002','revision_visual_y_documental'))
        self.assertEqual(self.c.execute('SELECT codigo_municipio_declarado FROM recarga_espacial__recarga_instalaciones_geo').fetchone()[0],'03001')

    def test_changed_visual_capture_invalidates_manual_admission(self):
        config,capture=self.visual_review()
        capture.write_bytes(b'otra captura')
        with self.assertRaisesRegex(ValueError,'Entrada distinta'):
            provider_evidence(self.root,config,self.c)

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            within(self.root,'../fuera.json')

    def input_run(self):
        directory=self.root/'resultados/silver/base_territorial'
        run=directory/'ejecucion'
        run.mkdir(parents=True)
        self.c.execute("CREATE TABLE municipios AS SELECT codigo_municipio FROM base_territorial__recintos_municipales")
        outputs=[]
        for name,source in [('municipios','municipios'),('recintos_municipales','base_territorial__recintos_municipales')]:
            path=run/(name+'.parquet')
            self.c.execute(f'COPY {source} TO ? (FORMAT PARQUET)',[str(path)])
            outputs.append({'archivo':path.name,'filas':2,**fingerprint(path),
                'esquema':[{'campo':r[0],'tipo':r[1]} for r in self.c.execute(f'DESCRIBE {source}').fetchall()]})
        report={'ejecucion':'ejecucion','estado':'preparada','salidas':outputs}
        (directory/'actual.json').write_text(json.dumps({'ejecucion':'ejecucion','informe':'ejecucion/informe.json'}),encoding='utf-8')
        path=run/'informe.json'
        path.write_text(json.dumps(report),encoding='utf-8')
        self.c.execute('DROP TABLE base_territorial__recintos_municipales')
        return directory,path,report

    def test_loader_checks_source_hash_before_using_parquet(self):
        _,path,report=self.input_run()
        report['salidas'][0]['sha256']='0'*64
        path.write_text(json.dumps(report),encoding='utf-8')
        with patch('validar_silver.BLOCKS',('base_territorial',)), self.assertRaisesRegex(ValueError,'Entrada distinta'):
            load_inputs(self.c,self.root)

    def test_loader_checks_counts_not_only_file_hashes(self):
        _,path,report=self.input_run()
        report['salidas'][0]['filas']=3
        path.write_text(json.dumps(report),encoding='utf-8')
        with patch('validar_silver.BLOCKS',('base_territorial',)), self.assertRaisesRegex(ValueError,'Recuento distinto'):
            load_inputs(self.c,self.root)

    def test_loader_rejects_inconsistent_run_pointer(self):
        directory,_,_=self.input_run()
        (directory/'actual.json').write_text(json.dumps({'ejecucion':'otra','informe':'ejecucion/informe.json'}),encoding='utf-8')
        with patch('validar_silver.BLOCKS',('base_territorial',)), self.assertRaisesRegex(ValueError,'Informe y ejecución'):
            load_inputs(self.c,self.root)

    def test_export_preserves_nulls_states_and_keys(self):
        self.charging()
        review_charging(self.c,{})
        for name in ('cobertura_estadistica','estado_fuentes'):
            self.c.execute(f'CREATE TABLE {name}('+','.join('"'+key+'" VARCHAR' for key in OUTPUT_KEYS[name])+')')
        outputs=write_outputs(self.c,self.root/'salidas')
        self.assertEqual(len(outputs),6)
        row=self.c.execute('SELECT estado_revision,codigo_municipio_validado FROM read_parquet(?)',[str(self.root/'salidas/revision_recarga.parquet')]).fetchone()
        self.assertEqual(row,('pendiente_contraste_externo',None))


if __name__=='__main__':
    unittest.main()
