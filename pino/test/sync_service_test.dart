import 'package:fake_cloud_firestore/fake_cloud_firestore.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';

import 'package:pino/core/services/sync_service.dart';
import 'package:pino/core/utils/connectivity_util.dart';
import 'package:pino/features/phoneme/data/models/exercise_result.dart';
import 'package:pino/features/phoneme/data/repositories/phoneme_repository.dart';
import 'package:pino/features/profile/data/models/user_profile.dart';
import 'package:pino/features/profile/data/repositories/profile_repository.dart';

import 'helpers/isar_test_helper.dart';

class _ConexionFalsa extends ConnectivityUtil {
  bool conectado = true;

  @override
  Future<bool> hayConexion() async => conectado;
}

void main() {
  late Isar isar;
  late FakeFirebaseFirestore firestore;
  late _ConexionFalsa conexion;
  late SyncService sync;

  setUp(() async {
    isar = await abrirIsarDePrueba();
    firestore = FakeFirebaseFirestore();
    conexion = _ConexionFalsa();
    sync = SyncService(isar, firestore, conexion);
  });

  tearDown(() => cerrarIsarDePrueba(isar));

  Future<UserProfile> crearPerfil(String nombre) async {
    final repo = ProfileRepository(isar);
    final id = await repo.crearPerfil(
      nombre: nombre,
      avatarIndex: 0,
      modo: ProfileMode.infantil,
    );
    return (await repo.obtenerPorId(id))!;
  }

  Future<void> guardarResultados(int perfilId, int cantidad) async {
    final repo = PhonemeRepository(isar);
    for (var i = 0; i < cantidad; i++) {
      await repo.guardarResultado(ExerciseResult()
        ..perfilId = perfilId
        ..tipo = TipoEjercicio.fonemaEmparejamiento
        ..contenidoId = 'fonema_a'
        ..correcto = i.isEven
        ..tiempoSegundos = 2
        ..fecha = DateTime.now()
        ..detalle = DetalleEjercicio());
    }
  }

  test('el perfil se guarda bajo usuarios/{uid} con su syncId', () async {
    final perfil = await crearPerfil('Ana');

    final ok = await sync.sincronizarPerfil(uid: 'tutor-1', perfilId: perfil.id);

    expect(ok, isTrue);
    final doc = await firestore
        .doc('usuarios/tutor-1/perfiles/${perfil.syncId}')
        .get();
    expect(doc.data()!['nombre'], 'Ana');
    // Nada en la ruta antigua que usaba el ID local.
    expect((await firestore.collection('perfiles').get()).docs, isEmpty);
  });

  test('perfiles con el mismo ID local en dos dispositivos no se pisan', () async {
    // Simula dos teléfonos: cada uno tiene su propio Isar y su perfil con id local 1.
    final perfilA = await crearPerfil('Ana');
    final otroIsar = await abrirIsarDePrueba();
    addTearDown(() => cerrarIsarDePrueba(otroIsar));
    final repoB = ProfileRepository(otroIsar);
    final idB = await repoB.crearPerfil(
      nombre: 'Luis',
      avatarIndex: 1,
      modo: ProfileMode.adulto,
    );
    expect(idB, perfilA.id);

    await sync.sincronizarPerfil(uid: 'tutor-1', perfilId: perfilA.id);
    await SyncService(otroIsar, firestore, conexion)
        .sincronizarPerfil(uid: 'tutor-2', perfilId: idB);

    final perfiles = await firestore.collectionGroup('perfiles').get();
    expect(perfiles.docs.map((d) => d['nombre']), unorderedEquals(['Ana', 'Luis']));
  });

  test('sube solo resultados pendientes y los marca como sincronizados', () async {
    final perfil = await crearPerfil('Ana');
    await guardarResultados(perfil.id, 3);

    expect(await sync.sincronizarResultados(uid: 'tutor-1', perfilId: perfil.id), 3);
    // Segunda vez: no hay nada pendiente.
    expect(await sync.sincronizarResultados(uid: 'tutor-1', perfilId: perfil.id), 0);

    await guardarResultados(perfil.id, 2);
    expect(await sync.sincronizarResultados(uid: 'tutor-1', perfilId: perfil.id), 2);

    final remotos = await firestore
        .collection('usuarios/tutor-1/perfiles/${perfil.syncId}/resultados')
        .get();
    expect(remotos.docs, hasLength(5));
  });

  test('más de un lote (500+) se sube completo', () async {
    final perfil = await crearPerfil('Ana');
    await guardarResultados(perfil.id, 450);

    final subidos =
        await sync.sincronizarResultados(uid: 'tutor-1', perfilId: perfil.id);

    expect(subidos, 450);
  });

  test('sin conexión no sube nada y deja todo pendiente', () async {
    final perfil = await crearPerfil('Ana');
    await guardarResultados(perfil.id, 2);
    conexion.conectado = false;

    expect(await sync.sincronizarResultados(uid: 'tutor-1', perfilId: perfil.id), 0);

    conexion.conectado = true;
    expect(await sync.sincronizarResultados(uid: 'tutor-1', perfilId: perfil.id), 2);
  });
}
