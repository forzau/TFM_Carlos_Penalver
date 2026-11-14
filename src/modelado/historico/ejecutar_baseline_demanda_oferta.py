"""Baseline de dos entradas, validación espacial y prueba final reservada."""

import csv
import json
import math
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import sklearn
from sklearn.preprocessing import StandardScaler

from src.datos_y_preparacion.historico.auditar_fuentes import query
from src.datos_y_preparacion.historico.catalogar_bronze import ROOT
from src.modelado.historico.ejecutar_baseline_segmentacion import escribir_csv, resumen_numerico
from src.datos_y_preparacion.historico.georreferenciar_recarga import checked
from src.modelado.historico.preparar_experimento_segmentacion import geometria, estabilidad_por_codigo


PARTICIONES = 'resultados/modelado/particiones/20261106T110046844319Z'
GOLD = 'resultados/gold/contexto_municipal/20261020T153200478279Z'
VARIABLES = ('vehiculos_distintivo_0', 'puntos_con_municipio_admitido')
Z = ('z_log1p_vehiculos', 'z_log1p_puntos')
SEMILLA = 20261109
CONSULTA = '''SELECT p.version_gold,p.codigo_municipio,p.nombre_municipio,
    p.bloque_espacial,p.particion_interna,p.estrato_poblacion,
    g.vehiculos_distintivo_0,g.puntos_con_municipio_admitido,
    g.instalaciones_pendientes_relacionadas,g.instalaciones_ausentes_relacionadas,
    g.hay_incertidumbre_sin_localizar
    FROM particiones p LEFT JOIN gold_municipios g USING(version_gold,codigo_municipio)
    WHERE p.conjunto='desarrollo' ORDER BY p.codigo_municipio'''


def validar(filas):
    assert filas, 'Conjunto vacío'
    assert len(filas) == len({f['codigo_municipio'] for f in filas}), 'Códigos repetidos'
    for f in filas:
        for v in VARIABLES:
            x = f[v]
            assert x is not None and math.isfinite(float(x)) and x >= 0 and int(x) == x, (f['codigo_municipio'], v)


def ajustar(entrenamiento):
    validar(entrenamiento)
    return float(np.median([f[VARIABLES[0]] for f in entrenamiento]))


def asignar(filas, mediana):
    validar(filas)
    assert math.isfinite(mediana) and mediana >= 0
    return {f['codigo_municipio']: ('I' if f[VARIABLES[0]] <= mediana else 'S') +
            ('-0' if f[VARIABLES[1]] == 0 else '-P') for f in filas}


def preparar(entrenamiento, validacion):
    validar(entrenamiento)
    if validacion:
        validar(validacion)
    assert {f['codigo_municipio'] for f in entrenamiento}.isdisjoint(f['codigo_municipio'] for f in validacion)
    assert {f['bloque_espacial'] for f in entrenamiento}.isdisjoint(f['bloque_espacial'] for f in validacion)
    matrices = [np.log1p(np.asarray([[f[v] for v in VARIABLES] for f in filas], dtype=float).reshape(-1, 2))
                for filas in (entrenamiento, validacion)]
    scaler = StandardScaler().fit(matrices[0])
    salida = []
    for rol, filas, x in zip(('entrenamiento', 'validacion'), (entrenamiento, validacion), matrices):
        zs = scaler.transform(x) if filas else np.empty((0, 2))
        assert np.isfinite(zs).all()
        salida.append([dict(f, rol=rol, **dict(zip(Z, z.tolist()))) for f, z in zip(filas, zs)])
    parametros = {'n_entrenamiento': len(entrenamiento), 'n_validacion': len(validacion),
                  'media_log1p': scaler.mean_.tolist(), 'varianza_log1p': scaler.var_.tolist(),
                  'escala': scaler.scale_.tolist()}
    return *salida, parametros


