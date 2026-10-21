# -*- coding: utf-8 -*-
"""
Configuración centralizada para Pino ML.
Carga variables de entorno, directorios y parámetros por defecto para modelos e inferencia.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class MLSettings(BaseModel):
    # Entorno
    env: str = Field(default="development")
    debug: bool = Field(default=True)
    
    # Rutas
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    raw_data_dir: Path = BASE_DIR / "data" / "raw"
    processed_data_dir: Path = BASE_DIR / "data" / "processed"
    models_artifact_dir: Path = BASE_DIR / "models_saved"
    visualizations_dir: Path = BASE_DIR / "visualizations"
    
    # Parámetros API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    max_audio_bytes: int = Field(default=10 * 1024 * 1024) # 10 MB
    
    # Whisper / STT
    whisper_model_name: str = Field(default="base") # "tiny", "base", "small", "medium"
    whisper_device: str = Field(default="cpu")
    
    # spaCy NLP
    spacy_model: str = Field(default="es_core_news_md")
    
    # Parámetros del Algoritmo Adaptativo
    sm2_default_easiness: float = Field(default=2.5)
    sm2_min_easiness: float = Field(default=1.3)
    adaptive_model_min_samples: int = Field(default=20)
    
    # Parámetros PISA
    pisa_passing_score: float = Field(default=407.0) # Umbral Nivel 2
    chile_pisa_mean: float = Field(default=448.0)
    oecd_pisa_mean: float = Field(default=476.0)

    model_config = {"arbitrary_types_allowed": True}

settings = MLSettings()
settings.models_artifact_dir.mkdir(parents=True, exist_ok=True)
