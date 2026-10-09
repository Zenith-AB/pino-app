import pytest

from pino_ml.models.analizador_trazos import AnalizadorTrazos, PuntoTrazo, RutaIdeal

ANCHO = ALTO = 400


@pytest.fixture
def analizador():
    return AnalizadorTrazos()


def ruta(analizador, letra, ancho=ANCHO, alto=ALTO):
    return RutaIdeal(letra, analizador.rutas_ideales[letra], ancho, alto)


def trazo_perfecto(analizador, letra, ancho=ANCHO, alto=ALTO, pasos=40):
    """Recorre cada segmento de la ruta ideal con puntos densos, en píxeles."""
    puntos, t = [], 0
    for trazo in analizador.rutas_ideales[letra]:
        for (x0, y0), (x1, y1) in zip(trazo[:-1], trazo[1:]):
            for k in range(pasos + 1):
                f = k / pasos
                puntos.append(PuntoTrazo((x0 + f * (x1 - x0)) * ancho,
                                         (y0 + f * (y1 - y0)) * alto, t))
                t += 10
    return puntos


@pytest.mark.parametrize("letra", ["A", "E", "I", "O", "U"])
def test_trazo_perfecto_es_correcto(analizador, letra):
    r = analizador.analizar_trazo(trazo_perfecto(analizador, letra), ruta(analizador, letra))

    assert r.porcentaje_dentro_margen == 100.0
    assert r.desviacion_maxima == 0.0
    assert r.trazo_completo
    assert r.confianza == 1.0
    assert r.segmentos_problematicos == []


def test_trazo_perfecto_en_canvas_no_cuadrado(analizador):
    r = analizador.analizar_trazo(
        trazo_perfecto(analizador, "E", ancho=300, alto=600),
        ruta(analizador, "E", ancho=300, alto=600),
    )
    assert r.confianza == 1.0


def test_trazo_incompleto_no_es_completo(analizador):
    # Solo la línea vertical de la "E"
    puntos = [PuntoTrazo(0.3 * ANCHO, (0.1 + 0.8 * k / 40) * ALTO, k * 10) for k in range(41)]

    r = analizador.analizar_trazo(puntos, ruta(analizador, "E"))

    assert r.porcentaje_dentro_margen == 100.0
    assert not r.trazo_completo


def test_la_a_tiene_el_vertice_arriba(analizador):
    # En pantalla y crece hacia abajo: el vértice de la A debe tener la y menor.
    ys = [y for trazo in analizador.rutas_ideales["A"] for _, y in trazo]
    vertice = analizador.rutas_ideales["A"][0][0]
    assert vertice[1] == min(ys)


def test_desvio_al_final_se_reporta(analizador):
    puntos = trazo_perfecto(analizador, "I")
    # Al terminar, el usuario se sale 100 px a la derecha
    puntos += [PuntoTrazo(0.5 * ANCHO + 100, 0.9 * ALTO, 9999)]

    r = analizador.analizar_trazo(puntos, ruta(analizador, "I"))

    assert len(r.segmentos_problematicos) == 1
    assert r.segmentos_problematicos[0]["desviacion_max"] == pytest.approx(100.0 - 0.15 * ANCHO, abs=0.5)


def test_la_tolerancia_cambia_el_margen(analizador):
    # Tramo central de la vertical de la "I" desplazado 20 px (lejos de las serifas):
    # dentro de "media" (30), fuera de "baja" (15)
    puntos = [PuntoTrazo(0.5 * ANCHO + 20, (0.3 + 0.4 * k / 40) * ALTO, k * 10) for k in range(41)]

    baja = analizador.analizar_trazo(puntos, ruta(analizador, "I"), "baja")
    media = analizador.analizar_trazo(puntos, ruta(analizador, "I"), "media")

    assert baja.porcentaje_dentro_margen < media.porcentaje_dentro_margen
    assert media.desviacion_promedio == pytest.approx(20.0, abs=0.1)


def test_sin_puntos(analizador):
    r = analizador.analizar_trazo([], ruta(analizador, "A"))
    assert r.confianza == 0.0
    assert not r.trazo_completo
