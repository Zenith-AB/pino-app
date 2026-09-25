"""
Pipeline de datos Kedro: ETL desde Firestore + Feature Engineering + Entrenamiento.

Este pipeline se ejecuta periódicamente (via Airflow) para:
1. Extraer datos de uso desde Firestore
2. Transformar en features para entrenamiento
3. Re-entrenar los modelos con datos frescos
4. Registrar modelos en MLflow
"""

from kedro.pipeline import Pipeline, pipeline, node

from .nodes import (
    extraer_datos_firestore,
    limpiar_y_transformar,
    generar_features_adaptativo,
    generar_features_dificultad,
    entrenar_modelo_adaptativo,
    entrenar_modelo_dificultad,
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
            func=generar_features_dificultad,
            inputs=["datos_limpios"],
            outputs="features_dificultad",
            name="features_clasificador_dificultad",
            tags=["features"],
        ),

        # ── Etapa 4: Entrenamiento ──
        node(
            func=entrenar_modelo_adaptativo,
            inputs=["features_adaptativo", "params:modelo_adaptativo"],
            outputs="modelo_adaptativo",
            name="entrenar_adaptativo",
            tags=["training"],
        ),
        node(
            func=entrenar_modelo_dificultad,
            inputs=["features_dificultad", "params:modelo_dificultad"],
            outputs="modelo_dificultad",
            name="entrenar_dificultad",
            tags=["training"],
        ),

        # ── Etapa 5: Evaluación y registro en MLflow ──
        node(
            func=evaluar_y_registrar,
            inputs=["modelo_adaptativo", "modelo_dificultad", "features_adaptativo", "features_dificultad"],
            outputs=None,
            name="evaluar_registrar",
            tags=["evaluation", "mlflow"],
        ),
    ])
