# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el Motor de Riesgo PISA (pisa_risk_engine.py).
"""

import pytest
from pino_ml.models.pisa_risk_engine import PisaRiskEngine, TelemetriaUsuarioPino

@pytest.fixture
def pisa_engine():
    return PisaRiskEngine()

def test_estudiante_alto_rendimiento(pisa_engine):
    tel = TelemetriaUsuarioPino(
        tasa_acierto_fonemas=0.98,
        tasa_acierto_silabas=0.95,
        desviacion_promedio_trazo=12.0,
        cobertura_promedio_trazo=0.92,
        latencia_media_respuesta_seg=1.2,
        palabras_por_minuto=70.0,
        tasa_error_pronunciacion=0.05,
        dias_activos_racha=12,
    )
    pred = pisa_engine.evaluar_riesgo(tel)
    assert pred.puntaje_pisa_estimado >= 470.0 # Superior a la media OCDE
    assert pred.probabilidad_bajo_nivel_2 < 0.20 # Riesgo muy bajo
    assert pred.categoria_riesgo == "Bajo"

def test_estudiante_en_riesgo_analfabetismo_funcional(pisa_engine):
    tel = TelemetriaUsuarioPino(
        tasa_acierto_fonemas=0.45,
        tasa_acierto_silabas=0.40,
        desviacion_promedio_trazo=45.0,
        cobertura_promedio_trazo=0.55,
        latencia_media_respuesta_seg=4.5,
        palabras_por_minuto=15.0,
        tasa_error_pronunciacion=0.40,
        dias_activos_racha=1,
    )
    pred = pisa_engine.evaluar_riesgo(tel)
    assert pred.puntaje_pisa_estimado < 407.0 # Bajo Nivel 2
    assert pred.probabilidad_bajo_nivel_2 >= 0.60
    assert pred.categoria_riesgo in ("Alto", "Crítico")
    assert len(pred.intervenciones_recomendadas) >= 2
    assert pred.cuello_botella_cognitivo in [
        "Decodificación Fonológica",
        "Fluidez y Memoria de Trabajo",
        "Integración Grafomotora",
        "Frecuencia y Adherencia",
    ]
