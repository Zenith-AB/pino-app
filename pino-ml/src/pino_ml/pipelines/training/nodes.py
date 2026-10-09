"""
Nodos del pipeline de entrenamiento.
Cada función es un paso atómico del pipeline Kedro.
"""

from datetime import datetime
from typing import Any

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from pino_ml.models.algoritmo_adaptativo import (
    FEATURE_COLS,
    AlgoritmoAdaptativo,
    ItemAprendizaje,
)


def extraer_datos_firestore(firebase_project_id: str) -> pd.DataFrame:
    """
    Etapa 1: Extrae datos de ejercicios y progreso desde Firestore.
    Se ejecuta en Databricks o en el servidor de Airflow.
    """
    # Import local: solo esta etapa necesita Firebase.
    import firebase_admin
    from firebase_admin import credentials, firestore

    # Inicializar Firebase si no está inicializado
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {'projectId': firebase_project_id})

    db = firestore.client()

    registros = []

    # Obtener todos los perfiles de todos los usuarios.
    # Estructura: usuarios/{uid}/perfiles/{syncId}/resultados/{syncId}
    perfiles = db.collection_group('perfiles').stream()

    for perfil in perfiles:
        perfil_data = perfil.to_dict()
        perfil_id = perfil.id  # syncId (UUID), único entre dispositivos

        # Obtener resultados de ejercicios de cada perfil
        resultados_ref = (
            perfil.reference
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

    df = pd.DataFrame(registros, columns=[
        'perfil_id', 'modo', 'nivel', 'tipo_ejercicio', 'contenido_id',
        'correcto', 'tiempo_segundos', 'fecha', 'racha_dias',
    ])
    print(f"📊 Extraídos {len(df)} registros de {df['perfil_id'].nunique()} perfiles")
    return df


def limpiar_y_transformar(datos_crudos: pd.DataFrame) -> pd.DataFrame:
    """
    Etapa 2: Limpia datos nulos, normaliza tipos y agrega columnas derivadas.
    """
    df = datos_crudos.copy()

    # Convertir fecha (Firestore entrega Timestamps con zona horaria → todo a UTC)
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True)
    df = df.dropna(subset=['fecha'])

    # Filtrar registros inválidos
    df = df[df['tipo_ejercicio'] != '']
    df['correcto'] = df['correcto'].astype(bool)

    # Columnas derivadas
    df['hora_del_dia'] = df['fecha'].dt.hour
    df['dia_semana'] = df['fecha'].dt.dayofweek
    df['es_fin_de_semana'] = df['dia_semana'].isin([5, 6])

    # Ordenar por perfil y fecha
    df = df.sort_values(['perfil_id', 'fecha']).reset_index(drop=True)

    # Resultado del intento anterior del mismo perfil
    df['acierto_previo'] = df.groupby('perfil_id')['correcto'].shift(1, fill_value=False)

    print(f"🧹 Datos limpios: {len(df)} registros")
    return df


def generar_features_adaptativo(datos_limpios: pd.DataFrame) -> pd.DataFrame:
    """
    Etapa 3a: Genera features para el modelo de algoritmo adaptativo.

    Una fila por intento, a partir del segundo intento de cada ítem. Las
    features se calculan reproduciendo SM-2 *solo con los intentos anteriores*
    (con la misma función que usa la API) y el target es si ese intento falló.
    Así el modelo nunca ve la respuesta que tiene que predecir.
    """
    algoritmo = AlgoritmoAdaptativo()
    filas = []

    grupos = datos_limpios.sort_values('fecha').groupby(['perfil_id', 'contenido_id'])
    for (perfil_id, contenido_id), intentos in grupos:
        item = ItemAprendizaje(item_id=contenido_id, tipo=intentos['tipo_ejercicio'].iloc[0])

        for intento in intentos.itertuples():
            # Fechas en UTC sin zona, igual para todo el historial
            cuando: datetime = intento.fecha.tz_convert(None).to_pydatetime()

            if item.ultima_practica is not None:
                filas.append({
                    'perfil_id': perfil_id,
                    'contenido_id': contenido_id,
                    'fecha': intento.fecha,
                    **AlgoritmoAdaptativo.features_de_item(item, ahora=cuando),
                    'target': int(not intento.correcto),
                })

            algoritmo.actualizar_item(item, bool(intento.correcto), cuando=cuando)

    result = pd.DataFrame(
        filas, columns=['perfil_id', 'contenido_id', 'fecha', *FEATURE_COLS, 'target']
    )
    print(f"🔧 Features adaptativo: {len(result)} filas, {len(result.columns)} columnas")
    return result


