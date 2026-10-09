import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';

import '../../features/phoneme/data/models/exercise_result.dart';
import '../../features/profile/data/models/user_profile.dart';
import '../database/database_service.dart';
import '../utils/connectivity_util.dart';

/// Servicio de sincronización entre Isar (local) y Firestore (nube).
/// Implementa el patrón offline-first: escribe siempre en local,
/// sincroniza con la nube cuando hay conexión (HU-10).
///
/// Estructura en Firestore (ver `firestore.rules`):
///   usuarios/{uid}/perfiles/{perfil.syncId}
///   usuarios/{uid}/perfiles/{perfil.syncId}/resultados/{resultado.syncId}
///
/// `uid` es el usuario de Firebase Auth (el tutor/dispositivo). Los IDs locales
/// de Isar no se usan en la nube porque se repiten entre dispositivos.
class SyncService {
  /// Firestore admite hasta 500 escrituras por batch.
  static const _maxPorBatch = 400;

  final Isar _isar;
  final FirebaseFirestore _firestore;
  final ConnectivityUtil _connectivity;

  SyncService(this._isar, this._firestore, this._connectivity);

  DocumentReference<Map<String, dynamic>> _docPerfil(
    String uid,
    UserProfile perfil,
  ) {
    return _firestore
        .collection('usuarios')
        .doc(uid)
        .collection('perfiles')
        .doc(perfil.syncId);
  }

  /// Sincronizar perfil local → Firestore.
  /// Devuelve `false` si no se pudo (sin conexión o error); se reintenta luego.
  Future<bool> sincronizarPerfil({
    required String uid,
    required int perfilId,
  }) async {
    if (!await _connectivity.hayConexion()) return false;

    final perfil = await _isar.userProfiles.get(perfilId);
    if (perfil == null) return false;

    try {
      await _docPerfil(uid, perfil).set({
        'nombre': perfil.nombre,
        'modo': perfil.modo.name,
        'nivel': perfil.nivel.name,
        'creadoEn': Timestamp.fromDate(perfil.creadoEn),
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
      return true;
    } catch (e, st) {
      // Los datos siguen seguros en Isar; se reintenta en la próxima conexión.
      debugPrint('SyncService: no se pudo sincronizar el perfil $perfilId: $e\n$st');
      return false;
    }
  }

  /// Sube los resultados pendientes (`sincronizado == false`) en lotes y los
  /// marca como sincronizados en Isar. Devuelve cuántos se subieron.
  Future<int> sincronizarResultados({
    required String uid,
    required int perfilId,
  }) async {
    if (!await _connectivity.hayConexion()) return 0;

    final perfil = await _isar.userProfiles.get(perfilId);
    if (perfil == null) return 0;
    final coleccion = _docPerfil(uid, perfil).collection('resultados');

    var subidos = 0;
    while (true) {
      final pendientes = await _isar.exerciseResults
          .where()
          .perfilIdEqualTo(perfilId)
          .filter()
          .sincronizadoEqualTo(false)
          .limit(_maxPorBatch)
          .findAll();
      if (pendientes.isEmpty) break;

      try {
        final batch = _firestore.batch();
        for (final resultado in pendientes) {
          batch.set(coleccion.doc(resultado.syncId), {
            'tipo': resultado.tipo.name,
            'contenidoId': resultado.contenidoId,
            'correcto': resultado.correcto,
            'tiempoSegundos': resultado.tiempoSegundos,
            'fecha': Timestamp.fromDate(resultado.fecha),
          });
        }
        await batch.commit();
      } catch (e, st) {
        // Lo que no se subió queda pendiente para el próximo intento.
        debugPrint('SyncService: no se pudieron subir resultados: $e\n$st');
        break;
      }

      for (final resultado in pendientes) {
        resultado.sincronizado = true;
      }
      await _isar.writeTxn(() => _isar.exerciseResults.putAll(pendientes));
      subidos += pendientes.length;
    }
    return subidos;
  }

  /// Sincronización completa de un perfil.
  Future<void> sincronizacionCompleta({
    required String uid,
    required int perfilId,
  }) async {
    await sincronizarPerfil(uid: uid, perfilId: perfilId);
    await sincronizarResultados(uid: uid, perfilId: perfilId);
  }
}

/// Provider del servicio de sincronización.
/// Requiere `Firebase.initializeApp()` antes de leerlo (ver main.dart).
final syncServiceProvider = Provider<SyncService>((ref) {
  final db = ref.watch(databaseServiceProvider);
  final connectivity = ref.watch(connectivityUtilProvider);
  return SyncService(
    db.instance,
    FirebaseFirestore.instance,
    connectivity,
  );
});
