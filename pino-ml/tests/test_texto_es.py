import pytest

from pino_ml.utils.texto_es import (
    contar_silabas,
    normalizar,
    palabra_a_fonemas,
    separar_silabas,
)


def test_normalizar_quita_puntuacion_y_tildes():
    assert normalizar("¡Mamá!  ¿Dónde está?") == "mama donde esta"
    assert normalizar("Niño.", quitar_tildes=False) == "niño"


@pytest.mark.parametrize("palabra, silabas", [
    ("casa", ["ca", "sa"]),
    ("mamá", ["ma", "má"]),
    ("perro", ["pe", "rro"]),
    ("árbol", ["ár", "bol"]),
    ("plato", ["pla", "to"]),
    ("agua", ["a", "gua"]),
    ("poeta", ["po", "e", "ta"]),
    ("día", ["dí", "a"]),
    ("instante", ["ins", "tan", "te"]),
    ("guitarra", ["gui", "ta", "rra"]),
    ("queso", ["que", "so"]),
    ("pingüino", ["pin", "güi", "no"]),
    ("muchacho", ["mu", "cha", "cho"]),
    ("llave", ["lla", "ve"]),
    ("huevo", ["hue", "vo"]),
    ("ahora", ["a", "ho", "ra"]),
    ("rey", ["rey"]),
    ("mayo", ["ma", "yo"]),
    ("abstracto", ["abs", "trac", "to"]),
    ("ciudad", ["ciu", "dad"]),
])
def test_separar_silabas(palabra, silabas):
    assert separar_silabas(palabra) == silabas


def test_contar_silabas_respeta_hiatos():
    assert contar_silabas("leer") == 2
    assert contar_silabas("país") == 2
    assert contar_silabas("aire") == 2


@pytest.mark.parametrize("palabra, fonemas", [
    ("mamá", ["/m/", "/a/", "/m/", "/a/"]),
    ("casa", ["/k/", "/a/", "/s/", "/a/"]),
    ("cine", ["/s/", "/i/", "/n/", "/e/"]),
    ("gato", ["/g/", "/a/", "/t/", "/o/"]),
    ("gente", ["/x/", "/e/", "/n/", "/t/", "/e/"]),
    ("guerra", ["/g/", "/e/", "/r/", "/a/"]),
    ("queso", ["/k/", "/e/", "/s/", "/o/"]),
    ("agua", ["/a/", "/g/", "/u/", "/a/"]),
    ("rana", ["/r/", "/a/", "/n/", "/a/"]),
    ("pera", ["/p/", "/e/", "/ɾ/", "/a/"]),
    ("honra", ["/o/", "/n/", "/r/", "/a/"]),
    ("hoy", ["/o/", "/i/"]),
])
def test_palabra_a_fonemas(palabra, fonemas):
    assert palabra_a_fonemas(palabra) == fonemas
