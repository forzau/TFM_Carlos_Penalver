"""Recalcula métricas por distancias/contingencias, sin los helpers del productor."""

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import duckdb
import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from src.modelado.preparar_experimento_segmentacion import RAIZ, Z, VARIABLES, DONANTES, cargar_desarrollo, huella
from src.rutas import codigo_versionado


def leer_csv(ruta):
    with ruta.open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def silhouette_directa(x, y):
    x, y = np.asarray(x, float), np.asarray(y)
    distancias = np.sqrt(np.square(x[:, None, :] - x[None, :, :]).sum(axis=2))
    valores = []
    for i, g in enumerate(y):
        mismos = y == g
        if mismos.sum() == 1:
            valores.append(0.)
            continue
        a = distancias[i, mismos].sum() / (mismos.sum() - 1)
        b = min(distancias[i, y == otro].mean() for otro in set(y) if otro != g)
        valores.append((b - a) / max(a, b) if max(a, b) else 0.)
    return np.array(valores)


def ari_contingencia(a, b):
    assert len(a) == len(b) and len(a) > 1
    total = math.comb(len(a), 2)
    pares = sum(math.comb(n, 2) for n in Counter(zip(a, b)).values())
    suma_a = sum(math.comb(n, 2) for n in Counter(a).values())
    suma_b = sum(math.comb(n, 2) for n in Counter(b).values())
    esperado = suma_a * suma_b / total
    denominador = (suma_a + suma_b) / 2 - esperado
    return (pares - esperado) / denominador if denominador else 1.


