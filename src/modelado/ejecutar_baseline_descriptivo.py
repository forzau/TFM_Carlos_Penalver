"""Baseline descriptivo sobre todos los municipios incluidos, sin reserva o CV."""

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import sklearn

from src.datos_y_preparacion.historico.auditar_fuentes import query
from src.datos_y_preparacion.historico.catalogar_bronze import ROOT
from src.modelado.ejecutar_baseline_demanda_oferta import (
    GOLD, PARTICIONES, VARIABLES, Z, validar, ajustar, asignar, preparar,
    perfiles, evaluar, planes_estabilidad, sin_avisos, guardar_json,
    escribir_csv, resumen_numerico, estabilidad_por_codigo,
)
from src.datos_y_preparacion.historico.georreferenciar_recarga import checked


SEMILLA = 20261111
CONSULTA = '''SELECT g.version_gold,g.codigo_municipio,g.nombre_municipio,
    b.bloque_espacial,g.vehiculos_distintivo_0,g.puntos_con_municipio_admitido,
    g.instalaciones_pendientes_relacionadas,g.instalaciones_ausentes_relacionadas,
    g.hay_incertidumbre_sin_localizar
    FROM gold_municipios g
    LEFT JOIN bloques b USING(version_gold,codigo_municipio)
    ANTI JOIN exclusiones e ON g.codigo_municipio=e.codigo_municipio
    ORDER BY g.codigo_municipio'''


def seleccionar_universo(filas, excluidos):
    validar(filas)
    assert excluidos <= {f['codigo_municipio'] for f in filas}, 'Exclusión ajena a Gold'
    elegidos = [f for f in filas if f['codigo_municipio'] not in excluidos]
    validar(elegidos)
    return sorted(elegidos, key=lambda f: f['codigo_municipio'])


def cargar_universo():
    fuentes = []
    config = ROOT / 'config/exclusiones_segmentacion.json'
    fuentes.append(checked(ROOT, config))
    excluidos = {x['codigo_municipio'] for x in json.loads(config.read_text(encoding='utf-8'))['municipios_excluidos']}
    assert excluidos == {'46201'}
    ruta_g = ROOT / GOLD / 'manifiesto.json'
    fuentes.append(checked(ROOT, ruta_g))
    doc_g = json.loads(ruta_g.read_text(encoding='utf-8'))
    ruta_p = ROOT / PARTICIONES / 'manifiesto.json'
    fuentes.append(checked(ROOT, ruta_p))
    doc_p = json.loads(ruta_p.read_text(encoding='utf-8'))
    e = next(x for x in doc_p['salidas'] if x['ruta'].endswith('/particiones_municipales.parquet'))
    sello = checked(ROOT, ROOT / e['ruta'])
    assert sello['sha256'] == e['sha256']
    fuentes.append(sello)
    with duckdb.connect(config={'threads': 2, 'memory_limit': '1GB'}) as c:
        for e in doc_g['salidas']:
            path = ruta_g.parent / e['archivo']
            fuentes.append(checked(ROOT, path, e))
            c.read_parquet(str(path)).create_view(path.stem)
        # Solo se recuperan bloques ya definidos; no se usan los antiguos roles o lotes.
        c.read_parquet(str(ROOT / PARTICIONES / 'particiones_municipales.parquet')).project(
            'version_gold,codigo_municipio,bloque_espacial').create_view('bloques')
        assert c.execute('SELECT count(*),count(DISTINCT codigo_municipio) FROM bloques').fetchone() == (541, 541)
        c.execute('CREATE TEMP TABLE exclusiones(codigo_municipio VARCHAR PRIMARY KEY)')
        c.executemany('INSERT INTO exclusiones VALUES (?)', [(x,) for x in sorted(excluidos)])
        base = query(c, 'SELECT codigo_municipio,vehiculos_distintivo_0,puntos_con_municipio_admitido FROM gold_municipios')
        assert len(base) == 542
        elegidos = seleccionar_universo(base, excluidos)
        filas = query(c, CONSULTA)
        validar(filas)
        assert len(filas) == 541
        assert [f['codigo_municipio'] for f in filas] == [f['codigo_municipio'] for f in elegidos]
        assert {f['version_gold'] for f in filas} == {doc_g['version_gold']}
        assert all(f['bloque_espacial'] and isinstance(f['hay_incertidumbre_sin_localizar'], bool) for f in filas)
        assert all(f[k] is not None and f[k] >= 0 for f in filas
                   for k in ('instalaciones_pendientes_relacionadas', 'instalaciones_ausentes_relacionadas'))
        c.execute('''CREATE TEMP VIEW incluidos AS SELECT codigo_municipio FROM gold_municipios
            ANTI JOIN exclusiones USING(codigo_municipio)''')
        oferta = query(c, '''SELECT codigo_municipio_admitido codigo_municipio,sum(puntos_registrados)::BIGINT puntos
            FROM gold_recarga_instalaciones JOIN incluidos ON codigo_municipio_admitido=codigo_municipio
            WHERE presente_copia_principal AND estado_admision='admitida_version_principal' GROUP BY 1''')
        avisos = query(c, '''SELECT codigo_municipio,
            count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='asignacion_pendiente') pendientes,
            count(DISTINCT instalacion_id) FILTER(WHERE tipo_incertidumbre='ausencia_exportacion') ausentes
            FROM gold_incertidumbre_recarga_municipio JOIN incluidos USING(codigo_municipio) GROUP BY 1''')
    oferta = {f['codigo_municipio']: f['puntos'] for f in oferta}
    avisos = {f['codigo_municipio']: f for f in avisos}
    for f in filas:
        codigo = f['codigo_municipio']
        assert f[VARIABLES[1]] == oferta.get(codigo, 0)
        assert f['instalaciones_pendientes_relacionadas'] == avisos.get(codigo, {}).get('pendientes', 0)
        assert f['instalaciones_ausentes_relacionadas'] == avisos.get(codigo, {}).get('ausentes', 0)
    return filas, fuentes


