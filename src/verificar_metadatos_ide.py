"""Comprueba la acreditación documental de fecha y CRS de una copia i-DE, sin red."""

import argparse
import csv
import json
import unicodedata
from collections import Counter
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from catalogar_bronze import ROOT, fingerprint
from preparar_capacidad_demanda import RAW, PROVINCES

PAGE = 'https://www.i-de.es/es/conexion-red-electrica/suministro-electrico/mapa-capacidad-consumo'
BOE = 'https://www.boe.es/buscar/doc.php?id=BOE-A-2025-9913'


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).split())


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = set()
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'a':
            self.links.update(v for k, v in attrs if k == 'href')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


def verify(root, evidence):
    if evidence['version'] != 1 or evidence['recurso_id'] != 'ide_capacidad_demanda':
        raise ValueError('Contrato de evidencia i-DE no admitido')

    def checked(entry):
        path = (root / entry['ruta']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Evidencia fuera del proyecto')
        stamp = fingerprint(path)
        if any(stamp[k] != entry[k] for k in ('bytes', 'sha256')):
            raise ValueError(f"Huella distinta: {entry['ruta']}")
        return path

    paths = {name: checked(entry) for name, entry in evidence['archivos'].items()}
    source, official = paths['original'], paths['csv_oficial']
    if evidence['archivos']['original']['sha256'] != evidence['archivos']['csv_oficial']['sha256']:
        raise ValueError('El CSV oficial no coincide con el original')
    with source.open('rb') as a, official.open('rb') as b:
        while True:
            left, right = a.read(1024 * 1024), b.read(1024 * 1024)
            if left != right:
                raise ValueError('Los CSV no son idénticos byte por byte')
            if not left:
                break
    with source.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, delimiter=';')
        if next(reader) != list(RAW.values()):
            raise ValueError('Cabecera ajena al formato comprobado')
        rows = list(reader)
    if any(len(row) != len(RAW) for row in rows):
        raise ValueError('Ancho de registro i-DE incorrecto')
    if len({r[-1] for r in rows}) != len(rows) or any(not r[-1].strip() for r in rows):
        raise ValueError('Identificadores vacíos o repetidos')
    provinces = Counter(r[1] for r in rows if r[1] in PROVINCES)
    if len(rows) != evidence['filas_nacionales'] or dict(provinces) != evidence['filas_cv_provincia']:
        raise ValueError('Recuentos diferentes de la edición acreditada')

    published = date.fromisoformat(evidence['fecha_publicacion'])
    url = evidence['url_csv_oficial']
    if not url.startswith('https://www.i-de.es/documents/') or published.strftime('%Y_%m_%d') not in url:
        raise ValueError('Fecha y enlace de edición incoherentes')
    page = json.loads(paths['pagina_ide'].read_text(encoding='utf-8'))
    regulation = Document()
    regulation.feed(paths['norma'].read_text(encoding='utf-8'))
    if url not in {entry['url'] for entry in page['enlaces']}:
        raise ValueError('El histórico conservado no enlaza el CSV')
    text = normalized(page['texto'])
    if 'resolución de 30 de abril de 2025' not in text:
        raise ValueError('No consta la declaración de formato del proveedor')
    text = normalized(' '.join(regulation.text))
    start = '1. Formato para la publicación de las capacidades de acceso para instalaciones de demanda'
    end = '2. Formato para la publicación de las capacidades de acceso para instalaciones de generación'
    if start not in text or end not in text:
        raise ValueError('No se identifica el apartado de demanda de la norma')
    demand = text.split(start, 1)[1].split(end, 1)[0]
    for field in ('X', 'Y'):
        fragment = f'Coordenada UTM {field}. Coordenadas de la ubicación de la subestación, en el sistema ETRS89 UTM referidas al huso 30 para la península'
        if fragment not in demand:
            raise ValueError('La norma conservada no acredita CRS en el apartado de demanda')
    rule = 'dentro de los cinco primeros días del mes siguiente al que se refiere la información'
    if rule not in text or not 1 <= published.day <= 5:
        raise ValueError('No se acredita la regla del periodo mensual')
    month = date(published.year - (published.month == 1), 12 if published.month == 1 else published.month - 1, 1)
    if evidence['periodo_referencia'] != month.strftime('%Y-%m'):
        raise ValueError('Periodo mensual incoherente con la publicación')
    if evidence['crs_cv'] != 'EPSG:25830' or evidence['fecha_corte_exacta'] is not None:
        raise ValueError('Metadatos incompatibles con el alcance acreditado')

    # Comprobar de nuevo las evidencias tras la lectura; no se modifica ningún insumo.
    for entry in evidence['archivos'].values():
        checked(entry)
    return {'estado': 'fecha_y_crs_acreditados_documentalmente',
            'comprobado_utc': datetime.now(timezone.utc).isoformat(),
            'identidad_csv': 'igualdad_binaria_completa', 'sha256_original': evidence['archivos']['original']['sha256'],
            'filas_nacionales': len(rows), 'filas_cv': sum(provinces.values()),
            'fecha_publicacion': published.isoformat(), 'periodo_referencia': evidence['periodo_referencia'],
            'criterio_periodo': 'mes_anterior_segun_formato_publicacion_CNMC',
            'fecha_corte_exacta': None, 'crs_cv': 'EPSG:25830',
            'referencia_crs': 'declaracion_de_formato_ide_y_anexo_demanda_BOE_A_2025_9913',
            'pagina': PAGE, 'norma': BOE,
            'alcance': 'Acreditación de metadatos; no genera capas, asignaciones municipales o una nueva ejecución Silver.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidencias', type=Path, required=True)
    parser.add_argument('--salida', type=Path)
    args = parser.parse_args()
    evidence_stamp = fingerprint(args.evidencias)
    result = verify(ROOT, json.loads(args.evidencias.read_text(encoding='utf-8')))
    if any(fingerprint(args.evidencias)[k] != evidence_stamp[k] for k in ('bytes', 'sha256')):
        raise ValueError('Cambió la declaración de evidencias durante la comprobación')
    result['declaracion_sha256'] = evidence_stamp['sha256']
    result['codigo_sha256'] = fingerprint(Path(__file__))['sha256']
    if args.salida:
        with args.salida.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
