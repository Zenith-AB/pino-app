# -*- coding: utf-8 -*-
"""
Módulo Algoritmo Adaptativo de Aprendizaje para Pino ML.
Implementa repetición espaciada inteligente (SuperMemo SM-2 personalizado) combinada con
un estimador Gradient Boosting para predecir fallos y optimizar la secuencia de lecciones (HU-05).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
import joblib

FEATURE_COLS = [
    'tasa_acierto', 'aciertos', 'fallos', 'racha_actual',
    'intervalo_dias', 'factor_facilidad', 'horas_desde_practica',
    'total_errores', 'errores_confusion', 'errores_pronunciacion',
]

class TipoError(Enum):
    CONFUSION_LETRAS = "confusion_letras"
    LONGITUD_PALABRA = "longitud_palabra"
    INFERENCIA = "inferencia"
    PRONUNCIACION = "pronunciacion"
    DIGRAFO = "digrafo"
    SILABA_INVERSA = "silaba_inversa"

@dataclass
class ItemAprendizaje:
    item_id: str
    tipo: str  # fonema, silaba, palabra, texto
    aciertos: int = 0
    fallos: int = 0
    racha_actual: int = 0
    ultima_practica: Optional[datetime] = None
    proxima_revision: Optional[datetime] = None
    intervalo_dias: float = 1.0
    factor_facilidad: float = 2.5
    errores_tipo: list[str] = field(default_factory=list)

    @property
    def tasa_acierto(self) -> float:
        total = self.aciertos + self.fallos
        return self.aciertos / total if total > 0 else 0.0

    @property
    def necesita_repaso(self) -> bool:
        if self.proxima_revision is None:
            return True
        return datetime.now() >= self.proxima_revision

class AlgoritmoAdaptativo:
    CALIDAD_ACIERTO = 5
    CALIDAD_FALLO = 2

    def __init__(self, modelo_path: Optional[str] = None):
        self.modelo_prediccion = None
        if modelo_path:
            try:
                self.modelo_prediccion = joblib.load(modelo_path)
            except Exception:
                self.modelo_prediccion = None

    @staticmethod
    def _nuevo_factor_facilidad(factor: float, calidad: int) -> float:
        q = 5 - calidad
        return max(1.3, factor + 0.1 - q * (0.08 + q * 0.02))

    def actualizar_item(
        self,
        item: ItemAprendizaje,
        correcto: bool,
        tipo_error: Optional[TipoError] = None,
        calidad: Optional[int] = None,
        cuando: Optional[datetime] = None,
    ) -> ItemAprendizaje:
        if calidad is None:
            calidad = self.CALIDAD_ACIERTO if correcto else self.CALIDAD_FALLO
        cuando = cuando or datetime.now()
        item.ultima_practica = cuando

        if correcto:
            item.aciertos += 1
            item.racha_actual += 1
            if item.racha_actual == 1:
                item.intervalo_dias = 1.0
            elif item.racha_actual == 2:
                item.intervalo_dias = 6.0
            else:
                item.intervalo_dias = round(item.intervalo_dias * item.factor_facilidad, 1)
        else:
            item.fallos += 1
            item.racha_actual = 0
            item.intervalo_dias = 1.0
            if tipo_error:
                item.errores_tipo.append(tipo_error.value)

        item.factor_facilidad = round(self._nuevo_factor_facilidad(item.factor_facilidad, calidad), 2)
        item.proxima_revision = cuando + timedelta(days=item.intervalo_dias)
        return item

    def seleccionar_proxima_leccion(
        self,
        items: list[ItemAprendizaje],
        cantidad: int = 5,
    ) -> list[ItemAprendizaje]:
        ahora = datetime.now()

        def prioridad(item: ItemAprendizaje) -> tuple:
            if item.proxima_revision and item.proxima_revision < ahora:
                dias_vencido = (ahora - item.proxima_revision).days
                urgencia = dias_vencido + 10
            elif item.ultima_practica is None:
                urgencia = 5
            else:
                urgencia = 0
            debilidad = 1.0 - item.tasa_acierto
            errores_recurrentes = len(item.errores_tipo)
            return (-urgencia, -debilidad, -errores_recurrentes)

        items_ordenados = sorted(items, key=prioridad)
        return items_ordenados[:cantidad]

    def verificar_desbloqueo(
        self,
        items: list[ItemAprendizaje],
        umbral_consecutivos: int = 3,
    ) -> bool:
        if not items:
            return False
        recientes = sorted(
            [i for i in items if i.ultima_practica],
            key=lambda x: x.ultima_practica,
            reverse=True,
        )
        consecutivos = 0
        for item in recientes[:umbral_consecutivos]:
            if item.racha_actual > 0:
                consecutivos += 1
            else:
                break
        return consecutivos >= umbral_consecutivos

    @staticmethod
    def features_de_item(
        item: ItemAprendizaje,
        ahora: Optional[datetime] = None,
    ) -> dict[str, float]:
        ahora = ahora or datetime.now()
        horas_desde_practica = 0.0
        if item.ultima_practica:
            horas_desde_practica = (ahora - item.ultima_practica).total_seconds() / 3600
        return {
            'tasa_acierto': item.tasa_acierto,
            'aciertos': item.aciertos,
            'fallos': item.fallos,
            'racha_actual': item.racha_actual,
            'intervalo_dias': item.intervalo_dias,
            'factor_facilidad': item.factor_facilidad,
            'horas_desde_practica': horas_desde_practica,
            'total_errores': len(item.errores_tipo),
            'errores_confusion': item.errores_tipo.count(TipoError.CONFUSION_LETRAS.value),
            'errores_pronunciacion': item.errores_tipo.count(TipoError.PRONUNCIACION.value),
        }

    def preparar_features(self, item: ItemAprendizaje) -> pd.DataFrame:
        return pd.DataFrame([self.features_de_item(item)], columns=FEATURE_COLS)

    def predecir_probabilidad_error(self, item: ItemAprendizaje) -> float:
        if self.modelo_prediccion:
            features = self.preparar_features(item)
            prob = self.modelo_prediccion.predict_proba(features)[0][1]
            return round(float(prob), 3)
        base = 1.0 - item.tasa_acierto
        if item.ultima_practica:
            horas = (datetime.now() - item.ultima_practica).total_seconds() / 3600
            decaimiento = min(0.3, horas * 0.01)
            base = min(1.0, base + decaimiento)
        return round(base, 3)

    def extraer_features(self, item: ItemAprendizaje) -> dict:
        return self.features_de_item(item)

    def estimar_probabilidad_error(self, item: ItemAprendizaje) -> float:
        return self.predecir_probabilidad_error(item)

    def seleccionar_siguiente_item(
        self,
        candidatos: list[ItemAprendizaje],
        estrategia: str = "repaso_inteligente",
    ) -> Optional[ItemAprendizaje]:
        res = self.seleccionar_proxima_leccion(candidatos, cantidad=1)
        return res[0] if res else None

    @staticmethod
    def entrenar_modelo(
        datos_historicos: pd.DataFrame,
        experiment_name: str = "pino-algoritmo-adaptativo",
    ) -> GradientBoostingClassifier:
        feature_cols = FEATURE_COLS
        X = datos_historicos[feature_cols]
        y = datos_historicos['target']
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        modelo = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
        )
        modelo.fit(X_train, y_train)
        return modelo
