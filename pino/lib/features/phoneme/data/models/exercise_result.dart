import 'package:isar/isar.dart';

part 'exercise_result.g.dart';

/// Tipos de ejercicio disponibles en la app.
enum TipoEjercicio {
  fonemaExploracion,   // Explorar grilla de fonemas
  fonemaEmparejamiento, // Escuchar y elegir letra correcta
  trazadoLetra,        // Dibujar letra en canvas
  lecturaGuiada,       // Leer texto con preguntas
  bloqueFonetico,      // Armar oraciones con sílabas
  lecturaVozAlta,      // Leer frente al micrófono
  documentoInteractivo, // Boletas y documentos (modo adulto)
  letrerosTransporte,  // Letreros y señalética (modo adulto)
  microHistoria,       // Comprensión inferencial
}

/// Resultado individual de un ejercicio.
/// Se almacena como documento independiente para consultas rápidas
/// y para sincronizar con Firestore cuando haya conexión.
@collection
class ExerciseResult {
  Id id = Isar.autoIncrement;

  /// ID del perfil que realizó el ejercicio.
  late int perfilId;

  /// Tipo de ejercicio realizado.
  @enumerated
  late TipoEjercicio tipo;

  /// Identificador del contenido (ej. "fonema_m", "leccion_3", "trazo_A").
  late String contenidoId;

  /// Si la respuesta fue correcta.
  late bool correcto;

  /// Tiempo que tardó en completar el ejercicio (en segundos).
  late int tiempoSegundos;

  /// Cuándo se realizó el ejercicio.
  @Index()
  late DateTime fecha;

  /// Datos adicionales específicos del tipo de ejercicio.
  /// NoSQL permite estructura flexible — cada tipo guarda lo que necesita.
  late DetalleEjercicio detalle;
}

/// Detalle flexible del ejercicio.
/// Cada tipo de ejercicio puede tener datos diferentes
/// sin necesidad de crear tablas separadas.
@embedded
class DetalleEjercicio {
  // ── Fonema / Emparejamiento ──
  /// El fonema que se estaba practicando.
  late String? fonemaObjetivo;

  /// La opción que eligió el usuario.
  late String? opcionElegida;

  /// Las opciones que se mostraron.
  late List<String> opcionesMostradas;

  // ── Trazado ──
  /// Desviación promedio en píxeles del trazo ideal.
  late double? desviacionPixeles;

  /// Tolerancia que estaba configurada al momento del ejercicio.
  late String? toleranciaUsada;

  // ── Lectura en voz alta ──
  /// Sílabas que se pronunciaron mal.
  late List<String> silabasMalPronunciadas;

  /// Puntaje de pronunciación (0.0 a 1.0).
  late double? puntajePronunciacion;

  // ── Lectura guiada / Micro-historia ──
  /// Tipo de pregunta: "causa-efecto", "idea-principal", "literal".
  late String? tipoPregunta;

  /// Si se necesitó pista para responder.
  late bool? usoPista;

  DetalleEjercicio() {
    opcionesMostradas = [];
    silabasMalPronunciadas = [];
  }
}
