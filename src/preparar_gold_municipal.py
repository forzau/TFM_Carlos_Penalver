"""Materializa el contrato inicial Gold desde Silver validada, sin red ni priorización."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from auditar_fuentes import ident, query
from catalogar_bronze import ROOT
from georreferenciar_recarga import checked
from preparar_demografia_parque import check_key
from preparar_recarga import SOURCE
from preparar_recarga_versionada import write_outputs
from validar_silver import require_zero


KEYS = {
    'gold_municipios': ['version_gold', 'codigo_municipio'],
    'gold_recarga_instalaciones': ['version_gold', 'instalacion_id'],
    'gold_incertidumbre_recarga_municipio': ['version_gold', 'instalacion_id', 'codigo_municipio', 'tipo_incertidumbre']}
BLOCKS = {
    'base_territorial': ['municipios', 'recintos_municipales'],
    'demografia_parque': ['parque_municipal', 'poblacion_municipal', 'renta_territorial'],
    'recarga_versionada': ['recarga_instalaciones_geo', 'recarga_puntos', 'recarga_conectores',
                          'recarga_municipio_validado', 'recarga_municipios_candidatos',
                          'recarga_ausentes', 'recarga_ausentes_municipios_candidatos']}


def load_inputs(c, root):
    files, reports = [], {}
    for block, names in BLOCKS.items():
        directory = root / 'resultados/silver' / block
        pointer = directory / 'actual.json'
        files.append(checked(root, pointer))
        selection = json.loads(pointer.read_text(encoding='utf-8'))
        report_path = (directory / selection['informe']).resolve()
        if (not report_path.is_relative_to(directory.resolve()) or
                report_path.name != 'informe.json' or report_path.parent.name != selection['ejecucion']):
            raise ValueError('Referencia de ejecución Silver incoherente o fuera de su bloque')
        files.append(checked(root, report_path))
        report = json.loads(report_path.read_text(encoding='utf-8'))
        if report['ejecucion'] != selection['ejecucion']:
            raise ValueError('El informe no corresponde a la ejecución Silver seleccionada')
        if report['estado'] not in ('preparada', 'preparada_con_limitaciones'):
            raise ValueError(f'Entrada Silver no preparada: {block}')
        reports[block] = report
        for name in names:
            entry = next(x for x in report['salidas'] if x['archivo'] == name + '.parquet')
            path = report_path.parent / entry['archivo']
            files.append(checked(root, path, entry))
            c.execute(f'CREATE TEMP TABLE {ident(name)} AS SELECT * FROM read_parquet(?)', [str(path)])
            expected_count = entry.get('filas', 542 if block == 'base_territorial' else None)
            if c.execute('SELECT count(*) FROM ' + ident(name)).fetchone()[0] != expected_count:
                raise ValueError(f'Recuento distinto del informe: {name}')
    # Reutilizar la preparación validada exige que sus copias y evidencias sigan intactas.
    for entry in reports['recarga_versionada']['entradas_verificadas']:
        files.append(checked(root, root / entry['ruta'], entry))
    if c.execute('SELECT count(*) FROM municipios').fetchone()[0] != 542:
        raise ValueError('La base municipal no contiene los 542 municipios')
    return files, reports


def select_inputs(c):
    c.execute("CREATE TEMP TABLE parque_elegido AS SELECT * FROM parque_municipal WHERE fecha_referencia=DATE '2025-12-31'")
    c.execute("CREATE TEMP TABLE poblacion_elegida AS SELECT * FROM poblacion_municipal WHERE sexo='Total' AND anio=2025")
    c.execute("""CREATE TEMP TABLE renta_elegida AS SELECT * FROM renta_territorial
        WHERE nivel_territorial='municipio' AND indicador='Renta neta media por persona' AND anio=2023""")
    for name in ('municipios', 'recintos_municipales', 'parque_elegido', 'poblacion_elegida', 'renta_elegida'):
        check_key(c, name, ['codigo_municipio'])
        require_zero(c, f'''SELECT count(*) FROM (
            (SELECT codigo_municipio FROM municipios EXCEPT SELECT codigo_municipio FROM {name}) UNION ALL
            (SELECT codigo_municipio FROM {name} EXCEPT SELECT codigo_municipio FROM municipios))''',
            f'Cobertura municipal incompleta o ajena a la referencia: {name}')
    for name, keys in (
        ('recarga_instalaciones_geo', ['instalacion_id']), ('recarga_ausentes', ['instalacion_id']),
        ('recarga_puntos', ['instalacion_id', 'punto_id']),
        ('recarga_conectores', ['instalacion_id', 'punto_id', 'conector_id']),
        ('recarga_municipio_validado', ['instalacion_id']),
        ('recarga_municipios_candidatos', ['instalacion_id', 'codigo_municipio']),
        ('recarga_ausentes_municipios_candidatos', ['instalacion_id', 'codigo_municipio'])):
        check_key(c, name, keys)
    for child, parent, columns in (
        ('recarga_puntos', 'recarga_instalaciones_geo', 'instalacion_id'),
        ('recarga_conectores', 'recarga_puntos', 'instalacion_id,punto_id')):
        require_zero(c, f'SELECT count(*) FROM {child} ANTI JOIN {parent} USING({columns})', 'Detalle de recarga huérfano')
        require_zero(c, f'SELECT count(*) FROM {parent} ANTI JOIN {child} USING({columns})', 'Instalación o punto sin detalle')
    for name, parent in (('recarga_municipio_validado', 'recarga_instalaciones_geo'),
                         ('recarga_municipios_candidatos', 'recarga_instalaciones_geo'),
                         ('recarga_ausentes_municipios_candidatos', 'recarga_ausentes')):
        require_zero(c, f'SELECT count(*) FROM {name} ANTI JOIN {parent} USING(instalacion_id)', 'Relación de recarga huérfana')
        require_zero(c, f'SELECT count(*) FROM {name} ANTI JOIN municipios USING(codigo_municipio)', 'Municipio de recarga no reconocido')
    require_zero(c, '''SELECT count(*) FROM recarga_ausentes a
        JOIN recarga_instalaciones_geo n USING(instalacion_id)''', 'Un ID figura como presente y ausente')
    require_zero(c, '''SELECT count(*) FROM recarga_ausentes a ANTI JOIN municipios m
        ON a.codigo_municipio_admitido_historico=m.codigo_municipio
        WHERE a.codigo_municipio_admitido_historico IS NOT NULL''', 'Admisión histórica fuera de la referencia')


def prepare(c, version, acquisition, main_origin, historical_origin):
    select_inputs(c)
    c.execute('''CREATE TABLE gold_recarga_instalaciones AS WITH
        puntos AS (SELECT instalacion_id,count(*)::BIGINT n FROM recarga_puntos GROUP BY 1),
        conectores AS (SELECT instalacion_id,count(*)::BIGINT n FROM recarga_conectores GROUP BY 1)
        SELECT ?::VARCHAR version_gold,g.instalacion_id,?::VARCHAR version_recarga_observada,
            true presente_copia_principal,g.nombre_instalacion,g.operador_id,g.geometria,g.estado_geometria,
            v.codigo_municipio codigo_municipio_admitido,
            CASE WHEN v.instalacion_id IS NULL THEN 'pendiente' ELSE 'admitida_version_principal' END estado_admision,
            v.metodo metodo_admision,p.n puntos_registrados,c.n conectores_registrados,
            ?::TIMESTAMPTZ fecha_adquisicion_observacion
        FROM recarga_instalaciones_geo g LEFT JOIN recarga_municipio_validado v USING(instalacion_id)
        LEFT JOIN puntos p USING(instalacion_id) LEFT JOIN conectores c USING(instalacion_id)
        UNION ALL SELECT ?::VARCHAR,a.instalacion_id,?::VARCHAR,false,a.nombre_instalacion,a.operador_id,
            a.geometria,a.estado_geometria,a.codigo_municipio_admitido_historico,
            CASE WHEN a.codigo_municipio_admitido_historico IS NULL THEN 'pendiente' ELSE 'admitida_solo_historica' END,
            a.metodo_admision_historica,a.puntos_registrados_historicos,a.conectores_registrados_historicos,
            NULL::TIMESTAMPTZ FROM recarga_ausentes a''',
        [version, main_origin, acquisition, version, historical_origin])
    c.execute('''CREATE TEMP TABLE avisos_recarga AS
        SELECT g.instalacion_id,'asignacion_pendiente'::VARCHAR tipo_incertidumbre,
            g.codigo_municipio_declarado,NULL::VARCHAR codigo_historico
        FROM recarga_instalaciones_geo g ANTI JOIN recarga_municipio_validado v USING(instalacion_id)
        UNION ALL SELECT instalacion_id,'ausencia_exportacion',codigo_municipio_declarado,
            codigo_municipio_admitido_historico FROM recarga_ausentes''')
    c.execute('''CREATE TABLE gold_incertidumbre_recarga_municipio AS WITH roles AS (
        SELECT instalacion_id,tipo_incertidumbre,codigo_historico codigo_municipio,
            true historico,false declarado,false espacial FROM avisos_recarga WHERE codigo_historico IS NOT NULL
        UNION ALL SELECT instalacion_id,tipo_incertidumbre,codigo_municipio_declarado,
            false,true,false FROM avisos_recarga WHERE codigo_municipio_declarado IS NOT NULL
        UNION ALL SELECT a.instalacion_id,a.tipo_incertidumbre,c.codigo_municipio,false,false,true
            FROM avisos_recarga a JOIN recarga_municipios_candidatos c USING(instalacion_id)
            WHERE tipo_incertidumbre='asignacion_pendiente'
        UNION ALL SELECT a.instalacion_id,a.tipo_incertidumbre,c.codigo_municipio,false,false,true
            FROM avisos_recarga a JOIN recarga_ausentes_municipios_candidatos c USING(instalacion_id)
            WHERE tipo_incertidumbre='ausencia_exportacion')
        SELECT ?::VARCHAR version_gold,r.instalacion_id,r.codigo_municipio,r.tipo_incertidumbre,
            bool_or(historico) es_municipio_admitido_historico,bool_or(declarado) es_municipio_declarado,
            bool_or(espacial) es_candidato_espacial FROM roles r JOIN municipios m USING(codigo_municipio)
            JOIN avisos_recarga a USING(instalacion_id,tipo_incertidumbre)
        WHERE a.codigo_historico IS NULL OR r.codigo_municipio=a.codigo_historico GROUP BY 2,3,4''', [version])
    c.execute('''CREATE TABLE gold_municipios AS WITH oferta AS (
        SELECT codigo_municipio_admitido codigo_municipio,count(*)::BIGINT instalaciones,
            sum(puntos_registrados)::BIGINT puntos,sum(conectores_registrados)::BIGINT conectores
        FROM gold_recarga_instalaciones WHERE presente_copia_principal AND estado_admision='admitida_version_principal'
        GROUP BY 1), incertidumbre AS (
        SELECT codigo_municipio,count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='asignacion_pendiente') pendientes,
            count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='ausencia_exportacion') ausentes
        FROM gold_incertidumbre_recarga_municipio GROUP BY 1)
        SELECT ?::VARCHAR version_gold,m.codigo_municipio,m.codigo_provincia,m.nombre_municipio,r.geometria,
            p.fecha_referencia fecha_referencia_parque,p.parque_total,p.vehiculos_distintivo_0,
            p.vehiculos_distintivo_0::DOUBLE/nullif(p.parque_total,0) proporcion_distintivo_0,
            b.anio anio_poblacion,b.poblacion poblacion_total,b.estado_valor estado_poblacion,
            i.anio anio_renta,i.valor_eur renta_neta_media_persona_eur,i.estado_valor estado_renta,
            ?::TIMESTAMPTZ fecha_adquisicion_recarga,
            coalesce(o.instalaciones,0)::BIGINT instalaciones_con_municipio_admitido,
            coalesce(o.puntos,0)::BIGINT puntos_con_municipio_admitido,
            coalesce(o.conectores,0)::BIGINT conectores_con_municipio_admitido,
            p.vehiculos_distintivo_0::DOUBLE/nullif(o.puntos,0) distintivo_0_por_punto_admitido,
            CASE WHEN p.vehiculos_distintivo_0 IS NULL THEN 'sin_numerador_informado'
                WHEN coalesce(o.puntos,0)=0 THEN 'sin_puntos_admitidos' ELSE 'calculable' END estado_presion_descriptiva,
            coalesce(u.pendientes,0)::BIGINT instalaciones_pendientes_relacionadas,
            coalesce(u.ausentes,0)::BIGINT instalaciones_ausentes_relacionadas,
            EXISTS(SELECT 1 FROM avisos_recarga a ANTI JOIN gold_incertidumbre_recarga_municipio v
                USING(instalacion_id,tipo_incertidumbre)) hay_incertidumbre_sin_localizar
        FROM municipios m LEFT JOIN recintos_municipales r USING(codigo_municipio)
        LEFT JOIN parque_elegido p USING(codigo_municipio) LEFT JOIN poblacion_elegida b USING(codigo_municipio)
        LEFT JOIN renta_elegida i USING(codigo_municipio) LEFT JOIN oferta o USING(codigo_municipio)
        LEFT JOIN incertidumbre u USING(codigo_municipio)''', [version, acquisition])


def validate(c, version):
    nullable = {
        'gold_municipios': {'parque_total', 'vehiculos_distintivo_0', 'proporcion_distintivo_0',
                           'poblacion_total', 'renta_neta_media_persona_eur', 'distintivo_0_por_punto_admitido'},
        'gold_recarga_instalaciones': {'geometria', 'codigo_municipio_admitido', 'metodo_admision', 'fecha_adquisicion_observacion'},
        'gold_incertidumbre_recarga_municipio': set()}
    for name, keys in KEYS.items():
        check_key(c, name, keys)
        required = [r[0] for r in c.execute('DESCRIBE ' + name).fetchall() if r[0] not in nullable[name]]
        require_zero(c, 'SELECT count(*) FROM ' + name + ' WHERE ' +
                     ' OR '.join(ident(f) + ' IS NULL' for f in required), 'Campo obligatorio Gold nulo')
        if c.execute(f'SELECT count(*) FROM {name} WHERE version_gold IS DISTINCT FROM ?', [version]).fetchone()[0]:
            raise ValueError('Versión Gold incoherente')
    require_zero(c, '''SELECT count(*) FROM (
        (SELECT codigo_municipio FROM municipios EXCEPT SELECT codigo_municipio FROM gold_municipios) UNION ALL
        (SELECT codigo_municipio FROM gold_municipios EXCEPT SELECT codigo_municipio FROM municipios))''', 'Se altera la cobertura municipal')
    require_zero(c, '''SELECT count(*) FROM gold_municipios WHERE geometria IS NULL OR NOT ST_IsValid(geometria)
        OR parque_total<0 OR vehiculos_distintivo_0<0 OR vehiculos_distintivo_0>parque_total
        OR poblacion_total<0 OR instalaciones_con_municipio_admitido<0 OR puntos_con_municipio_admitido<0
        OR conectores_con_municipio_admitido<0 OR instalaciones_pendientes_relacionadas<0
        OR instalaciones_ausentes_relacionadas<0''', 'Valor municipal fuera del contrato')
    require_zero(c, '''SELECT count(*) FROM gold_municipios WHERE
        proporcion_distintivo_0 IS DISTINCT FROM vehiculos_distintivo_0::DOUBLE/nullif(parque_total,0)
        OR distintivo_0_por_punto_admitido IS DISTINCT FROM vehiculos_distintivo_0::DOUBLE/nullif(puntos_con_municipio_admitido,0)
        OR (distintivo_0_por_punto_admitido IS NOT NULL AND NOT isfinite(distintivo_0_por_punto_admitido))
        OR estado_presion_descriptiva IS DISTINCT FROM CASE WHEN vehiculos_distintivo_0 IS NULL
            THEN 'sin_numerador_informado' WHEN puntos_con_municipio_admitido=0 THEN 'sin_puntos_admitidos'
            ELSE 'calculable' END''', 'Cociente o estado de presión incorrecto')
    require_zero(c, '''SELECT count(*) FROM gold_municipios m JOIN parque_elegido p USING(codigo_municipio)
        JOIN poblacion_elegida b USING(codigo_municipio) JOIN renta_elegida r USING(codigo_municipio) WHERE
        m.parque_total IS DISTINCT FROM p.parque_total OR m.vehiculos_distintivo_0 IS DISTINCT FROM p.vehiculos_distintivo_0
        OR m.fecha_referencia_parque IS DISTINCT FROM p.fecha_referencia
        OR m.poblacion_total IS DISTINCT FROM b.poblacion OR m.estado_poblacion IS DISTINCT FROM b.estado_valor
        OR m.anio_poblacion IS DISTINCT FROM b.anio OR m.renta_neta_media_persona_eur IS DISTINCT FROM r.valor_eur
        OR m.estado_renta IS DISTINCT FROM r.estado_valor OR m.anio_renta IS DISTINCT FROM r.anio''', 'Se altera una observación demográfica')
    require_zero(c, '''SELECT count(*) FROM gold_recarga_instalaciones WHERE puntos_registrados IS NULL
        OR conectores_registrados IS NULL OR puntos_registrados<=0 OR conectores_registrados<puntos_registrados
        OR estado_admision NOT IN ('pendiente','admitida_version_principal','admitida_solo_historica')
        OR (estado_admision='pendiente' AND (codigo_municipio_admitido IS NOT NULL OR metodo_admision IS NOT NULL))
        OR (estado_admision<>'pendiente' AND (codigo_municipio_admitido IS NULL OR metodo_admision IS NULL))
        OR (presente_copia_principal AND (fecha_adquisicion_observacion IS NULL OR estado_admision='admitida_solo_historica'))
        OR (NOT presente_copia_principal AND (fecha_adquisicion_observacion IS NOT NULL OR estado_admision='admitida_version_principal'))''',
        'Presencia, recuento o admisión de recarga incoherente')
    require_zero(c, '''SELECT count(*) FROM gold_recarga_instalaciones g ANTI JOIN municipios m
        ON g.codigo_municipio_admitido=m.codigo_municipio WHERE g.codigo_municipio_admitido IS NOT NULL''', 'Admisión fuera de la referencia municipal')
    require_zero(c, '''SELECT count(*) FROM (
        (SELECT instalacion_id,presente_copia_principal FROM gold_recarga_instalaciones EXCEPT ALL
         (SELECT instalacion_id,true FROM recarga_instalaciones_geo UNION ALL SELECT instalacion_id,false FROM recarga_ausentes))
        UNION ALL
        ((SELECT instalacion_id,true FROM recarga_instalaciones_geo UNION ALL SELECT instalacion_id,false FROM recarga_ausentes)
         EXCEPT ALL SELECT instalacion_id,presente_copia_principal FROM gold_recarga_instalaciones))''', 'Se altera el universo presente o histórico')
    require_zero(c, '''SELECT count(*) FROM gold_incertidumbre_recarga_municipio u
        ANTI JOIN municipios m USING(codigo_municipio)''', 'Incertidumbre para municipio inexistente')
    require_zero(c, '''SELECT count(*) FROM gold_incertidumbre_recarga_municipio u
        LEFT JOIN gold_recarga_instalaciones g USING(instalacion_id) WHERE g.instalacion_id IS NULL
        OR NOT (es_municipio_admitido_historico OR es_municipio_declarado OR es_candidato_espacial)
        OR tipo_incertidumbre NOT IN ('asignacion_pendiente','ausencia_exportacion')
        OR (tipo_incertidumbre='asignacion_pendiente' AND (NOT presente_copia_principal OR estado_admision<>'pendiente'))
        OR (tipo_incertidumbre='ausencia_exportacion' AND presente_copia_principal)''', 'Vínculo de incertidumbre incoherente')
    require_zero(c, '''SELECT count(*) FROM gold_municipios m LEFT JOIN (
        SELECT codigo_municipio,count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='asignacion_pendiente') pendientes,
            count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='ausencia_exportacion') ausentes
        FROM gold_incertidumbre_recarga_municipio GROUP BY 1) u USING(codigo_municipio)
        WHERE m.instalaciones_pendientes_relacionadas<>coalesce(u.pendientes,0)
        OR m.instalaciones_ausentes_relacionadas<>coalesce(u.ausentes,0)
        OR m.hay_incertidumbre_sin_localizar IS DISTINCT FROM EXISTS(
            SELECT 1 FROM avisos_recarga ANTI JOIN gold_incertidumbre_recarga_municipio
            USING(instalacion_id,tipo_incertidumbre))''', 'Avisos municipales no reconciliados')
    require_zero(c, '''SELECT count(*) FROM gold_municipios m LEFT JOIN (
        SELECT v.codigo_municipio,count(DISTINCT g.instalacion_id) instalaciones,
            count(DISTINCT (p.instalacion_id,p.punto_id)) puntos,
            count(DISTINCT (c.instalacion_id,c.punto_id,c.conector_id)) conectores
        FROM recarga_instalaciones_geo g JOIN recarga_municipio_validado v USING(instalacion_id)
        JOIN recarga_puntos p USING(instalacion_id) JOIN recarga_conectores c USING(instalacion_id,punto_id)
        GROUP BY 1) o USING(codigo_municipio) WHERE
        m.instalaciones_con_municipio_admitido<>coalesce(o.instalaciones,0)
        OR m.puntos_con_municipio_admitido<>coalesce(o.puntos,0)
        OR m.conectores_con_municipio_admitido<>coalesce(o.conectores,0)''', 'Recuento de oferta no reconciliado con Silver')
    return {'tablas': {name: c.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in KEYS},
        'municipios_sin_puntos_admitidos': c.execute('SELECT count(*) FROM gold_municipios WHERE puntos_con_municipio_admitido=0').fetchone()[0],
        'renta_no_informada': c.execute('SELECT count(*) FROM gold_municipios WHERE renta_neta_media_persona_eur IS NULL').fetchone()[0],
        'oferta_principal': query(c, '''SELECT sum(instalaciones_con_municipio_admitido) instalaciones,
            sum(puntos_con_municipio_admitido) puntos,sum(conectores_con_municipio_admitido) conectores FROM gold_municipios''')[0],
        'estados_admision': query(c, 'SELECT presente_copia_principal,estado_admision,count(*) instalaciones FROM gold_recarga_instalaciones GROUP BY ALL ORDER BY 1,2'),
        'incertidumbre': query(c, '''SELECT tipo_incertidumbre,count(*) vinculos,count(DISTINCT instalacion_id) instalaciones,
            count(DISTINCT codigo_municipio) municipios FROM gold_incertidumbre_recarga_municipio GROUP BY 1 ORDER BY 1'''),
        'incertidumbre_sin_localizar': c.execute('''SELECT count(*) FROM avisos_recarga
            ANTI JOIN gold_incertidumbre_recarga_municipio USING(instalacion_id,tipo_incertidumbre)''').fetchone()[0]}


def main():
    directory = ROOT / 'resultados/gold/contexto_municipal'
    directory.mkdir(parents=True, exist_ok=True)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = directory / run
    codes = [checked(ROOT, ROOT / 'src' / name) for name in ('preparar_gold_municipal.py',
        'preparar_recarga_versionada.py', 'preparar_demografia_parque.py', 'georreferenciar_recarga.py',
        'validar_silver.py', 'catalogar_bronze.py', 'auditar_fuentes.py')]
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        with duckdb.connect(str(Path(tmp) / 'trabajo.duckdb'), config={'threads': 2, 'memory_limit': '1GB',
            'storage_compatibility_version': 'v1.5.0', 'temp_directory': str(Path(tmp) / 'desborde'),
            'extension_directory': str(ROOT / '.venv/duckdb_extensions')}) as c:
            c.execute('LOAD spatial')
            c.execute("SET TimeZone='UTC'")
            files, reports = load_inputs(c, ROOT)
            recarga = reports['recarga_versionada']
            acquisition = datetime.fromisoformat(recarga['fecha_adquisicion_utc'])
            if acquisition.tzinfo is None:
                raise ValueError('Adquisición de recarga sin zona horaria')
            historical = next(x for x in recarga['entradas_verificadas'] if x['ruta'] == SOURCE)
            origins = {'principal': 'miteco_recarga:' + recarga['entrada_seleccionada']['sha256'],
                       'historico': 'miteco_recarga:' + historical['sha256']}
            prepare(c, run, acquisition, origins['principal'], origins['historico'])
            quality = validate(c, run)
            outputs = write_outputs(c, target, KEYS)
            environment = {'duckdb': duckdb.__version__, 'spatial': c.execute(
                "SELECT extension_version FROM duckdb_extensions() WHERE extension_name='spatial'").fetchone()[0],
                'memoria_motor': '1GB', 'hilos': 2}
    unique = {}
    for entry in [*files, *codes]:
        if entry['ruta'] in unique and any(entry[k] != unique[entry['ruta']][k] for k in ('bytes', 'sha256')):
            raise ValueError('Entrada modificada entre lecturas')
        unique[entry['ruta']] = checked(ROOT, ROOT / entry['ruta'], entry)
    manifest = {'version_contrato': 1, 'version_gold': run,
        'fecha_proceso_utc': datetime.now(timezone.utc).isoformat(), 'entradas_verificadas': list(unique.values()),
        'ejecuciones_silver': {k: v['ejecucion'] for k, v in reports.items()}, 'origenes_recarga': origins,
        'periodos': {'parque': '2025-12-31', 'poblacion': 2025, 'renta': 2023,
                    'adquisicion_recarga_utc': acquisition.isoformat(), 'adquisicion_recarga_historica': None,
                    'referencia_municipios': reports['base_territorial']['referencia_ine'],
                    'consulta_recintos': reports['base_territorial']['fecha_consulta_ign'],
                    'edicion_historica_limites': None},
        'reglas': {'poblacion': "sexo='Total'", 'renta': "nivel_territorial='municipio'; indicador='Renta neta media por persona'",
                  'oferta': 'Solo presentes con admisión municipal; entidades agregadas por separado.',
                  'proporcion_distintivo_0': 'vehiculos_distintivo_0/parque_total; escala 0–1; nulo con parque cero.',
                  'presion': 'vehiculos_distintivo_0/puntos admitidos; nulo con denominador cero.',
                  'incertidumbre': 'Vínculos diagnósticos; no aditivos entre municipios; sin penalización numérica.'},
        'unidades': {'renta_neta_media_persona_eur': 'EUR/persona, media anual de la fuente',
                     'parque_y_poblacion': 'recuentos', 'presion': 'vehículos Distintivo 0/punto',
                     'geometria': 'EPSG:25830'}, 'codigo': codes, 'salidas': outputs, 'controles': quality, 'entorno': environment}
    (target / 'manifiesto.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = {'version_gold': run, 'estado': 'preparada_con_limitaciones', 'calidad': quality,
              'limitaciones': ['Presión descriptiva, no suficiencia operativa ni necesidad exacta.',
                  'Ausencias y asignaciones pendientes separadas de la oferta principal.',
                  'Periodos distintos y renta nula conservados; sin imputación.',
                  'Sin candidatos, cobertura de personas, ranking, pesos o modelo entrenado.']}
    (target / 'informe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    pointer = directory / 'actual.tmp'
    pointer.write_text(json.dumps({'ejecucion': run, 'manifiesto': f'{run}/manifiesto.json',
        'informe': f'{run}/informe.json'}, indent=2) + '\n', encoding='utf-8')
    pointer.replace(directory / 'actual.json')
    print(json.dumps(quality, ensure_ascii=False, indent=2))
    print('Informe:', (target / 'informe.json').relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
