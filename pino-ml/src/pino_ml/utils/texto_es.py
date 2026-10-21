# -*- coding: utf-8 -*-
"""
Utilidades de texto en español: normalización, separación silábica,
conversión de grafemas a fonemas y métricas de distancia fonética.

Se asume la pronunciación hispanoamericana/chilena (seseo: "ce", "ci" y "z" suenan /s/)
y yeísmo ("ll" y "y" consonante suenan igual /ʝ/).
"""

import re
import unicodedata
from difflib import SequenceMatcher

_VOCALES_FUERTES = set('aeoáéóíú')  # í/ú con tilde rompen el diptongo (hiato)
_VOCALES_DEBILES = set('iuü')
_VOCALES = _VOCALES_FUERTES | _VOCALES_DEBILES

# Grupos consonánticos que no se separan (van juntos al inicio de sílaba)
_GRUPOS_INSEPARABLES = {
    'pl', 'pr', 'bl', 'br', 'fl', 'fr', 'cl', 'cr', 'gl', 'gr',
    'tr', 'dr', 'kl', 'kr', 'tl',
}
_DIGRAFOS = ('ch', 'll', 'rr')
_SIN_TILDE = str.maketrans('áéíóú', 'aeiou')


def normalizar(texto: str, quitar_tildes: bool = True) -> str:
    """
    Minúsculas, sin puntuación ni espacios repetidos. Conserva la ñ.
    Con `quitar_tildes`, "Mamá." y "mama" quedan iguales.
    """
    if not texto:
        return ""
    texto = unicodedata.normalize('NFC', texto.lower())
    texto = re.sub(r"[^a-záéíóúüñ\s]", " ", texto)
    if quitar_tildes:
        texto = texto.translate(_SIN_TILDE)
    return " ".join(texto.split())


def _es_vocal(palabra: str, i: int) -> bool:
    c = palabra[i]
    if c == 'y':
        # "y" es vocal al final de palabra o antes de consonante: rey, muy, y
        return i == len(palabra) - 1 or palabra[i + 1] not in _VOCALES
    if c == 'u' and i > 0 and palabra[i - 1] in 'qg' and i + 1 < len(palabra) and palabra[i + 1] in 'eiéí':
        # "u" muda en que, qui, gue, gui
        return False
    return c in _VOCALES


def _unidades(palabra: str) -> list[tuple[str, bool]]:
    """
    Divide la palabra en unidades (texto, es_vocal). Los dígrafos ch/ll/rr y
    qu/gu (con u muda) son una sola consonante.
    """
    unidades = []
    i = 0
    while i < len(palabra):
        if palabra[i:i + 2] in _DIGRAFOS:
            unidades.append((palabra[i:i + 2], False))
            i += 2
        elif palabra[i] in 'qg' and i + 1 < len(palabra) and not _es_vocal(palabra, i + 1) and palabra[i + 1] == 'u':
            unidades.append((palabra[i:i + 2], False))
            i += 2
        else:
            unidades.append((palabra[i], _es_vocal(palabra, i)))
            i += 1
    return unidades


def _hay_hiato(a: str, b: str) -> bool:
    """Dos vocales seguidas van en sílabas distintas si ambas son fuertes."""
    return a[-1] in _VOCALES_FUERTES and b in _VOCALES_FUERTES


def separar_silabas(palabra: str) -> list[str]:
    """
    Separa una palabra en sílabas fonológicas:
    ca-sa, pe-rro, ár-bol, pla-to, a-gua, po-e-ta, dí-a, ins-tan-te.
    """
    palabra = normalizar(palabra, quitar_tildes=False).replace(' ', '')
    if not palabra:
        return []

    bloques: list[tuple[str, bool]] = []
    for texto, es_vocal in _unidades(palabra):
        if es_vocal and bloques and bloques[-1][1] and not _hay_hiato(bloques[-1][0], texto):
            bloques[-1] = (bloques[-1][0] + texto, True)  # diptongo / triptongo
        else:
            bloques.append((texto, es_vocal))

    nucleos = [i for i, (_, es_vocal) in enumerate(bloques) if es_vocal]
    if not nucleos:
        return [palabra]

    silabas = []
    inicio = 0
    for actual, siguiente in zip(nucleos, nucleos[1:]):
        consonantes = [t for t, _ in bloques[actual + 1:siguiente]]
        n = len(consonantes)
        if n >= 2 and (consonantes[-2] + consonantes[-1]) in _GRUPOS_INSEPARABLES:
            van_con_la_siguiente = 2   # pla-to, ins-trui-do
        elif n >= 1:
            van_con_la_siguiente = 1   # ca-sa, ár-bol, ins-tan-te
        else:
            van_con_la_siguiente = 0   # po-e-ta
        corte = siguiente - van_con_la_siguiente
        silabas.append("".join(t for t, _ in bloques[inicio:corte]))
        inicio = corte
    silabas.append("".join(t for t, _ in bloques[inicio:]))
    return silabas