def planes_estabilidad(entrenamiento, semilla):
    bloques = sorted({f['bloque_espacial'] for f in entrenamiento})
    n = math.ceil(.1 * len(bloques))
    if n >= len(bloques) or math.comb(len(bloques), n) < 10:
        raise ValueError('No hay diez omisiones distintas viables')
    rng, planes = random.Random(semilla), []
    for _ in range(1000):
        omitidos = sorted(rng.sample(bloques, n))
        if any(p['bloques_omitidos'] == omitidos for p in planes):
            continue
        planes.append({'repeticion': len(planes) + 1, 'bloques_omitidos': omitidos})
        if len(planes) == 10:
            return planes
    raise ValueError('No se consiguieron diez omisiones distintas')


def sin_avisos(f):
    return not (f['instalaciones_pendientes_relacionadas'] or
                f['instalaciones_ausentes_relacionadas'] or f['hay_incertidumbre_sin_localizar'])


def evaluar(filas, etiquetas):
    return geometria([[f[z] for z in Z] for f in filas], [etiquetas[f['codigo_municipio']] for f in filas])


def perfiles(filas, etiquetas):
    salida = []
    for etiqueta in sorted(set(etiquetas.values())):
        grupo = [f for f in filas if etiquetas[f['codigo_municipio']] == etiqueta]
        x = np.asarray([[f[z] for z in Z] for f in grupo])
        orden = sorted(range(len(grupo)), key=lambda i: (float(((x[i] - x.mean(axis=0)) ** 2).sum()), grupo[i]['codigo_municipio']))
        salida.append({'perfil': etiqueta, 'n': len(grupo), 'porcentaje': 100 * len(grupo) / len(filas),
                       'municipios_con_avisos': sum(not sin_avisos(f) for f in grupo),
                       'variables': {v: dict(zip(('min', 'q25', 'mediana', 'q75', 'max'),
                                               np.quantile([f[v] for f in grupo], [0, .25, .5, .75, 1]).tolist())) for v in VARIABLES},
                       'ejemplos': [{'codigo': grupo[i]['codigo_municipio'], 'nombre': grupo[i]['nombre_municipio']} for i in orden[:3]]})
    assert sum(p['n'] for p in salida) == len(filas)
    return salida


