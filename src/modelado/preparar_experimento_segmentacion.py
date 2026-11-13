"""Prepara desarrollo y validaciones; no ejecuta el baseline ni abre la prueba final."""

import csv
import hashlib
import json
import math
import random
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import duckdb
import numpy as np
import sklearn
from sklearn.metrics import adjusted_rand_score, silhouette_samples
from sklearn.preprocessing import StandardScaler


from src.rutas import RAIZ
PARTICIONES = "resultados/modelado/particiones/20261106T110046844319Z"
RENTAS = "resultados/modelado/renta_sempere/20261105/20261105T163350801909Z"
GOLD = "resultados/gold/contexto_municipal/20261020T153200478279Z/gold_municipios.parquet"
DONANTES = {"03068", "03130", "12123"}
VARIABLES = ["vehiculos_distintivo_0", "proporcion_distintivo_0", "renta_modelado_2023_eur"]
Z = ["z_log1p_volumen", "z_proporcion", "z_renta"]
SEMILLA = 20261106
CONSULTA = """SELECT p.version_gold, p.codigo_municipio, p.nombre_municipio,
    p.bloque_espacial, p.particion_interna, p.estrato_poblacion,
    g.parque_total, g.vehiculos_distintivo_0, g.proporcion_distintivo_0,
    CASE WHEN p.codigo_municipio = '46226' THEN NULL
         ELSE r.renta_modelado_2023_eur END AS renta_modelado_2023_eur,
    r.estado_renta_modelado
    FROM read_parquet(?) p
    JOIN read_parquet(?) g USING(version_gold, codigo_municipio)
    JOIN read_parquet(?) r USING(version_gold, codigo_municipio)
    WHERE p.conjunto = 'desarrollo' ORDER BY p.codigo_municipio"""


def huella(ruta):
    with ruta.open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").hexdigest()


def cargar_desarrollo():
    previo = json.loads((RAIZ / PARTICIONES / "manifiesto.json").read_text(encoding="utf-8"))
    fuentes = previo["fuentes"] + previo["salidas"]
    assert all(huella(RAIZ / f["ruta"]) == f["sha256"] for f in fuentes)
    c = duckdb.connect()
    datos = c.execute(CONSULTA, [str(RAIZ / PARTICIONES / "particiones_municipales.parquet"), str(RAIZ / GOLD), str(RAIZ / RENTAS / "rentas_municipios_incluidos.parquet")]).fetchall()
    columnas = [d[0] for d in c.description]
    filas = [dict(zip(columnas, f)) for f in datos]
    assert len(filas) == len({f["codigo_municipio"] for f in filas}) == 433
    assert "46201" not in {f["codigo_municipio"] for f in filas}
    assert Counter(f["estado_renta_modelado"] for f in filas) == {"publicada_2023": 426, "estimada_historico_ipc": 6, "estimada_media_comparables": 1}
    for f in filas:
        assert f["parque_total"] > 0 and 0 <= f["vehiculos_distintivo_0"] <= f["parque_total"]
        assert math.isclose(f["proporcion_distintivo_0"], f["vehiculos_distintivo_0"] / f["parque_total"], abs_tol=1e-12)
    return filas


