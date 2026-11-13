"""Entrada compatible con los comandos de la Entrega 02.

La implementación está en datos_y_preparacion; se recomienda ejecutarla con:
python -m src.datos_y_preparacion
"""

import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.datos_y_preparacion.flujo import main

if __name__ == '__main__':
    main()
