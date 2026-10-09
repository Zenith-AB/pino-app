"""
API de ML para Pino — FastAPI.

Expone los modelos ML como endpoints REST para consumo
desde la app Flutter y desde procesos de análisis.

Ejecutar (desde pino-ml/, con el paquete instalado):
    uvicorn pino_ml.api.main:app --env-file .env

Los endpoints que usan modelos pesados (Whisper, spaCy) son funciones
normales (`def`, no `async def`): FastAPI los ejecuta en un pool de hilos y
así no bloquean el servidor mientras procesan.
"""

import logging
import os
import tempfile
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, Optional, TypeVar

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from pino_ml.models.algoritmo_adaptativo import AlgoritmoAdaptativo, ItemAprendizaje
from pino_ml.models.analizador_trazos import AnalizadorTrazos, PuntoTrazo, RutaIdeal
from pino_ml.models.clasificador_dificultad import ClasificadorDificultad
from pino_ml.models.stt_fonetico import STTFonetico

logger = logging.getLogger("pino_ml.api")

# Tamaño máximo del audio subido (MB). Una lectura de pocos segundos pesa
# mucho menos; el límite evita que un archivo enorme tumbe el servidor.
MAX_AUDIO_BYTES = int(os.getenv("MAX_AUDIO_MB", "10")) * 1024 * 1024
EXTENSIONES_AUDIO = {".wav", ".m4a", ".mp3", ".aac", ".ogg", ".webm", ".flac"}


# ─── Modelos globales (se cargan al iniciar) ───

stt: Optional[STTFonetico] = None
adaptativo: Optional[AlgoritmoAdaptativo] = None
clasificador: Optional[ClasificadorDificultad] = None
analizador: Optional[AnalizadorTrazos] = None

# Whisper usa mucha memoria: se procesa un audio a la vez.
_lock_stt = threading.Lock()

T = TypeVar("T")


