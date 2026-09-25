import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/diagnostic_result.dart';
import '../../../../core/database/database_service.dart';
import '../../../profile/data/models/user_profile.dart';
import '../../../profile/presentation/providers/profile_provider.dart';

/// Estado del flujo de diagnóstico.
class DiagnosticState {
  final int preguntaActual;
  final List<RespuestaDiagnostico> respuestas;
  final bool completado;
  final NivelDiagnostico? nivelDetectado;
  final DateTime? horaInicio;

  const DiagnosticState({
    this.preguntaActual = 0,
    this.respuestas = const [],
    this.completado = false,
    this.nivelDetectado,
    this.horaInicio,
  });

  DiagnosticState copyWith({
    int? preguntaActual,
    List<RespuestaDiagnostico>? respuestas,
    bool? completado,
    NivelDiagnostico? nivelDetectado,
    DateTime? horaInicio,
  }) {
    return DiagnosticState(
      preguntaActual: preguntaActual ?? this.preguntaActual,
      respuestas: respuestas ?? this.respuestas,
      completado: completado ?? this.completado,
      nivelDetectado: nivelDetectado ?? this.nivelDetectado,
      horaInicio: horaInicio ?? this.horaInicio,
    );
  }
}

/// Definición de las 3 preguntas del diagnóstico.
class PreguntaDiagnostico {
  final String pregunta;
  final List<String> opciones;
  final String respuestaCorrecta;

  const PreguntaDiagnostico({
    required this.pregunta,
    required this.opciones,
    required this.respuestaCorrecta,
  });
}

/// Las 3 preguntas del test diagnóstico (HU-01).
const preguntasDiagnostico = [
  // Nivel 1: Reconocer letras
  PreguntaDiagnostico(
    pregunta: '¿Puedes encontrar la letra A?',
    opciones: ['A', 'M', 'S'],
    respuestaCorrecta: 'A',
  ),
  // Nivel 2: Reconocer palabras
  PreguntaDiagnostico(
    pregunta: '¿Cuál de estas dice "mamá"?',
    opciones: ['mesa', 'mamá', 'mapa'],
    respuestaCorrecta: 'mamá',
  ),
  // Nivel 3: Comprensión de texto corto
  PreguntaDiagnostico(
    pregunta: 'Lee: "El gato duerme en la silla." ¿Dónde está el gato?',
    opciones: ['En la mesa', 'En la silla'],
    respuestaCorrecta: 'En la silla',
  ),
];

/// Notifier del flujo diagnóstico.
class DiagnosticNotifier extends StateNotifier<DiagnosticState> {
  final DatabaseService _db;

  DiagnosticNotifier(this._db) : super(const DiagnosticState());

  /// Iniciar el diagnóstico.
  void iniciar() {
    state = DiagnosticState(horaInicio: DateTime.now());
  }

  /// Responder la pregunta actual.
  void responder(String respuestaElegida) {
    final pregunta = preguntasDiagnostico[state.preguntaActual];
    final correcta = respuestaElegida == pregunta.respuestaCorrecta;

    final respuesta = RespuestaDiagnostico()
      ..numeroPregunta = state.preguntaActual + 1
      ..pregunta = pregunta.pregunta
      ..respuestaElegida = respuestaElegida
      ..respuestaCorrecta = pregunta.respuestaCorrecta
      ..correcta = correcta
      ..tiempoSegundos = state.horaInicio != null
          ? DateTime.now().difference(state.horaInicio!).inSeconds
          : 0;

    final nuevasRespuestas = [...state.respuestas, respuesta];

    if (state.preguntaActual >= 2) {
      // Última pregunta — calcular nivel
      final nivel = _calcularNivel(nuevasRespuestas);
      state = state.copyWith(
        respuestas: nuevasRespuestas,
        completado: true,
        nivelDetectado: nivel,
      );
    } else {
      state = state.copyWith(
        respuestas: nuevasRespuestas,
        preguntaActual: state.preguntaActual + 1,
      );
    }
  }

  /// Clasificar el nivel según las respuestas.
  NivelDiagnostico _calcularNivel(List<RespuestaDiagnostico> respuestas) {
    final correctas = respuestas.where((r) => r.correcta).length;

    if (correctas == 0) return NivelDiagnostico.preLector;
    if (correctas == 1) return NivelDiagnostico.silabico;
    if (correctas == 2) return NivelDiagnostico.palabras;
    return NivelDiagnostico.textos;
  }

  /// Guardar el resultado del diagnóstico en Isar.
  Future<void> guardarResultado(int perfilId) async {
    if (!state.completado || state.nivelDetectado == null) return;

    final resultado = DiagnosticResult()
      ..perfilId = perfilId
      ..fecha = DateTime.now()
      ..nivelDetectado = state.nivelDetectado!
      ..respuestas = state.respuestas
      ..tiempoTotalSegundos = state.horaInicio != null
          ? DateTime.now().difference(state.horaInicio!).inSeconds
          : 0;

    await _db.instance.writeTxn(() async {
      await _db.diagnosticos.put(resultado);
    });
  }

  /// Reiniciar el diagnóstico.
  void reiniciar() {
    state = const DiagnosticState();
  }
}

/// Provider del diagnóstico.
final diagnosticProvider =
    StateNotifierProvider<DiagnosticNotifier, DiagnosticState>((ref) {
  final db = ref.watch(databaseServiceProvider);
  return DiagnosticNotifier(db);
});
