# -*- coding: utf-8 -*-
"""
Esquemas Pydantic v2 para la API de Machine Learning de Pino.
Garantiza compatibilidad estricta con el cliente Flutter (MLApiClient) y extiende
capacidades analíticas para métricas PISA y macroeconomía educativa.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# --- Schemas para /predict/pronunciacion ---
class SegmentoFoneticoSchema(BaseModel):
    texto: str
    inicio_seg: float
    fin_seg: float
    confianza: float
    fonemas: List[str] = Field(default_factory=list)

class ResultadoPronunciacionSchema(BaseModel):
    texto_esperado: str
    texto_detectado: str
    puntaje_global: float
    word_error_rate: float
    character_error_rate: float
    silabas_correctas: List[str]
    silabas_incorrectas: List[str]
    segmentos: List[SegmentoFoneticoSchema] = Field(default_factory=list)
    similitud_fonetica_global: float = 0.0

# --- Schemas para /predict/fonema ---
class ResultadoFonemaSchema(BaseModel):
    fonema_esperado: str
    correcto: bool
    confianza: float

# --- Schemas para /predict/siguiente-leccion ---
class ItemHistorialSchema(BaseModel):
    item_id: str
    tipo: str = "fonema" # fonema, silaba, palabra, texto
    aciertos: int = 0
    fallos: int = 0
    racha_actual: int = 0
    intervalo_dias: float = 1.0
    factor_facilidad: float = 2.5
    horas_desde_practica: float = 0.0
    errores_tipo: List[str] = Field(default_factory=list)

class SiguienteLeccionRequest(BaseModel):
    historial: List[ItemHistorialSchema]
    modo: str = "infantil" # infantil, adulto
    nivel_actual: int = 1

class SiguienteLeccionResponse(BaseModel):
    siguiente_item_id: str
    tipo: str
    prioridad_repaso: bool
    probabilidad_error_estimada: float
    factor_facilidad: float
    desbloquea_siguiente_nivel: bool
    mensaje_pedagogico: str

# --- Schemas para /predict/dificultad-texto ---
class DificultadTextoRequest(BaseModel):
    texto: str
    nivel_objetivo: Optional[int] = None

class DificultadTextoResponse(BaseModel):
    texto: str
    nivel_dificultad: int
    etiqueta: str
    puntaje_legibilidad: float
    indice_gutierrez: float
    promedio_largo_palabra: float
    promedio_largo_oracion: float
    total_palabras: int
    total_oraciones: int
    palabras_complejas: List[str]
    silabas_por_palabra: float
    vocabulario_unico_ratio: float
    nivel_pisa_estimado: str

# --- Schemas para /analyze/trazo ---
class PuntoInputSchema(BaseModel):
    x: float
    y: float
    timestamp: float = 0.0
    presion: float = 1.0

class TrazoRequest(BaseModel):
    puntos: List[Any] # Puede recibir [[x,y],...] o [{"x":..,"y":..},...]
    letra_esperada: str = "A"
    tolerancia: str = "media" # baja, media, alta
    ancho_canvas: float = 300.0
    alto_canvas: float = 300.0

class TrazoResponse(BaseModel):
    letra_detectada: str
    confianza: float
    desviacion_promedio: float
    desviacion_maxima: float
    porcentaje_dentro_margen: float
    velocidad_promedio: float
    trazo_completo: bool
    tolerancia_sugerida: str
    segmentos_problematicos: List[Dict[str, Any]] = Field(default_factory=list)

# --- Schemas para Predicción de Riesgo PISA ---
class PisaRiskRequest(BaseModel):
    tasa_acierto_fonemas: float = Field(..., ge=0.0, le=1.0)
    tasa_acierto_silabas: float = Field(..., ge=0.0, le=1.0)
    desviacion_promedio_trazo: float = Field(default=25.0)
    cobertura_promedio_trazo: float = Field(default=0.85, ge=0.0, le=1.0)
    latencia_media_respuesta_seg: float = Field(default=2.5, ge=0.0)
    palabras_por_minuto: float = Field(default=45.0, ge=0.0)
    tasa_error_pronunciacion: float = Field(default=0.15, ge=0.0, le=1.0)
    dias_activos_racha: int = Field(default=5, ge=0)

class PisaRiskResponse(BaseModel):
    puntaje_pisa_estimado: float
    nivel_competencia_pisa: str
    probabilidad_bajo_nivel_2: float
    categoria_riesgo: str
    diferencia_con_media_chile: float
    diferencia_con_media_ocde: float
    cuello_botella_cognitivo: str
    desglose_componentes: Dict[str, float]
    intervenciones_recomendadas: List[str]

# --- Schemas para Salud y Analítica ---
class HealthResponse(BaseModel):
    status: str
    version: str
    service: str
    environment: str
    models_status: Dict[str, bool]
