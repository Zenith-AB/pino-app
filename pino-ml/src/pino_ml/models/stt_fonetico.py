# -*- coding: utf-8 -*-
"""
Módulo STT Fonético para Pino ML.
Transcribe audio, alinea sílabas y fonemas, calcula WER/CER y evalúa
pronunciación en tiempo real para lectura en voz alta (HU-06) y fonemas (HU-03).
"""

import difflib
import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import numpy as np
from jiwer import cer, wer

from pino_ml.utils.texto_es import normalizar, palabra_a_fonemas, separar_silabas, similitud_fonetica

UMBRAL_SIN_HABLA = 0.6

@dataclass
class SegmentoFonetico:
    """Un segmento de audio con su transcripción y métricas."""
    texto: str
    inicio_seg: float
    fin_seg: float
    confianza: float
    fonemas: list[str]

@dataclass
class ResultadoPronunciacion:
    """Resultado completo del análisis de pronunciación."""
    texto_esperado: str
    texto_detectado: str
    puntaje_global: float          # 0.0 a 1.0
    word_error_rate: float         # WER
    character_error_rate: float    # CER
    segmentos: list[SegmentoFonetico]
    silabas_incorrectas: list[str]
    silabas_correctas: list[str]
    similitud_fonetica_global: float = 0.0

def _segmentos_con_habla(resultado_whisper: dict) -> list[dict]:
    return [
        s for s in resultado_whisper.get("segments", [])
        if s.get("no_speech_prob", 0.0) < UMBRAL_SIN_HABLA
    ]

def _texto_detectado(resultado_whisper: dict) -> str:
    return " ".join(s.get("text", "") for s in _segmentos_con_habla(resultado_whisper))

def _silabas_de_texto(texto: str) -> list[str]:
    return [s for palabra in texto.split() for s in separar_silabas(palabra)]

def comparar_silabas(
    esperadas: list[str],
    detectadas: list[str],
) -> tuple[list[str], list[str]]:
    """
    Alinea las sílabas esperadas con las detectadas mediante SequenceMatcher
    y devuelve (correctas, incorrectas).
    """
    matcher = difflib.SequenceMatcher(
        a=[normalizar(s) for s in esperadas],
        b=[normalizar(s) for s in detectadas],
        autojunk=False,
    )
    acertadas = set()
    for bloque in matcher.get_matching_blocks():
        acertadas.update(range(bloque.a, bloque.a + bloque.size))

    correctas = [s for i, s in enumerate(esperadas) if i in acertadas]
    incorrectas = [s for i, s in enumerate(esperadas) if i not in acertadas]
    return correctas, incorrectas

def _extraer_segmentos(resultado_whisper: dict) -> list[SegmentoFonetico]:
    segmentos = []
    for segmento in _segmentos_con_habla(resultado_whisper):
        for palabra in segmento.get("words", []):
            texto = palabra.get("word", "").strip()
            segmentos.append(SegmentoFonetico(
                texto=texto,
                inicio_seg=palabra.get("start", 0.0),
                fin_seg=palabra.get("end", 0.0),
                confianza=palabra.get("probability", 0.0),
                fonemas=palabra_a_fonemas(texto),
            ))
    return segmentos

def evaluar_transcripcion(texto_esperado: str, resultado_whisper: dict) -> ResultadoPronunciacion:
    """Compara una transcripción de Whisper contra el texto esperado."""
    esperado_visible = normalizar(texto_esperado, quitar_tildes=False)
    detectado_visible = normalizar(_texto_detectado(resultado_whisper), quitar_tildes=False)
    esperado = normalizar(esperado_visible)
    detectado = normalizar(detectado_visible)

    if not esperado:
        word_error = char_error = 0.0 if not detectado else 1.0
    elif not detectado:
        word_error = char_error = 1.0
    else:
        word_error = wer(esperado, detectado)
        char_error = cer(esperado, detectado)

    puntaje = max(0.0, 1.0 - word_error)

    correctas, incorrectas = comparar_silabas(
        _silabas_de_texto(esperado_visible), _silabas_de_texto(detectado_visible)
    )

    fon_esp = palabra_a_fonemas(esperado)
    fon_det = palabra_a_fonemas(detectado)
    sim_fon = similitud_fonetica(fon_esp, fon_det)

    return ResultadoPronunciacion(
        texto_esperado=esperado_visible,
        texto_detectado=detectado_visible,
        puntaje_global=round(puntaje, 3),
        word_error_rate=round(word_error, 3),
        character_error_rate=round(char_error, 3),
        segmentos=_extraer_segmentos(resultado_whisper),
        silabas_incorrectas=incorrectas,
        silabas_correctas=correctas,
        similitud_fonetica_global=round(sim_fon, 3)
    )

def evaluar_fonema(fonema_esperado: str, resultado_whisper: dict) -> tuple[bool, float]:
    """Evalúa un fonema aislado a partir de la transcripción."""
    segmentos = _segmentos_con_habla(resultado_whisper)
    if not segmentos:
        return False, 0.0

    esperado = normalizar(fonema_esperado).replace(" ", "")
    texto = normalizar(" ".join(s.get("text", "") for s in segmentos)).replace(" ", "")
    if 'h' not in esperado:
        texto = texto.replace('h', '')
    texto = re.sub(r"(.)\1+", r"\1", texto)

    correcto = texto == esperado
    confianza = float(np.mean([np.exp(s.get("avg_logprob", -10.0)) for s in segmentos]))
    return correcto, round(min(1.0, max(0.0, confianza)), 3)

class STTFonetico:
    """Motor de inferencia Whisper para evaluación fonética."""
    def __init__(self, modelo_size: str = "base", device: Optional[str] = None):
        import torch
        import whisper
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.modelo = whisper.load_model(modelo_size, device=self.device)

    def transcribir(self, ruta_audio: str, idioma: str = "es") -> dict:
        return self.modelo.transcribe(
            ruta_audio,
            language=idioma,
            word_timestamps=True,
            task="transcribe",
            fp16=self.device == "cuda",
            condition_on_previous_text=False,
        )

    def analizar_pronunciacion(
        self, ruta_audio: str, texto_esperado: str, idioma: str = "es"
    ) -> ResultadoPronunciacion:
        return evaluar_transcripcion(texto_esperado, self.transcribir(ruta_audio, idioma))

    def evaluar_fonema_aislado(self, ruta_audio: str, fonema_esperado: str) -> tuple[bool, float]:
        return evaluar_fonema(fonema_esperado, self.transcribir(ruta_audio))
