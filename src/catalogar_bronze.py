"""Registra copias Bronze sin transformarlas y verifica sus huellas por bloques."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config/catalogo_bronze.json'
RAW_ROOTS = ('Fuentes', 'datos/bronze')


def raw_path(root, relative):
    if not isinstance(relative, str) or '\\' in relative or ':' in relative:
        raise ValueError(f'Ruta relativa no válida: {relative!r}')
    parts = PurePosixPath(relative).parts
    if not parts or '..' in parts or PurePosixPath(relative).is_absolute():
        raise ValueError(f'Ruta fuera de Bronze: {relative!r}')
    path = root / relative
    if not any(path.resolve().is_relative_to((root / folder).resolve()) for folder in RAW_ROOTS):
        raise ValueError(f'Ruta fuera de Bronze: {relative!r}')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Ruta fuera del proyecto: {relative!r}')
    return path


def fingerprint(path):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f'El archivo cambió durante la lectura: {path.name}')
    return {'bytes': before.st_size, 'sha256': digest.hexdigest(),
            'mtime_ns': before.st_mtime_ns,
            'modificacion_local_utc': datetime.fromtimestamp(before.st_mtime, timezone.utc).isoformat()}


def registered_files(root, catalog):
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
            raw_path(root, pattern)
            if entry['rol'] not in ('datos', 'documentacion'):
                raise ValueError(f'Rol no válido: {entry["rol"]}')
            matches = sorted(root.glob(pattern))
            if len(matches) != entry.get('cantidad', 1):
                raise ValueError(f'Número de archivos inesperado para {pattern}: {len(matches)}')
            for path in matches:
                relative = path.relative_to(root).as_posix()
                raw_path(root, relative)
                if not path.is_file() or relative in registered:
                    raise ValueError(f'Entrada repetida o no regular: {relative}')
                registered[relative] = {'recurso_id': resource['id'], 'rol': entry['rol']}
    actual = {path.relative_to(root).as_posix() for folder in RAW_ROOTS
              for path in (root / folder).rglob('*') if path.is_file()}
    if actual != set(registered):
        raise ValueError(f'Archivos sin catalogar: {sorted(actual - set(registered))}')
    return registered


def build_manifest(root, catalog):
    files = registered_files(root, catalog)
    records = []
    for relative, metadata in sorted(files.items()):
        print(f'Registrando {relative}', flush=True)
        records.append({'ruta': relative, **metadata, **fingerprint(raw_path(root, relative))})
    # Comprobar también archivos añadidos mientras se calculaban las huellas.
    if registered_files(root, catalog) != files:
        raise RuntimeError('Cambió el conjunto de entradas durante el registro')
    return {'version_manifiesto': 1, 'fecha_registro_utc': datetime.now(timezone.utc).isoformat(),
            'catalogo': catalog, 'archivos': records}


def verify_manifest(root, manifest):
    if manifest.get('version_manifiesto') != 1:
        raise ValueError('Versión de manifiesto no admitida')
    expected = registered_files(root, manifest['catalogo'])
    records = manifest['archivos']
    if len(records) != len(expected) or {r['ruta'] for r in records} != set(expected):
        raise ValueError('Las entradas del manifiesto no coinciden con el catálogo')
    for record in records:
        relative = record['ruta']
        if any(record[key] != value for key, value in expected[relative].items()):
            raise ValueError(f'Metadatos de archivo incoherentes: {relative}')
        print(f'Verificando {relative}', flush=True)
        observed = fingerprint(raw_path(root, relative))
        if any(observed[key] != record[key] for key in ('bytes', 'sha256')):
            raise ValueError(f'Integridad no válida: {relative}')
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verificar', type=Path, help='Manifiesto local que se quiere comprobar sin sobrescribirlo')
    args = parser.parse_args()
    try:
        if args.verificar:
            manifest = json.loads(args.verificar.read_text(encoding='utf-8'))
            total = verify_manifest(ROOT, manifest)
            print(f'Integridad comprobada: {total} archivos.')
        else:
            content = CONFIG.read_bytes()
            manifest = build_manifest(ROOT, json.loads(content))
            manifest['catalogo_sha256'] = hashlib.sha256(content).hexdigest()
            directory = ROOT / 'resultados/bronze'
            directory.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            path = directory / f'manifiesto_{stamp}.json'
            with path.open('x', encoding='utf-8') as stream:
                json.dump(manifest, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
            print(f'Manifiesto creado: {path.relative_to(ROOT).as_posix()} ({len(manifest["archivos"])} archivos)')
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
