"""
Pipeline de datos Kedro: ETL desde Firestore + Feature Engineering + Entrenamiento.

Este pipeline se ejecuta periódicamente (via Airflow) para:
1. Extraer datos de uso desde Firestore
2. Transformar en features para entrenamiento
3. Re-entrenar el modelo adaptativo con datos frescos
4. Registrar métricas y modelo en MLflow
"""

from kedro.pipeline import Pipeline, pipeline, node

from .nodes import (
    extraer_datos_firestore,
    limpiar_y_transformar,
    generar_features_adaptativo,
    generar_resumen_desempeno,
    entrenar_modelo_adaptativo,
    evaluar_y_registrar,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Pipeline principal de entrenamiento ML."""

    return pipeline([
        # ── Etapa 1: Extracción (ETL) ──
        node(
            func=extraer_datos_firestore,
            inputs=["params:firebase_project_id"],
            outputs="datos_crudos",
            name="extraer_datos",
            tags=["etl"],
        ),

        # ── Etapa 2: Limpieza y transformación ──
        node(
            func=limpiar_y_transformar,
            inputs=["datos_crudos"],
            outputs="datos_limpios",
            name="limpiar_datos",
            tags=["etl", "transform"],
        ),

        # ── Etapa 3: Feature Engineering ──
        node(
            func=generar_features_adaptativo,
            inputs=["datos_limpios"],
            outputs="features_adaptativo",
            name="features_algoritmo_adaptativo",
            tags=["features"],
        ),
        node(
            func=generar_resumen_desempeno,
            inputs=["datos_limpios"],
            outputs="resumen_desempeno",
            name="resumen_desempeno",
            tags=["features"],
        ),

        # ── Etapa 4: Entrenamiento ──
        node(
            func=entrenar_modelo_adaptativo,
            inputs=["features_adaptativo", "params:modelo_adaptativo"],
            outputs="resultado_adaptativo",
            name="entrenar_adaptativo",
            tags=["training"],
        ),

        # ── Etapa 5: Evaluación y registro en MLflow ──
        node(
            func=evaluar_y_registrar,
            inputs=["resultado_adaptativo", "features_adaptativo", "resumen_desempeno"],
            outputs=None,
            name="evaluar_registrar",
            tags=["evaluation", "mlflow"],
        ),
    ])
