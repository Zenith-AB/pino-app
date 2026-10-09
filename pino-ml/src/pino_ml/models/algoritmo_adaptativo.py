"""
Modelo 2: Algoritmo Adaptativo de Aprendizaje.

Implementa repetición espaciada inteligente usando:
- Curva de olvido (Ebbinghaus) personalizada
- Modelo de respuesta al ítem (IRT simplificado)
- Features del historial del usuario para predecir la lección óptima

Usado en: HU-05 (Ajuste dinámico de dificultad)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
import joblib


# Orden de las columnas que espera el modelo de predicción de errores.
FEATURE_COLS = [
    'tasa_acierto', 'aciertos', 'fallos', 'racha_actual',
    'intervalo_dias', 'factor_facilidad', 'horas_desde_practica',
    'total_errores', 'errores_confusion', 'errores_pronunciacion',
]


class TipoError(Enum):
    """Clasificación de errores del usuario."""
    CONFUSION_LETRAS = "confusion_letras"       # b/d, p/q
    LONGITUD_PALABRA = "longitud_palabra"       # Falla en palabras largas
    INFERENCIA = "inferencia"                   # Comprensión lectora
    PRONUNCIACION = "pronunciacion"             # Lectura en voz alta
    DIGRAFO = "digrafo"                        # ch, ll, rr, etc.
    SILABA_INVERSA = "silaba_inversa"          # al, er, is


@dataclass
class ItemAprendizaje:
    """Un ítem (fonema, palabra, texto) con sus métricas de aprendizaje."""
    item_id: str
    tipo: str                           # fonema, silaba, palabra, texto
    aciertos: int = 0
    fallos: int = 0
    racha_actual: int = 0               # Aciertos consecutivos
    ultima_practica: Optional[datetime] = None
    proxima_revision: Optional[datetime] = None
    intervalo_dias: float = 1.0         # Intervalo de repetición actual
    factor_facilidad: float = 2.5       # Factor SM-2
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
    """
    Motor de aprendizaje adaptativo para Pino.

    Combina:
    1. SM-2 (SuperMemo) para repetición espaciada
    2. Gradient Boosting para predecir probabilidad de error
    3. Priorización por debilidades detectadas
    """

    def __init__(self, modelo_path: Optional[str] = None):
        self.modelo_prediccion = None
        if modelo_path:
            self.modelo_prediccion = joblib.load(modelo_path)

    # ─── Repetición espaciada (SM-2 adaptado) ───

    # Calidad de respuesta SM-2 (0-5) cuando no se indica una explícita.
    CALIDAD_ACIERTO = 5
    CALIDAD_FALLO = 2

    @staticmethod
    def _nuevo_factor_facilidad(factor: float, calidad: int) -> float:
        """Fórmula SM-2: EF' = EF + 0.1 - (5-q)·(0.08 + (5-q)·0.02), mínimo 1.3."""
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
        """
        Actualiza un ítem de aprendizaje tras una respuesta.
        Implementa el algoritmo SM-2 con modificaciones para alfabetización.

        `calidad` (0-5) es la calidad de la respuesta de SM-2. Si no se indica,
        se usa CALIDAD_ACIERTO o CALIDAD_FALLO según `correcto`.
        `cuando` es el momento de la respuesta (por defecto, ahora); el
        pipeline de entrenamiento lo usa para reproducir historiales.
        """
        if calidad is None:
            calidad = self.CALIDAD_ACIERTO if correcto else self.CALIDAD_FALLO
        cuando = cuando or datetime.now()
        item.ultima_practica = cuando

        if correcto:
            item.aciertos += 1
            item.racha_actual += 1

            # SM-2: Aumentar intervalo
            if item.racha_actual == 1:
                item.intervalo_dias = 1
            elif item.racha_actual == 2:
                item.intervalo_dias = 3
            else:
                item.intervalo_dias *= item.factor_facilidad
        else:
            item.fallos += 1
            item.racha_actual = 0

            # Registrar tipo de error
            if tipo_error:
                item.errores_tipo.append(tipo_error.value)

            # SM-2: Reiniciar intervalo
            item.intervalo_dias = 1

        item.factor_facilidad = self._nuevo_factor_facilidad(
            item.factor_facilidad, calidad
        )

        # Calcular próxima revisión
        item.proxima_revision = cuando + timedelta(days=item.intervalo_dias)

        return item

    def seleccionar_proxima_leccion(
        self,
        items: list[ItemAprendizaje],
        cantidad: int = 5,
    ) -> list[ItemAprendizaje]:
        """
        Selecciona los próximos ítems a practicar, priorizando:
        1. Ítems que necesitan repaso urgente (vencidos)
        2. Ítems con menor tasa de acierto
        3. Ítems con errores de tipo específico recurrente
        4. Ítems nuevos (nunca practicados)
        """
        ahora = datetime.now()

        def prioridad(item: ItemAprendizaje) -> tuple:
            # Urgencia de repaso (mayor = más urgente)
            if item.proxima_revision and item.proxima_revision < ahora:
                dias_vencido = (ahora - item.proxima_revision).days
                urgencia = dias_vencido + 10  # Bonus por vencido
            elif item.ultima_practica is None:
                urgencia = 5  # Nuevo, prioridad media
            else:
                urgencia = 0

            # Inversión de tasa de acierto (menor acierto = mayor prioridad)
            debilidad = 1.0 - item.tasa_acierto

            # Frecuencia de errores recurrentes
            errores_recurrentes = len(item.errores_tipo)

            return (-urgencia, -debilidad, -errores_recurrentes)

        items_ordenados = sorted(items, key=prioridad)
        return items_ordenados[:cantidad]

    def verificar_desbloqueo(
        self,
        items: list[ItemAprendizaje],
        umbral_consecutivos: int = 3,
    ) -> bool:
        """
        Verifica si el usuario debe desbloquear el siguiente nivel.
        Requiere N ejercicios consecutivos perfectos (HU-05).
        """
        if not items:
            return False

        # Ordenar por última práctica (más reciente primero)
        recientes = sorted(
            [i for i in items if i.ultima_practica],
            key=lambda x: x.ultima_practica,
            reverse=True,
        )

        # Verificar racha en los N más recientes
        consecutivos = 0
        for item in recientes[:umbral_consecutivos]:
            if item.racha_actual > 0:
                consecutivos += 1
            else:
                break

        return consecutivos >= umbral_consecutivos

    # ─── Modelo ML para predicción de errores ───

    @staticmethod
    def features_de_item(
        item: ItemAprendizaje,
        ahora: Optional[datetime] = None,
    ) -> dict[str, float]:
        """
        Features del modelo ML para un ítem, en el momento `ahora`.
        Se usa igual al servir (API) y al entrenar (pipeline), para que el
        modelo vea los mismos valores en ambos casos.
        """
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
        """Convierte un ItemAprendizaje en la fila de features del modelo ML."""
        return pd.DataFrame([self.features_de_item(item)], columns=FEATURE_COLS)

    def predecir_probabilidad_error(
        self,
        item: ItemAprendizaje,
    ) -> float:
        """
        Predice la probabilidad de que el usuario falle este ítem.
        Usa el modelo ML entrenado si existe, sino usa heurística.
        """
        if self.modelo_prediccion:
            features = self.preparar_features(item)
            prob = self.modelo_prediccion.predict_proba(features)[0][1]
            return round(float(prob), 3)

        # Heurística si no hay modelo ML
        base = 1.0 - item.tasa_acierto
        if item.ultima_practica:
            horas = (datetime.now() - item.ultima_practica).total_seconds() / 3600
            decaimiento = min(0.3, horas * 0.01)  # Curva de olvido simplificada
            base = min(1.0, base + decaimiento)

        return round(base, 3)

    # ─── Entrenamiento del modelo ───

    @staticmethod
    def entrenar_modelo(
        datos_historicos: pd.DataFrame,
        experiment_name: str = "pino-algoritmo-adaptativo",
    ) -> GradientBoostingClassifier:
        """
        Entrena el modelo predictivo de errores usando datos históricos.
        Registra el experimento en MLflow.

        Args:
            datos_historicos: DataFrame con columnas:
                - tasa_acierto, aciertos, fallos, racha_actual,
                - intervalo_dias, factor_facilidad, horas_desde_practica,
                - total_errores, errores_confusion, errores_pronunciacion,
                - target (0=acierto, 1=fallo)
        """
        feature_cols = FEATURE_COLS

        X = datos_historicos[feature_cols]
        y = datos_historicos['target']

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Import local: MLflow solo se necesita al entrenar, no al servir la API.
        import mlflow

        # Entrenar con tracking en MLflow
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run(run_name="gradient_boosting_v1"):
            modelo = GradientBoostingClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            )
            modelo.fit(X_train, y_train)

            # Evaluar
            y_pred = modelo.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred)

            # Registrar en MLflow
            mlflow.log_params({
                "n_estimators": 200,
                "max_depth": 4,
                "learning_rate": 0.1,
                "n_features": len(feature_cols),
                "train_size": len(X_train),
            })
            mlflow.log_metrics({
                "accuracy": accuracy,
                "f1_score": f1,
            })
            mlflow.sklearn.log_model(
                modelo,
                artifact_path="modelo_adaptativo",
                registered_model_name="pino-algoritmo-adaptativo",
            )

            print(f"Modelo entrenado — Accuracy: {accuracy:.3f}, F1: {f1:.3f}")

        return modelo
