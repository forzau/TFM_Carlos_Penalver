"""Fija bloques espaciales y estratos de tamaño sin ajustar la segmentación."""

import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb


from src.rutas import RAIZ
GOLD = "resultados/gold/contexto_municipal/20261020T153200478279Z/gold_municipios.parquet"
SELECCION = "resultados/modelado/renta_sempere/20261105/20261105T163350801909Z/rentas_municipios_incluidos.parquet"
RECUENTO = "resultados/diseno_particiones/20261106/recuento_tramos_poblacion.json"
EXCLUSIONES = "config/exclusiones_segmentacion.json"
SEMILLA = 20261106
LADO_M = 20000
INTENTOS = 32
TRAMOS = ["<=2000", ">2000 y <=10000", ">10000 y <=50000", ">50000 y <100000", ">=100000"]


def huella(ruta):
    with ruta.open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").hexdigest()


def estrato(poblacion):
    return next((i for i, limite in enumerate((2000, 10000, 50000, 99999)) if poblacion <= limite), 4)


def repartir(bloques, totales, semilla):
    """Equilibra cinco lotes completos: prueba final y cuatro validaciones."""
    rng = random.Random(semilla)
    objetivos = [n / 5 for n in totales]

    def coste(vector):
        return sum(((n - t) / max(t, 1)) ** 2 for n, t in zip(vector, objetivos)) + ((sum(vector) - sum(objetivos)) / sum(objetivos)) ** 2

    claves = sorted(bloques)
    anclas = [b for b in claves if bloques[b][4]]
    assert len(anclas) == 5 and all(bloques[b][4] == 1 for b in anclas)
    rng.shuffle(anclas)
    asignacion = {b: grupo for grupo, b in enumerate(anclas)}
    cuentas = [list(bloques[b]) for b in anclas]
    otros = [b for b in claves if b not in asignacion]
    rng.shuffle(otros)
    otros.sort(key=lambda b: -sum(n / t for n, t in zip(bloques[b], totales)))
    for b in otros:
        grupos = list(range(5))
        rng.shuffle(grupos)
        grupo = min(grupos, key=lambda g: coste([x + y for x, y in zip(cuentas[g], bloques[b])]) - coste(cuentas[g]))
        asignacion[b] = grupo
        cuentas[grupo] = [x + y for x, y in zip(cuentas[grupo], bloques[b])]

    # La mejora solo usa conteos de población; no consulta resultados de modelos.
    for _ in range(12):
        mejora = False
        rng.shuffle(otros)
        for b in otros:
            origen = asignacion[b]
            resto = [x - y for x, y in zip(cuentas[origen], bloques[b])]
            for destino in range(5):
                if destino == origen:
                    continue
                suma = [x + y for x, y in zip(cuentas[destino], bloques[b])]
                if coste(resto) + coste(suma) < coste(cuentas[origen]) + coste(cuentas[destino]) - 1e-12:
                    cuentas[origen], cuentas[destino] = resto, suma
                    asignacion[b] = destino
                    mejora = True
                    break
        for i, b in enumerate(otros):
            for d in otros[i + 1:]:
                origen, destino = asignacion[b], asignacion[d]
                if origen == destino:
                    continue
                nueva_a = [x - y + z for x, y, z in zip(cuentas[origen], bloques[b], bloques[d])]
                nueva_b = [x - z + y for x, y, z in zip(cuentas[destino], bloques[b], bloques[d])]
                if coste(nueva_a) + coste(nueva_b) < coste(cuentas[origen]) + coste(cuentas[destino]) - 1e-12:
                    cuentas[origen], cuentas[destino] = nueva_a, nueva_b
                    asignacion[b], asignacion[d] = destino, origen
                    mejora = True
        if not mejora:
            break
    return sum(coste(v) for v in cuentas), asignacion


