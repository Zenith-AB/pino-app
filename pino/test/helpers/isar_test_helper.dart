import 'dart:ffi' show Abi;
import 'dart:io';
import 'dart:math';

import 'package:isar/isar.dart';

import 'package:pino/features/diagnostic/data/models/diagnostic_result.dart';
import 'package:pino/features/phoneme/data/models/exercise_result.dart';
import 'package:pino/features/phoneme/data/models/phoneme.dart';
import 'package:pino/features/profile/data/models/user_profile.dart';

bool _coreInicializado = false;

/// Carga la librería nativa de Isar para correr los tests en el PC (no en el
/// teléfono). Se descarga una sola vez a `.dart_tool/isar_test/`.
///
/// `flutter test` corre cada archivo en un proceso aparte y en paralelo. Si
/// todos descargaran al mismo archivo, uno podría cargarlo a medio escribir y
/// caerse (segmentation fault). Por eso cada proceso descarga a un archivo
/// propio en la misma carpeta y luego lo mueve con `rename`, que es atómico.
Future<void> _inicializarIsarCore() async {
  final carpeta = Directory('${Directory.current.path}/.dart_tool/isar_test');
  final nombre = Platform.isWindows
      ? 'isar.dll'
      : Platform.isMacOS
          ? 'libisar.dylib'
          : 'libisar.so';
  final compartida = File('${carpeta.path}/$nombre');

  if (compartida.existsSync()) {
    await Isar.initializeIsarCore(libraries: {Abi.current(): compartida.path});
    return;
  }

  await carpeta.create(recursive: true);
  final propia = '${carpeta.path}/descarga_${pid}_${Random().nextInt(1 << 32)}_$nombre';
  await Isar.initializeIsarCore(libraries: {Abi.current(): propia}, download: true);
  try {
    File(propia).renameSync(compartida.path);
  } on FileSystemException {
    // Otro proceso ya dejó la suya; esta copia ya está cargada y sirve igual.
  }
}

/// Abre una base Isar temporal con todas las colecciones de la app.
/// Llama a [cerrarIsarDePrueba] en el tearDown.
Future<Isar> abrirIsarDePrueba() async {
  if (!_coreInicializado) {
    await _inicializarIsarCore();
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
