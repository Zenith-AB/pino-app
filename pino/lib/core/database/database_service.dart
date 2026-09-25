import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:path_provider/path_provider.dart';

import '../../features/profile/data/models/user_profile.dart';
import '../../features/phoneme/data/models/phoneme.dart';
import '../../features/phoneme/data/models/exercise_result.dart';
import '../../features/diagnostic/data/models/diagnostic_result.dart';

/// Servicio central de base de datos NoSQL (Isar).
/// Gestiona la inicialización y el acceso a todas las colecciones.
class DatabaseService {
  late Isar _isar;

  Isar get instance => _isar;

  /// Inicializa Isar con todas las colecciones del proyecto.
  /// Se llama una sola vez al arrancar la app.
  Future<void> inicializar() async {
    final dir = await getApplicationDocumentsDirectory();

    _isar = await Isar.open(
      [
        UserProfileSchema,
        ExerciseResultSchema,
        DiagnosticResultSchema,
        PhonemeSchema,
      ],
      directory: dir.path,
      name: 'pino_db',
    );
  }

  /// Cierra la conexión a la base de datos.
  Future<void> cerrar() async {
    await _isar.close();
  }

  // ─── Acceso rápido a colecciones ───

  IsarCollection<UserProfile> get perfiles => _isar.userProfiles;
  IsarCollection<ExerciseResult> get resultados => _isar.exerciseResults;
  IsarCollection<DiagnosticResult> get diagnosticos => _isar.diagnosticResults;
  IsarCollection<Phoneme> get fonemas => _isar.phonemes;
}

/// Provider global del servicio de base de datos.
/// Se inicializa en main.dart antes de runApp.
final databaseServiceProvider = Provider<DatabaseService>((ref) {
  throw UnimplementedError(
    'DatabaseService debe inicializarse antes de crear el ProviderScope. '
    'Usa un override en main.dart.',
  );
});
