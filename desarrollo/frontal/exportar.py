"""Prepara los datos del visor a partir de las salidas versionadas del TFM."""

import argparse
import csv
import json
import re
import struct
from pathlib import Path
from tempfile import NamedTemporaryFile

import duckdb

FRONTAL = Path(__file__).resolve().parent
RAIZ = FRONTAL.parents[1]
VERSION_GOLD = "20261020T153200478279Z"
EJECUCION = "20261111T161605225327Z"
MODELO = "kmeans_k6"
GOLD = RAIZ / "resultados/gold/contexto_municipal" / VERSION_GOLD / "gold_municipios.parquet"
ASIGNACIONES = RAIZ / "resultados/modelado/comparacion_descriptiva" / EJECUCION / "asignaciones_municipales.csv"
SALIDA = FRONTAL / "datos/municipios.json"
ETIQUETAS = {
    "0": "Parque elevado y muchos puntos",
    "1": "Parque muy reducido y oferta mínima",
    "2": "Parque intermedio y pocos puntos",
    "3": "Gran concentración de parque y recarga",
    "4": "Parque reducido con oferta registrada",
    "5": "Parque reducido y oferta mínima",
}
RECUENTOS = ("vehiculos_distintivo_0", "puntos_con_municipio_admitido")
PROVINCIAS = {"03": "Alicante/Alacant", "12": "Castellón/Castelló", "46": "Valencia/València"}


def leer_asignaciones():
    asignaciones = {}
    with ASIGNACIONES.open(encoding="utf-8-sig", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["configuracion"] != MODELO:
                continue
            codigo = fila["codigo_municipio"]
            if not re.fullmatch(r"[0-9]{5}", codigo) or codigo in asignaciones:
                raise ValueError(f"Código de asignación inválido o duplicado: {codigo!r}")
            if fila["version_gold"] != VERSION_GOLD or fila["perfil"] not in ETIQUETAS:
                raise ValueError(f"Versión o perfil inesperado en la asignación de {codigo}")
            asignaciones[codigo] = fila
    if len(asignaciones) != 541 or {fila["perfil"] for fila in asignaciones.values()} != set(ETIQUETAS):
        raise ValueError("Se esperaban 541 códigos asignados a los seis perfiles")
    return asignaciones


def anillos_wkb(wkb):
    """Lee los anillos 2D de un MultiPolygon WKB de Gold, incluidos sus huecos."""
    datos = memoryview(wkb)

    def leer_encabezado(posicion, tipo):
        orden = {0: ">", 1: "<"}[datos[posicion]]
        tipo_leido, cantidad = struct.unpack_from(orden + "II", datos, posicion + 1)
        if tipo_leido != tipo or not cantidad:
            raise ValueError("Tipo geométrico o número de partes inesperado")
        return orden, cantidad, posicion + 9

    _, num_poligonos, posicion = leer_encabezado(0, 6)
    for _ in range(num_poligonos):
        orden, num_anillos, posicion = leer_encabezado(posicion, 3)
        for _ in range(num_anillos):
            num_puntos, = struct.unpack_from(orden + "I", datos, posicion)
            inicio = posicion + 4
            posicion = inicio + num_puntos * 16
            puntos = list(struct.iter_unpack(orden + "dd", datos[inicio:posicion]))
            if len(puntos) < 4 or len(puntos) != num_puntos or puntos[0] != puntos[-1]:
                raise ValueError("Anillo municipal vacío, incompleto o abierto")
            yield puntos[:-1]
    if posicion != len(datos):
        raise ValueError("La geometría contiene bytes fuera de los anillos esperados")


def ruta_municipal(wkb):
    """Representa las coordenadas originales en un plano SVG, a un metro."""
    partes = []
    xs, ys = [], []
    for anillo in anillos_wkb(wkb):
        puntos = [(round(x) - 600000, 4520000 - round(y)) for x, y in anillo]
        x, y = zip(*puntos)
        xs.extend(x)
        ys.extend(y)
        partes.append("M" + " ".join(f"{px},{py}" for px, py in puntos) + "Z")
    return " ".join(partes), [min(xs), min(ys), max(xs), max(ys)]


def exportar():
    asignaciones = leer_asignaciones()
    with (RAIZ / "config/exclusiones_segmentacion.json").open(encoding="utf-8") as archivo:
        excluidos = {
            fila["codigo_municipio"] for fila in json.load(archivo)["municipios_excluidos"]
        }
    with duckdb.connect() as conexion:
        cursor = conexion.execute(
            """
            SELECT version_gold, codigo_municipio, codigo_provincia, nombre_municipio,
                   vehiculos_distintivo_0, puntos_con_municipio_admitido,
                   poblacion_total, anio_poblacion, instalaciones_pendientes_relacionadas,
                   instalaciones_ausentes_relacionadas, hay_incertidumbre_sin_localizar,
                   ST_AsWKB(geometria) AS wkb
            FROM read_parquet(?)
            ORDER BY codigo_municipio
            """,
            [str(GOLD)],
        )
        campos = [columna[0] for columna in cursor.description]
        filas = [dict(zip(campos, valores, strict=True)) for valores in cursor.fetchall()]

    codigos = {fila["codigo_municipio"] for fila in filas}
    if len(filas) != 542 or len(codigos) != 542:
        raise ValueError("Gold debe contener 542 municipios únicos")
    if set(asignaciones) - codigos or codigos - set(asignaciones) != excluidos:
        raise ValueError("La cobertura de las asignaciones y las exclusiones no coincide con Gold")

    for fila in filas:
        codigo = fila["codigo_municipio"]
        asignacion = asignaciones.get(codigo)
        provincia = fila["codigo_provincia"]
        if (not re.fullmatch(r"[0-9]{5}", codigo) or provincia not in PROVINCIAS
                or not codigo.startswith(provincia) or not fila["nombre_municipio"]):
            raise ValueError(f"Identificación municipal inválida para {codigo}")
        if fila.pop("version_gold") != VERSION_GOLD or fila.pop("anio_poblacion") != 2025:
            raise ValueError(f"Versión Gold o año de población inesperado en {codigo}")
        if asignacion and any(fila[campo] != int(asignacion[campo]) for campo in RECUENTOS):
            raise ValueError(f"Los recuentos de Gold y K-means no coinciden para {codigo}")
        fila["perfil"] = asignacion["perfil"] if asignacion else None
        fila["trazado"], fila["limites"] = ruta_municipal(fila.pop("wkb"))

    return {
        "versiones": {
            "gold": VERSION_GOLD, "ejecucion": EJECUCION, "modelo": MODELO,
            "etiquetas": "Entrega 03, apartado 5", "geometria": "EPSG:25830",
        },
        "perfiles": ETIQUETAS,
        "provincias": PROVINCIAS,
        "municipios": filas,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=SALIDA, help="Ruta del JSON de navegación.")
    salida = parser.parse_args().salida
    provisional = None
    try:
        datos = exportar()
        salida.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=salida.parent, delete=False) as temporal:
            provisional = Path(temporal.name)
            json.dump(datos, temporal, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        provisional.replace(salida)
    except (OSError, ValueError, duckdb.Error) as error:
        parser.exit(1, f"No se pudo exportar el visor: {error}\n")
    finally:
        if provisional is not None:
            provisional.unlink(missing_ok=True)
    print(f"Exportados {len(datos['municipios'])} municipios y 541 perfiles en {salida.name}.")


if __name__ == "__main__":
    main()
