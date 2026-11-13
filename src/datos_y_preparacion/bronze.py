"""Bronze: identificación de originales y comprobación de entradas."""

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import duckdb
import json
import tempfile

from src.datos_y_preparacion.comunes import RAIZ, comprobar_archivo, conectar, huella
from src.datos_y_preparacion.silver.capacidad import metadatos_ide_verify
from src.datos_y_preparacion.silver.recarga import recarga_geo_evidence


ENTRADAS = {
    'catalogo': 'config/catalogo_bronze.json',
    'recarga_principal': 'resultados/revision_recarga/20261018_ampliacion/miteco_exportacion_actual.csv',
    'metadatos_recarga': 'resultados/investigacion_datum_miteco/20261016/catalogo.json',
    'metadatos_capacidad': 'resultados/investigacion_ide/20261019/metadatos.json',
    'decisiones_recarga': 'resultados/revision_recarga/20261018_revision_manual/decisiones.json',
}


BRONZE_RAW_ROOTS = ('Fuentes', 'datos/bronze')


def bronze_raw_path(root, relative):
    if not isinstance(relative, str) or '\\' in relative or ':' in relative:
        raise ValueError(f'Ruta relativa no válida: {relative!r}')
    parts = PurePosixPath(relative).parts
    if not parts or '..' in parts or PurePosixPath(relative).is_absolute():
        raise ValueError(f'Ruta fuera de Bronze: {relative!r}')
    path = root / relative
    if not any(path.resolve().is_relative_to((root / folder).resolve()) for folder in BRONZE_RAW_ROOTS):
        raise ValueError(f'Ruta fuera de Bronze: {relative!r}')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Ruta fuera del proyecto: {relative!r}')
    return path


def bronze_registered_files(root, catalog):
    resources = catalog['recursos']
    ids = [resource['id'] for resource in resources]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('El catálogo está vacío o repite identificadores')
    registered = {}
    for resource in resources:
        if not resource['entradas']:
            raise ValueError(f"Recurso sin entradas: {resource['id']}")
        for entry in resource['entradas']:
            pattern = entry['patron']
            bronze_raw_path(root, pattern)
            if entry['rol'] not in ('datos', 'documentacion'):
                raise ValueError(f'Rol no válido: {entry["rol"]}')
            matches = sorted(root.glob(pattern))
            if len(matches) != entry.get('cantidad', 1):
                raise ValueError(f'Número de archivos inesperado para {pattern}: {len(matches)}')
            for path in matches:
                relative = path.relative_to(root).as_posix()
                bronze_raw_path(root, relative)
                if not path.is_file() or relative in registered:
                    raise ValueError(f'Entrada repetida o no regular: {relative}')
                registered[relative] = {'recurso_id': resource['id'], 'rol': entry['rol']}
    actual = {path.relative_to(root).as_posix() for folder in BRONZE_RAW_ROOTS
              for path in (root / folder).rglob('*') if path.is_file()}
    if actual != set(registered):
        raise ValueError(f'Archivos sin catalogar: {sorted(actual - set(registered))}')
    return registered


def bronze_build_manifest(root, catalog):
    files = bronze_registered_files(root, catalog)
    records = []
    for relative, metadata in sorted(files.items()):
        print(f'Registrando {relative}', flush=True)
        records.append({'ruta': relative, **metadata, **huella(bronze_raw_path(root, relative))})
    # Comprobar también archivos añadidos mientras se calculaban las huellas.
    if bronze_registered_files(root, catalog) != files:
        raise RuntimeError('Cambió el conjunto de entradas durante el registro')
    return {'version_manifiesto': 1, 'fecha_registro_utc': datetime.now(timezone.utc).isoformat(),
            'catalogo': catalog, 'archivos': records}


def comprobar_entradas():
    if duckdb.__version__ != '1.5.0':
        raise ValueError('Instalar las versiones de requirements.txt; se requiere DuckDB 1.5.0')
    with tempfile.TemporaryDirectory() as temporal:
        with conectar(Path(temporal)):
            pass
    # Registrar todos los módulos del flujo, incluidos los puntos de entrada.
    codigo = [RAIZ / 'src/__init__.py', RAIZ / 'src/rutas.py', RAIZ / 'src/preparar_dataset.py']
    codigo.extend(p for p in sorted(Path(__file__).parent.rglob('*.py')) if 'historico' not in p.parts)
    archivos = [comprobar_archivo(RAIZ, p) for p in codigo]
    for ruta in ENTRADAS.values():
        archivos.append(comprobar_archivo(RAIZ, RAIZ / ruta))
    catalogo = json.loads((RAIZ / ENTRADAS['catalogo']).read_text(encoding='utf-8'))
    bronze = bronze_build_manifest(RAIZ, catalogo)
    archivos.extend(bronze['archivos'])
    recarga_geo_evidence(RAIZ, RAIZ / ENTRADAS['metadatos_recarga'])
    archivos.append(comprobar_archivo(RAIZ, RAIZ / (ENTRADAS['metadatos_recarga'] + '.adquisicion.json')))
    evidencia = json.loads((RAIZ / ENTRADAS['metadatos_capacidad']).read_text(encoding='utf-8'))
    metadatos = metadatos_ide_verify(RAIZ, evidencia)
    archivos.extend(comprobar_archivo(RAIZ, RAIZ / e['ruta'], e) for e in evidencia['archivos'].values())
    recibo_path = RAIZ / (ENTRADAS['recarga_principal'] + '.adquisicion.json')
    archivos.append(comprobar_archivo(RAIZ, recibo_path))
    recibo = json.loads(recibo_path.read_text(encoding='utf-8'))
    principal = comprobar_archivo(RAIZ, RAIZ / ENTRADAS['recarga_principal'], recibo)
    archivos.append(principal)
    adquisicion = datetime.fromisoformat(recibo['fecha_utc'])
    if adquisicion.tzinfo is None:
        raise ValueError('Adquisición de recarga sin zona horaria')
    origenes = {e['ruta']: e['recurso_id'] + ':' + e['sha256'] for e in bronze['archivos']}
    origenes['recarga_principal'] = 'miteco_recarga:' + principal['sha256']
    return bronze, archivos, metadatos, adquisicion, origenes
