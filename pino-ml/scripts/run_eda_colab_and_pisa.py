#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Análisis Unificado: EDA Colab Pino + Estudios PISA en Chile y el Mundo.
Genera análisis estadísticos y visualizaciones científicas en el directorio visualizations/.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Renderizado sin interfaz gráfica
import matplotlib.pyplot as plt

# Directorios de trabajo
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
VIS_DIR = os.path.join(BASE_DIR, "visualizations")
os.makedirs(VIS_DIR, exist_ok=True)

# Estilo visual moderno y limpio para gráficos
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#e0e0e0'
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.7

def generate_eda_colab_charts():
    print("=== [1/2] Generando Visualizaciones de los Estudios EDA Colab ===")
    
    lit_file = os.path.join(DATA_DIR, "literacy_rates_owid.csv")
    mob_file = os.path.join(DATA_DIR, "mobile_subscriptions_owid.csv")
    
    if not os.path.exists(lit_file) or not os.path.exists(mob_file):
        print("Error: Datasets no encontrados. Ejecuta download_and_prepare_datasets.py primero.")
        return

    df_lit = pd.read_csv(lit_file)
    df_mob = pd.read_csv(mob_file)
    
    lit_col = [c for c in df_lit.columns if "Literacy rate" in c or "literacy" in c.lower()][0]
    mob_col = [c for c in df_mob.columns if "cellular" in c.lower() or "mobile" in c.lower()][0]

    df_lit = df_lit.rename(columns={lit_col: "Literacy_Rate"})
    df_mob = df_mob.rename(columns={mob_col: "Mobile_Subs"})
    df_lit_post2000 = df_lit[df_lit["Year"] >= 2000]

    # 1. Distribución Global de Alfabetización
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(df_lit_post2000["Literacy_Rate"].dropna(), bins=25, color="#3498db", edgecolor="#2980b9", alpha=0.85)
    mean_val = df_lit_post2000["Literacy_Rate"].mean()
    median_val = df_lit_post2000["Literacy_Rate"].median()
    ax.axvline(mean_val, color="#e74c3c", linestyle="--", linewidth=2, label=f"Media Global ({mean_val:.1f}%)")
    ax.axvline(median_val, color="#2ecc71", linestyle="-.", linewidth=2, label=f"Mediana Global ({median_val:.1f}%)")
    ax.set_title("Distribución Global de Tasas de Alfabetización (2000 - Presente)", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Tasa de Alfabetización (%)", fontsize=12)
    ax.set_ylabel("Frecuencia (Observaciones País-Año)", fontsize=12)
    ax.legend(frameon=True, facecolor="white", edgecolor="#e0e0e0")
    ax.grid(True)
    plt.tight_layout()
    fig.savefig(os.path.join(VIS_DIR, "01_global_literacy_distribution.png"), dpi=300)
    plt.close()
    print("Guardado: 01_global_literacy_distribution.png")

    # 2. Top 15 Países con Menor Tasa de Alfabetización
    latest_lit = df_lit_post2000.sort_values("Year").groupby("Entity").last().reset_index()
    # Filtrar entidades que no sean países agregados
    non_countries = ["World", "Africa", "Asia", "Europe", "South America", "Northern America", "Low income", "Lower middle income"]
    latest_countries = latest_lit[~latest_lit["Entity"].isin(non_countries)]
    bottom_15 = latest_countries.sort_values("Literacy_Rate").head(15)

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(bottom_15["Entity"], bottom_15["Literacy_Rate"], color="#e74c3c", alpha=0.85, edgecolor="#c0392b")
    ax.set_xlim(0, 100)
    ax.set_title("Top 15 Países con Menor Tasa de Alfabetización (Registros Recientes)", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Tasa de Alfabetización (%)", fontsize=12)
    ax.set_ylabel("País", fontsize=12)
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 1.5, bar.get_y() + bar.get_height()/2, f"{w:.1f}%", va='center', fontsize=10, fontweight='bold', color="#2c3e50")
    ax.grid(axis='x')
    plt.tight_layout()
    fig.savefig(os.path.join(VIS_DIR, "02_bottom_15_literacy_countries.png"), dpi=300)
    plt.close()
    print("Guardado: 02_bottom_15_literacy_countries.png")

    # 3. Convergencia de Alfabetización en 18 Países
    paises_convergencia = [
        "Argentina", "Brazil", "Chile", "China", "Colombia", "Costa Rica",
        "Hungary", "Indonesia", "Italy", "Mexico", "Panama", "Paraguay",
        "Peru", "Poland", "Portugal", "Spain", "Turkey", "Uruguay"
    ]
    df_conv = df_lit_post2000[df_lit_post2000["Entity"].isin(paises_convergencia)]
    
    fig, ax = plt.subplots(figsize=(13, 7))
    for p in paises_convergencia:
        sub = df_conv[df_conv["Entity"] == p].sort_values("Year")
        if len(sub) > 1:
            line_width = 3 if p == "Chile" else 1.5
            alpha = 1.0 if p == "Chile" else 0.6
            color = "#e74c3c" if p == "Chile" else None
            ax.plot(sub["Year"], sub["Literacy_Rate"], marker="o", markersize=4, label=p, linewidth=line_width, alpha=alpha, color=color)
    ax.set_ylim(85, 101)
    ax.set_title("Convergencia de la Alfabetización: 18 Países con Datos Frecuentes (Destacado: Chile)", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Año", fontsize=12)
    ax.set_ylabel("Tasa de Alfabetización (%)", fontsize=12)
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', ncol=1, frameon=True, fontsize=9)
    ax.grid(True)
    plt.tight_layout()
    fig.savefig(os.path.join(VIS_DIR, "03_literacy_convergence_countries.png"), dpi=300)
    plt.close()
    print("Guardado: 03_literacy_convergence_countries.png")

    # 4. Caso de India: Salto Tecnológico vs Progreso Educativo
    df_india_lit = df_lit_post2000[df_lit_post2000["Entity"] == "India"].sort_values("Year")
    df_india_mob = df_mob[(df_mob["Entity"] == "India") & (df_mob["Year"] >= 2000)].sort_values("Year")

    fig, ax1 = plt.subplots(figsize=(12, 6))
    line1 = ax1.plot(df_india_mob["Year"], df_india_mob["Mobile_Subs"], color="#2980b9", marker="s", linewidth=2.5, label="Suscripciones Móviles (por 100 hab)")
    ax1.set_ylabel("Suscripciones Móviles (por 100 hab)", color="#2980b9", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Año", fontsize=12)
    ax1.tick_params(axis='y', labelcolor="#2980b9")
    ax1.grid(True)

    ax2 = ax1.twinx()
    line2 = ax2.plot(df_india_lit["Year"], df_india_lit["Literacy_Rate"], color="#e74c3c", marker="o", linewidth=3.5, label="Tasa de Alfabetización (%)")
    ax2.set_ylabel("Tasa de Alfabetización (%)", color="#e74c3c", fontsize=12, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor="#e74c3c")
    ax2.set_ylim(50, 100)

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", frameon=True, facecolor="white")
    plt.title("India: El Desacople Tecnológico-Educativo (Infraestructura Móvil vs Alfabetización)", fontsize=14, fontweight='bold', pad=15)
    plt.tight_layout()
    fig.savefig(os.path.join(VIS_DIR, "04_india_leapfrog_tech_vs_literacy.png"), dpi=300)
    plt.close()
    print("Guardado: 04_india_leapfrog_tech_vs_literacy.png")

    # 5. Paradoja de la Digitalización Oral: África Occidental (Senegal y Costa de Marfil)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    paises_foco = ["Cote d'Ivoire", "Senegal"]
    nombres_es = ["Costa de Marfil", "Senegal"]

    for i, pais in enumerate(paises_foco):
        ax = ax1 if i == 0 else ax2
        t_data = df_mob[(df_mob["Entity"] == pais) & (df_mob["Year"] >= 2000)].sort_values("Year")
        l_data = df_lit_post2000[df_lit_post2000["Entity"] == pais].sort_values("Year")

        ax_twin = ax.twinx()
        p1 = ax.plot(t_data["Year"], t_data["Mobile_Subs"], color="#8e44ad", marker="s", linewidth=2.5, label="Móviles (x 100 hab)")
        p2 = ax_twin.plot(l_data["Year"], l_data["Literacy_Rate"], color="#e67e22", marker="o", linewidth=3, label="Alfabetización (%)")

        ax.set_title(f"{nombres_es[i]}: Brecha Digital-Oral", fontsize=13, fontweight='bold')
        ax.set_xlabel("Año", fontsize=11)
        ax.grid(True)
        ax.set_ylabel("Móviles por cada 100 hab", color="#8e44ad", fontsize=11)
        ax_twin.set_ylabel("Alfabetización (%)", color="#e67e22", fontsize=11)
        ax_twin.set_ylim(20, 100)
        
        # Anotar el gap de oralidad
        if len(t_data) > 0 and len(l_data) > 0:
            last_t = t_data.iloc[-1]
            ax.annotate(f"Penetración Móvil: {last_t['Mobile_Subs']:.0f}%",
                        xy=(last_t["Year"], last_t["Mobile_Subs"]),
                        xytext=(last_t["Year"]-5, last_t["Mobile_Subs"]-20),
                        arrowprops=dict(facecolor='#8e44ad', shrink=0.08, width=1.5, headwidth=6),
                        fontsize=9, fontweight='bold', color="#8e44ad")

    plt.suptitle("La Paradoja de la Digitalización Oral: Saturación Móvil vs Rezago de Lectoescritura", fontsize=15, fontweight='bold')
    plt.tight_layout()
    fig.savefig(os.path.join(VIS_DIR, "05_west_africa_oral_paradox.png"), dpi=300)
    plt.close()
    print("Guardado: 05_west_africa_oral_paradox.png")

def generate_pisa_charts():
    print("\n=== [2/2] Generando Visualizaciones de los Estudios PISA (Chile y el Mundo) ===")
    
    pisa_hist_file = os.path.join(DATA_DIR, "pisa_reading_scores_2000_2022.csv")
    pisa_levels_file = os.path.join(DATA_DIR, "pisa_proficiency_levels_2022.csv")
    chile_escs_file = os.path.join(DATA_DIR, "pisa_chile_escs_breakdown.csv")

    df_hist = pd.read_csv(pisa_hist_file)
    df_levels = pd.read_csv(pisa_levels_file)
    df_chile = pd.read_csv(chile_escs_file)

    # 6. Trayectoria Histórica PISA Lectura (Chile vs OCDE vs Latinoamérica)
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Chile
    chile_hist = df_hist[df_hist["Country"] == "Chile"].sort_values("Year")
    ax.plot(chile_hist["Year"], chile_hist["ReadingScore"], color="#e74c3c", marker="o", markersize=8, linewidth=3.5, label="Chile (Líder LatAm)")
    
    # OCDE Promedio
    oecd_hist = df_hist[df_hist["Country"] == "OECD Average"].sort_values("Year")
    ax.plot(oecd_hist["Year"], oecd_hist["ReadingScore"], color="#2c3e50", marker="s", markersize=7, linewidth=3, linestyle="--", label="Promedio OCDE")
    
    # Países Comparativos
    for country, col, ls in [("Uruguay", "#3498db", "-."), ("Mexico", "#27ae60", ":"), ("Brazil", "#f39c12", ":"), ("Singapore", "#8e44ad", "-")]:
        sub = df_hist[df_hist["Country"] == country].sort_values("Year")
        if len(sub) > 0:
            ax.plot(sub["Year"], sub["ReadingScore"], color=col, marker="^", markersize=5, linewidth=1.8, linestyle=ls, alpha=0.85, label=country)

    ax.set_title("Evolución PISA en Lectura (2000 - 2022): Chile frente a OCDE y la Región", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Ciclo de Evaluación PISA", fontsize=12)
    ax.set_ylabel("Puntaje Escala PISA Lectura", fontsize=12)
    ax.set_ylim(350, 570)
    ax.axhline(407, color="#c0392b", linestyle=":", alpha=0.7, label="Umbral Nivel 2 (Mínimo Funcional: 407 pts)")
    ax.legend(loc="lower right", frameon=True, facecolor="white", fontsize=10)
    ax.grid(True)
    plt.tight_layout()
    fig.savefig(os.path.join(VIS_DIR, "06_pisa_historical_reading_chile_vs_oecd.png"), dpi=300)
    plt.close()
    print("Guardado: 06_pisa_historical_reading_chile_vs_oecd.png")

    # 7. Porcentaje de Estudiantes Bajo el Nivel 2 (Analfabetismo Funcional en PISA 2022)
    df_levels_sorted = df_levels.sort_values("Under_Level_2_Total", ascending=True)
    
    fig, ax = plt.subplots(figsize=(13, 8))
    colors = ["#2ecc71" if x < 20 else "#f39c12" if x < 30 else "#e74c3c" if x < 40 else "#c0392b" for x in df_levels_sorted["Under_Level_2_Total"]]
    # Resaltar Chile especialmente
    for idx, cname in enumerate(df_levels_sorted["Country"]):
        if cname == "Chile":
            colors[idx] = "#d35400"

    bars = ax.barh(df_levels_sorted["Country"], df_levels_sorted["Under_Level_2_Total"], color=colors, alpha=0.85, edgecolor="#7f8c8d")
    ax.set_xlim(0, 70)
    ax.set_title("Porcentaje de Estudiantes con Analfabetismo Funcional (Bajo Nivel 2 PISA 2022)", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("% de Jóvenes de 15 Años que No Alcanzan el Umbral Mínimo de Lectura", fontsize=12)
    ax.set_ylabel("País / Bloque", fontsize=12)
    ax.axvline(26.3, color="#2c3e50", linestyle="--", linewidth=1.5, label="Media OCDE (26.3%)")

    for bar in bars:
        w = bar.get_width()
        ax.text(w + 1.0, bar.get_y() + bar.get_height()/2, f"{w:.1f}%", va='center', fontsize=9.5, fontweight='bold', color="#2c3e50")

    ax.legend(loc="lower right", frameon=True)
    ax.grid(axis='x')
    plt.tight_layout()
    fig.savefig(os.path.join(VIS_DIR, "07_pisa_functional_illiteracy_levels.png"), dpi=300)
    plt.close()
    print("Guardado: 07_pisa_functional_illiteracy_levels.png")

    # 8. Gradiente Socioeconómico en Chile (ESCS y Dependencia Administrativa)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Cuartil ESCS
    escs_data = df_chile[df_chile["Segmento_Tipo"] == "Cuartil_ESCS"]
    bars1 = ax1.bar(escs_data["Grupo"].str.replace(" \\(.*\\)", "", regex=True), escs_data["ReadingScore"], color=["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71"], edgecolor="#7f8c8d")
    ax1.set_ylim(350, 520)
    ax1.set_title("Puntaje PISA Lectura según Cuartil Socioeconómico (Chile)", fontsize=12, fontweight='bold')
    ax1.set_ylabel("Puntaje PISA", fontsize=11)
    ax1.grid(axis='y')
    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, h + 3, f"{h:.0f} pts", ha='center', fontweight='bold')

    # Dependencia Administrativa
    dep_data = df_chile[df_chile["Segmento_Tipo"] == "Dependencia"]
    bars2 = ax2.bar(dep_data["Grupo"].str.replace(" \\(.*\\)", "", regex=True), dep_data["Pct_Bajo_Nivel_2"], color=["#c0392b", "#d35400", "#27ae60"], edgecolor="#7f8c8d")
    ax2.set_ylim(0, 60)
    ax2.set_title("Tasa de Rezago (< Nivel 2) según Tipo de Colegio (Chile)", fontsize=12, fontweight='bold')
    ax2.set_ylabel("% Bajo Nivel 2 (Analfabetismo Funcional)", fontsize=11)
    ax2.grid(axis='y')
    for bar in bars2:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, h + 1.2, f"{h:.1f}%", ha='center', fontweight='bold')

    plt.suptitle("Impacto de la Desigualdad Estructural en el Rendimiento Lector en Chile (PISA 2022)", fontsize=14, fontweight='bold')
    plt.tight_layout()
    fig.savefig(os.path.join(VIS_DIR, "08_chile_pisa_socioeconomic_gradient.png"), dpi=300)
    plt.close()
    print("Guardado: 08_chile_pisa_socioeconomic_gradient.png")

    # 9. Modelo Neurocognitivo: De la Conciencia Fonológica Temprana al Éxito en PISA
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis('off')
    
    # Diagrama conceptual de bloques cognitivos
    boxes = [
        {"x": 0.05, "y": 0.65, "w": 0.25, "h": 0.25, "title": "Paso 1: Fundamento Pino\n(Conciencia Fonológica)", "desc": "• Fonemas y Grafemas\n• Sílabas Directas/Trabadas\n• Trazado Motor (Refuerzo)", "color": "#d4efdf", "border": "#27ae60"},
        {"x": 0.38, "y": 0.65, "w": 0.25, "h": 0.25, "title": "Paso 2: Automatización\n(Fluidez Lectora)", "desc": "• STT / Lectura en voz alta\n• Descompresión Memoria Trabajo\n• Algoritmo Adaptativo SM-2", "color": "#d6eaf8", "border": "#2980b9"},
        {"x": 0.71, "y": 0.65, "w": 0.25, "h": 0.25, "title": "Paso 3: Comprensión PISA\n(Nivel 2 o Superior)", "desc": "• Inferencia Compleja\n• Evaluación Crítica Textos\n• Superación Analfabetismo Funcional", "color": "#fcf3cf", "border": "#f39c12"},
        {"x": 0.20, "y": 0.15, "w": 0.60, "h": 0.35, "title": "Cuello de Botella Cognitivo (Modelo de Doble Ruta & Stanovich)", "desc": "Si la decodificación NO se automatiza a temprana edad, la memoria de trabajo se satura descifrando grafemas sueltos.\nResultado empírico: 33.7% de jóvenes chilenos y 51.5% en América Latina colapsan en PISA Nivel 1 (analfabetismo funcional).\nPino resuelve la causa raíz en la fase fonológico-motora.", "color": "#fadbd8", "border": "#e74c3c"}
    ]

    from matplotlib.patches import FancyBboxPatch

    for b in boxes:
        rect = FancyBboxPatch((b["x"], b["y"]), b["w"], b["h"], boxstyle="round,pad=0.02,rounding_size=0.02",
                              facecolor=b["color"], edgecolor=b["border"], linewidth=2, transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(b["x"] + b["w"]/2, b["y"] + b["h"] - 0.06, b["title"], ha='center', va='top', fontsize=11, fontweight='bold', transform=ax.transAxes, color="#2c3e50")
        ax.text(b["x"] + 0.02, b["y"] + 0.03, b["desc"], ha='left', va='bottom', fontsize=9.5, transform=ax.transAxes, color="#34495e")

    # Flechas de conexión
    ax.annotate("", xy=(0.37, 0.77), xytext=(0.31, 0.77), arrowprops=dict(facecolor="#2c3e50", shrink=0.05, width=2, headwidth=8), transform=ax.transAxes)
    ax.annotate("", xy=(0.70, 0.77), xytext=(0.64, 0.77), arrowprops=dict(facecolor="#2c3e50", shrink=0.05, width=2, headwidth=8), transform=ax.transAxes)
    ax.annotate("", xy=(0.50, 0.52), xytext=(0.50, 0.64), arrowprops=dict(facecolor="#e74c3c", shrink=0.05, width=2, headwidth=8), transform=ax.transAxes)

    plt.title("Justificación Neurocognitiva: Cómo Pino Previene el Fracaso en Evaluaciones PISA", fontsize=14, fontweight='bold', pad=15)
    plt.tight_layout()
    fig.savefig(os.path.join(VIS_DIR, "09_phonology_to_pisa_cognitive_bottleneck.png"), dpi=300)
    plt.close()
    print("Guardado: 09_phonology_to_pisa_cognitive_bottleneck.png")

if __name__ == "__main__":
    generate_eda_colab_charts()
    generate_pisa_charts()
    print("\n¡Todas las visualizaciones analíticas generadas exitosamente en 'visualizations/'!")
