"""Descarga las referencias oficiales declaradas en Bronze sin sustituir copias."""

import hashlib
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from catalogar_bronze import CONFIG, ROOT, fingerprint, raw_path

REFERENCES = ('ine_municipios_2025', 'ign_unidades_cv')


def download(url, path, limit=256 * 1024 * 1024):
    receipt_path = path.with_suffix(path.suffix + '.adquisicion.json')
    if path.exists():
        if not receipt_path.exists():
            raise ValueError(f'Existe una copia sin recibo de adquisición: {path.name}')
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        observed = fingerprint(path)
        if receipt['url_solicitada'] != url or any(observed[k] != receipt[k] for k in ('bytes', 'sha256')):
            raise ValueError(f'La copia existente difiere de su recibo: {path.name}')
        return receipt
    if receipt_path.exists():
        raise ValueError(f'Existe recibo sin la copia original: {path.name}')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    digest, total = hashlib.sha256(), 0
    # Un temporal exclusivo evita pisar una descarga interrumpida o en curso.
    with temporary.open('xb') as stream:
        try:
            with urlopen(Request(url, headers={'User-Agent': 'TFM-source-audit/1.0'}), timeout=60) as response:
                while block := response.read(1024 * 1024):
                    total += len(block)
                    if total > limit:
                        raise ValueError(f'Descarga superior al límite: {path.name}')
                    stream.write(block)
                    digest.update(block)
                receipt = {'url_solicitada': url, 'url_respuesta': response.url,
                           'fecha_descarga_utc': datetime.now(timezone.utc).isoformat(),
                           'bytes': total, 'sha256': digest.hexdigest(),
                           'content_type': response.headers.get('Content-Type'),
                           'last_modified_http': response.headers.get('Last-Modified')}
        except BaseException:
            stream.close()
            temporary.unlink()
            raise
    temporary.rename(path)
    with receipt_path.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return receipt


def main():
    catalog = json.loads(CONFIG.read_text(encoding='utf-8'))
    for resource in catalog['recursos']:
        if resource['id'] not in REFERENCES:
            continue
        for entry in resource['entradas']:
            if 'url' in entry:
                receipt = download(entry['url'], raw_path(ROOT, entry['patron']))
                print(f"{resource['id']}: {entry['patron']} ({receipt['bytes']} bytes)", flush=True)


if __name__ == '__main__':
    main()
