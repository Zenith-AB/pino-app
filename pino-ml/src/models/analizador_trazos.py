"""
Modelo 4: Analizador de trazos para grafomotricidad.

Analiza los trazos dibujados por el usuario en pantalla para:
- Reconocer qué letra intentó escribir
- Calcular desviación respecto al trazo ideal
- Sugerir calibración de tolerancia (HU-13)

Usado en: HU-02 (Trazado), HU-13 (Calibración de sensibilidad)
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional

import mlflow
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
import joblib


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
    puntos: list[tuple[float, float]]   # Secuencia de (x, y) normalizados
    ancho_canvas: float
    alto_canvas: float


class AnalizadorTrazos:
    """
    Analiza trazos de escritura en pantalla.
    Compara el trazo del usuario contra rutas ideales predefinidas.
    """

    def __init__(self):
        self.modelo_reconocimiento = None
        self.scaler = StandardScaler()

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

        # Normalizar puntos del usuario al espacio de la ruta ideal
        puntos_norm = self._normalizar_puntos(
            puntos_usuario, ruta_ideal.ancho_canvas, ruta_ideal.alto_canvas
        )

        # Calcular desviaciones punto a punto
        desviaciones = self._calcular_desviaciones(
            puntos_norm, ruta_ideal.puntos
        )

        desviacion_promedio = np.mean(desviaciones) if desviaciones else 999.0
        desviacion_maxima = np.max(desviaciones) if desviaciones else 999.0

        # Porcentaje dentro del margen
        margen_normalizado = margen / max(ruta_ideal.ancho_canvas, ruta_ideal.alto_canvas)
        dentro_margen = sum(1 for d in desviaciones if d <= margen_normalizado)
        porcentaje_dentro = dentro_margen / max(1, len(desviaciones))

        # Velocidad
        velocidad = self._calcular_velocidad(puntos_usuario)

        # Completitud del trazo
        cobertura = self._calcular_cobertura(puntos_norm, ruta_ideal.puntos)
        trazo_completo = cobertura >= 0.75

        # Confianza general
        confianza = porcentaje_dentro * cobertura

        # Detectar segmentos problemáticos
        problematicos = self._detectar_segmentos_problematicos(
            puntos_norm, ruta_ideal.puntos, desviaciones, margen_normalizado
        )

        # Sugerir tolerancia
        tolerancia_sugerida = self._sugerir_tolerancia(
            desviacion_promedio, porcentaje_dentro
        )

        return ResultadoTrazo(
            letra_detectada=ruta_ideal.letra,
            confianza=round(confianza, 3),
            desviacion_promedio=round(
                desviacion_promedio * ruta_ideal.ancho_canvas, 1
            ),
            desviacion_maxima=round(
                desviacion_maxima * ruta_ideal.ancho_canvas, 1
            ),
            porcentaje_dentro_margen=round(porcentaje_dentro * 100, 1),
            velocidad_promedio=round(velocidad, 1),
            trazo_completo=trazo_completo,
            tolerancia_sugerida=tolerancia_sugerida,
            segmentos_problematicos=problematicos,
        )

    def _normalizar_puntos(
        self,
        puntos: list[PuntoTrazo],
        ancho: float,
        alto: float,
    ) -> list[tuple[float, float]]:
        """Normaliza puntos al rango [0, 1]."""
        return [(p.x / ancho, p.y / alto) for p in puntos]

    def _calcular_desviaciones(
        self,
        puntos_usuario: list[tuple[float, float]],
        puntos_ideal: list[tuple[float, float]],
    ) -> list[float]:
        """Calcula la distancia mínima de cada punto del usuario a la ruta ideal."""
        if not puntos_ideal:
            return []

        ideal_array = np.array(puntos_ideal)
        desviaciones = []

        for punto in puntos_usuario:
            punto_arr = np.array(punto)
            distancias = np.linalg.norm(ideal_array - punto_arr, axis=1)
            desviaciones.append(float(np.min(distancias)))

        return desviaciones

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
        puntos_usuario: list[tuple[float, float]],
        puntos_ideal: list[tuple[float, float]],
    ) -> float:
        """
        Calcula qué porcentaje de la ruta ideal fue cubierto por el trazo.
        Divide la ruta en segmentos y verifica cuáles tienen puntos cercanos.
        """
        if not puntos_ideal or not puntos_usuario:
            return 0.0

        usuario_array = np.array(puntos_usuario)
        segmentos_cubiertos = 0
        umbral = 0.05  # 5% del canvas

        for punto_ideal in puntos_ideal:
            punto_arr = np.array(punto_ideal)
            distancias = np.linalg.norm(usuario_array - punto_arr, axis=1)
            if np.min(distancias) <= umbral:
                segmentos_cubiertos += 1

        return segmentos_cubiertos / len(puntos_ideal)

    def _detectar_segmentos_problematicos(
        self,
        puntos_usuario: list[tuple[float, float]],
        puntos_ideal: list[tuple[float, float]],
        desviaciones: list[float],
        margen: float,
    ) -> list[dict]:
        """Identifica zonas donde el usuario se desvió significativamente."""
        problematicos = []
        en_problema = False
        inicio_problema = 0

        for i, desv in enumerate(desviaciones):
            if desv > margen and not en_problema:
                en_problema = True
                inicio_problema = i
            elif desv <= margen and en_problema:
                en_problema = False
                problematicos.append({
                    'inicio_indice': inicio_problema,
                    'fin_indice': i,
                    'desviacion_max': round(max(desviaciones[inicio_problema:i]), 4),
                    'punto_usuario': puntos_usuario[inicio_problema] if inicio_problema < len(puntos_usuario) else None,
                })

        return problematicos[:5]  # Máximo 5 segmentos

    def _sugerir_tolerancia(
        self,
        desviacion_promedio: float,
        porcentaje_dentro: float,
    ) -> str:
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

    def _generar_rutas_vocales(self) -> dict[str, list[tuple[float, float]]]:
        """Genera rutas ideales simplificadas para las vocales."""
        # Coordenadas normalizadas (0-1) de los puntos guía de cada vocal
        return {
            'A': [
                (0.5, 0.9), (0.3, 0.5), (0.15, 0.1),  # Trazo izquierdo
                (0.5, 0.9), (0.7, 0.5), (0.85, 0.1),   # Trazo derecho
                (0.3, 0.5), (0.7, 0.5),                  # Barra horizontal
            ],
            'E': [
                (0.7, 0.1), (0.3, 0.1),                 # Línea superior
                (0.3, 0.1), (0.3, 0.9),                  # Línea vertical
                (0.3, 0.5), (0.6, 0.5),                  # Línea media
                (0.3, 0.9), (0.7, 0.9),                  # Línea inferior
            ],
            'I': [
                (0.5, 0.1), (0.5, 0.9),                 # Línea vertical
                (0.35, 0.1), (0.65, 0.1),                # Serifa superior
                (0.35, 0.9), (0.65, 0.9),                # Serifa inferior
            ],
            'O': [
                (0.5, 0.1), (0.8, 0.3), (0.8, 0.7),    # Lado derecho
                (0.5, 0.9), (0.2, 0.7), (0.2, 0.3),     # Lado izquierdo
                (0.5, 0.1),                               # Cerrar
            ],
            'U': [
                (0.2, 0.1), (0.2, 0.7),                  # Línea izquierda
                (0.2, 0.7), (0.5, 0.9), (0.8, 0.7),     # Curva inferior
                (0.8, 0.7), (0.8, 0.1),                   # Línea derecha
            ],
        }
