"""
DAG de Airflow para orquestar el pipeline de entrenamiento ML de Pino.

Ejecuta el pipeline Kedro en un schedule semanal:
1. Extrae datos de Firestore, procesa features y re-entrena (Kedro)
2. Promueve el modelo nuevo a producción solo si mejora al actual
3. Notifica resultado

El entrenamiento corre en la VM de Airflow o en Databricks según la variable
de entorno PINO_USAR_DATABRICKS=1 (se lee al cargar el DAG): nunca en ambos.
"""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


MODELO = 'pino-algoritmo-adaptativo'
ALIAS_PRODUCCION = 'produccion'
# Métrica (registrada por el pipeline en MLflow) con la que se compara el
# modelo nuevo contra el de producción.
METRICA_PROMOCION = 'f1'


# ─── Configuración del DAG ───

default_args = {
    'owner': 'pino-ml-team',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    dag_id='pino_ml_training_pipeline',
    default_args=default_args,
    description='Pipeline semanal de re-entrenamiento de modelos ML para Pino',
    schedule='0 3 * * 0',  # Cada domingo a las 3:00 AM
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['pino', 'ml', 'training'],
)


# ─── Tareas ───

# Tarea 1: Entrenar (Kedro local o job de Databricks, uno solo)
if os.getenv('PINO_USAR_DATABRICKS') == '1':
    from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator

    entrenar = DatabricksRunNowOperator(
        task_id='ejecutar_en_databricks',
        databricks_conn_id='databricks_default',
        job_id='{{ var.value.pino_training_job_id }}',
        notebook_params={
            'pipeline': 'training',
            'firebase_project_id': 'pino-app',
        },
        dag=dag,
    )
else:
    entrenar = BashOperator(
        task_id='ejecutar_pipeline_kedro',
        bash_command=(
            'cd /opt/pino-ml && '
            'kedro run --pipeline training '
            '--params=firebase_project_id=pino-app'
        ),
        dag=dag,
    )


# Tarea 2: Promover a producción solo si el modelo nuevo es mejor
def promover_si_mejora(**kwargs):
    """
    Toma la última versión registrada y le asigna el alias de producción
    solo si su métrica es mayor o igual a la del modelo actual. Si no hay
    modelo en producción, la promueve directamente.
    """
    from mlflow import MlflowClient
    from mlflow.exceptions import MlflowException

    client = MlflowClient()

    versiones = client.search_model_versions(
        f"name='{MODELO}'", order_by=['version_number DESC'], max_results=1
    )
    if not versiones:
        print(f"ℹ️ {MODELO}: no hay versiones registradas todavía.")
        return
    candidata = versiones[0]

    try:
        actual = client.get_model_version_by_alias(MODELO, ALIAS_PRODUCCION)
    except MlflowException:
        actual = None

    if actual is not None and actual.version == candidata.version:
        print(f"ℹ️ {MODELO} v{candidata.version} ya está en producción.")
        return

    metrica_nueva = client.get_run(candidata.run_id).data.metrics.get(METRICA_PROMOCION)
    if metrica_nueva is None:
        print(f"⏭️ {MODELO} v{candidata.version} no tiene '{METRICA_PROMOCION}'; no se promueve.")
        return

    if actual is not None:
        metrica_actual = client.get_run(actual.run_id).data.metrics.get(METRICA_PROMOCION)
        if metrica_actual is not None and metrica_nueva < metrica_actual:
            print(
                f"⏭️ {MODELO} v{candidata.version} ({METRICA_PROMOCION}={metrica_nueva:.3f}) "
                f"no mejora a v{actual.version} ({metrica_actual:.3f}); no se promueve."
            )
            return

    client.set_registered_model_alias(MODELO, ALIAS_PRODUCCION, candidata.version)
    print(f"🚀 {MODELO} v{candidata.version} → alias '{ALIAS_PRODUCCION}'")


promover = PythonOperator(
    task_id='promover_si_mejora',
    python_callable=promover_si_mejora,
    dag=dag,
)

# Tarea 3: Notificar resultado
notificar = BashOperator(
    task_id='notificar_resultado',
    bash_command='echo "✅ Pipeline de entrenamiento ML completado: $(date)"',
    dag=dag,
)


# ─── Dependencias ───
# Flujo: Entrenar → Promover (si mejora) → Notificar
entrenar >> promover >> notificar
