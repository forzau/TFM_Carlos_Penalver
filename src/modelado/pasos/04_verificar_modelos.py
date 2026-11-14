"""Comprueba modelos guardados, preparación, silhouettes y ARI sin reajustarlos."""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from scipy.special import logsumexp

from src.datos_y_preparacion.historico.catalogar_bronze import ROOT
from src.datos_y_preparacion.historico.georreferenciar_recarga import checked
from src.modelado.historico.verificar_baseline_demanda_oferta import ari_contingencia, silhouette_directa


def main():
    ruta = Path(sys.argv[1]).resolve()
    assert ruta.is_relative_to(ROOT.resolve()) and ruta.is_dir()
    leer_json = lambda p: json.loads(p.read_text(encoding='utf-8'))
    def leer_csv(p):
        with p.open(encoding='utf-8', newline='') as f:
            return list(csv.DictReader(f))
    mf = leer_json(ruta / 'manifiesto.json')
    for e in mf['fuentes'] + mf['salidas'] + mf['apoyos'] + [mf['productor']]:
        checked(ROOT, ROOT / e['ruta'], e)
    protocolo, doc = (leer_json(ruta / n) for n in ('protocolo.json', 'resultados.json'))
    entradas, asignaciones, replicas, resumen = (leer_csv(ruta / n) for n in (
        'entradas_municipales.csv', 'asignaciones_municipales.csv', 'replicas_asignaciones.csv', 'comparacion.csv'))
    base = ROOT / protocolo['baseline']
    bd, bp = (leer_json(base / n) for n in ('resultados.json', 'protocolo.json'))
    anteriores = leer_csv(base / 'asignaciones_municipales.csv')
    assert protocolo['planes_estabilidad'] == bp['planes_estabilidad']
    assert doc['diseno'] == protocolo['diseno'] == 'descriptivo_sin_separacion'
    assert doc['n_reservados'] == protocolo['n_reservados'] == 0
    assert len(entradas) == len({f['codigo_municipio'] for f in entradas}) == 541
    assert entradas == leer_csv(base / 'entradas_municipales.csv')
    assert not {'rol', 'conjunto', 'particion_interna'} & set(entradas[0])
    assert len(asignaciones) == 5410 and len(replicas) == 80520
    variables = protocolo['entradas']
    crudos = lambda fs: np.log1p(np.asarray([[float(f[v]) for v in variables] for f in fs]))
    limpio = lambda f: f['instalaciones_pendientes_relacionadas'] == '0' and f['instalaciones_ausentes_relacionadas'] == '0' and f['hay_incertidumbre_sin_localizar'] == 'False'
    limpios = [f for f in entradas if limpio(f)]
    assert len(limpios) == 478
    muestras = {'principal': entradas, 'sin_avisos': limpios}
    for p in protocolo['planes_estabilidad']:
        muestras[f"bloques_{p['repeticion']}"] = [f for f in entradas if f['bloque_espacial'] not in p['bloques_omitidos']]
    error_p = error_s = error_a = 0.
    n_sil = n_ari = n_modelos = n_ajustes = 0
    for nombre, fs in muestras.items():
        x = crudos(fs)
        pp = protocolo['preparaciones'][nombre]
        var = x.var(axis=0)
        assert pp['n_ajuste'] == len(fs) and pp['n_descripcion'] == (478 if nombre == 'sin_avisos' else 541)
        for clave, esperado in (('media_log1p', x.mean(axis=0)), ('varianza_log1p', var), ('escala', np.where(var == 0, 1, np.sqrt(var)))):
            error_p = max(error_p, float(np.max(np.abs(np.asarray(pp[clave]) - esperado))))
    assert protocolo['preparaciones']['principal'] == bd['preparacion_principal']
    def transformar(fs, nombre):
        pp = protocolo['preparaciones'][nombre]
        return (crudos(fs) - np.asarray(pp['media_log1p'])) / np.asarray(pp['escala'])
    x = transformar(entradas, 'principal')
    for config in doc['configuraciones']:
        r = config['resumen']
        nombre, metodo, k = r['configuracion'], r['metodo'], r['k']
        guardado = next(f for f in resumen if f['configuracion'] == nombre)
        for clave, valor in r.items():
            assert guardado[clave] == str(valor), (nombre, clave)
        fs = [f for f in asignaciones if f['configuracion'] == nombre]
        assert [f['codigo_municipio'] for f in fs] == [f['codigo_municipio'] for f in entradas]
        assert np.allclose(x, [[float(f[z]) for z in protocolo['columnas_distancias']] for f in fs], atol=1e-12, rtol=0)
        etiquetas = [int(f['perfil']) for f in fs]
        paquete = joblib.load(ruta / 'modelos' / f'{nombre}.joblib')
        modelo = paquete['modelo']
        assert paquete['preparacion'] == protocolo['preparaciones']['principal']
        assert tuple(paquete['variables']) == tuple(variables) and modelo.n_features_in_ == 2
        assert modelo.get_params() == config['ajuste_principal']['parametros']
        if metodo == 'kmeans':
            pred = np.argmin(((x[:, None, :] - modelo.cluster_centers_[None, :, :]) ** 2).sum(axis=2), axis=1)
        else:
            densidades = []
            for media, cov, peso in zip(modelo.means_, modelo.covariances_, modelo.weights_):
                signo, logdet = np.linalg.slogdet(cov)
                assert signo == 1 and np.linalg.eigvalsh(cov).min() >= 1e-6 - 1e-12
                d = x - media
                densidades.append(np.log(peso) - .5 * (2 * np.log(2 * np.pi) + logdet + np.sum(d * np.linalg.solve(cov, d.T).T, axis=1)))
            logp = np.asarray(densidades).T
            proba = np.exp(logp - logsumexp(logp, axis=1)[:, None])
            pred = np.argmax(logp, axis=1)
            assert np.allclose(proba.max(axis=1), [float(f['pertenencia_maxima']) for f in fs], atol=1e-10, rtol=0)
        assert np.array_equal(pred, etiquetas) and len(set(etiquetas)) == k
        n_modelos += 1
        sil = silhouette_directa(x, etiquetas)
        error_s = max(error_s, float(np.max(np.abs(np.asarray(sil) - [float(f['silhouette']) for f in fs]))))
        assert abs(np.mean(sil) - r['silhouette_interna']) < 1e-8
        assert sum(s < 0 for s in sil) == r['silhouettes_negativas']
        n_sil += len(sil)
        for p in config['perfiles']:
            grupo = [f for f in fs if int(f['perfil']) == p['perfil']]
            assert len(grupo) == p['n'] and sum(not limpio(f) for f in grupo) == p['municipios_con_avisos']
            for v in variables:
                assert np.allclose(list(p['variables'][v].values()), np.quantile([float(f[v]) for f in grupo], [0, .25, .5, .75, 1]))
        assert sum(p['n'] for p in config['perfiles']) == 541
        aris = {'bloques': [], 'semilla': [], 'sin_avisos': []}
        for e in config['ensayos']:
            tipo, rep = e['tipo'], e['repeticion']
            rs = [f for f in replicas if f['configuracion'] == nombre and f['tipo'] == tipo and int(f['repeticion']) == rep]
            esperados = limpios if tipo == 'sin_avisos' else entradas
            assert [f['codigo_municipio'] for f in rs] == [f['codigo_municipio'] for f in esperados]
            principal = {f['codigo_municipio']: f['perfil'] for f in fs}
            assert all(f['perfil_principal'] == principal[f['codigo_municipio']] for f in rs)
            ari = ari_contingencia([f['perfil_principal'] for f in rs], [f['perfil_replica'] for f in rs])
            aris[tipo].append(ari)
            error_a = max(error_a, abs(ari - e['ari']))
            n_ari += 1
            if tipo == 'sin_avisos':
                ss = silhouette_directa(transformar(limpios, 'sin_avisos'), [f['perfil_replica'] for f in rs])
                error_s = max(error_s, float(np.max(np.abs(np.asarray(ss) - e['geometria_interna']['por_municipio_en_orden']))))
                n_sil += len(ss)
            pp = protocolo['preparaciones']['sin_avisos' if tipo == 'sin_avisos' else f'bloques_{rep}' if tipo == 'bloques' else 'principal']
            assert (e['ajuste']['n_ajuste'], e['ajuste']['n_descripcion']) == (pp['n_ajuste'], pp['n_descripcion'])
            assert e['ajuste']['semilla'] == (protocolo['semillas_extra'][rep - 1] if tipo == 'semilla' else protocolo['semilla_principal'])
        assert [len(aris[t]) for t in aris] == [10, 4, 1]
        assert np.allclose([r['ari_bloques_media'], r['ari_bloques_min'], r['ari_semillas_media'], r['ari_semillas_min'], r['ari_sin_avisos']],
                           [np.mean(aris['bloques']), min(aris['bloques']), np.mean(aris['semilla']), min(aris['semilla']), aris['sin_avisos'][0]], atol=1e-12, rtol=0)
        error_a = max(error_a, abs(ari_contingencia([f['perfil'] for f in anteriores], etiquetas) - r['ari_baseline']))
        n_ari += 1
        ajustes = [config['ajuste_principal']] + [e['ajuste'] for e in config['ensayos']]
        assert len(ajustes) == r['n_ajustes'] == 16
        assert sum(len(a['avisos']) for a in ajustes) == r['n_avisos_ajuste']
        assert sum(a.get('convergencia') is False for a in ajustes) == r['n_sin_convergencia']
        assert sum(a['k_observado_ajuste'] != k or a['k_observado_descripcion'] != k for a in ajustes) == r['n_k_observado_distinto']
        n_ajustes += len(ajustes)
    assert n_modelos == 10 and n_ajustes == protocolo['n_ajustes'] == 160
    assert error_s < 1e-8 and error_a < 1e-12 and error_p < 1e-12
    informe = {'estado': 'correcto', 'modelos_con_prediccion_independiente': n_modelos,
               'ajustes_registrados': n_ajustes, 'preparaciones_contrastadas': len(muestras),
               'silhouettes_recalculadas': n_sil, 'ari_por_contingencias': n_ari,
               'error_max_silhouette': error_s, 'error_max_ari': error_a,
               'error_max_parametros': error_p, 'tolerancia_silhouette': 1e-8,
               'limite': 'No se reajustan modelos ni se comprueba generalización o necesidad real.',
               'manifiesto': checked(ROOT, ruta / 'manifiesto.json'), 'verificador': checked(ROOT, Path(__file__))}
    (ruta / 'verificacion_independiente.json').write_text(json.dumps(informe, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(informe, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
