"""K-means y GMM sobre el universo descriptivo, con protocolo previo e histórico intacto."""

import csv
import json
import platform
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from threadpoolctl import threadpool_limits

from src.datos_y_preparacion.historico.catalogar_bronze import ROOT
from src.modelado.pasos import baseline as _baseline
from src.modelado.historico.ejecutar_baseline_demanda_oferta import (
    VARIABLES, Z, evaluar, perfiles, sin_avisos, guardar_json, escribir_csv,
    resumen_numerico, estabilidad_por_codigo,
)
from src.datos_y_preparacion.historico.georreferenciar_recarga import checked


BASELINE = 'resultados/modelado/baseline_descriptivo/20261111T160303732930Z'
METODOS = ('kmeans', 'gmm')
K = tuple(range(2, 7))
SEMILLAS_EXTRA = tuple(_baseline.SEMILLA + i for i in (100, 200, 300, 400))
PARAMETROS = {
    'kmeans': dict(init='k-means++', n_init=20, max_iter=500, tol=1e-4, algorithm='lloyd'),
    'gmm': dict(covariance_type='full', init_params='kmeans', n_init=10,
                max_iter=500, tol=1e-3, reg_covar=1e-6),
}


def matriz(filas):
    assert filas and len(filas) == len({f['codigo_municipio'] for f in filas})
    x = np.asarray([[f[z] for z in Z] for f in filas], dtype=float)
    assert x.shape == (len(filas), 2) and np.isfinite(x).all()
    return x


def ajustar(metodo, k, semilla, muestra, universo):
    if metodo not in METODOS or k not in K:
        raise ValueError('Método o número de grupos fuera del protocolo.')
    x, u = matriz(muestra), matriz(universo)
    por_codigo = {f['codigo_municipio']: f for f in universo}
    assert all(f['codigo_municipio'] in por_codigo and
               all(f[z] == por_codigo[f['codigo_municipio']][z] for z in Z) for f in muestra)
    assert len(np.unique(x, axis=0)) >= k, 'Menos posiciones distintas que grupos solicitados'
    modelo = (KMeans(n_clusters=k, **PARAMETROS[metodo], random_state=semilla) if metodo == 'kmeans'
              else GaussianMixture(n_components=k, **PARAMETROS[metodo], random_state=semilla))
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter('always')
        modelo.fit(x)
    etiquetas = dict(zip((f['codigo_municipio'] for f in universo), modelo.predict(u).tolist()))
    assert all(0 <= e < k for e in etiquetas.values())
    info = {'semilla': semilla, 'n_ajuste': len(muestra), 'n_descripcion': len(universo),
            'parametros': modelo.get_params(), 'n_iter': int(modelo.n_iter_),
            'avisos': [str(a.message) for a in avisos],
            'k_observado_ajuste': len(set(modelo.predict(x).tolist())),
            'k_observado_descripcion': len(set(etiquetas.values()))}
    if metodo == 'gmm':
        proba = modelo.predict_proba(u)
        assert np.isfinite(proba).all() and (proba >= 0).all() and np.allclose(proba.sum(axis=1), 1)
        info.update(convergencia=bool(modelo.converged_),
                    limite_inferior=float(modelo.lower_bound_),
                    menor_autovalor_covarianza=float(np.linalg.eigvalsh(modelo.covariances_).min()),
                    menor_peso=float(modelo.weights_.min()),
                    pertenencia_maxima=resumen_numerico(proba.max(axis=1).tolist()))
    else:
        info['inercia'] = float(modelo.inertia_)
    return modelo, etiquetas, info


