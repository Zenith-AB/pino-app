"""
Modelo 1: Speech-to-Text Fonético para español.

Usa Whisper (OpenAI, sin ajuste fino) para:
- Transcribir audio del usuario a texto
- Convertir la transcripción a fonemas con timestamps por palabra
- Comparar sílaba a sílaba contra el texto esperado

Limitación importante: Whisper es un modelo de lenguaje que tiende a
"corregir" lo que oye hacia palabras reales, así que puede no detectar
errores de pronunciación (sobre todo en niños). Para evaluar pronunciación
de verdad hace falta un reconocedor fonético o alineamiento forzado.

Usado en: HU-06 (Lectura en voz alta con feedback)
"""

import difflib
import re
from dataclasses import dataclass
from typing import Optional

import numpy as np
from jiwer import cer, wer

from pino_ml.utils.texto_es import normalizar, palabra_a_fonemas, separar_silabas

# Si Whisper estima que no hubo habla con esta probabilidad o más, se descarta
# el segmento (evita "alucinaciones" sobre silencio o ruido).
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
    Alinea las sílabas esperadas con las detectadas (como un diff) y devuelve
    (correctas, incorrectas). Una sílaba repetida u omitida no desplaza al
    resto: "la-ca-sa" leído como "la-la-ca-sa" sigue marcando ca y sa como
    correctas.
    """
    matcher = difflib.SequenceMatcher(a=esperadas, b=detectadas, autojunk=False)
    acertadas = set()
    for bloque in matcher.get_matching_blocks():
        acertadas.update(range(bloque.a, bloque.a + bloque.size))

    correctas = [s for i, s in enumerate(esperadas) if i in acertadas]
    incorrectas = [s for i, s in enumerate(esperadas) if i not in acertadas]
    return correctas, incorrectas


def evaluar_transcripcion(texto_esperado: str, resultado_whisper: dict) -> ResultadoPronunciacion:
    """Compara una transcripción de Whisper contra el texto esperado."""
    esperado = normalizar(texto_esperado)
    detectado = normalizar(_texto_detectado(resultado_whisper))

    if not esperado:
        word_error = char_error = 0.0 if not detectado else 1.0
    elif not detectado:
        word_error = char_error = 1.0
    else:
        word_error = wer(esperado, detectado)
        char_error = cer(esperado, detectado)

    # Puntaje global (invertido: menor error = mayor puntaje)
    puntaje = max(0.0, 1.0 - word_error)

    correctas, incorrectas = comparar_silabas(
        _silabas_de_texto(esperado), _silabas_de_texto(detectado)
    )

    return ResultadoPronunciacion(
        texto_esperado=esperado,
        texto_detectado=detectado,
        puntaje_global=round(puntaje, 3),
        word_error_rate=round(word_error, 3),
        character_error_rate=round(char_error, 3),
        segmentos=_extraer_segmentos(resultado_whisper),
        silabas_incorrectas=incorrectas,
        silabas_correctas=correctas,
    )


def evaluar_fonema(fonema_esperado: str, resultado_whisper: dict) -> tuple[bool, float]:
    """
    Evalúa un fonema aislado a partir de la transcripción: es correcto si lo
    que se transcribió, sin letras repetidas ni h muda ("Mmm." → "m",
    "Ah" → "a"), coincide exactamente con el fonema esperado.
    Retorna (correcto, confianza).
    """
    segmentos = _segmentos_con_habla(resultado_whisper)
    if not segmentos:
        return False, 0.0

    esperado = normalizar(fonema_esperado).replace(" ", "")
    texto = normalizar(" ".join(s.get("text", "") for s in segmentos)).replace(" ", "")
    if 'h' not in esperado:
        texto = texto.replace('h', '')
    texto = re.sub(r"(.)\1+", r"\1", texto)  # "aaa" → "a", "mmm" → "m"

    correcto = texto == esperado

    # Probabilidad media de los segmentos (avg_logprob es un log)
    confianza = float(np.mean([np.exp(s.get("avg_logprob", -10.0)) for s in segmentos]))
    return correcto, round(min(1.0, max(0.0, confianza)), 3)


def _extraer_segmentos(resultado_whisper: dict) -> list[SegmentoFonetico]:
    """Extrae segmentos fonéticos por palabra con timestamps."""
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


class STTFonetico:
    """
    Motor de Speech-to-Text fonético para español.
    Analiza la pronunciación del usuario y genera feedback detallado.
    """

    def __init__(self, modelo_size: str = "medium", device: Optional[str] = None):
        # Imports locales: torch y whisper son pesados y solo se necesitan aquí.
        import torch
        import whisper

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.modelo = whisper.load_model(modelo_size, device=self.device)

    def transcribir(self, ruta_audio: str) -> dict:
        """Transcribe un archivo de audio a texto con timestamps."""
        return self.modelo.transcribe(
            ruta_audio,
            language="es",
            word_timestamps=True,
            task="transcribe",
            fp16=self.device == "cuda",
            # Cada audio es independiente: no arrastrar contexto entre segmentos
            condition_on_previous_text=False,
        )

    def analizar_pronunciacion(
        self,
        ruta_audio: str,
        texto_esperado: str,
    ) -> ResultadoPronunciacion:
        """
        Compara la pronunciación del usuario contra el texto esperado.
        Retorna un análisis detallado con las sílabas correctas e incorrectas.
        """
        return evaluar_transcripcion(texto_esperado, self.transcribir(ruta_audio))

    def evaluar_fonema_aislado(
        self,
        ruta_audio: str,
        fonema_esperado: str,
    ) -> tuple[bool, float]:
        """
        Evalúa si el usuario pronunció correctamente un fonema aislado.
        Retorna (correcto, confianza). Usado para HU-03.
        """
        return evaluar_fonema(fonema_esperado, self.transcribir(ruta_audio))
