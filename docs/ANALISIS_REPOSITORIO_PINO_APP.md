# 📱 Análisis Arquitectónico y Técnico: Repositorio `pino-app`

> **Repositorio Oficial:** [Zenith-AB/pino-app](https://github.com/Zenith-AB/pino-app)  
> **Área:** Frontend Móvil, Arquitectura de Software e Integración de Machine Learning  
> **Estado:** MVP en Desarrollo Activo / Preparado para Integración de Inferencia ML  

---

## 1. Resumen Ejecutivo y Propósito de la Aplicación

**Pino** es una plataforma móvil diseñada para abordar la brecha de alfabetización inicial y el analfabetismo funcional tanto en infancias como en población adulta. La aplicación se distingue de los métodos tradicionales al combinar:
1. **Instrucción fónica explícita y sistemática** (asociación grafema-fonema y descomposición silábica).
2. **Grafomotricidad táctil con feedback visual inmediato** (trazado guiado sobre pantalla).
3. **Lectura oral interactiva** con tecnología *Tap-to-Speech* y evaluación acústica.
4. **Diseño centrado en la accesibilidad:** interfaz configurable con temas diferenciados para público infantil (lúdico, gamificado) y público adulto (sobrio, funcional, libre de condescendencia pedagógica).
5. **Arquitectura local-first (offline):** operatividad completa sin conexión a internet, respaldada por sincronización oportunista en la nube.

---

## 2. Pila Tecnológica y Estructura del Código

El repositorio está construido sobre **Flutter** con Dart, adoptando los principios de **Clean Architecture** orientada a características (*feature-first*) con una capa `core` compartida.

```
pino/
├── lib/
│   ├── app.dart                   # Configuración global de MaterialApp y temas
│   ├── main.dart                  # Punto de entrada, inicialización de Isar y Firebase
│   ├── core/                      # Servicios transversales y utilidades
│   │   ├── constants/             # Constantes de negocio y UI
│   │   ├── database/              # Servicio de base de datos NoSQL local (Isar)
│   │   ├── router/                # Enrutador declarativo (go_router)
│   │   ├── services/              # Clientes de API, Audio, TTS y Sync
│   │   │   ├── audio_service.dart # Reproducción de bancos de sonidos
│   │   │   ├── ml_api_client.dart # Cliente HTTP para inferencia ML (FastAPI)
│   │   │   ├── sync_service.dart  # Sincronización con Firestore
│   │   │   └── tts_service.dart   # Síntesis local de voz (flutter_tts)
│   │   ├── theme/                 # Paletas cromáticas y tipografías (Nunito / Atkinson)
│   │   └── utils/                 # Monitoreo de conectividad (connectivity_plus)
│   └── features/                  # Módulos de negocio independientes
│       ├── diagnostic/            # Evaluación inicial de nivel lector
│       ├── home/                  # Menú principal, rutas de aprendizaje y racha
│       ├── phoneme/               # Exploración y discriminación de fonemas
│       ├── profile/               # Multiperfil local y selector de avatares
│       ├── tap_to_speech/         # Texto desglosado en sílabas audibles
│       └── tracing/               # Canvas de grafomotricidad y guía caligráfica
```

### Dependencias Críticas (`pubspec.yaml`)
- **Gestión de Estado:** `flutter_riverpod` (^2.4.9) proporciona inyección de dependencias modular, desacoplando la lógica de negocio (`Notifier` / `AsyncNotifier`) de la interfaz de usuario.
- **Base de Datos NoSQL Local:** `isar` (^3.1.0+1) e `isar_flutter_libs` permiten consultas ACID de altísima velocidad directamente en SQLite/C++ embebido, eliminando bloqueos en el hilo principal de Flutter.
- **Sincronización Cloud:** `cloud_firestore` (^4.13.6) y `firebase_auth` para autenticación y respaldo remoto.
- **Enrutamiento:** `go_router` (^12.1.1) con navegación declarativa y protección de rutas.
- **Audio & Multimedia:** `audioplayers` (^5.2.1) para efectos y muestras fonéticas de baja latencia; `flutter_tts` (^3.8.3) para asistencia oral en el dispositivo.

---

## 3. Modelo de Persistencia Local y Estrategia Offline-First

Uno de los mayores aciertos de diseño en `pino-app` es su **independencia de la conectividad continua**. Dado que el público objetivo suele residir en zonas rurales, periurbanas o de bajos recursos (donde los datos móviles son intermitentes), la app almacena todo el progreso de forma local.

### Esquema de Entidades Isar
1. **`UserProfile` (`user_profile.dart`)**:
   Documento agregado que contiene el estado íntegro del aprendiz:
   - Identificadores: `id` (entero Isar), `syncId` (UUID v4 para correlación en la nube), `firebaseUid`.
   - Perfil pedagógico: `nombre`, `avatarIndex`, `modo` (`infantil` vs `adulto`), `nivelActual` (1 a 5).
   - Objetos embebidos (sin joins costosos):
     * `ProgresoUsuario`: métricas de fonemas dominados, palabras aprendidas y trazos completados.
     * `ConfiguracionPerfil`: sensibilidad de trazo (`baja`, `media`, `alta`), temporizadores de ejercicio y variantes dialectales.
     * `RachaUsuario`: conteo de días consecutivos, hitos desbloqueados y fecha de última sesión.
     * `List<ErrorFrecuente>`: catálogo de confusiones grafema-fonema para adaptación.
2. **`ExerciseResult`**: Registro pormenorizado de cada intento (tiempo de respuesta, acierto/fallo, desviación de trazo, audio analizado).
3. **`DiagnosticResult`**: Historial de la prueba inicial de clasificación.

---

## 4. Análisis de Módulos Pedagógicos de la App

### 4.1 Fonemas y Discriminación Auditiva (`features/phoneme/`)
Permite asociar el sonido puro de las letras con su representación ortográfica. Implementa ejercicios de emparejamiento fonético (*matching*) donde el usuario escucha un sonido y selecciona la opción correcta entre distractores cuidadosamente elegidos (ej. pares mínimos /p/ y /b/).

### 4.2 Trazado Grafomotor y Canvas Táctil (`features/tracing/`)
Captura la interacción táctil continua del usuario:
- `tracing_canvas.dart`: implementa un `CustomPainter` que almacena puntos coordenados `(x, y)` conforme el usuario dibuja.
- `tracing_guide.dart`: proyecta la ruta ideal y guías visuales con flechas de dirección.
- El canvas calcula en tiempo real la colisión y genera una serie de coordenadas que son enviadas al backend o evaluadas localmente.

### 4.3 Tap-to-Speech Interactivo (`features/tap_to_speech/`)
Transforma cualquier texto en un recurso de aprendizaje multimodal:
- Separa dinámicamente las palabras en bloques silábicos legibles.
- Al tocar cualquier palabra o sílaba, activa un feedback háptico, anima la separación silábica y reproduce el audio correspondiente mediante TTS nativo o grabaciones precargadas.
- Reduce drásticamente la frustración y la ansiedad lectora en aprendices iniciales.

### 4.4 Diagnóstico y Multiperfil (`features/diagnostic/`, `features/profile/`)
- Permite que múltiples miembros de una misma familia o aula compartan un solo dispositivo (común en sectores vulnerables) mediante perfiles aislados.
- El flujo de diagnóstico clasifica al aprendiz en pre-lector, lector silábico, lector de palabras o lector de oraciones en menos de 3 minutos.

---

## 5. El Contrato de Integración con Machine Learning (`MLApiClient`)

En `lib/core/services/ml_api_client.dart`, la aplicación ya tiene implementada la capa de consumo HTTP con el backend FastAPI:

| Endpoint | Método | Input desde Flutter | Output esperado por Flutter |
| :--- | :--- | :--- | :--- |
| `/predict/pronunciacion` | `POST` (Multipart) | Archivo de audio (WAV/M4A) + `texto_esperado` | `ResultadoPronunciacionML`: puntaje global (0-1), WER, CER, sílabas correctas/incorrectas |
| `/predict/fonema` | `POST` (Multipart) | Archivo de audio + `fonema_esperado` | `ResultadoFonemaML`: `correcto` (bool), `confianza` (double) |
| `/predict/siguiente-leccion` | `POST` (JSON) | Array de `historial` de ítems, `modo`, `nivel_actual` | `RecomendacionLeccion`: `siguienteItemId`, probabilidad de error, flag de desbloqueo de nivel |
| `/predict/dificultad-texto` | `POST` (JSON) | `texto` (String), `nivel_objetivo` | `AnalisisTextoML`: nivel (1-5), legibilidad Fernández-Huerta, palabras complejas |
| `/analyze/trazo` | `POST` (JSON) | Array de puntos `[x, y]`, `letra_esperada`, dimensiones canvas | `ResultadoTrazoML`: desviación promedio, cobertura %, tolerancia sugerida |
| `/health` | `GET` | Ninguno | Estado del servicio y disponibilidad de modelos |

### Requerimientos Críticos de la App hacia la Infraestructura ML:
1. **Latencia Interactiva:**
   - La evaluación de trazos y la selección de la siguiente lección deben responder en **menos de 300 ms** para mantener la fluidez de la interfaz.
   - El análisis fonético de audio admite hasta 2 a 3 segundos (mostrando un indicador visual lúdico mientras procesa).
2. **Resiliencia ante Fallos de Conexión:**
   - `MLApiClient` incluye manejo de timeouts y decodificación explícita en UTF-8 para evitar corrupción de caracteres con tildes y diéresis (`á`, `é`, `í`, `ó`, `ú`, `ñ`, `ü`).
   - La infraestructura de ML debe proveer modelos livianos o cuantizados que puedan ser empaquetados en un futuro directamente en el teléfono (ONNX Runtime / TFLite) para asegurar funcionamiento offline al 100%.