def main(baseline=BASELINE):
    base = (ROOT / baseline).resolve()
    baseline = base.relative_to(ROOT.resolve()).as_posix()
    universo, fuentes = _baseline.cargar_universo()
    mf = json.loads((base / 'manifiesto.json').read_text(encoding='utf-8'))
    for e in mf['fuentes'] + mf['salidas'] + mf['apoyos'] + [mf['productor']]:
        checked(ROOT, ROOT / e['ruta'], e)
    fuentes.extend(checked(ROOT, base / n) for n in ('manifiesto.json', 'protocolo.json', 'resultados.json', 'asignaciones_municipales.csv'))
    bd = json.loads((base / 'resultados.json').read_text(encoding='utf-8'))
    bp = json.loads((base / 'protocolo.json').read_text(encoding='utf-8'))
    planes = bp['planes_estabilidad']
    completos, params = _baseline.representar(universo, universo)
    assert params == bd['preparacion_principal'] and len(planes) == 10
    with (base / 'asignaciones_municipales.csv').open(encoding='utf-8', newline='') as f:
        anteriores = list(csv.DictReader(f))
    assert [f['codigo_municipio'] for f in completos] == [f['codigo_municipio'] for f in anteriores]
    assert all(all(f[v] == int(b[v]) for v in VARIABLES) and
               all(abs(f[z] - float(b[z])) < 1e-12 for z in Z) for f, b in zip(completos, anteriores))
    base_etiquetas = {f['codigo_municipio']: f['perfil'] for f in anteriores}
    preparaciones = {'principal': params}
    perturbaciones = []
    for plan, guardado in zip(planes, bd['estabilidad']):
        sub = [f for f in universo if f['bloque_espacial'] not in plan['bloques_omitidos']]
        fs, pp = _baseline.representar(sub, universo)
        assert pp == guardado['preparacion']
        codigos = {f['codigo_municipio'] for f in sub}
        perturbaciones.append((plan, [f for f in fs if f['codigo_municipio'] in codigos], fs))
        preparaciones[f"bloques_{plan['repeticion']}"] = pp
    limpios = [f for f in universo if sin_avisos(f)]
    lc, lp = _baseline.representar(limpios, limpios)
    assert lp == bd['sensibilidad']['preparacion'] and len(limpios) == 478
    preparaciones['sin_avisos'] = lp
    ejecucion = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    salida = ROOT / 'resultados/modelado/comparacion_descriptiva' / ejecucion
    salida.mkdir(parents=True, exist_ok=False)
    (salida / 'modelos').mkdir()
    protocolo = {'diseno': 'descriptivo_sin_separacion', 'n_municipios': 541, 'n_reservados': 0,
                 'entradas': VARIABLES, 'columnas_distancias': Z, 'baseline': baseline,
                 'preparacion': bp['preparacion'], 'preparaciones': preparaciones,
                 'metodos': METODOS, 'k': K, 'parametros': PARAMETROS,
                 'semilla_principal': _baseline.SEMILLA, 'semillas_extra': SEMILLAS_EXTRA,
                 'planes_estabilidad': planes, 'n_ajustes': 160,
                 'evaluacion': 'Silhouette euclídea interna; 10 ARI de omisión de bloques sobre los541 reasignados; '
                               '4 ARI por semillas extra sobre los541; ARI sin avisos sobre los478 comunes. '
                               'No CV ni prueba fuera de muestra. Etiquetas numéricas arbitrarias; comparar con ARI.',
                 'seleccion': 'Sin ganador automático ni combinación ponderada. Comparar también k4, tamaños, '
                              'perfiles, avisos, convergencia y utilidad. No interpretar pertenencia GMM como necesidad.',
                 'estado': 'Fijado antes de cualquier ajuste ML; no cambiar configuraciones tras ver métricas.'}
    guardar_json(salida / 'protocolo.json', protocolo)
    escribir_csv(salida / 'entradas_municipales.csv', universo)
    resultados, resumen, asignaciones, replicas, perfiles_csv = [], [], [], [], []
    with threadpool_limits(limits=2):
        for metodo in METODOS:
            for k in K:
                nombre = f'{metodo}_k{k}'
                modelo, etiquetas, info = ajustar(metodo, k, _baseline.SEMILLA, completos, completos)
                joblib.dump({'modelo': modelo, 'preparacion': params, 'variables': VARIABLES, 'z': Z},
                            salida / 'modelos' / f'{nombre}.joblib')
                g = evaluar(completos, etiquetas)
                assert g['k'] == k and g['silhouette'] is not None
                ps = perfiles(completos, etiquetas)
                ensayos = []
                for tipo, repeticion, semilla, muestra, descritos in (
                    [('bloques', p['repeticion'], _baseline.SEMILLA, a, b) for p, a, b in perturbaciones] +
                    [('semilla', i, s, completos, completos) for i, s in enumerate(SEMILLAS_EXTRA, 1)] +
                    [('sin_avisos', 1, _baseline.SEMILLA, lc, lc)]
                ):
                    _, otras, ii = ajustar(metodo, k, semilla, muestra, descritos)
                    comun = {c: etiquetas[c] for c in otras}
                    ari = estabilidad_por_codigo(comun, otras)
                    ensayo = {'tipo': tipo, 'repeticion': repeticion, 'ari': ari, 'ajuste': ii}
                    if tipo == 'sin_avisos':
                        ensayo['geometria_interna'] = evaluar(descritos, otras)
                    ensayos.append(ensayo)
                    replicas.extend({'configuracion': nombre, 'tipo': tipo, 'repeticion': repeticion,
                                     'codigo_municipio': c, 'perfil_principal': etiquetas[c],
                                     'perfil_replica': otras[c]} for c in sorted(otras))
                est = resumen_numerico([e['ari'] for e in ensayos if e['tipo'] == 'bloques'])
                semillas = resumen_numerico([e['ari'] for e in ensayos if e['tipo'] == 'semilla'])
                sensibilidad = next(e for e in ensayos if e['tipo'] == 'sin_avisos')
                todos = [info] + [e['ajuste'] for e in ensayos]
                r = {'configuracion': nombre, 'metodo': metodo, 'k': k, 'cobertura': len(etiquetas) / 541,
                     'silhouette_interna': g['silhouette'],
                     'silhouettes_negativas': sum(s < 0 for s in g['por_municipio_en_orden']),
                     'grupo_menor': min(p['n'] for p in ps), 'grupo_mayor': max(p['n'] for p in ps),
                     'ari_bloques_media': est['media'], 'ari_bloques_min': est['min'],
                     'ari_semillas_media': semillas['media'], 'ari_semillas_min': semillas['min'],
                     'ari_sin_avisos': sensibilidad['ari'],
                     'ari_baseline': estabilidad_por_codigo(base_etiquetas, etiquetas),
                     'n_ajustes': len(todos), 'n_avisos_ajuste': sum(len(a['avisos']) for a in todos),
                     'n_sin_convergencia': sum(a.get('convergencia') is False for a in todos),
                     'n_k_observado_distinto': sum(a['k_observado_ajuste'] != k or a['k_observado_descripcion'] != k for a in todos)}
                resumen.append(r)
                resultados.append({'resumen': r, 'ajuste_principal': info, 'geometria_interna': g,
                                   'perfiles': ps, 'ensayos': ensayos})
                proba = modelo.predict_proba(matriz(completos)) if metodo == 'gmm' else None
                for i, (f, sil) in enumerate(zip(completos, g['por_municipio_en_orden'])):
                    asignaciones.append(dict(f, configuracion=nombre, perfil=etiquetas[f['codigo_municipio']],
                                             silhouette=sil, pertenencia_maxima=float(proba[i].max()) if proba is not None else None))
                for p in ps:
                    filas = [f for f in completos if etiquetas[f['codigo_municipio']] == p['perfil']]
                    perfiles_csv.append({'configuracion': nombre, 'perfil': p['perfil'], 'municipios': p['n'],
                                         'con_avisos': p['municipios_con_avisos'],
                                         'sin_puntos': sum(f[VARIABLES[1]] == 0 for f in filas),
                                         'mediana_vehiculos': p['variables'][VARIABLES[0]]['mediana'],
                                         'mediana_puntos': p['variables'][VARIABLES[1]]['mediana']})
                print(json.dumps(r, ensure_ascii=False), flush=True)
    assert len(resultados) == 10 and sum(r['n_ajustes'] for r in resumen) == 160
    assert len(asignaciones) == 5410 and len(replicas) == 10 * (14 * 541 + 478)
    guardar_json(salida / 'resultados.json', {'ejecucion': ejecucion, 'diseno': protocolo['diseno'],
                 'n_reservados': 0, 'baseline_resumen': bd['resumen'], 'configuraciones': resultados,
                 'seleccion_final': None, 'limites': bd['limites'] + [
                     'Diez configuraciones exploradas sobre los mismos datos; las métricas internas no estiman rendimiento futuro.',
                     'Semillas extra con los mismos n_init; no son cuatro inicios simples ni una muestra de municipios independiente.',
                     'GMM usa covarianza completa regularizada; revisar ceros y componentes estrechos, sin ajustar regularización tras observar resultados.']})
    for nombre, filas in (('comparacion.csv', resumen), ('asignaciones_municipales.csv', asignaciones),
                          ('replicas_asignaciones.csv', replicas), ('resumen_perfiles.csv', perfiles_csv)):
        escribir_csv(salida / nombre, filas)
    for e in fuentes:
        checked(ROOT, ROOT / e['ruta'], e)
    guardar_json(salida / 'manifiesto.json', {'ejecucion': ejecucion, 'fuentes': fuentes,
                 'productor': checked(ROOT, Path(__file__)),
                 'apoyos': [checked(ROOT, ROOT / 'src' / n) for n in ('rutas.py',
                     'modelado/pasos/01_baseline.py', 'modelado/historico/ejecutar_baseline_demanda_oferta.py',
                     'modelado/historico/ejecutar_baseline_segmentacion.py', 'modelado/historico/preparar_experimento_segmentacion.py',
                     'datos_y_preparacion/historico/georreferenciar_recarga.py', 'datos_y_preparacion/historico/catalogar_bronze.py', 'datos_y_preparacion/historico/auditar_fuentes.py')],
                 'salidas': [checked(ROOT, p) for p in sorted(salida.rglob('*')) if p.is_file()],
                 'versiones': {'python': platform.python_version(), 'numpy': np.__version__,
                              'sklearn': sklearn.__version__, 'joblib': joblib.__version__}})
    print(json.dumps({'carpeta': salida.relative_to(ROOT).as_posix(), 'n_ajustes': 160}), flush=True)
    return salida


if __name__ == '__main__':
    main()
