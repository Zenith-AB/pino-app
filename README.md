# Pino

Aplicación móvil de alfabetización en español (y próximamente inglés) para **niños y adultos**. Enseña a
asociar sonidos con letras, trazar letras, leer textos graduados y entender
documentos de la vida diaria, con audio en cada paso y funcionamiento **offline**.

Proyecto de un equipo de 4 integrantes organizado en sprints de 2 semanas
(ver [`plan-sprints-pino.md`](plan-sprints-pino.md)).

## 🧠 Novedad (noviembre 2026): nivelación de vocabulario infantil en español e inglés

Pino se amplía para enseñar **español e inglés a niños pequeños**. La carpeta
[`ep3-machine-learning/`](ep3-machine-learning/) contiene un modelo que estima **a qué
edad aprende un niño cada palabra** (edad de adquisición, AoA). Con esa estimación el
vocabulario se ordena en los niveles de la app de forma automática y no palabra por
palabra a mano.

| Nivel | Edad | Uso en la app |
|-------|------|---------------|
| 1 · Primeras palabras | < 4 años | Vocabulario oral con imagen y audio |
| 2 · Preescolar | 4–5 años | Sílabas directas (CV) y conciencia fonológica |
| 3 · Lectura inicial | 6–7 años | Decodificación de palabras completas |
| 4 · Lector en desarrollo | 8–9 años | Palabras largas y menos frecuentes |

**Resultados**
- **Datos reales y públicos:** normas de AoA de Kuperman (≈ 30.000 palabras en inglés) y de Alonso (1.239 en español), frecuencias SUBTLEX, concreción de Brysbaert, diccionario de pronunciación CMU e imágenes MultiPic.
- **Modelo elegido: Gradient Boosting.** Error medio de **1,50 años** en palabras nunca vistas (R² = 0,58). Ubica la palabra en el nivel correcto ±1 en el **94 %** de los casos, y una palabra adulta cae en un nivel infantil solo en el **0,05 %**.
- **Español:** combinado con lo aprendido del inglés, la correlación con las normas reales llega a **ρ = 0,71**.
- **Producto para la app**, en [`ep3-machine-learning/data/processed/`](ep3-machine-learning/data/processed/):
  - `vocabulario_infantil_es.csv`: **1.312** palabras con nivel, sílabas (*ca-sa*), fonemas y traducción.
  - `vocabulario_infantil_en.csv`: **10.333** palabras con nivel y fonemas.
  - `pares_imagen_es_en.csv`: **473** pares imagen–palabra en ambos idiomas.
  - Un filtro editorial excluye groserías, violencia, alcohol y sexualidad, pero la validación de una educadora sigue siendo necesaria.

**Documentos**
- 📘 [Informe técnico](ep3-machine-learning/README.md): problema, KPIs, CRISP-DM, EDA, modelos, optimización, ensambles, evaluación, sesgos y recomendaciones.
- 📓 [Notebook ejecutado](ep3-machine-learning/notebooks/pino_edad_adquisicion_palabras.ipynb), reproducible con semilla fija.
- 📚 [Datasets y métodos de enseñanza](ep3-machine-learning/docs/DATASETS_Y_METODOS_ENSENANZA.md): Wordbank, CHILDES, EsPal, Dolch/Fry; método silábico, fonético, *synthetic phonics*, *word families*.
- 🎞️ [Presentación del cambio de enfoque](ep3-machine-learning/presentacion/Pino_cambio_de_enfoque.pptx).

**Próximos pasos:** exponer el modelo en `pino-ml` (`/predict/aoa-palabra`), usar la AoA como
dificultad inicial del repaso espaciado SM-2, completar el nivel 1 con Wordbank (datos de
niños reales) y sumar vocabulario chileno validado por educadoras.

---

## 🚀 Evolución y Nuevo Sprint: PISA, Macroeconomía y Motores ML Avanzados (Octubre 2026)

