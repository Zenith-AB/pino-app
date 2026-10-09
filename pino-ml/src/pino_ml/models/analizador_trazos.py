"""
Modelo 4: Analizador de trazos para grafomotricidad.

Analiza los trazos dibujados por el usuario en pantalla para:
- Calcular desviación respecto al trazo ideal
- Medir qué parte de la letra se recorrió (cobertura)
- Sugerir calibración de tolerancia (HU-13)

Pendiente: reconocer qué letra intentó escribir. Por ahora
`letra_detectada` siempre es la letra esperada.

Convención de coordenadas: la de la pantalla (Flutter), origen arriba a la
izquierda y `y` hacia abajo. Las rutas ideales están normalizadas a [0, 1]
y se escalan al tamaño del canvas; todas las distancias se miden en píxeles.

Usado en: HU-02 (Trazado), HU-13 (Calibración de sensibilidad)
"""

from dataclasses import dataclass

import numpy as np


Punto = tuple[float, float]


@dataclass
class PuntoTrazo:
    """Un punto en el trazo del usuario."""
    x: float
    y: float
    timestamp: float  # Milisegundos desde inicio
    presion: float = 1.0  # Presión del toque (0-1)


@dataclass
class ResultadoTrazo:
    """Resultado del análisis de un trazo."""
    letra_detectada: str
    confianza: float
    desviacion_promedio: float          # Píxeles promedio de desviación
    desviacion_maxima: float            # Píxel máximo de desviación
    porcentaje_dentro_margen: float     # % del trazo dentro del margen
    velocidad_promedio: float           # Píxeles/segundo
    trazo_completo: bool               # Si cubrió toda la ruta
    tolerancia_sugerida: str            # "baja", "media", "alta"
    segmentos_problematicos: list[dict] # Zonas donde se desvió más


@dataclass
class RutaIdeal:
    """Ruta ideal para el trazo de una letra."""
    letra: str
    # Cada trazo es una polilínea de puntos (x, y) normalizados, en el orden
    # en que se dibuja. Los trazos están separados: no se une el final de uno
    # con el inicio del siguiente.
    trazos: list[list[Punto]]
    ancho_canvas: float
    alto_canvas: float


