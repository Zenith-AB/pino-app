"""Registro de pipelines del proyecto Kedro."""

from kedro.pipeline import Pipeline

from pino_ml.pipelines.training.pipeline import create_pipeline as crear_pipeline_training


def register_pipelines() -> dict[str, Pipeline]:
    """Pipelines disponibles para `kedro run --pipeline <nombre>`."""
    training = crear_pipeline_training()
    return {
        "training": training,
        "__default__": training,
    }
