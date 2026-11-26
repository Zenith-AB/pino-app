# App Streamlit · Probador del modelo de edad de adquisición

Interfaz interactiva para probar los modelos del notebook (`models/*.joblib`): predice **a qué edad
aprende un niño una palabra** (AoA, en años) en **español o inglés**, la ubica en un **nivel de Pino**
y estima si es adecuada para la **edad del niño** elegida.

## Ejecutar

```bash
cd eft-machine-learning
pip install -r requirements.txt -r app/requirements.txt
streamlit run app/streamlit_app.py
```

En Windows también se puede hacer doble clic en `app/ejecutar_app.bat`.
La primera carga tarda ~15 s (lee las normas de `data/raw/`); después todo es instantáneo.

## Qué tiene

| Pestaña | Para qué sirve |
|---|---|
| 🔮 Predecir una palabra | Escribe una palabra → **Autocompletar** calcula sus variables con las mismas reglas del entrenamiento (`src/lexico.py`, `texto_es`). Luego se puede mover cada variable (frecuencia, concreción, letras, fonemas, sílabas, vecinos, grupo consonántico, categoría y, en español, complejidad silábica y AoA de la traducción). Muestra AoA, nivel, rango al 80 %, norma real (si existe), probabilidad de que el niño ya la conozca, familia de lección (K-Means) y un análisis **¿qué pasaría si…?** |
| 🌎 Español vs. inglés | Pares `perro = dog`: compara la edad de adquisición del mismo concepto en los dos idiomas. |
| 📋 Nivelar una lección | Pega una lista de palabras → las ordena de la más fácil a la más difícil, marca cuáles son aptas para la edad y permite descargar el CSV. |
| 📊 Sobre el modelo | KPIs, CV repetida, estrategias del español, hiperparámetros y gráficos de generalización. |

## Cómo predice

* **Inglés:** `modelo_aoa_en.joblib` (Gradient Boosting, MAE test 1,50 años).
* **Español:** `modelo_aoa_es.joblib` (modelo propio + transferencia: usa la AoA de la traducción inglesa y la
  predicción del modelo inglés como variables). La escala 1–11 de Alonso se convierte a años con el enlace equipercentil guardado (`q_es`, `q_en`).
* **Variables desconocidas** (casilla "desconocida"): quedan como `NaN` y el `Pipeline` las imputa con la mediana, igual que en el entrenamiento.
* **Probabilidad por edad:** `P(AoA ≤ edad)` suponiendo error normal con el RMSE del modelo (EN: RMSE en test; ES: RMSE fuera de muestra en la escala 1–11; ambos leídos de `models/metricas.json`). Es una guía, no una probabilidad calibrada.
