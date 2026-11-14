"""Pasos numerados; nombres descriptivos para importarlos sin duplicar código."""

from importlib import import_module


_MODULOS = {
    'baseline': '01_baseline',
    'verificar_baseline': '02_verificar_baseline',
    'comparar_modelos': '03_comparar_modelos',
    'verificar_modelos': '04_verificar_modelos',
    'exportar_imagenes': '05_exportar_imagenes',
}


def __getattr__(nombre):
    if nombre not in _MODULOS:
        raise AttributeError(f'{__name__} no contiene {nombre}')
    modulo = import_module(f'.{_MODULOS[nombre]}', __name__)
    globals()[nombre] = modulo
    return modulo
