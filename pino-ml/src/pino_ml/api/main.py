# -*- coding: utf-8 -*-
"""
API de ML para Pino — FastAPI.

Expone los modelos ML como endpoints REST para consumo
desde la app Flutter y desde procesos de análisis y evaluación PISA.
"""

import logging
import os
import tempfile
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, Optional, TypeVar, List, Dict, Any, Union

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pino_ml.models.algoritmo_adaptativo import AlgoritmoAdaptativo, ItemAprendizaje
from pino_ml.models.analizador_trazos import AnalizadorTrazos, PuntoTrazo, RutaIdeal
from pino_ml.models.clasificador_dificultad import ClasificadorDificultad
from pino_ml.models.edad_adquisicion import EdadAdquisicion
from pino_ml.models.stt_fonetico import STTFonetico, evaluar_transcripcion, evaluar_fonema
from pino_ml.models.pisa_risk_engine import PisaRiskEngine, TelemetriaUsuarioPino, pisa_risk_engine
from pino_ml.models.macro_analytics import MacroAnalyticsEngine, macro_analytics_engine
from pino_ml.utils.pisa_data_loader import pisa_data

logger = logging.getLogger("pino_ml.api")

MAX_AUDIO_BYTES = int(os.getenv("MAX_AUDIO_MB", "10")) * 1024 * 1024
EXTENSIONES_AUDIO = {".wav", ".m4a", ".mp3", ".aac", ".ogg", ".webm", ".flac"}

# Modelos globales
stt: Optional[STTFonetico] = None
adaptativo: Optional[AlgoritmoAdaptativo] = None
clasificador: Optional[ClasificadorDificultad] = None
analizador: Optional[AnalizadorTrazos] = None
edad: Optional[EdadAdquisicion] = None

_lock_stt = threading.Lock()
T = TypeVar("T")

def _cargar(nombre: str, crear: Callable[[], T]) -> Optional[T]:
    try:
        modelo = crear()
        logger.info("✅ Modelo '%s' cargado", nombre)
        return modelo
    except Exception:
        logger.exception("❌ No se pudo cargar el modelo '%s'", nombre)
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global stt, adaptativo, clasificador, analizador, edad
    logger.info("🔄 Cargando modelos ML...")
    stt = _cargar("stt", lambda: STTFonetico(modelo_size=os.getenv("WHISPER_MODEL_SIZE", "base")))
    adaptativo = _cargar("adaptativo", AlgoritmoAdaptativo)
    clasificador = _cargar("clasificador", lambda: ClasificadorDificultad(modelo_spacy=os.getenv("SPACY_MODEL", "es_core_news_md")))
    analizador = _cargar("analizador", AnalizadorTrazos)
    edad = _cargar("edad_adquisicion", EdadAdquisicion)
    yield
    logger.info("🛑 API finalizada")