def cargar_desarrollo():
    fuentes = []
    ruta_particiones = ROOT / PARTICIONES / 'manifiesto.json'
    fuentes.append(checked(ROOT, ruta_particiones))
    doc_p = json.loads(ruta_particiones.read_text(encoding='utf-8'))
    for e in doc_p['salidas']:
        sello = checked(ROOT, ROOT / e['ruta'])
        assert sello['sha256'] == e['sha256'], e['ruta']
        fuentes.append(sello)
    config = ROOT / 'config/exclusiones_segmentacion.json'
    fuentes.append(checked(ROOT, config))
    excluidos = {x['codigo_municipio'] for x in json.loads(config.read_text(encoding='utf-8'))['municipios_excluidos']}
    assert excluidos == {'46201'}
    ruta_gold = ROOT / GOLD / 'manifiesto.json'
    fuentes.append(checked(ROOT, ruta_gold))
    doc_g = json.loads(ruta_gold.read_text(encoding='utf-8'))
    with duckdb.connect(config={'threads': 2, 'memory_limit': '1GB'}) as c:
        c.read_parquet(str(ROOT / PARTICIONES / 'particiones_municipales.parquet')).create_view('particiones')
        for e in doc_g['salidas']:
            path = ruta_gold.parent / e['archivo']
            fuentes.append(checked(ROOT, path, e))
            c.read_parquet(str(path)).create_view(path.stem)
        diseno = query(c, 'SELECT codigo_municipio,conjunto,bloque_espacial,particion_interna FROM particiones')
        assert len(diseno) == len({f['codigo_municipio'] for f in diseno}) == 541
        test = {f['codigo_municipio'] for f in diseno if f['conjunto'] == 'prueba_final'}
        filas = query(c, CONSULTA)
        assert len(filas) == len({f['codigo_municipio'] for f in filas}) == 433 and len(test) == 108
        assert {f['codigo_municipio'] for f in filas}.isdisjoint(test | excluidos)
        assert {f['codigo_municipio'] for f in filas} == {f['codigo_municipio'] for f in diseno if f['conjunto'] == 'desarrollo'}
        assert Counter(f['particion_interna'] for f in filas) == {1: 108, 2: 108, 3: 109, 4: 108}
        assert {f['bloque_espacial'] for f in filas}.isdisjoint(f['bloque_espacial'] for f in diseno if f['conjunto'] == 'prueba_final')
        assert len({f['version_gold'] for f in filas}) == 1 and filas[0]['version_gold'] == doc_g['version_gold']
        validar(filas)
        for f in filas:
            assert all(f[v] is not None and f[v] >= 0 for v in ('instalaciones_pendientes_relacionadas', 'instalaciones_ausentes_relacionadas'))
            assert isinstance(f['hay_incertidumbre_sin_localizar'], bool)
        c.execute("CREATE TEMP VIEW desarrollo AS SELECT codigo_municipio FROM particiones WHERE conjunto='desarrollo'")
        oferta = query(c, '''SELECT codigo_municipio_admitido codigo_municipio,sum(puntos_registrados)::BIGINT puntos
            FROM gold_recarga_instalaciones JOIN desarrollo ON codigo_municipio_admitido=codigo_municipio
            WHERE presente_copia_principal AND estado_admision='admitida_version_principal' GROUP BY 1''')
        avisos = query(c, '''SELECT codigo_municipio,
            count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='asignacion_pendiente') pendientes,
            count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='ausencia_exportacion') ausentes
            FROM gold_incertidumbre_recarga_municipio JOIN desarrollo USING(codigo_municipio) GROUP BY 1''')
    por_oferta = {f['codigo_municipio']: f['puntos'] for f in oferta}
    por_aviso = {f['codigo_municipio']: f for f in avisos}
    for f in filas:
        codigo = f['codigo_municipio']
        assert f[VARIABLES[1]] == por_oferta.get(codigo, 0)
        assert f['instalaciones_pendientes_relacionadas'] == por_aviso.get(codigo, {}).get('pendientes', 0)
        assert f['instalaciones_ausentes_relacionadas'] == por_aviso.get(codigo, {}).get('ausentes', 0)
    return filas, fuentes


