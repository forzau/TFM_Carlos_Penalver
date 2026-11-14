"""Contrasta las salidas guardadas con SQL, distancias y contingencias, sin reajustar."""

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

import duckdb
import numpy as np
from scipy.spatial.distance import cdist

from src.datos_y_preparacion.historico.catalogar_bronze import ROOT
from src.datos_y_preparacion.historico.georreferenciar_recarga import checked


def ari_contingencia(a, b):
    assert len(a) == len(b) > 1
    pares = lambda vals: sum(n * (n - 1) / 2 for n in Counter(vals).values())
    indice = pares(list(zip(a, b)))
    sa, sb = pares(a), pares(b)
    total = len(a) * (len(a) - 1) / 2
    esperado, maximo = sa * sb / total, (sa + sb) / 2
    return (indice - esperado) / (maximo - esperado) if maximo != esperado else 1.0


def silhouette_directa(x, etiquetas):
    d = cdist(x, x)
    resultado = []
    for i, etiqueta in enumerate(etiquetas):
        propios = [j for j, e in enumerate(etiquetas) if e == etiqueta and j != i]
        if not propios:
            resultado.append(0.0)
            continue
        a = float(np.mean(d[i, propios]))
        b = min(float(np.mean(d[i, [j for j, e in enumerate(etiquetas) if e == otro]]))
                for otro in set(etiquetas) - {etiqueta})
        resultado.append((b - a) / max(a, b) if max(a, b) else 0.0)
    return resultado


