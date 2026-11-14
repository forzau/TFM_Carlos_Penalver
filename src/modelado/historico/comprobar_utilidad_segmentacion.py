"""Piloto descriptivo de perfiles y oferta registrada; solo desarrollo, sin ajustar modelos."""

import csv
import json
import math
from datetime import datetime, timezone
from statistics import median

import duckdb

from src.datos_y_preparacion.historico.auditar_fuentes import query
from src.datos_y_preparacion.historico.catalogar_bronze import ROOT
from src.modelado.historico.ejecutar_baseline_segmentacion import escribir_csv
from src.datos_y_preparacion.historico.georreferenciar_recarga import checked


COMPARACION = 'resultados/modelado/comparacion_ml/20261107T114151583233Z'
PARTICIONES = 'resultados/modelado/particiones/20261106T110046844319Z'
GOLD = 'resultados/gold/contexto_municipal/20261020T153200478279Z'
Z = ('z_log1p_volumen', 'z_proporcion', 'z_renta')
CONSULTAS = {
    'oferta': '''SELECT m.version_gold,m.codigo_municipio,m.codigo_provincia,
        m.poblacion_total,m.vehiculos_distintivo_0,m.proporcion_distintivo_0,
        m.instalaciones_con_municipio_admitido instalaciones,
        m.puntos_con_municipio_admitido puntos,m.conectores_con_municipio_admitido conectores,
        m.distintivo_0_por_punto_admitido presion,
        m.instalaciones_pendientes_relacionadas pendientes,
        m.instalaciones_ausentes_relacionadas ausentes,
        m.hay_incertidumbre_sin_localizar sin_localizar,
        m.fecha_referencia_parque,m.anio_poblacion,
        (m.fecha_adquisicion_recarga AT TIME ZONE 'UTC')::VARCHAR || '+00:00' fecha_adquisicion_recarga_utc
        FROM gold_municipios m JOIN codigos_desarrollo USING(codigo_municipio)
        ORDER BY m.codigo_municipio''',
    'recuento_instalaciones': '''SELECT r.codigo_municipio_admitido codigo_municipio,
        count(*) instalaciones,sum(r.puntos_registrados)::BIGINT puntos,
        sum(r.conectores_registrados)::BIGINT conectores
        FROM gold_recarga_instalaciones r JOIN codigos_desarrollo d
        ON r.codigo_municipio_admitido=d.codigo_municipio
        WHERE r.presente_copia_principal AND r.estado_admision='admitida_version_principal'
        GROUP BY 1''',
    'recuento_avisos': '''SELECT u.codigo_municipio,
        count(DISTINCT u.instalacion_id) FILTER(WHERE tipo_incertidumbre='asignacion_pendiente') pendientes,
        count(DISTINCT u.instalacion_id) FILTER(WHERE tipo_incertidumbre='ausencia_exportacion') ausentes
        FROM gold_incertidumbre_recarga_municipio u
        JOIN codigos_desarrollo USING(codigo_municipio) GROUP BY 1''',
}


def validar_desarrollo(filas, particiones):
    codigos = [f['codigo_municipio'] for f in filas]
    desarrollo = {f['codigo_municipio'] for f in particiones if f['conjunto'] == 'desarrollo'}
    prueba = {f['codigo_municipio'] for f in particiones if f['conjunto'] == 'prueba_final'}
    assert len(codigos) == len(set(codigos)), 'Asignaciones municipales duplicadas'
    assert set(codigos) == desarrollo and set(codigos).isdisjoint(prueba), 'Ámbito distinto de desarrollo'
    assert all(all(math.isfinite(float(f[z])) for z in Z) for f in filas)


def unir_oferta(filas, oferta):
    por_codigo = {f['codigo_municipio']: f for f in oferta}
    assert len(por_codigo) == len(oferta), 'Oferta municipal duplicada'
    assert set(por_codigo) == {f['codigo_municipio'] for f in filas}, 'Oferta sin cobertura exacta'
    salida = []
    for fila in filas:
        o = por_codigo[fila['codigo_municipio']]
        assert fila['version_gold'] == o['version_gold']
        for variable in ('vehiculos_distintivo_0', 'proporcion_distintivo_0'):
            assert math.isclose(float(fila[variable]), o[variable], rel_tol=1e-12, abs_tol=1e-12)
        assert all(o[k] >= 0 for k in ('instalaciones', 'puntos', 'conectores', 'pendientes', 'ausentes'))
        esperado = o['vehiculos_distintivo_0'] / o['puntos'] if o['puntos'] else None
        assert ((esperado is None and o['presion'] is None) or
                (esperado is not None and o['presion'] is not None and
                 math.isclose(esperado, o['presion'], rel_tol=1e-12)))
        salida.append({**fila, **o, 'grupo': int(fila['grupo']),
                       'renta_modelado_2023_eur': float(fila['renta_modelado_2023_eur'])})
    return salida


