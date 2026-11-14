"""Coordina los experimentos descriptivos de la Entrega 03 desde Gold existente."""

import argparse
import json
import subprocess
import sys

from src.exportar_resultados import BASELINE, COMPARACION
from src.rutas import RAIZ


def verificar(tipo, carpeta):
    """Detiene el flujo si el verificador independiente encuentra un problema."""
    modulo = {'baseline': '02_verificar_baseline',
              'comparacion': '04_verificar_modelos'}[tipo]
    subprocess.run(
        [sys.executable, '-m', f'src.modelado.pasos.{modulo}', str(carpeta)],
        cwd=RAIZ, check=True,
    )


def reproducir():
    """Crea ejecuciones nuevas y compara con el baseline generado en este flujo."""
    from src.modelado.pasos import baseline as _baseline
    from src.modelado.pasos import comparar_modelos as _comparar_modelos
    from src.modelado.pasos import exportar_imagenes as _exportar_imagenes

    carpeta_baseline = _baseline.main()
    verificar('baseline', carpeta_baseline)
    carpeta_comparacion = _comparar_modelos.main(baseline=carpeta_baseline.relative_to(RAIZ).as_posix())
    verificar('comparacion', carpeta_comparacion)
    imagenes = _exportar_imagenes.exportar(carpeta_comparacion)
    return {nombre: ruta.relative_to(RAIZ).as_posix() for nombre, ruta in (
        ('baseline', carpeta_baseline), ('comparacion', carpeta_comparacion), ('imagenes', imagenes),
    )}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Entrega 03: baseline, verificación, ML, verificación e imágenes. '
                    'Reutiliza Gold y crea carpetas nuevas; no adquiere ni prepara datos.',
    )
    parser.add_argument(
        '--verificar', action='store_true',
        help='Comprueba baseline y diez modelos de referencia sin entrenar ni generar imágenes.',
    )
    args = parser.parse_args(argv)
    if args.verificar:
        verificar('baseline', RAIZ / BASELINE)
        verificar('comparacion', RAIZ / COMPARACION)
        resultado = {'estado': 'verificado_sin_reajuste', 'baseline': BASELINE, 'comparacion': COMPARACION}
    else:
        resultado = reproducir()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return resultado
