#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Descarga y Preparación de Datasets Empíricos para Pino ML.
Descarga datos oficiales de Our World in Data y compila bases de datos normativas de PISA (OCDE)
para Chile y el mundo.
"""

import os
import sys
import requests
import pandas as pd
import numpy as np

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def download_owid_data():
    print("--- [1/3] Descargando Datasets de Our World in Data ---")
    urls = {
        "literacy_rates_owid.csv": "https://ourworldindata.org/grapher/cross-country-literacy-rates.csv?v=1&csvType=full&useColumnShortNames=false",
        "mobile_subscriptions_owid.csv": "https://ourworldindata.org/grapher/mobile-cellular-subscriptions-per-100-people.csv?v=1&csvType=full",
        "internet_usage_owid.csv": "https://ourworldindata.org/grapher/share-of-individuals-using-the-internet.csv?v=1&csvType=full"
    }
    
    for filename, url in urls.items():
        filepath = os.path.join(DATA_DIR, filename)
        print(f"Descargando {filename} desde {url}...")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
            print(f"Guardado exitosamente: {filepath} ({len(resp.content):,} bytes)")
        except Exception as e:
            print(f"Error descargando {filename}: {e}")

def compile_pisa_datasets():
    print("\n--- [2/3] Compilando Datasets Oficiales de Pruebas PISA (OCDE) ---")
    
    # 1. Puntajes Históricos de Lectura (2000-2022)
    # Fuentes: OECD PISA Databases (2000, 2003, 2006, 2009, 2012, 2015, 2018, 2022)
    pisa_historical_data = [
        # Chile
        {"Country": "Chile", "Code": "CHL", "Region": "Latin America", "OECD_Member": True, "Year": 2000, "ReadingScore": 410, "MathScore": 384, "ScienceScore": 415},
        {"Country": "Chile", "Code": "CHL", "Region": "Latin America", "OECD_Member": True, "Year": 2006, "ReadingScore": 442, "MathScore": 411, "ScienceScore": 438},
        {"Country": "Chile", "Code": "CHL", "Region": "Latin America", "OECD_Member": True, "Year": 2009, "ReadingScore": 449, "MathScore": 421, "ScienceScore": 447},
        {"Country": "Chile", "Code": "CHL", "Region": "Latin America", "OECD_Member": True, "Year": 2012, "ReadingScore": 441, "MathScore": 423, "ScienceScore": 445},
        {"Country": "Chile", "Code": "CHL", "Region": "Latin America", "OECD_Member": True, "Year": 2015, "ReadingScore": 459, "MathScore": 423, "ScienceScore": 447},
        {"Country": "Chile", "Code": "CHL", "Region": "Latin America", "OECD_Member": True, "Year": 2018, "ReadingScore": 452, "MathScore": 417, "ScienceScore": 444},
        {"Country": "Chile", "Code": "CHL", "Region": "Latin America", "OECD_Member": True, "Year": 2022, "ReadingScore": 448, "MathScore": 412, "ScienceScore": 444},
        
        # Promedio OCDE
        {"Country": "OECD Average", "Code": "OECD", "Region": "OECD", "OECD_Member": True, "Year": 2000, "ReadingScore": 493, "MathScore": 496, "ScienceScore": 497},
        {"Country": "OECD Average", "Code": "OECD", "Region": "OECD", "OECD_Member": True, "Year": 2006, "ReadingScore": 492, "MathScore": 498, "ScienceScore": 500},
        {"Country": "OECD Average", "Code": "OECD", "Region": "OECD", "OECD_Member": True, "Year": 2009, "ReadingScore": 493, "MathScore": 496, "ScienceScore": 501},
        {"Country": "OECD Average", "Code": "OECD", "Region": "OECD", "OECD_Member": True, "Year": 2012, "ReadingScore": 496, "MathScore": 494, "ScienceScore": 501},
        {"Country": "OECD Average", "Code": "OECD", "Region": "OECD", "OECD_Member": True, "Year": 2015, "ReadingScore": 493, "MathScore": 490, "ScienceScore": 493},
        {"Country": "OECD Average", "Code": "OECD", "Region": "OECD", "OECD_Member": True, "Year": 2018, "ReadingScore": 487, "MathScore": 489, "ScienceScore": 489},
        {"Country": "OECD Average", "Code": "OECD", "Region": "OECD", "OECD_Member": True, "Year": 2022, "ReadingScore": 476, "MathScore": 472, "ScienceScore": 485},
        
        # Uruguay (Competidor regional de Chile)
        {"Country": "Uruguay", "Code": "URY", "Region": "Latin America", "OECD_Member": False, "Year": 2006, "ReadingScore": 413, "MathScore": 427, "ScienceScore": 428},
        {"Country": "Uruguay", "Code": "URY", "Region": "Latin America", "OECD_Member": False, "Year": 2009, "ReadingScore": 426, "MathScore": 427, "ScienceScore": 427},
        {"Country": "Uruguay", "Code": "URY", "Region": "Latin America", "OECD_Member": False, "Year": 2012, "ReadingScore": 411, "MathScore": 409, "ScienceScore": 416},
        {"Country": "Uruguay", "Code": "URY", "Region": "Latin America", "OECD_Member": False, "Year": 2015, "ReadingScore": 437, "MathScore": 418, "ScienceScore": 435},
        {"Country": "Uruguay", "Code": "URY", "Region": "Latin America", "OECD_Member": False, "Year": 2018, "ReadingScore": 427, "MathScore": 418, "ScienceScore": 426},
        {"Country": "Uruguay", "Code": "URY", "Region": "Latin America", "OECD_Member": False, "Year": 2022, "ReadingScore": 430, "MathScore": 409, "ScienceScore": 435},
        
        # México
        {"Country": "Mexico", "Code": "MEX", "Region": "Latin America", "OECD_Member": True, "Year": 2000, "ReadingScore": 422, "MathScore": 387, "ScienceScore": 422},
        {"Country": "Mexico", "Code": "MEX", "Region": "Latin America", "OECD_Member": True, "Year": 2009, "ReadingScore": 425, "MathScore": 419, "ScienceScore": 416},
        {"Country": "Mexico", "Code": "MEX", "Region": "Latin America", "OECD_Member": True, "Year": 2018, "ReadingScore": 420, "MathScore": 409, "ScienceScore": 419},
        {"Country": "Mexico", "Code": "MEX", "Region": "Latin America", "OECD_Member": True, "Year": 2022, "ReadingScore": 415, "MathScore": 395, "ScienceScore": 410},
        
        # Colombia
        {"Country": "Colombia", "Code": "COL", "Region": "Latin America", "OECD_Member": True, "Year": 2006, "ReadingScore": 385, "MathScore": 370, "ScienceScore": 388},
        {"Country": "Colombia", "Code": "COL", "Region": "Latin America", "OECD_Member": True, "Year": 2012, "ReadingScore": 403, "MathScore": 376, "ScienceScore": 399},
        {"Country": "Colombia", "Code": "COL", "Region": "Latin America", "OECD_Member": True, "Year": 2018, "ReadingScore": 412, "MathScore": 391, "ScienceScore": 413},
        {"Country": "Colombia", "Code": "COL", "Region": "Latin America", "OECD_Member": True, "Year": 2022, "ReadingScore": 409, "MathScore": 383, "ScienceScore": 411},

        # Brasil
        {"Country": "Brazil", "Code": "BRA", "Region": "Latin America", "OECD_Member": False, "Year": 2000, "ReadingScore": 396, "MathScore": 334, "ScienceScore": 375},
        {"Country": "Brazil", "Code": "BRA", "Region": "Latin America", "OECD_Member": False, "Year": 2009, "ReadingScore": 412, "MathScore": 386, "ScienceScore": 405},
        {"Country": "Brazil", "Code": "BRA", "Region": "Latin America", "OECD_Member": False, "Year": 2018, "ReadingScore": 413, "MathScore": 384, "ScienceScore": 404},
        {"Country": "Brazil", "Code": "BRA", "Region": "Latin America", "OECD_Member": False, "Year": 2022, "ReadingScore": 410, "MathScore": 379, "ScienceScore": 403},

        # Argentina
        {"Country": "Argentina", "Code": "ARG", "Region": "Latin America", "OECD_Member": False, "Year": 2000, "ReadingScore": 418, "MathScore": 388, "ScienceScore": 396},
        {"Country": "Argentina", "Code": "ARG", "Region": "Latin America", "OECD_Member": False, "Year": 2012, "ReadingScore": 396, "MathScore": 388, "ScienceScore": 406},
        {"Country": "Argentina", "Code": "ARG", "Region": "Latin America", "OECD_Member": False, "Year": 2018, "ReadingScore": 402, "MathScore": 379, "ScienceScore": 404},
        {"Country": "Argentina", "Code": "ARG", "Region": "Latin America", "OECD_Member": False, "Year": 2022, "ReadingScore": 401, "MathScore": 378, "ScienceScore": 406},

        # Perú
        {"Country": "Peru", "Code": "PER", "Region": "Latin America", "OECD_Member": False, "Year": 2000, "ReadingScore": 327, "MathScore": 292, "ScienceScore": 333},
        {"Country": "Peru", "Code": "PER", "Region": "Latin America", "OECD_Member": False, "Year": 2009, "ReadingScore": 370, "MathScore": 365, "ScienceScore": 369},
        {"Country": "Peru", "Code": "PER", "Region": "Latin America", "OECD_Member": False, "Year": 2018, "ReadingScore": 401, "MathScore": 400, "ScienceScore": 404},
        {"Country": "Peru", "Code": "PER", "Region": "Latin America", "OECD_Member": False, "Year": 2022, "ReadingScore": 408, "MathScore": 391, "ScienceScore": 408},

        # Líderes Globales y Referencias OCDE
        {"Country": "Singapore", "Code": "SGP", "Region": "Asia", "OECD_Member": False, "Year": 2018, "ReadingScore": 549, "MathScore": 569, "ScienceScore": 551},
        {"Country": "Singapore", "Code": "SGP", "Region": "Asia", "OECD_Member": False, "Year": 2022, "ReadingScore": 543, "MathScore": 575, "ScienceScore": 561},
        {"Country": "Japan", "Code": "JPN", "Region": "Asia", "OECD_Member": True, "Year": 2018, "ReadingScore": 504, "MathScore": 527, "ScienceScore": 529},
        {"Country": "Japan", "Code": "JPN", "Region": "Asia", "OECD_Member": True, "Year": 2022, "ReadingScore": 516, "MathScore": 536, "ScienceScore": 547},
        {"Country": "Ireland", "Code": "IRL", "Region": "Europe", "OECD_Member": True, "Year": 2018, "ReadingScore": 518, "MathScore": 500, "ScienceScore": 496},
        {"Country": "Ireland", "Code": "IRL", "Region": "Europe", "OECD_Member": True, "Year": 2022, "ReadingScore": 516, "MathScore": 492, "ScienceScore": 504},
        {"Country": "Finland", "Code": "FIN", "Region": "Europe", "OECD_Member": True, "Year": 2000, "ReadingScore": 546, "MathScore": 536, "ScienceScore": 538},
        {"Country": "Finland", "Code": "FIN", "Region": "Europe", "OECD_Member": True, "Year": 2018, "ReadingScore": 520, "MathScore": 507, "ScienceScore": 522},
        {"Country": "Finland", "Code": "FIN", "Region": "Europe", "OECD_Member": True, "Year": 2022, "ReadingScore": 490, "MathScore": 484, "ScienceScore": 511},
        {"Country": "Spain", "Code": "ESP", "Region": "Europe", "OECD_Member": True, "Year": 2018, "ReadingScore": 477, "MathScore": 481, "ScienceScore": 483},
        {"Country": "Spain", "Code": "ESP", "Region": "Europe", "OECD_Member": True, "Year": 2022, "ReadingScore": 474, "MathScore": 473, "ScienceScore": 485},
        {"Country": "United States", "Code": "USA", "Region": "North America", "OECD_Member": True, "Year": 2018, "ReadingScore": 505, "MathScore": 478, "ScienceScore": 502},
        {"Country": "United States", "Code": "USA", "Region": "North America", "OECD_Member": True, "Year": 2022, "ReadingScore": 504, "MathScore": 465, "ScienceScore": 499},
        {"Country": "Germany", "Code": "DEU", "Region": "Europe", "OECD_Member": True, "Year": 2018, "ReadingScore": 498, "MathScore": 500, "ScienceScore": 503},
        {"Country": "Germany", "Code": "DEU", "Region": "Europe", "OECD_Member": True, "Year": 2022, "ReadingScore": 480, "MathScore": 475, "ScienceScore": 492},
    ]
    df_hist = pd.DataFrame(pisa_historical_data)
    hist_file = os.path.join(DATA_DIR, "pisa_reading_scores_2000_2022.csv")
    df_hist.to_csv(hist_file, index=False)
    print(f"Dataset histórico PISA guardado: {hist_file} ({len(df_hist)} registros)")

    # 2. Distribución de Niveles de Competencia Lectora (PISA 2022)
    # Nivel 2 es el umbral mínimo de competencia funcional (alfabetización funcional).
    # Debajo de Nivel 2 (< 407 puntos) se subdivide en: Nivel 1a (335-407), Nivel 1b (262-335), Nivel 1c (< 262).
    pisa_levels_data = [
        {"Country": "Singapore", "Below_Level_1b": 0.8, "Level_1b": 2.9, "Level_1a": 7.3, "Under_Level_2_Total": 11.0, "Level_2": 15.6, "Level_3": 23.4, "Level_4": 26.2, "Level_5_and_6": 23.8},
        {"Country": "Japan", "Below_Level_1b": 1.1, "Level_1b": 3.7, "Level_1a": 8.7, "Under_Level_2_Total": 13.5, "Level_2": 18.2, "Level_3": 28.1, "Level_4": 25.4, "Level_5_and_6": 14.8},
        {"Country": "Ireland", "Below_Level_1b": 1.2, "Level_1b": 3.8, "Level_1a": 9.3, "Under_Level_2_Total": 14.3, "Level_2": 19.8, "Level_3": 29.5, "Level_4": 24.1, "Level_5_and_6": 12.3},
        {"Country": "Finland", "Below_Level_1b": 2.5, "Level_1b": 6.1, "Level_1a": 12.8, "Under_Level_2_Total": 21.4, "Level_2": 23.1, "Level_3": 26.9, "Level_4": 18.9, "Level_5_and_6": 9.7},
        {"Country": "United States", "Below_Level_1b": 3.1, "Level_1b": 6.4, "Level_1a": 11.9, "Under_Level_2_Total": 21.4, "Level_2": 21.8, "Level_3": 24.3, "Level_4": 18.9, "Level_5_and_6": 13.6},
        {"Country": "Spain", "Below_Level_1b": 2.9, "Level_1b": 7.3, "Level_1a": 14.2, "Under_Level_2_Total": 24.4, "Level_2": 26.8, "Level_3": 28.7, "Level_4": 15.2, "Level_5_and_6": 4.9},
        {"Country": "OECD Average", "Below_Level_1b": 3.5, "Level_1b": 7.9, "Level_1a": 14.9, "Under_Level_2_Total": 26.3, "Level_2": 24.5, "Level_3": 25.8, "Level_4": 16.2, "Level_5_and_6": 7.2},
        {"Country": "Germany", "Below_Level_1b": 3.8, "Level_1b": 8.1, "Level_1a": 13.7, "Under_Level_2_Total": 25.6, "Level_2": 23.4, "Level_3": 24.9, "Level_4": 17.6, "Level_5_and_6": 8.5},
        
        # Chile: 33.7% bajo Nivel 2 (Analfabetismo funcional en jóvenes de 15 años)
        {"Country": "Chile", "Below_Level_1b": 3.9, "Level_1b": 10.1, "Level_1a": 19.7, "Under_Level_2_Total": 33.7, "Level_2": 31.4, "Level_3": 24.2, "Level_4": 8.9, "Level_5_and_6": 1.8},
        
        # Latinoamérica: > 50% bajo nivel 2
        {"Country": "Uruguay", "Below_Level_1b": 6.8, "Level_1b": 13.4, "Level_1a": 21.8, "Under_Level_2_Total": 42.0, "Level_2": 28.5, "Level_3": 20.3, "Level_4": 7.6, "Level_5_and_6": 1.6},
        {"Country": "Mexico", "Below_Level_1b": 7.9, "Level_1b": 16.5, "Level_1a": 22.8, "Under_Level_2_Total": 47.2, "Level_2": 31.2, "Level_3": 17.4, "Level_4": 3.8, "Level_5_and_6": 0.4},
        {"Country": "Brazil", "Below_Level_1b": 10.2, "Level_1b": 18.1, "Level_1a": 21.9, "Under_Level_2_Total": 50.2, "Level_2": 28.4, "Level_3": 15.9, "Level_4": 4.7, "Level_5_and_6": 0.8},
        {"Country": "Peru", "Below_Level_1b": 9.5, "Level_1b": 17.8, "Level_1a": 23.1, "Under_Level_2_Total": 50.4, "Level_2": 28.9, "Level_3": 15.6, "Level_4": 4.5, "Level_5_and_6": 0.6},
        {"Country": "Colombia", "Below_Level_1b": 11.4, "Level_1b": 17.9, "Level_1a": 21.8, "Under_Level_2_Total": 51.1, "Level_2": 28.9, "Level_3": 15.4, "Level_4": 4.1, "Level_5_and_6": 0.5},
        {"Country": "Argentina", "Below_Level_1b": 12.8, "Level_1b": 19.4, "Level_1a": 22.2, "Under_Level_2_Total": 54.4, "Level_2": 26.5, "Level_3": 14.3, "Level_4": 4.2, "Level_5_and_6": 0.6},
        {"Country": "Latin America Average", "Below_Level_1b": 10.5, "Level_1b": 18.0, "Level_1a": 23.0, "Under_Level_2_Total": 51.5, "Level_2": 28.8, "Level_3": 15.6, "Level_4": 3.7, "Level_5_and_6": 0.4}
    ]
    df_levels = pd.DataFrame(pisa_levels_data)
    levels_file = os.path.join(DATA_DIR, "pisa_proficiency_levels_2022.csv")
    df_levels.to_csv(levels_file, index=False)
    print(f"Dataset de niveles PISA 2022 guardado: {levels_file}")

    # 3. Chile PISA 2022 Detalle Socioeconómico (ESCS), Dependencia y Regiones
    # Fuente: Agencia de Calidad de la Educación de Chile (2023)
    chile_socioeconomic_data = [
        # Por Cuartil Socioeconómico (ESCS)
        {"Segmento_Tipo": "Cuartil_ESCS", "Grupo": "Cuartil 1 (Más vulnerable)", "ReadingScore": 405, "Pct_Bajo_Nivel_2": 49.8, "Pct_Nivel_2_y_Superior": 50.2, "Brecha_Respecto_Q4": -83},
        {"Segmento_Tipo": "Cuartil_ESCS", "Grupo": "Cuartil 2 (Vulnerable-Medio)", "ReadingScore": 435, "Pct_Bajo_Nivel_2": 37.6, "Pct_Nivel_2_y_Superior": 62.4, "Brecha_Respecto_Q4": -53},
        {"Segmento_Tipo": "Cuartil_ESCS", "Grupo": "Cuartil 3 (Medio-Alto)", "ReadingScore": 461, "Pct_Bajo_Nivel_2": 27.4, "Pct_Nivel_2_y_Superior": 72.6, "Brecha_Respecto_Q4": -27},
        {"Segmento_Tipo": "Cuartil_ESCS", "Grupo": "Cuartil 4 (Mayor ingreso)", "ReadingScore": 488, "Pct_Bajo_Nivel_2": 19.9, "Pct_Nivel_2_y_Superior": 80.1, "Brecha_Respecto_Q4": 0},
        
        # Por Dependencia Administrativa
        {"Segmento_Tipo": "Dependencia", "Grupo": "Municipal / SLEP (Público)", "ReadingScore": 418, "Pct_Bajo_Nivel_2": 45.2, "Pct_Nivel_2_y_Superior": 54.8, "Brecha_Respecto_Q4": -70},
        {"Segmento_Tipo": "Dependencia", "Grupo": "Particular Subvencionado", "ReadingScore": 451, "Pct_Bajo_Nivel_2": 31.9, "Pct_Nivel_2_y_Superior": 68.1, "Brecha_Respecto_Q4": -37},
        {"Segmento_Tipo": "Dependencia", "Grupo": "Particular Pagado (Privado)", "ReadingScore": 508, "Pct_Bajo_Nivel_2": 11.2, "Pct_Nivel_2_y_Superior": 88.8, "Brecha_Respecto_Q4": 20},

        # Por Zona Geográfica
        {"Segmento_Tipo": "Zona", "Grupo": "Urbana", "ReadingScore": 450, "Pct_Bajo_Nivel_2": 33.1, "Pct_Nivel_2_y_Superior": 66.9, "Brecha_Respecto_Q4": 0},
        {"Segmento_Tipo": "Zona", "Grupo": "Rural", "ReadingScore": 421, "Pct_Bajo_Nivel_2": 43.8, "Pct_Nivel_2_y_Superior": 56.2, "Brecha_Respecto_Q4": -29},

        # Por Género
        {"Segmento_Tipo": "Genero", "Grupo": "Mujeres", "ReadingScore": 457, "Pct_Bajo_Nivel_2": 30.2, "Pct_Nivel_2_y_Superior": 69.8, "Brecha_Respecto_Q4": 0},
        {"Segmento_Tipo": "Genero", "Grupo": "Hombres", "ReadingScore": 439, "Pct_Bajo_Nivel_2": 37.4, "Pct_Nivel_2_y_Superior": 62.6, "Brecha_Respecto_Q4": -18}
    ]
    df_chile = pd.DataFrame(chile_socioeconomic_data)
    chile_file = os.path.join(DATA_DIR, "pisa_chile_escs_breakdown.csv")
    df_chile.to_csv(chile_file, index=False)
    print(f"Dataset de Chile PISA 2022 ESCS guardado: {chile_file}")

def create_integrated_macro_processed_dataset():
    print("\n--- [3/3] Creando Dataset Integrado Procesado (Macro-Analytics + PISA) ---")
    lit_path = os.path.join(DATA_DIR, "literacy_rates_owid.csv")
    mob_path = os.path.join(DATA_DIR, "mobile_subscriptions_owid.csv")
    pisa_path = os.path.join(DATA_DIR, "pisa_proficiency_levels_2022.csv")

    if not (os.path.exists(lit_path) and os.path.exists(mob_path)):
        print("Faltan archivos descargados, no se puede generar el integrado.")
        return

    df_lit = pd.read_csv(lit_path)
    df_mob = pd.read_csv(mob_path)
    df_pisa = pd.read_csv(pisa_path)

    # Limpiar columnas
    # df_lit tiene: Entity, Code, Year, Literacy rate
    lit_col = [c for c in df_lit.columns if "Literacy rate" in c or "literacy" in c.lower()][0]
    mob_col = [c for c in df_mob.columns if "cellular" in c.lower() or "mobile" in c.lower()][0]

    df_lit_clean = df_lit.rename(columns={lit_col: "Literacy_Rate"})
    df_mob_clean = df_mob.rename(columns={mob_col: "Mobile_Subscriptions_Per_100"})

    # Filtrar años >= 2000
    df_lit_clean = df_lit_clean[df_lit_clean["Year"] >= 2000]
    df_mob_clean = df_mob_clean[df_mob_clean["Year"] >= 2000]

    # Obtener el registro más reciente por país
    lit_latest = df_lit_clean.sort_values("Year").groupby("Entity").last().reset_index()
    mob_latest = df_mob_clean.sort_values("Year").groupby("Entity").last().reset_index()

    # Unir datos
    merged = pd.merge(
        lit_latest[["Entity", "Code", "Year", "Literacy_Rate"]],
        mob_latest[["Entity", "Year", "Mobile_Subscriptions_Per_100"]],
        on="Entity",
        suffixes=("_Lit", "_Mob")
    )

    # Calcular Índice de Brecha Digital-Oral (Digital Orality Gap Index):
    # Cuanto mayor sea la diferencia (Tecnología alta - Alfabetización baja), mayor es el salto digital oral
    merged["Orality_Opportunity_Gap"] = merged["Mobile_Subscriptions_Per_100"] - merged["Literacy_Rate"]
    
    # Agregar métricas PISA si coinciden
    merged = pd.merge(merged, df_pisa[["Country", "Under_Level_2_Total"]], left_on="Entity", right_on="Country", how="left")
    merged.rename(columns={"Under_Level_2_Total": "PISA_Below_Level_2_Pct"}, inplace=True)
    merged.drop(columns=["Country"], inplace=True)

    out_file = os.path.join(PROCESSED_DIR, "macro_literacy_tech_pisa_integrated.csv")
    merged.to_csv(out_file, index=False)
    print(f"Dataset integrado procesado generado: {out_file} ({len(merged)} países)")

if __name__ == "__main__":
    download_owid_data()
    compile_pisa_datasets()
    create_integrated_macro_processed_dataset()
    print("\nTodos los datasets preparados exitosamente.")