def vecinos(ancla, filas, n=3):
    candidatos = [f for f in filas if f['grupo'] == ancla['grupo'] and
                  f['codigo_municipio'] != ancla['codigo_municipio']]
    return sorted(((math.dist([float(ancla[z]) for z in Z], [float(f[z]) for z in Z]), f)
                   for f in candidatos), key=lambda x: (x[0], x[1]['codigo_municipio']))[:n]


def resumen_grupo(filas):
    avisos = lambda f: f['pendientes'] > 0 or f['ausentes'] > 0
    presiones = [f['presion'] for f in filas if f['presion'] is not None]
    return {'grupo': filas[0]['grupo'], 'municipios': len(filas),
            'sin_puntos_admitidos': sum(f['puntos'] == 0 for f in filas),
            'porcentaje_sin_puntos': 100 * sum(f['puntos'] == 0 for f in filas) / len(filas),
            'municipios_con_avisos': sum(avisos(f) for f in filas),
            'sin_puntos_con_avisos': sum(f['puntos'] == 0 and avisos(f) for f in filas),
            'instalaciones': sum(f['instalaciones'] for f in filas),
            'puntos': sum(f['puntos'] for f in filas),
            'mediana_puntos': median(f['puntos'] for f in filas),
            'mediana_presion_solo_con_puntos': median(presiones) if presiones else None,
            'municipios_presion_calculable': len(presiones),
            'min_distintivo_0': min(f['vehiculos_distintivo_0'] for f in filas),
            'max_distintivo_0': max(f['vehiculos_distintivo_0'] for f in filas)}


