# -*- coding: utf-8 -*-
"""
Módulo Clasificador de Dificultad de Textos en Español para Pino ML.
Evalúa legibilidad (Fernández-Huerta, Gutiérrez de Polini), complejidad léxica,
densidad silábica y correlaciona con la Escala de Competencia Lectora PISA (HU-04, HU-17).
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from pino_ml.utils.texto_es import contar_silabas, normalizar

@dataclass
class AnalisisTexto:
    texto: str
    nivel_dificultad: int               # 1 a 5
    etiqueta: str                       # "muy_facil", "facil", "medio", "dificil", "avanzado"
    puntaje_legibilidad: float          # Índice Fernández-Huerta (0 a 100+)
    indice_gutierrez: float             # Índice Gutiérrez de Polini
    promedio_largo_palabra: float
    promedio_largo_oracion: float
    total_palabras: int
    total_oraciones: int
    palabras_complejas: list[str]       # Palabras >= 4 sílabas
    silabas_por_palabra: float
    vocabulario_unico_ratio: float      # Type-token ratio
    nivel_pisa_estimado: str            # "Bajo Nivel 1b", "Nivel 1a", "Nivel 2 (Mínimo)", "Nivel 3", "Nivel 4+"

ETIQUETAS_NIVEL = {
    1: "muy_facil",
    2: "facil",
    3: "medio",
    4: "dificil",
    5: "avanzado",
}

class ClasificadorDificultad:
    """Clasificador de legibilidad adaptada para alfabetización infantil y de adultos."""

    def __init__(self, modelo_spacy: str = "es_core_news_md"):
        import spacy
        try:
            self.nlp = spacy.load(modelo_spacy)
        except Exception:
            # Fallback en caso de que el modelo en disco tarde en cargar
            self.nlp = spacy.blank("es")
            if "sentencizer" not in self.nlp.pipe_names:
                self.nlp.add_pipe("sentencizer")

        self.umbral_silabas_compleja = 4

    def _contar_silabas(self, palabra: str) -> int:
        return contar_silabas(palabra)

    def _indice_fernandez_huerta(self, total_palabras: int, total_oraciones: int, total_silabas: int) -> float:
        """
        Fórmula de Fernández-Huerta (adaptación española de Flesch):
        L = 206.84 - 0.60 * P - 1.02 * F
        P: sílabas por 100 palabras = (total_silabas / total_palabras) * 100
        F: palabras por oración = total_palabras / total_oraciones
        """
        if total_palabras == 0 or total_oraciones == 0:
            return 100.0
        P = (total_silabas / total_palabras) * 100.0
        F = total_palabras / total_oraciones
        return 206.84 - (0.60 * P) - (1.02 * F)

    def _indice_gutierrez_polini(self, total_palabras: int, total_oraciones: int, total_letras: int) -> float:
        """
        Fórmula de Gutiérrez de Polini:
        I_GP = 95.2 - 9.7 * (total_letras / total_palabras) - 0.35 * (total_palabras / total_oraciones)
        > 40: Muy fácil / accesible para primeros lectores
        30 - 40: Adecuado para educación primaria
        < 30: Complejidad alta
        """
        if total_palabras == 0 or total_oraciones == 0:
            return 80.0
        letras_por_palabra = total_letras / total_palabras
        palabras_por_oracion = total_palabras / total_oraciones
        return 95.2 - (9.7 * letras_por_palabra) - (0.35 * palabras_por_oracion)

    def _clasificar_nivel(
        self,
        puntaje_legibilidad: float,
        promedio_largo_palabra: float,
        promedio_largo_oracion: float,
        silabas_por_palabra: float,
        total_palabras: int,
        ratio_complejas: float,
    ) -> int:
        # Nivel 1: Palabras muy cortas, frases mínimas
        if puntaje_legibilidad >= 90 and total_palabras <= 6 and ratio_complejas == 0:
            return 1
        elif puntaje_legibilidad >= 80 and promedio_largo_oracion <= 7:
            return 2
        elif puntaje_legibilidad >= 65 and promedio_largo_oracion <= 12:
            return 3
        elif puntaje_legibilidad >= 50 or ratio_complejas <= 0.15:
            return 4
        return 5

    def _estimar_nivel_pisa(self, nivel: int, legibilidad: float) -> str:
        if nivel == 1:
            return "Bajo Nivel 1c (Pre-lector)"
        elif nivel == 2:
            return "Nivel 1b (Decodificación Básica)"
        elif nivel == 3:
            return "Nivel 1a (Comprensión Literal)"
        elif nivel == 4:
            return "Nivel 2 (Umbral Mínimo Funcional PISA)"
        return "Nivel 3+ (Comprensión Inferencial y Crítica)"

    def analizar(self, texto: str) -> AnalisisTexto:
        doc = self.nlp(texto)

        palabras = [token.text for token in doc if token.is_alpha]
        oraciones = list(doc.sents)
        total_palabras = len(palabras)
        total_oraciones = max(1, len(oraciones))

        promedio_largo_palabra = np.mean([len(p) for p in palabras]) if palabras else 0.0
        promedio_largo_oracion = total_palabras / total_oraciones

        total_letras = sum(len(p) for p in palabras)
        silabas_total = sum(self._contar_silabas(p) for p in palabras)
        silabas_por_palabra = silabas_total / max(1, total_palabras)

        puntaje_legibilidad = self._indice_fernandez_huerta(
            total_palabras, total_oraciones, silabas_total
        )
        indice_gutierrez = self._indice_gutierrez_polini(
            total_palabras, total_oraciones, total_letras
        )

        palabras_lower = [p.lower() for p in palabras]
        vocabulario_unico = len(set(palabras_lower)) / max(1, len(palabras_lower))

        palabras_complejas = [
            p for p in set(palabras_lower)
            if self._contar_silabas(p) >= self.umbral_silabas_compleja
        ]

        nivel = self._clasificar_nivel(
            puntaje_legibilidad=puntaje_legibilidad,
            promedio_largo_palabra=promedio_largo_palabra,
            promedio_largo_oracion=promedio_largo_oracion,
            silabas_por_palabra=silabas_por_palabra,
            total_palabras=total_palabras,
            ratio_complejas=len(palabras_complejas) / max(1, total_palabras),
        )

        pisa_nivel = self._estimar_nivel_pisa(nivel, puntaje_legibilidad)

        return AnalisisTexto(
            texto=texto,
            nivel_dificultad=nivel,
            etiqueta=ETIQUETAS_NIVEL[nivel],
            puntaje_legibilidad=round(float(puntaje_legibilidad), 2),
            indice_gutierrez=round(float(indice_gutierrez), 2),
            promedio_largo_palabra=round(float(promedio_largo_palabra), 2),
            promedio_largo_oracion=round(float(promedio_largo_oracion), 2),
            total_palabras=total_palabras,
            total_oraciones=total_oraciones,
            palabras_complejas=sorted(palabras_complejas),
            silabas_por_palabra=round(float(silabas_por_palabra), 2),
            vocabulario_unico_ratio=round(float(vocabulario_unico), 3),
            nivel_pisa_estimado=pisa_nivel,
        )
