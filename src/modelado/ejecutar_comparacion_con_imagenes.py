"""Ejecuta la comparación conservada y exporta automáticamente sus diez PNG."""

import json
import os
import subprocess
import sys

from src.datos_y_preparacion.historico.catalogar_bronze import ROOT
from src.modelado.exportar_clusters_descriptivos import exportar


def main():
    proceso = subprocess.run([sys.executable, '-m', 'src.modelado.ejecutar_comparacion_descriptiva'],
                             cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                             capture_output=True, text=True, encoding='utf-8', check=True)
    print(proceso.stdout, end='')
    if proceso.stderr:
        print(proceso.stderr, end='', file=sys.stderr)
    ruta = ROOT / json.loads(proceso.stdout.strip().splitlines()[-1])['carpeta']
    print(json.dumps({'imagenes': exportar(ruta).relative_to(ROOT).as_posix()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
