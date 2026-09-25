import 'package:isar/isar.dart';

part 'diagnostic_result.g.dart';

/// Nivel detectado por el diagnóstico inicial.
enum NivelDiagnostico { preLector, silabico, palabras, textos }

/// Resultado del test diagnóstico inicial de 3 preguntas (HU-01).
/// Se almacena por perfil para poder re-evaluar en el futuro.
@collection
class DiagnosticResult {
  Id id = Isar.autoIncrement;

  /// ID del perfil evaluado.
  @Index()
  late int perfilId;

  /// Fecha en que se realizó el diagnóstico.
  late DateTime fecha;

  /// Nivel detectado automáticamente.
  @enumerated
  late NivelDiagnostico nivelDetectado;

  /// Respuestas individuales de las 3 preguntas.
  late List<RespuestaDiagnostico> respuestas;

  /// Tiempo total del diagnóstico en segundos.
  late int tiempoTotalSegundos;
}

/// Respuesta individual a una pregunta del diagnóstico.
@embedded
class RespuestaDiagnostico {
  /// Número de pregunta (1, 2 o 3).
  late int numeroPregunta;

  /// Texto de la pregunta mostrada.
  late String pregunta;

  /// Opción que eligió el usuario.
  late String respuestaElegida;

  /// Opción correcta.
  late String respuestaCorrecta;

  /// Si la respuesta fue correcta.
  late bool correcta;

  /// Tiempo en segundos que tardó en responder esta pregunta.
  late int tiempoSegundos;

  RespuestaDiagnostico() {
    numeroPregunta = 0;
    pregunta = '';
    respuestaElegida = '';
    respuestaCorrecta = '';
    correcta = false;
    tiempoSegundos = 0;
  }
}