Este nuevo sprint incorpora la investigación psicométrica internacional de las pruebas **PISA (OCDE)**, formaliza los estudios del Colab sobre la **Paradoja de la Digitalización Oral**, expande los motores de inferencia de `pino-ml` a 6 modelos y agrega una **presentación ejecutiva interactiva en HTML**.

### 1. Documentación y Estudios Técnicos
- 📊 **[docs/ESTUDIO_PISA_CHILE_Y_MUNDO.md](docs/ESTUDIO_PISA_CHILE_Y_MUNDO.md):** Estudio empírico sobre los resultados de lectura en PISA 2022 (Chile 448 pts vs OCDE 476 pts), la crisis estructural del 33.7% bajo Nivel 2 (analfabetismo funcional), el gradiente socioeconómico del índice ESCS (brecha de 83 pts entre cuartil 1 y cuartil 4) y la justificación neurocognitiva del cuello de botella en la memoria de trabajo.
- 🌍 **[docs/ANALISIS_EDA_COLAB_Y_PARADOJA_ORAL.md](docs/ANALISIS_EDA_COLAB_Y_PARADOJA_ORAL.md):** Análisis exhaustivo de `exploracionedapino.py`. Explica por qué en Senegal, Costa de Marfil e India la penetración móvil supera el 120-140% mientras la alfabetización ronda el 48-77%, y cómo Pino utiliza la cultura oral digital como puente pedagógico.
- 📱 **[docs/ANALISIS_REPOSITORIO_PINO_APP.md](docs/ANALISIS_REPOSITORIO_PINO_APP.md):** Auditoría técnica del frontend Flutter (Riverpod, Isar NoSQL offline-first, módulos pedagógicos y contratos de `MLApiClient`).
- 🏗️ **[docs/ARQUITECTURA_ML_INFRAESTRUCTURA.md](docs/ARQUITECTURA_ML_INFRAESTRUCTURA.md):** Manual técnico de la infraestructura con formulaciones matemáticas (SM-2 adaptado, distancia Hausdorff/DTW, Fernández-Huerta, Gutiérrez de Polini y modelo sigmoide de riesgo PISA).
- 🎨 **[presentacion.html](presentacion.html) / [index.html](index.html):** Presentación ejecutiva interactiva de 9 diapositivas con diseño minimalista, paleta cálida sobria, animaciones fluidas, navegación por teclado y vista general (`O`).

### 2. Nuevos Motores de Inferencia (`pino-ml/src/pino_ml/models/`)
1. **`PisaRiskEngine` (`pisa_risk_engine.py`):** Transforma la microtelemetría de Pino (acierto fonémico, latencia, fluidez WPM y grafomotricidad) en una proyección continua en la escala PISA (200-600) y calcula la probabilidad de caer bajo el umbral de alfabetización funcional Nivel 2.
2. **`MacroAnalyticsEngine` (`macro_analytics.py`):** Modela el *Índice de Brecha de Oralidad Digital* ($DOPI$) cruzando datos de Our World in Data y Banco Mundial.
3. **`AnalizadorTrazos` (mejorado):** Incorpora velocidad cinemática, cobertura de polilíneas y sugerencia de tolerancia dinámica (baja, media, alta).
4. **`ClasificadorDificultad` (mejorado):** Combina el índice de Fernández-Huerta con el índice de Gutiérrez de Polini y spaCy, mapeando la complejidad a los niveles PISA 1c a 5.

### 3. Suite de Pruebas Automatizadas
- **Backend ML:** 80 tests aprobados al 100% (`pytest pino-ml/tests`).
- **Frontend Flutter:** 21 tests aprobados al 100% (`cd pino && flutter test`).

---

## Qué hace (y qué hará)

