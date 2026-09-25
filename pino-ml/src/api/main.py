"""
API de ML para Pino — FastAPI.

Expone los modelos ML como endpoints REST para consumo
desde la app Flutter y desde procesos de análisis.
"""

import os
import tempfile
from contextlib import asynccontextmanager
from typing import Optional

import mlflow
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel, Field

from src.models.stt_fonetico import STTFonetico, ResultadoPronunciacion
from src.models.algoritmo_adaptativo import AlgoritmoAdaptativo, ItemAprendizaje, TipoError
from src.models.clasificador_dificultad import ClasificadorDificultad
from src.models.analizador_trazos import AnalizadorTrazos, PuntoTrazo, RutaIdeal


# ─── Modelos globales (se cargan al iniciar) ───

stt: Optional[STTFonetico] = None
adaptativo: Optional[AlgoritmoAdaptativo] = None
clasificador: Optional[ClasificadorDificultad] = None
analizador: Optional[AnalizadorTrazos] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga los modelos al iniciar la API."""
    global stt, adaptativo, clasificador, analizador

    print("🔄 Cargando modelos ML...")

    whisper_size = os.getenv("WHISPER_MODEL_SIZE", "medium")
    stt = STTFonetico(modelo_size=whisper_size)

    adaptativo = AlgoritmoAdaptativo()
    clasificador = ClasificadorDificultad()
    analizador = AnalizadorTrazos()

    print("✅ Modelos cargados correctamente")
    yield
    print("🛑 API finalizada")


app = FastAPI(
    title="Pino ML API",
    description="API de Machine Learning para la plataforma de alfabetización Pino",
    version="0.1.0",
    lifespan=lifespan,
)


# ─── Schemas ───

class PronunciacionRequest(BaseModel):
    texto_esperado: str = Field(..., description="Texto que el usuario debía leer")


class PronunciacionResponse(BaseModel):
    texto_esperado: str
    texto_detectado: str
    puntaje_global: float
    word_error_rate: float
    character_error_rate: float
    silabas_incorrectas: list[str]
    silabas_correctas: list[str]
    correcto: bool


class FonemaAisladoRequest(BaseModel):
    fonema_esperado: str = Field(..., description="Fonema que el usuario debía pronunciar")


class FonemaAisladoResponse(BaseModel):
    correcto: bool
    confianza: float
    fonema_esperado: str


class ProximaLeccionRequest(BaseModel):
    items: list[dict] = Field(..., description="Lista de ítems de aprendizaje del usuario")
    cantidad: int = Field(5, description="Cantidad de ítems a recomendar")


class DificultadRequest(BaseModel):
    texto: str = Field(..., description="Texto a analizar")
    nivel_objetivo: Optional[int] = Field(None, description="Nivel deseado (1-5)")


class DificultadResponse(BaseModel):
    nivel_dificultad: int
    etiqueta: str
    puntaje_legibilidad: float
    total_palabras: int
    palabras_complejas: list[str]
    silabas_por_palabra: float
    requiere_adaptacion: bool = False
    sugerencias: list[str] = []


class TrazoRequest(BaseModel):
    puntos: list[dict] = Field(..., description="Puntos del trazo [{x, y, timestamp, presion}]")
    letra: str = Field(..., description="Letra que se intentaba trazar")
    ancho_canvas: float = Field(..., description="Ancho del canvas en píxeles")
    alto_canvas: float = Field(..., description="Alto del canvas en píxeles")
    tolerancia: str = Field("media", description="Nivel de tolerancia: baja, media, alta")


class TrazoResponse(BaseModel):
    letra_detectada: str
    confianza: float
    desviacion_promedio: float
    porcentaje_dentro_margen: float
    trazo_completo: bool
    tolerancia_sugerida: str
    correcto: bool


# ─── Endpoints ───

@app.get("/health")
async def health():
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
async def evaluar_pronunciacion(
    audio: UploadFile = File(..., description="Archivo de audio del usuario"),
    texto_esperado: str = "",
):
    """
    Evalúa la pronunciación del usuario comparándola con el texto esperado.
    Usado por HU-06: Lectura en voz alta con feedback.
    """
    if not stt:
        raise HTTPException(503, "Modelo STT no disponible")

    # Guardar audio temporal
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        contenido = await audio.read()
        tmp.write(contenido)
        tmp_path = tmp.name

    try:
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
async def evaluar_fonema(
    audio: UploadFile = File(...),
    fonema_esperado: str = "",
):
    """
    Evalúa la pronunciación de un fonema aislado.
    Usado por HU-03: Asociación fonema-grafema.
    """
    if not stt:
        raise HTTPException(503, "Modelo STT no disponible")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        contenido = await audio.read()
        tmp.write(contenido)
        tmp_path = tmp.name

    try:
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
async def obtener_siguiente_leccion(request: ProximaLeccionRequest):
    """
    Recomienda los próximos ítems a practicar basándose en el historial.
    Usado por HU-05: Ajuste dinámico de dificultad.
    """
    if not adaptativo:
        raise HTTPException(503, "Modelo adaptativo no disponible")

    # Reconstruir ItemAprendizaje desde los dicts
    items = []
    for item_dict in request.items:
        item = ItemAprendizaje(
            item_id=item_dict.get("item_id", ""),
            tipo=item_dict.get("tipo", "fonema"),
            aciertos=item_dict.get("aciertos", 0),
            fallos=item_dict.get("fallos", 0),
            racha_actual=item_dict.get("racha_actual", 0),
            factor_facilidad=item_dict.get("factor_facilidad", 2.5),
            intervalo_dias=item_dict.get("intervalo_dias", 1.0),
        )
        items.append(item)

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
async def analizar_dificultad(request: DificultadRequest):
    """
    Analiza la dificultad de un texto en español.
    Usado por HU-04 y HU-17 para adaptar contenido al nivel del usuario.
    """
    if not clasificador:
        raise HTTPException(503, "Clasificador no disponible")

    if request.nivel_objetivo:
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
async def analizar_trazo(request: TrazoRequest):
    """
    Analiza el trazo de una letra dibujada por el usuario.
    Usado por HU-02 y HU-13.
    """
    if not analizador:
        raise HTTPException(503, "Analizador no disponible")

    # Convertir puntos
    puntos = [
        PuntoTrazo(
            x=p["x"],
            y=p["y"],
            timestamp=p.get("timestamp", 0),
            presion=p.get("presion", 1.0),
        )
        for p in request.puntos
    ]

    # Obtener ruta ideal
    rutas = analizador._generar_rutas_vocales()
    letra_upper = request.letra.upper()

    if letra_upper not in rutas:
        raise HTTPException(400, f"No hay ruta ideal para '{request.letra}'")

    ruta = RutaIdeal(
        letra=letra_upper,
        puntos=rutas[letra_upper],
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
