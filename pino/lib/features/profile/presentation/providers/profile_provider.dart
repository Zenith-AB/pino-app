import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/user_profile.dart';
import '../../data/repositories/profile_repository.dart';

/// Estado del perfil activo en la aplicación.
class ProfileState {
  final List<UserProfile> perfiles;
  final UserProfile? perfilActivo;
  final bool cargando;

  const ProfileState({
    this.perfiles = const [],
    this.perfilActivo,
    this.cargando = false,
  });

  ProfileState copyWith({
    List<UserProfile>? perfiles,
    UserProfile? perfilActivo,
    bool? cargando,
  }) {
    return ProfileState(
      perfiles: perfiles ?? this.perfiles,
      perfilActivo: perfilActivo ?? this.perfilActivo,
      cargando: cargando ?? this.cargando,
    );
  }
}

/// Notifier que gestiona el estado de los perfiles.
class ProfileNotifier extends StateNotifier<ProfileState> {
  final ProfileRepository _repository;

  ProfileNotifier(this._repository) : super(const ProfileState());

  /// Cargar todos los perfiles desde Isar.
  Future<void> cargarPerfiles() async {
    state = state.copyWith(cargando: true);
    final perfiles = await _repository.obtenerTodos();
    state = state.copyWith(perfiles: perfiles, cargando: false);
  }

  /// Seleccionar un perfil como activo.
  void seleccionarPerfil(UserProfile perfil) {
    state = state.copyWith(perfilActivo: perfil);
  }

  /// Crear un nuevo perfil.
  Future<int> crearPerfil({
    required String nombre,
    required int avatarIndex,
    required ProfileMode modo,
  }) async {
    final id = await _repository.crearPerfil(
      nombre: nombre,
      avatarIndex: avatarIndex,
      modo: modo,
    );
    await cargarPerfiles();
    return id;
  }

  /// Eliminar un perfil.
  Future<void> eliminarPerfil(int id) async {
    await _repository.eliminarPerfil(id);

    // Si el perfil eliminado era el activo, limpiar selección
    if (state.perfilActivo?.id == id) {
      state = state.copyWith(perfilActivo: null);
    }
    await cargarPerfiles();
  }

  /// Actualizar el nivel tras el diagnóstico.
  Future<void> actualizarNivel(UserLevel nuevoNivel) async {
    final perfil = state.perfilActivo;
    if (perfil == null) return;

    await _repository.actualizarNivel(perfil.id, nuevoNivel);

    // Recargar el perfil actualizado
    final actualizado = await _repository.obtenerPorId(perfil.id);
    if (actualizado != null) {
      state = state.copyWith(perfilActivo: actualizado);
    }
  }

  /// Registrar progreso de un fonema.
  Future<void> registrarProgresoFonema(String fonemaId, bool acierto) async {
    final perfil = state.perfilActivo;
    if (perfil == null) return;

    await _repository.actualizarProgresoFonema(
      perfilId: perfil.id,
      fonemaId: fonemaId,
      acierto: acierto,
    );

    // Recargar perfil con progreso actualizado
    final actualizado = await _repository.obtenerPorId(perfil.id);
    if (actualizado != null) {
      state = state.copyWith(perfilActivo: actualizado);
    }
  }

  /// Marcar día como completado en la racha.
  Future<void> completarDia() async {
    final perfil = state.perfilActivo;
    if (perfil == null) return;

    await _repository.registrarDiaCompletado(perfil.id);

    final actualizado = await _repository.obtenerPorId(perfil.id);
    if (actualizado != null) {
      state = state.copyWith(perfilActivo: actualizado);
    }
  }
}

/// Provider del estado de perfiles.
final profileProvider =
    StateNotifierProvider<ProfileNotifier, ProfileState>((ref) {
  final repository = ref.watch(profileRepositoryProvider);
  return ProfileNotifier(repository);
});

/// Provider de conveniencia: perfil activo actual.
final perfilActivoProvider = Provider<UserProfile?>((ref) {
  return ref.watch(profileProvider).perfilActivo;
});

/// Provider de conveniencia: modo actual (infantil/adulto).
final modoActualProvider = Provider<ProfileMode?>((ref) {
  return ref.watch(perfilActivoProvider)?.modo;
});
