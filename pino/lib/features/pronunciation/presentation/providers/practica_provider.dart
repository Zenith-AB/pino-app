import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/services/grabador_voz.dart';
import '../../../../core/services/ml_api_client.dart';
import '../../../phoneme/data/models/exercise_result.dart';
import '../../../phoneme/data/repositories/phoneme_repository.dart';
import '../../../profile/presentation/providers/profile_provider.dart';

enum FasePractica { lista, grabando, evaluando }

enum Veredicto { bien, casi, otra, sinVoz }

class EstadoPractica {
  const EstadoPractica({this.fase = FasePractica.lista, this.resultado, this.error});

  final FasePractica fase;
  final ResultadoPronunciacionML? resultado;
  final String? error;
}

Veredicto veredictoDe(ResultadoPronunciacionML r) {
  if (r.textoDetectado.trim().isEmpty) return Veredicto.sinVoz;
  if (r.correcto) return Veredicto.bien;
  return r.similitudFonetica >= 0.6 ? Veredicto.casi : Veredicto.otra;
}

/// Graba, envía el audio a la API de Pino y borra el archivo.
class PracticaNotifier extends StateNotifier<EstadoPractica> {
  PracticaNotifier(this._grabador, this._api, {this.alEvaluar}) : super(const EstadoPractica());

  /// Se llama con cada intento en que se oyó algo, para guardar el progreso.
  final Future<void> Function(String palabra, ResultadoPronunciacionML resultado)? alEvaluar;

  final GrabadorVoz _grabador;
  final MLApiClient _api;

  /// Cambia al pasar a otra palabra, para descartar respuestas atrasadas.
  int _turno = 0;

  /// Evita iniciar dos grabaciones con un doble toque.
  bool _iniciando = false;

  Future<void> alternarGrabacion({required String palabra, required String idioma}) async {
    final turno = _turno;
    try {
      switch (state.fase) {
        case FasePractica.evaluando:
          return;
        case FasePractica.lista:
          if (_iniciando) return;
          _iniciando = true;
          final bool permitido;
          try {
            permitido = await _grabador.iniciar();
          } finally {
            _iniciando = false;
          }
          if (!mounted || turno != _turno) {
            // Cambió la palabra mientras arrancaba el micrófono.
            if (permitido) await _descartar();
            return;
          }
          state = permitido
              ? const EstadoPractica(fase: FasePractica.grabando)
              : const EstadoPractica(error: 'Pino necesita permiso para usar el micrófono.');
        case FasePractica.grabando:
          state = const EstadoPractica(fase: FasePractica.evaluando);
          final audio = await _grabador.detener();
          if (audio == null) throw StateError('sin audio');
          try {
            final resultado = await _api.evaluarPronunciacion(
              archivoAudio: audio,
              textoEsperado: palabra,
              idioma: idioma,
            );
            if (mounted && turno == _turno) state = EstadoPractica(resultado: resultado);
            if (veredictoDe(resultado) != Veredicto.sinVoz) await _guardar(palabra, resultado);
          } finally {
            if (audio.existsSync()) audio.deleteSync();
          }
      }
    } catch (_) {
      if (mounted && turno == _turno) {
        state = const EstadoPractica(
          error: 'No se pudo evaluar. Revisa la conexión con Pino y vuelve a intentar.',
        );
      }
    }
  }

  Future<void> reiniciar() async {
    _turno++;
    final grababa = state.fase == FasePractica.grabando;
    state = const EstadoPractica();
    if (grababa) await _descartar();
  }

  /// Un fallo al guardar no borra el resultado que ya se mostró.
  Future<void> _guardar(String palabra, ResultadoPronunciacionML resultado) async {
    try {
      await alEvaluar?.call(palabra, resultado);
    } catch (e) {
      debugPrint('No se pudo guardar el intento: $e');
    }
  }

  Future<void> _descartar() async {
    final audio = await _grabador.detener();
    if (audio != null && audio.existsSync()) audio.deleteSync();
  }
}

final practicaProvider = StateNotifierProvider.autoDispose<PracticaNotifier, EstadoPractica>(
  (ref) => PracticaNotifier(
    ref.watch(grabadorVozProvider),
    ref.watch(mlApiClientProvider),
    alEvaluar: (palabra, resultado) => registrarLectura(ref, palabra, resultado),
  ),
);

/// Guarda el intento en el historial del perfil activo y cuenta el día en su racha.
/// Sin perfil (práctica libre) no guarda nada.
Future<void> registrarLectura(Ref ref, String palabra, ResultadoPronunciacionML resultado) async {
  final perfil = ref.read(perfilActivoProvider);
  if (perfil == null) return;

  await ref
      .read(phonemeRepositoryProvider)
      .guardarResultado(
        ExerciseResult()
          ..perfilId = perfil.id
          ..tipo = TipoEjercicio.lecturaVozAlta
          ..contenidoId = 'palabra_$palabra'
          ..correcto = resultado.correcto
          ..tiempoSegundos = 0
          ..fecha = DateTime.now()
          ..detalle = (DetalleEjercicio()
            ..silabasMalPronunciadas = resultado.silabasIncorrectas
            ..puntajePronunciacion = resultado.puntajeGlobal),
      );
  await ref.read(profileProvider.notifier).completarDia();
}
