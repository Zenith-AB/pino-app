"""
Modelo 3: Clasificador de dificultad de textos en español.

Analiza textos y los clasifica en niveles de dificultad lectora:
- Nivel 1: Palabras aisladas (3-4 letras)
- Nivel 2: Frases simples (sujeto + verbo)
- Nivel 3: Oraciones compuestas
- Nivel 4: Párrafos con vocabulario cotidiano
- Nivel 5: Textos con inferencia y vocabulario técnico

Usado en: HU-04 (Lectura guiada), HU-17 (Micro-historias)
"""

from dataclasses import dataclass

import numpy as np

from pino_ml.utils.texto_es import contar_silabas


@dataclass
class AnalisisTexto:
    """Resultado del análisis de dificultad de un texto."""
    texto: str
    nivel_dificultad: int               # 1 a 5
    etiqueta: str                       # "muy_facil", "facil", "medio", "dificil", "avanzado"
    puntaje_legibilidad: float          # Índice Fernández-Huerta
    promedio_largo_palabra: float
    promedio_largo_oracion: float
    total_palabras: int
    total_oraciones: int
    palabras_complejas: list[str]       # Palabras que necesitan definición
    silabas_por_palabra: float
    vocabulario_unico_ratio: float      # Type-token ratio


ETIQUETAS_NIVEL = {
    1: "muy_facil",
    2: "facil",
    3: "medio",
    4: "dificil",
    5: "avanzado",
}


