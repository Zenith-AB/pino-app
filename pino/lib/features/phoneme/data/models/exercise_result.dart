import 'package:isar/isar.dart';
import 'package:uuid/uuid.dart';

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
  /// ID local de Isar. Se repite entre dispositivos: no usar fuera del teléfono.
  Id id = Isar.autoIncrement;

  /// ID global del resultado, usado como ID del documento en Firestore.
  String syncId = const Uuid().v4();

  /// Si ya se subió a Firestore (HU-10).
  bool sincronizado = false;

  /// ID del perfil que realizó el ejercicio.
  /// Indexado: todas las consultas del historial filtran por perfil.
  @Index()
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
  String? fonemaObjetivo;

  /// La opción que eligió el usuario.
  String? opcionElegida;

  /// Las opciones que se mostraron.
  late List<String> opcionesMostradas;

  // ── Trazado ──
  /// Desviación promedio en píxeles del trazo ideal.
  double? desviacionPixeles;

  /// Tolerancia que estaba configurada al momento del ejercicio.
  String? toleranciaUsada;

  // ── Lectura en voz alta ──
  /// Sílabas que se pronunciaron mal.
  late List<String> silabasMalPronunciadas;

  /// Puntaje de pronunciación (0.0 a 1.0).
  double? puntajePronunciacion;

  // ── Lectura guiada / Micro-historia ──
  /// Tipo de pregunta: "causa-efecto", "idea-principal", "literal".
  String? tipoPregunta;

  /// Si se necesitó pista para responder.
  bool? usoPista;

  DetalleEjercicio() {
    opcionesMostradas = [];
    silabasMalPronunciadas = [];
  }
}
