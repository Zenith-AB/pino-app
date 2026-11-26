"""Prueba el modelo real de edad de adquisición. Se omite si faltan sus dependencias."""

import pytest

sklearn = pytest.importorskip("sklearn")
pytest.importorskip("openpyxl")

from pino_ml.models.edad_adquisicion import EdadAdquisicion  # noqa: E402

pytestmark = pytest.mark.skipif(
    sklearn.__version__ != "1.9.1", reason="los .joblib requieren scikit-learn 1.9.1"
)


@pytest.fixture(scope="module")
def modelo():
    return EdadAdquisicion()


def test_palabra_con_norma_usa_la_norma(modelo):
    r = modelo.analizar("Perro", "es")
    assert r["origen"] == "norma" and r["nivel"] == 1
    assert r["silabas"] == ["pe", "rro"]


def test_palabra_nueva_usa_el_modelo(modelo):
    r = modelo.analizar("pikachu", "en")
    assert r["origen"] == "modelo"
    assert r["edad_anios"] == r["edad_modelo"]
    assert 1 <= r["nivel"] <= 5


@pytest.mark.parametrize("texto", ["", "dos palabras", "abc123", "a" * 41])
def test_rechaza_lo_que_no_es_una_palabra(modelo, texto):
    with pytest.raises(ValueError):
        modelo.analizar(texto, "es")