def main():
    ruta = Path(sys.argv[1]).resolve()
    assert ruta.is_relative_to(ROOT.resolve()) and ruta.is_dir()
    doc = json.loads((ruta / 'resultados.json').read_text(encoding='utf-8'))
    protocolo = json.loads((ruta / 'protocolo.json').read_text(encoding='utf-8'))
    manifiesto = json.loads((ruta / 'manifiesto.json').read_text(encoding='utf-8'))
    for e in manifiesto['fuentes'] + manifiesto['salidas'] + manifiesto['apoyos'] + [manifiesto['productor']]:
        checked(ROOT, ROOT / e['ruta'], e)
    leer = lambda nombre: list(csv.DictReader((ruta / nombre).open(encoding='utf-8', newline='')))
    entradas = leer('entradas_desarrollo.csv')
    oof = leer('asignaciones_validacion.csv')
    estabilidad = leer('estabilidad_asignaciones.csv')
    sensibilidad = leer('sensibilidad_asignaciones.csv')
    descriptivo = leer('perfiles_desarrollo.csv')
    assert len(entradas) == len(oof) == len(descriptivo) == 433
    assert len({f['codigo_municipio'] for f in oof}) == 433
    assert {f['codigo_municipio'] for f in entradas} == {f['codigo_municipio'] for f in oof}
    assert all('renta' not in campo for campo in entradas[0])
    sin_avisos = lambda f: f['instalaciones_pendientes_relacionadas'] == '0' and f['instalaciones_ausentes_relacionadas'] == '0' and f['hay_incertidumbre_sin_localizar'] == 'False'
    vehiculos = 'vehiculos_distintivo_0'
    puntos = 'puntos_con_municipio_admitido'
    z = ['z_log1p_vehiculos', 'z_log1p_puntos']
    x = lambda filas: np.log1p(np.asarray([[float(f[vehiculos]), float(f[puntos])] for f in filas]))
    perfil = lambda f, corte: ('I' if float(f[vehiculos]) <= corte else 'S') + ('-0' if int(f[puntos]) == 0 else '-P')
    max_s, max_a, max_p, n_params = 0.0, 0.0, 0.0, 0
    with duckdb.connect() as c:
        c.read_csv(str(ruta / 'entradas_desarrollo.csv'), all_varchar=True).create_view('entradas')
        corte_global = c.execute(f'SELECT median({vehiculos}::DOUBLE) FROM entradas').fetchone()[0]
        assert corte_global == doc['descriptivo']['mediana_vehiculos']
        for fila in descriptivo:
            assert fila['perfil'] == perfil(fila, corte_global)
        for v in doc['validaciones']:
            nombre = v['ajuste']
            interna = nombre.rsplit('_', 1)[1]
            train = [f for f in entradas if f['particion_interna'] != interna]
            val = [f for f in oof if f['ajuste'] == nombre]
            corte = c.execute(f'SELECT median({vehiculos}::DOUBLE) FROM entradas WHERE particion_interna<>?', [interna]).fetchone()[0]
            assert corte == v['mediana_vehiculos']
            for f in val:
                assert f['particion_interna'] == interna and f['perfil'] == perfil(f, corte)
            assert {f['bloque_espacial'] for f in train}.isdisjoint(f['bloque_espacial'] for f in val)
            media, varianza = x(train).mean(axis=0), x(train).var(axis=0)
            escala = np.where(varianza == 0, 1, np.sqrt(varianza))
            zs = (x(val) - media) / escala
            assert np.allclose(zs, [[float(f[k]) for k in z] for f in val], atol=1e-12)
            sil = silhouette_directa(zs, [f['perfil'] for f in val])
            max_s = max(max_s, max(abs(s - float(f['silhouette'])) for s, f in zip(sil, val)))
            # Las distancias por producto escalar de sklearn dejan redondeo en filas coincidentes.
            assert math.isclose(float(np.mean(sil)), v['geometria']['silhouette'], abs_tol=1e-8)
            variantes = [(train, corte, json.loads((ruta / 'preparaciones.json').read_text(encoding='utf-8'))[nombre]['preparacion'])]
            for p in v['estabilidad']:
                assert p['bloques_omitidos'] == protocolo['planes_estabilidad'][nombre][p['repeticion'] - 1]['bloques_omitidos']
                sub = [f for f in train if f['bloque_espacial'] not in p['bloques_omitidos']]
                assert len(p['bloques_omitidos']) == math.ceil(.1 * len({f['bloque_espacial'] for f in train}))
                corte_sub = float(np.median([float(f[vehiculos]) for f in sub]))
                assert corte_sub == p['mediana_vehiculos']
                filas_p = sorted((f for f in estabilidad if f['ajuste'] == nombre and int(f['repeticion']) == p['repeticion']), key=lambda f: f['codigo_municipio'])
                assert len(filas_p) == len(val)
                por_codigo = {f['codigo_municipio']: f for f in val}
                for f in filas_p:
                    original = por_codigo[f['codigo_municipio']]
                    assert f['perfil_principal'] == original['perfil'] and f['perfil_perturbado'] == perfil(original, corte_sub)
                ari = ari_contingencia([f['perfil_principal'] for f in filas_p], [f['perfil_perturbado'] for f in filas_p])
                max_a = max(max_a, abs(ari - p['ari']))
                variantes.append((sub, corte_sub, p['preparacion']))
            cs = v['sensibilidad_sin_avisos']
            clean_train = [f for f in train if sin_avisos(f)]
            clean_val = [f for f in val if sin_avisos(f)]
            corte_clean = float(np.median([float(f[vehiculos]) for f in clean_train]))
            assert (len(clean_train), len(clean_val), corte_clean) == (cs['n_train'], cs['n_val'], cs['mediana_vehiculos'])
            sv = sorted((f for f in sensibilidad if f['ajuste'] == nombre), key=lambda f: f['codigo_municipio'])
            cv = {f['codigo_municipio']: f for f in clean_val}
            assert set(cv) == {f['codigo_municipio'] for f in sv}
            for f in sv:
                assert f['perfil_sin_avisos'] == perfil(cv[f['codigo_municipio']], corte_clean)
            max_a = max(max_a, abs(ari_contingencia([f['perfil_principal'] for f in sv], [f['perfil_sin_avisos'] for f in sv]) - cs['ari_sobre_comunes']))
            variantes.append((clean_train, corte_clean, cs['preparacion']))
            for filas, umbral, params in variantes:
                xx = x(filas)
                assert umbral == float(np.median([float(f[vehiculos]) for f in filas]))
                vv = xx.var(axis=0)
                for observado, esperado in ((params['media_log1p'], xx.mean(axis=0)), (params['varianza_log1p'], vv), (params['escala'], np.where(vv == 0, 1, np.sqrt(vv)))):
                    max_p = max(max_p, float(np.max(np.abs(np.asarray(observado) - esperado))))
                n_params += 1
        params = json.loads((ruta / 'preparaciones.json').read_text(encoding='utf-8'))['desarrollo_completo']['preparacion']
        assert np.allclose(params['media_log1p'], x(entradas).mean(axis=0), atol=1e-12)
        assert np.allclose(params['varianza_log1p'], x(entradas).var(axis=0), atol=1e-12)
        for p in doc['descriptivo']['perfiles']:
            fs = [f for f in descriptivo if f['perfil'] == p['perfil']]
            assert len(fs) == p['n']
            for campo in (vehiculos, puntos):
                assert np.allclose(list(p['variables'][campo].values()), np.quantile([float(f[campo]) for f in fs], [0, .25, .5, .75, 1]))
    assert max_s < 1e-8 and max_a < 1e-12 and max_p < 1e-12
    salida = {'estado': 'correcto', 'silhouettes_municipales_por_distancia': 433,
              'ari_por_contingencias': 44, 'preparaciones_contrastadas': n_params + 1,
              'error_max_silhouette': max_s, 'error_max_ari': max_a, 'error_max_parametros': max_p,
              'tolerancia_silhouette': 1e-8,
              'motivo_tolerancia': 'Redondeo de distancias sklearn por producto escalar entre observaciones coincidentes; contraste directo mediante cdist.',
              'cambios_literal_sin_avisos': sum(f['perfil_principal'] != f['perfil_sin_avisos'] for f in sensibilidad),
              'n_sensibilidad': len(sensibilidad), 'n_prueba_evaluados': 0,
              'manifiesto': checked(ROOT, ruta / 'manifiesto.json'), 'verificador': checked(ROOT, Path(__file__))}
    (ruta / 'verificacion_independiente.json').write_text(json.dumps(salida, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(salida, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
