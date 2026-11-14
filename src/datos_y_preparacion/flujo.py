"""Preparación reproducible Bronze -> Silver -> Gold.

Ejecutar desde la raíz: python -m src.datos_y_preparacion
"""

from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import argparse
import duckdb
import tempfile

from src.datos_y_preparacion.pasos import bronze as _bronze
from src.datos_y_preparacion.pasos.comunes import (
    RAIZ,
    comprobar_archivo,
    conectar,
    exigir_cero,
    exportar_tablas,
    guardar_json,
    identificador_sql,
    texto_sql,
)
from src.datos_y_preparacion.pasos import gold as _gold
from src.datos_y_preparacion.pasos import capacidad as _capacidad
from src.datos_y_preparacion.pasos import demografia as _demografia
from src.datos_y_preparacion.pasos import integracion as _integracion
from src.datos_y_preparacion.pasos import osm as _osm
from src.datos_y_preparacion.pasos import recarga as _recarga
from src.datos_y_preparacion.pasos import territorio as _territorio
from src.datos_y_preparacion.pasos import trafico as _trafico


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--comprobar-entradas', action='store_true',
                        help='Comprueba entorno, originales y metadatos sin transformar tablas.')
    args = parser.parse_args()
    bronze, archivos, metadatos, adquisicion, origenes = _bronze.comprobar_entradas()
    if args.comprobar_entradas:
        print(f'Entradas comprobadas: {len(bronze["archivos"])} archivos Bronze y evidencias complementarias.')
        return

    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    salida = RAIZ / 'resultados/entrega02' / version
    salida.mkdir(parents=True, exist_ok=False)
    guardar_json(salida / 'bronze/manifiesto.json', bronze)
    tablas, controles = {}, {}

    @contextmanager
    def etapa(bloque):
        print(f'\nPreparando {bloque}...', flush=True)
        with tempfile.TemporaryDirectory(dir=salida) as temporal:
            temporal = Path(temporal)
            with conectar(temporal) as c:
                yield c, temporal
        print(f'Completado {bloque}.', flush=True)

    def cargar(c, bloque, nombres=None, prefijo='', alias=None):
        for nombre in nombres if nombres is not None else tablas[bloque]:
            entrada = tablas[bloque][nombre]
            path = RAIZ / entrada['ruta']
            comprobar_archivo(RAIZ, path, entrada)
            destino = (alias or {}).get(nombre, prefijo + nombre)
            c.execute(f'CREATE TEMP VIEW {identificador_sql(destino)} AS '
                      f'SELECT * FROM read_parquet({texto_sql(str(path))})')

    def territorio(c):
        cargar(c, 'silver/base_territorial', alias={'recintos_municipales': 'recintos'})
        c.execute('CREATE TEMP TABLE ambito_cv AS SELECT ST_Union_Agg(geometria) geometria FROM recintos')

    def exportar(c, bloque, claves, calidad):
        tablas[bloque] = exportar_tablas(c, salida / bloque, claves)
        controles[bloque] = calidad

    # Silver: conservar entidades, periodos, estados y valores originales por fuente.
    with etapa('silver/base_territorial') as (c, temporal):
        municipios, total_nacional = _territorio.referencia_municipal_reference(RAIZ / _territorio.TERRITORIO_INE)
        if Counter(codigo[:2] for codigo in municipios) != {'03': 141, '12': 135, '46': 266}:
            raise ValueError('La referencia no contiene los 542 municipios previstos')
        calidad = _territorio.territorio_build_base(c, municipios, RAIZ / _territorio.TERRITORIO_IGN,
                                      RAIZ / _territorio.TERRITORIO_HITS, origenes[_territorio.TERRITORIO_IGN])
        calidad['municipios_nacionales'] = total_nacional
        exportar(c, 'silver/base_territorial',
                 dict.fromkeys(('municipios', 'recintos_municipales'), ['codigo_municipio']), calidad)

    with etapa('silver/demografia_parque') as (c, temporal):
        cargar(c, 'silver/base_territorial', ['municipios'])
        _demografia.demografia_prepare_municipal_park(c, RAIZ / _demografia.DEMOGRAFIA_XLSX, municipios)
        _demografia.demografia_prepare_ine(c, RAIZ / _demografia.DEMOGRAFIA_POP, RAIZ / _demografia.DEMOGRAFIA_INCOME,
                              municipios, temporal, origenes)
        print('Leyendo el TXT nacional DGT secuencialmente, con trabajo en disco...', flush=True)
        _demografia.demografia_prepare_detail(c, RAIZ / _demografia.DEMOGRAFIA_TXT, origenes[_demografia.DEMOGRAFIA_TXT])
        exportar(c, 'silver/demografia_parque', {**_demografia.DEMOGRAFIA_KEYS, 'incidencias': None},
                 _demografia.demografia_validate(c, municipios))

    with etapa('silver/recarga') as (c, temporal):
        _recarga.recarga_prepare(c, RAIZ / _recarga.RECARGA_SOURCE, temporal)
        exportar(c, 'silver/recarga', {**_recarga.RECARGA_KEYS, 'incidencias': None}, _recarga.recarga_validate(c))

    with etapa('silver/trafico_red') as (c, temporal):
        _trafico.trafico_prepare_traffic(c, RAIZ / _trafico.TRAFICO_GVA, temporal, origenes[_trafico.TRAFICO_GVA])
        for provincia, carpeta in _trafico.TRAFICO_ROADS.items():
            ruta = carpeta + '/red_viaria.gpkg'
            _trafico.trafico_prepare_road(c, RAIZ / ruta, provincia, temporal, origenes[ruta])
        exportar(c, 'silver/trafico_red', {**_trafico.TRAFICO_KEYS, 'incidencias': None}, _trafico.trafico_validate(c))

    with etapa('silver/poi_osm') as (c, temporal):
        territorio(c)
        recuentos = _osm.osm_prepare(c, RAIZ / _osm.OSM_SOURCE, temporal, origenes[_osm.OSM_SOURCE])
        _osm.osm_classify(c)
        _osm.osm_correspondences(c)
        exportar(c, 'silver/poi_osm', {**_osm.OSM_KEYS, 'incidencias': None}, _osm.osm_validate(c, recuentos))

    with etapa('silver/capacidad_demanda') as (c, temporal):
        _capacidad.capacidad_prepare(c, RAIZ / _capacidad.CAPACIDAD_SOURCE, temporal, origenes[_capacidad.CAPACIDAD_SOURCE])
        exportar(c, 'silver/capacidad_demanda',
                 {'capacidad_demanda': ['punto_conexion_id'], 'incidencias': None}, _capacidad.capacidad_validate(c))

    with etapa('silver/recarga_espacial') as (c, temporal):
        territorio(c)
        cargar(c, 'silver/recarga', _recarga.RECARGA_KEYS)
        _recarga.recarga_geo_prepare(c, temporal)
        exportar(c, 'silver/recarga_espacial', {**_recarga.RECARGA_GEO_KEYS, 'incidencias_espaciales': None},
                 _recarga.recarga_geo_validate(c))

    with etapa('silver/capacidad_demanda_espacial') as (c, temporal):
        territorio(c)
        cargar(c, 'silver/capacidad_demanda', ['capacidad_demanda'])
        _capacidad.capacidad_geo_prepare(c, metadatos)
        exportar(c, 'silver/capacidad_demanda_espacial', _capacidad.CAPACIDAD_GEO_KEYS, _capacidad.capacidad_geo_validate(c))

    with etapa('silver/validacion_conjunta') as (c, temporal):
        for bloque in list(tablas):
            cargar(c, bloque, prefijo=bloque.split('/')[-1] + '__')
        calidad = _integracion.integracion_integrity(c)
        decisiones, evidencias = _integracion.integracion_provider_evidence(RAIZ, RAIZ / _bronze.ENTRADAS['decisiones_recarga'], c)
        archivos.extend(evidencias)
        calidad['recarga'] = _integracion.integracion_review_charging(c, decisiones)
        calidad['relaciones'] = _integracion.integrar_relaciones(c)
        calidad['cobertura'] = _integracion.integracion_coverage(c)
        _integracion.crear_estado_fuentes(c)
        exportar(c, 'silver/validacion_conjunta', _integracion.INTEGRACION_OUTPUT_KEYS, calidad)

    # La versión principal hereda geometría solo si los atributos coinciden exactamente.
    # Las ausencias históricas y las decisiones documentales se conservan por separado.
    with etapa('silver/recarga_versionada') as (c, temporal):
        territorio(c)
        cargar(c, 'silver/recarga', _recarga.RECARGA_KEYS, prefijo='anterior_')
        cargar(c, 'silver/recarga_espacial', ['recarga_instalaciones_geo', 'recarga_municipios_candidatos'],
               alias={'recarga_instalaciones_geo': 'geometria_anterior',
                      'recarga_municipios_candidatos': 'candidatos_anteriores'})
        cargar(c, 'silver/validacion_conjunta', ['recarga_municipio_validado'],
               alias={'recarga_municipio_validado': 'admisiones_anteriores'})
        _recarga.recarga_prepare(c, RAIZ / _bronze.ENTRADAS['recarga_principal'], temporal)
        calidad = _recarga.recarga_validate(c)
        if calidad['incidencias']:
            raise ValueError('Revisar incidencias tabulares de la recarga principal')
        _integracion.recarga_versionada_inherit_geometry(c)
        calidad['espacial'] = _recarga.recarga_geo_validate(c)
        _integracion.crear_vistas_revision(c)
        decisiones, evidencias = _integracion.integracion_provider_evidence(RAIZ, RAIZ / _bronze.ENTRADAS['decisiones_recarga'], c)
        archivos.extend(evidencias)
        calidad['revision'] = _integracion.integracion_review_charging(c, decisiones)
        exigir_cero(c, '''SELECT count(*) FROM (
            (SELECT * FROM recarga_municipio_validado EXCEPT ALL SELECT a.* FROM admisiones_anteriores a
             JOIN recarga_instalaciones n USING(instalacion_id)) UNION ALL
            (SELECT a.* FROM admisiones_anteriores a JOIN recarga_instalaciones n USING(instalacion_id)
             EXCEPT ALL SELECT * FROM recarga_municipio_validado))''', 'Admisiones incompatibles entre versiones')
        _integracion.recarga_versionada_preserve_absences(c)
        exportar(c, 'silver/recarga_versionada', _integracion.RECARGA_VERSIONADA_KEYS, calidad)

    # Gold: conjunto relacional final, sin pesos, ranking o entrenamiento.
    with etapa('gold/contexto_municipal') as (c, temporal):
        for bloque, nombres in _gold.GOLD_MUNICIPAL_BLOCKS.items():
            cargar(c, 'silver/' + bloque, nombres)
        _gold.gold_municipal_prepare(c, version, adquisicion, origenes['recarga_principal'], origenes[_recarga.RECARGA_SOURCE])
        exportar(c, 'gold/contexto_municipal', _gold.GOLD_MUNICIPAL_KEYS, _gold.gold_municipal_validate(c, version))

    with etapa('gold/candidatos') as (c, temporal):
        for bloque, nombres in _gold.GOLD_CANDIDATOS_SOURCES.items():
            cargar(c, bloque, nombres)
        _gold.gold_candidatos_prepare(c, version)
        _gold.gold_candidatos_proximity(c, version)
        exportar(c, 'gold/candidatos', _gold.GOLD_CANDIDATOS_KEYS, _gold.gold_candidatos_validate(c, version))

    with etapa('gold/controles_espaciales') as (c, temporal):
        cargar(c, 'gold/contexto_municipal')
        cargar(c, 'gold/candidatos')
        _gold.gold_controles_prepare(c, version)
        exportar(c, 'gold/controles_espaciales', _gold.GOLD_CONTROLES_KEYS, _gold.gold_controles_validate(c, version))

    with etapa('gold/variables') as (c, temporal):
        for bloque in ('gold/contexto_municipal', 'gold/candidatos', 'gold/controles_espaciales'):
            cargar(c, bloque)
        _gold.gold_variables_prepare(c, version)
        exportar(c, 'gold/variables', _gold.GOLD_VARIABLES_KEYS, _gold.gold_variables_validate(c, version))

    # El manifiesto marca una ejecución terminada; una interrupción deja su carpeta sin validar.
    for entrada in archivos:
        comprobar_archivo(RAIZ, RAIZ / entrada['ruta'], entrada)
    manifiesto = {'version_script': 1, 'ejecucion': version, 'estado': 'preparada_con_limitaciones',
                  'entradas_verificadas': list({x['ruta']: x for x in archivos}.values()),
                  'metadatos_capacidad': metadatos, 'tablas': tablas, 'controles': controles,
                  'entorno': {'duckdb': duckdb.__version__, 'memoria_motor': '1GB', 'hilos': 2},
                  'limitaciones': ['Distintivo 0 aproxima demanda municipal; no demanda local observada.',
                      'Asignaciones pendientes y ausencias no equivalen a inexistencia o cierre.',
                      'POI requieren revisión local; distancias planas no son rutas ni suficiencia.',
                      'Capacidad i-DE orientativa, no aditiva ni garantía de conexión.']}
    guardar_json(salida / 'manifiesto.json', manifiesto)
    print(f'\nPreparación completada: {salida.relative_to(RAIZ).as_posix()}/manifiesto.json', flush=True)
