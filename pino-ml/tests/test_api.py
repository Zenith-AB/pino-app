"""
Tests de la API. Whisper y spaCy no se cargan: se reemplazan por dobles
(o quedan como no disponibles) para probar la API sin los modelos pesados.
"""

import pytest
from fastapi.testclient import TestClient

import pino_ml.api.main as api
from pino_ml.models.stt_fonetico import evaluar_transcripcion


class STTFalso:
    idiomas: list[str] = []

    def analizar_pronunciacion(self, ruta_audio, texto_esperado, idioma="es"):
        self.idiomas.append(idioma)
        return evaluar_transcripcion(texto_esperado, {
            "segments": [{"text": " Mamá.", "no_speech_prob": 0.0, "words": []}]
        })


class EdadFalsa:
    def analizar(self, palabra, idioma="es", traduccion=None):
        if " " in palabra:
            raise ValueError("Se espera una sola palabra")
        return {"palabra": palabra, "idioma": idioma, "nivel": 1}


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(api, "EdadAdquisicion", EdadFalsa)
    # Evita cargar Whisper y spaCy al arrancar
    monkeypatch.setattr(api, "STTFonetico", lambda **_: STTFalso())
    monkeypatch.setattr(api, "ClasificadorDificultad", lambda **_: (_ for _ in ()).throw(OSError("sin spaCy")))
    with TestClient(api.app) as c:
        yield c


def test_health_reporta_modelos(cliente):
    modelos = cliente.get("/health").json()["modelos_cargados"]
    assert modelos == {"stt": True, "adaptativo": True, "clasificador": False, "analizador": True,
                       "edad_adquisicion": True}


def test_modelo_no_disponible_responde_503(cliente):
    r = cliente.post("/predict/dificultad-texto", json={"texto": "El gato duerme."})
    assert r.status_code == 503


def test_pronunciacion(cliente):
    r = cliente.post(
        "/predict/pronunciacion",
        params={"texto_esperado": "mamá"},
        files={"audio": ("lectura.m4a", b"\x00" * 100, "audio/mp4")},
    )
    assert r.status_code == 200
    assert r.json()["correcto"] is True


@pytest.mark.parametrize("idioma", ["es", "en"])
def test_pronunciacion_pasa_el_idioma(cliente, idioma):
    STTFalso.idiomas.clear()
    r = cliente.post(
        "/predict/pronunciacion",
        params={"texto_esperado": "mamá", "idioma": idioma},
        files={"audio": ("lectura.wav", b"\x00" * 100, "audio/wav")},
    )
    assert r.status_code == 200
    assert STTFalso.idiomas == [idioma]


def test_pronunciacion_rechaza_idioma_desconocido(cliente):
    r = cliente.post(
        "/predict/pronunciacion",
        params={"texto_esperado": "mamá", "idioma": "fr"},
        files={"audio": ("lectura.wav", b"\x00" * 100, "audio/wav")},
    )
    assert r.status_code == 422


def test_edad_de_palabra(cliente):
    r = cliente.get("/predict/aoa-palabra", params={"palabra": "dog", "idioma": "en"})
    assert r.status_code == 200
    assert r.json() == {"palabra": "dog", "idioma": "en", "nivel": 1}
    assert cliente.get("/predict/aoa-palabra", params={"palabra": "dos palabras"}).status_code == 422


def test_audio_demasiado_grande(cliente, monkeypatch):
    monkeypatch.setattr(api, "MAX_AUDIO_BYTES", 1000)
    r = cliente.post(
        "/predict/pronunciacion",
        params={"texto_esperado": "mamá"},
        files={"audio": ("lectura.wav", b"\x00" * 1001, "audio/wav")},
    )
    assert r.status_code == 413


def test_trazo_perfecto(cliente):
    puntos = [{"x": 200.0, "y": 40 + 320 * k / 40, "timestamp": k * 10} for k in range(41)]
    puntos += [{"x": 140 + 120 * k / 20, "y": y} for y in (40.0, 360.0) for k in range(21)]

    r = cliente.post("/analyze/trazo", json={
        "puntos": puntos, "letra": "i", "ancho_canvas": 400, "alto_canvas": 400,
    })

    assert r.status_code == 200
    assert r.json()["correcto"] is True


def test_trazo_valida_entrada(cliente):
    r = cliente.post("/analyze/trazo", json={
        "puntos": [{"y": 1}], "letra": "A", "ancho_canvas": 0, "alto_canvas": 400,
        "tolerancia": "extrema",
    })
    assert r.status_code == 422


def test_siguiente_leccion_usa_fechas(cliente):
    ahora = "2026-10-09T12:00:00"
    items = [
        {"item_id": f"fonema_{l}", "racha_actual": 2, "aciertos": 2, "ultima_practica": ahora}
        for l in "mps"
    ]
    r = cliente.post("/predict/siguiente-leccion", json={"items": items})

    assert r.status_code == 200
    assert r.json()["desbloquear_nivel"] is True
