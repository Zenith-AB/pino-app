# -*- coding: utf-8 -*-
"""
Pruebas de integración para los Endpoints de la API FastAPI (api/main.py).
Verifica contratos de Flutter, análisis de trazos, dificultad, PISA y macroeconomía.
"""

import pytest
from starlette.testclient import TestClient
from pino_ml.api.main import app

@pytest.fixture
def client():
    import pino_ml.api.main as api
    from pino_ml.models.clasificador_dificultad import ClasificadorDificultad
    if api.clasificador is None:
        try:
            api.clasificador = ClasificadorDificultad()
        except Exception:
            pass
    return TestClient(app)

def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "pino-ml-engine"

def test_siguiente_leccion_cold_start(client):
    payload = {
        "historial": [],
        "modo": "infantil",
        "nivel_actual": 1,
    }
    res = client.post("/predict/siguiente-leccion", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["siguiente_item_id"] == "a"
    assert "mensaje_pedagogico" in data

def test_dificultad_texto_endpoint(client):
    payload = {"texto": "El perro corre en el parque."}
    res = client.post("/predict/dificultad-texto", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "nivel_dificultad" in data
    assert "puntaje_legibilidad" in data
    assert "nivel_pisa_estimado" in data

def test_analyze_trazo_endpoint(client):
    payload = {
        "puntos": [[60, 270], [150, 30], [240, 270]],
        "letra_esperada": "A",
        "tolerancia": "media",
        "ancho_canvas": 300.0,
        "alto_canvas": 300.0,
    }
    res = client.post("/analyze/trazo", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["letra_detectada"] == "A"
    assert "porcentaje_dentro_margen" in data
    assert "tolerancia_sugerida" in data

def test_pisa_risk_endpoint(client):
    payload = {
        "tasa_acierto_fonemas": 0.85,
        "tasa_acierto_silabas": 0.80,
        "desviacion_promedio_trazo": 20.0,
        "cobertura_promedio_trazo": 0.90,
        "latencia_media_respuesta_seg": 2.0,
        "palabras_por_minuto": 50.0,
        "tasa_error_pronunciacion": 0.10,
        "dias_activos_racha": 7,
    }
    res = client.post("/predict/pisa-risk", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "puntaje_pisa_estimado" in data
    assert "probabilidad_bajo_nivel_2" in data
    assert "intervenciones_recomendadas" in data

def test_analytics_endpoints(client):
    # PISA History
    res_hist = client.get("/analytics/pisa-history?country=Chile")
    assert res_hist.status_code == 200
    assert len(res_hist.json()["history"]) > 0

    # PISA Levels
    res_lev = client.get("/analytics/pisa-levels")
    assert res_lev.status_code == 200
    assert len(res_lev.json()["levels"]) > 0

    # Chile Socioeconomic
    res_chi = client.get("/analytics/chile-socioeconomic")
    assert res_chi.status_code == 200
    assert "por_cuartil_escs" in res_chi.json()

    # Macro Opportunity
    res_mac = client.get("/analytics/macro-opportunity?top_n=5")
    assert res_mac.status_code == 200
    assert len(res_mac.json()["ranking"]) == 5
