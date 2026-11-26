import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/exercise_result.dart';
import '../../data/models/phoneme.dart';
import '../../data/repositories/phoneme_repository.dart';
import '../../../profile/presentation/providers/profile_provider.dart';

/// Estado de los ejercicios de fonemas.
class PhonemeState {
  final List<Phoneme> fonemas;
  final Phoneme? fonemaActual;
  final List<Phoneme> opcionesEmparejamiento;
  final bool cargando;
  final int aciertosConsecutivos;
  final String? feedback;

  const PhonemeState({
    this.fonemas = const [],
    this.fonemaActual,
    this.opcionesEmparejamiento = const [],
    this.cargando = false,
    this.aciertosConsecutivos = 0,
    this.feedback,
  });

  /// `feedback: null` no borra el mensaje (se interpreta como "sin cambio");
  /// para quitarlo usa `limpiarFeedback: true`.
  PhonemeState copyWith({
    List<Phoneme>? fonemas,
    Phoneme? fonemaActual,
    List<Phoneme>? opcionesEmparejamiento,
    bool? cargando,
    int? aciertosConsecutivos,
    String? feedback,
    bool limpiarFeedback = false,
  }) {
    return PhonemeState(
      fonemas: fonemas ?? this.fonemas,
      fonemaActual: fonemaActual ?? this.fonemaActual,
      opcionesEmparejamiento: opcionesEmparejamiento ?? this.opcionesEmparejamiento,
      cargando: cargando ?? this.cargando,
      aciertosConsecutivos: aciertosConsecutivos ?? this.aciertosConsecutivos,
      feedback: limpiarFeedback ? null : (feedback ?? this.feedback),
    );
  }
}

/// Notifier de ejercicios de fonemas.
class PhonemeNotifier extends StateNotifier<PhonemeState> {
  final PhonemeRepository _repository;
  final Ref _ref;

  PhonemeNotifier(this._repository, this._ref) : super(const PhonemeState());

  /// Cargar catálogo de fonemas. Precarga si es la primera vez.
  Future<void> cargarFonemas() async {
    state = state.copyWith(cargando: true);

    // Precargar catálogo si no existe
    await _repository.precargarFonemas();

    final fonemas = await _repository.obtenerTodos();
    state = state.copyWith(fonemas: fonemas, cargando: false);
  }

  /// Cargar fonemas filtrados por tipo.
  Future<void> cargarPorTipo(TipoFonema tipo) async {
    state = state.copyWith(cargando: true);
    final fonemas = await _repository.obtenerPorTipo(tipo);
    state = state.copyWith(fonemas: fonemas, cargando: false);
  }

  /// Generar un ejercicio de emparejamiento aleatorio (HU-03).
  Future<void> generarEjercicioEmparejamiento() async {
    final todos = await _repository.obtenerTodos();
    if (todos.length < 3) return;

    todos.shuffle();
    // La pregunta es con qué letra empieza: solo sirven ejemplos que empiezan con su grafema
    // (no "pera" para la r), y ningún distractor puede escribirse o sonar igual al comienzo.
    final correcto = todos.firstWhere((f) => f.palabraEjemplo.startsWith(f.grafema));

    // Seleccionar 2 distractores
    final distractores = todos
        .where((f) =>
            !correcto.palabraEjemplo.startsWith(f.grafema) &&
            !_suenanIgual(f.grafema, correcto.grafema))
        .take(2)
        .toList();
    final opciones = [correcto, ...distractores]..shuffle();

    state = state.copyWith(
      fonemaActual: correcto,
      opcionesEmparejamiento: opciones,
      limpiarFeedback: true,
    );
  }

  /// Verificar respuesta en ejercicio de emparejamiento.
  /// Guarda el intento y actualiza el progreso del perfil activo (HU-05).
  Future<void> verificarRespuesta(Phoneme seleccionado) async {
    final perfil = _ref.read(perfilActivoProvider);
    final objetivo = state.fonemaActual;
    if (perfil == null || objetivo == null) return;

    final correcto = seleccionado.grafema == objetivo.grafema;

    // Guardar resultado en Isar
    final resultado = ExerciseResult()
      ..perfilId = perfil.id
      ..tipo = TipoEjercicio.fonemaEmparejamiento
      ..contenidoId = 'fonema_${objetivo.grafema}'
      ..correcto = correcto
      ..tiempoSegundos = 0  // TODO: Implementar cronómetro
      ..fecha = DateTime.now()
      ..detalle = (DetalleEjercicio()
        ..fonemaObjetivo = objetivo.grafema
        ..opcionElegida = seleccionado.grafema
        ..opcionesMostradas = state.opcionesEmparejamiento
            .map((o) => o.grafema)
            .toList());

    await _repository.guardarResultado(resultado);
    await _ref
        .read(profileProvider.notifier)
        .registrarProgresoFonema(objetivo.grafema, correcto);

    if (correcto) {
      final nuevosConsecutivos = state.aciertosConsecutivos + 1;
      state = state.copyWith(
        feedback: '¡Correcto! 🎉',
        aciertosConsecutivos: nuevosConsecutivos,
      );

      // Desbloqueo automático tras 3 aciertos seguidos (HU-05)
      if (nuevosConsecutivos >= 3) {
        state = state.copyWith(
          feedback: '¡Excelente! Has desbloqueado un nuevo nivel 🌟',
          aciertosConsecutivos: 0,
        );
      }
    } else {
      state = state.copyWith(
        feedback: 'Intenta de nuevo. Escucha el sonido otra vez.',
        aciertosConsecutivos: 0,
      );
    }
  }
}

const _mismoSonido = [
  {'b', 'v'},
  {'c', 'k', 'qu'},
  {'c', 's', 'z', 'x'},
  {'g', 'gu'},
  {'g', 'j'},
  {'ll', 'y'},
  {'r', 'rr'},
];

bool _suenanIgual(String a, String b) =>
    _mismoSonido.any((grupo) => grupo.contains(a) && grupo.contains(b));

/// Provider del estado de fonemas.
final phonemeProvider =
    StateNotifierProvider<PhonemeNotifier, PhonemeState>((ref) {
  final repository = ref.watch(phonemeRepositoryProvider);
  return PhonemeNotifier(repository, ref);
});
