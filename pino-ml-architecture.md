# 🧠 Pino ML — Arquitectura de Machine Learning

## Arquitectura General

```mermaid
flowchart TB
    subgraph APP["📱 Flutter App"]
        A1[Ejercicios de fonemas]
        A2[Lectura en voz alta]
        A3[Trazado de letras]
        A4[Progreso del usuario]
    end

    subgraph FIREBASE["☁️ Firebase"]
        F1[Cloud Firestore]
        F2[Firebase Auth]
        F3[Cloud Storage - Audio]
    end

    subgraph ML_API["🔌 API de ML - FastAPI"]
        API1["/predict/pronunciacion"]
        API2["/predict/siguiente-leccion"]
        API3["/predict/dificultad-texto"]
        API4["/analyze/trazo"]
    end

    subgraph ML_PIPELINE["⚙️ Pipeline ML - Kedro + Airflow"]
        K1["ETL: Firestore → DataLake"]
        K2["Feature Engineering"]
        K3["Entrenamiento de Modelos"]
        K4["Evaluación y Registro"]
    end

    subgraph ML_INFRA["🏗️ Infraestructura ML"]
        DB["Databricks\nEntrenamiento distribuido"]
        MLF["MLflow\nTracking + Registry"]
        DL["Data Lake\nS3 / GCS"]
    end

    APP --> FIREBASE
    FIREBASE --> ML_PIPELINE
    APP -->|"Audio en tiempo real"| ML_API
    ML_API -->|"Modelos servidos"| MLF
    ML_PIPELINE --> DB
    ML_PIPELINE --> MLF
    ML_PIPELINE --> DL
    K3 --> MLF
```

## Los 4 Modelos ML de Pino

| # | Modelo | Input | Output | Uso en la app |
|---|--------|-------|--------|---------------|
| 1 | **STT Fonético** | Audio del usuario | Fonemas detectados + confianza | HU-06: Lectura en voz alta con feedback |
| 2 | **Algoritmo Adaptativo** | Historial de errores | Siguiente lección óptima | HU-05: Repetición espaciada inteligente |
| 3 | **Clasificador de Dificultad** | Texto en español | Nivel de dificultad (1-5) | HU-04/17: Adaptar textos al nivel |
| 4 | **Analizador de Trazos** | Puntos del trazo | Calidad + letra reconocida | HU-02/13: Feedback de grafomotricidad |

