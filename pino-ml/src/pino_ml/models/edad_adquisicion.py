# -*- coding: utf-8 -*-
"""
Edad de adquisición (AoA) de una palabra en español o inglés.

Reutiliza los modelos y el código de ``eft-machine-learning`` (``app/motor.py``), para que
la API entregue lo mismo que el notebook. La carpeta se puede indicar con ``PINO_AOA_DIR``.
Requiere las versiones de ``eft-machine-learning/requirements.txt`` (los ``.joblib``
dependen de la versión de scikit-learn).
"""

from __future__ import annotations

import importlib
import os
import re
import sys
from pathlib import Path

PALABRA_VALIDA = re.compile(r"[a-záéíóúüñ]{1,40}")


def _carpeta() -> Path:
    if os.getenv("PINO_AOA_DIR"):
        return Path(os.environ["PINO_AOA_DIR"])
    return Path(__file__).resolve().parents[4] / "eft-machine-learning"


class EdadAdquisicion:
    def __init__(self, carpeta: Path | None = None):
        app = (carpeta or _carpeta()) / "app"
        if not (app / "motor.py").exists():
            raise FileNotFoundError(f"No se encontró {app / 'motor.py'}")
        if str(app) not in sys.path:
            sys.path.append(str(app))
        self.motor = importlib.import_module("motor")
        # Lee las normas al arrancar (unos segundos) para que la primera consulta sea rápida
        for idioma, palabra in (("es", "perro"), ("en", "dog"), ("es", "zzz"), ("en", "zzz")):
            self.analizar(palabra, idioma)

    def analizar(self, palabra: str, idioma: str = "es", traduccion: str | None = None) -> dict:
        palabra = palabra.strip().lower()
        if not PALABRA_VALIDA.fullmatch(palabra):
            raise ValueError("Se espera una sola palabra, solo con letras")
        m = self.motor
        rasgos = m.rasgos_es(palabra, traduccion) if idioma == "es" else m.rasgos_en(palabra)
        pred = m.predecir(idioma, rasgos)
        norma = rasgos.get("aoa_real")
        # Si hay una norma publicada manda ella; el modelo es para palabras sin norma
        edad = norma if norma is not None else pred["aoa"]
        nivel = m.nivel_de(edad)
        return {
            "palabra": palabra, "idioma": idioma,
            "edad_anios": round(float(edad), 2),
            "edad_modelo": round(float(pred["aoa"]), 2),
            "rango_modelo": [round(max(float(pred["lo"]), 0.0), 2), round(float(pred["hi"]), 2)],
            "origen": "norma" if norma is not None else "modelo",
            "nivel": int(nivel) + 1, "nivel_nombre": m.NIVELES[nivel],
            "silabas": rasgos["silabas"].split("-") if idioma == "es" else [],
        }
