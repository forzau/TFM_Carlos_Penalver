"""Ejecuta las reglas por medianas y su protocolo fijo, exclusivamente en desarrollo."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np

from src.modelado.historico.preparar_experimento_segmentacion import (
    RAIZ, VARIABLES, Z, cargar_desarrollo, estabilidad_por_codigo,
    geometria, huella, preparar,
)


PREPARACION = "resultados/modelado/preparacion/20261106T112331494635Z"


def ajustar_medianas(entrenamiento):
    x = np.asarray([[float(f[v]) for v in VARIABLES] for f in entrenamiento])
    assert len(x) > 0 and np.isfinite(x).all()
    return dict(zip(VARIABLES, np.median(x, axis=0).tolist()))


def asignar(filas, medianas):
    assert len({f["codigo_municipio"] for f in filas}) == len(filas)
    return {f["codigo_municipio"]: "-".join("S" if float(f[v]) > medianas[v] else "I" for v in VARIABLES) for f in filas}


def evaluar(filas, etiquetas):
    return geometria([[f[z] for z in Z] for f in filas], [etiquetas[f["codigo_municipio"]] for f in filas])


def resumen_numerico(valores):
    return {"n": len(valores), "media": float(np.mean(valores)), "min": float(np.min(valores)), "max": float(np.max(valores))}


def perfiles(filas, etiquetas):
    resultado = []
    for perfil in sorted(set(etiquetas.values())):
        grupo = [f for f in filas if etiquetas[f["codigo_municipio"]] == perfil]
        x = np.array([[f[z] for z in Z] for f in grupo])
        distancias = ((x - x.mean(axis=0)) ** 2).sum(axis=1)
        orden = sorted(range(len(grupo)), key=lambda i: (distancias[i], grupo[i]["codigo_municipio"]))
        resultado.append({"perfil": perfil, "n": len(grupo), "porcentaje": len(grupo) / len(filas) * 100,
            "variables": {v: dict(zip(("min", "q25", "mediana", "q75", "max"), np.quantile([float(f[v]) for f in grupo], [0, .25, .5, .75, 1]).tolist())) for v in VARIABLES},
            "ejemplos_cercanos_a_media_grupo": [{"codigo": grupo[i]["codigo_municipio"], "nombre": grupo[i]["nombre_municipio"]} for i in orden[:3]],
            "rentas_estimadas": sum(f["estado_renta_modelado"] != "publicada_2023" for f in grupo)})
    assert sum(g["n"] for g in resultado) == len(filas)
    return resultado


def escribir_csv(ruta, filas):
    assert filas
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


def main():
    carpeta_previa = RAIZ / PREPARACION
    manifiesto_previo = json.loads((carpeta_previa / "manifiesto.json").read_text(encoding="utf-8"))
    for item in manifiesto_previo["fuentes"] + manifiesto_previo["salidas"] + [manifiesto_previo["productor"]]:
        assert huella(RAIZ / item["ruta"]) == item["sha256"]
    protocolo = json.loads((carpeta_previa / "protocolo.json").read_text(encoding="utf-8"))
    c = duckdb.connect()
    c.read_parquet(str(carpeta_previa / "entradas_desarrollo.parquet")).create_view("entradas")

    def leer(ajuste, rol):
        datos = c.execute("SELECT * FROM entradas WHERE ajuste=? AND rol=? ORDER BY codigo_municipio", [ajuste, rol]).fetchall()
        columnas = [d[0] for d in c.description]
        return [dict(zip(columnas, f)) for f in datos]

    desarrollo = cargar_desarrollo()
    codigos_desarrollo = {f["codigo_municipio"] for f in desarrollo}
    resultados, validaciones, perturbaciones, sensibilidad = [], [], [], []
    for i in range(1, 5):
        ajuste = f"interna_{i}"
        train, val = leer(ajuste, "entrenamiento"), leer(ajuste, "validacion")
        assert len(train) + len(val) == 433
        medianas = ajustar_medianas(train)
        etiquetas = asignar(val, medianas)
        metricas = evaluar(val, etiquetas)
        assert set(etiquetas) <= codigos_desarrollo
        for f, valor in zip(val, metricas["por_municipio_en_orden"]):
            validaciones.append(dict(f, perfil=etiquetas[f["codigo_municipio"]], silhouette=valor))

        train_original = [f for f in desarrollo if f["particion_interna"] != i]
        val_original = [f for f in desarrollo if f["particion_interna"] == i]
        estabilidad = []
        for plan in protocolo["planes_estabilidad"][ajuste]:
            subconjunto = [f for f in train_original if f["bloque_espacial"] not in plan["bloques_omitidos"]]
            a, b, preparacion = preparar(subconjunto, val_original)
            cortes = ajustar_medianas(a)
            otras = asignar(b, cortes)
            ari = estabilidad_por_codigo(etiquetas, otras)
            estabilidad.append({**plan, "medianas": cortes, "preparacion": preparacion, "ari": ari,
                "fraccion_cambio_perfil_literal": sum(etiquetas[k] != otras[k] for k in etiquetas) / len(etiquetas)})
            perturbaciones.extend({"ajuste": ajuste, "repeticion": plan["repeticion"], "codigo_municipio": k, "perfil_principal": etiquetas[k], "perfil_perturbado": otras[k]} for k in sorted(otras))

        train_pub = [f for f in train_original if f["estado_renta_modelado"] == "publicada_2023"]
        val_pub = [f for f in val_original if f["estado_renta_modelado"] == "publicada_2023"]
        a, b, params_pub = preparar(train_pub, val_pub)
        cortes_pub = ajustar_medianas(a)
        etiquetas_pub = asignar(b, cortes_pub)
        principal_comun = {k: etiquetas[k] for k in etiquetas_pub}
        sens = {"n_train_publicada": len(a), "n_val_publicada": len(b), "medianas": cortes_pub,
            "preparacion": params_pub, "ari_sobre_mismos_municipios": estabilidad_por_codigo(principal_comun, etiquetas_pub),
            "geometria_variante": evaluar(b, etiquetas_pub),
            "cambios_perfil_literal": [k for k in sorted(etiquetas_pub) if etiquetas_pub[k] != principal_comun[k]],
            "cautela": "Se excluyen los siete estimados; mide influencia conjunta de esas filas y de cambios de preparacion, no valida sus importes."}
        sensibilidad.extend({"ajuste": ajuste, "codigo_municipio": k, "perfil_principal": principal_comun[k], "perfil_solo_publicadas": etiquetas_pub[k]} for k in sorted(etiquetas_pub))
        resultados.append({"ajuste": ajuste, "n_entrenamiento": len(train), "n_validacion": len(val), "medianas": medianas,
            "grupos_entrenamiento": len(set(asignar(train, medianas).values())), "cobertura_validacion": len(etiquetas) / len(val),
            "geometria_validacion": metricas, "perfiles_validacion": perfiles(val, etiquetas),
            "estabilidad": estabilidad, "ari_estabilidad_resumen": resumen_numerico([e["ari"] for e in estabilidad]),
            "sensibilidad_renta": sens})
    assert len(validaciones) == len({f["codigo_municipio"] for f in validaciones}) == 433
    assert {f["codigo_municipio"] for f in validaciones} == codigos_desarrollo
    assert len(perturbaciones) == 4330 and len(sensibilidad) == 426

    completo = leer("desarrollo_completo", "entrenamiento")
    cortes_completos = ajustar_medianas(completo)
    etiquetas_completas = asignar(completo, cortes_completos)
    descriptivo = {"n": len(completo), "medianas": cortes_completos,
        "perfiles": perfiles(completo, etiquetas_completas),
        "cautela": "Ajuste descriptivo sobre los 433 de desarrollo. No es rendimiento fuera de entrenamiento ni clasificacion de los 541."}
    resumen = {"silhouette_validacion": resumen_numerico([r["geometria_validacion"]["silhouette"] for r in resultados]),
        "ari_estabilidad_40_repeticiones": resumen_numerico([e["ari"] for r in resultados for e in r["estabilidad"]]),
        "ari_sensibilidad_renta": resumen_numerico([r["sensibilidad_renta"]["ari_sobre_mismos_municipios"] for r in resultados]),
        "cobertura_validacion": len(validaciones) / len(desarrollo), "n_municipios_desarrollo": 433, "n_prueba_evaluados": 0}
    ejecucion = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    carpeta = RAIZ / "resultados/modelado/baseline" / ejecucion
    carpeta.mkdir(parents=True, exist_ok=False)
    resultado = {"ejecucion": ejecucion, "leyenda": "I=inferior o igual a mediana; S=superior; orden volumen,proporcion,renta. Sin prioridad.",
        "resumen": resumen, "validaciones": resultados, "descriptivo_desarrollo": descriptivo,
        "limites": ["Sin prueba final o alternativa ML.", "Bloques20km sin banda de separacion; no prueban independencia espacial completa.", "Silhouette evalua la representacion elegida; perfiles no acreditan deficit de recarga.", "Estabilidad se calcula frente a cada ajuste principal, no como cuarenta muestras independientes."]}
    (carpeta / "resultados.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    escribir_csv(carpeta / "asignaciones_validacion.csv", validaciones)
    escribir_csv(carpeta / "estabilidad_asignaciones.csv", perturbaciones)
    escribir_csv(carpeta / "sensibilidad_asignaciones.csv", sensibilidad)
    escribir_csv(carpeta / "perfiles_desarrollo.csv", [dict(f, perfil=etiquetas_completas[f["codigo_municipio"]]) for f in completo])
    escribir_csv(carpeta / "metricas_validacion.csv", [{"ajuste": r["ajuste"], "n_train": r["n_entrenamiento"], "n_val": r["n_validacion"],
        "silhouette": r["geometria_validacion"]["silhouette"], "fraccion_negativa": r["geometria_validacion"]["fraccion_negativa"],
        "k_observado": r["geometria_validacion"]["k"], "cobertura": r["cobertura_validacion"],
        "ari_estabilidad_medio": r["ari_estabilidad_resumen"]["media"], "ari_estabilidad_min": r["ari_estabilidad_resumen"]["min"],
        "ari_sensibilidad_renta": r["sensibilidad_renta"]["ari_sobre_mismos_municipios"]} for r in resultados])
    manifiesto = {"ejecucion": ejecucion, "fuentes": [{"ruta": str(p.relative_to(RAIZ)).replace('\\', '/'), "sha256": huella(p)} for p in (carpeta_previa / "manifiesto.json", carpeta_previa / "protocolo.json", carpeta_previa / "entradas_desarrollo.parquet")],
        "productor": {"ruta": Path(__file__).resolve().relative_to(RAIZ).as_posix(), "sha256": huella(Path(__file__))},
        "salidas": [{"ruta": p.relative_to(RAIZ).as_posix(), "sha256": huella(p)} for p in sorted(carpeta.iterdir())],
        "versiones": manifiesto_previo["versiones"], "n_ajustes_baseline": 49,
        "controles": "433 validaciones unicas, cada una fuera de su entrenamiento; 40 perturbaciones del protocolo; sensibilidad sobre mismos426 publicados; 433 perfiles descriptivos; test0."}
    (carpeta / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"salida": carpeta.relative_to(RAIZ).as_posix(), "resumen": resumen,
        "validaciones": [{"ajuste": r["ajuste"], "silhouette": r["geometria_validacion"]["silhouette"], "medianas": r["medianas"], "ari": r["ari_estabilidad_resumen"]} for r in resultados],
        "descriptivo": descriptivo}, ensure_ascii=True))


if __name__ == "__main__":
    main()