def generar_resumen_desempeno(datos_limpios: pd.DataFrame) -> pd.DataFrame:
    """
    Etapa 3b: Resumen de tasa de éxito por tipo de ejercicio y nivel (para reportes).

    No entrena ningún modelo: el clasificador de dificultad de textos necesita
    textos etiquetados por nivel, no datos de uso de la app.
    """
    resumen = datos_limpios.groupby(['tipo_ejercicio', 'nivel']).agg(
        total=('correcto', 'count'),
        aciertos=('correcto', 'sum'),
        tiempo_promedio=('tiempo_segundos', 'mean'),
    ).reset_index()

    resumen['tasa_exito'] = resumen['aciertos'] / resumen['total']

    print(f"🔧 Resumen de desempeño: {len(resumen)} combinaciones tipo-nivel")
    return resumen


def entrenar_modelo_adaptativo(
    features: pd.DataFrame,
    params: dict[str, Any],
) -> dict[str, Any]:
    """
    Etapa 4: Entrena el modelo predictivo de errores.

    Separa entrenamiento y prueba por perfil (un mismo niño no aparece en
    ambos) y mide sobre la parte de prueba. Si no hay datos suficientes
    devuelve `modelo = None` y el motivo, en vez de un modelo sin entrenar.
    """
    min_filas = params.get("min_filas", 200)
    min_perfiles = params.get("min_perfiles", 5)

    motivo = None
    if len(features) < min_filas:
        motivo = f"{len(features)} filas (mínimo {min_filas})"
    elif features['perfil_id'].nunique() < min_perfiles:
        motivo = f"{features['perfil_id'].nunique()} perfiles (mínimo {min_perfiles})"
    elif features['target'].nunique() < 2:
        motivo = "todos los intentos tienen el mismo resultado"
    if motivo:
        print(f"⚠️ Datos insuficientes para entrenar: {motivo}. No se genera modelo.")
        return {"modelo": None, "metricas": {}, "motivo": motivo}

    X = features[FEATURE_COLS].fillna(0)
    y = features['target']

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=params.get("test_size", 0.2),
        random_state=42,
    )
    train_idx, test_idx = next(splitter.split(X, y, groups=features['perfil_id']))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    if y_train.nunique() < 2:
        motivo = "la parte de entrenamiento tiene un solo resultado"
        print(f"⚠️ {motivo}. No se genera modelo.")
        return {"modelo": None, "metricas": {}, "motivo": motivo}

    modelo = GradientBoostingClassifier(
        n_estimators=params.get("n_estimators", 200),
        max_depth=params.get("max_depth", 4),
        learning_rate=params.get("learning_rate", 0.1),
        random_state=42,
    )
    modelo.fit(X_train, y_train)

    y_pred = modelo.predict(X_test)
    metricas = {
        "accuracy": accuracy_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "filas_entrenamiento": len(X_train),
        "filas_prueba": len(X_test),
    }
    if y_test.nunique() == 2:
        metricas["roc_auc"] = roc_auc_score(y_test, modelo.predict_proba(X_test)[:, 1])

    print(f"✅ Modelo adaptativo entrenado — {metricas}")
    return {"modelo": modelo, "metricas": metricas, "motivo": None}


def evaluar_y_registrar(
    resultado_adaptativo: dict[str, Any],
    features_adaptativo: pd.DataFrame,
    resumen_desempeno: pd.DataFrame,
) -> None:
    """
    Etapa 5: Registra métricas en MLflow y, si hay modelo, lo registra.
    La promoción a producción la decide el DAG comparando métricas.
    """
    import mlflow

    mlflow.set_experiment("pino-training-pipeline")

    with mlflow.start_run(run_name=f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        mlflow.log_metrics({
            "total_datos_adaptativo": len(features_adaptativo),
            "perfiles_unicos": features_adaptativo['perfil_id'].nunique(),
            **resultado_adaptativo["metricas"],
        })
        mlflow.log_text(
            resumen_desempeno.to_csv(index=False), "resumen_desempeno.csv"
        )

        modelo = resultado_adaptativo["modelo"]
        if modelo is None:
            mlflow.set_tag("modelo_registrado", "no")
            mlflow.set_tag("motivo", resultado_adaptativo["motivo"])
            print(f"⏭️ Sin modelo nuevo: {resultado_adaptativo['motivo']}")
            return

        mlflow.set_tag("modelo_registrado", "si")
        mlflow.sklearn.log_model(
            modelo,
            artifact_path="modelo_adaptativo",
            registered_model_name="pino-algoritmo-adaptativo",
        )
        print("📦 Modelo registrado en MLflow")
