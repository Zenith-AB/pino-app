# -*- coding: utf-8 -*-
"""
Pino Beta · Escucha y practica la pronunciación de palabras en español e inglés.

Escucha tu voz con el micrófono y la compara con la palabra (``escucha.py``, Whisper local).

Voces:
  * edge-tts (por defecto): gratis y sin clave. Usa las voces neuronales de Microsoft Edge
    por internet; es un servicio no oficial y puede cambiar sin aviso.
  * ElevenLabs (opcional): requiere la variable de entorno ELEVENLABS_API_KEY.

La palabra escrita se envía al servicio de voz: no escribir datos personales.
La grabación del micrófono se procesa en el computador y no se guarda ni se envía.

    streamlit run app/pino_beta.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "app"))
import escucha  # noqa: E402
import texto_es  # noqa: E402

VOCES_EDGE = {
    "es": {"Catalina (Chile)": "es-CL-CatalinaNeural", "Lorenzo (Chile)": "es-CL-LorenzoNeural",
           "Dalia (México)": "es-MX-DaliaNeural", "Elvira (España)": "es-ES-ElviraNeural"},
    "en": {"Ana (niña, EE. UU.)": "en-US-AnaNeural", "Jenny (EE. UU.)": "en-US-JennyNeural",
           "Maisie (niña, Reino Unido)": "en-GB-MaisieNeural"},
}
API_11 = "https://api.elevenlabs.io/v1"
CLAVE_11 = os.environ.get("ELEVENLABS_API_KEY", "")


@st.cache_data
def vocabulario(idioma: str) -> pd.DataFrame:
    return pd.read_csv(RAIZ / "data" / "processed" / f"vocabulario_infantil_{idioma}.csv", keep_default_na=False)


@st.cache_data
def cmudict() -> dict[str, str]:
    pron = {}
    for linea in (RAIZ / "data" / "raw" / "en_cmudict.dict").read_text(encoding="utf-8").splitlines():
        partes = linea.split("#")[0].split()
        if partes and "(" not in partes[0]:
            pron[partes[0]] = " ".join(partes[1:])
    return pron


@st.cache_data(show_spinner="Generando audio…", max_entries=500)
def audio_edge(texto: str, voz: str, velocidad: int) -> bytes:
    import edge_tts

    async def generar() -> bytes:
        com = edge_tts.Communicate(texto, voz, rate=f"{velocidad:+d}%")
        return b"".join([c["data"] async for c in com.stream() if c["type"] == "audio"])

    return asyncio.run(generar())


@st.cache_data(ttl=600)
def voces_11(clave: str) -> dict[str, str]:
    r = requests.get(f"{API_11}/voices", headers={"xi-api-key": clave}, timeout=20)
    r.raise_for_status()
    return {v["name"]: v["voice_id"] for v in r.json()["voices"]}


@st.cache_data(show_spinner="Generando audio…", max_entries=500)
def audio_11(texto: str, voz: str, idioma: str, velocidad: int, clave: str) -> bytes:
    r = requests.post(f"{API_11}/text-to-speech/{voz}", headers={"xi-api-key": clave}, timeout=60,
                      json={"text": texto, "model_id": "eleven_flash_v2_5", "language_code": idioma,
                            "voice_settings": {"speed": max(0.7, 1 + velocidad / 100)}})
    r.raise_for_status()
    return r.content


@st.cache_resource(show_spinner="Preparando el reconocimiento de voz (la primera vez descarga el modelo)…")
def modelo_voz(tamano: str):
    return escucha.cargar_modelo(tamano)


st.set_page_config(page_title="Pino Beta", page_icon="🌲")
st.title("🌲 Pino Beta")
st.caption("Escucha cómo se pronuncia una palabra y practica con el micrófono.")

with st.sidebar:
    idioma = st.radio("Idioma", ["es", "en"], format_func={"es": "Español", "en": "Inglés"}.get)
    servicio = st.radio("Servicio de voz", ["edge-tts (gratis)"] + (["ElevenLabs"] if CLAVE_11 else []))
    if not CLAVE_11:
        st.caption("Para usar ElevenLabs define `ELEVENLABS_API_KEY` antes de abrir la app.")
    try:
        voces = voces_11(CLAVE_11) if servicio == "ElevenLabs" else VOCES_EDGE[idioma]
    except requests.RequestException as e:
        st.error(f"ElevenLabs no respondió: {e}")
        st.stop()
    voz = voces[st.selectbox("Voz", list(voces))]
    lenta = st.slider("Velocidad de la versión lenta (%)", -30 if servicio == "ElevenLabs" else -60, -10, -30, 5)
    tamano = st.selectbox("Precisión al escuchar", ["small", "base"],
                          format_func={"small": "Mayor (modelo small)", "base": "Más rápida (modelo base)"}.get)
    st.caption("La palabra escrita se envía al servicio de voz por internet: no escribas datos personales. "
               "Tu grabación se procesa en este computador y no se guarda.")

voc = vocabulario(idioma)
origen = st.radio("Palabra", ["Del vocabulario por nivel", "Escribir otra"], horizontal=True)
if origen == "Escribir otra":
    palabra = st.text_input("Escribe una palabra y presiona Enter", max_chars=40).strip().lower()
else:
    nivel = st.selectbox("Nivel", sorted(voc["nivel_pino"].unique()))
    palabra = st.selectbox("Palabra del nivel", sorted(voc.loc[voc["nivel_pino"] == nivel, "palabra"].astype(str)))

if not palabra:
    st.info("Elige o escribe una palabra.")
    st.stop()

st.header(palabra)
silabas: list[str] = []
if idioma == "es":
    silabas = texto_es.separar_silabas(palabra)
    st.markdown(f"**Sílabas:** {' · '.join(silabas)}  \n**Fonemas:** `{' '.join(texto_es.palabra_a_fonemas(palabra))}`")
else:
    st.markdown(f"**Fonemas (CMU):** `{cmudict().get(palabra, 'no está en el diccionario')}`")

fila = voc[voc["palabra"] == palabra]
if len(fila):
    f = fila.iloc[0]
    traduccion = f["traduccion_en" if idioma == "es" else "traduccion_es"]
    st.caption(f"{f['nivel_pino']}" + (f" · en {'inglés' if idioma == 'es' else 'español'}: {traduccion}" if traduccion else ""))

versiones = [("Normal", palabra, 0), ("Lenta", palabra, lenta)]
if len(silabas) > 1:
    versiones.append(("Por sílabas (aproximada)", ", ".join(silabas), lenta))

st.subheader("🔊 Escucha")
for titulo, texto, velocidad in versiones:
    st.markdown(f"**{titulo}**")
    try:
        audio = (audio_11(texto, voz, idioma, velocidad, CLAVE_11) if servicio == "ElevenLabs"
                 else audio_edge(texto, voz, velocidad))
    except Exception as e:  # sin internet, cuota agotada o cambio del servicio
        st.error(f"No se pudo generar el audio: {e}")
        continue
    st.audio(audio, format="audio/mpeg")
    if titulo == "Normal":
        st.download_button("Descargar MP3", audio, f"{palabra}_{idioma}.mp3", "audio/mpeg")

st.subheader("🎤 Ahora tú")
grabacion = st.audio_input(f"Graba diciendo «{palabra}»", key=f"mic_{idioma}_{palabra}")
if grabacion is not None:
    try:
        with st.spinner("Escuchando…"):
            oido = escucha.transcribir(modelo_voz(tamano), grabacion, idioma)
    except Exception as e:  # sin modelo descargado o audio ilegible
        st.error(f"No se pudo analizar la grabación: {e}")
    else:
        r = escucha.evaluar(palabra, oido, idioma, cmudict() if idioma == "en" else None)
        if r.veredicto == "bien":
            st.success(f"✅ ¡Muy bien! Se entendió «{palabra}».")
        elif r.veredicto == "casi":
            st.warning(f"🟡 Casi. Escuché «{r.oido}». Prueba otra vez.")
        elif r.veredicto == "otra":
            st.error(f"🔁 Escuché «{r.oido}». Escucha la palabra y repítela.")
        else:
            st.info("No escuché ninguna palabra. Acércate al micrófono y graba de nuevo.")
        if r.veredicto != "sin_voz":
            st.progress(r.puntaje, text=f"Parecido de los sonidos: {r.puntaje:.0%}")
            if r.silabas:
                st.markdown(" · ".join(f":green[**{x}**]" if ok else f":red[**{x}**]" for x, ok in r.silabas))
    st.caption("Función experimental: puede equivocarse, sobre todo con palabras cortas y voces de niños. "
               "No reemplaza a una persona que escuche.")
