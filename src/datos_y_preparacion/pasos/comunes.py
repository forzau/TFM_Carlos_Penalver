"""SQL, integridad de archivos, conexión y exportación de tablas."""

from datetime import datetime, timezone
from pathlib import Path
import duckdb
import hashlib
import json
import struct

from src.rutas import RAIZ


def identificador_sql(name):
    return '"' + name.replace('"', '""') + '"'


def texto_sql(value):
    return "'" + str(value).replace("'", "''") + "'"


def consultar(connection, sql):
    cursor = connection.execute(sql)
    return [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]


def huella(path):
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


def comprobar_clave(connection, table, columns):
    key = ','.join(identificador_sql(column) for column in columns)
    nulls = ' OR '.join(f'{identificador_sql(column)} IS NULL' for column in columns)
    if connection.execute(f'SELECT count(*) FROM {identificador_sql(table)} WHERE {nulls}').fetchone()[0]:
        raise ValueError(f'Clave incompleta: {table}')
    if connection.execute(f'SELECT count(*) FROM (SELECT {key} FROM {identificador_sql(table)} GROUP BY {key} HAVING count(*)>1)').fetchone()[0]:
        raise ValueError(f'Clave repetida: {table}')


def gpkg_gpkg_wkb(blob, expected_srs):
    """Extrae el WKB estándar sin perder el fid que se lee con SQLite."""
    if not isinstance(blob, bytes) or len(blob) < 8 or blob[:3] != b'GP\x00':
        raise ValueError('Cabecera GeoPackage no admitida')
    flags = blob[3]
    envelope = (flags >> 1) & 7
    if flags & 0xE0 or envelope > 4:
        raise ValueError('Geometría extendida o indicadores GeoPackage no admitidos')
    order = '<' if flags & 1 else '>'
    if struct.unpack(order + 'i', blob[4:8])[0] != expected_srs:
        raise ValueError('SRS de geometría distinto del declarado en su capa')
    offset = 8 + (0, 32, 48, 48, 64)[envelope]
    if len(blob) < offset + 5 or blob[offset] not in (0, 1):
        raise ValueError('Contenido WKB ausente o truncado')
    return blob[offset:]


def comprobar_archivo(root, path, expected=None):
    path = path.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Entrada fuera del proyecto')
    stamp = huella(path)
    if expected and any(stamp[k] != expected[k] for k in ('bytes', 'sha256')):
        raise ValueError(f'Entrada distinta de su informe o recibo: {path.name}')
    return {'ruta': path.relative_to(root.resolve()).as_posix(), **stamp}


def integracion_scalar(c, sql):
    return c.execute(sql).fetchone()[0]


def exigir_cero(c, sql, message):
    if integracion_scalar(c, sql):
        raise ValueError(message)


def guardar_json(path, contenido):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contenido, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')


def conectar(temporal):
    c = duckdb.connect(str(temporal / 'trabajo.duckdb'), config={
        'threads': 2, 'memory_limit': '1GB', 'storage_compatibility_version': 'v1.5.0',
        'extension_directory': str(RAIZ / '.venv/duckdb_extensions'),
        'temp_directory': str(temporal / 'desborde')})
    try:
        c.execute('LOAD spatial')
        c.execute("SET TimeZone='UTC'")
    except Exception:
        c.close()
        raise
    return c


def exportar_tablas(c, carpeta, claves):
    carpeta.mkdir(parents=True, exist_ok=False)
    salidas = {}
    for nombre, clave in claves.items():
        if clave:
            comprobar_clave(c, nombre, clave)
        path = carpeta / (nombre + '.parquet')
        c.execute(f'COPY {identificador_sql(nombre)} TO ? (FORMAT PARQUET, COMPRESSION ZSTD)', [str(path)])
        esquema = [(r[0], r[1]) for r in c.execute('DESCRIBE ' + identificador_sql(nombre)).fetchall()]
        restaurado = [(r[0], r[1]) for r in c.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(path)]).fetchall()]
        if esquema != restaurado:
            raise ValueError(f'Exportación alteró el esquema: {nombre}')
        geometrias = [campo for campo, tipo in esquema if tipo.startswith('GEOMETRY')]
        campos = ','.join('ST_AsWKB(' + identificador_sql(campo) + ') AS ' + identificador_sql(campo)
                          if campo in geometrias else identificador_sql(campo) for campo, _ in esquema)
        exigir_cero(c, f'''SELECT count(*) FROM (
            (SELECT {campos} FROM {identificador_sql(nombre)} EXCEPT ALL
             SELECT {campos} FROM read_parquet({texto_sql(str(path))})) UNION ALL
            (SELECT {campos} FROM read_parquet({texto_sql(str(path))}) EXCEPT ALL
             SELECT {campos} FROM {identificador_sql(nombre)}))''', f'Exportación alteró valores: {nombre}')
        if geometrias:
            metadatos = dict(c.execute('SELECT decode(key),decode(value) FROM parquet_kv_metadata(?)', [str(path)]).fetchall())
            geo = json.loads(metadatos['geo'])
            for campo in geometrias:
                if geo['columns'][campo]['crs']['id'] != {'authority': 'EPSG', 'code': 25830}:
                    raise ValueError(f'CRS GeoParquet incorrecto: {nombre}/{campo}')
        salidas[nombre] = {'ruta': path.relative_to(RAIZ).as_posix(), **huella(path),
            'clave': clave, 'esquema': [{'campo': a, 'tipo': b} for a, b in esquema],
            'filas': c.execute('SELECT count(*) FROM ' + identificador_sql(nombre)).fetchone()[0]}
    return salidas