def _cargar(nombre: str, crear: Callable[[], T]) -> Optional[T]:
    """Carga un modelo; si falla, la API arranca igual sin ese modelo (503)."""
    try:
        modelo = crear()
        logger.info("✅ Modelo '%s' cargado", nombre)
        return modelo
    except Exception:
        logger.exception("❌ No se pudo cargar el modelo '%s'", nombre)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga los modelos al iniciar la API."""
    global stt, adaptativo, clasificador, analizador

    logger.info("🔄 Cargando modelos ML...")
    stt = _cargar("stt", lambda: STTFonetico(
        modelo_size=os.getenv("WHISPER_MODEL_SIZE", "medium")
    ))
    adaptativo = _cargar("adaptativo", AlgoritmoAdaptativo)
    clasificador = _cargar("clasificador", lambda: ClasificadorDificultad(
        modelo_spacy=os.getenv("SPACY_MODEL", "es_core_news_md")
    ))
    analizador = _cargar("analizador", AnalizadorTrazos)
    yield
    logger.info("🛑 API finalizada")


app = FastAPI(
    title="Pino ML API",
    description="API de Machine Learning para la plataforma de alfabetización Pino",
    version="0.1.0",
    lifespan=lifespan,
)


# ─── Schemas ───

class PronunciacionResponse(BaseModel):
    texto_esperado: str
    texto_detectado: str
    puntaje_global: float
    word_error_rate: float
    character_error_rate: float
    silabas_incorrectas: list[str]
    silabas_correctas: list[str]
    correcto: bool


class FonemaAisladoResponse(BaseModel):
    correcto: bool
    confianza: float
    fonema_esperado: str


class ItemAprendizajeRequest(BaseModel):
    item_id: str
    tipo: str = "fonema"
    aciertos: int = 0
    fallos: int = 0
    racha_actual: int = 0
    factor_facilidad: float = 2.5
    intervalo_dias: float = 1.0
    ultima_practica: Optional[datetime] = None
    proxima_revision: Optional[datetime] = None
    errores_tipo: list[str] = []

    def a_item(self) -> ItemAprendizaje:
        return ItemAprendizaje(
            item_id=self.item_id,
            tipo=self.tipo,
            aciertos=self.aciertos,
            fallos=self.fallos,
            racha_actual=self.racha_actual,
            factor_facilidad=self.factor_facilidad,
            intervalo_dias=self.intervalo_dias,
            ultima_practica=_a_hora_local(self.ultima_practica),
            proxima_revision=_a_hora_local(self.proxima_revision),
            errores_tipo=list(self.errores_tipo),
        )


def _a_hora_local(fecha: Optional[datetime]) -> Optional[datetime]:
    """El algoritmo compara con datetime.now() (sin zona): normaliza a hora local."""
    if fecha is None or fecha.tzinfo is None:
        return fecha
    return fecha.astimezone().replace(tzinfo=None)


class ProximaLeccionRequest(BaseModel):
    items: list[ItemAprendizajeRequest] = Field(..., description="Lista de ítems de aprendizaje del usuario")
    cantidad: int = Field(5, ge=1, le=50, description="Cantidad de ítems a recomendar")


class DificultadRequest(BaseModel):
    texto: str = Field(..., max_length=10_000, description="Texto a analizar")
    nivel_objetivo: Optional[int] = Field(None, ge=1, le=5, description="Nivel deseado (1-5)")


class DificultadResponse(BaseModel):
    nivel_dificultad: int
    etiqueta: str
    puntaje_legibilidad: float
    total_palabras: int
    palabras_complejas: list[str]
    silabas_por_palabra: float
    requiere_adaptacion: bool = False
    sugerencias: list[str] = []


class PuntoTrazoRequest(BaseModel):
    x: float
    y: float
    timestamp: float = 0
    presion: float = 1.0


class TrazoRequest(BaseModel):
    puntos: list[PuntoTrazoRequest] = Field(..., max_length=5_000, description="Puntos del trazo")
    letra: str = Field(..., min_length=1, max_length=2, description="Letra que se intentaba trazar")
    ancho_canvas: float = Field(..., gt=0, description="Ancho del canvas en píxeles")
    alto_canvas: float = Field(..., gt=0, description="Alto del canvas en píxeles")
    tolerancia: Literal["baja", "media", "alta"] = Field("media", description="Nivel de tolerancia")


class TrazoResponse(BaseModel):
    letra_detectada: str
    confianza: float
    desviacion_promedio: float
    porcentaje_dentro_margen: float
    trazo_completo: bool
    tolerancia_sugerida: str
    correcto: bool


# ─── Utilidades ───

def _guardar_audio_temporal(audio: UploadFile) -> str:
    """Guarda el audio subido en un archivo temporal, respetando el tamaño máximo."""
    contenido = audio.file.read(MAX_AUDIO_BYTES + 1)
    if len(contenido) > MAX_AUDIO_BYTES:
        raise HTTPException(413, f"El audio supera {MAX_AUDIO_BYTES // (1024 * 1024)} MB")
    if not contenido:
        raise HTTPException(400, "El audio está vacío")

    # Whisper (ffmpeg) detecta el formato por el contenido; la extensión ayuda.
    sufijo = Path(audio.filename or "").suffix.lower()
    if sufijo not in EXTENSIONES_AUDIO:
        sufijo = ".wav"

    with tempfile.NamedTemporaryFile(suffix=sufijo, delete=False) as tmp:
        tmp.write(contenido)
        return tmp.name


# ─── Endpoints ───

@app.get("/health")
def health():
    """Health check del servicio."""
    return {
        "status": "ok",
        "modelos_cargados": {
            "stt": stt is not None,
            "adaptativo": adaptativo is not None,
            "clasificador": clasificador is not None,
            "analizador": analizador is not None,
        },
    }


# ── 1. Pronunciación ──

@app.post("/predict/pronunciacion", response_model=PronunciacionResponse)
def evaluar_pronunciacion(
    audio: UploadFile = File(..., description="Archivo de audio del usuario"),
    texto_esperado: str = "",
):
    """
    Evalúa la pronunciación del usuario comparándola con el texto esperado.
    Usado por HU-06: Lectura en voz alta con feedback.
    """
    if not stt:
        raise HTTPException(503, "Modelo STT no disponible")

    tmp_path = _guardar_audio_temporal(audio)
    try:
        with _lock_stt:
            resultado = stt.analizar_pronunciacion(tmp_path, texto_esperado)

        return PronunciacionResponse(
            texto_esperado=resultado.texto_esperado,
            texto_detectado=resultado.texto_detectado,
            puntaje_global=resultado.puntaje_global,
            word_error_rate=resultado.word_error_rate,
            character_error_rate=resultado.character_error_rate,
            silabas_incorrectas=resultado.silabas_incorrectas,
            silabas_correctas=resultado.silabas_correctas,
            correcto=resultado.puntaje_global >= 0.8,
        )
    finally:
        os.unlink(tmp_path)


@app.post("/predict/fonema", response_model=FonemaAisladoResponse)
def evaluar_fonema(
    audio: UploadFile = File(...),
    fonema_esperado: str = "",
):
    """
    Evalúa la pronunciación de un fonema aislado (experimental: ver
    limitaciones en stt_fonetico.py).
    Usado por HU-03: Asociación fonema-grafema.
    """
    if not stt:
        raise HTTPException(503, "Modelo STT no disponible")

    tmp_path = _guardar_audio_temporal(audio)
    try:
        with _lock_stt:
            correcto, confianza = stt.evaluar_fonema_aislado(tmp_path, fonema_esperado)

        return FonemaAisladoResponse(
            correcto=correcto,
            confianza=confianza,
            fonema_esperado=fonema_esperado,
        )
    finally:
        os.unlink(tmp_path)


# ── 2. Algoritmo Adaptativo ──

@app.post("/predict/siguiente-leccion")
def obtener_siguiente_leccion(request: ProximaLeccionRequest):
    """
    Recomienda los próximos ítems a practicar basándose en el historial.
    Usado por HU-05: Ajuste dinámico de dificultad.
    """
    if not adaptativo:
        raise HTTPException(503, "Modelo adaptativo no disponible")

    items = [item.a_item() for item in request.items]

    recomendados = adaptativo.seleccionar_proxima_leccion(items, request.cantidad)
    desbloquear = adaptativo.verificar_desbloqueo(items)

    return {
        "items_recomendados": [
            {
                "item_id": item.item_id,
                "tipo": item.tipo,
                "tasa_acierto": item.tasa_acierto,
                "prob_error": adaptativo.predecir_probabilidad_error(item),
            }
            for item in recomendados
        ],
        "desbloquear_nivel": desbloquear,
    }


# ── 3. Dificultad de texto ──

@app.post("/predict/dificultad-texto", response_model=DificultadResponse)
def analizar_dificultad(request: DificultadRequest):
    """
    Analiza la dificultad de un texto en español.
    Usado por HU-04 y HU-17 para adaptar contenido al nivel del usuario.
    """
    if not clasificador:
        raise HTTPException(503, "Clasificador no disponible")

    if request.nivel_objetivo is not None:
        resultado = clasificador.adaptar_texto_a_nivel(
            request.texto, request.nivel_objetivo
        )
        analisis = resultado['analisis']
        return DificultadResponse(
            nivel_dificultad=analisis.nivel_dificultad,
            etiqueta=analisis.etiqueta,
            puntaje_legibilidad=analisis.puntaje_legibilidad,
            total_palabras=analisis.total_palabras,
            palabras_complejas=analisis.palabras_complejas,
            silabas_por_palabra=analisis.silabas_por_palabra,
            requiere_adaptacion=resultado['requiere_adaptacion'],
            sugerencias=resultado['sugerencias'],
        )

    analisis = clasificador.analizar(request.texto)
    return DificultadResponse(
        nivel_dificultad=analisis.nivel_dificultad,
        etiqueta=analisis.etiqueta,
        puntaje_legibilidad=analisis.puntaje_legibilidad,
        total_palabras=analisis.total_palabras,
        palabras_complejas=analisis.palabras_complejas,
        silabas_por_palabra=analisis.silabas_por_palabra,
    )


# ── 4. Análisis de trazos ──

@app.post("/analyze/trazo", response_model=TrazoResponse)
def analizar_trazo(request: TrazoRequest):
    """
    Analiza el trazo de una letra dibujada por el usuario.
    Usado por HU-02 y HU-13.
    """
    if not analizador:
        raise HTTPException(503, "Analizador no disponible")

    puntos = [
        PuntoTrazo(x=p.x, y=p.y, timestamp=p.timestamp, presion=p.presion)
        for p in request.puntos
    ]

    # Obtener ruta ideal
    rutas = analizador.rutas_ideales
    letra_upper = request.letra.upper()

    if letra_upper not in rutas:
        raise HTTPException(400, f"No hay ruta ideal para '{request.letra}'")

    ruta = RutaIdeal(
        letra=letra_upper,
        trazos=rutas[letra_upper],
        ancho_canvas=request.ancho_canvas,
        alto_canvas=request.alto_canvas,
    )

    resultado = analizador.analizar_trazo(puntos, ruta, request.tolerancia)

    return TrazoResponse(
        letra_detectada=resultado.letra_detectada,
        confianza=resultado.confianza,
        desviacion_promedio=resultado.desviacion_promedio,
        porcentaje_dentro_margen=resultado.porcentaje_dentro_margen,
        trazo_completo=resultado.trazo_completo,
        tolerancia_sugerida=resultado.tolerancia_sugerida,
        correcto=resultado.confianza >= 0.7 and resultado.trazo_completo,
    )
