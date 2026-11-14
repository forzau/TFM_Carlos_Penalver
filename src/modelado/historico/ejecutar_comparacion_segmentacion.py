"""Compara tres métodos inductivos en desarrollo; no evalúa la prueba final."""

import json
import platform
import sys
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import joblib
import numpy as np
import scipy
import sklearn
from sklearn.cluster import BisectingKMeans, KMeans
from sklearn.mixture import GaussianMixture
from threadpoolctl import threadpool_limits

from src.modelado.historico.preparar_experimento_segmentacion import (
    RAIZ, VARIABLES, Z, cargar_desarrollo, estabilidad_por_codigo,
    geometria, huella, preparar,
)
from src.modelado.historico.ejecutar_baseline_segmentacion import escribir_csv, perfiles, resumen_numerico


PREPARACION = "resultados/modelado/preparacion/20261106T112331494635Z"
BASELINE = "resultados/modelado/baseline/20261106T114636184831Z"
METODOS = ("kmeans", "gmm", "bisecting_kmeans")
SEMILLA = 20261107
K = tuple(range(2, 11))
DESPLAZAMIENTOS_SEMILLAS = (100, 200, 300, 400)
PARAMETROS = {
    "kmeans": dict(init="k-means++", n_init=20, max_iter=500, tol=1e-4, algorithm="lloyd"),
    "gmm": dict(covariance_type="full", init_params="kmeans", n_init=10,
                max_iter=500, tol=1e-3, reg_covar=1e-6),
    "bisecting_kmeans": dict(init="k-means++", n_init=10, max_iter=500,
                            tol=1e-4, algorithm="lloyd", bisecting_strategy="biggest_inertia"),
}


def crear_modelo(metodo, k, semilla):
    clases = {"kmeans": KMeans, "gmm": GaussianMixture, "bisecting_kmeans": BisectingKMeans}
    if metodo not in clases or k not in K:
        raise ValueError("Método o número de grupos fuera del protocolo.")
    nombre_k = "n_components" if metodo == "gmm" else "n_clusters"
    return clases[metodo](**{nombre_k: k}, random_state=semilla, **PARAMETROS[metodo])


def matriz(filas):
    x = np.asarray([[f[z] for z in Z] for f in filas], dtype=float)
    assert x.ndim == 2 and x.shape[1] == 3 and len(x) and np.isfinite(x).all()
    return x


def predecir(modelo, filas):
    codigos = [f["codigo_municipio"] for f in filas]
    assert len(codigos) == len(set(codigos))
    etiquetas = modelo.predict(matriz(filas))
    assert len(etiquetas) == len(filas) and (etiquetas >= 0).all()
    return dict(zip(codigos, etiquetas.tolist()))


def ajustar(metodo, k, semilla, train, val):
    assert {f["codigo_municipio"] for f in train}.isdisjoint(f["codigo_municipio"] for f in val)
    modelo = crear_modelo(metodo, k, semilla)
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        modelo.fit(matriz(train))
    etiquetas = predecir(modelo, val) if val else {}
    info = {"semilla": semilla, "parametros": modelo.get_params(),
            "avisos": [str(a.message) for a in avisos],
            "n_iter": int(modelo.n_iter_) if hasattr(modelo, "n_iter_") else None,
            "convergencia_gmm": bool(modelo.converged_) if metodo == "gmm" else None,
            "k_entrenamiento": len(set(modelo.predict(matriz(train)).tolist()))}
    if metodo == "gmm":
        info["limite_inferior_log_verosimilitud"] = float(modelo.lower_bound_)
    else:
        info["inercia_entrenamiento"] = float(modelo.inertia_)
    return modelo, etiquetas, info


def verificar_manifiesto(ruta):
    doc = json.loads(ruta.read_text(encoding="utf-8"))
    for item in doc["fuentes"] + doc["salidas"] + [doc["productor"]]:
        assert huella(RAIZ / item["ruta"]) == item["sha256"], item["ruta"]
    return doc