def validar(filas, asignacion):
    codigos = {f["codigo_municipio"] for f in filas}
    assert len(codigos) == len(filas) == 541 and "46201" not in codigos
    assert set(asignacion) == {f["bloque_espacial"] for f in filas}
    assert set(asignacion.values()) == set(range(5))
    for grupo in range(5):
        lote = [f for f in filas if asignacion[f["bloque_espacial"]] == grupo]
        cuenta = Counter(f["estrato_indice"] for f in lote)
        assert set(cuenta) == set(range(5)) and cuenta[4] == 1
        assert 0.18 <= len(lote) / len(filas) <= 0.22
    prueba = {f["codigo_municipio"] for f in filas if asignacion[f["bloque_espacial"]] == 0}
    desarrollo = codigos - prueba
    for grupo in range(1, 5):
        validacion = {f["codigo_municipio"] for f in filas if asignacion[f["bloque_espacial"]] == grupo}
        entrenamiento = desarrollo - validacion
        assert not (prueba & (entrenamiento | validacion))
        assert entrenamiento.isdisjoint(validacion) and entrenamiento | validacion == desarrollo
        bloques_entrenamiento = {f["bloque_espacial"] for f in filas if f["codigo_municipio"] in entrenamiento}
        bloques_validacion = {f["bloque_espacial"] for f in filas if f["codigo_municipio"] in validacion}
        assert bloques_entrenamiento.isdisjoint(bloques_validacion)


