import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';

import '../../../../core/database/database_service.dart';
import '../models/phoneme.dart';
import '../models/exercise_result.dart';

/// Repositorio de fonemas y resultados de ejercicios.
/// Gestiona el catálogo de fonemas y el historial de ejercicios.
class PhonemeRepository {
  final Isar _isar;

  PhonemeRepository(this._isar);

  // ─── Catálogo de fonemas ───

  /// Obtener todos los fonemas ordenados por currículo.
  Future<List<Phoneme>> obtenerTodos() async {
    return await _isar.phonemes
        .where()
        .sortByOrdenCurriculo()
        .findAll();
  }

  /// Obtener fonemas por tipo (vocal, consonante, sílaba, dígrafo).
  Future<List<Phoneme>> obtenerPorTipo(TipoFonema tipo) async {
    return await _isar.phonemes
        .filter()
        .tipoEqualTo(tipo)
        .sortByOrdenCurriculo()
        .findAll();
  }

  /// Buscar un fonema por su grafema.
  Future<Phoneme?> obtenerPorGrafema(String grafema) async {
    return await _isar.phonemes
        .filter()
        .grafemaEqualTo(grafema)
        .findFirst();
  }

  /// Precargar el catálogo inicial de fonemas al instalar la app.
  Future<void> precargarFonemas() async {
    final existentes = await _isar.phonemes.count();
    if (existentes > 0) return; // Ya están precargados

    final fonemas = _generarCatalogoInicial();
    await _isar.writeTxn(() async {
      await _isar.phonemes.putAll(fonemas);
    });
  }

  /// Genera el catálogo inicial de fonemas del español.
  List<Phoneme> _generarCatalogoInicial() {
    int orden = 0;

    // Vocales
    final vocales = ['a', 'e', 'i', 'o', 'u'].map((v) {
      return Phoneme()
        ..grafema = v
        ..tipo = TipoFonema.vocal
        ..rutaAudio = 'assets/audio/fonemas/$v.mp3'
        ..descripcionFonetica = 'Sonido /$v/'
        ..palabraEjemplo = _ejemploVocal(v)
        ..ordenCurriculo = orden++
        ..desbloqueadoPorDefecto = true
        ..confusionesComunes = []
        ..variantes = [];
    }).toList();

    // Consonantes
    final consonantesData = {
      'm': ('mamá', ['n']),
      'p': ('papá', ['b']),
      's': ('sol', ['z', 'c']),
      'l': ('luna', ['r']),
      'n': ('nariz', ['m']),
      't': ('taza', ['d']),
      'd': ('dedo', ['t', 'b']),
      'r': ('rana', ['l', 'rr']),
      'b': ('boca', ['d', 'p']),
      'c': ('casa', ['s', 'k']),
      'f': ('foca', []),
      'g': ('gato', ['j']),
      'h': ('huevo', []),
      'j': ('jugo', ['g']),
      'k': ('kilo', ['c']),
      'v': ('vaso', ['b']),
      'w': ('wifi', []),
      'x': ('xilófono', ['s']),
      'y': ('yoyo', ['ll']),
      'z': ('zapato', ['s', 'c']),
      'ñ': ('niño', ['n']),
    };

    final consonantes = consonantesData.entries.map((e) {
      return Phoneme()
        ..grafema = e.key
        ..tipo = TipoFonema.consonante
        ..rutaAudio = 'assets/audio/fonemas/${e.key}.mp3'
        ..descripcionFonetica = 'Sonido /${e.key}/'
        ..palabraEjemplo = e.value.$1
        ..ordenCurriculo = orden++
        ..desbloqueadoPorDefecto = e.key == 'm' || e.key == 'p' || e.key == 's'
        ..confusionesComunes = e.value.$2
        ..variantes = [];
    }).toList();

    // Dígrafos
    final digrafosData = {
      'ch': ('chico', []),
      'll': ('llave', ['y']),
      'rr': ('perro', ['r']),
      'gu': ('guante', ['g']),
      'qu': ('queso', ['c', 'k']),
    };

    final digrafos = digrafosData.entries.map((e) {
      return Phoneme()
        ..grafema = e.key
        ..tipo = TipoFonema.digrafo
        ..rutaAudio = 'assets/audio/fonemas/${e.key}.mp3'
        ..descripcionFonetica = 'Sonido /${e.key}/'
        ..palabraEjemplo = e.value.$1
        ..ordenCurriculo = orden++
        ..desbloqueadoPorDefecto = false
        ..confusionesComunes = e.value.$2
        ..variantes = [];
    }).toList();

    return [...vocales, ...consonantes, ...digrafos];
  }

  String _ejemploVocal(String vocal) {
    switch (vocal) {
      case 'a': return 'agua';
      case 'e': return 'estrella';
      case 'i': return 'iglú';
      case 'o': return 'oso';
      case 'u': return 'uva';
      default: return '';
    }
  }

  // ─── Resultados de ejercicios ───

  /// Guardar el resultado de un ejercicio.
  Future<void> guardarResultado(ExerciseResult resultado) async {
    await _isar.writeTxn(() async {
      await _isar.exerciseResults.put(resultado);
    });
  }

  /// Obtener historial de resultados de un perfil.
  Future<List<ExerciseResult>> obtenerResultadosPorPerfil(
    int perfilId, {
    int limite = 50,
  }) async {
    return await _isar.exerciseResults
        .filter()
        .perfilIdEqualTo(perfilId)
        .sortByFechaDesc()
        .limit(limite)
        .findAll();
  }

  /// Obtener resultados de un tipo de ejercicio específico.
  Future<List<ExerciseResult>> obtenerResultadosPorTipo(
    int perfilId,
    TipoEjercicio tipo,
  ) async {
    return await _isar.exerciseResults
        .filter()
        .perfilIdEqualTo(perfilId)
        .tipoEqualTo(tipo)
        .sortByFechaDesc()
        .findAll();
  }

  /// Contar ejercicios correctos consecutivos (para desbloqueo automático HU-05).
  Future<int> contarAciertosConsecutivos(int perfilId) async {
    final resultados = await _isar.exerciseResults
        .filter()
        .perfilIdEqualTo(perfilId)
        .sortByFechaDesc()
        .limit(10)
        .findAll();

    int consecutivos = 0;
    for (final r in resultados) {
      if (r.correcto) {
        consecutivos++;
      } else {
        break;
      }
    }
    return consecutivos;
  }

  /// Calcular tasa de acierto global de un perfil.
  Future<double> calcularTasaAciertoGlobal(int perfilId) async {
    final todos = await _isar.exerciseResults
        .filter()
        .perfilIdEqualTo(perfilId)
        .findAll();

    if (todos.isEmpty) return 0.0;

    final correctos = todos.where((r) => r.correcto).length;
    return correctos / todos.length;
  }
}

/// Provider del repositorio de fonemas.
final phonemeRepositoryProvider = Provider<PhonemeRepository>((ref) {
  final db = ref.watch(databaseServiceProvider);
  return PhonemeRepository(db.instance);
});
