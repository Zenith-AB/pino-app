import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';

import '../../../../core/database/database_service.dart';
import '../../../diagnostic/data/models/diagnostic_result.dart';
import '../../../phoneme/data/models/exercise_result.dart';
import '../models/user_profile.dart';

/// Repositorio de perfiles usando Isar (NoSQL local).
/// Todas las operaciones son offline-first y no requieren conexión.
class ProfileRepository {
  final Isar _isar;

  ProfileRepository(this._isar);

  /// Obtener todos los perfiles (para la pantalla de selección).
  Future<List<UserProfile>> obtenerTodos() async {
    return await _isar.userProfiles.where().findAll();
  }

  /// Obtener un perfil por su ID.
  Future<UserProfile?> obtenerPorId(int id) async {
    return await _isar.userProfiles.get(id);
  }

  /// Crear un nuevo perfil con valores iniciales.
  Future<int> crearPerfil({
    required String nombre,
    required int avatarIndex,
    required ProfileMode modo,
  }) async {
    final perfil = UserProfile()
      ..nombre = nombre
      ..avatarIndex = avatarIndex
      ..modo = modo
      ..nivel = UserLevel.preLector
      ..creadoEn = DateTime.now()
      ..progreso = ProgresoUsuario()
      ..configuracion = ConfiguracionPerfil()
      ..erroresFrecuentes = []
      ..racha = RachaUsuario();

    // Configuración por defecto según el modo
    if (modo == ProfileMode.infantil) {
      perfil.configuracion.tiempoMaximoMinutos = 30;
      perfil.configuracion.toleranciaTrazo = 'alta';
    } else {
      perfil.configuracion.toleranciaTrazo = 'media';
    }

    return await _isar.writeTxn(() async {
      return await _isar.userProfiles.put(perfil);
    });
  }

  /// Actualizar un perfil existente (una sola escritura, todo el documento).
  Future<void> actualizarPerfil(UserProfile perfil) async {
    await _isar.writeTxn(() async {
      await _isar.userProfiles.put(perfil);
    });
  }

  /// Eliminar un perfil por ID junto con todos sus datos asociados
  /// (resultados de ejercicios y diagnósticos), en una sola transacción.
  Future<bool> eliminarPerfil(int id) async {
    return await _isar.writeTxn(() async {
      await _isar.exerciseResults.where().perfilIdEqualTo(id).deleteAll();
      await _isar.diagnosticResults.where().perfilIdEqualTo(id).deleteAll();
      return await _isar.userProfiles.delete(id);
    });
  }

  /// Actualizar el nivel del usuario tras el diagnóstico.
  Future<void> actualizarNivel(int perfilId, UserLevel nuevoNivel) async {
    final perfil = await obtenerPorId(perfilId);
    if (perfil == null) return;

    perfil.nivel = nuevoNivel;
    await actualizarPerfil(perfil);
  }

  /// Registrar un día completado en la racha (HU-08).
  Future<void> registrarDiaCompletado(int perfilId) async {
    final perfil = await obtenerPorId(perfilId);
    if (perfil == null) return;

    final hoy = DateTime.now().toIso8601String().substring(0, 10);

    // Evitar duplicados del mismo día
    if (perfil.racha.diasCompletados.contains(hoy)) return;

    // Isar devuelve listas de tamaño fijo: se reemplazan en vez de usar add().
    perfil.racha.diasCompletados = [...perfil.racha.diasCompletados, hoy];

    // Calcular racha consecutiva
    final ayer = DateTime.now()
        .subtract(const Duration(days: 1))
        .toIso8601String()
        .substring(0, 10);

    if (perfil.racha.diasCompletados.contains(ayer)) {
      perfil.racha.diasConsecutivos++;
    } else {
      perfil.racha.diasConsecutivos = 1;
    }

    // Actualizar mejor racha
    if (perfil.racha.diasConsecutivos > perfil.racha.mejorRacha) {
      perfil.racha.mejorRacha = perfil.racha.diasConsecutivos;
    }

    await actualizarPerfil(perfil);
  }

  /// Actualizar el progreso de un fonema específico (HU-05).
  Future<void> actualizarProgresoFonema({
    required int perfilId,
    required String fonemaId,
    required bool acierto,
  }) async {
    final perfil = await obtenerPorId(perfilId);
    if (perfil == null) return;

    // Buscar o crear el progreso del fonema
    var progresoFonema = perfil.progreso.fonemas.firstWhere(
      (f) => f.fonemaId == fonemaId,
      orElse: () {
        final nuevo = ProgresoFonema()..fonemaId = fonemaId;
        perfil.progreso.fonemas = [...perfil.progreso.fonemas, nuevo];
        return nuevo;
      },
    );

    // Actualizar métricas
    if (acierto) {
      progresoFonema.aciertos++;
    } else {
      progresoFonema.fallos++;
    }
    progresoFonema.ultimaPractica = DateTime.now();
    progresoFonema.nivelDominio = progresoFonema.tasaAcierto;

    await actualizarPerfil(perfil);
  }

  /// Obtener los fonemas con menor tasa de acierto (para repaso espaciado HU-05).
  Future<List<ProgresoFonema>> obtenerFonemasDebiles(
    int perfilId, {
    int cantidad = 5,
  }) async {
    final perfil = await obtenerPorId(perfilId);
    if (perfil == null) return [];

    final fonemas = List<ProgresoFonema>.from(perfil.progreso.fonemas);
    fonemas.sort((a, b) => a.tasaAcierto.compareTo(b.tasaAcierto));

    return fonemas.take(cantidad).toList();
  }

  /// Registrar un error frecuente (HU-05).
  Future<void> registrarError({
    required int perfilId,
    required String tipo,
    required String detalle,
  }) async {
    final perfil = await obtenerPorId(perfilId);
    if (perfil == null) return;

    // Buscar si ya existe este error
    final existente = perfil.erroresFrecuentes.where(
      (e) => e.tipo == tipo && e.detalle == detalle,
    );

    if (existente.isNotEmpty) {
      existente.first.frecuencia++;
      existente.first.ultimaOcurrencia = DateTime.now();
    } else {
      perfil.erroresFrecuentes = [
        ...perfil.erroresFrecuentes,
        ErrorFrecuente()
          ..tipo = tipo
          ..detalle = detalle
          ..frecuencia = 1
          ..ultimaOcurrencia = DateTime.now(),
      ];
    }

    await actualizarPerfil(perfil);
  }

  /// Contar perfiles existentes.
  Future<int> contarPerfiles() async {
    return await _isar.userProfiles.count();
  }
}

/// Provider del repositorio de perfiles.
final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  final db = ref.watch(databaseServiceProvider);
  return ProfileRepository(db.instance);
});