app = FastAPI(
    title="Pino ML & PISA Analytics Engine",
    description="API de Machine Learning y Analítica PISA para la plataforma de alfabetización Pino",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas ---

class PronunciacionResponse(BaseModel):
    texto_esperado: str
    texto_detectado: str
    puntaje_global: float
    word_error_rate: float
    character_error_rate: float
    silabas_incorrectas: list[str]
    silabas_correctas: list[str]
    correcto: bool = True
    segmentos: list[dict] = Field(default_factory=list)
    similitud_fonetica_global: float = 0.0

class FonemaAisladoResponse(BaseModel):
    correcto: bool
    confianza: float
    fonema_esperado: str

def _a_hora_local(fecha: Optional[datetime]) -> Optional[datetime]:
    if fecha is None or fecha.tzinfo is None:
        return fecha
    return fecha.astimezone().replace(tzinfo=None)

class ItemAprendizajeRequest(BaseModel):
    item_id: str
    tipo: str = "fonema"
    aciertos: int = 0
    fallos: int = 0
    racha_actual: int = 0
    factor_facilidad: float = 2.5
    intervalo_dias: float = 1.0
    horas_desde_practica: float = 0.0
    ultima_practica: Optional[datetime] = None
    proxima_revision: Optional[datetime] = None
    errores_tipo: list[str] = Field(default_factory=list)

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

class ProximaLeccionRequest(BaseModel):
    items: Optional[list[ItemAprendizajeRequest]] = None
    historial: Optional[list[ItemAprendizajeRequest]] = None
    cantidad: int = Field(5, ge=1, le=50)
    modo: str = "infantil"
    nivel_actual: int = 1

class DificultadRequest(BaseModel):
    texto: str = Field(..., min_length=1)
    nivel_objetivo: Optional[int] = Field(None, ge=1, le=5)

class DificultadResponse(BaseModel):
    texto: Optional[str] = None
    nivel_dificultad: int
    etiqueta: str
    puntaje_legibilidad: float
    indice_gutierrez: Optional[float] = 0.0
    promedio_largo_palabra: Optional[float] = 0.0
    promedio_largo_oracion: Optional[float] = 0.0
    total_palabras: int
    total_oraciones: Optional[int] = 1
    palabras_complejas: list[str]
    silabas_por_palabra: float
    vocabulario_unico_ratio: Optional[float] = 0.0
    requiere_adaptacion: Optional[bool] = False
    sugerencias: Optional[list[str]] = None
    nivel_pisa_estimado: Optional[str] = None

class PuntoTrazoRequest(BaseModel):
    x: float = Field(..., ge=0)
    y: float = Field(..., ge=0)
    timestamp: float = 0.0
    presion: float = 1.0

class TrazoRequest(BaseModel):
    puntos: list[Any]
    letra: Optional[str] = None
    letra_esperada: Optional[str] = None
    ancho_canvas: float = Field(300.0, gt=0)
    alto_canvas: float = Field(300.0, gt=0)
    tolerancia: Literal["baja", "media", "alta"] = "media"

class TrazoResponse(BaseModel):
    letra_detectada: str
    confianza: float
    desviacion_promedio: float
    desviacion_maxima: Optional[float] = 0.0
    porcentaje_dentro_margen: float
    velocidad_promedio: Optional[float] = 0.0
    trazo_completo: bool
    tolerancia_sugerida: str
    correcto: bool = True
    segmentos_problematicos: list[dict] = Field(default_factory=list)

class PisaRiskRequest(BaseModel):
    tasa_acierto_fonemas: float = Field(..., ge=0.0, le=1.0)
    tasa_acierto_silabas: float = Field(..., ge=0.0, le=1.0)
    desviacion_promedio_trazo: float = Field(default=25.0)
    cobertura_promedio_trazo: float = Field(default=0.85, ge=0.0, le=1.0)
    latencia_media_respuesta_seg: float = Field(default=2.5, ge=0.0)
    palabras_por_minuto: float = Field(default=45.0, ge=0.0)
    tasa_error_pronunciacion: float = Field(default=0.15, ge=0.0, le=1.0)
    dias_activos_racha: int = Field(default=5, ge=0)

# --- Endpoints ---

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.2.0",
        "service": "pino-ml-engine",
        "modelos_cargados": {
            "stt": stt is not None,
            "adaptativo": adaptativo is not None,
            "clasificador": clasificador is not None,
            "analizador": analizador is not None,
            "edad_adquisicion": edad is not None,
        },
    }

def _guardar_audio_temporal(upload: UploadFile) -> str:
    ext = Path(upload.filename or "audio.wav").suffix.lower()
    if ext not in EXTENSIONES_AUDIO:
        ext = ".wav"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        contenido = upload.file.read()
        if len(contenido) > MAX_AUDIO_BYTES:
            raise HTTPException(413, "Audio excede el tamaño máximo permitido")
        f.write(contenido)
        return f.name

