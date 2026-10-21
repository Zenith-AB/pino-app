# -*- coding: utf-8 -*-
"""
Cargador y Gestor de Datos Normativos PISA y Métricas Educativas.
Permite consultar puntajes, distribuciones por niveles de competencia y gradientes socioeconómicos.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
from pino_ml.settings import settings

class PisaDataLoader:
    _instance = None
    
    def __init__(self):
        self.raw_dir = settings.raw_data_dir
        self.processed_dir = settings.processed_data_dir
        self._df_hist: Optional[pd.DataFrame] = None
        self._df_levels: Optional[pd.DataFrame] = None
        self._df_chile: Optional[pd.DataFrame] = None
        self._df_macro: Optional[pd.DataFrame] = None
        self._load_all()

    def _load_all(self):
        hist_p = self.raw_dir / "pisa_reading_scores_2000_2022.csv"
        levels_p = self.raw_dir / "pisa_proficiency_levels_2022.csv"
        chile_p = self.raw_dir / "pisa_chile_escs_breakdown.csv"
        macro_p = self.processed_dir / "macro_literacy_tech_pisa_integrated.csv"

        if hist_p.exists():
            self._df_hist = pd.read_csv(hist_p)
        if levels_p.exists():
            self._df_levels = pd.read_csv(levels_p)
        if chile_p.exists():
            self._df_chile = pd.read_csv(chile_p)
        if macro_p.exists():
            self._df_macro = pd.read_csv(macro_p)

    def get_country_reading_history(self, country: str = "Chile") -> List[Dict[str, Any]]:
        """Retorna la serie histórica de lectura para un país."""
        if self._df_hist is None:
            return []
        sub = self._df_hist[self._df_hist["Country"].str.lower() == country.lower()].sort_values("Year")
        return sub.to_dict(orient="records")

    def get_pisa_levels(self, country: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna la distribución de niveles de competencia PISA 2022."""
        if self._df_levels is None:
            return []
        if country:
            sub = self._df_levels[self._df_levels["Country"].str.lower() == country.lower()]
            return sub.to_dict(orient="records")
        return self._df_levels.to_dict(orient="records")

    def get_chile_socioeconomic_metrics(self) -> Dict[str, Any]:
        """Retorna las métricas del gradiente socioeconómico chileno."""
        if self._df_chile is None:
            return {}
        return {
            "por_cuartil_escs": self._df_chile[self._df_chile["Segmento_Tipo"] == "Cuartil_ESCS"].to_dict(orient="records"),
            "por_dependencia": self._df_chile[self._df_chile["Segmento_Tipo"] == "Dependencia"].to_dict(orient="records"),
            "por_zona": self._df_chile[self._df_chile["Segmento_Tipo"] == "Zona"].to_dict(orient="records"),
            "por_genero": self._df_chile[self._df_chile["Segmento_Tipo"] == "Genero"].to_dict(orient="records"),
        }

    def get_macro_gap_ranking(self, top_n: int = 15) -> List[Dict[str, Any]]:
        """Retorna los países con mayor brecha digital-oral (alta tecnología vs baja alfabetización)."""
        if self._df_macro is None:
            return []
        sorted_macro = self._df_macro.sort_values("Orality_Opportunity_Gap", ascending=False).head(top_n)
        return sorted_macro.to_dict(orient="records")

# Instancia singleton accesible
pisa_data = PisaDataLoader()
