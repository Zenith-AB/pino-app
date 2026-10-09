import numpy as np
import pandas as pd
import pytest

from pino_ml.pipelines.training.nodes import (
    entrenar_modelo_adaptativo,
    generar_features_adaptativo,
    generar_resumen_desempeno,
    limpiar_y_transformar,
)


def datos_crudos(intentos):
    """intentos: lista de (perfil, contenido, correcto, minutos desde el inicio)."""
    base = pd.Timestamp("2026-03-01T10:00:00Z")
    return pd.DataFrame([
        {
            'perfil_id': perfil,
            'modo': 'infantil',
            'nivel': 'preLector',
            'tipo_ejercicio': 'fonemaEmparejamiento',
            'contenido_id': contenido,
            'correcto': correcto,
            'tiempo_segundos': 3,
            'fecha': base + pd.Timedelta(minutes=minutos),
            'racha_dias': 0,
        }
        for perfil, contenido, correcto, minutos in intentos
    ])


def test_features_solo_usan_intentos_anteriores():
    limpios = limpiar_y_transformar(datos_crudos([
        ('p1', 'fonema_m', True, 0),
        ('p1', 'fonema_m', True, 60),
        ('p1', 'fonema_m', False, 180),
    ]))

    features = generar_features_adaptativo(limpios)

    # El primer intento no tiene historial: no genera fila
    assert len(features) == 2
    ultima = features.iloc[-1]
    # Antes del intento fallido había 2 aciertos y racha 2; el fallo no se cuela
    assert ultima['aciertos'] == 2
    assert ultima['fallos'] == 0
    assert ultima['racha_actual'] == 2
    assert ultima['horas_desde_practica'] == 2.0
    assert ultima['target'] == 1


def test_racha_no_predice_trivialmente_el_target():
    # Con la versión anterior, racha_actual > 0 equivalía a target == 0.
    rng = np.random.default_rng(0)
    intentos = [
        (f'p{p}', f'fonema_{c}', bool(rng.random() < 0.7), k * 30)
        for p in range(5) for c in 'mps' for k in range(8)
    ]
    features = generar_features_adaptativo(limpiar_y_transformar(datos_crudos(intentos)))

    con_racha = features[features['racha_actual'] > 0]
    assert con_racha['target'].nunique() == 2


def test_sin_datos_suficientes_no_hay_modelo():
    features = generar_features_adaptativo(limpiar_y_transformar(datos_crudos([
        ('p1', 'fonema_m', True, 0),
        ('p1', 'fonema_m', False, 60),
    ])))

    resultado = entrenar_modelo_adaptativo(features, {"min_filas": 200})

    assert resultado["modelo"] is None
    assert "filas" in resultado["motivo"]


def test_entrena_y_mide_sobre_perfiles_no_vistos():
    rng = np.random.default_rng(1)
    intentos = [
        (f'p{p}', f'fonema_{c}', bool(rng.random() < 0.6), k * 45)
        for p in range(12) for c in 'mpslnt' for k in range(6)
    ]
    features = generar_features_adaptativo(limpiar_y_transformar(datos_crudos(intentos)))

    resultado = entrenar_modelo_adaptativo(
        features, {"min_filas": 50, "min_perfiles": 5, "n_estimators": 20}
    )

    assert resultado["modelo"] is not None
    m = resultado["metricas"]
    assert m["filas_entrenamiento"] + m["filas_prueba"] == len(features)
    assert 0.0 <= m["accuracy"] <= 1.0


def test_resumen_desempeno():
    limpios = limpiar_y_transformar(datos_crudos([
        ('p1', 'fonema_m', True, 0),
        ('p1', 'fonema_m', False, 60),
    ]))
    resumen = generar_resumen_desempeno(limpios)
    assert resumen.iloc[0]['tasa_exito'] == 0.5
