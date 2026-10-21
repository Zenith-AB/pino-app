# -*- coding: utf-8 -*-
"""
Módulo de Analítica Macroeconómica y Justificación Empírica para Pino ML.
Modela la 'Paradoja de la Digitalización Oral', la brecha tecnológica y
el índice de oportunidad de mercado educativo global.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from pino_ml.settings import settings
from pino_ml.utils.pisa_data_loader import pisa_data

@dataclass
class PaisOportunidadEducativa:
    pais: str
    tasa_alfabetizacion: float
    suscripciones_moviles_x100: float
    brecha_oralidad_digital: float     # Móviles - Alfabetización
    tasa_analfabetismo_funcional_pisa: Optional[float]
    indice_oportunidad_pino: float     # 0 a 100
    categoria_estrategica: str         # "Salto Digital Primario", "Cierre Brecha Funcional", "Convergencia"
    justificacion_tecnica: str

class MacroAnalyticsEngine:
    """
    Motor analítico que formaliza matemáticamente los hallazgos de exploracionedapino.py
    y los cruza con los requerimientos pedagógicos de PISA.
    """

    def __init__(self):
        self.loader = pisa_data

    def calcular_indice_oportunidad(
        self,
        alfabetizacion: float,
        moviles: float,
        pisa_bajo_nivel_2: Optional[float] = None,
    ) -> tuple[float, str, str]:
        """
        Calcula el Índice de Oportunidad de Pino (IOP):
        IOP = 0.5 * (Brecha_Oralidad) + 0.3 * (Urgencia_Educativa) + 0.2 * (Penetracion_Movil)
        """
        brecha_oralidad = max(0.0, moviles - alfabetizacion)
        urgencia = 100.0 - alfabetizacion
        if pisa_bajo_nivel_2 is not None and not np.isnan(pisa_bajo_nivel_2):
            urgencia = max(urgencia, pisa_bajo_nivel_2)

        # Normalización a 100
        score = (
            min(100.0, brecha_oralidad * 1.2) * 0.45 +
            min(100.0, urgencia * 1.5) * 0.35 +
            min(100.0, moviles) * 0.20
        )
        score = float(np.clip(score, 0.0, 100.0))

        if alfabetizacion < 70 and moviles >= 80:
            categoria = "Salto Digital Primario (Alta Urgencia + Alta Infraestructura)"
            justificacion = (
                "Población con adopción masiva de smartphones pero excluida de la lectoescritura formal. "
                "La interfaz basada en audio de Pino permite el salto directo sin requerir escuelas físicas adicionales."
            )
        elif alfabetizacion >= 95 and (pisa_bajo_nivel_2 is not None and pisa_bajo_nivel_2 > 25):
            categoria = "Cierre de Brecha Funcional (Países Emergentes / Chile)"
            justificacion = (
                "Alfabetización básica casi universal (~98%), pero alto analfabetismo funcional en PISA (~34% en Chile). "
                "El foco de Pino debe ser la fluidez, discriminación fonológica fina y comprensión autónoma."
            )
        else:
            categoria = "Convergencia y Consolidación"
            justificacion = (
                "Mercado con crecimiento equilibrado; Pino actúa como refuerzo pedagógico escolar y familiar."
            )

        return round(score, 1), categoria, justificacion

    def obtener_ranking_global(self, top_n: int = 20) -> List[PaisOportunidadEducativa]:
        """Genera el ranking estructurado de países prioritarios."""
        ranking_raw = self.loader.get_macro_gap_ranking(top_n=top_n)
        resultado = []

        for row in ranking_raw:
            pais = row.get("Entity", "Desconocido")
            lit = float(row.get("Literacy_Rate", 0.0))
            mob = float(row.get("Mobile_Subscriptions_Per_100", 0.0))
            gap = float(row.get("Orality_Opportunity_Gap", 0.0))
            pisa_val = row.get("PISA_Below_Level_2_Pct", None)
            if pd.isna(pisa_val):
                pisa_val = None
            else:
                pisa_val = float(pisa_val)

            iop, cat, just = self.calcular_indice_oportunidad(lit, mob, pisa_val)

            resultado.append(PaisOportunidadEducativa(
                pais=pais,
                tasa_alfabetizacion=round(lit, 1),
                suscripciones_moviles_x100=round(mob, 1),
                brecha_oralidad_digital=round(gap, 1),
                tasa_analfabetismo_funcional_pisa=round(pisa_val, 1) if pisa_val else None,
                indice_oportunidad_pino=iop,
                categoria_estrategica=cat,
                justificacion_tecnica=just,
            ))

        resultado.sort(key=lambda x: x.indice_oportunidad_pino, reverse=True)
        return resultado

# Instancia singleton
macro_analytics_engine = MacroAnalyticsEngine()
