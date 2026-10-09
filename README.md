# Pino

Aplicación móvil de alfabetización en español para **niños y adultos**. Enseña a
asociar sonidos con letras, trazar letras, leer textos graduados y entender
documentos de la vida diaria, con audio en cada paso y funcionamiento **offline**.

Proyecto de un equipo de 4 integrantes organizado en sprints de 2 semanas
(ver [`plan-sprints-pino.md`](plan-sprints-pino.md)).

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

Requisitos: Flutter 3.x estable, Android Studio o Xcode.

```bash
cd pino

# Solo la primera vez: genera las carpetas android/ e ios/ sin tocar lib/.
# --org define el applicationId (p. ej. cl.miuniversidad → cl.miuniversidad.pino):
# elíjanlo antes de conectar Firebase, después cuesta cambiarlo.
flutter create --platforms=android,ios --org <dominio-invertido> .

flutter pub get

# Genera el código de Isar (*.g.dart). Repetir cada vez que cambie un modelo.
dart run build_runner build --delete-conflicting-outputs

flutter analyze
flutter test
flutter run
```

Notas:

- Los archivos `*.g.dart` no se versionan: cada integrante los genera con `build_runner`.
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
source .venv/bin/activate

# API + herramientas de desarrollo
pip install -e ".[api,dev]"
python -m spacy download es_core_news_md

cp .env.example .env
uvicorn pino_ml.api.main:app --env-file .env --reload   # http://localhost:8000/docs

pytest
```

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
