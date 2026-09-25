"""
Modelo 1: Speech-to-Text Fonético para español.

Usa Whisper (OpenAI) fine-tuneado para:
- Transcribir audio del usuario a texto
- Extraer fonemas individuales con timestamps
- Calcular confianza por segmento para feedback específico

Usado en: HU-06 (Lectura en voz alta con feedback en tiempo real)
"""

import numpy as np
import torch
import whisper
import librosa
from dataclasses import dataclass
from typing import Optional

from jiwer import wer, cer


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


class STTFonetico:
    """
    Motor de Speech-to-Text fonético para español.
    Analiza la pronunciación del usuario y genera feedback detallado.
    """

    def __init__(self, modelo_size: str = "medium", device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.modelo = whisper.load_model(modelo_size, device=self.device)

        # Mapa de fonemas del español
        self.fonemas_espanol = {
            'a': '/a/', 'e': '/e/', 'i': '/i/', 'o': '/o/', 'u': '/u/',
            'b': '/b/', 'c': '/k/', 'd': '/d/', 'f': '/f/', 'g': '/g/',
            'j': '/x/', 'k': '/k/', 'l': '/l/', 'm': '/m/', 'n': '/n/',
            'ñ': '/ɲ/', 'p': '/p/', 'r': '/ɾ/', 's': '/s/', 't': '/t/',
            'v': '/b/', 'x': '/ks/', 'y': '/ʝ/', 'z': '/s/',
            'ch': '/tʃ/', 'll': '/ʝ/', 'rr': '/r/', 'gu': '/g/', 'qu': '/k/',
        }

    def transcribir(self, ruta_audio: str) -> dict:
        """Transcribe un archivo de audio a texto con timestamps."""
        resultado = self.modelo.transcribe(
            ruta_audio,
            language="es",
            word_timestamps=True,
            task="transcribe",
        )
        return resultado

    def analizar_pronunciacion(
        self,
        ruta_audio: str,
        texto_esperado: str,
    ) -> ResultadoPronunciacion:
        """
        Compara la pronunciación del usuario contra el texto esperado.
        Retorna un análisis detallado con las sílabas correctas e incorrectas.
        """
        # Transcribir el audio del usuario
        resultado_whisper = self.transcribir(ruta_audio)
        texto_detectado = resultado_whisper["text"].strip().lower()
        texto_esperado_norm = texto_esperado.strip().lower()

        # Calcular métricas de error
        word_error = wer(texto_esperado_norm, texto_detectado)
        char_error = cer(texto_esperado_norm, texto_detectado)

        # Puntaje global (invertido: menor error = mayor puntaje)
        puntaje = max(0.0, 1.0 - word_error)

        # Extraer segmentos con timestamps
        segmentos = self._extraer_segmentos(resultado_whisper)

        # Comparar sílabas
        silabas_esperadas = self._separar_silabas(texto_esperado_norm)
        silabas_detectadas = self._separar_silabas(texto_detectado)

        correctas, incorrectas = self._comparar_silabas(
            silabas_esperadas, silabas_detectadas
        )

        return ResultadoPronunciacion(
            texto_esperado=texto_esperado_norm,
            texto_detectado=texto_detectado,
            puntaje_global=round(puntaje, 3),
            word_error_rate=round(word_error, 3),
            character_error_rate=round(char_error, 3),
            segmentos=segmentos,
            silabas_incorrectas=incorrectas,
            silabas_correctas=correctas,
        )

    def _extraer_segmentos(self, resultado_whisper: dict) -> list[SegmentoFonetico]:
        """Extrae segmentos fonéticos con timestamps del resultado de Whisper."""
        segmentos = []

        for segmento in resultado_whisper.get("segments", []):
            palabras = segmento.get("words", [])
            for palabra in palabras:
                fonemas = self._palabra_a_fonemas(palabra.get("word", ""))
                segmentos.append(SegmentoFonetico(
                    texto=palabra.get("word", "").strip(),
                    inicio_seg=palabra.get("start", 0.0),
                    fin_seg=palabra.get("end", 0.0),
                    confianza=palabra.get("probability", 0.0),
                    fonemas=fonemas,
                ))

        return segmentos

    def _palabra_a_fonemas(self, palabra: str) -> list[str]:
        """Convierte una palabra a su representación fonémica."""
        fonemas = []
        palabra = palabra.lower().strip()
        i = 0

        while i < len(palabra):
            # Verificar dígrafos primero (ch, ll, rr, gu, qu)
            if i + 1 < len(palabra):
                digrafo = palabra[i:i+2]
                if digrafo in self.fonemas_espanol:
                    fonemas.append(self.fonemas_espanol[digrafo])
                    i += 2
                    continue

            # Consonante o vocal simple
            char = palabra[i]
            if char in self.fonemas_espanol:
                fonemas.append(self.fonemas_espanol[char])
            i += 1

        return fonemas

    def _separar_silabas(self, texto: str) -> list[str]:
        """
        Separación silábica básica del español.
        Para producción, usar Pyphen o un modelo más sofisticado.
        """
        # Separación simplificada por vocales como núcleos silábicos
        vocales = set('aeiouáéíóúü')
        silabas = []
        silaba_actual = ""

        for i, char in enumerate(texto):
            if char == ' ':
                if silaba_actual:
                    silabas.append(silaba_actual)
                    silaba_actual = ""
                continue

            silaba_actual += char

            # Si el siguiente caracter es vocal y el actual es vocal,
            # cerrar sílaba (simplificación)
            if (char in vocales and
                i + 1 < len(texto) and
                texto[i + 1] not in vocales and
                texto[i + 1] != ' ' and
                i + 2 < len(texto) and
                texto[i + 2] in vocales):
                silabas.append(silaba_actual)
                silaba_actual = ""

        if silaba_actual:
            silabas.append(silaba_actual)

        return silabas

    def _comparar_silabas(
        self,
        esperadas: list[str],
        detectadas: list[str],
    ) -> tuple[list[str], list[str]]:
        """Compara sílabas esperadas vs detectadas."""
        correctas = []
        incorrectas = []

        for i, silaba in enumerate(esperadas):
            if i < len(detectadas) and silaba == detectadas[i]:
                correctas.append(silaba)
            else:
                incorrectas.append(silaba)

        return correctas, incorrectas

    def evaluar_fonema_aislado(
        self,
        ruta_audio: str,
        fonema_esperado: str,
    ) -> tuple[bool, float]:
        """
        Evalúa si el usuario pronunció correctamente un fonema aislado.
        Retorna (correcto, confianza).
        Usado para HU-03.
        """
        resultado = self.transcribir(ruta_audio)
        texto = resultado["text"].strip().lower()

        # Comparar fonema
        correcto = fonema_esperado.lower() in texto
        confianza = resultado["segments"][0].get("avg_logprob", -1.0) if resultado["segments"] else 0.0

        # Convertir log-prob a probabilidad
        confianza_norm = min(1.0, max(0.0, np.exp(confianza)))

        return correcto, round(confianza_norm, 3)