| Área | Historias de usuario | Estado |
|------|---------------------|--------|
| Perfiles locales (infantil/adulto) y diagnóstico inicial | HU-01, HU-15 | Lógica y datos listos; pantallas por hacer |
| Fonemas con audio y ejercicio de emparejamiento | HU-03, HU-14 | Lógica y datos listos; pantallas y audios por hacer |
| Trazado de letras con tolerancia ajustable | HU-02, HU-13 | Análisis de trazo en la API (vocales); canvas por hacer |
| Racha diaria y repaso espaciado | HU-05, HU-08 | Lógica lista |
| Sincronización con la nube cuando hay conexión | HU-10 | `SyncService` listo; falta inicializar Firebase |
| Lectura guiada, bloques fonéticos, modo adulto, voz, accesibilidad | HU-04, 06, 07, 09, 11, 12, 16–22 | Sprints 4 a 7 |

## Arquitectura

| Carpeta | Qué es |
|---------|--------|
| `pino/` | App móvil: Flutter + Riverpod (estado) + Isar (base de datos local) + Firebase (Auth y Firestore) |
| `pino-ml/` | Backend de ML en Python: API FastAPI con 4 modelos y pipeline de entrenamiento Kedro + MLflow, orquestado con Airflow |
| `ep3-machine-learning/` | Modelo de edad de adquisición de palabras (ES/EN) y vocabulario infantil nivelado para la app |
| `plan-sprints-pino.md` | **Plan vigente** de sprints y tareas por integrante |
| `backlog-pino.md` | Detalle de las historias de usuario (tareas, puntos, dependencias) |
| `pino-ml-architecture.md` | Arquitectura de ML y estado de cada modelo |

La app guarda todo primero en el teléfono (Isar) y sincroniza con Firestore cuando
hay red, en `usuarios/{uid}/perfiles/{syncId}/resultados/{syncId}`. La API de ML
ofrece:

| Endpoint | Modelo | Uso |
|----------|--------|-----|
| `POST /predict/pronunciacion` | Whisper + comparación de sílabas | Lectura en voz alta (HU-06) |
| `POST /predict/fonema` | Whisper (experimental) | Pronunciar un fonema (HU-03) |
| `POST /predict/siguiente-leccion` | SM-2 + modelo de probabilidad de error | Repaso espaciado (HU-05) |
| `POST /predict/dificultad-texto` | Índice Fernández-Huerta + spaCy | Adaptar textos al nivel (HU-04, HU-17) |
| `POST /analyze/trazo` | Distancia a la ruta ideal | Trazado de letras (HU-02, HU-13) |

---

## Cómo levantar el proyecto

### App Flutter (`pino/`)

Requisitos: Flutter 3.x estable. Para Android, Android Studio con el SDK; sin
él se puede probar en el PC como app de escritorio Linux.

```bash
cd pino

# Solo la primera vez: genera las carpetas de cada plataforma sin tocar lib/.
# --org define el applicationId (p. ej. cl.miuniversidad → cl.miuniversidad.pino):
# elíjanlo antes de conectar Firebase, después cuesta cambiarlo.
flutter create --platforms=android,ios,linux --org <dominio-invertido> .
# flutter create agrega un test de plantilla que no aplica a Pino (usa MyApp):
rm test/widget_test.dart

flutter pub get

# Genera el código de Isar (*.g.dart). Repetir cada vez que cambie un modelo.
dart run build_runner build --delete-conflicting-outputs

flutter analyze
flutter test
flutter run -d linux     # o un emulador/teléfono Android: flutter run
```

Notas:

- Las pantallas todavía son esqueletos: al abrir la app se ve la selección de
  perfil con texto de relleno. La lógica se prueba con `flutter test`.
- Los archivos `*.g.dart` no se versionan: cada integrante los genera con `build_runner`.
- `flutter create` genera `.metadata` y `flutter pub get` genera `pubspec.lock`:
  conviene versionar ambos. El `pino/README.md` que crea `flutter create` se puede borrar.
