"""Verificación independiente del baseline descriptivo, sin volver a ajustarlo."""

import csv
import json
import math
import sys
from pathlib import Path

import duckdb
import numpy as np

from src.datos_y_preparacion.historico.catalogar_bronze import ROOT
from src.datos_y_preparacion.historico.georreferenciar_recarga import checked
from src.modelado.historico.verificar_baseline_demanda_oferta import ari_contingencia, silhouette_directa


def main():
    ruta = Path(sys.argv[1]).resolve()
    assert ruta.is_relative_to(ROOT.resolve()) and ruta.is_dir()
    doc = json.loads((ruta / 'resultados.json').read_text(encoding='utf-8'))
    protocolo = json.loads((ruta / 'protocolo.json').read_text(encoding='utf-8'))
    manifiesto = json.loads((ruta / 'manifiesto.json').read_text(encoding='utf-8'))
    for e in manifiesto['fuentes'] + manifiesto['salidas'] + manifiesto['apoyos'] + [manifiesto['productor']]:
        checked(ROOT, ROOT / e['ruta'], e)
    def leer(nombre):
        with (ruta / nombre).open(encoding='utf-8', newline='') as f:
            return list(csv.DictReader(f))
    entradas = leer('entradas_municipales.csv')
    filas = leer('asignaciones_municipales.csv')
    perturbadas = leer('estabilidad_asignaciones.csv')
    sensibilidad = leer('sensibilidad_asignaciones.csv')
    assert len(entradas) == len(filas) == len({f['codigo_municipio'] for f in filas}) == 541
    assert [f['codigo_municipio'] for f in entradas] == [f['codigo_municipio'] for f in filas]
    assert '46201' not in {f['codigo_municipio'] for f in filas}
    assert not {'conjunto', 'particion_interna', 'rol'} & set(entradas[0])
    assert doc['diseno'] == protocolo['diseno'] == 'descriptivo_sin_separacion'
    assert doc['resumen']['n_reservados'] == protocolo['n_reservados'] == 0
    v, p = 'vehiculos_distintivo_0', 'puntos_con_municipio_admitido'
    matrix = lambda fs: np.log1p(np.asarray([[float(f[v]), float(f[p])] for f in fs]))
    perfil = lambda f, corte: ('I' if float(f[v]) <= corte else 'S') + ('-0' if int(f[p]) == 0 else '-P')
    limpio = lambda f: f['instalaciones_pendientes_relacionadas'] == '0' and f['instalaciones_ausentes_relacionadas'] == '0' and f['hay_incertidumbre_sin_localizar'] == 'False'
    params_error = 0.0
    def comprobar_parametros(fs, params, n_descripcion):
        nonlocal params_error
        x = matrix(fs)
        var = x.var(axis=0)
        assert (params['n_ajuste'], params['n_descripcion']) == (len(fs), n_descripcion)
        for observado, esperado in ((params['media_log1p'], x.mean(axis=0)),
                                    (params['varianza_log1p'], var),
                                    (params['escala'], np.where(var == 0, 1, np.sqrt(var)))):
            params_error = max(params_error, float(np.max(np.abs(np.asarray(observado) - esperado))))
    with duckdb.connect() as c:
        c.read_csv(str(ruta / 'entradas_municipales.csv'), all_varchar=True).create_view('entradas')
        corte = c.execute(f'SELECT median({v}::DOUBLE) FROM entradas').fetchone()[0]
    assert corte == doc['resumen']['mediana_vehiculos']
    for f in filas:
        assert f['perfil'] == perfil(f, corte)
    params = doc['preparacion_principal']
    comprobar_parametros(entradas, params, len(entradas))
    z = (matrix(entradas) - np.asarray(params['media_log1p'])) / np.asarray(params['escala'])
    assert np.allclose(z, [[float(f['z_log1p_vehiculos']), float(f['z_log1p_puntos'])] for f in filas], atol=1e-12)
    sil = silhouette_directa(z, [f['perfil'] for f in filas])
    error_s = max(abs(a - float(f['silhouette'])) for a, f in zip(sil, filas))
    assert math.isclose(float(np.mean(sil)), doc['resumen']['silhouette_interna'], abs_tol=1e-8)
    assert sum(s < 0 for s in sil) == doc['resumen']['silhouettes_negativas']
    error_ari = 0.0
    for plan, guardado in zip(protocolo['planes_estabilidad'], doc['estabilidad']):
        assert plan['repeticion'] == guardado['repeticion'] and plan['bloques_omitidos'] == guardado['bloques_omitidos']
        muestra = [f for f in entradas if f['bloque_espacial'] not in plan['bloques_omitidos']]
        assert len(plan['bloques_omitidos']) == math.ceil(.1 * len({f['bloque_espacial'] for f in entradas}))
        cc = float(np.median([float(f[v]) for f in muestra]))
        assert cc == guardado['mediana_vehiculos']
        comprobar_parametros(muestra, guardado['preparacion'], len(entradas))
        pp = sorted((f for f in perturbadas if int(f['repeticion']) == plan['repeticion']), key=lambda f: f['codigo_municipio'])
        assert [f['codigo_municipio'] for f in pp] == [f['codigo_municipio'] for f in filas]
        for f, principal in zip(pp, filas):
            assert f['perfil_principal'] == principal['perfil'] and f['perfil_perturbado'] == perfil(principal, cc)
        ari = ari_contingencia([f['perfil_principal'] for f in pp], [f['perfil_perturbado'] for f in pp])
        error_ari = max(error_ari, abs(ari - guardado['ari']))
    assert len(doc['estabilidad']) == len(protocolo['planes_estabilidad']) == 10 and len(perturbadas) == 5410
    limpios = [f for f in entradas if limpio(f)]
    ss = doc['sensibilidad']
    comprobar_parametros(limpios, ss['preparacion'], len(limpios))
    cc = float(np.median([float(f[v]) for f in limpios]))
    assert (len(limpios), cc) == (ss['n_municipios'], ss['mediana_vehiculos'])
    assert [f['codigo_municipio'] for f in sensibilidad] == [f['codigo_municipio'] for f in limpios]
    for f, original in zip(sensibilidad, limpios):
        assert f['perfil_principal'] == perfil(original, corte) and f['perfil_sin_avisos'] == perfil(original, cc)
    error_ari = max(error_ari, abs(ari_contingencia([f['perfil_principal'] for f in sensibilidad], [f['perfil_sin_avisos'] for f in sensibilidad]) - ss['ari_sobre_comunes']))
    assert sum(f['perfil_principal'] != f['perfil_sin_avisos'] for f in sensibilidad) == len(ss['cambios_literal'])
    for grupo in doc['perfiles']:
        fs = [f for f in filas if f['perfil'] == grupo['perfil']]
        assert len(fs) == grupo['n'] and sum(not limpio(f) for f in fs) == grupo['municipios_con_avisos']
        for campo in (v, p):
            assert np.allclose(list(grupo['variables'][campo].values()), np.quantile([float(f[campo]) for f in fs], [0, .25, .5, .75, 1]))
    assert error_s < 1e-8 and error_ari < 1e-12 and params_error < 1e-12
    informe = {'estado': 'correcto', 'n_municipios': len(filas), 'n_reservados': 0,
               'mediana_sql': corte, 'silhouettes_recalculadas': len(sil), 'ari_por_contingencias': 11,
               'preparaciones_contrastadas': 12, 'error_max_silhouette': error_s,
               'error_max_ari': error_ari, 'error_max_parametros': params_error,
               'tolerancia_silhouette': 1e-8,
               'cautela': 'Redondeo de distancias sklearn entre filas coincidentes; evaluación interna, no generalización.',
               'manifiesto': checked(ROOT, ruta / 'manifiesto.json'), 'verificador': checked(ROOT, Path(__file__))}
    (ruta / 'verificacion_independiente.json').write_text(json.dumps(informe, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(informe, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
