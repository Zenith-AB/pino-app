# -*- coding: utf-8 -*-
"""Genera assets/data/vocabulario_beta.json desde el vocabulario nivelado de eft-machine-learning.

    python pino/tool/generar_vocabulario_beta.py
"""
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ORIGEN = REPO / "eft-machine-learning" / "data" / "processed"
DESTINO = REPO / "pino" / "assets" / "data" / "vocabulario_beta.json"
POR_NIVEL = 40
# Revisión adicional para la app infantil: palabras que el filtro del dataset deja pasar.
# Una educadora debe revisar la lista final antes de usarla con niños.
EXCLUIDAS = {
    "es": set("bala batalla granada ataúd calavera tumba cuchilla viuda trampa costilla caspa teta".split()),
    "en": set("pussy bar gang casino flesh chick butt breast boob bra thong weed joint nipple".split()),
}

salida = {}
for idioma in ("es", "en"):
    with open(ORIGEN / f"vocabulario_infantil_{idioma}.csv", encoding="utf-8") as f:
        filas = [r for r in csv.DictReader(f)
                 if r["categoria"] == "sustantivo" and r["concrecion"] and float(r["concrecion"]) >= 4
                 and len(r["palabra"]) >= 3 and r["zipf"]
                 and r["palabra"] not in EXCLUIDAS[idioma]]
    salida[idioma] = []
    for nivel in range(1, 5):
        grupo = sorted((r for r in filas if r["nivel_pino"].startswith(str(nivel))),
                       key=lambda r: -float(r["zipf"]))[:POR_NIVEL]
        salida[idioma] += [{"palabra": r["palabra"], "nivel": nivel,
                            "silabas": r["silabas"].split("-") if idioma == "es" else []} for r in grupo]

DESTINO.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print({k: len(v) for k, v in salida.items()})
