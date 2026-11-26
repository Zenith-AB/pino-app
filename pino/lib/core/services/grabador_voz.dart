import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

/// Grabación del micrófono a un archivo temporal.
abstract class GrabadorVoz {
  /// Devuelve `false` si no hay permiso de micrófono.
  Future<bool> iniciar();

  /// Termina la grabación y entrega el archivo, o `null` si no se grabó nada.
  Future<File?> detener();

  Future<void> cerrar();
}

class GrabadorMicrofono implements GrabadorVoz {
  AudioRecorder? _grabador;
  String? _ruta;

  @override
  Future<bool> iniciar() async {
    final grabador = _grabador ??= AudioRecorder();
    if (!await grabador.hasPermission()) return false;
    final carpeta = await getTemporaryDirectory();
    // Un archivo por grabación: borrar una evaluación anterior no afecta a la nueva.
    final ruta = '${carpeta.path}/pino_voz_${DateTime.now().microsecondsSinceEpoch}.wav';
    await grabador.start(
      const RecordConfig(encoder: AudioEncoder.wav, sampleRate: 16000, numChannels: 1),
      path: ruta,
    );
    _ruta = ruta;
    return true;
  }

  @override
  Future<File?> detener() async {
    final ruta = await _grabador?.stop();
    _ruta = null;
    return ruta == null ? null : File(ruta);
  }

  @override
  Future<void> cerrar() async {
    // Si se sale de la pantalla mientras se graba, no queda el audio en el teléfono.
    final pendiente = _ruta;
    await _grabador?.dispose();
    _grabador = null;
    _ruta = null;
    if (pendiente != null && File(pendiente).existsSync()) File(pendiente).deleteSync();
  }
}

final grabadorVozProvider = Provider.autoDispose<GrabadorVoz>((ref) {
  final grabador = GrabadorMicrofono();
  ref.onDispose(grabador.cerrar);
  return grabador;
});
