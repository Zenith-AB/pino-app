import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// Voz del dispositivo para leer palabras (HU-01, HU-06). Funciona sin conexión
/// si el teléfono tiene instalada la voz del idioma.
class TtsService {
  TtsService([FlutterTts? tts]) : _tts = tts ?? FlutterTts();

  static const velocidadNormal = 0.45;
  static const velocidadLenta = 0.2;

  /// Se usa la primera voz disponible de cada lista.
  static const _voces = {
    'es': ['es-CL', 'es-US', 'es-MX', 'es-ES'],
    'en': ['en-US', 'en-GB'],
  };

  final FlutterTts _tts;

  /// Devuelve `false` si el dispositivo no tiene voz para el idioma.
  Future<bool> hablar(String texto, {String idioma = 'es', bool lento = false}) async {
    try {
      for (final codigo in _voces[idioma] ?? const <String>[]) {
        if (await _tts.isLanguageAvailable(codigo) == true) {
          await _tts.stop();
          await _tts.setLanguage(codigo);
          await _tts.setSpeechRate(lento ? velocidadLenta : velocidadNormal);
          await _tts.speak(texto);
          return true;
        }
      }
    } on MissingPluginException {
      // flutter_tts no tiene versión para Linux.
    }
    return false;
  }

  Future<void> detener() async {
    try {
      await _tts.stop();
    } on MissingPluginException {
      // Sin motor de voz no hay nada que detener.
    }
  }
}

final ttsServiceProvider = Provider<TtsService>((ref) => TtsService());