def main():
    entradas = []
    for carpeta, nombres in ((COMPARACION, ('asignaciones_desarrollo.csv', 'kmeans_k3.json')),
                              (PARTICIONES, ('particiones_municipales.csv',))):
        manifiesto = ROOT / carpeta / 'manifiesto.json'
        entradas.append(checked(ROOT, manifiesto))
        doc = json.loads(manifiesto.read_text(encoding='utf-8'))
        for nombre in nombres:
            ruta = f'{carpeta}/{nombre}'
            e = next(x for x in doc['salidas'] if x['ruta'] == ruta)
            sello = checked(ROOT, ROOT / ruta)
            assert sello['sha256'] == e['sha256'], ruta
            entradas.append(sello)
    with (ROOT / COMPARACION / 'asignaciones_desarrollo.csv').open(encoding='utf-8', newline='') as f:
        filas = [x for x in csv.DictReader(f) if x['metodo'] == 'kmeans' and x['k_configurado'] == '3']
    with (ROOT / PARTICIONES / 'particiones_municipales.csv').open(encoding='utf-8', newline='') as f:
        particiones = list(csv.DictReader(f))
    validar_desarrollo(filas, particiones)
    assert len(filas) == 433 and len({x['codigo_municipio'] for x in particiones}) == 541
    assert {int(f['grupo']) for f in filas} == {0, 1, 2}
    assert all(f['rol'] == 'entrenamiento' for f in filas)
    manifiesto_gold = ROOT / GOLD / 'manifiesto.json'
    entradas.append(checked(ROOT, manifiesto_gold))
    doc_gold = json.loads(manifiesto_gold.read_text(encoding='utf-8'))
    with duckdb.connect(config={'threads': 2, 'memory_limit': '1GB'}) as c:
        c.execute('CREATE TEMP TABLE codigos_desarrollo(codigo_municipio VARCHAR PRIMARY KEY)')
        c.executemany('INSERT INTO codigos_desarrollo VALUES (?)', [(f['codigo_municipio'],) for f in filas])
        for e in doc_gold['salidas']:
            ruta = ROOT / GOLD / e['archivo']
            entradas.append(checked(ROOT, ruta, e))
            c.read_parquet(str(ruta)).create_view(ruta.stem)
        filas = unir_oferta(filas, query(c, CONSULTAS['oferta']))
        recuentos = {x['codigo_municipio']: x for x in query(c, CONSULTAS['recuento_instalaciones'])}
        avisos = {x['codigo_municipio']: x for x in query(c, CONSULTAS['recuento_avisos'])}
    for fila in filas:
        for campos, calculados in ((('instalaciones', 'puntos', 'conectores'), recuentos),
                                    (('pendientes', 'ausentes'), avisos)):
            for campo in campos:
                assert fila[campo] == calculados.get(fila['codigo_municipio'], {}).get(campo, 0)
    perfiles = json.loads((ROOT / COMPARACION / 'kmeans_k3.json').read_text(encoding='utf-8'))['descriptivo']['perfiles']
    por_codigo = {f['codigo_municipio']: f for f in filas}
    pares = []
    for perfil in perfiles:
        for ejemplo in perfil['ejemplos_cercanos_a_media_grupo']:
            ancla = por_codigo[ejemplo['codigo']]
            for orden, (distancia, vecino) in enumerate(vecinos(ancla, filas), 1):
                par = {'grupo': ancla['grupo'], 'orden_vecino': orden, 'distancia_z': distancia}
                for prefijo, item in (('ancla', ancla), ('vecino', vecino)):
                    for campo in ('codigo_municipio', 'nombre_municipio', 'vehiculos_distintivo_0',
                                  'proporcion_distintivo_0', 'renta_modelado_2023_eur',
                                  'estado_renta_modelado', 'puntos', 'presion', 'pendientes', 'ausentes'):
                        par[f'{prefijo}_{campo}'] = item[campo]
                pares.append(par)
    # Selección ilustrativa por similitud; la oferta nunca interviene en el orden.
    seleccion = [min((p for p in pares if p['grupo'] == g and p['orden_vecino'] == 1),
                     key=lambda p: (p['distancia_z'], p['ancla_codigo_municipio'], p['vecino_codigo_municipio']))
                 for g in range(3)]
    resumen = [resumen_grupo([f for f in filas if f['grupo'] == g]) for g in range(3)]
    assert sum(g['municipios'] for g in resumen) == 433
    assert len(pares) == 27 and len(seleccion) == 3
    for e in entradas:
        checked(ROOT, ROOT / e['ruta'], e)
    ejecucion = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    salida = ROOT / 'resultados/modelado/utilidad_kmeans' / ejecucion
    salida.mkdir(parents=True, exist_ok=False)
    escribir_csv(salida / 'municipios_desarrollo.csv', filas)
    escribir_csv(salida / 'resumen_grupos.csv', resumen)
    escribir_csv(salida / 'comparaciones_representantes.csv', pares)
    escribir_csv(salida / 'ejemplos_por_similitud.csv', seleccion)
    resultado = {'ejecucion': ejecucion, 'caracter': 'piloto_exploratorio_descriptivo_en_desarrollo',
                 'n_municipios': len(filas), 'n_prueba_evaluados': 0, 'n_ajustes_nuevos': 0,
                 'regla_seleccion': 'Nueve representantes ya guardados; tres vecinos del mismo grupo '
                 'por distancia euclídea en Z guardadas. Para ilustrar cada grupo se elige la pareja '
                 'más cercana de representante y primer vecino, sin seleccionar por oferta.',
                 'resumen_grupos': resumen, 'ejemplos_por_similitud': seleccion,
                 'limites': ['Exploración sobre entrenamiento, no validación de utilidad real ni evaluación final.',
                            'Sin puntos admitidos significa cero registros con municipio admitido en esta copia.',
                            'Oferta adquirida 18-10-2026, parque 31-12-2025 y renta 2023.',
                            'No se evalúan potencia, disponibilidad, ocupación, recarga privada o accesibilidad vecina.',
                            'Mismo grupo no garantiza similitud suficiente; revisar los tres valores municipales.',
                            'La presión es descriptiva; denominador cero produce nulo, nunca infinito o prioridad.'],
                 'comprobaciones': ['433 códigos únicos idénticos al desarrollo, sin prueba final.',
                                    'Join 1:1 y versión Gold e inputs del modelo reconciliados.',
                                    '433 recuentos de oferta y avisos contrastados con tablas Gold de detalle.',
                                    'Presiones recalculadas desde operandos; ceros y nulos conservados.',
                                    'Huellas de entradas comprobadas antes y después.'],
                 'consultas_sql': CONSULTAS, 'entradas_verificadas': entradas,
                 'productor': checked(ROOT, ROOT / 'src/modelado/historico/comprobar_utilidad_segmentacion.py')}
    (salida / 'resultados.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=str,
                                                     allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'carpeta': salida.relative_to(ROOT).as_posix(), 'resumen': resumen,
                      'ejemplos': seleccion}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