def preparar(entrenamiento, validacion):
    ids_train = {f["codigo_municipio"] for f in entrenamiento}
    ids_val = {f["codigo_municipio"] for f in validacion}
    assert len(ids_train) == len(entrenamiento) and len(ids_val) == len(validacion)
    assert ids_train.isdisjoint(ids_val)
    assert {f["bloque_espacial"] for f in entrenamiento}.isdisjoint({f["bloque_espacial"] for f in validacion})
    donantes = [f for f in entrenamiento if f["codigo_municipio"] in DONANTES]
    hay_sempere = "46226" in ids_train | ids_val
    if hay_sempere:
        if not donantes:
            raise ValueError("Sempere requiere un donante de entrenamiento; revisar la partición.")
        media = (sum(Decimal(str(f[VARIABLES[2]])) for f in donantes) / len(donantes)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        media = None
    preparados = []
    for rol, origen in (("entrenamiento", entrenamiento), ("validacion", validacion)):
        filas = []
        for original in origen:
            f = original.copy()
            f["rol"] = rol
            if f["codigo_municipio"] == "46226":
                f[VARIABLES[2]] = media
            f["n_donantes_particion"] = len(donantes) if f["codigo_municipio"] == "46226" else None
            f["donantes_particion"] = ",".join(sorted(d["codigo_municipio"] for d in donantes)) if f["codigo_municipio"] == "46226" else ""
            assert all(f[v] is not None and math.isfinite(float(f[v])) for v in VARIABLES)
            assert f[VARIABLES[0]] >= 0 and 0 <= f[VARIABLES[1]] <= 1 and f[VARIABLES[2]] > 0
            filas.append(f)
        preparados.append(filas)
    matrices = [np.array([[float(f[v]) for v in VARIABLES] for f in filas], dtype=float).reshape(-1, 3) for filas in preparados]
    for x in matrices:
        x[:, 0] = np.log1p(x[:, 0])
    scaler = StandardScaler().fit(matrices[0])
    for filas, x in zip(preparados, matrices):
        if not filas:
            continue
        escalado = scaler.transform(x)
        assert np.isfinite(escalado).all()
        for f, z in zip(filas, escalado):
            f.update(dict(zip(Z, z.tolist())))
    assert np.allclose(np.mean([[f[z] for z in Z] for f in preparados[0]], axis=0), 0, atol=1e-12)
    parametros = {"n_entrenamiento": len(entrenamiento), "n_validacion": len(validacion),
        "donantes_sempere": [{"codigo": f["codigo_municipio"], "renta": str(f[VARIABLES[2]])} for f in donantes] if hay_sempere else [],
        "renta_sempere": str(media) if media is not None else None,
        "media_transformada": scaler.mean_.tolist(), "varianza_poblacional": scaler.var_.tolist(), "escala": scaler.scale_.tolist(),
        "regla": "log1p solo volumen; z=(x-media)/desviacion ddof=0 solo entrenamiento; variable constante usa escala 1"}
    return preparados[0], preparados[1], parametros


def plan_estabilidad(entrenamiento, semilla):
    bloques = sorted({f["bloque_espacial"] for f in entrenamiento})
    n_omitidos = max(1, math.ceil(len(bloques) * 0.10))
    rng = random.Random(semilla)
    planes = []
    for _ in range(1000):
        omitidos = sorted(rng.sample(bloques, n_omitidos))
        if any(p["bloques_omitidos"] == omitidos for p in planes):
            continue
        # Conservar algún donante permite recalcular Sempere sin usar validación.
        if not any(f["codigo_municipio"] in DONANTES and f["bloque_espacial"] not in omitidos for f in entrenamiento):
            continue
        planes.append({"repeticion": len(planes) + 1, "bloques_omitidos": omitidos})
        if len(planes) == 10:
            return planes
    raise ValueError("No se han podido obtener diez perturbaciones distintas con donantes.")


def geometria(x, etiquetas):
    x = np.asarray(x, dtype=float)
    etiquetas = np.asarray(etiquetas)
    assert x.shape[0] == len(etiquetas) and np.isfinite(x).all()
    n, k = len(etiquetas), len(set(etiquetas.tolist()))
    if not 2 <= k < n:
        return {"n": n, "k": k, "silhouette": None, "motivo": "Se requieren entre 2 y n-1 grupos observados."}
    valores = silhouette_samples(x, etiquetas, metric="euclidean")
    return {"n": n, "k": k, "silhouette": float(valores.mean()), "fraccion_negativa": float((valores < 0).mean()),
        "por_grupo": {str(g): {"n": int((etiquetas == g).sum()), "silhouette": float(valores[etiquetas == g].mean())} for g in sorted(set(etiquetas.tolist()))},
        "por_municipio_en_orden": valores.tolist()}


def estabilidad_por_codigo(primera, segunda):
    assert set(primera) == set(segunda), "ARI requiere los mismos municipios."
    codigos = sorted(primera)
    assert len(codigos) > 1
    return float(adjusted_rand_score([primera[c] for c in codigos], [segunda[c] for c in codigos]))


def main():
    desarrollo = cargar_desarrollo()
    planes, parametros, todas = {}, {}, []
    for i in range(1, 5):
        train = [f for f in desarrollo if f["particion_interna"] != i]
        val = [f for f in desarrollo if f["particion_interna"] == i]
        a, b, parametros[f"interna_{i}"] = preparar(train, val)
        planes[f"interna_{i}"] = plan_estabilidad(train, SEMILLA + i)
        for plan in planes[f"interna_{i}"]:
            subtrain = [f for f in train if f["bloque_espacial"] not in plan["bloques_omitidos"]]
            preparar(subtrain, val)  # Comprueba imputación y escalas; no asigna clusters.
        # Comprueba también que la sensibilidad usa solo renta publicada.
        preparar([f for f in train if f["estado_renta_modelado"] == "publicada_2023"], [f for f in val if f["estado_renta_modelado"] == "publicada_2023"])
        todas.extend(dict(f, ajuste=f"interna_{i}") for f in a + b)
    a, _, parametros["desarrollo_completo"] = preparar(desarrollo, [])
    todas.extend(dict(f, ajuste="desarrollo_completo") for f in a)
    assert len(todas) == 2165
    ejecucion = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    carpeta = RAIZ / "resultados/modelado/preparacion" / ejecucion
    carpeta.mkdir(parents=True, exist_ok=False)
    archivo = carpeta / "entradas_desarrollo.csv"
    with archivo.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=list(todas[0]))
        escritor.writeheader()
        escritor.writerows(todas)
    c = duckdb.connect()
    c.read_csv(str(archivo), dtype={"codigo_municipio": "VARCHAR", "version_gold": "VARCHAR", "donantes_particion": "VARCHAR"}).write_parquet(str(carpeta / "entradas_desarrollo.parquet"))
    protocolo = {
        "estado": "Preparacion verificada. Sin baseline ajustado, clusters ni metricas reales.",
        "entradas": VARIABLES, "columnas_distancias": Z, "parametros_por_ajuste": parametros,
        "baseline": "Medianas de las tres entradas originales en entrenamiento; <= mediana frente a > mediana; hasta ocho combinaciones; no usar z para los umbrales.",
        "geometria": "Silhouette euclidea sobre validacion asignada sin reajuste, misma representacion para baseline/ML. Media, por grupo, fraccion negativa y valores municipales. Degenerado: no calculable, nunca cero inventado.",
        "cobertura": "Numero y porcentaje asignados, grupos efectivos y n/% por grupo. No omitir casos no asignados sin informar su cobertura; comparar metodos sobre municipios comunes.",
        "estabilidad": "Diez repeticiones por validacion omitiendo ceil(10%) de bloques de entrenamiento sin reemplazo; conservar al menos un donante. Reajustar imputacion, escalas y metodo. ARI sobre la misma validacion por codigo respecto al ajuste principal; no comparar validaciones disjuntas. En ML registrar ademas variacion de semillas.",
        "planes_estabilidad": planes,
        "sensibilidad_renta": "Por validacion, repetir con entrenamiento/validacion de renta publicada; comparar ARI con resultado principal filtrado a esos mismos codigos. Informar tambien perfil de los siete estimados, sin usar prueba final.",
        "interpretacion": "n y porcentaje, mediana y cuartiles en unidades originales por grupo; ejemplos identificados, grupos pequenos/dominantes sin imponer equilibrio.",
        "agregacion": "Mostrar cuatro resultados, media no ponderada y rango. No tratarlos como cuatro observaciones independientes ni dar intervalos de confianza injustificados.",
        "seleccion": "Mejora consistente frente al baseline con estabilidad y perfiles explicables; a resultados parecidos preferir sencillez/menos grupos. Sin umbral universal ni puntuacion ponderada. Test solo despues de fijar solucion.",
        "reserva": "No se han cargado entradas de los 108 de prueba en las matrices ni se preparan asignaciones de prueba. Solo metadatos previamente fijados y huellas de fuentes completas.",
    }
    (carpeta / "protocolo.json").write_text(json.dumps(protocolo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifiesto = {"ejecucion": ejecucion, "consulta": CONSULTA, "n_desarrollo": len(desarrollo), "n_filas_preparadas": len(todas),
        "versiones": {"duckdb": duckdb.__version__, "numpy": np.__version__, "scikit_learn": sklearn.__version__},
        "fuentes": [{"ruta": p, "sha256": huella(RAIZ / p)} for p in (GOLD, PARTICIONES + "/particiones_municipales.parquet", PARTICIONES + "/manifiesto.json", RENTAS + "/rentas_municipios_incluidos.parquet")],
        "productor": {"ruta": Path(__file__).resolve().relative_to(RAIZ).as_posix(), "sha256": huella(Path(__file__))},
        "salidas": [{"ruta": p.relative_to(RAIZ).as_posix(), "sha256": huella(p)} for p in sorted(carpeta.iterdir())],
        "verificacion": "433 codigos sin test; 4 pares entrenamiento/validacion sin cruce; imputaciones solo entrenamiento; matrices finitas; medias z de entrenamiento cero; 40 perturbaciones y cuatro sensibilidades preparables sin ajustar grupos."}
    (carpeta / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"salida": carpeta.relative_to(RAIZ).as_posix(), "parametros": parametros}, ensure_ascii=True))


if __name__ == "__main__":
    main()
