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
  final UserLevel? nivelDetectado;
  final DateTime? horaInicio;

  /// Momento en que se mostró la pregunta actual (para medir cada respuesta).
  final DateTime? horaPregunta;

  const DiagnosticState({
    this.preguntaActual = 0,
    this.respuestas = const [],
    this.completado = false,
    this.nivelDetectado,
    this.horaInicio,
    this.horaPregunta,
  });

  DiagnosticState copyWith({
    int? preguntaActual,
    List<RespuestaDiagnostico>? respuestas,
    bool? completado,
    UserLevel? nivelDetectado,
    DateTime? horaInicio,
    DateTime? horaPregunta,
  }) {
    return DiagnosticState(
      preguntaActual: preguntaActual ?? this.preguntaActual,
      respuestas: respuestas ?? this.respuestas,
      completado: completado ?? this.completado,
      nivelDetectado: nivelDetectado ?? this.nivelDetectado,
      horaInicio: horaInicio ?? this.horaInicio,
      horaPregunta: horaPregunta ?? this.horaPregunta,
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
  final Ref _ref;

  DiagnosticNotifier(this._db, this._ref) : super(const DiagnosticState());

  /// Iniciar el diagnóstico. La pantalla debe llamarlo al abrirse.
  void iniciar() {
    final ahora = DateTime.now();
    state = DiagnosticState(horaInicio: ahora, horaPregunta: ahora);
  }

  /// Responder la pregunta actual.
  void responder(String respuestaElegida) {
    if (state.completado) return;

    final pregunta = preguntasDiagnostico[state.preguntaActual];
    final correcta = respuestaElegida == pregunta.respuestaCorrecta;
    final ahora = DateTime.now();

    final respuesta = RespuestaDiagnostico()
      ..numeroPregunta = state.preguntaActual + 1
      ..pregunta = pregunta.pregunta
      ..respuestaElegida = respuestaElegida
      ..respuestaCorrecta = pregunta.respuestaCorrecta
      ..correcta = correcta
      ..tiempoSegundos = state.horaPregunta != null
          ? ahora.difference(state.horaPregunta!).inSeconds
          : 0;

    final nuevasRespuestas = [...state.respuestas, respuesta];

    if (state.preguntaActual >= preguntasDiagnostico.length - 1) {
      // Última pregunta — calcular nivel
      final nivel = calcularNivel(nuevasRespuestas);
      state = state.copyWith(
        respuestas: nuevasRespuestas,
        completado: true,
        nivelDetectado: nivel,
      );
    } else {
      state = state.copyWith(
        respuestas: nuevasRespuestas,
        preguntaActual: state.preguntaActual + 1,
        horaPregunta: ahora,
      );
    }
  }

  /// Guarda el resultado en Isar y actualiza el nivel del perfil activo.
  Future<void> guardarResultado() async {
    final perfil = _ref.read(perfilActivoProvider);
    final nivel = state.nivelDetectado;
    if (perfil == null || !state.completado || nivel == null) return;

    final resultado = DiagnosticResult()
      ..perfilId = perfil.id
      ..fecha = DateTime.now()
      ..nivelDetectado = nivel
      ..respuestas = state.respuestas
      ..tiempoTotalSegundos = state.horaInicio != null
          ? DateTime.now().difference(state.horaInicio!).inSeconds
          : 0;

    await _db.instance.writeTxn(() async {
      await _db.diagnosticos.put(resultado);
    });
    await _ref.read(profileProvider.notifier).actualizarNivel(nivel);
  }

  /// Reiniciar el diagnóstico.
  void reiniciar() {
    state = const DiagnosticState();
  }
}

/// Clasifica el nivel según las respuestas.
///
/// Las preguntas van de menor a mayor dificultad, así que el nivel es la
/// cantidad de preguntas acertadas *en orden* hasta el primer error. Así un
/// acierto al azar en la pregunta 3 (2 opciones) no sube el nivel de alguien
/// que no reconoce letras.
UserLevel calcularNivel(List<RespuestaDiagnostico> respuestas) {
  final aciertosEnOrden = respuestas.takeWhile((r) => r.correcta).length;
  return UserLevel.values[aciertosEnOrden.clamp(0, UserLevel.values.length - 1)];
}

/// Provider del diagnóstico.
final diagnosticProvider =
    StateNotifierProvider<DiagnosticNotifier, DiagnosticState>((ref) {
  final db = ref.watch(databaseServiceProvider);
  return DiagnosticNotifier(db, ref);
});
