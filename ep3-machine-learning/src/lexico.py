# -*- coding: utf-8 -*-
"""
Construcción del dataset léxico bilingüe (español / inglés) para Pino.

Carga las fuentes crudas de ``data/raw`` y calcula, con **las mismas definiciones
para ambos idiomas**, las variables psicolingüísticas que se pueden obtener de
forma automática para cualquier palabra nueva del catálogo de la app:

    zipf                 frecuencia de uso (escala Zipf = log10(frecuencia por millón) + 3)
    n_letras             longitud ortográfica
    n_fonemas            longitud fonológica
    n_silabas            número de sílabas
    opacidad             n_letras - n_fonemas (letras mudas / dígrafos: costo de decodificación)
    grupo_cons_max       mayor secuencia de consonantes seguidas en la pronunciación ("tr", "str")
    vecinos_ort          vecindario ortográfico de Coltheart (palabras a una letra de distancia)
    concrecion           cuán concreta/perceptible es la palabra (1 abstracta – 5 concreta)
    categoria            sustantivo / verbo / adjetivo / otra

Para el español la separación silábica y la transcripción fonológica se hacen con
``pino_ml.utils.texto_es``, el mismo módulo que usa el backend de la app.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
sys.path.insert(0, str(RAIZ.parent / "pino-ml" / "src"))
from pino_ml.utils import texto_es  # noqa: E402

VOCALES_ARPA = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
VOCALES_ES = {"/a/", "/e/", "/i/", "/o/", "/u/"}

POS_EN = {"Noun": "sustantivo", "Verb": "verbo", "Adjective": "adjetivo"}
POS_ES = {"NOUN": "sustantivo", "VERB": "verbo", "ADJECTIVE": "adjetivo"}


# --------------------------------------------------------------------------- utilidades
def zipf(freq_pm):
    """Escala Zipf (van Heuven et al., 2014). Palabras ausentes del corpus -> NaN."""
    f = pd.to_numeric(freq_pm, errors="coerce")
    return np.where(f > 0, np.log10(f) + 3, np.nan)


def vecinos_coltheart(palabras, lexico) -> np.ndarray:
    """N de Coltheart: cuántas palabras del léxico difieren en exactamente una letra (sustitución)."""
    patrones = Counter()
    lex = set(lexico)
    for w in lex:
        for i in range(len(w)):
            patrones[w[:i] + "*" + w[i + 1:]] += 1
    salida = []
    for w in palabras:
        en_lex = w in lex
        n = sum(patrones.get(w[:i] + "*" + w[i + 1:], 0) - (1 if en_lex else 0) for i in range(len(w)))
        salida.append(n)
    return np.array(salida)


def max_racha(fonos, es_vocal) -> int:
    mejor = actual = 0
    for f in fonos:
        actual = 0 if es_vocal(f) else actual + 1
        mejor = max(mejor, actual)
    return mejor


def es_palabra_simple(w: str) -> bool:
    return bool(re.fullmatch(r"[a-záéíóúüñ]+", w))


def limpiar_glosa(g: str) -> str:
    """CONCEPTICON_GLOSS -> palabra inglesa: 'THE SUN' -> 'sun', 'TO EAT' -> 'eat', 'FLY (INSECT)' -> 'fly'."""
    g = re.sub(r"\s*\(.*?\)", "", str(g).lower()).strip()
    g = re.sub(r"^(the|to|a) ", "", g)
    return g


# ------------------------------------------------------------------------- cargadores
def cargar_cmudict() -> dict[str, list[str]]:
    pron = {}
    with open(RAW / "en_cmudict.dict", encoding="utf-8") as f:
        for linea in f:
            partes = linea.split("#")[0].split()
            if not partes:
                continue
            w = partes[0]
            if "(" in w:          # variantes de pronunciación: se usa la primera
                continue
            pron[w] = [re.sub(r"\d", "", p) for p in partes[1:]]
    return pron


def cargar_subtlex_esp() -> pd.DataFrame:
    """El archivo original trae 3 bloques de columnas lado a lado; se apilan."""
    s = pd.read_excel(RAW / "es_subtlex_esp_cuetos2011.xlsx")
    bloques = []
    for suf in ["", ".1", ".2"]:
        b = s[[f"Word{suf}", f"Freq. per million{suf}"]].copy()
        b.columns = ["palabra", "freq_pm"]
        bloques.append(b)
    d = pd.concat(bloques).dropna(subset=["palabra"])
    d["palabra"] = d["palabra"].astype(str).str.lower().str.strip()
    return d.groupby("palabra", as_index=False)["freq_pm"].sum()


def cargar_concrecion_en() -> pd.Series:
    c = pd.read_excel(RAW / "en_brysbaert2014_concreteness.xlsx")
    c = c[c["Bigram"] == 0]
    c["Word"] = c["Word"].astype(str).str.lower()
    return c.groupby("Word")["Conc.M"].mean()


def cargar_kuperman() -> pd.DataFrame:
    k = pd.read_excel(RAW / "en_kuperman2012_aoa_51715.xlsx")
    k["Word"] = k["Word"].astype(str).str.lower().str.strip()
    return k


# ----------------------------------------------------------------------- inglés
def construir_ingles() -> pd.DataFrame:
    k = cargar_kuperman()
    cmu = cargar_cmudict()
    conc = cargar_concrecion_en()

    d = k[k["Word"].str.fullmatch(r"[a-z]+")].drop_duplicates("Word").copy()
    d = pd.DataFrame({
        "palabra": d["Word"],
        "idioma": "en",
        "aoa": d["AoA_Kup"],                         # objetivo (años); NaN si la palabra no fue evaluada
        "pct_conocida": d["Perc_known"],
        "zipf": zipf(d["Freq_pm"]),
        "n_letras": d["Nletters"],
        "n_fonemas": d["Nphon"],
        "n_silabas": d["Nsyll"],
        "categoria": d["Dom_PoS_SUBTLEX"].map(POS_EN).fillna("otra"),
    })
    d["opacidad"] = d["n_letras"] - d["n_fonemas"]
    d["grupo_cons_max"] = [max_racha(cmu[w], lambda f: f in VOCALES_ARPA) if w in cmu else np.nan for w in d["palabra"]]
    d["vecinos_ort"] = vecinos_coltheart(d["palabra"], d["palabra"])
    d["concrecion"] = d["palabra"].map(conc)
    d["fonemas"] = [" ".join(cmu[w]) if w in cmu else "" for w in d["palabra"]]
    return d.reset_index(drop=True)


# ----------------------------------------------------------------------- español
def rasgos_es(palabras: pd.Series, lexico_freq: pd.DataFrame) -> pd.DataFrame:
    fpm = lexico_freq.set_index("palabra")["freq_pm"]
    sil = [texto_es.separar_silabas(w) for w in palabras]
    fon = [texto_es.palabra_a_fonemas(w) for w in palabras]
    lex_sin_tilde = lexico_freq["palabra"][lexico_freq["freq_pm"] >= 0.5].map(sin_tildes)
    return pd.DataFrame({
        "zipf": zipf(palabras.map(fpm)),
        "n_letras": palabras.str.len(),
        "n_fonemas": [len(f) for f in fon],
        "n_silabas": [len(s) for s in sil],
        "grupo_cons_max": [max_racha(f, lambda x: x in VOCALES_ES) for f in fon],
        "vecinos_ort": vecinos_coltheart(palabras.map(sin_tildes), lex_sin_tilde),
        "complejidad_silabica": [np.mean([texto_es.calcular_complejidad_silabica(x) for x in s]) if s else np.nan for s in sil],
        "silabas": ["-".join(s) for s in sil],
        "fonemas": [" ".join(f) for f in fon],
    }, index=palabras.index)


def sin_tildes(w: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn" or c == "̃")


def construir_espanol() -> pd.DataFrame:
    a = pd.read_csv(RAW / "es_alonso2015_aoa_norare.tsv", sep="\t")
    a["palabra"] = a["SPANISH"].astype(str).str.lower().str.strip()
    a = a[a["palabra"].map(es_palabra_simple)].drop_duplicates("palabra")

    subtlex = cargar_subtlex_esp()
    conc = cargar_concrecion_en()
    kup = cargar_kuperman().drop_duplicates("Word").set_index("Word")["AoA_Kup"]

    glosa = a["CONCEPTICON_GLOSS"].map(limpiar_glosa)
    d = pd.DataFrame({
        "palabra": a["palabra"],
        "idioma": "es",
        "aoa": a["SPANISH_AOA_MEAN"],                # objetivo: escala de Alonso (1-11)
        "traduccion_en": glosa,
        "concepticon_id": a["CONCEPTICON_ID"],
        "categoria": a["SPANISH_POS"].map(POS_ES).fillna("otra"),
        "concrecion": glosa.map(conc),               # concreción del equivalente inglés
        "aoa_equivalente_en": glosa.map(kup),        # AoA del equivalente inglés (Kuperman)
    })
    d = d.join(rasgos_es(d["palabra"], subtlex))
    d["opacidad"] = d["n_letras"] - d["n_fonemas"]
    return d.reset_index(drop=True)


def construir_multipic() -> pd.DataFrame:
    """Pares imagen–palabra español/inglés (MultiPic, 750 dibujos) con acuerdo de nombre."""
    m = pd.read_csv(RAW / "multipic_dunabeitia2022.csv", sep=";", decimal=",")
    m.columns = ["idioma", "codigo", "n_resp", "H", "nombre", "pct_acuerdo", "pct_nose", "pct_idiosincratico", "familiaridad"]
    piv = {}
    for lang, etiqueta in [("Spanish", "es"), ("Rioplatense Spanish", "es_rio"), ("American English", "en_us"), ("British English", "en_gb")]:
        x = m[m["idioma"] == lang].set_index("codigo")
        piv[f"nombre_{etiqueta}"] = x["nombre"].astype(str).str.lower().str.strip()
        piv[f"acuerdo_{etiqueta}"] = x["pct_acuerdo"]
    return pd.DataFrame(piv).reset_index()


if __name__ == "__main__":
    en, es, mp = construir_ingles(), construir_espanol(), construir_multipic()
    print(en.shape, en["aoa"].notna().sum(), es.shape, mp.shape)
