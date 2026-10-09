import 'dart:io';

import 'package:isar/isar.dart';

import 'package:pino/features/diagnostic/data/models/diagnostic_result.dart';
import 'package:pino/features/phoneme/data/models/exercise_result.dart';
import 'package:pino/features/phoneme/data/models/phoneme.dart';
import 'package:pino/features/profile/data/models/user_profile.dart';

bool _coreInicializado = false;

/// Abre una base Isar temporal con todas las colecciones de la app.
/// Llama a [cerrarIsarDePrueba] en el tearDown.
Future<Isar> abrirIsarDePrueba() async {
  if (!_coreInicializado) {
    // Descarga la librería nativa de Isar para correr en el host (no en el teléfono).
    await Isar.initializeIsarCore(download: true);
    _coreInicializado = true;
  }
  final dir = await Directory.systemTemp.createTemp('pino_test_');
  return Isar.open(
    [UserProfileSchema, ExerciseResultSchema, DiagnosticResultSchema, PhonemeSchema],
    directory: dir.path,
    name: 'test_${DateTime.now().microsecondsSinceEpoch}',
  );
}

Future<void> cerrarIsarDePrueba(Isar isar) async {
  final dir = isar.directory;
  await isar.close(deleteFromDisk: true);
  if (dir != null) await Directory(dir).delete(recursive: true);
}
