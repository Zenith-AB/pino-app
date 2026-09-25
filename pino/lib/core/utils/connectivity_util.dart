import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Utilidad para verificar el estado de conectividad del dispositivo.
/// Usado por SyncService para decidir cuándo sincronizar con Firestore (HU-10).
class ConnectivityUtil {
  final Connectivity _connectivity = Connectivity();

  /// Verifica si el dispositivo tiene conexión a internet.
  Future<bool> hayConexion() async {
    final resultado = await _connectivity.checkConnectivity();
    return resultado != ConnectivityResult.none;
  }

  /// Stream reactivo de cambios de conectividad.
  /// Se usa para disparar sincronización automática al recuperar conexión.
  Stream<bool> get cambiosConectividad {
    return _connectivity.onConnectivityChanged.map(
      (resultado) => resultado != ConnectivityResult.none,
    );
  }
}

/// Provider de la utilidad de conectividad.
final connectivityUtilProvider = Provider<ConnectivityUtil>((ref) {
  return ConnectivityUtil();
});