class AnalizadorTrazos:
    """
    Analiza trazos de escritura en pantalla.
    Compara el trazo del usuario contra rutas ideales predefinidas.
    """

    # Separación (en píxeles) entre puntos de muestreo de la ruta ideal
    # para medir la cobertura.
    PASO_MUESTREO_PX = 5.0

    # Fracción mínima de la ruta que hay que recorrer para considerar
    # el trazo completo.
    COBERTURA_MINIMA = 0.75

    def __init__(self):
        # Márgenes de tolerancia en píxeles
        self.margenes = {
            'baja': 15.0,    # Exigente
            'media': 30.0,   # Estándar
            'alta': 50.0,    # Permisivo (niños, adultos mayores)
        }

        # Rutas ideales precargadas (normalizadas 0-1)
        self.rutas_ideales = self._generar_rutas_vocales()

    def analizar_trazo(
        self,
        puntos_usuario: list[PuntoTrazo],
        ruta_ideal: RutaIdeal,
        tolerancia: str = "media",
    ) -> ResultadoTrazo:
        """
        Analiza el trazo del usuario comparándolo con la ruta ideal.
        """
        if not puntos_usuario:
            return ResultadoTrazo(
                letra_detectada="?",
                confianza=0.0,
                desviacion_promedio=999.0,
                desviacion_maxima=999.0,
                porcentaje_dentro_margen=0.0,
                velocidad_promedio=0.0,
                trazo_completo=False,
                tolerancia_sugerida="alta",
                segmentos_problematicos=[],
            )

        margen = self.margenes.get(tolerancia, self.margenes['media'])

        segmentos = self._segmentos_en_pixeles(ruta_ideal)
        usuario = np.array([(p.x, p.y) for p in puntos_usuario], dtype=float)

        # Distancia de cada punto del usuario a la ruta (al segmento más cercano)
        desviaciones = self._distancias_a_segmentos(usuario, segmentos)

        desviacion_promedio = float(np.mean(desviaciones))
        desviacion_maxima = float(np.max(desviaciones))
        porcentaje_dentro = float(np.mean(desviaciones <= margen))

        velocidad = self._calcular_velocidad(puntos_usuario)

        # Completitud: qué parte de la ruta tiene algún punto del usuario cerca
        cobertura = self._calcular_cobertura(usuario, segmentos, margen)
        trazo_completo = cobertura >= self.COBERTURA_MINIMA

        confianza = porcentaje_dentro * cobertura

        problematicos = self._detectar_segmentos_problematicos(
            usuario, desviaciones, margen
        )

        tolerancia_sugerida = self._sugerir_tolerancia(porcentaje_dentro)

        return ResultadoTrazo(
            letra_detectada=ruta_ideal.letra,
            confianza=round(confianza, 3),
            desviacion_promedio=round(desviacion_promedio, 1),
            desviacion_maxima=round(desviacion_maxima, 1),
            porcentaje_dentro_margen=round(porcentaje_dentro * 100, 1),
            velocidad_promedio=round(velocidad, 1),
            trazo_completo=trazo_completo,
            tolerancia_sugerida=tolerancia_sugerida,
            segmentos_problematicos=problematicos,
        )

    def _segmentos_en_pixeles(self, ruta: RutaIdeal) -> np.ndarray:
        """
        Convierte los trazos normalizados en segmentos en píxeles.
        Devuelve un array (N, 2, 2): N segmentos con punto inicial y final.
        """
        escala = np.array([ruta.ancho_canvas, ruta.alto_canvas], dtype=float)
        segmentos = []
        for trazo in ruta.trazos:
            puntos = np.array(trazo, dtype=float) * escala
            if len(puntos) == 1:
                segmentos.append((puntos[0], puntos[0]))
            for a, b in zip(puntos[:-1], puntos[1:]):
                segmentos.append((a, b))
        return np.array(segmentos, dtype=float)

    @staticmethod
    def _distancias_a_segmentos(
        puntos: np.ndarray,
        segmentos: np.ndarray,
    ) -> np.ndarray:
        """Distancia mínima de cada punto (M, 2) al conjunto de segmentos (N, 2, 2)."""
        a = segmentos[:, 0, :]                      # (N, 2)
        ab = segmentos[:, 1, :] - a                 # (N, 2)
        largo2 = np.sum(ab * ab, axis=1)            # (N,)
        largo2 = np.where(largo2 == 0, 1.0, largo2) # segmentos de un solo punto

        ap = puntos[:, None, :] - a[None, :, :]     # (M, N, 2)
        t = np.clip(np.sum(ap * ab[None], axis=2) / largo2[None], 0.0, 1.0)
        proyeccion = a[None] + t[..., None] * ab[None]
        distancias = np.linalg.norm(puntos[:, None, :] - proyeccion, axis=2)
        return distancias.min(axis=1)

    def _calcular_velocidad(self, puntos: list[PuntoTrazo]) -> float:
        """Calcula velocidad promedio en píxeles/segundo."""
        if len(puntos) < 2:
            return 0.0

        distancia_total = 0.0
        for i in range(1, len(puntos)):
            dx = puntos[i].x - puntos[i-1].x
            dy = puntos[i].y - puntos[i-1].y
            distancia_total += np.sqrt(dx**2 + dy**2)

        tiempo_total = (puntos[-1].timestamp - puntos[0].timestamp) / 1000.0
        if tiempo_total <= 0:
            return 0.0

        return distancia_total / tiempo_total

    def _calcular_cobertura(
        self,
        usuario: np.ndarray,
        segmentos: np.ndarray,
        margen: float,
    ) -> float:
        """
        Fracción de la ruta ideal recorrida: se muestrea la ruta cada
        PASO_MUESTREO_PX y se cuenta qué muestras tienen un punto del
        usuario a menos de `margen` píxeles.
        """
        muestras = []
        for a, b in segmentos:
            largo = float(np.linalg.norm(b - a))
            n = max(1, int(np.ceil(largo / self.PASO_MUESTREO_PX)))
            for t in np.linspace(0.0, 1.0, n + 1):
                muestras.append(a + t * (b - a))
        muestras = np.array(muestras)

        distancias = np.linalg.norm(
            muestras[:, None, :] - usuario[None, :, :], axis=2
        ).min(axis=1)
        return float(np.mean(distancias <= margen))

    def _detectar_segmentos_problematicos(
        self,
        usuario: np.ndarray,
        desviaciones: np.ndarray,
        margen: float,
    ) -> list[dict]:
        """Identifica tramos del trazo del usuario fuera del margen."""
        problematicos = []
        inicio = None

        # Se agrega un centinela "dentro del margen" para cerrar un tramo
        # que siga abierto al terminar el trazo.
        for i, desv in enumerate([*desviaciones, 0.0]):
            if desv > margen and inicio is None:
                inicio = i
            elif desv <= margen and inicio is not None:
                problematicos.append({
                    'inicio_indice': inicio,
                    'fin_indice': i,
                    'desviacion_max': round(float(max(desviaciones[inicio:i])), 1),
                    'punto_usuario': tuple(float(c) for c in usuario[inicio]),
                })
                inicio = None

        return problematicos[:5]  # Máximo 5 segmentos

    def _sugerir_tolerancia(self, porcentaje_dentro: float) -> str:
        """
        Sugiere ajuste de tolerancia basándose en el rendimiento (HU-13).
        Si falla mucho por milímetros, subir tolerancia.
        """
        if porcentaje_dentro < 0.4:
            return "alta"
        elif porcentaje_dentro < 0.7:
            return "media"
        else:
            return "baja"

    def calibrar_tolerancia_automatica(
        self,
        resultados_recientes: list[ResultadoTrazo],
        cantidad_minima: int = 5,
    ) -> str:
        """
        Calibración automática basada en los últimos N intentos (HU-13).
        Si el usuario falla repetidamente por desviaciones pequeñas, sube tolerancia.
        """
        if len(resultados_recientes) < cantidad_minima:
            return "media"  # No hay suficientes datos

        porcentajes = [r.porcentaje_dentro_margen for r in resultados_recientes]
        promedio = np.mean(porcentajes)

        # Si consistentemente está entre 40-60%, la tolerancia es demasiado baja
        if promedio < 50:
            return "alta"
        elif promedio < 75:
            return "media"
        else:
            return "baja"

    def _generar_rutas_vocales(self) -> dict[str, list[list[Punto]]]:
        """
        Rutas ideales simplificadas para las vocales mayúsculas.
        Coordenadas normalizadas (0-1) con y hacia abajo (0 = arriba).
        """
        return {
            'A': [
                [(0.5, 0.1), (0.15, 0.9)],               # Trazo izquierdo
                [(0.5, 0.1), (0.85, 0.9)],               # Trazo derecho
                [(0.28, 0.6), (0.72, 0.6)],              # Barra horizontal
            ],
            'E': [
                [(0.3, 0.1), (0.3, 0.9)],                # Línea vertical
                [(0.3, 0.1), (0.7, 0.1)],                # Línea superior
                [(0.3, 0.5), (0.6, 0.5)],                # Línea media
                [(0.3, 0.9), (0.7, 0.9)],                # Línea inferior
            ],
            'I': [
                [(0.5, 0.1), (0.5, 0.9)],                # Línea vertical
                [(0.35, 0.1), (0.65, 0.1)],              # Serifa superior
                [(0.35, 0.9), (0.65, 0.9)],              # Serifa inferior
            ],
            'O': [
                [(0.5, 0.1), (0.8, 0.3), (0.8, 0.7),    # Lado derecho
                 (0.5, 0.9), (0.2, 0.7), (0.2, 0.3),     # Lado izquierdo
                 (0.5, 0.1)],                             # Cerrar
            ],
            'U': [
                [(0.2, 0.1), (0.2, 0.7),                 # Línea izquierda
                 (0.5, 0.9), (0.8, 0.7),                 # Curva inferior
                 (0.8, 0.1)],                             # Línea derecha
            ],
        }
