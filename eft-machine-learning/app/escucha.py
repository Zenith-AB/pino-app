# -*- coding: utf-8 -*-
"""
Compara lo que se dice al micrófono con la palabra esperada.

La transcripción usa Whisper en el propio computador (faster-whisper): el audio no se envía
a ningún servicio. La comparación sigue la lógica de ``pino_ml.models.stt_fonetico``.

Es una ayuda experimental: Whisper tiende a "corregir" lo que oye, así que puede dar por buena
una pronunciación imperfecta o fallar con palabras muy cortas y voces infantiles.
"""

from __future__ import annotations

import difflib
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import texto_es  # noqa: E402

UMBRAL_SIN_HABLA = 0.6
UMBRAL_CASI = 0.6
NUMEROS = {"es": "cero uno dos tres cuatro cinco seis siete ocho nueve diez".split(),
           "en": "zero one two three four five six seven eight nine ten".split()}


@dataclass
class Resultado:
    veredicto: str                      # "bien" | "casi" | "otra" | "sin_voz"
    puntaje: float                      # similitud de sonidos, 0 a 1
    oido: str = ""
    silabas: list[tuple[str, bool]] = field(default_factory=list)   # solo español


def cargar_modelo(tamano: str = "small"):
    """La primera vez descarga el modelo (internet); después funciona sin conexión."""
    from faster_whisper import WhisperModel
    return WhisperModel(tamano, device="cpu", compute_type="int8")


def transcribir(modelo, audio, idioma: str) -> str:
    """No se le entrega la palabra esperada, para no sesgar lo que "oye"."""
    segmentos, _ = modelo.transcribe(audio, language=idioma, beam_size=5, vad_filter=True,
                                     condition_on_previous_text=False)
    return " ".join(s.text.strip() for s in segmentos if s.no_speech_prob < UMBRAL_SIN_HABLA)


def limpiar(texto: str, idioma: str) -> list[str]:
    texto = re.sub(r"\b(10|\d)\b", lambda m: NUMEROS[idioma][int(m.group())], texto.lower())
    if idioma == "es":
        return texto_es.normalizar(texto, quitar_tildes=True).split()
    return re.sub(r"[^a-z' ]", " ", texto).split()


def sonidos(palabra: str, idioma: str, cmu: dict[str, str] | None = None) -> list[str]:
    if idioma == "es":
        return texto_es.palabra_a_fonemas(palabra)
    if cmu and palabra in cmu:
        return re.sub(r"\d", "", cmu[palabra]).split()
    return list(palabra)


def parecido(esperada: str, dicha: str, idioma: str, cmu=None) -> float:
    if esperada == dicha:
        return 1.0
    # Se comparan sonidos solo si ambas palabras se pueden representar igual
    if idioma == "en" and not (cmu and esperada in cmu and dicha in cmu):
        return difflib.SequenceMatcher(None, esperada, dicha).ratio()
    return difflib.SequenceMatcher(None, sonidos(esperada, idioma, cmu), sonidos(dicha, idioma, cmu)).ratio()


def evaluar(esperada: str, transcripcion: str, idioma: str, cmu: dict[str, str] | None = None) -> Resultado:
    objetivo = "".join(limpiar(esperada, idioma))
    palabras = limpiar(transcripcion, idioma)
    if not palabras or not objetivo:
        return Resultado("sin_voz", 0.0)
    # Todo junto ("mari posa") y, en respuestas cortas, cada palabra por separado ("la pelota")
    candidatas = ["".join(palabras)] + (palabras if len(palabras) <= 3 else [])
    mejor = max(candidatas, key=lambda c: parecido(objetivo, c, idioma, cmu))
    puntaje = parecido(objetivo, mejor, idioma, cmu)
    veredicto = "bien" if math.isclose(puntaje, 1.0) else "casi" if puntaje >= UMBRAL_CASI else "otra"
    silabas = []
    if idioma == "es":
        esperadas = texto_es.separar_silabas(esperada)
        bloques = difflib.SequenceMatcher(
            None, [texto_es.normalizar(s) for s in esperadas],
            [texto_es.normalizar(s) for s in texto_es.separar_silabas(mejor)], autojunk=False).get_matching_blocks()
        ok = {i for b in bloques for i in range(b.a, b.a + b.size)}
        silabas = [(s, veredicto == "bien" or i in ok) for i, s in enumerate(esperadas)]
    return Resultado(veredicto, round(puntaje, 3), " ".join(palabras), silabas)
