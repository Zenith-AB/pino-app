# -*- coding: utf-8 -*-
"""
Motor Predictivo de Riesgo PISA y Analfabetismo Funcional para Pino ML.
Correlaciona la micro-telemetría de aprendizaje de Pino (conciencia fonológica,
trazado grafomotor, decodificación silábica y fluidez) con el rendimiento proyectado
en la escala de comprensión lectora PISA de la OCDE (Umbral Nivel 2: 407 puntos).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import numpy as np

from pino_ml.settings import settings
from pino_ml.utils.pisa_data_loader import pisa_data

@dataclass
class TelemetriaUsuarioPino:
    """Micro-telemetría capturada por la aplicación durante los ejercicios."""
    tasa_acierto_fonemas: float          # 0.0 a 1.0 (ejercicios HU-03)
    tasa_acierto_silabas: float          # 0.0 a 1.0 (matching silábico)
    desviacion_promedio_trazo: float      # Píxeles promedio (HU-02)
    cobertura_promedio_trazo: float       # 0.0 a 1.0
    latencia_media_respuesta_seg: float  # Segundos en responder
    palabras_por_minuto: float           # Fluidez de lectura en voz alta (HU-06)
    tasa_error_pronunciacion: float      # WER en lectura
    dias_activos_racha: int              # Adherencia y constancia

@dataclass
class PrediccionRiesgoPisa:
    """Diagnóstico predictivo del desempeño en la escala PISA."""
    puntaje_pisa_estimado: float         # Escala PISA (200 a 600)
    nivel_competencia_pisa: str          # "Bajo Nivel 1b", "Nivel 1a", "Nivel 2", "Nivel 3", etc.
    probabilidad_bajo_nivel_2: float     # Riesgo de analfabetismo funcional (0.0 a 1.0)
    categoria_riesgo: str                # "Bajo", "Moderado", "Alto", "Crítico"
    diferencia_con_media_chile: float    # Comparación con 448 pts
    diferencia_con_media_ocde: float     # Comparación con 476 pts
    cuello_botella_cognitivo: str        # Factor limitante primario
    desglose_componentes: Dict[str, float]
    intervenciones_recomendadas: List[str]

class PisaRiskEngine:
    """
    Motor inferencial que conecta la automatización fonológica temprana
    con la capacidad de procesamiento de textos según el modelo neurocognitivo
    de Doble Ruta y el Modelo Simple de Lectura (Gough & Tunmer).
    """

    PISA_UMBRAL_NIVEL_2 = 407.0   # Umbral OCDE de alfabetización funcional
    CHILE_MEDIA_PISA = 448.0      # PISA 2022 Chile
    OCDE_MEDIA_PISA = 476.0       # PISA 2022 OCDE

    def __init__(self):
        # Coeficientes empíricos basados en investigaciones psicométricas de lectura:
        # - Decodificación fonológica automatizada: 35% del peso predictivo
        # - Fluidez lectora (WPM / baja latencia): 30%
        # - Integración grafomotora (trazado preciso): 20%
        # - Consistencia / Repetición espaciada (adherencia): 15%
        self.pesos = {
            'fonologia': 0.35,
            'fluidez': 0.30,
            'grafomotricidad': 0.20,
            'adherencia': 0.15,
        }

    def _calcular_score_fonologico(self, tel: TelemetriaUsuarioPino) -> float:
        # Score normalizado de 0 a 100
        base = (tel.tasa_acierto_fonemas * 0.5 + tel.tasa_acierto_silabas * 0.5) * 100.0
        penalizacion_wer = tel.tasa_error_pronunciacion * 30.0
        return float(np.clip(base - penalizacion_wer, 0.0, 100.0))

    def _calcular_score_fluidez(self, tel: TelemetriaUsuarioPino) -> float:
        # 60 palabras por minuto es el estándar de fluidez básica en primer ciclo
        wpm_score = min(100.0, (tel.palabras_por_minuto / 60.0) * 100.0)
        # Latencia ideal <= 2 segundos
        lat_score = max(0.0, 100.0 - (tel.latencia_media_respuesta_seg - 2.0) * 20.0)
        return float(np.clip(wpm_score * 0.6 + lat_score * 0.4, 0.0, 100.0))

    def _calcular_score_grafomotor(self, tel: TelemetriaUsuarioPino) -> float:
        # Desviación ideal <= 20 px, cobertura >= 0.85
        cob_score = tel.cobertura_promedio_trazo * 100.0
        desv_score = max(0.0, 100.0 - (tel.desviacion_promedio_trazo / 40.0) * 100.0)
        return float(np.clip(cob_score * 0.6 + desv_score * 0.4, 0.0, 100.0))

    def _calcular_score_adherencia(self, tel: TelemetriaUsuarioPino) -> float:
        # Racha de 14 días = 100% de adherencia
        return float(np.clip((tel.dias_activos_racha / 14.0) * 100.0, 0.0, 100.0))

    def evaluar_riesgo(self, tel: TelemetriaUsuarioPino) -> PrediccionRiesgoPisa:
        s_fon = self._calcular_score_fonologico(tel)
        s_flu = self._calcular_score_fluidez(tel)
        s_gra = self._calcular_score_grafomotor(tel)
        s_adh = self._calcular_score_adherencia(tel)

        indice_global = (
            s_fon * self.pesos['fonologia'] +
            s_flu * self.pesos['fluidez'] +
            s_gra * self.pesos['grafomotricidad'] +
            s_adh * self.pesos['adherencia']
        )

        # Mapeo a escala PISA (rango típico: 280 pts a 560 pts)
        # 0 en índice -> ~280 pts (Bajo Nivel 1c)
        # 50 en índice -> ~415 pts (Nivel 2 justo sobre el umbral)
        # 100 en índice -> ~550 pts (Nivel 4-5 excelencia)
        puntaje_pisa = 280.0 + (indice_global / 100.0) * 270.0

        # Probabilidad logística de quedar bajo Nivel 2 (< 407 pts)
        # Sigmoide centrada en 407 puntos
        z = (self.PISA_UMBRAL_NIVEL_2 - puntaje_pisa) / 25.0
        prob_bajo_nivel_2 = float(1.0 / (1.0 + np.exp(-z)))

        # Clasificación de categoría y nivel PISA
        if prob_bajo_nivel_2 >= 0.70:
            cat_riesgo = "Crítico"
        elif prob_bajo_nivel_2 >= 0.45:
            cat_riesgo = "Alto"
        elif prob_bajo_nivel_2 >= 0.20:
            cat_riesgo = "Moderado"
        else:
            cat_riesgo = "Bajo"

        if puntaje_pisa < 335:
            nivel_pisa = "Bajo Nivel 1b (Analfabetismo Funcional Severo)"
        elif puntaje_pisa < 407:
            nivel_pisa = "Nivel 1a (Analfabetismo Funcional Leve)"
        elif puntaje_pisa < 480:
            nivel_pisa = "Nivel 2 (Alfabetización Funcional Básica)"
        elif puntaje_pisa < 552:
            nivel_pisa = "Nivel 3 (Comprensión Autónoma)"
        else:
            nivel_pisa = "Nivel 4+ (Lectura Crítica Avanzada)"

        # Diagnóstico de cuello de botella cognitivo
        scores_map = {
            "Decodificación Fonológica": s_fon,
            "Fluidez y Memoria de Trabajo": s_flu,
            "Integración Grafomotora": s_gra,
            "Frecuencia y Adherencia": s_adh,
        }
        cuello_botella = min(scores_map.items(), key=lambda x: x[1])[0]

        # Intervenciones pedagógicas personalizadas
        intervenciones = []
        if s_fon < 60:
            intervenciones.append("Reforzar discriminación auditiva de fonemas mínimos (ej. p/b, d/t) en modo asistido.")
            intervenciones.append("Aumentar repeticiones de sílabas trabadas y compuestas antes de textos largos.")
        if s_flu < 60:
            intervenciones.append("Implementar sesiones cortas de lectura en voz alta con Tap-to-Speech inmediato para reducir sobrecarga cognitiva.")
        if s_gra < 60:
            intervenciones.append("Ajustar tolerancia de trazo a 'alta' e incrementar guías visuales con flechas animadas.")
        if s_adh < 50:
            intervenciones.append("Activar notificaciones motivacionales y micro-sesiones de 5 minutos diarios para afianzar retención SM-2.")

        if not intervenciones:
            intervenciones.append("Progresión óptima. Pasar a desafíos de textos nivel 4 con preguntas de inferencia.")

        return PrediccionRiesgoPisa(
            puntaje_pisa_estimado=round(puntaje_pisa, 1),
            nivel_competencia_pisa=nivel_pisa,
            probabilidad_bajo_nivel_2=round(prob_bajo_nivel_2, 3),
            categoria_riesgo=cat_riesgo,
            diferencia_con_media_chile=round(puntaje_pisa - self.CHILE_MEDIA_PISA, 1),
            diferencia_con_media_ocde=round(puntaje_pisa - self.OCDE_MEDIA_PISA, 1),
            cuello_botella_cognitivo=cuello_botella,
            desglose_componentes={
                "score_fonologico": round(s_fon, 1),
                "score_fluidez": round(s_flu, 1),
                "score_grafomotor": round(s_gra, 1),
                "score_adherencia": round(s_adh, 1),
            },
            intervenciones_recomendadas=intervenciones,
        )

# Instancia singleton
pisa_risk_engine = PisaRiskEngine()