def main():
    carpeta = (RAIZ / sys.argv[1]).resolve()
    assert carpeta.is_relative_to(RAIZ / "resultados/modelado/comparacion_ml")
    manifiesto = json.loads((carpeta / "manifiesto.json").read_text(encoding="utf-8"))
    for f in manifiesto["fuentes"] + manifiesto["salidas"] + [manifiesto["productor"]]:
        assert huella(codigo_versionado(RAIZ, RAIZ / f["ruta"], f["sha256"])) == f["sha256"], f["ruta"]
    principales = leer_csv(carpeta / "asignaciones_validacion.csv")
    variantes = leer_csv(carpeta / "variaciones_asignaciones.csv")
    descriptivos = leer_csv(carpeta / "asignaciones_desarrollo.csv")
    resumenes = leer_csv(carpeta / "resumen_comparacion.csv")
    metricas = leer_csv(carpeta / "metricas_validacion.csv")
    grupos = defaultdict(list)
    for f in principales:
        grupos[(f["metodo"], int(f["k_configurado"]), int(f["interna"]))].append(f)
    grupos_descriptivos = defaultdict(list)
    for f in descriptivos:
        grupos_descriptivos[(f["metodo"], int(f["k_configurado"]))].append(f)
    desarrollo = cargar_desarrollo()
    ids_desarrollo = {f["codigo_municipio"] for f in desarrollo}
    c = duckdb.connect(config={"threads": 2})
    tabla_particiones = "resultados/modelado/particiones/20261106T110046844319Z/particiones_municipales.parquet"
    ids_test = {f[0] for f in c.execute("SELECT codigo_municipio FROM read_parquet(?) WHERE conjunto='prueba_final'", [str(RAIZ / tabla_particiones)]).fetchall()}
    # Solo códigos del reparto; ninguna variable ni asignación del test.
    assert len(ids_test) == 108 and ids_desarrollo.isdisjoint(ids_test)
    assert len(principales) == len(descriptivos) == 11691
    assert len(variantes) == 175176 and len(grupos) == len(metricas) == 108
    assert all(f["codigo_municipio"] in ids_desarrollo for f in principales + variantes + descriptivos)
    error_s = 0.
    todas_s, todos_ari, diagnosticos = {}, {}, []
    for clave, filas in grupos.items():
        metodo, k, interna = clave
        esperado = {f["codigo_municipio"] for f in desarrollo if f["particion_interna"] == interna}
        assert {f["codigo_municipio"] for f in filas} == esperado
        assert len(filas) == len(esperado)
        x = np.array([[float(f[z]) for z in Z] for f in filas])
        y = np.array([int(f["grupo"]) for f in filas])
        s = silhouette_directa(x, y)
        error_s = max(error_s, float(np.abs(s - [float(f["silhouette"]) for f in filas]).max()))
        assert np.allclose(s, [float(f["silhouette"]) for f in filas], atol=1e-12, rtol=0)
        todas_s[clave] = float(s.mean())
        modelo = joblib.load(carpeta / "modelos" / f"{metodo}_k{k}_interna{interna}.joblib")
        assert np.array_equal(modelo.predict(x), y)
        if metodo == "kmeans":
            assert np.array_equal(((x[:, None] - modelo.cluster_centers_[None]) ** 2).sum(axis=2).argmin(axis=1), y)
        if metodo == "gmm":
            logpesos = []
            for media, cov, peso in zip(modelo.means_, modelo.covariances_, modelo.weights_):
                d = x - media
                logpesos.append(np.log(peso) - .5 * (np.linalg.slogdet(cov)[1] + np.einsum("ij,jk,ik->i", d, np.linalg.inv(cov), d)))
            assert np.array_equal(np.array(logpesos).argmax(axis=0), y)
    agrupadas = defaultdict(list)
    for f in variantes:
        agrupadas[(f["metodo"], int(f["k_configurado"]), int(f["interna"]), f["tipo"], int(f["repeticion"]))].append(f)
    assert len(agrupadas) == 1620
    for clave, filas in agrupadas.items():
        principal = {f["codigo_municipio"]: f["grupo"] for f in grupos[clave[:3]]}
        esperado = set(principal)
        if clave[3] == "renta_publicada":
            esperado &= {f["codigo_municipio"] for f in desarrollo if f["estado_renta_modelado"] == "publicada_2023"}
        assert {f["codigo_municipio"] for f in filas} == esperado
        assert len(filas) == len(esperado)
        assert all(principal[f["codigo_municipio"]] == f["grupo_principal"] for f in filas)
        todos_ari[clave] = ari_contingencia([f["grupo_principal"] for f in filas], [f["grupo_variante"] for f in filas])
    error_ari = 0.
    for resumen in resumenes:
        metodo, k = resumen["metodo"], int(resumen["k_configurado"])
        assert math.isclose(float(resumen["silhouette_media"]), np.mean([todas_s[(metodo, k, i)] for i in range(1, 5)]), abs_tol=1e-12)
        doc = json.loads((carpeta / f"{metodo}_k{k}.json").read_text(encoding="utf-8"))
        for r in doc["validaciones"]:
            info = r["ajuste"]
            diagnosticos.append(info)
            assert math.isclose(r["geometria"]["silhouette"], todas_s[(metodo, k, r["interna"])], abs_tol=1e-12)
            for v in r["variaciones"]:
                diagnosticos.append(v["ajuste"])
                oracle = todos_ari[(metodo, k, r["interna"], v["tipo"], v["repeticion"])]
                error_ari = max(error_ari, abs(oracle - v["ari"]))
                assert math.isclose(oracle, v["ari"], abs_tol=1e-12)
        diagnosticos.append(doc["descriptivo"]["ajuste"])
        assert sum(p["n"] for p in doc["descriptivo"]["perfiles"]) == 433
        filas_desc = grupos_descriptivos[(metodo, k)]
        assert len(filas_desc) == 433 and {f["codigo_municipio"] for f in filas_desc} == ids_desarrollo
        for perfil in doc["descriptivo"]["perfiles"]:
            filas_grupo = [f for f in filas_desc if int(f["grupo"]) == perfil["perfil"]]
            assert len(filas_grupo) == perfil["n"]
            for v in VARIABLES:
                cuantiles = np.quantile([float(f[v]) for f in filas_grupo], [0, .25, .5, .75, 1])
                assert np.allclose(cuantiles, [perfil["variables"][v][q] for q in ("min", "q25", "mediana", "q75", "max")], atol=1e-12)
        for tipo in ("bloques", "semilla", "renta_publicada"):
            aris = [v for clave, v in todos_ari.items() if clave[:2] == (metodo, k) and clave[3] == tipo]
            assert math.isclose(float(resumen[f"ari_{tipo}_media"]), np.mean(aris), abs_tol=1e-12)
    assert len(diagnosticos) == 1755
    # Revisión independiente de escalas y donantes de todas las preparaciones.
    protocolo_original = json.loads((RAIZ / "resultados/modelado/preparacion/20261106T112331494635Z/protocolo.json").read_text(encoding="utf-8"))
    params = json.loads((carpeta / "preparaciones.json").read_text(encoding="utf-8"))
    for nombre, p in params.items():
        train = desarrollo
        if nombre != "desarrollo_completo":
            i = int(nombre.split("_")[1])
            train = [f for f in desarrollo if f["particion_interna"] != i]
            val = [f for f in desarrollo if f["particion_interna"] == i]
            if "perturbacion" in nombre:
                rep = int(nombre.split("_")[-1])
                plan = protocolo_original["planes_estabilidad"][f"interna_{i}"][rep - 1]
                train = [f for f in train if f["bloque_espacial"] not in plan["bloques_omitidos"]]
            if "solo_publicadas" in nombre:
                train = [f for f in train if f["estado_renta_modelado"] == "publicada_2023"]
                val = [f for f in val if f["estado_renta_modelado"] == "publicada_2023"]
            assert {f["bloque_espacial"] for f in train}.isdisjoint(f["bloque_espacial"] for f in val)
            assert len(val) == p["n_validacion"]
        assert len(train) == p["n_entrenamiento"]
        donantes = [f for f in train if f["codigo_municipio"] in DONANTES]
        media = ((sum(Decimal(str(f[VARIABLES[2]])) for f in donantes) / len(donantes)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
                 if donantes else None)
        assert media is not None or all(f["codigo_municipio"] != "46226" for f in train)
        x = np.array([[float(media) if v == VARIABLES[2] and f["codigo_municipio"] == "46226" else float(f[v]) for v in VARIABLES] for f in train])
        x[:, 0] = np.log1p(x[:, 0])
        assert np.allclose(x.mean(axis=0), p["media_transformada"], atol=1e-12)
        assert np.allclose(x.var(axis=0), p["varianza_poblacional"], atol=1e-12)
        if p["renta_sempere"] is not None:
            assert Decimal(p["renta_sempere"]) == media
    salida = {"estado": "correcto", "n_ajustes": len(diagnosticos), "n_validaciones": len(grupos),
              "n_ari_recalculados": len(todos_ari), "n_preparaciones_comprobadas": len(params),
              "error_max_silhouette_directa": error_s, "error_max_ari_contingencia": error_ari,
              "n_test_evaluados": 0, "n_codigos_test_solo_metadatos": len(ids_test),
              "gmm_no_convergentes": sum(d["convergencia_gmm"] is False for d in diagnosticos),
              "avisos": [d for d in diagnosticos if d["avisos"]],
              "limite_iteraciones_alcanzado": sum(d["n_iter"] is not None and d["n_iter"] >= 500 for d in diagnosticos),
              "manifiesto_sha256": huella(carpeta / "manifiesto.json"),
              "verificador_sha256": huella(Path(__file__)),
              "alcance": "Huellas, códigos y grupos completos; 108 silhouettes por distancias,1620 ARI por contingencias; predicción persistida principal; asignación GMM/KMeans independiente; escalas y donantes49; tamaños y cuantiles de27 descriptivos contra CSV. No se repiten los ajustes."}
    (carpeta / "verificacion_independiente.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=True))


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
