# -*- coding: utf-8 -*-
"""
Pipeline de Ingesta y Validación de Datos para Pino ML.
Carga datos de telemetría de usuarios (Firestore o mocks locales), datasets de alfabetización
Our World in Data y tablas normativas de la OCDE / PISA.
"""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from pino_ml.settings import settings

def cargar_datasets_macro() -> pd.DataFrame:
    """Carga y valida el dataset integrado de alfabetización y penetración móvil."""
    p = settings.processed_data_dir / "macro_literacy_tech_pisa_integrated.csv"
    if not p.exists():
        raise FileNotFoundError(f"No existe el archivo procesado en {p}")
    df = pd.read_csv(p)
    # Validaciones mínimas
    assert "Literacy_Rate" in df.columns
    assert "Mobile_Subscriptions_Per_100" in df.columns
    return df

def cargar_datasets_pisa() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Carga las tablas históricas y de niveles de competencia PISA."""
    hist_p = settings.raw_data_dir / "pisa_reading_scores_2000_2022.csv"
    levels_p = settings.raw_data_dir / "pisa_proficiency_levels_2022.csv"
    
    df_hist = pd.read_csv(hist_p)
    df_levels = pd.read_csv(levels_p)
    return df_hist, df_levels

def generar_dataset_simulado_telemetria(n_muestras: int = 500) -> pd.DataFrame:
    """
    Genera un dataset sintético realista de telemetría de aprendizaje de Pino
    para entrenamiento y calibración del modelo adaptativo y el motor PISA.
    """
    np.random.seed(42)
    perfiles = [f"perfil_{i}" for i in range(1, 26)]
    
    data = []
    for _ in range(n_muestras):
        perf = np.random.choice(perfiles)
        fon_acc = np.random.beta(5, 2) # Sesgo a rendimiento medio-alto
        sil_acc = np.clip(fon_acc + np.random.normal(0, 0.1), 0.0, 1.0)
        trazo_desv = np.random.gamma(3, 8) # Media ~24px
        trazo_cob = np.random.beta(8, 2)  # Cobertura alta
        latencia = np.random.exponential(1.5) + 1.0
        wpm = np.random.normal(45, 15)
        wpm = max(10.0, wpm)
        wer_pron = np.clip(1.0 - fon_acc + np.random.normal(0, 0.05), 0.0, 1.0)
        racha = int(np.random.geometric(0.2))

        # Target: etiqueta binaria si falló en el siguiente intento
        prob_fallo = (1.0 - fon_acc) * 0.6 + (wer_pron) * 0.3 + (trazo_desv / 100.0) * 0.1
        fallo_siguiente = 1 if np.random.rand() < prob_fallo else 0

        data.append({
            "perfil_id": perf,
            "tasa_acierto_fonemas": round(fon_acc, 3),
            "tasa_acierto_silabas": round(sil_acc, 3),
            "desviacion_promedio_trazo": round(trazo_desv, 1),
            "cobertura_promedio_trazo": round(trazo_cob, 3),
            "latencia_media_respuesta_seg": round(latencia, 2),
            "palabras_por_minuto": round(wpm, 1),
            "tasa_error_pronunciacion": round(wer_pron, 3),
            "dias_activos_racha": racha,
            "fallo_siguiente": fallo_siguiente,
        })

    return pd.DataFrame(data)
