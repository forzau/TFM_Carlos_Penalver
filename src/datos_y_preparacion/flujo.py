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

from src.datos_y_preparacion.bronze import ENTRADAS, comprobar_entradas
from src.datos_y_preparacion.comunes import (
    RAIZ,
    comprobar_archivo,
    conectar,
    exigir_cero,
    exportar_tablas,
    guardar_json,
    identificador_sql,
    texto_sql,
)
from src.datos_y_preparacion.gold import (
    GOLD_CANDIDATOS_KEYS,
    GOLD_CANDIDATOS_SOURCES,
    GOLD_CONTROLES_KEYS,
    GOLD_MUNICIPAL_BLOCKS,
    GOLD_MUNICIPAL_KEYS,
    GOLD_VARIABLES_KEYS,
    gold_candidatos_prepare,
    gold_candidatos_proximity,
    gold_candidatos_validate,
    gold_controles_prepare,
    gold_controles_validate,
    gold_municipal_prepare,
    gold_municipal_validate,
    gold_variables_prepare,
    gold_variables_validate,
)
from src.datos_y_preparacion.silver.capacidad import (
    CAPACIDAD_GEO_KEYS,
    CAPACIDAD_SOURCE,
    capacidad_geo_prepare,
    capacidad_geo_validate,
    capacidad_prepare,
    capacidad_validate,
)
from src.datos_y_preparacion.silver.demografia import (
    DEMOGRAFIA_INCOME,
    DEMOGRAFIA_KEYS,
    DEMOGRAFIA_POP,
    DEMOGRAFIA_TXT,
    DEMOGRAFIA_XLSX,
    demografia_prepare_detail,
    demografia_prepare_ine,
    demografia_prepare_municipal_park,
    demografia_validate,
)
from src.datos_y_preparacion.silver.integracion import (
    INTEGRACION_OUTPUT_KEYS,
    RECARGA_VERSIONADA_KEYS,
    crear_estado_fuentes,
    crear_vistas_revision,
    integracion_coverage,
    integracion_integrity,
    integracion_provider_evidence,
    integracion_review_charging,
    integrar_relaciones,
    recarga_versionada_inherit_geometry,
    recarga_versionada_preserve_absences,
)
from src.datos_y_preparacion.silver.osm import (
    OSM_KEYS,
    OSM_SOURCE,
    osm_classify,
    osm_correspondences,
    osm_prepare,
    osm_validate,
)
from src.datos_y_preparacion.silver.recarga import (
    RECARGA_GEO_KEYS,
    RECARGA_KEYS,
    RECARGA_SOURCE,
    recarga_geo_prepare,
    recarga_geo_validate,
    recarga_prepare,
    recarga_validate,
)
from src.datos_y_preparacion.silver.territorio import (
    TERRITORIO_HITS,
    TERRITORIO_IGN,
    TERRITORIO_INE,
    referencia_municipal_reference,
    territorio_build_base,
)
from src.datos_y_preparacion.silver.trafico import (
    TRAFICO_GVA,
    TRAFICO_KEYS,
    TRAFICO_ROADS,
    trafico_prepare_road,
    trafico_prepare_traffic,
    trafico_validate,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--comprobar-entradas', action='store_true',
                        help='Comprueba entorno, originales y metadatos sin transformar tablas.')
    args = parser.parse_args()
    bronze, archivos, metadatos, adquisicion, origenes = comprobar_entradas()
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
        municipios, total_nacional = referencia_municipal_reference(RAIZ / TERRITORIO_INE)
        if Counter(codigo[:2] for codigo in municipios) != {'03': 141, '12': 135, '46': 266}:
            raise ValueError('La referencia no contiene los 542 municipios previstos')
        calidad = territorio_build_base(c, municipios, RAIZ / TERRITORIO_IGN,
                                      RAIZ / TERRITORIO_HITS, origenes[TERRITORIO_IGN])
        calidad['municipios_nacionales'] = total_nacional
        exportar(c, 'silver/base_territorial',
                 dict.fromkeys(('municipios', 'recintos_municipales'), ['codigo_municipio']), calidad)

    with etapa('silver/demografia_parque') as (c, temporal):
        cargar(c, 'silver/base_territorial', ['municipios'])
        demografia_prepare_municipal_park(c, RAIZ / DEMOGRAFIA_XLSX, municipios)
        demografia_prepare_ine(c, RAIZ / DEMOGRAFIA_POP, RAIZ / DEMOGRAFIA_INCOME,
                              municipios, temporal, origenes)
        print('Leyendo el TXT nacional DGT secuencialmente, con trabajo en disco...', flush=True)
        demografia_prepare_detail(c, RAIZ / DEMOGRAFIA_TXT, origenes[DEMOGRAFIA_TXT])
        exportar(c, 'silver/demografia_parque', {**DEMOGRAFIA_KEYS, 'incidencias': None},
                 demografia_validate(c, municipios))

    with etapa('silver/recarga') as (c, temporal):
        recarga_prepare(c, RAIZ / RECARGA_SOURCE, temporal)
        exportar(c, 'silver/recarga', {**RECARGA_KEYS, 'incidencias': None}, recarga_validate(c))

    with etapa('silver/trafico_red') as (c, temporal):
        trafico_prepare_traffic(c, RAIZ / TRAFICO_GVA, temporal, origenes[TRAFICO_GVA])
        for provincia, carpeta in TRAFICO_ROADS.items():
            ruta = carpeta + '/red_viaria.gpkg'
            trafico_prepare_road(c, RAIZ / ruta, provincia, temporal, origenes[ruta])
        exportar(c, 'silver/trafico_red', {**TRAFICO_KEYS, 'incidencias': None}, trafico_validate(c))

    with etapa('silver/poi_osm') as (c, temporal):
        territorio(c)
        recuentos = osm_prepare(c, RAIZ / OSM_SOURCE, temporal, origenes[OSM_SOURCE])
        osm_classify(c)
        osm_correspondences(c)
        exportar(c, 'silver/poi_osm', {**OSM_KEYS, 'incidencias': None}, osm_validate(c, recuentos))

    with etapa('silver/capacidad_demanda') as (c, temporal):
        capacidad_prepare(c, RAIZ / CAPACIDAD_SOURCE, temporal, origenes[CAPACIDAD_SOURCE])
        exportar(c, 'silver/capacidad_demanda',
                 {'capacidad_demanda': ['punto_conexion_id'], 'incidencias': None}, capacidad_validate(c))

    with etapa('silver/recarga_espacial') as (c, temporal):
        territorio(c)
        cargar(c, 'silver/recarga', RECARGA_KEYS)
        recarga_geo_prepare(c, temporal)
        exportar(c, 'silver/recarga_espacial', {**RECARGA_GEO_KEYS, 'incidencias_espaciales': None},
                 recarga_geo_validate(c))

    with etapa('silver/capacidad_demanda_espacial') as (c, temporal):
        territorio(c)
        cargar(c, 'silver/capacidad_demanda', ['capacidad_demanda'])
        capacidad_geo_prepare(c, metadatos)
        exportar(c, 'silver/capacidad_demanda_espacial', CAPACIDAD_GEO_KEYS, capacidad_geo_validate(c))

    with etapa('silver/validacion_conjunta') as (c, temporal):
        for bloque in list(tablas):
            cargar(c, bloque, prefijo=bloque.split('/')[-1] + '__')
        calidad = integracion_integrity(c)
        decisiones, evidencias = integracion_provider_evidence(RAIZ, RAIZ / ENTRADAS['decisiones_recarga'], c)
        archivos.extend(evidencias)
        calidad['recarga'] = integracion_review_charging(c, decisiones)
        calidad['relaciones'] = integrar_relaciones(c)
        calidad['cobertura'] = integracion_coverage(c)
        crear_estado_fuentes(c)
        exportar(c, 'silver/validacion_conjunta', INTEGRACION_OUTPUT_KEYS, calidad)

    # La versión principal hereda geometría solo si los atributos coinciden exactamente.
    # Las ausencias históricas y las decisiones documentales se conservan por separado.
    with etapa('silver/recarga_versionada') as (c, temporal):
        territorio(c)
        cargar(c, 'silver/recarga', RECARGA_KEYS, prefijo='anterior_')
        cargar(c, 'silver/recarga_espacial', ['recarga_instalaciones_geo', 'recarga_municipios_candidatos'],
               alias={'recarga_instalaciones_geo': 'geometria_anterior',
                      'recarga_municipios_candidatos': 'candidatos_anteriores'})
        cargar(c, 'silver/validacion_conjunta', ['recarga_municipio_validado'],
               alias={'recarga_municipio_validado': 'admisiones_anteriores'})
        recarga_prepare(c, RAIZ / ENTRADAS['recarga_principal'], temporal)
        calidad = recarga_validate(c)
        if calidad['incidencias']:
            raise ValueError('Revisar incidencias tabulares de la recarga principal')
        recarga_versionada_inherit_geometry(c)
        calidad['espacial'] = recarga_geo_validate(c)
        crear_vistas_revision(c)
        decisiones, evidencias = integracion_provider_evidence(RAIZ, RAIZ / ENTRADAS['decisiones_recarga'], c)
        archivos.extend(evidencias)
        calidad['revision'] = integracion_review_charging(c, decisiones)
        exigir_cero(c, '''SELECT count(*) FROM (
            (SELECT * FROM recarga_municipio_validado EXCEPT ALL SELECT a.* FROM admisiones_anteriores a
             JOIN recarga_instalaciones n USING(instalacion_id)) UNION ALL
            (SELECT a.* FROM admisiones_anteriores a JOIN recarga_instalaciones n USING(instalacion_id)
             EXCEPT ALL SELECT * FROM recarga_municipio_validado))''', 'Admisiones incompatibles entre versiones')
        recarga_versionada_preserve_absences(c)
        exportar(c, 'silver/recarga_versionada', RECARGA_VERSIONADA_KEYS, calidad)

    # Gold: conjunto relacional final, sin pesos, ranking o entrenamiento.
    with etapa('gold/contexto_municipal') as (c, temporal):
        for bloque, nombres in GOLD_MUNICIPAL_BLOCKS.items():
            cargar(c, 'silver/' + bloque, nombres)
        gold_municipal_prepare(c, version, adquisicion, origenes['recarga_principal'], origenes[RECARGA_SOURCE])
        exportar(c, 'gold/contexto_municipal', GOLD_MUNICIPAL_KEYS, gold_municipal_validate(c, version))

    with etapa('gold/candidatos') as (c, temporal):
        for bloque, nombres in GOLD_CANDIDATOS_SOURCES.items():
            cargar(c, bloque, nombres)
        gold_candidatos_prepare(c, version)
        gold_candidatos_proximity(c, version)
        exportar(c, 'gold/candidatos', GOLD_CANDIDATOS_KEYS, gold_candidatos_validate(c, version))

    with etapa('gold/controles_espaciales') as (c, temporal):
        cargar(c, 'gold/contexto_municipal')
        cargar(c, 'gold/candidatos')
        gold_controles_prepare(c, version)
        exportar(c, 'gold/controles_espaciales', GOLD_CONTROLES_KEYS, gold_controles_validate(c, version))

    with etapa('gold/variables') as (c, temporal):
        for bloque in ('gold/contexto_municipal', 'gold/candidatos', 'gold/controles_espaciales'):
            cargar(c, bloque)
        gold_variables_prepare(c, version)
        exportar(c, 'gold/variables', GOLD_VARIABLES_KEYS, gold_variables_validate(c, version))

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
