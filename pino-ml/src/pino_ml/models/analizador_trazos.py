# -*- coding: utf-8 -*-
"""
Módulo Analizador de Trazos para Grafomotricidad y Caligrafía Digital.
Analiza trazos manuscritos en pantalla táctil (Flutter Canvas), calcula desviaciones
geométricas, cobertura, velocidad y sugiere tolerancia adaptativa (HU-02, HU-13).
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

Punto = Tuple[float, float]

@dataclass
class PuntoTrazo:
    """Un punto en el trazo del usuario capturado por el canvas."""
    x: float
    y: float
    timestamp: float = 0.0  # Milisegundos desde inicio
    presion: float = 1.0    # Presión táctil (0.0 a 1.0)

@dataclass
class ResultadoTrazo:
    """Resultado del análisis de grafomotricidad."""
    letra_detectada: str
    confianza: float
    desviacion_promedio: float          # Píxeles promedio de desviación
    desviacion_maxima: float            # Píxel máximo de desviación
    porcentaje_dentro_margen: float     # % del trazo dentro del margen
    velocidad_promedio: float           # Píxeles/segundo
    trazo_completo: bool               # Si cubrió la ruta requerida
    tolerancia_sugerida: str            # "baja", "media", "alta"
    segmentos_problematicos: list[dict] # Zonas con mayor desvío

@dataclass
class RutaIdeal:
    """Ruta geométrica ideal para el trazo de una letra."""
    letra: str
    trazos: list[list[Punto]]
    ancho_canvas: float = 300.0
    alto_canvas: float = 300.0

class AnalizadorTrazos:
    """
    Analizador geométrico y cinemático de trazos táctiles.
    """
    PASO_MUESTREO_PX = 5.0
    COBERTURA_MINIMA = 0.75

    def __init__(self):
        self.margenes = {
            'baja': 15.0,    # Exigente / avanzado
            'media': 30.0,   # Estándar
            'alta': 50.0,    # Inclusivo (niños, adultos mayores o motricidad fina reducida)
        }
        self.rutas_ideales = self._generar_rutas_vocales()

    def analizar_trazo(
        self,
        puntos_usuario: list[PuntoTrazo],
        ruta_ideal: RutaIdeal,
        tolerancia: str = "media",
    ) -> ResultadoTrazo:
        """Compara la polilínea del usuario contra la ruta ideal de la letra."""
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

        desviaciones = self._distancias_a_segmentos(usuario, segmentos)
        desviacion_promedio = float(np.mean(desviaciones))
        desviacion_maxima = float(np.max(desviaciones))
        porcentaje_dentro = float(np.mean(desviaciones <= margen))

        velocidad = self._calcular_velocidad(puntos_usuario)
        cobertura = self._calcular_cobertura(usuario, segmentos, margen)
        trazo_completo = cobertura >= self.COBERTURA_MINIMA
        confianza = porcentaje_dentro * cobertura

        problematicos = self._detectar_segmentos_problematicos(usuario, desviaciones, margen)
        tolerancia_sugerida = self._sugerir_tolerancia(porcentaje_dentro)

        return ResultadoTrazo(
            letra_detectada=ruta_ideal.letra,
            confianza=round(float(confianza), 3),
            desviacion_promedio=round(desviacion_promedio, 1),
            desviacion_maxima=round(desviacion_maxima, 1),
            porcentaje_dentro_margen=round(porcentaje_dentro * 100, 1),
            velocidad_promedio=round(velocidad, 1),
            trazo_completo=bool(trazo_completo),
            tolerancia_sugerida=tolerancia_sugerida,
            segmentos_problematicos=problematicos,
        )

    def _segmentos_en_pixeles(self, ruta: RutaIdeal) -> list[tuple[np.ndarray, np.ndarray]]:
        w, h = ruta.ancho_canvas, ruta.alto_canvas
        segmentos = []
        for trazo in ruta.trazos:
            pts = [np.array([x * w, y * h], dtype=float) for x, y in trazo]
            for a, b in zip(pts, pts[1:]):
                segmentos.append((a, b))
        return segmentos

    def _distancias_a_segmentos(
        self,
        puntos: np.ndarray,
        segmentos: list[tuple[np.ndarray, np.ndarray]],
    ) -> np.ndarray:
        if not segmentos:
            return np.zeros(len(puntos))
        distancias_min = np.full(len(puntos), np.inf)
        for a, b in segmentos:
            ab = b - a
            norm_sq = float(np.dot(ab, ab))
            if norm_sq == 0.0:
                d = np.linalg.norm(puntos - a, axis=1)
            else:
                ap = puntos - a
                t = np.clip(np.sum(ap * ab, axis=1) / norm_sq, 0.0, 1.0)
                proy = a + t[:, np.newaxis] * ab
                d = np.linalg.norm(puntos - proy, axis=1)
            distancias_min = np.minimum(distancias_min, d)
        return distancias_min

    def _calcular_velocidad(self, puntos: list[PuntoTrazo]) -> float:
        if len(puntos) < 2:
            return 0.0
        dt = (puntos[-1].timestamp - puntos[0].timestamp) / 1000.0
        if dt <= 0:
            return 0.0
        pts = np.array([(p.x, p.y) for p in puntos])
        distancias = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        return float(np.sum(distancias) / dt)

    def _calcular_cobertura(
        self,
        usuario: np.ndarray,
        segmentos: list[tuple[np.ndarray, np.ndarray]],
        margen: float,
    ) -> float:
        if not segmentos or len(usuario) == 0:
            return 0.0
        muestras = []
        for a, b in segmentos:
            longitud = float(np.linalg.norm(b - a))
            pasos = max(1, int(np.ceil(longitud / self.PASO_MUESTREO_PX)))
            for t in np.linspace(0.0, 1.0, pasos, endpoint=True):
                muestras.append(a + t * (b - a))
        muestras_arr = np.array(muestras)
        dists = self._distancias_puntos_a_puntos(muestras_arr, usuario)
        return float(np.mean(dists <= margen))

    def _distancias_puntos_a_puntos(self, origen: np.ndarray, destino: np.ndarray) -> np.ndarray:
        return np.min(np.linalg.norm(origen[:, np.newaxis, :] - destino[np.newaxis, :, :], axis=2), axis=1)

    def _detectar_segmentos_problematicos(
        self,
        usuario: np.ndarray,
        desviaciones: np.ndarray,
        margen: float,
    ) -> list[dict]:
        problematicos = []
        inicio = None
        for i, desv in enumerate(desviaciones):
            if desv > margen and inicio is None:
                inicio = i
            elif desv <= margen and inicio is not None:
                problematicos.append({
                    'inicio_indice': inicio,
                    'fin_indice': i,
                    'desviacion_max': round(float(np.max(desviaciones[inicio:i])), 1),
                    'punto_usuario': tuple(float(c) for c in usuario[inicio]),
                    'punto_inicio': {'x': float(usuario[inicio][0]), 'y': float(usuario[inicio][1])},
                    'punto_fin': {'x': float(usuario[i - 1][0]), 'y': float(usuario[i - 1][1])},
                })
                inicio = None
        if inicio is not None:
            problematicos.append({
                'inicio_indice': inicio,
                'fin_indice': len(desviaciones),
                'desviacion_max': round(float(np.max(desviaciones[inicio:])), 1),
                'punto_usuario': tuple(float(c) for c in usuario[inicio]),
                'punto_inicio': {'x': float(usuario[inicio][0]), 'y': float(usuario[inicio][1])},
                'punto_fin': {'x': float(usuario[-1][0]), 'y': float(usuario[-1][1])},
            })
        return problematicos[:5]

    def _sugerir_tolerancia(self, porcentaje_dentro: float) -> str:
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
        if len(resultados_recientes) < cantidad_minima:
            return "media"
        porcentajes = [r.porcentaje_dentro_margen for r in resultados_recientes]
        promedio = np.mean(porcentajes)
        if promedio < 50:
            return "alta"
        elif promedio < 75:
            return "media"
        else:
            return "baja"

    def _generar_rutas_vocales(self) -> dict[str, list[list[Punto]]]:
        return {
            'A': [
                [(0.5, 0.1), (0.15, 0.9)],
                [(0.5, 0.1), (0.85, 0.9)],
                [(0.28, 0.6), (0.72, 0.6)],
            ],
            'E': [
                [(0.3, 0.1), (0.3, 0.9)],
                [(0.3, 0.1), (0.7, 0.1)],
                [(0.3, 0.5), (0.6, 0.5)],
                [(0.3, 0.9), (0.7, 0.9)],
            ],
            'I': [
                [(0.5, 0.1), (0.5, 0.9)],
                [(0.35, 0.1), (0.65, 0.1)],
                [(0.35, 0.9), (0.65, 0.9)],
            ],
            'O': [
                [(0.5, 0.1), (0.8, 0.3), (0.8, 0.7),
                 (0.5, 0.9), (0.2, 0.7), (0.2, 0.3),
                 (0.5, 0.1)],
            ],
            'U': [
                [(0.2, 0.1), (0.2, 0.7),
                 (0.5, 0.9), (0.8, 0.7),
                 (0.8, 0.1)],
            ],
        }
