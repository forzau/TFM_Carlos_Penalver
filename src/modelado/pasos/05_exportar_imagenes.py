"""Exporta PNG comparables desde asignaciones guardadas, sin volver a ajustar."""

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import joblib
import numpy as np

from src.datos_y_preparacion.historico.catalogar_bronze import ROOT
from src.datos_y_preparacion.historico.georreferenciar_recarga import checked


VARIABLES = ('vehiculos_distintivo_0', 'puntos_con_municipio_admitido')
Z = ('z_log1p_vehiculos', 'z_log1p_puntos')
COLORES = ('#0072B2', '#E69F00', '#009E73', '#CC79A7', '#D55E00', '#56B4E9')


def coordenadas(filas, campos):
    x = np.asarray([[float(f[c]) for c in campos] for f in filas])
    assert x.shape == (len(filas), 2) and len(x) and np.isfinite(x).all()
    return x


def limites(x):
    margen = np.maximum(np.ptp(x, axis=0) * .05, .5)
    return list(zip((x.min(axis=0) - margen).tolist(), (x.max(axis=0) + margen).tolist()))


def centros_del_modelo(paquete, resumen):
    assert tuple(paquete['variables']) == VARIABLES and tuple(paquete['z']) == Z
    modelo, preparacion = paquete['modelo'], paquete['preparacion']
    assert modelo.n_features_in_ == 2
    centros = np.asarray(modelo.cluster_centers_ if resumen['metodo'] == 'kmeans' else modelo.means_, dtype=float)
    media, escala = (np.asarray(preparacion[k], dtype=float) for k in ('media_log1p', 'escala'))
    assert centros.shape == (resumen['k'], 2) and np.isfinite(centros).all()
    assert media.shape == escala.shape == (2,) and np.isfinite(media).all() and np.isfinite(escala).all() and (escala > 0).all()
    originales = np.expm1(centros * escala + media)
    assert np.isfinite(originales).all() and (originales >= -1e-10).all()
    # El inverso de un cero puede quedar ligeramente negativo por redondeo.
    return np.maximum(originales, 0), centros


def dibujar(filas, resumen, limites_originales, limites_modelo, centros_originales, centros_modelo):
    originales, preparados = coordenadas(filas, VARIABLES), coordenadas(filas, Z)
    etiquetas = np.asarray([int(f['perfil']) for f in filas])
    grupos = sorted(set(etiquetas.tolist()))
    assert grupos == list(range(resumen['k'])) and len(grupos) <= len(COLORES)
    assert (originales >= 0).all() and np.equal(originales, np.floor(originales)).all()
    assert len({f['codigo_municipio'] for f in filas}) == len(filas)
    assert np.asarray(centros_originales).shape == np.asarray(centros_modelo).shape == (resumen['k'], 2)
    assert np.isfinite(centros_originales).all() and np.isfinite(centros_modelo).all()
    fig, axes = plt.subplots(1, 2, figsize=(14, 7.5))
    fig.subplots_adjust(left=.08, right=.97, top=.80, bottom=.31, wspace=.25)
    nombre = {'kmeans': 'K-means', 'gmm': 'GMM'}[resumen['metodo']]
    fig.suptitle(f"{nombre} · {resumen['k']} grupos", fontsize=20, fontweight='bold', y=.97)
    fig.text(.5, .905, f"{len(filas)} municipios · dos variables · ajuste descriptivo sin separación", ha='center', fontsize=12)
    for ax, x, rango, titulo, centros in zip(axes, (originales, preparados),
                                   (limites_originales, limites_modelo),
                                   ('Recuentos originales', 'Representación utilizada por el modelo'),
                                   (centros_originales, centros_modelo)):
        for grupo in grupos:
            seleccion = etiquetas == grupo
            ax.scatter(x[seleccion, 0], x[seleccion, 1], color=COLORES[grupo], s=24, alpha=.65,
                       linewidths=.3, edgecolors='white', label=f'Grupo {grupo} · n={int(seleccion.sum())}')
        ax.scatter(centros[:, 0], centros[:, 1], c=COLORES[:len(grupos)], marker='X', s=180,
                   edgecolors='black', linewidths=1.3, zorder=5)
        for grupo, centro in enumerate(centros):
            ax.annotate(f'C{grupo}', centro, xytext=(10, 12 + 14 * grupo if ax is axes[0] else 10),
                        textcoords='offset points', fontsize=10, fontweight='bold', zorder=6,
                        bbox=dict(facecolor='white', edgecolor='none', alpha=.85, pad=1),
                        arrowprops=dict(arrowstyle='-', color='black', lw=.6))
        ax.set(xlim=rango[0], ylim=rango[1], title=titulo,
               xlabel='Vehículos con Distintivo 0', ylabel='Puntos de recarga con municipio admitido')
        ax.grid(alpha=.2)
        ax.set_axisbelow(True)
        if ax is axes[0]:
            ax.xaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
            ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
        else:
            ax.set_aspect('equal', adjustable='box')
    fig.legend(*axes[0].get_legend_handles_labels(), loc='lower center', bbox_to_anchor=(.5, .165),
               ncol=3, frameon=False, fontsize=11, markerscale=1.5)
    tipo = 'Centroides K-means' if resumen['metodo'] == 'kmeans' else 'Medias de componentes GMM'
    fig.legend(handles=[Line2D([], [], marker='X', linestyle='none', markerfacecolor='white',
               markeredgecolor='black', markersize=10, label=f'{tipo} · Cn corresponde al grupo n')],
               loc='upper center', bbox_to_anchor=(.5, .875), frameon=False, fontsize=11)
    fig.text(.5, .12, 'Derecha: log1p + estandarización en ambos ejes; unidades estandarizadas. Límites comunes a las diez configuraciones.', ha='center', fontsize=10)
    fig.text(.5, .075, 'Izquierda: centros devueltos por la transformación inversa; no son medias aritméticas de los recuentos. Municipios coincidentes se superponen.', ha='center', fontsize=9)
    fig.text(.5, .035, 'La numeración y los colores son propios de cada configuración: no indican urgencia ni equivalencia entre modelos.', ha='center', fontsize=10)
    return fig


