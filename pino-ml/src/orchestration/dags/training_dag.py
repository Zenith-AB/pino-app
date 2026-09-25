"""
DAG de Airflow para orquestar el pipeline de entrenamiento ML de Pino.

Ejecuta el pipeline Kedro en un schedule semanal:
1. Extrae datos de Firestore
2. Procesa features
3. Re-entrena modelos
4. Registra en MLflow
5. Notifica resultado

Puede ejecutarse localmente o en Databricks via operadores dedicados.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator
from airflow.utils.dates import days_ago


# ─── Configuración del DAG ───

default_args = {
    'owner': 'pino-ml-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    dag_id='pino_ml_training_pipeline',
    default_args=default_args,
    description='Pipeline semanal de re-entrenamiento de modelos ML para Pino',
    schedule_interval='0 3 * * 0',  # Cada domingo a las 3:00 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['pino', 'ml', 'training'],
)


# ─── Tareas ───

# Tarea 1: Ejecutar pipeline Kedro completo (entorno local/VM)
ejecutar_kedro_local = BashOperator(
    task_id='ejecutar_pipeline_kedro',
    bash_command=(
        'cd /opt/pino-ml && '
        'kedro run --pipeline training '
        '--params firebase_project_id:pino-app'
    ),
    dag=dag,
)

# Tarea 2 (alternativa): Ejecutar en Databricks
ejecutar_en_databricks = DatabricksRunNowOperator(
    task_id='ejecutar_en_databricks',
    databricks_conn_id='databricks_default',
    job_id='{{ var.value.pino_training_job_id }}',
    notebook_params={
        'pipeline': 'training',
        'firebase_project_id': 'pino-app',
    },
    dag=dag,
)

# Tarea 3: Verificar que los modelos se registraron en MLflow
def verificar_modelos_mlflow(**kwargs):
    """Verifica que los modelos se registraron correctamente."""
    import mlflow

    client = mlflow.tracking.MlflowClient()

    modelos_requeridos = [
        'pino-algoritmo-adaptativo',
        'pino-clasificador-dificultad',
    ]

    for nombre in modelos_requeridos:
        try:
            versiones = client.get_latest_versions(nombre)
            ultima = versiones[0] if versiones else None
            if ultima:
                print(f"✅ {nombre}: versión {ultima.version}, estado: {ultima.current_stage}")
            else:
                raise Exception(f"❌ No se encontró versión para {nombre}")
        except Exception as e:
            raise Exception(f"Error verificando modelo {nombre}: {e}")

verificar_modelos = PythonOperator(
    task_id='verificar_modelos_mlflow',
    python_callable=verificar_modelos_mlflow,
    dag=dag,
)

# Tarea 4: Promover modelos a producción
def promover_modelos(**kwargs):
    """Promueve la última versión de cada modelo a 'Production' en MLflow."""
    import mlflow

    client = mlflow.tracking.MlflowClient()

    modelos = ['pino-algoritmo-adaptativo', 'pino-clasificador-dificultad']

    for nombre in modelos:
        versiones = client.get_latest_versions(nombre, stages=['None'])
        if versiones:
            version = versiones[0].version
            client.transition_model_version_stage(
                name=nombre,
                version=version,
                stage='Production',
                archive_existing_versions=True,
            )
            print(f"🚀 {nombre} v{version} → Production")

promover = PythonOperator(
    task_id='promover_modelos_produccion',
    python_callable=promover_modelos,
    dag=dag,
)

# Tarea 5: Notificar resultado
notificar = BashOperator(
    task_id='notificar_resultado',
    bash_command='echo "✅ Pipeline de entrenamiento ML completado: $(date)"',
    dag=dag,
)


# ─── Dependencias ───
# Flujo: Kedro → Verificar → Promover → Notificar
ejecutar_kedro_local >> verificar_modelos >> promover >> notificar