- Los tests descargan una vez la librería nativa de Isar a `.dart_tool/isar_test/`
  (necesitan internet la primera vez).
- Firebase todavía no está inicializado (`main.dart`). Al conectarlo, `SyncService`
  necesita el `uid` del usuario de Firebase Auth. Las reglas de seguridad están
  en `pino/firestore.rules` (`firebase deploy --only firestore:rules`).
- La API de ML se configura con `--dart-define=ML_API_URL=https://...`.
  Por defecto apunta a `http://10.0.2.2:8000` (el `localhost` del PC visto desde el
  emulador de Android). Android bloquea `http://` sin cifrar en las versiones
  release; en producción hay que usar HTTPS.

### Backend de ML (`pino-ml/`)

Requisitos: Python 3.10+ y `ffmpeg` (lo usa Whisper para leer audio).

```bash
cd pino-ml
python -m venv .venv
source .venv/bin/activate        # en fish: source .venv/bin/activate.fish

# torch solo para CPU (~200 MB). Sin esto, pip baja la versión con CUDA (~3 GB).
pip install torch --index-url https://download.pytorch.org/whl/cpu

# API + herramientas de desarrollo
pip install -e ".[api,dev]"
python -m spacy download es_core_news_md

cp .env.example .env
# Para probar en el PC, un modelo de Whisper más chico y rápido (descarga ~140 MB):
sed -i 's/^WHISPER_MODEL_SIZE=.*/WHISPER_MODEL_SIZE=base/' .env

pytest
uvicorn pino_ml.api.main:app --env-file .env --reload   # http://localhost:8000/docs
```

La primera vez que arranca, la API descarga el modelo de Whisper elegido.

Si un modelo no se puede cargar (por ejemplo, falta el de spaCy), la API arranca
igual y ese endpoint responde 503. `GET /health` muestra qué modelos están cargados.

#### Pipeline de entrenamiento

```bash
pip install -e ".[training]"
export GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/credenciales-firebase.json
export MLFLOW_TRACKING_URI=http://localhost:5000
kedro run --pipeline training
```

Los parámetros están en `pino-ml/conf/base/parameters.yml`. Con menos datos que
los mínimos configurados (`min_filas`, `min_perfiles`) el pipeline no registra
ningún modelo. El DAG de Airflow (`src/pino_ml/orchestration/dags/`) solo
pasa un modelo a producción si mejora al actual.

---

## Correcciones estructurales (octubre 2026)

Revisión completa del código inicial y corrección de los problemas encontrados.
Antes la app no compilaba y no había tests; ahora hay **21 tests en Flutter y
72 en Python**, todos pasando, y `flutter analyze` no reporta errores.

### App Flutter

- **Compilación:** se corrigieron 7 errores (provider y campo inexistentes en
  `app.dart`, import roto en `sync_service.dart`, tipos de listas en el catálogo
  de fonemas). Se declaró `http` en `pubspec.yaml` y se activó el linter
  (`analysis_options.yaml`).
- **Crashes al guardar en Isar:** los campos `late` que aceptan null lanzaban
  `LateInitializationError` al crear perfiles, cargar fonemas o guardar
  resultados. Además, Isar devuelve listas de tamaño fijo y `.add()` fallaba al
  registrar la racha, el progreso de fonemas y los errores frecuentes.
- **Estado:** `copyWith` ahora puede borrar el perfil activo y el mensaje de
  feedback. Responder un ejercicio actualiza el progreso del perfil.
- **Diagnóstico:** un solo enum de nivel (`UserLevel`), tiempo medido por
  pregunta y el nivel se guarda en el perfil. El nivel cuenta los aciertos en
  orden hasta el primer error, para que un acierto al azar no lo suba.
- **Datos:** eliminar un perfil borra sus resultados y diagnósticos; las
  consultas por perfil usan un índice.
