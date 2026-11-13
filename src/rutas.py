"""Raíz del proyecto, independiente del directorio de ejecución."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def codigo_versionado(root, path, sha256):
    """Localiza una copia exacta del productor anterior; el llamador verifica la huella."""
    root, path = root.resolve(), path.resolve()
    if (path.is_relative_to(root / 'src') and path.suffix == '.py'
            and isinstance(sha256, str) and len(sha256) == 64
            and all(c in '0123456789abcdef' for c in sha256)):
        copia = (root / 'resultados/codigo_historico' / (sha256 + '.py')).resolve()
        if not copia.is_relative_to(root):
            raise ValueError('Copia de código fuera del proyecto')
        if copia.is_file():
            return copia
    return path
