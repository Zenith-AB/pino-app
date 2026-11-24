# -*- coding: utf-8 -*-
"""
Motor de predicción de la app Streamlit de Pino.

Carga los modelos entrenados en el notebook (``models/*.joblib``) y calcula, para
cualquier palabra, las mismas variables que usa ``src/lexico.py``. Así la interfaz
puede autocompletar los campos a partir de una palabra escrita por el usuario y
luego predecir la edad de adquisición (AoA) en años y el nivel de la app.

No depende de Streamlit: se puede probar con ``python -I app/motor.py``.
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
import lexico  # noqa: E402  (también deja disponible pino_ml.utils.texto_es)
from lexico import texto_es  # noqa: E402

MODELS = RAIZ / "models"
PROC = RAIZ / "data" / "processed"

# Mismas variables y cortes que el notebook
NUM_EN = ["zipf", "n_letras", "n_fonemas", "n_silabas", "opacidad", "grupo_cons_max", "vecinos_ort", "concrecion"]
CAT = ["categoria"]
CORTES = [0, 4, 6, 8, 10, 99]
NIVELES = ["1 · Primeras palabras", "2 · Preescolar", "3 · Lectura inicial", "4 · Lector en desarrollo", "Fuera de foco (≥ 10 años)"]
USO_NIVEL = [
    "Vocabulario oral con imagen y audio",
    "Sílabas directas (CV) y conciencia fonológica",
    "Decodificación de palabras completas",
    "Palabras largas y menos frecuentes",
    "No se recomienda para la app infantil",
]
CATEGORIAS = ["sustantivo", "verbo", "adjetivo", "otra"]

# Error del modelo, usado para el intervalo y la probabilidad por edad.
# EN: RMSE en test (años). ES: MAE de CV de la mejor estrategia (escala 1–11) × 1,25 ≈ RMSE.
RMSE_EN_ANIOS = 1.8954
RMSE_ES_ESCALA = 0.9533 * 1.25

VOCALES_ARPA = lexico.VOCALES_ARPA
VOCALES_ES = lexico.VOCALES_ES


# ----------------------------------------------------------------------------- carga
@lru_cache(maxsize=None)
def modelos():
    en = joblib.load(MODELS / "modelo_aoa_en.joblib")
    es = joblib.load(MODELS / "modelo_aoa_es.joblib")
    km = joblib.load(MODELS / "kmeans_familias.joblib")
    with open(MODELS / "metricas.json", encoding="utf-8") as f:
        met = json.loads(f.read().replace("NaN", "null"))
    return en, es, km, met


@lru_cache(maxsize=None)
def tabla_en() -> pd.DataFrame:
    """28.825 palabras inglesas con todas sus variables y la AoA real (Kuperman)."""
    return pd.read_csv(PROC / "palabras_en_modelado.csv").drop_duplicates("palabra").set_index("palabra")


@lru_cache(maxsize=None)
def tabla_es() -> pd.DataFrame:
    """1.239 palabras españolas con variables y la AoA real (Alonso, escala 1–11)."""
    return pd.read_csv(PROC / "palabras_es_modelado.csv").drop_duplicates("palabra").set_index("palabra")


@lru_cache(maxsize=None)
def vocab_es() -> pd.DataFrame:
    return pd.read_csv(PROC / "vocabulario_infantil_es.csv").drop_duplicates("palabra").set_index("palabra")


@lru_cache(maxsize=None)
def vocab_en() -> pd.DataFrame:
    return pd.read_csv(PROC / "vocabulario_infantil_en.csv").drop_duplicates("palabra").set_index("palabra")


@lru_cache(maxsize=None)
def cmudict() -> dict:
    return lexico.cargar_cmudict()


@lru_cache(maxsize=None)
def concrecion_en() -> pd.Series:
    return lexico.cargar_concrecion_en()


@lru_cache(maxsize=None)
def kuperman() -> pd.DataFrame:
    k = lexico.cargar_kuperman()
    return k[k["Word"].str.fullmatch(r"[a-z]+")].drop_duplicates("Word").set_index("Word")


@lru_cache(maxsize=None)
def subtlex_es() -> pd.DataFrame:
    return lexico.cargar_subtlex_esp()


def _patrones(lexico_iter) -> tuple[Counter, frozenset]:
    pat, lex = Counter(), frozenset(lexico_iter)
    for w in lex:
        for i in range(len(w)):
            pat[w[:i] + "*" + w[i + 1:]] += 1
    return pat, lex


@lru_cache(maxsize=None)
def patrones_en():
    return _patrones(kuperman().index)


@lru_cache(maxsize=None)
def patrones_es():
    s = subtlex_es()
    return _patrones(s.loc[s["freq_pm"] >= 0.5, "palabra"].map(lexico.sin_tildes))


def vecinos(w: str, pat_lex) -> int:
    pat, lex = pat_lex
    en_lex = w in lex
    return int(sum(pat.get(w[:i] + "*" + w[i + 1:], 0) - (1 if en_lex else 0) for i in range(len(w))))


def _num(x):
    try:
        x = float(x)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------- variables: inglés
def rasgos_en(palabra: str) -> dict:
    """Variables de una palabra inglesa. Usa las normas si existen y las calcula si no."""
    w = palabra.strip().lower()
    t = tabla_en()
    if w in t.index:
        r = t.loc[w]
        return {
            "zipf": _num(r["zipf"]), "n_letras": int(r["n_letras"]), "n_fonemas": int(r["n_fonemas"]),
            "n_silabas": int(r["n_silabas"]), "grupo_cons_max": _num(r["grupo_cons_max"]),
            "vecinos_ort": int(r["vecinos_ort"]), "concrecion": _num(r["concrecion"]), "categoria": r["categoria"],
            "fonemas": r["fonemas"] if isinstance(r["fonemas"], str) else "",
            "aoa_real": _num(r["aoa"]), "fuente": "Palabra con norma (Kuperman et al., 2012)",
        }
    # Palabra nueva: se calcula todo lo posible
    cmu = cmudict()
    k = kuperman()
    fon = cmu.get(w)
    if fon:
        n_fon = len(fon)
        n_sil = max(1, sum(f in VOCALES_ARPA for f in fon))
        gcm = lexico.max_racha(fon, lambda f: f in VOCALES_ARPA)
    else:  # sin pronunciación: aproximación ortográfica
        n_fon = len(w)
        n_sil = max(1, len(re.findall(r"[aeiouy]+", w)) - (1 if w.endswith("e") and len(w) > 3 else 0))
        gcm = max((len(m) for m in re.findall(r"[^aeiouy]+", w)), default=0)
    zipf = None
    categoria = "otra"
    if w in k.index:
        fpm = pd.to_numeric(k.loc[w, "Freq_pm"], errors="coerce")
        zipf = float(np.log10(fpm) + 3) if fpm and fpm > 0 else None
        categoria = lexico.POS_EN.get(k.loc[w, "Dom_PoS_SUBTLEX"], "otra")
    return {
        "zipf": zipf, "n_letras": len(w), "n_fonemas": n_fon, "n_silabas": n_sil, "grupo_cons_max": gcm,
        "vecinos_ort": vecinos(w, patrones_en()), "concrecion": _num(concrecion_en().get(w)), "categoria": categoria,
        "fonemas": " ".join(fon) if fon else "", "aoa_real": None,
        "fuente": "Palabra nueva: variables calculadas automáticamente" + ("" if fon else " (sin pronunciación en CMU)"),
    }


# ------------------------------------------------------------------- variables: español
def traduccion_sugerida(palabra: str) -> str:
    w = palabra.strip().lower()
    for tabla, col in ((tabla_es(), "traduccion_en"), (vocab_es(), "traduccion_en")):
        if w in tabla.index and isinstance(tabla.loc[w, col], str):
            return tabla.loc[w, col]
    return ""


def info_traduccion(trad: str) -> dict:
    """AoA (Kuperman) y concreción (Brysbaert) del equivalente inglés."""
    t = trad.strip().lower()
    if not t:
        return {"aoa_equivalente_en": None, "concrecion": None}
    aoa = None
    if t in tabla_en().index:
        aoa = _num(tabla_en().loc[t, "aoa"])
    elif t in kuperman().index:
        aoa = _num(kuperman().loc[t, "AoA_Kup"])
    return {"aoa_equivalente_en": aoa, "concrecion": _num(concrecion_en().get(t))}


def rasgos_es(palabra: str, traduccion: str | None = None) -> dict:
    w = palabra.strip().lower()
    t = tabla_es()
    trad = (traduccion or "").strip().lower() or traduccion_sugerida(w)
    sil = texto_es.separar_silabas(w)
    fon = texto_es.palabra_a_fonemas(w)
    fpm = subtlex_es().set_index("palabra")["freq_pm"].get(w)
    out = {
        "zipf": float(np.log10(fpm) + 3) if fpm and fpm > 0 else None,
        "n_letras": len(w), "n_fonemas": len(fon), "n_silabas": len(sil),
        "grupo_cons_max": lexico.max_racha(fon, lambda x: x in VOCALES_ES),
        "vecinos_ort": vecinos(lexico.sin_tildes(w), patrones_es()),
        "complejidad_silabica": float(np.mean([texto_es.calcular_complejidad_silabica(s) for s in sil])) if sil else 1.0,
        "categoria": "sustantivo", "traduccion_en": trad,
        "silabas": "-".join(sil), "fonemas": " ".join(fon), "aoa_real": None,
        "fuente": "Palabra nueva: variables calculadas con texto_es (backend de Pino)",
    }
    out.update(info_traduccion(trad))
    if w in t.index:
        r = t.loc[w]
        out["categoria"] = r["categoria"]
        out["aoa_real"] = float(escala_es_a_anios(r["aoa"]))
        out["fuente"] = "Palabra con norma (Alonso et al., 2015)"
    return out


# ------------------------------------------------------------------------ predicción
def escala_es_a_anios(x):
    _, es, _, _ = modelos()
    return np.interp(x, es["q_es"], es["q_en"])


def anios_a_escala_es(anios):
    _, es, _, _ = modelos()
    return np.interp(anios, es["q_en"], es["q_es"])


def nivel_de(aoa: float) -> int:
    for i in range(len(CORTES) - 1):
        if CORTES[i] <= aoa < CORTES[i + 1]:
            return i
    return len(NIVELES) - 1


def _fila(v: dict, cols) -> pd.DataFrame:
    f = {c: (np.nan if v.get(c) is None else v.get(c)) for c in cols}
    f["opacidad"] = f["n_letras"] - f["n_fonemas"]
    return pd.DataFrame([f])


def _normal_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def familia(v: dict) -> str:
    _, _, km, _ = modelos()
    x = pd.DataFrame([{c: (np.nan if v.get(c) is None else v.get(c)) for c in km["variables"]}])
    return km["nombres"][int(km["kmeans"].predict(km["prep"].transform(x))[0])]


def predecir(idioma: str, v: dict, edad_nino: float | None = None) -> dict:
    """
    idioma: "es" | "en". v: diccionario con las variables (None = desconocida, el modelo la imputa).
    Devuelve AoA en años, nivel, intervalo aproximado al 80 % y la probabilidad de que la
    palabra ya esté adquirida a la edad indicada.
    """
    m_en, m_es, _, _ = modelos()
    if idioma == "en":
        X = _fila(v, NUM_EN + CAT)
        aoa = float(m_en.predict(X[NUM_EN + CAT])[0])
        lo, hi = aoa - 1.2816 * RMSE_EN_ANIOS, aoa + 1.2816 * RMSE_EN_ANIOS
        prob = None if edad_nino is None else _normal_cdf((edad_nino - aoa) / RMSE_EN_ANIOS)
        extra = {}
    else:
        cols = [c for c in m_es["variables"] if c not in ("pred_modelo_en",)]
        X = _fila(v, list(dict.fromkeys(NUM_EN + cols)))
        X["pred_modelo_en"] = m_en.predict(X[NUM_EN + CAT])     # stacking entre idiomas
        escala = float(m_es["modelo"].predict(X[m_es["variables"]])[0])
        aoa = float(escala_es_a_anios(escala))
        lo = float(escala_es_a_anios(escala - 1.2816 * RMSE_ES_ESCALA))
        hi = float(escala_es_a_anios(escala + 1.2816 * RMSE_ES_ESCALA))
        prob = None if edad_nino is None else _normal_cdf((float(anios_a_escala_es(edad_nino)) - escala) / RMSE_ES_ESCALA)
        extra = {"aoa_escala": escala, "pred_modelo_en": float(X["pred_modelo_en"][0])}
    n = nivel_de(aoa)
    return {"aoa": aoa, "lo": lo, "hi": hi, "nivel": n, "nivel_nombre": NIVELES[n], "uso": USO_NIVEL[n],
            "prob_edad": prob, "familia": familia(v), **extra}


def curva(idioma: str, v: dict, variable: str, valores) -> pd.DataFrame:
    """Análisis "¿qué pasaría si...?": AoA predicha al variar una sola variable."""
    filas = []
    for x in valores:
        vv = dict(v)
        vv[variable] = float(x)
        filas.append({variable: float(x), "AoA (años)": predecir(idioma, vv)["aoa"]})
    return pd.DataFrame(filas)


if __name__ == "__main__":
    for w in ["dog", "butterfly", "democracy", "dinosaur", "pikachu"]:
        r = rasgos_en(w)
        p = predecir("en", r, 5)
        print(f"EN {w:<11} real={r['aoa_real']}  pred={p['aoa']:.2f}  {p['nivel_nombre']}  P(5 años)={p['prob_edad']:.0%}  {p['familia']}")
    for w, t in [("perro", ""), ("mariposa", "butterfly"), ("democracia", "democracy"), ("guagua", "baby"), ("palta", "avocado")]:
        r = rasgos_es(w, t)
        p = predecir("es", r, 5)
        print(f"ES {w:<11} real={r['aoa_real']}  pred={p['aoa']:.2f}  {p['nivel_nombre']}  P(5 años)={p['prob_edad']:.0%}  {p['familia']}  sil={r['silabas']}")
