# -*- coding: utf-8 -*-
"""
Pipeline de Feature Engineering para Pino ML.
Calcula variables derivadas: ratios fonema-sílaba, índice cinemático de grafomotricidad,
índice de decaimiento por intervalo SM-2 y features para predicción de riesgo PISA.
"""

import pandas as pd
import numpy as np

def construir_features_adaptativas(df: pd.DataFrame) -> pd.DataFrame:
    """Construye las features para el modelo adaptativo GradientBoosting."""
    df_out = df.copy()
    
    # Ratios de balance
    df_out["ratio_silaba_fonema"] = df_out["tasa_acierto_silabas"] / np.clip(df_out["tasa_acierto_fonemas"], 0.05, 1.0)
    
    # Índice de estabilidad grafomotora
    df_out["indice_estabilidad_motriz"] = df_out["cobertura_promedio_trazo"] / (1.0 + df_out["desviacion_promedio_trazo"] / 20.0)
    
    # Factor de saturación cognitiva (alta latencia + bajo acierto = sobrecarga de memoria de trabajo)
    df_out["sobrecarga_cognitiva"] = (df_out["latencia_media_respuesta_seg"] / 3.0) * (1.0 - df_out["tasa_acierto_fonemas"])
    
    return df_out

def preparar_matriz_pisa_entrenamiento(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Prepara matriz de características X e y para entrenar el clasificador de riesgo."""
    df_feat = construir_features_adaptativas(df)
    
    feature_cols = [
        "tasa_acierto_fonemas",
        "tasa_acierto_silabas",
        "desviacion_promedio_trazo",
        "cobertura_promedio_trazo",
        "latencia_media_respuesta_seg",
        "palabras_por_minuto",
        "tasa_error_pronunciacion",
        "dias_activos_racha",
        "ratio_silaba_fonema",
        "indice_estabilidad_motriz",
        "sobrecarga_cognitiva",
    ]
    
    X = df_feat[feature_cols]
    y = df_feat["fallo_siguiente"]
    return X, y
