"""Tests de la lógica de evaluación, con respuestas de Whisper simuladas (sin cargar el modelo)."""

from pino_ml.models.stt_fonetico import (
    comparar_silabas,
    evaluar_fonema,
    evaluar_transcripcion,
)


def whisper(*textos, no_speech_prob=0.01, avg_logprob=-0.1):
    return {
        "text": " ".join(textos),
        "segments": [
            {"text": t, "no_speech_prob": no_speech_prob, "avg_logprob": avg_logprob, "words": []}
            for t in textos
        ],
    }


def test_lectura_correcta_con_puntuacion_y_mayusculas():
    r = evaluar_transcripcion("mamá", whisper(" Mamá."))

    assert r.puntaje_global == 1.0
    assert r.silabas_incorrectas == []


def test_lectura_correcta_sin_tilde_en_la_transcripcion():
    r = evaluar_transcripcion("El niño come.", whisper(" el niño come"))
    assert r.puntaje_global == 1.0


def test_silencio_no_cuenta_como_lectura():
    # Whisper "alucina" texto sobre silencio, pero marca no_speech_prob alto
    r = evaluar_transcripcion("mamá", whisper("Gracias por ver el video.", no_speech_prob=0.95))

    assert r.texto_detectado == ""
    assert r.puntaje_global == 0.0
    assert r.silabas_incorrectas == ["ma", "ma"]


def test_silaba_repetida_no_desplaza_el_resto():
    correctas, incorrectas = comparar_silabas(["la", "ca", "sa"], ["la", "la", "ca", "sa"])
    assert correctas == ["la", "ca", "sa"]
    assert incorrectas == []


def test_silaba_omitida():
    correctas, incorrectas = comparar_silabas(["pe", "lo", "ta"], ["pe", "ta"])
    assert correctas == ["pe", "ta"]
    assert incorrectas == ["lo"]


def test_fonema_aislado():
    assert evaluar_fonema("m", whisper("Mmm."))[0]
    assert evaluar_fonema("a", whisper(" Ah."))[0]
    assert evaluar_fonema("a", whisper("Aaa"))[0]


def test_fonema_aislado_no_acepta_cualquier_texto_que_contenga_la_letra():
    # Antes: "a" in "casa" → correcto
    assert not evaluar_fonema("a", whisper("casa"))[0]
    assert not evaluar_fonema("m", whisper("mamá"))[0]


def test_fonema_aislado_en_silencio():
    assert evaluar_fonema("a", whisper("A.", no_speech_prob=0.9)) == (False, 0.0)