def guardar_json(ruta, doc):
    ruta.write_text(json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def main():
    desarrollo, fuentes = cargar_desarrollo()
    planes = {f'interna_{i}': planes_estabilidad([f for f in desarrollo if f['particion_interna'] != i], SEMILLA + i) for i in range(1, 5)}
    ejecucion = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    salida = ROOT / 'resultados/modelado/baseline_demanda_oferta' / ejecucion
    salida.mkdir(parents=True, exist_ok=False)
    protocolo = {'entradas': VARIABLES, 'columnas_distancias': Z,
                 'baseline': 'Mediana de vehículos solo en entrenamiento; <= frente >; puntos cero frente positivos. I-0/I-P/S-0/S-P, sin prioridad.',
                 'preparacion': 'log1p de ambas entradas y StandardScaler ddof=0 solo entrenamiento; divisor1 si constante. Reglas sobre originales.',
                 'calidad': 'Mantener recuentos admitidos y avisos, sin imputación. Fallar si falta una entrada. Sensibilidad: retirar municipios con avisos de entrenamiento/validación; comparar solo códigos comunes.',
                 'geometria': 'Silhouette euclídea en validación sin reajustar; media no ponderada de cuatro validaciones y rango. Misma representación futura para ML.',
                 'estabilidad': 'Diez omisiones distintas de ceil(10% de bloques de entrenamiento) por interna; muestreo sin reemplazo dentro de cada repetición. Recalcular corte y preparación. Sin restricción de donantes de renta.',
                 'semilla': SEMILLA, 'planes_estabilidad': planes,
                 'separacion': 'Particiones espaciales originales,433 desarrollo/108 prueba. Prueba solo metadatos; no se evalúa.',
                 'estado': 'Congelado antes de calcular métricas. No buscar configuraciones para elevar resultados.'}
    guardar_json(salida / 'protocolo.json', protocolo)
    validaciones, oof, perturbaciones, sensibilidad, preparados = [], [], [], [], []
    parametros = {}
    for i in range(1, 5):
        nombre = f'interna_{i}'
        train = [f for f in desarrollo if f['particion_interna'] != i]
        val = [f for f in desarrollo if f['particion_interna'] == i]
        a, b, params = preparar(train, val)
        corte = ajustar(a)
        etiquetas = asignar(b, corte)
        g = evaluar(b, etiquetas)
        parametros[nombre] = {'preparacion': params, 'mediana_vehiculos': corte}
        preparados.extend(dict(f, ajuste=nombre) for f in a + b)
        oof.extend(dict(f, ajuste=nombre, perfil=etiquetas[f['codigo_municipio']], silhouette=s)
                   for f, s in zip(b, g.get('por_municipio_en_orden', [None] * len(b))))
        estabilidad = []
        for plan in planes[nombre]:
            sub = [f for f in train if f['bloque_espacial'] not in plan['bloques_omitidos']]
            pa, pb, pp = preparar(sub, val)
            umbral = ajustar(pa)
            otras = asignar(pb, umbral)
            ari = estabilidad_por_codigo(etiquetas, otras)
            estabilidad.append({**plan, 'mediana_vehiculos': umbral, 'preparacion': pp, 'ari': ari})
            perturbaciones.extend({'ajuste': nombre, 'repeticion': plan['repeticion'], 'codigo_municipio': c,
                                   'perfil_principal': etiquetas[c], 'perfil_perturbado': otras[c]} for c in sorted(otras))
        ca, cb, cp = preparar([f for f in train if sin_avisos(f)], [f for f in val if sin_avisos(f)])
        cc = ajustar(ca)
        ce = asignar(cb, cc)
        comunes = {c: etiquetas[c] for c in ce}
        cs = {'n_train': len(ca), 'n_val': len(cb), 'mediana_vehiculos': cc, 'preparacion': cp,
              'ari_sobre_comunes': estabilidad_por_codigo(comunes, ce), 'geometria': evaluar(cb, ce),
              'cambios_literal': [c for c in sorted(ce) if ce[c] != etiquetas[c]]}
        sensibilidad.extend({'ajuste': nombre, 'codigo_municipio': c, 'perfil_principal': etiquetas[c],
                             'perfil_sin_avisos': ce[c]} for c in sorted(ce))
        validaciones.append({'ajuste': nombre, 'n_train': len(train), 'n_val': len(val), 'mediana_vehiculos': corte,
                             'cobertura': len(etiquetas) / len(val), 'geometria': g, 'perfiles': perfiles(b, etiquetas),
                             'estabilidad': estabilidad, 'ari_estabilidad': resumen_numerico([x['ari'] for x in estabilidad]),
                             'sensibilidad_sin_avisos': cs})
    a, _, params = preparar(desarrollo, [])
    corte = ajustar(a)
    etiquetas = asignar(a, corte)
    parametros['desarrollo_completo'] = {'preparacion': params, 'mediana_vehiculos': corte}
    preparados.extend(dict(f, ajuste='desarrollo_completo') for f in a)
    assert len(oof) == len({f['codigo_municipio'] for f in oof}) == 433
    assert {f['codigo_municipio'] for f in oof} == {f['codigo_municipio'] for f in desarrollo}
    assert len(perturbaciones) == 4330 and len(preparados) == 2165
    assert len(sensibilidad) == sum(sin_avisos(f) for f in desarrollo)
    resumen = {'silhouette': resumen_numerico([x['geometria']['silhouette'] for x in validaciones if x['geometria']['silhouette'] is not None]),
               'ari_estabilidad': resumen_numerico([p['ari'] for x in validaciones for p in x['estabilidad']]),
               'ari_sensibilidad_sin_avisos': resumen_numerico([x['sensibilidad_sin_avisos']['ari_sobre_comunes'] for x in validaciones]),
               'cobertura': 1.0, 'n_desarrollo': 433, 'n_con_avisos': sum(not sin_avisos(f) for f in desarrollo),
               'n_sin_puntos': sum(f[VARIABLES[1]] == 0 for f in desarrollo),
               'n_sin_puntos_con_avisos': sum(f[VARIABLES[1]] == 0 and not sin_avisos(f) for f in desarrollo),
               'n_prueba_evaluados': 0, 'n_ajustes_baseline': 49}
    resultado = {'ejecucion': ejecucion, 'resumen': resumen, 'validaciones': validaciones,
                 'descriptivo': {'n': len(a), 'mediana_vehiculos': corte, 'perfiles': perfiles(a, etiquetas),
                                 'cautela': 'Descripción de entrenamiento de433, no evaluación ni asignación de541.'},
                 'limites': ['Bloques20km sin banda de separación; no garantizan independencia espacial.',
                            'Presencia de registro no acredita servicio; avisos no cuantifican oferta faltante.',
                            'Excluir avisos mide sensibilidad conjunta, no corrige asignaciones inciertas.',
                            'Medias/rangos de validaciones y perturbaciones no son intervalos de confianza.',
                            'No comparar directamente estas métricas de dos entradas con las de tres entradas anteriores.',
                            'Ningún perfil demuestra necesidad de recarga, suficiencia, urgencia o prioridad.']}
    guardar_json(salida / 'resultados.json', resultado)
    guardar_json(salida / 'preparaciones.json', parametros)
    escribir_csv(salida / 'entradas_desarrollo.csv', desarrollo)
    escribir_csv(salida / 'entradas_preparadas.csv', preparados)
    escribir_csv(salida / 'asignaciones_validacion.csv', oof)
    escribir_csv(salida / 'estabilidad_asignaciones.csv', perturbaciones)
    escribir_csv(salida / 'sensibilidad_asignaciones.csv', sensibilidad)
    escribir_csv(salida / 'perfiles_desarrollo.csv', [dict(f, perfil=etiquetas[f['codigo_municipio']]) for f in a])
    escribir_csv(salida / 'metricas_validacion.csv', [{'ajuste': x['ajuste'], 'n_train': x['n_train'], 'n_val': x['n_val'],
                  'mediana_vehiculos': x['mediana_vehiculos'], 'silhouette': x['geometria']['silhouette'],
                  'fraccion_negativa': x['geometria'].get('fraccion_negativa'), 'k_observado': x['geometria']['k'],
                  'cobertura': x['cobertura'], 'ari_estabilidad_medio': x['ari_estabilidad']['media'],
                  'ari_estabilidad_min': x['ari_estabilidad']['min'],
                  'ari_sensibilidad_sin_avisos': x['sensibilidad_sin_avisos']['ari_sobre_comunes']} for x in validaciones])
    for e in fuentes:
        checked(ROOT, ROOT / e['ruta'], e)
    guardar_json(salida / 'manifiesto.json', {'ejecucion': ejecucion, 'fuentes': fuentes,
                 'productor': checked(ROOT, Path(__file__)),
                 'apoyos': [checked(ROOT, ROOT / 'src' / n) for n in ('rutas.py', 'modelado/historico/preparar_experimento_segmentacion.py', 'modelado/historico/ejecutar_baseline_segmentacion.py', 'datos_y_preparacion/historico/georreferenciar_recarga.py')],
                 'salidas': [checked(ROOT, p) for p in sorted(salida.iterdir())],
                 'versiones': {'numpy': np.__version__, 'sklearn': sklearn.__version__, 'duckdb': duckdb.__version__},
                 'controles': '433 OOF únicos,4330 perturbaciones,2165 preparados; oferta/avisos reconciliados; sin renta ni test.'})
    print(json.dumps({'carpeta': salida.relative_to(ROOT).as_posix(), 'resumen': resumen,
                      'validaciones': [{'ajuste': x['ajuste'], 'corte': x['mediana_vehiculos'], 'silhouette': x['geometria']['silhouette'], 'ari': x['ari_estabilidad']} for x in validaciones],
                      'descriptivo': resultado['descriptivo']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