@app.post("/predict/pronunciacion", response_model=PronunciacionResponse)
def evaluar_pronunciacion(
    audio: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    texto_esperado: Optional[str] = None,
    idioma: Literal["es", "en"] = "es",
):
    upload = audio or file
    if upload is None:
        raise HTTPException(422, "Archivo de audio requerido ('audio' o 'file')")
    if not texto_esperado:
        raise HTTPException(422, "Parámetro 'texto_esperado' requerido")
    if not stt:
        raise HTTPException(503, "Modelo STT no disponible")

    tmp_path = _guardar_audio_temporal(upload)
    try:
        with _lock_stt:
            resultado = stt.analizar_pronunciacion(tmp_path, texto_esperado, idioma)

        return PronunciacionResponse(
            texto_esperado=resultado.texto_esperado,
            texto_detectado=resultado.texto_detectado,
            puntaje_global=resultado.puntaje_global,
            word_error_rate=resultado.word_error_rate,
            character_error_rate=resultado.character_error_rate,
            silabas_incorrectas=resultado.silabas_incorrectas,
            silabas_correctas=resultado.silabas_correctas,
            correcto=resultado.puntaje_global >= 0.7,
            similitud_fonetica_global=getattr(resultado, "similitud_fonetica_global", 0.0),
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.post("/predict/fonema", response_model=FonemaAisladoResponse)
def evaluar_fonema_endpoint(
    audio: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    fonema_esperado: str = "",
):
    upload = audio or file
    if upload is None:
        raise HTTPException(422, "Archivo de audio requerido")
    if not stt:
        raise HTTPException(503, "Modelo STT no disponible")

    tmp_path = _guardar_audio_temporal(upload)
    try:
        with _lock_stt:
            correcto, confianza = stt.evaluar_fonema_aislado(tmp_path, fonema_esperado)

        return FonemaAisladoResponse(
            correcto=correcto,
            confianza=confianza,
            fonema_esperado=fonema_esperado,
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.get("/predict/aoa-palabra")
def edad_de_palabra(
    palabra: str = Query(..., min_length=1, max_length=40),
    idioma: Literal["es", "en"] = "es",
    traduccion: Optional[str] = Query(None, max_length=40),
):
    """Edad a la que se suele aprender una palabra y su nivel en Pino."""
    if not edad:
        raise HTTPException(503, "Modelo de edad de adquisición no disponible")
    try:
        return edad.analizar(palabra, idioma, traduccion)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

@app.post("/predict/siguiente-leccion")
def obtener_siguiente_leccion(request: ProximaLeccionRequest):
    if not adaptativo:
        raise HTTPException(503, "Modelo adaptativo no disponible")

    items_req = request.items if request.items is not None else request.historial
    if not items_req:
        return {
            "siguiente_item_id": "a" if request.nivel_actual == 1 else "ma",
            "tipo": "fonema" if request.nivel_actual == 1 else "silaba",
            "prioridad_repaso": False,
            "probabilidad_error_estimada": 0.5,
            "factor_facilidad": 2.5,
            "desbloquea_siguiente_nivel": False,
            "desbloquear_nivel": False,
            "items_recomendados": [],
            "mensaje_pedagogico": "Bienvenido a tu lección inicial.",
        }

    items = [item.a_item() for item in items_req]
    recomendados = adaptativo.seleccionar_proxima_leccion(items, request.cantidad)
    desbloquear = adaptativo.verificar_desbloqueo(items)
    primer_elegido = recomendados[0] if recomendados else items[0]

    return {
        "siguiente_item_id": primer_elegido.item_id,
        "tipo": primer_elegido.tipo,
        "prioridad_repaso": primer_elegido.necesita_repaso,
        "probabilidad_error_estimada": adaptativo.predecir_probabilidad_error(primer_elegido),
        "factor_facilidad": primer_elegido.factor_facilidad,
        "desbloquea_siguiente_nivel": desbloquear,
        "desbloquear_nivel": desbloquear,
        "items_recomendados": [
            {
                "item_id": item.item_id,
                "tipo": item.tipo,
                "tasa_acierto": item.tasa_acierto,
                "prob_error": adaptativo.predecir_probabilidad_error(item),
            }
            for item in recomendados
        ],
        "mensaje_pedagogico": "Excelente ritmo de práctica.",
    }

@app.post("/predict/dificultad-texto", response_model=DificultadResponse)
def analizar_dificultad(request: DificultadRequest):
    if not clasificador:
        raise HTTPException(503, "Clasificador no disponible")

    res = clasificador.analizar(request.texto)
    return DificultadResponse(
        texto=res.texto,
        nivel_dificultad=res.nivel_dificultad,
        etiqueta=res.etiqueta,
        puntaje_legibilidad=res.puntaje_legibilidad,
        indice_gutierrez=getattr(res, "indice_gutierrez", 0.0),
        promedio_largo_palabra=getattr(res, "promedio_largo_palabra", 0.0),
        promedio_largo_oracion=getattr(res, "promedio_largo_oracion", 0.0),
        total_palabras=res.total_palabras,
        total_oraciones=getattr(res, "total_oraciones", 1),
        palabras_complejas=res.palabras_complejas,
        silabas_por_palabra=res.silabas_por_palabra,
        vocabulario_unico_ratio=getattr(res, "vocabulario_unico_ratio", 0.0),
        nivel_pisa_estimado=getattr(res, "nivel_pisa_estimado", None),
    )

@app.post("/analyze/trazo", response_model=TrazoResponse)
def analizar_trazo(request: TrazoRequest):
    if not analizador:
        raise HTTPException(503, "Analizador no disponible")

    if request.tolerancia not in ("baja", "media", "alta"):
        raise HTTPException(422, "Tolerancia inválida")

    letra = (request.letra or request.letra_esperada or "A").upper()

    puntos: list[PuntoTrazo] = []
    for p in request.puntos:
        if isinstance(p, dict):
            if "x" not in p or "y" not in p:
                raise HTTPException(422, "Punto incompleto")
            puntos.append(PuntoTrazo(
                x=float(p["x"]),
                y=float(p["y"]),
                timestamp=float(p.get("timestamp", 0.0)),
                presion=float(p.get("presion", 1.0)),
            ))
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            puntos.append(PuntoTrazo(x=float(p[0]), y=float(p[1])))
        else:
            raise HTTPException(422, "Formato de punto inválido")

    rutas = analizador.rutas_ideales
    if letra not in rutas:
        raise HTTPException(400, f"No hay ruta ideal para '{letra}'")

    ruta = RutaIdeal(
        letra=letra,
        trazos=rutas[letra],
        ancho_canvas=request.ancho_canvas,
        alto_canvas=request.alto_canvas,
    )

    resultado = analizador.analizar_trazo(puntos, ruta, request.tolerancia)

    return TrazoResponse(
        letra_detectada=resultado.letra_detectada,
        confianza=resultado.confianza,
        desviacion_promedio=resultado.desviacion_promedio,
        desviacion_maxima=resultado.desviacion_maxima,
        porcentaje_dentro_margen=resultado.porcentaje_dentro_margen,
        velocidad_promedio=resultado.velocidad_promedio,
        trazo_completo=resultado.trazo_completo,
        tolerancia_sugerida=resultado.tolerancia_sugerida,
        correcto=resultado.confianza >= 0.7 and resultado.trazo_completo,
        segmentos_problematicos=resultado.segmentos_problematicos,
    )

# --- Endpoints Analítica PISA & Macro ---

@app.post("/predict/pisa-risk")
def predict_pisa_risk(req: PisaRiskRequest):
    tel = TelemetriaUsuarioPino(
        tasa_acierto_fonemas=req.tasa_acierto_fonemas,
        tasa_acierto_silabas=req.tasa_acierto_silabas,
        desviacion_promedio_trazo=req.desviacion_promedio_trazo,
        cobertura_promedio_trazo=req.cobertura_promedio_trazo,
        latencia_media_respuesta_seg=req.latencia_media_respuesta_seg,
        palabras_por_minuto=req.palabras_por_minuto,
        tasa_error_pronunciacion=req.tasa_error_pronunciacion,
        dias_activos_racha=req.dias_activos_racha,
    )
    pred = pisa_risk_engine.evaluar_riesgo(tel)
    return {
        "puntaje_pisa_estimado": pred.puntaje_pisa_estimado,
        "nivel_competencia_pisa": pred.nivel_competencia_pisa,
        "probabilidad_bajo_nivel_2": pred.probabilidad_bajo_nivel_2,
        "categoria_riesgo": pred.categoria_riesgo,
        "diferencia_con_media_chile": pred.diferencia_con_media_chile,
        "diferencia_con_media_ocde": pred.diferencia_con_media_ocde,
        "cuello_botella_cognitivo": pred.cuello_botella_cognitivo,
        "desglose_componentes": pred.desglose_componentes,
        "intervenciones_recomendadas": pred.intervenciones_recomendadas,
    }

@app.get("/analytics/pisa-history")
def get_pisa_history(country: str = Query("Chile")):
    return {"country": country, "history": pisa_data.get_country_reading_history(country)}

@app.get("/analytics/pisa-levels")
def get_pisa_levels(country: Optional[str] = Query(None)):
    return {"levels": pisa_data.get_pisa_levels(country)}

@app.get("/analytics/chile-socioeconomic")
def get_chile_socioeconomic():
    return pisa_data.get_chile_socioeconomic_metrics()

@app.get("/analytics/macro-opportunity")
def get_macro_opportunity_ranking(top_n: int = Query(15, ge=1, le=50)):
    ranking = macro_analytics_engine.obtener_ranking_global(top_n=top_n)
    return {"ranking": [r.__dict__ for r in ranking]}