def guardar_json(ruta, valor):
    ruta.write_text(json.dumps(valor, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def cargar_preparaciones():
    verificar_manifiesto(RAIZ / PREPARACION / "manifiesto.json")
    verificar_manifiesto(RAIZ / BASELINE / "manifiesto.json")
    protocolo = json.loads((RAIZ / PREPARACION / "protocolo.json").read_text(encoding="utf-8"))
    desarrollo = cargar_desarrollo()
    c = duckdb.connect(config={"threads": 2, "memory_limit": "1GB"})
    c.read_parquet(str(RAIZ / PREPARACION / "entradas_desarrollo.parquet")).create_view("entradas")
    lotes, parametros = {}, {}
    for i in range(1, 5):
        nombre = f"interna_{i}"
        train = [f for f in desarrollo if f["particion_interna"] != i]
        val = [f for f in desarrollo if f["particion_interna"] == i]
        a, b, params = preparar(train, val)
        # Concordancia con la preparación usada por el baseline, sin regenerarla.
        datos = c.execute("SELECT codigo_municipio, rol, " + ",".join(Z) +
                          " FROM entradas WHERE ajuste=? ORDER BY codigo_municipio", [nombre]).fetchall()
        esperado = {f["codigo_municipio"]: f for f in a + b}
        assert len(datos) == len(esperado) == 433
        for codigo, rol, *z in datos:
            assert esperado[codigo]["rol"] == rol
            assert np.allclose(z, [esperado[codigo][v] for v in Z], rtol=0, atol=1e-12)
        perturbaciones = []
        for plan in protocolo["planes_estabilidad"][nombre]:
            sub = [f for f in train if f["bloque_espacial"] not in plan["bloques_omitidos"]]
            ap, bp, pp = preparar(sub, val)
            perturbaciones.append((plan, ap, bp))
            parametros[f"{nombre}_perturbacion_{plan['repeticion']}"] = pp
        ap, bp, pp = preparar([f for f in train if f["estado_renta_modelado"] == "publicada_2023"],
                             [f for f in val if f["estado_renta_modelado"] == "publicada_2023"])
        parametros[nombre] = params
        parametros[nombre + "_solo_publicadas"] = pp
        lotes[i] = (a, b, perturbaciones, (ap, bp))
    completo, _, pp = preparar(desarrollo, [])
    parametros["desarrollo_completo"] = pp
    c.close()
    return desarrollo, lotes, completo, parametros


def main():
    desarrollo, lotes, completo, parametros = cargar_preparaciones()
    ejecucion = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    carpeta = RAIZ / "resultados/modelado/comparacion_ml" / ejecucion
    carpeta.mkdir(parents=True, exist_ok=False)
    (carpeta / "modelos").mkdir()
    protocolo = {
        "ejecucion": ejecucion, "fijado_antes_de_ajustar": True,
        "metodos": list(METODOS), "k": list(K), "comparacion_fija": 8,
        "parametros": PARAMETROS, "semilla_base": SEMILLA,
        "regla_semilla": "Principal SEMILLA+interna; perturbaciones y sensibilidad conservan esa semilla; descriptivo SEMILLA.",
        "desplazamientos_semillas_adicionales": list(DESPLAZAMIENTOS_SEMILLAS),
        "inicializaciones": "Repetir procedimiento completo multiinicio con cuatro semillas adicionales. No seleccionar semilla por validación. n_init de Bisecting es por bisección; los presupuestos no son equivalentes.",
        "gmm": "Covarianza completa fijada a priori; grupos por componente de mayor probabilidad. Probabilidades del modelo, sin calibración externa.",
        "seleccion": "No automatizar ganador por silhouette. Revisar geometría, estabilidad, sensibilidad, tamaños y perfiles. Comparación k8 y rango por separado.",
        "evaluacion": "Cuatro validaciones espaciales fijas, preparación exclusiva de entrenamiento, 10 perturbaciones por interna del protocolo original, sensibilidad solo rentas publicadas.",
        "reserva": "No se preparan, asignan ni evalúan los 108 municipios de prueba final.",
        "n_ajustes_previstos": 1755, "hilos_numericos": 2,
        "referencias": {
            "kmeans": "https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html",
            "gmm": "https://scikit-learn.org/stable/modules/generated/sklearn.mixture.GaussianMixture.html",
            "bisecting": "https://scikit-learn.org/stable/modules/generated/sklearn.cluster.BisectingKMeans.html"},
    }
    guardar_json(carpeta / "protocolo_ml.json", protocolo)
    guardar_json(carpeta / "preparaciones.json", parametros)
    print(json.dumps({"salida": carpeta.relative_to(RAIZ).as_posix(), "estado": "protocolo fijado"}), flush=True)
    resultados, metricas, asignaciones, variaciones, descripciones = [], [], [], [], []
    for metodo in METODOS:
        for k in K:
            internas = []
            for i, (train, val, perturbaciones, solo_publicadas) in lotes.items():
                semilla = SEMILLA + i
                modelo, etiquetas, info = ajustar(metodo, k, semilla, train, val)
                joblib.dump(modelo, carpeta / "modelos" / f"{metodo}_k{k}_interna{i}.joblib")
                geo = geometria(matriz(val), [etiquetas[f["codigo_municipio"]] for f in val])
                assert geo["silhouette"] is not None
                max_probs = modelo.predict_proba(matriz(val)).max(axis=1).tolist() if metodo == "gmm" else [None] * len(val)
                for f, s, p in zip(val, geo["por_municipio_en_orden"], max_probs):
                    asignaciones.append(dict(f, metodo=metodo, k_configurado=k, interna=i,
                                             grupo=etiquetas[f["codigo_municipio"]], silhouette=s,
                                             probabilidad_maxima_gmm=p))
                variaciones_fold = []
                for tipo, rep, a, b, otra_semilla in (
                    [("bloques", p["repeticion"], a, b, semilla) for p, a, b in perturbaciones] +
                    [("semilla", j, train, val, semilla + d) for j, d in enumerate(DESPLAZAMIENTOS_SEMILLAS, 1)] +
                    [("renta_publicada", 1, *solo_publicadas, semilla)]
                ):
                    _, otras, infov = ajustar(metodo, k, otra_semilla, a, b)
                    principal = {codigo: etiquetas[codigo] for codigo in otras}
                    ari = estabilidad_por_codigo(principal, otras)
                    variaciones_fold.append({"tipo": tipo, "repeticion": rep, "ari": ari, "ajuste": infov})
                    variaciones.extend({"metodo": metodo, "k_configurado": k, "interna": i,
                                        "tipo": tipo, "repeticion": rep, "semilla": otra_semilla,
                                        "codigo_municipio": codigo, "grupo_principal": principal[codigo],
                                        "grupo_variante": otras[codigo]} for codigo in sorted(otras))
                r = {"metodo": metodo, "k_configurado": k, "interna": i, "ajuste": info,
                     "n_train": len(train), "n_val": len(val), "cobertura": len(etiquetas) / len(val),
                     "geometria": geo, "perfiles_validacion": perfiles(val, etiquetas),
                     "variaciones": variaciones_fold,
                     "tamanos_entrenamiento": dict(Counter(modelo.predict(matriz(train)).tolist()))}
                internas.append(r)
                metricas.append({"metodo": metodo, "k_configurado": k, "interna": i,
                                 "n_train": len(train), "n_val": len(val), "cobertura": r["cobertura"],
                                 "k_observado": geo["k"], "silhouette": geo["silhouette"],
                                 "fraccion_negativa": geo["fraccion_negativa"],
                                 **{f"ari_{t}_medio": float(np.mean([v["ari"] for v in variaciones_fold if v["tipo"] == t]))
                                    for t in ("bloques", "semilla", "renta_publicada")}})
            modelo, etiquetas, info = ajustar(metodo, k, SEMILLA, completo, [])
            etiquetas = predecir(modelo, completo)
            joblib.dump(modelo, carpeta / "modelos" / f"{metodo}_k{k}_desarrollo.joblib")
            desc = perfiles(completo, etiquetas)
            descripciones.extend(dict(f, metodo=metodo, k_configurado=k, grupo=etiquetas[f["codigo_municipio"]]) for f in completo)
            resumen = {"metodo": metodo, "k_configurado": k,
                       "silhouette": resumen_numerico([r["geometria"]["silhouette"] for r in internas]),
                       "fraccion_negativa_media": float(np.mean([r["geometria"]["fraccion_negativa"] for r in internas])),
                       "grupos_observados": [r["geometria"]["k"] for r in internas],
                       "cobertura": min(r["cobertura"] for r in internas),
                       **{f"ari_{t}": resumen_numerico([v["ari"] for r in internas for v in r["variaciones"] if v["tipo"] == t])
                          for t in ("bloques", "semilla", "renta_publicada")},
                       "tamano_min_desarrollo": min(p["n"] for p in desc),
                       "tamano_max_desarrollo": max(p["n"] for p in desc)}
            resultados.append({"resumen": resumen, "validaciones": internas,
                               "descriptivo": {"ajuste": info, "perfiles": desc, "n": len(completo),
                                               "cautela": "Descriptivo de entrenamiento; no rendimiento fuera de ajuste ni clasificación de 541."}})
            guardar_json(carpeta / f"{metodo}_k{k}.json", resultados[-1])
            print(json.dumps(resumen, ensure_ascii=True), flush=True)
    ids = {f["codigo_municipio"] for f in desarrollo}
    assert len(ids) == 433
    assert len(asignaciones) == len(descripciones) == 433 * 27
    assert len(variaciones) == 433 * 27 * 14 + 426 * 27
    for metodo in METODOS:
        for k in K:
            seleccion = [f for f in asignaciones if f["metodo"] == metodo and f["k_configurado"] == k]
            assert len(seleccion) == len({f["codigo_municipio"] for f in seleccion}) == 433
            assert {f["codigo_municipio"] for f in seleccion} == ids
    escribir_csv(carpeta / "metricas_validacion.csv", metricas)
    escribir_csv(carpeta / "asignaciones_validacion.csv", asignaciones)
    escribir_csv(carpeta / "variaciones_asignaciones.csv", variaciones)
    escribir_csv(carpeta / "asignaciones_desarrollo.csv", descripciones)
    resumenes = [{"metodo": r["resumen"]["metodo"], "k_configurado": r["resumen"]["k_configurado"],
                 "silhouette_media": r["resumen"]["silhouette"]["media"],
                 "silhouette_min": r["resumen"]["silhouette"]["min"],
                 "silhouette_max": r["resumen"]["silhouette"]["max"],
                 **{f"ari_{t}_{s}": r["resumen"][f"ari_{t}"][s] for t in ("bloques", "semilla", "renta_publicada") for s in ("media", "min")},
                 "tamano_min_desarrollo": r["resumen"]["tamano_min_desarrollo"],
                 "tamano_max_desarrollo": r["resumen"]["tamano_max_desarrollo"],
                 "cobertura": r["resumen"]["cobertura"]} for r in resultados]
    escribir_csv(carpeta / "resumen_comparacion.csv", resumenes)
    escribir_csv(carpeta / "comparacion_k8.csv", [r for r in resumenes if r["k_configurado"] == 8])
    baseline = json.loads((RAIZ / BASELINE / "resultados.json").read_text(encoding="utf-8"))
    guardar_json(carpeta / "resultados.json", {"ejecucion": ejecucion, "n_desarrollo": 433,
                 "n_prueba_evaluados": 0, "n_ajustes": 1755, "resumenes": [r["resumen"] for r in resultados],
                 "baseline": baseline["resumen"], "estado": "Comparación de desarrollo completa; sin selección definitiva o prueba final."})
    versiones = {"python": sys.version, "plataforma": platform.platform(), "duckdb": duckdb.__version__,
                 "numpy": np.__version__, "scikit_learn": sklearn.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__}
    fuentes = [RAIZ / PREPARACION / "manifiesto.json", RAIZ / PREPARACION / "protocolo.json",
               RAIZ / PREPARACION / "entradas_desarrollo.parquet", RAIZ / BASELINE / "manifiesto.json",
               RAIZ / BASELINE / "resultados.json", Path(__file__).with_name("preparar_experimento_segmentacion.py"),
               Path(__file__).with_name("ejecutar_baseline_segmentacion.py")]
    guardar_json(carpeta / "manifiesto.json", {"ejecucion": ejecucion, "versiones": versiones,
        "fuentes": [{"ruta": p.relative_to(RAIZ).as_posix(), "sha256": huella(p)} for p in fuentes],
        "productor": {"ruta": Path(__file__).relative_to(RAIZ).as_posix(), "sha256": huella(Path(__file__))},
        "salidas": [{"ruta": p.relative_to(RAIZ).as_posix(), "sha256": huella(p)} for p in sorted(carpeta.rglob("*")) if p.is_file()],
        "controles": "27 configuraciones; 433 validaciones únicas cada una; 108 ajustes principales,1080 perturbaciones,432 semillas,108 sensibilidades,27 descriptivos; sin prueba final."})
    print(json.dumps({"terminado": carpeta.relative_to(RAIZ).as_posix(), "ajustes": 1755}), flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
