"""Pasos numerados; nombres descriptivos para importarlos sin duplicar código."""

from importlib import import_module


_MODULOS = {
    'bronze': '01_bronze',
    'territorio': '02_territorio',
    'demografia': '03_demografia',
    'recarga': '04_recarga',
    'trafico': '05_trafico',
    'osm': '06_osm',
    'capacidad': '07_capacidad',
    'integracion': '08_integracion',
    'gold': '09_gold',
}


def __getattr__(nombre):
    if nombre not in _MODULOS:
        raise AttributeError(f'{__name__} no contiene {nombre}')
    modulo = import_module(f'.{_MODULOS[nombre]}', __name__)
    globals()[nombre] = modulo
    return modulo
