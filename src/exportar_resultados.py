"""Exporta informes agregados y figuras existentes, sin transformar datos ni ajustar modelos.

Ejecutar desde la raíz: python -m src.exportar_resultados
"""

import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from src.rutas import RAIZ


PREPARACION = 'resultados/entrega02/20261022T150925140929Z/manifiesto.json'
BASELINE = 'resultados/modelado/baseline_descriptivo/20261111T160303732930Z'
COMPARACION = 'resultados/modelado/comparacion_descriptiva/20261111T161605225327Z'
IMAGENES = COMPARACION + '/imagenes_clusters/20261111T170051625718Z'
COPIAS = {
    'modelado/comparacion.csv': COMPARACION + '/comparacion.csv',
    'modelado/perfiles_modelos.csv': COMPARACION + '/resumen_perfiles.csv',
    'modelado/perfiles_baseline.csv': BASELINE + '/resumen_perfiles.csv',
    'modelado/verificacion_baseline.json': BASELINE + '/verificacion_independiente.json',
    'modelado/verificacion_comparacion.json': COMPARACION + '/verificacion_independiente.json',
    **{f'modelado/imagenes/{metodo}_k{k}.png': f'{IMAGENES}/{metodo}_k{k}.png'
       for metodo in ('kmeans', 'gmm') for k in range(2, 7)},
}


def sello(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': path.stat().st_size, 'sha256': digest}


def guardar_json(path, datos):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def exportar(raiz=RAIZ):
    fuentes = [PREPARACION, BASELINE + '/resultados.json', COMPARACION + '/protocolo.json',
               IMAGENES + '/manifiesto_imagenes.json', *COPIAS.values()]
    fuentes = {ruta: sello(raiz / ruta) for ruta in fuentes}
    leer = lambda ruta: json.loads((raiz / ruta).read_text(encoding='utf-8'))
    preparacion = leer(PREPARACION)
    baseline = leer(BASELINE + '/resultados.json')
    protocolo = leer(COMPARACION + '/protocolo.json')
    configuraciones = leer(IMAGENES + '/manifiesto_imagenes.json')['configuraciones']
    if {c['imagen']['ruta'] for c in configuraciones} != {p for p in COPIAS.values() if p.endswith('.png')}:
        raise ValueError('El manifiesto no identifica las diez figuras seleccionadas.')
    for configuracion in configuraciones:
        imagen = configuracion['imagen']
        if fuentes[imagen['ruta']] != {campo: imagen[campo] for campo in ('bytes', 'sha256')}:
            raise ValueError('Imagen distinta de la exportación verificada: ' + imagen['ruta'])

    filas, esquemas = [], []
    for bloque, tablas in preparacion['tablas'].items():
        for nombre, entrada in tablas.items():
            filas.append({'capa': bloque.split('/')[0], 'bloque': bloque.split('/')[1],
                          'tabla': nombre, 'filas': entrada['filas'],
                          'columnas': len(entrada['esquema']), 'clave': ', '.join(entrada['clave'] or [])})
            esquemas.append({'bloque': bloque, 'tabla': nombre,
                             'clave': entrada['clave'], 'esquema': entrada['esquema']})

    destino = raiz / 'resultados/informes'
    with tempfile.TemporaryDirectory(dir=raiz / 'resultados') as folder:
        temporal = Path(folder)
        tabla = temporal / 'preparacion/resumen_tablas.csv'
        tabla.parent.mkdir()
        with tabla.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=('capa', 'bloque', 'tabla', 'filas', 'columnas', 'clave'),
                                    lineterminator='\n')
            writer.writeheader()
            writer.writerows(filas)
        guardar_json(temporal / 'preparacion/esquemas.json', esquemas)
        guardar_json(temporal / 'preparacion/resumen.json', {
            'ejecucion': preparacion['ejecucion'], 'estado': preparacion['estado'],
            'tablas_por_capa': {capa: sum(f['capa'] == capa for f in filas) for capa in ('silver', 'gold')},
            'entorno': preparacion['entorno'], 'limitaciones': preparacion['limitaciones'],
        })
        guardar_json(temporal / 'modelado/protocolo.json', {campo: protocolo[campo] for campo in (
            'diseno', 'n_municipios', 'n_reservados', 'entradas', 'preparacion',
            'metodos', 'k', 'parametros', 'n_ajustes')})
        guardar_json(temporal / 'modelado/resumen.json', {
            'baseline': baseline['resumen'],
            'seleccion_trabajo': {'configuracion': 'kmeans_k6', 'fecha_decision': '2026-11-13',
                                  'estado': 'provisional_hasta_comprobar_utilidad_en_el_MVP'},
            'limites': baseline['limites'],
        })
        for relativa, origen in COPIAS.items():
            path = temporal / relativa
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(raiz / origen, path)
        if any(sello(raiz / ruta) != huella for ruta, huella in fuentes.items()):
            raise RuntimeError('Una fuente cambió durante la exportación; se conservan los informes anteriores.')
        guardar_json(temporal / 'procedencia.json', {
            'productor': {'ruta': 'src/exportar_resultados.py', **sello(Path(__file__))},
            'fuentes': [{'ruta': ruta, **huella} for ruta, huella in fuentes.items()],
            'salidas': [{'ruta': p.relative_to(temporal).as_posix(), **sello(p)}
                        for p in sorted(temporal.rglob('*')) if p.is_file()],
            'criterio': 'Solo esquemas, recuentos, métricas agregadas y figuras; sin bases ni modelos.',
        })
        # El manifiesto se sustituye al final, tras preparar todos los informes.
        archivos = sorted(p for p in temporal.rglob('*') if p.is_file() and p.name != 'procedencia.json')
        for p in archivos + [temporal / 'procedencia.json']:
            salida = destino / p.relative_to(temporal)
            salida.parent.mkdir(parents=True, exist_ok=True)
            p.replace(salida)
    return destino


if __name__ == '__main__':
    print(exportar().relative_to(RAIZ).as_posix())