- **Sincronización con Firestore:** los IDs locales de Isar se repetían entre
  teléfonos y los datos de distintas familias se pisaban. Ahora cada perfil y
  resultado tiene un UUID (`syncId`), la ruta incluye el `uid` del usuario, solo
  se suben los resultados pendientes (en lotes) y los errores quedan en el log.
  Se agregaron reglas de seguridad (`firestore.rules`).
- **Cliente de la API:** parámetros codificados en la URL, respuestas
  decodificadas como UTF-8 (antes se rompían las tildes) y tiempos límite.
- **Contenido:** el catálogo de fonemas describe correctamente la h muda, c/g con
  dos sonidos, qu/gu, etc. La "r" usa "pera" (en "rana" suena fuerte, como rr) y
  "gu" usa "guitarra" (en "guante" la u sí suena).

### Backend de ML

- **Analizador de trazos:** medía la distancia a las esquinas de la ruta y no a
  sus líneas; una letra perfecta daba 50 %. Ahora mide en píxeles contra cada
  trazo por separado, y la "A" ya no está invertida.
- **Repetición espaciada (SM-2):** la fórmula del factor de facilidad sumaba 0;
  ahora sube con aciertos y baja con fallos. La API además descartaba las fechas
  de práctica que envía la app.
- **Voz:** "Mamá." ya no se evalúa como error por la puntuación; separación
  silábica con reglas del español (perro, árbol, día…); comparación de sílabas
  alineada (una sílaba repetida no desplaza al resto); fonemas según contexto
  (casa/cine, rana/pera); se descarta el texto que Whisper inventa sobre silencio.
- **API:** los endpoints pesados ya no bloquean el servidor, hay límite de tamaño
  para el audio, validación de entradas y, si un modelo no carga, la API arranca
  igual.
- **Pipeline de entrenamiento:** el modelo "veía" la respuesta que debía predecir
  (fuga del target); ahora cada intento se predice solo con los anteriores y la
  evaluación separa perfiles. Se quitó el "clasificador de dificultad" que se
  entrenaba sin textos. Con pocos datos no se registra ningún modelo.
- **Airflow:** la tarea de Databricks corría en paralelo a Kedro (doble
  entrenamiento); ahora se usa una u otra. Un modelo solo pasa a producción si
  mejora al actual.
- **Empaquetado:** el paquete pasó de `src` a `pino_ml` (instalable con
  `pip install -e`), se agregó la configuración de Kedro (`conf/`) y las
  dependencias se separaron en `api`, `training`, `airflow` y `dev`, quitando las
  que no se usaban.

### Documentación

- `plan-sprints-pino.md` es el plan vigente; `backlog-pino.md` lo indica y su
  tabla de stack refleja las decisiones tomadas.
- `pino-ml-architecture.md` describe el estado real de cada modelo.

### Decisiones pendientes del equipo

- **Voz (Sprint 5):** Whisper "corrige" lo que oye y no detecta bien errores de
  pronunciación. Evaluar un reconocedor fonético, alineamiento forzado o Vosk.
- **Trazado y repaso espaciado en el teléfono (Dart):** funcionarían 100 %
  offline, como pide HU-10.
- **Base de datos local:** Isar 3 ya no se mantiene; evaluar `isar_community` o Drift.
- **API:** autenticación (token de Firebase) y HTTPS.
- **Privacidad:** son datos de menores; definir si hace falta subir el nombre del
  niño a Firestore, el consentimiento del tutor y el borrado de datos.
- **Pendientes de implementación:** inicializar Firebase, incluir las fuentes
  como assets (hoy se descargan al abrir la app), audio en las preguntas del
  diagnóstico y desbloqueo real de fonemas (HU-05c).

---

## Flujo de Git

- `main`: versión estable (demos de fin de sprint).
- `develop`: integración; los PR van aquí.
- `feature/<hu>-<descripcion>`: una rama por tarea, con al menos una revisión antes del merge.
