# -*- coding: utf-8 -*-
"""
Pipeline de Entrenamiento y Evaluación de Modelos para Pino ML.
Entrena el clasificador Gradient Boosting para el algoritmo adaptativo y
calibra el modelo de riesgo de analfabetismo funcional.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from pino_ml.settings import settings
from pino_ml.pipelines.data_ingestion import generar_dataset_simulado_telemetria
from pino_ml.pipelines.feature_engineering import preparar_matriz_pisa_entrenamiento

def ejecutar_entrenamiento(
    n_muestras: int = 1000,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Entrena y valida el modelo adaptativo y guarda los artefactos."""
    print("Iniciando pipeline de entrenamiento Pino ML...")
    
    # 1. Ingesta
    df_raw = generar_dataset_simulado_telemetria(n_muestras=n_muestras)
    
    # 2. Features
    X, y = preparar_matriz_pisa_entrenamiento(df_raw)
    
    # 3. Split estratificado
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    # 4. Entrenamiento de Gradient Boosting
    clf = GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=4,
        random_state=random_state,
    )
    clf.fit(X_train, y_train)
    
    # 5. Evaluación
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    
    metricas = {
        "n_muestras_total": n_muestras,
        "n_muestras_train": len(X_train),
        "n_muestras_test": len(X_test),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "f1_score": round(float(f1_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred)), 4),
        "recall": round(float(recall_score(y_test, y_pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "importancia_variables": {
            col: round(float(imp), 4)
            for col, imp in zip(X.columns, clf.feature_importances_)
        }
    }
    
    # 6. Guardado de artefactos
    model_path = settings.models_artifact_dir / "modelo_adaptativo_gb.joblib"
    joblib.dump(clf, model_path)
    
    metrics_path = settings.models_artifact_dir / "metricas_entrenamiento.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False)
        
    print(f"Modelo guardado en: {model_path}")
    print(f"Métricas guardadas en: {metrics_path}")
    print(f"Resultados: Accuracy={metricas['accuracy']}, F1={metricas['f1_score']}, AUC={metricas['roc_auc']}")
    
    return metricas

if __name__ == "__main__":
    ejecutar_entrenamiento()
