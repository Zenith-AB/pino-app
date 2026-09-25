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

  PhonemeState copyWith({
    List<Phoneme>? fonemas,
    Phoneme? fonemaActual,
    List<Phoneme>? opcionesEmparejamiento,
    bool? cargando,
    int? aciertosConsecutivos,
    String? feedback,
  }) {
    return PhonemeState(
      fonemas: fonemas ?? this.fonemas,
      fonemaActual: fonemaActual ?? this.fonemaActual,
      opcionesEmparejamiento: opcionesEmparejamiento ?? this.opcionesEmparejamiento,
      cargando: cargando ?? this.cargando,
      aciertosConsecutivos: aciertosConsecutivos ?? this.aciertosConsecutivos,
      feedback: feedback ?? this.feedback,
    );
  }
}

/// Notifier de ejercicios de fonemas.
class PhonemeNotifier extends StateNotifier<PhonemeState> {
  final PhonemeRepository _repository;

  PhonemeNotifier(this._repository) : super(const PhonemeState());

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
    final correcto = todos.first;

    // Seleccionar 2 distractores
    final distractores = todos.sublist(1, 3);
    final opciones = [correcto, ...distractores]..shuffle();

    state = state.copyWith(
      fonemaActual: correcto,
      opcionesEmparejamiento: opciones,
      feedback: null,
    );
  }

  /// Verificar respuesta en ejercicio de emparejamiento.
  Future<void> verificarRespuesta(
    Phoneme seleccionado,
    int perfilId,
  ) async {
    final correcto = seleccionado.grafema == state.fonemaActual?.grafema;

    // Guardar resultado en Isar
    final resultado = ExerciseResult()
      ..perfilId = perfilId
      ..tipo = TipoEjercicio.fonemaEmparejamiento
      ..contenidoId = 'fonema_${state.fonemaActual?.grafema}'
      ..correcto = correcto
      ..tiempoSegundos = 0  // TODO: Implementar cronómetro
      ..fecha = DateTime.now()
      ..detalle = (DetalleEjercicio()
        ..fonemaObjetivo = state.fonemaActual?.grafema
        ..opcionElegida = seleccionado.grafema
        ..opcionesMostradas = state.opcionesEmparejamiento
            .map((o) => o.grafema)
            .toList());

    await _repository.guardarResultado(resultado);

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

/// Provider del estado de fonemas.
final phonemeProvider =
    StateNotifierProvider<PhonemeNotifier, PhonemeState>((ref) {
  final repository = ref.watch(phonemeRepositoryProvider);
  return PhonemeNotifier(repository);
});
