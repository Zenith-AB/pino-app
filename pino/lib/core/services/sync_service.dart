import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';

import '../../features/phoneme/data/models/exercise_result.dart';
import '../../features/profile/data/models/user_profile.dart';
import '../database/database_service.dart';
import 'connectivity_util.dart';

/// Servicio de sincronización entre Isar (local) y Firestore (nube).
/// Implementa el patrón offline-first: escribe siempre en local,
/// sincroniza con la nube cuando hay conexión (HU-10).
class SyncService {
  final Isar _isar;
  final FirebaseFirestore _firestore;
  final ConnectivityUtil _connectivity;

  SyncService(this._isar, this._firestore, this._connectivity);

  /// Sincronizar perfil local → Firestore.
  /// Se llama cuando se detecta conexión después de estar offline.
  Future<void> sincronizarPerfil(int perfilId) async {
    if (!await _connectivity.hayConexion()) return;

    final perfil = await _isar.userProfiles.get(perfilId);
    if (perfil == null) return;

    try {
      await _firestore
          .collection('perfiles')
          .doc(perfilId.toString())
          .set({
            'nombre': perfil.nombre,
            'modo': perfil.modo.name,
            'nivel': perfil.nivel.name,
            'creadoEn': perfil.creadoEn.toIso8601String(),
            'racha': {
              'diasConsecutivos': perfil.racha.diasConsecutivos,
              'mejorRacha': perfil.racha.mejorRacha,
              'diasCompletados': perfil.racha.diasCompletados,
            },
            'progreso': {
              'leccionesTerminadas': perfil.progreso.leccionesTerminadas,
              'porcentajeAciertoGlobal': perfil.progreso.porcentajeAciertoGlobal,
              'trazosCompletados': perfil.progreso.trazosCompletados,
              'fonemas': perfil.progreso.fonemas.map((f) => {
                'fonemaId': f.fonemaId,
                'aciertos': f.aciertos,
                'fallos': f.fallos,
                'nivelDominio': f.nivelDominio,
                'ultimaPractica': f.ultimaPractica?.toIso8601String(),
              }).toList(),
            },
            'erroresFrecuentes': perfil.erroresFrecuentes.map((e) => {
              'tipo': e.tipo,
              'detalle': e.detalle,
              'frecuencia': e.frecuencia,
            }).toList(),
            'sincronizadoEn': FieldValue.serverTimestamp(),
          }, SetOptions(merge: true));
    } catch (e) {
      // Si falla la sincronización, no hay problema.
      // Los datos están seguros en Isar local.
      // Se reintentará en la próxima conexión.
    }
  }

  /// Sincronizar resultados de ejercicios pendientes → Firestore.
  Future<void> sincronizarResultados(int perfilId) async {
    if (!await _connectivity.hayConexion()) return;

    // Obtener resultados recientes no sincronizados
    final resultados = await _isar.exerciseResults
        .filter()
        .perfilIdEqualTo(perfilId)
        .sortByFechaDesc()
        .limit(100)
        .findAll();

    if (resultados.isEmpty) return;

    try {
      final batch = _firestore.batch();

      for (final resultado in resultados) {
        final docRef = _firestore
            .collection('perfiles')
            .doc(perfilId.toString())
            .collection('resultados')
            .doc(resultado.id.toString());

        batch.set(docRef, {
          'tipo': resultado.tipo.name,
          'contenidoId': resultado.contenidoId,
          'correcto': resultado.correcto,
          'tiempoSegundos': resultado.tiempoSegundos,
          'fecha': resultado.fecha.toIso8601String(),
        }, SetOptions(merge: true));
      }

      await batch.commit();
    } catch (e) {
      // Fallo silencioso — se reintenta después
    }
  }

  /// Sincronización completa de un perfil.
  Future<void> sincronizacionCompleta(int perfilId) async {
    await sincronizarPerfil(perfilId);
    await sincronizarResultados(perfilId);
  }
}

/// Provider del servicio de sincronización.
final syncServiceProvider = Provider<SyncService>((ref) {
  final db = ref.watch(databaseServiceProvider);
  final connectivity = ref.watch(connectivityUtilProvider);
  return SyncService(
    db.instance,
    FirebaseFirestore.instance,
    connectivity,
  );
});