class ClasificadorDificultad:
    """
    Clasifica textos en español por nivel de dificultad lectora.
    Combina métricas lingüísticas con un modelo ML para mayor precisión.
    """

    def __init__(self, modelo_spacy: str = "es_core_news_md"):
        # Import local: spaCy es pesado y solo se necesita al usar el clasificador.
        # El modelo se instala aparte: python -m spacy download es_core_news_md
        import spacy

        self.nlp = spacy.load(modelo_spacy)
        self.modelo_ml = None

        # Umbral de sílabas para considerar una palabra "compleja"
        self.umbral_silabas_compleja = 4

    def analizar(self, texto: str) -> AnalisisTexto:
        """Analiza un texto y retorna sus métricas de dificultad."""
        doc = self.nlp(texto)

        # Métricas básicas
        palabras = [token.text for token in doc if token.is_alpha]
        oraciones = list(doc.sents)
        total_palabras = len(palabras)
        total_oraciones = max(1, len(oraciones))

        # Largo promedio
        promedio_largo_palabra = np.mean([len(p) for p in palabras]) if palabras else 0
        promedio_largo_oracion = total_palabras / total_oraciones

        # Sílabas
        silabas_total = sum(self._contar_silabas(p) for p in palabras)
        silabas_por_palabra = silabas_total / max(1, total_palabras)

        # Legibilidad (Fernández-Huerta para español)
        puntaje_legibilidad = self._indice_fernandez_huerta(
            total_palabras, total_oraciones, silabas_total
        )

        # Vocabulario único (type-token ratio)
        palabras_lower = [p.lower() for p in palabras]
        vocabulario_unico = len(set(palabras_lower)) / max(1, len(palabras_lower))

        # Palabras complejas
        palabras_complejas = [
            p for p in set(palabras_lower)
            if self._contar_silabas(p) >= self.umbral_silabas_compleja
        ]

        # Clasificar nivel
        nivel = self._clasificar_nivel(
            puntaje_legibilidad=puntaje_legibilidad,
            promedio_largo_palabra=promedio_largo_palabra,
            promedio_largo_oracion=promedio_largo_oracion,
            silabas_por_palabra=silabas_por_palabra,
            total_palabras=total_palabras,
            ratio_complejas=len(palabras_complejas) / max(1, total_palabras),
        )

        return AnalisisTexto(
            texto=texto,
            nivel_dificultad=nivel,
            etiqueta=ETIQUETAS_NIVEL[nivel],
            puntaje_legibilidad=round(puntaje_legibilidad, 2),
            promedio_largo_palabra=round(promedio_largo_palabra, 2),
            promedio_largo_oracion=round(promedio_largo_oracion, 2),
            total_palabras=total_palabras,
            total_oraciones=total_oraciones,
            palabras_complejas=sorted(palabras_complejas),
            silabas_por_palabra=round(silabas_por_palabra, 2),
            vocabulario_unico_ratio=round(vocabulario_unico, 3),
        )

    def _indice_fernandez_huerta(
        self,
        palabras: int,
        oraciones: int,
        silabas: int,
    ) -> float:
        """
        Índice de legibilidad Fernández-Huerta (adaptación del Flesch para español).
        Rango: 0-100 (mayor = más fácil de leer).
        """
        if palabras == 0 or oraciones == 0:
            return 100.0

        P = palabras / oraciones          # Promedio palabras por oración
        S = silabas / palabras * 100      # Promedio sílabas por 100 palabras

        return 206.84 - (0.60 * S) - (1.02 * P)

    def _contar_silabas(self, palabra: str) -> int:
        """Cuenta sílabas de una palabra en español (respeta hiatos: dí-a, po-e-ta)."""
        return contar_silabas(palabra)

    def _clasificar_nivel(
        self,
        puntaje_legibilidad: float,
        promedio_largo_palabra: float,
        promedio_largo_oracion: float,
        silabas_por_palabra: float,
        total_palabras: int,
        ratio_complejas: float,
    ) -> int:
        """Clasifica el nivel de dificultad usando reglas + modelo ML."""

        # Si hay modelo ML entrenado, usarlo
        if self.modelo_ml:
            features = np.array([[
                puntaje_legibilidad, promedio_largo_palabra,
                promedio_largo_oracion, silabas_por_palabra,
                total_palabras, ratio_complejas,
            ]])
            return int(self.modelo_ml.predict(features)[0])

        # Heurística basada en Fernández-Huerta
        if puntaje_legibilidad >= 90 or total_palabras <= 5:
            return 1  # Muy fácil: palabras sueltas
        elif puntaje_legibilidad >= 75 or total_palabras <= 15:
            return 2  # Fácil: frases simples
        elif puntaje_legibilidad >= 55:
            return 3  # Medio: oraciones compuestas
        elif puntaje_legibilidad >= 35:
            return 4  # Difícil: párrafos
        else:
            return 5  # Avanzado: textos complejos

    def obtener_palabras_clickeables(self, texto: str) -> list[dict]:
        """
        Identifica palabras que deberían ser clickeables para
        mostrar definición contextual (HU-04, HU-14).
        """
        doc = self.nlp(texto)
        clickeables = []

        for token in doc:
            if not token.is_alpha or token.is_stop:
                continue

            silabas = self._contar_silabas(token.text)
            if silabas >= 3 or token.pos_ in ('NOUN', 'VERB', 'ADJ'):
                clickeables.append({
                    'palabra': token.text,
                    'lema': token.lemma_,
                    'pos': token.pos_,
                    'silabas': silabas,
                    'inicio': token.idx,
                    'fin': token.idx + len(token.text),
                })

        return clickeables

    def adaptar_texto_a_nivel(
        self,
        texto: str,
        nivel_objetivo: int,
    ) -> dict:
        """
        Sugiere cómo adaptar un texto al nivel objetivo.
        Retorna métricas actuales y sugerencias.
        """
        analisis = self.analizar(texto)

        sugerencias = []
        if analisis.nivel_dificultad > nivel_objetivo:
            if analisis.promedio_largo_oracion > 10:
                sugerencias.append("Dividir oraciones largas en frases más cortas")
            if analisis.palabras_complejas:
                sugerencias.append(
                    f"Simplificar palabras: {', '.join(analisis.palabras_complejas[:5])}"
                )
            if analisis.silabas_por_palabra > 2.5:
                sugerencias.append("Usar palabras con menos sílabas")

        return {
            'nivel_actual': analisis.nivel_dificultad,
            'nivel_objetivo': nivel_objetivo,
            'requiere_adaptacion': analisis.nivel_dificultad != nivel_objetivo,
            'sugerencias': sugerencias,
            'analisis': analisis,
        }
