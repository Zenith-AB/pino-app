import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';

import 'package:pino/features/diagnostic/data/models/diagnostic_result.dart';
import 'package:pino/features/phoneme/data/models/exercise_result.dart';
import 'package:pino/features/phoneme/data/repositories/phoneme_repository.dart';
import 'package:pino/features/profile/data/models/user_profile.dart';
import 'package:pino/features/profile/data/repositories/profile_repository.dart';

import 'helpers/isar_test_helper.dart';

void main() {
  late Isar isar;

  setUp(() async => isar = await abrirIsarDePrueba());
  tearDown(() => cerrarIsarDePrueba(isar));

  group('ProfileRepository', () {
    test('crea perfiles infantil y adulto sin campos opcionales', () async {
      final repo = ProfileRepository(isar);

      final idInfantil = await repo.crearPerfil(
        nombre: 'Ana',
        avatarIndex: 0,
        modo: ProfileMode.infantil,
      );
      final idAdulto = await repo.crearPerfil(
        nombre: 'Luis',
        avatarIndex: 1,
        modo: ProfileMode.adulto,
      );

      final infantil = await repo.obtenerPorId(idInfantil);
      final adulto = await repo.obtenerPorId(idAdulto);
      expect(infantil!.configuracion.tiempoMaximoMinutos, 30);
      expect(adulto!.configuracion.tiempoMaximoMinutos, isNull);
      expect(adulto.configuracion.varianteDialectal, isNull);
    });

    test('registra progreso de un fonema nuevo', () async {
      final repo = ProfileRepository(isar);
      final id = await repo.crearPerfil(
        nombre: 'Ana',
        avatarIndex: 0,
        modo: ProfileMode.infantil,
      );

      await repo.actualizarProgresoFonema(perfilId: id, fonemaId: 'm', acierto: true);
      await repo.actualizarProgresoFonema(perfilId: id, fonemaId: 'm', acierto: false);

      final perfil = await repo.obtenerPorId(id);
      final m = perfil!.progreso.fonemas.single;
      expect(m.aciertos, 1);
      expect(m.fallos, 1);
      expect(m.nivelDominio, 0.5);
    });

    test('registra el día en la racha una sola vez', () async {
      final repo = ProfileRepository(isar);
      final id = await repo.crearPerfil(
        nombre: 'Ana',
        avatarIndex: 0,
        modo: ProfileMode.infantil,
      );

      await repo.registrarDiaCompletado(id);
      await repo.registrarDiaCompletado(id);

      final racha = (await repo.obtenerPorId(id))!.racha;
      expect(racha.diasCompletados, hasLength(1));
      expect(racha.diasConsecutivos, 1);
      expect(racha.mejorRacha, 1);
    });

    test('acumula errores frecuentes por tipo y detalle', () async {
      final repo = ProfileRepository(isar);
      final id = await repo.crearPerfil(
        nombre: 'Ana',
        avatarIndex: 0,
        modo: ProfileMode.infantil,
      );

      await repo.registrarError(perfilId: id, tipo: 'confusion', detalle: 'b-d');
      await repo.registrarError(perfilId: id, tipo: 'confusion', detalle: 'b-d');
      await repo.registrarError(perfilId: id, tipo: 'confusion', detalle: 'p-q');

      final errores = (await repo.obtenerPorId(id))!.erroresFrecuentes;
      expect(errores, hasLength(2));
      expect(errores.firstWhere((e) => e.detalle == 'b-d').frecuencia, 2);
    });

    test('eliminar un perfil borra sus resultados y diagnósticos', () async {
      final repo = ProfileRepository(isar);
      final borrar = await repo.crearPerfil(
        nombre: 'Ana',
        avatarIndex: 0,
        modo: ProfileMode.infantil,
      );
      final conservar = await repo.crearPerfil(
        nombre: 'Luis',
        avatarIndex: 1,
        modo: ProfileMode.adulto,
      );
      final fonemas = PhonemeRepository(isar);
      for (final perfilId in [borrar, conservar]) {
        await fonemas.guardarResultado(ExerciseResult()
          ..perfilId = perfilId
          ..tipo = TipoEjercicio.fonemaEmparejamiento
          ..contenidoId = 'fonema_a'
          ..correcto = true
          ..tiempoSegundos = 1
          ..fecha = DateTime.now()
          ..detalle = DetalleEjercicio());
        await isar.writeTxn(() => isar.diagnosticResults.put(DiagnosticResult()
          ..perfilId = perfilId
          ..fecha = DateTime.now()
          ..nivelDetectado = UserLevel.silabico
          ..respuestas = []
          ..tiempoTotalSegundos = 10));
      }

      await repo.eliminarPerfil(borrar);

      expect(await repo.obtenerPorId(borrar), isNull);
      expect(await fonemas.obtenerResultadosPorPerfil(borrar), isEmpty);
      expect(await fonemas.obtenerResultadosPorPerfil(conservar), hasLength(1));
      expect(await isar.diagnosticResults.count(), 1);
    });
  });

  group('PhonemeRepository', () {
    test('precarga el catálogo de 31 fonemas una sola vez', () async {
      final repo = PhonemeRepository(isar);

      await repo.precargarFonemas();
      await repo.precargarFonemas();

      final fonemas = await repo.obtenerTodos();
      expect(fonemas, hasLength(31));
      expect(fonemas.first.grafema, 'a');
    });

    test('el catálogo describe bien los casos especiales', () async {
      final repo = PhonemeRepository(isar);
      await repo.precargarFonemas();

      final r = await repo.obtenerPorGrafema('r');
      final h = await repo.obtenerPorGrafema('h');
      final gu = await repo.obtenerPorGrafema('gu');
      expect(r!.palabraEjemplo, 'pera');
      expect(h!.descripcionFonetica, contains('muda'));
      expect(gu!.palabraEjemplo, 'guitarra');
    });

    test('guarda un resultado con detalle parcial', () async {
      final repo = PhonemeRepository(isar);
      final resultado = ExerciseResult()
        ..perfilId = 1
        ..tipo = TipoEjercicio.fonemaEmparejamiento
        ..contenidoId = 'fonema_m'
        ..correcto = true
        ..tiempoSegundos = 3
        ..fecha = DateTime.now()
        ..detalle = (DetalleEjercicio()
          ..fonemaObjetivo = 'm'
          ..opcionElegida = 'm');

      await repo.guardarResultado(resultado);

      final guardados = await repo.obtenerResultadosPorPerfil(1);
      expect(guardados.single.detalle.desviacionPixeles, isNull);
    });
  });
}