def contar_silabas(palabra: str) -> int:
    return max(1, len(separar_silabas(palabra)))


_FONEMA_SIMPLE = {
    'a': '/a/', 'e': '/e/', 'i': '/i/', 'o': '/o/', 'u': '/u/',
    'b': '/b/', 'v': '/b/', 'd': '/d/', 'f': '/f/', 'j': '/x/', 'k': '/k/',
    'l': '/l/', 'm': '/m/', 'n': '/n/', 'ñ': '/ɲ/', 'p': '/p/', 's': '/s/',
    't': '/t/', 'w': '/w/', 'x': '/ks/', 'z': '/s/', 'ü': '/w/',
}


def palabra_a_fonemas(palabra: str) -> list[str]:
    """
    Convierte una palabra escrita en su secuencia de fonemas IPA estándar latinoamericano:
    casa /k/ vs cine /s/, gato /g/ vs gente /x/, guerra /g/, queso /k/, rana /r/ vs pera /ɾ/.
    """
    p = normalizar(palabra, quitar_tildes=True).replace(' ', '')
    fonemas = []
    i = 0
    while i < len(p):
        c = p[i]
        sig = p[i + 1] if i + 1 < len(p) else ''
        sig2 = p[i + 2] if i + 2 < len(p) else ''

        if p[i:i + 2] == 'ch':
            fonemas.append('/tʃ/'); i += 2
        elif p[i:i + 2] == 'll':
            fonemas.append('/ʝ/'); i += 2
        elif p[i:i + 2] == 'rr':
            fonemas.append('/r/'); i += 2
        elif c == 'q' and sig == 'u':
            fonemas.append('/k/'); i += 2
        elif c == 'g' and sig == 'u' and sig2 in ('e', 'i'):
            fonemas.append('/g/'); i += 2
        elif c == 'c':
            fonemas.append('/s/' if sig in ('e', 'i') else '/k/'); i += 1
        elif c == 'g':
            fonemas.append('/x/' if sig in ('e', 'i') else '/g/'); i += 1
        elif c == 'r':
            fuerte = i == 0 or (i > 0 and p[i - 1] in 'lns')
            fonemas.append('/r/' if fuerte else '/ɾ/'); i += 1
        elif c == 'y':
            fonemas.append('/i/' if _es_vocal(p, i) else '/ʝ/'); i += 1
        elif c == 'h':
            i += 1  # muda
        elif c in _FONEMA_SIMPLE:
            fonemas.append(_FONEMA_SIMPLE[c]); i += 1
        else:
            i += 1
    return fonemas


def similitud_fonetica(fonemas_esperados: list[str], fonemas_obtenidos: list[str]) -> float:
    """Calcula la razón de similitud entre dos secuencias de fonemas (0.0 a 1.0)."""
    if not fonemas_esperados and not fonemas_obtenidos:
        return 1.0
    if not fonemas_esperados or not fonemas_obtenidos:
        return 0.0
    return SequenceMatcher(None, fonemas_esperados, fonemas_obtenidos).ratio()


def calcular_complejidad_silabica(silaba: str) -> float:
    """
    Puntúa la dificultad silábica para niños y aprendices:
    - CV (directa, ej: ma, pa): 1.0
    - V (vocal sola, ej: a): 1.1
    - CVC (inversa/cerrada, ej: sol, pan): 1.6
    - CCV (trabada/compleja, ej: tra, pla): 2.4
    - CCVC (mixta compleja, ej: tren, plas): 3.0
    """
    s = normalizar(silaba, quitar_tildes=True)
    if not s:
        return 1.0
    es_trabada = any(s.startswith(g) for g in _GRUPOS_INSEPARABLES)
    num_cons = sum(1 for c in s if c not in _VOCALES)
    if es_trabada and num_cons >= 3:
        return 3.0
    elif es_trabada:
        return 2.4
    elif num_cons >= 2:
        return 1.6
    elif len(s) == 1 and s in _VOCALES:
        return 1.1
    return 1.0