def main():
    assert [estrato(n) for n in (2000, 2001, 10000, 10001, 50000, 50001, 99999, 100000)] == [0, 1, 1, 2, 2, 3, 3, 4]
    previo = json.loads((RAIZ / RECUENTO).read_text(encoding="utf-8"))
    assert all(huella(RAIZ / f["ruta"]) == f["sha256"] for f in previo["fuentes"])
    excluidos = json.loads((RAIZ / EXCLUSIONES).read_text(encoding="utf-8"))["municipios_excluidos"]
    assert [f["codigo_municipio"] for f in excluidos] == ["46201"]
    c = duckdb.connect(config={"extension_directory": str(RAIZ / ".venv/duckdb_extensions")})
    c.execute("LOAD spatial")
    consulta = """WITH base AS (
        SELECT g.version_gold, g.codigo_municipio, g.nombre_municipio,
        g.codigo_provincia, g.poblacion_total, g.anio_poblacion,
        ST_PointOnSurface(g.geometria) AS punto
        FROM read_parquet(?) g JOIN read_parquet(?) s
        USING(version_gold, codigo_municipio))
        SELECT version_gold, codigo_municipio, nombre_municipio,
        codigo_provincia, poblacion_total, anio_poblacion,
        ST_X(punto) AS x_m, ST_Y(punto) AS y_m
        FROM base ORDER BY codigo_municipio"""
    datos = c.execute(consulta, [str(RAIZ / GOLD), str(RAIZ / SELECCION)]).fetchall()
    columnas = [d[0] for d in c.description]
    filas = [dict(zip(columnas, f)) for f in datos]
    assert all(f["anio_poblacion"] == 2025 and f["poblacion_total"] > 0 and math.isfinite(f["x_m"]) and math.isfinite(f["y_m"]) for f in filas)
    bloques = defaultdict(lambda: [0] * 5)
    for f in filas:
        f["celda_x"] = math.floor(f["x_m"] / LADO_M)
        f["celda_y"] = math.floor(f["y_m"] / LADO_M)
        f["bloque_espacial"] = f'{f["celda_x"]}_{f["celda_y"]}'
        f["estrato_indice"] = estrato(f["poblacion_total"])
        f["estrato_poblacion"] = TRAMOS[f["estrato_indice"]]
        bloques[f["bloque_espacial"]][f["estrato_indice"]] += 1
    totales = [sum(v[i] for v in bloques.values()) for i in range(5)]
    assert totales == [t["n"] for t in previo["tramos"]]
    candidatos = [(s, *repartir(bloques, totales, s)) for s in range(SEMILLA, SEMILLA + INTENTOS)]
    semilla, coste, asignacion = min(candidatos, key=lambda a: (a[1], a[0]))
    validar(filas, asignacion)
    assert repartir(bloques, totales, semilla)[1] == asignacion
    for f in filas:
        grupo = asignacion[f["bloque_espacial"]]
        f["conjunto"] = "prueba_final" if grupo == 0 else "desarrollo"
        f["particion_interna"] = grupo or None

    ejecucion = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    salida = RAIZ / "resultados/modelado/particiones" / ejecucion
    salida.mkdir(parents=True, exist_ok=False)
    csv_path = salida / "particiones_municipales.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)
    c.read_csv(str(csv_path), columns={k: ("BIGINT" if k in ("poblacion_total", "anio_poblacion", "celda_x", "celda_y", "estrato_indice", "particion_interna") else "DOUBLE" if k in ("x_m", "y_m") else "VARCHAR") for k in filas[0]}).create_view("particiones")
    c.sql("SELECT * FROM particiones ORDER BY codigo_municipio").write_parquet(str(salida / "particiones_municipales.parquet"))
    resumen = []
    for grupo in range(5):
        lote = [f for f in filas if asignacion[f["bloque_espacial"]] == grupo]
        resumen.append({"grupo": grupo, "uso": "prueba_final" if grupo == 0 else f"validacion_interna_{grupo}", "n": len(lote), "bloques": len({f["bloque_espacial"] for f in lote}), "tramos": [sum(f["estrato_indice"] == i for f in lote) for i in range(5)], "provincias": dict(sorted(Counter(f["codigo_provincia"] for f in lote).items()))})
    entrenamiento = {"ajuste_final": {f["codigo_municipio"] for f in filas if f["conjunto"] == "desarrollo"}}
    entrenamiento.update({f"interna_{i}": {f["codigo_municipio"] for f in filas if f["conjunto"] == "desarrollo" and f["particion_interna"] != i} for i in range(1, 5)})
    donantes = {"03068", "03130", "12123"}
    manifiesto = {
        "ejecucion": ejecucion, "n_municipios": len(filas), "n_bloques": len(bloques),
        "crs": "EPSG:25830, ya presente en Gold; sin reproyeccion", "lado_celda_m": LADO_M,
        "asignacion_bloque": "floor(ST_X(ST_PointOnSurface(geometria))/20000), floor(ST_Y(...)/20000); origen fijo 0,0",
        "semilla_base": SEMILLA, "intentos": INTENTOS, "semilla_elegida": semilla, "coste": coste,
        "objetivo": "Minimizar desviaciones relativas cuadraticas de conteos por tramo y total en cinco lotes. Un bloque con gran ciudad en cada lote; cuatro validaciones internas del desarrollo. Sin variables de renta, parque, oferta ni resultados de modelos.",
        "consulta": consulta, "tramos": TRAMOS, "totales_tramos": totales, "resumen": resumen,
        "regla_interna": "Para i=1..4, entrenar con desarrollo cuya particion_interna != i; validar con desarrollo cuya particion_interna == i. Prueba final nunca interviene.",
        "donantes_sempere_disponibles_sin_consultar_importes": {k: sorted(v & donantes) for k, v in entrenamiento.items()},
        "limites": ["20 km es una eleccion operativa inicial, no un alcance de autocorrelacion validado.", "Bloques por punto representativo: no se dividen observaciones municipales ni se garantiza contiguidad de todos sus recintos.", "No se aplica banda de separacion: puede haber vecinos de bloques diferentes en entrenamiento y evaluacion.", "La prueba queda fijada por metadatos de diseño; no se han ajustado modelos ni evaluado resultados."],
        "fuentes": [{"ruta": p, "sha256": huella(RAIZ / p)} for p in (GOLD, SELECCION, RECUENTO, EXCLUSIONES)],
        "productor": {"ruta": Path(__file__).resolve().relative_to(RAIZ).as_posix(), "sha256": huella(Path(__file__))},
        "salidas": [{"ruta": p.relative_to(RAIZ).as_posix(), "sha256": huella(p)} for p in sorted(salida.iterdir())],
        "verificaciones": ["541 codigos unicos, sin Puebla", "Cinco tramos en cada lote, una gran ciudad por lote", "Bloques integros y sin cruce entrenamiento/validacion/prueba", "Prueba solo en conjunto final; validaciones disjuntas cubren desarrollo", "Recuentos reconciliados con diagnostico previo", "Misma asignacion al repetir la semilla elegida"],
    }
    (salida / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"salida": salida.relative_to(RAIZ).as_posix(), "resumen": resumen, "semilla": semilla, "coste": coste}, ensure_ascii=True))


if __name__ == "__main__":
    main()
