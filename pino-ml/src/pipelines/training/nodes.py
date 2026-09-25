"""
Nodos del pipeline de entrenamiento.
Cada función es un paso atómico del pipeline Kedro.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Any

import mlflow
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
import firebase_admin
from firebase_admin import credentials, firestore


def extraer_datos_firestore(firebase_project_id: str) -> pd.DataFrame:
    """
    Etapa 1: Extrae datos de ejercicios y progreso desde Firestore.
    Se ejecuta en Databricks o en el servidor de Airflow.
    """
    # Inicializar Firebase si no está inicializado
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {'projectId': firebase_project_id})

    db = firestore.client()

    registros = []

    # Obtener todos los perfiles
    perfiles_ref = db.collection('perfiles')
    perfiles = perfiles_ref.stream()

    for perfil in perfiles:
        perfil_data = perfil.to_dict()
        perfil_id = perfil.id

        # Obtener resultados de ejercicios de cada perfil
        resultados_ref = (
            perfiles_ref.document(perfil_id)
            .collection('resultados')
            .order_by('fecha', direction=firestore.Query.DESCENDING)
            .limit(1000)
        )

        for resultado in resultados_ref.stream():
            r = resultado.to_dict()
            registros.append({
                'perfil_id': perfil_id,
                'modo': perfil_data.get('modo', 'infantil'),
                'nivel': perfil_data.get('nivel', 'preLector'),
                'tipo_ejercicio': r.get('tipo', ''),
                'contenido_id': r.get('contenidoId', ''),
                'correcto': r.get('correcto', False),
                'tiempo_segundos': r.get('tiempoSegundos', 0),
                'fecha': r.get('fecha', ''),
                'racha_dias': perfil_data.get('racha', {}).get('diasConsecutivos', 0),
            })

    df = pd.DataFrame(registros)
    print(f"📊 Extraídos {len(df)} registros de {len(set(df.get('perfil_id', [])))} perfiles")
    return df


def limpiar_y_transformar(datos_crudos: pd.DataFrame) -> pd.DataFrame:
    """
    Etapa 2: Limpia datos nulos, normaliza tipos y agrega columnas derivadas.
    """
    df = datos_crudos.copy()

    # Convertir fecha
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df = df.dropna(subset=['fecha'])

    # Filtrar registros inválidos
    df = df[df['tipo_ejercicio'] != '']

    # Columnas derivadas
    df['hora_del_dia'] = df['fecha'].dt.hour
    df['dia_semana'] = df['fecha'].dt.dayofweek
    df['es_fin_de_semana'] = df['dia_semana'].isin([5, 6])

    # Ordenar por perfil y fecha
    df = df.sort_values(['perfil_id', 'fecha']).reset_index(drop=True)

    # Calcular racha de aciertos por perfil
    df['acierto_previo'] = df.groupby('perfil_id')['correcto'].shift(1).fillna(False)

    print(f"🧹 Datos limpios: {len(df)} registros")
    return df


def generar_features_adaptativo(datos_limpios: pd.DataFrame) -> pd.DataFrame:
    """
    Etapa 3a: Genera features para el modelo de algoritmo adaptativo.
    """
    df = datos_limpios.copy()

    features_por_perfil = []

    for perfil_id, grupo in df.groupby('perfil_id'):
        for contenido_id, sub_grupo in grupo.groupby('contenido_id'):
            total = len(sub_grupo)
            aciertos = sub_grupo['correcto'].sum()
            fallos = total - aciertos

            # Calcular racha actual
            racha = 0
            for _, row in sub_grupo.sort_values('fecha', ascending=False).iterrows():
                if row['correcto']:
                    racha += 1
                else:
                    break

            # Horas desde última práctica
            ultima = sub_grupo['fecha'].max()
            horas = (datetime.now() - ultima).total_seconds() / 3600 if pd.notna(ultima) else 0

            features_por_perfil.append({
                'perfil_id': perfil_id,
                'contenido_id': contenido_id,
                'tasa_acierto': aciertos / max(1, total),
                'aciertos': aciertos,
                'fallos': fallos,
                'racha_actual': racha,
                'intervalo_dias': min(30, horas / 24),
                'factor_facilidad': 2.5 - (fallos * 0.1),  # Estimación
                'horas_desde_practica': horas,
                'total_errores': fallos,
                'errores_confusion': 0,  # TODO: Extraer del detalle
                'errores_pronunciacion': 0,
                # Target: ¿falló en el último intento?
                'target': int(not sub_grupo.sort_values('fecha').iloc[-1]['correcto']),
            })

    result = pd.DataFrame(features_por_perfil)
    print(f"🔧 Features adaptativo: {len(result)} filas, {len(result.columns)} columnas")
    return result


def generar_features_dificultad(datos_limpios: pd.DataFrame) -> pd.DataFrame:
    """
    Etapa 3b: Genera features para el clasificador de dificultad.
    Analiza la relación entre nivel del usuario y tipo de ejercicio exitoso.
    """
    df = datos_limpios.copy()

    # Agrupar por tipo de ejercicio y nivel
    resumen = df.groupby(['tipo_ejercicio', 'nivel']).agg(
        total=('correcto', 'count'),
        aciertos=('correcto', 'sum'),
        tiempo_promedio=('tiempo_segundos', 'mean'),
    ).reset_index()

    resumen['tasa_exito'] = resumen['aciertos'] / resumen['total']

    print(f"🔧 Features dificultad: {len(resumen)} combinaciones tipo-nivel")
    return resumen


def entrenar_modelo_adaptativo(
    features: pd.DataFrame,
    params: dict[str, Any],
) -> GradientBoostingClassifier:
    """
    Etapa 4a: Entrena el modelo predictivo de errores.
    """
    feature_cols = [
        'tasa_acierto', 'aciertos', 'fallos', 'racha_actual',
        'intervalo_dias', 'factor_facilidad', 'horas_desde_practica',
        'total_errores', 'errores_confusion', 'errores_pronunciacion',
    ]

    X = features[feature_cols].fillna(0)
    y = features['target']

    if len(X) < 20:
        print("⚠️ Datos insuficientes para entrenar. Retornando modelo por defecto.")
        modelo = GradientBoostingClassifier(n_estimators=10)
        modelo.fit(X, y)
        return modelo

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=params.get("test_size", 0.2),
        random_state=42,
    )

    modelo = GradientBoostingClassifier(
        n_estimators=params.get("n_estimators", 200),
        max_depth=params.get("max_depth", 4),
        learning_rate=params.get("learning_rate", 0.1),
    )
    modelo.fit(X_train, y_train)

    accuracy = accuracy_score(y_test, modelo.predict(X_test))
    print(f"✅ Modelo adaptativo entrenado — Accuracy: {accuracy:.3f}")

    return modelo


def entrenar_modelo_dificultad(
    features: pd.DataFrame,
    params: dict[str, Any],
) -> RandomForestClassifier:
    """
    Etapa 4b: Entrena el clasificador de dificultad.
    """
    if len(features) < 10:
        print("⚠️ Datos insuficientes para clasificador de dificultad.")
        return RandomForestClassifier(n_estimators=10)

    # Preparar features
    X = features[['total', 'aciertos', 'tiempo_promedio', 'tasa_exito']].fillna(0)

    # Mapear nivel a ordinal
    nivel_map = {'preLector': 1, 'silabico': 2, 'palabras': 3, 'textos': 4}
    y = features['nivel'].map(nivel_map).fillna(1).astype(int)

    modelo = RandomForestClassifier(
        n_estimators=params.get("n_estimators", 100),
        max_depth=params.get("max_depth", 5),
        random_state=42,
    )
    modelo.fit(X, y)

    accuracy = accuracy_score(y, modelo.predict(X))
    print(f"✅ Clasificador dificultad entrenado — Accuracy: {accuracy:.3f}")

    return modelo


def evaluar_y_registrar(
    modelo_adaptativo: GradientBoostingClassifier,
    modelo_dificultad: RandomForestClassifier,
    features_adaptativo: pd.DataFrame,
    features_dificultad: pd.DataFrame,
) -> None:
    """
    Etapa 5: Evalúa modelos finales y registra en MLflow.
    """
    mlflow.set_experiment("pino-training-pipeline")

    with mlflow.start_run(run_name=f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        # Registrar modelo adaptativo
        mlflow.sklearn.log_model(
            modelo_adaptativo,
            artifact_path="modelo_adaptativo",
            registered_model_name="pino-algoritmo-adaptativo",
        )

        # Registrar clasificador de dificultad
        mlflow.sklearn.log_model(
            modelo_dificultad,
            artifact_path="modelo_dificultad",
            registered_model_name="pino-clasificador-dificultad",
        )

        # Métricas generales
        mlflow.log_metrics({
            "total_datos_adaptativo": len(features_adaptativo),
            "total_datos_dificultad": len(features_dificultad),
            "perfiles_unicos": features_adaptativo['perfil_id'].nunique()
            if 'perfil_id' in features_adaptativo.columns else 0,
        })

        print("📦 Modelos registrados en MLflow")
