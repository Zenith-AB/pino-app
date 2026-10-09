from datetime import datetime, timedelta

import pytest

from pino_ml.models.algoritmo_adaptativo import (
    FEATURE_COLS,
    AlgoritmoAdaptativo,
    ItemAprendizaje,
)


@pytest.fixture
def algoritmo():
    return AlgoritmoAdaptativo()


def test_factor_de_facilidad_sube_con_aciertos(algoritmo):
    item = ItemAprendizaje("m", "fonema")
    factores = []
    for _ in range(3):
        algoritmo.actualizar_item(item, True)
        factores.append(item.factor_facilidad)

    assert factores == pytest.approx([2.6, 2.7, 2.8])


def test_factor_de_facilidad_baja_con_fallos_y_tiene_minimo(algoritmo):
    item = ItemAprendizaje("m", "fonema")
    algoritmo.actualizar_item(item, False)
    assert item.factor_facilidad == pytest.approx(2.5 - 0.32)

    for _ in range(10):
        algoritmo.actualizar_item(item, False)
    assert item.factor_facilidad == 1.3


def test_se_recupera_despues_de_fallar(algoritmo):
    item = ItemAprendizaje("m", "fonema")
    algoritmo.actualizar_item(item, False)
    despues_del_fallo = item.factor_facilidad
    for _ in range(4):
        algoritmo.actualizar_item(item, True)
    assert item.factor_facilidad > despues_del_fallo


def test_calidad_explicita(algoritmo):
    item = ItemAprendizaje("m", "fonema")
    algoritmo.actualizar_item(item, True, calidad=4)  # acierto con duda: sin cambio
    assert item.factor_facilidad == pytest.approx(2.5)


def test_cuando_fija_las_fechas(algoritmo):
    item = ItemAprendizaje("m", "fonema")
    cuando = datetime(2026, 3, 1, 10, 0)
    algoritmo.actualizar_item(item, True, cuando=cuando)
    assert item.ultima_practica == cuando
    assert item.proxima_revision == cuando + timedelta(days=1)


def test_features_de_item_respetan_el_orden_del_modelo(algoritmo):
    item = ItemAprendizaje("m", "fonema", ultima_practica=datetime(2026, 3, 1, 10))
    features = AlgoritmoAdaptativo.features_de_item(item, ahora=datetime(2026, 3, 1, 13))
    assert list(features) == FEATURE_COLS
    assert features["horas_desde_practica"] == 3.0
    assert list(algoritmo.preparar_features(item).columns) == FEATURE_COLS


def test_desbloqueo_con_tres_items_recientes_en_racha(algoritmo):
    ahora = datetime.now()
    items = [
        ItemAprendizaje(f"i{k}", "fonema", racha_actual=1,
                        ultima_practica=ahora - timedelta(minutes=k))
        for k in range(3)
    ]
    assert algoritmo.verificar_desbloqueo(items)

    items[0].racha_actual = 0
    assert not algoritmo.verificar_desbloqueo(items)