def exportar(ruta):
    ruta = Path(ruta).resolve()
    assert ruta.is_dir() and ruta.is_relative_to(ROOT.resolve())
    manifiesto = json.loads((ruta / 'manifiesto.json').read_text(encoding='utf-8'))
    for e in manifiesto['salidas']:
        checked(ROOT, ROOT / e['ruta'], e)
    doc = json.loads((ruta / 'resultados.json').read_text(encoding='utf-8'))
    protocolo = json.loads((ruta / 'protocolo.json').read_text(encoding='utf-8'))
    with (ruta / 'asignaciones_municipales.csv').open(encoding='utf-8', newline='') as f:
        filas = list(csv.DictReader(f))
    assert doc['diseno'] == protocolo['diseno'] == 'descriptivo_sin_separacion'
    assert tuple(protocolo['entradas']) == VARIABLES and tuple(protocolo['columnas_distancias']) == Z
    configuraciones = [c['resumen'] for c in doc['configuraciones']]
    nombres = [c['configuracion'] for c in configuraciones]
    assert len(nombres) == len(set(nombres)) == 10
    assert set(nombres) == {f['configuracion'] for f in filas}
    grupos = {n: [f for f in filas if f['configuracion'] == n] for n in nombres}
    referencia = grupos[nombres[0]]
    codigos = [f['codigo_municipio'] for f in referencia]
    assert len(codigos) == len(set(codigos)) == protocolo['n_municipios']
    originales, preparados = coordenadas(referencia, VARIABLES), coordenadas(referencia, Z)
    for c in configuraciones:
        assert c['metodo'] in ('kmeans', 'gmm') and c['k'] in range(2, 7)
        assert c['configuracion'] == f"{c['metodo']}_k{c['k']}"
        fs = grupos[c['configuracion']]
        assert [f['codigo_municipio'] for f in fs] == codigos
        assert np.array_equal(coordenadas(fs, VARIABLES), originales)
        assert np.allclose(coordenadas(fs, Z), preparados, atol=1e-12, rtol=0)
    salida = ruta / 'imagenes_clusters' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    salida.mkdir(parents=True, exist_ok=False)
    resumenes = []
    modelos = []
    for c in configuraciones:
        fs = grupos[c['configuracion']]
        ruta_modelo = ruta / 'modelos' / f"{c['configuracion']}.joblib"
        modelos.append(checked(ROOT, ruta_modelo))
        paquete = joblib.load(ruta_modelo)
        assert paquete['preparacion'] == protocolo['preparaciones']['principal']
        co, cm = centros_del_modelo(paquete, c)
        fig = dibujar(fs, c, limites(originales), limites(preparados), co, cm)
        archivo = salida / f"{c['configuracion']}.png"
        fig.savefig(archivo, dpi=200, facecolor='white')
        plt.close(fig)
        resumenes.append({'configuracion': c['configuracion'], 'n_municipios': len(fs),
                          'por_grupo': dict(Counter(f['perfil'] for f in fs)),
                          'posiciones_distintas': len(np.unique(originales, axis=0)),
                          'tipo_centro': 'centroide_kmeans' if c['metodo'] == 'kmeans' else 'media_componente_gmm',
                          'centros_modelo': cm.tolist(), 'centros_escala_original': co.tolist(),
                          'imagen': checked(ROOT, archivo)})
    informe = {'exportacion_sin_reajuste': True, 'n_imagenes': len(resumenes), 'dimensiones_png': [2800, 1500],
               'limites_originales': limites(originales), 'limites_modelo': limites(preparados),
               'colores_por_etiqueta_local': COLORES, 'configuraciones': resumenes,
               'fuentes': [checked(ROOT, ruta / n) for n in ('manifiesto.json', 'resultados.json', 'protocolo.json', 'asignaciones_municipales.csv')] + modelos,
               'productor': checked(ROOT, Path(__file__)), 'version_matplotlib': matplotlib.__version__}
    (salida / 'manifiesto_imagenes.json').write_text(json.dumps(informe, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return salida


if __name__ == '__main__':
    print(exportar(sys.argv[1]).relative_to(ROOT).as_posix())