def representar(muestra, universo):
    validar(muestra)
    validar(universo)
    por_codigo = {f['codigo_municipio']: f for f in universo}
    assert {f['codigo_municipio'] for f in muestra} <= set(por_codigo)
    assert all(all(f[k] == por_codigo[f['codigo_municipio']][k] for k in (*VARIABLES, 'bloque_espacial')) for f in muestra)
    codigos = {f['codigo_municipio'] for f in muestra}
    omitidos = [f for f in universo if f['codigo_municipio'] not in codigos]
    a, b, p = preparar(muestra, omitidos)
    # El complemento solo completa el mismo universo al medir robustez; no es un test.
    filas = [{k: v for k, v in f.items() if k != 'rol'} for f in a + b]
    filas.sort(key=lambda f: f['codigo_municipio'])
    params = {'n_ajuste': len(muestra), 'n_descripcion': len(universo),
              'media_log1p': p['media_log1p'], 'varianza_log1p': p['varianza_log1p'], 'escala': p['escala']}
    return filas, params


def main():
    universo, fuentes = cargar_universo()
    planes = planes_estabilidad(universo, SEMILLA)
    ejecucion = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    salida = ROOT / 'resultados/modelado/baseline_descriptivo' / ejecucion
    salida.mkdir(parents=True, exist_ok=False)
    protocolo = {'diseno': 'descriptivo_sin_separacion', 'n_municipios': 541, 'n_reservados': 0,
                 'justificacion': 'Segmentar la fotografía municipal actual; no estimar generalización. '
                 'El usuario comunica autorización docente para adaptar el diseño al alcance descriptivo.',
                 'entradas': VARIABLES, 'columnas_distancias': Z,
                 'reglas': 'Mediana de vehículos del universo incluido; <= frente > y puntos0 frente >0; cuatro combinaciones sin prioridad.',
                 'preparacion': 'log1p de ambas entradas y StandardScaler ddof=0 sobre el universo descrito; divisor1 si constante. Reglas en originales.',
                 'geometria': 'Silhouette interna sobre los mismos municipios utilizados en ajuste; no rendimiento fuera de muestra.',
                 'estabilidad': 'Diez omisiones distintas de ceil10% de los bloques existentes; recalcular corte y preparación y asignar TODOS los541. ARI frente a referencia completa, con solapamiento; no CV ni prueba independiente.',
                 'calidad': 'Mantener recuentos admitidos/avisos. Fallar ante entradas ausentes/incorrectas. Sensibilidad: retirar avisos, reajustar sobre restantes y comparar solo códigos comunes.',
                 'semilla': SEMILLA, 'planes_estabilidad': planes,
                 'estado': 'Fijado antes de calcular resultados; no cambiar reglas buscando elevar métricas.'}
    guardar_json(salida / 'protocolo.json', protocolo)
    completos, params = representar(universo, universo)
    corte = ajustar(universo)
    etiquetas = asignar(completos, corte)
    g = evaluar(completos, etiquetas)
    estabilidad, asignaciones_estabilidad = [], []
    for plan in planes:
        muestra = [f for f in universo if f['bloque_espacial'] not in plan['bloques_omitidos']]
        filas, pp = representar(muestra, universo)
        cc = ajustar(muestra)
        otras = asignar(filas, cc)
        ari = estabilidad_por_codigo(etiquetas, otras)
        estabilidad.append({**plan, 'n_ajuste': len(muestra), 'mediana_vehiculos': cc,
                            'preparacion': pp, 'ari': ari,
                            'cambios_literal': sum(etiquetas[c] != otras[c] for c in etiquetas)})
        asignaciones_estabilidad.extend({'repeticion': plan['repeticion'], 'codigo_municipio': c,
                                        'perfil_principal': etiquetas[c], 'perfil_perturbado': otras[c]} for c in sorted(otras))
    limpios = [f for f in universo if sin_avisos(f)]
    lc, lp = representar(limpios, limpios)
    corte_limpio = ajustar(limpios)
    le = asignar(lc, corte_limpio)
    comun = {c: etiquetas[c] for c in le}
    sensibilidad = {'n_municipios': len(limpios), 'n_retirados': len(universo) - len(limpios),
                    'mediana_vehiculos': corte_limpio, 'preparacion': lp,
                    'ari_sobre_comunes': estabilidad_por_codigo(comun, le),
                    'cambios_literal': [c for c in sorted(le) if le[c] != etiquetas[c]],
                    'geometria_interna_variante': evaluar(lc, le)}
    resumen = {'n_municipios': len(universo), 'n_reservados': 0, 'cobertura': len(etiquetas) / len(universo),
               'mediana_vehiculos': corte, 'silhouette_interna': g['silhouette'],
               'silhouettes_negativas': sum(s < 0 for s in g.get('por_municipio_en_orden', [])),
               'ari_estabilidad': resumen_numerico([p['ari'] for p in estabilidad]),
               'ari_sin_avisos': sensibilidad['ari_sobre_comunes'],
               'n_con_avisos': len(universo) - len(limpios),
               'n_sin_puntos': sum(f[VARIABLES[1]] == 0 for f in universo),
               'n_sin_puntos_con_avisos': sum(f[VARIABLES[1]] == 0 and not sin_avisos(f) for f in universo),
               'n_bloques': len({f['bloque_espacial'] for f in universo}), 'n_ajustes': 12}
    resultado = {'ejecucion': ejecucion, 'diseno': 'descriptivo_sin_separacion', 'resumen': resumen,
                 'preparacion_principal': params, 'geometria_interna': g,
                 'perfiles': perfiles(completos, etiquetas), 'estabilidad': estabilidad, 'sensibilidad': sensibilidad,
                 'limites': ['Ajuste y evaluación geométrica sobre la misma fotografía de541; no prueba independiente de generalización.',
                            'Las perturbaciones incluyen municipios usados al ajustar: ARI de robustez interna, no validación cruzada.',
                            'La selección futura de modelos/k con métricas internas no proporciona una estimación imparcial fuera de muestra.',
                            'El recuento admitido no certifica servicio ni oferta completa; excluir avisos no corrige registros inciertos.',
                            'No comparar directamente con métricas de la ejecución con separación: universo y evaluación distintos.',
                            'Los perfiles no acreditan necesidad, urgencia, suficiencia o viabilidad de instalación.']}
    guardar_json(salida / 'resultados.json', resultado)
    escribir_csv(salida / 'entradas_municipales.csv', universo)
    escribir_csv(salida / 'asignaciones_municipales.csv', [dict(f, perfil=etiquetas[f['codigo_municipio']], silhouette=s)
                  for f, s in zip(completos, g.get('por_municipio_en_orden', [None] * len(completos)))])
    escribir_csv(salida / 'estabilidad_asignaciones.csv', asignaciones_estabilidad)
    escribir_csv(salida / 'sensibilidad_asignaciones.csv', [{'codigo_municipio': c,
                  'perfil_principal': etiquetas[c], 'perfil_sin_avisos': le[c]} for c in sorted(le)])
    escribir_csv(salida / 'resumen_perfiles.csv', [{'perfil': p['perfil'], 'municipios': p['n'],
                  'porcentaje': p['porcentaje'], 'con_avisos': p['municipios_con_avisos'],
                  'mediana_vehiculos': p['variables'][VARIABLES[0]]['mediana'],
                  'mediana_puntos': p['variables'][VARIABLES[1]]['mediana']} for p in resultado['perfiles']])
    assert len(asignaciones_estabilidad) == 10 * len(universo)
    for e in fuentes:
        checked(ROOT, ROOT / e['ruta'], e)
    guardar_json(salida / 'manifiesto.json', {'ejecucion': ejecucion, 'fuentes': fuentes,
                 'productor': checked(ROOT, Path(__file__)),
                 'apoyos': [checked(ROOT, ROOT / 'src' / n) for n in ('rutas.py', 'modelado/ejecutar_baseline_demanda_oferta.py', 'modelado/ejecutar_baseline_segmentacion.py', 'modelado/preparar_experimento_segmentacion.py', 'datos_y_preparacion/historico/georreferenciar_recarga.py')],
                 'salidas': [checked(ROOT, p) for p in sorted(salida.iterdir())],
                 'versiones': {'python': platform.python_version(), 'numpy': np.__version__, 'sklearn': sklearn.__version__, 'duckdb': duckdb.__version__},
                 'controles': 'Universo Gold menos exclusión exacta;541 únicos sin roles de partición; puntos/avisos reconciliados;12ajustes y5410asignaciones de robustez.'})
    print(json.dumps({'carpeta': salida.relative_to(ROOT).as_posix(), 'resumen': resumen,
                      'perfiles': resultado['perfiles'], 'sensibilidad_corte': corte_limpio,
                      'cambios_sensibilidad': len(sensibilidad['cambios_literal'])}, ensure_ascii=False, indent=2))
    return salida


if __name__ == '__main__':
    main()
