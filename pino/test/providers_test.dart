import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';

import 'package:pino/core/database/database_service.dart';
import 'package:pino/features/diagnostic/data/models/diagnostic_result.dart';
import 'package:pino/features/diagnostic/presentation/providers/diagnostic_provider.dart';
import 'package:pino/features/phoneme/presentation/providers/phoneme_provider.dart';
import 'package:pino/features/profile/data/models/user_profile.dart';
import 'package:pino/features/profile/presentation/providers/profile_provider.dart';

import 'helpers/isar_test_helper.dart';

void main() {
  late Isar isar;
  late ProviderContainer container;

  setUp(() async {
    isar = await abrirIsarDePrueba();
    container = ProviderContainer(overrides: [
      databaseServiceProvider.overrideWithValue(DatabaseService.desde(isar)),
    ]);
  });

  tearDown(() async {
    container.dispose();
    await cerrarIsarDePrueba(isar);
  });

  /// Crea un perfil y lo deja como activo.
  Future<UserProfile> crearPerfilActivo() async {
    final notifier = container.read(profileProvider.notifier);
    await notifier.crearPerfil(
      nombre: 'Ana',
      avatarIndex: 0,
      modo: ProfileMode.infantil,
    );
    final perfil = container.read(profileProvider).perfiles.single;
    notifier.seleccionarPerfil(perfil);
    return perfil;
  }

  group('ProfileNotifier', () {
    test('eliminar el perfil activo lo quita de la selección', () async {
      final perfil = await crearPerfilActivo();
      expect(container.read(perfilActivoProvider), isNotNull);

      await container.read(profileProvider.notifier).eliminarPerfil(perfil.id);

      expect(container.read(perfilActivoProvider), isNull);
      expect(container.read(profileProvider).perfiles, isEmpty);
    });
  });

  group('PhonemeNotifier', () {
    test('responder actualiza el progreso del perfil activo', () async {
      await crearPerfilActivo();
      final notifier = container.read(phonemeProvider.notifier);
      await notifier.cargarFonemas();
      await notifier.generarEjercicioEmparejamiento();
      final objetivo = container.read(phonemeProvider).fonemaActual!;

      await notifier.verificarRespuesta(objetivo);

      final progreso = container.read(perfilActivoProvider)!.progreso.fonemas;
      expect(progreso.single.fonemaId, objetivo.grafema);
      expect(progreso.single.aciertos, 1);
      expect(container.read(phonemeProvider).feedback, isNotNull);
    });

    test('un ejercicio nuevo limpia el feedback anterior', () async {
      await crearPerfilActivo();
      final notifier = container.read(phonemeProvider.notifier);
      await notifier.cargarFonemas();
      await notifier.generarEjercicioEmparejamiento();
      await notifier.verificarRespuesta(
        container.read(phonemeProvider).fonemaActual!,
      );

      await notifier.generarEjercicioEmparejamiento();

      expect(container.read(phonemeProvider).feedback, isNull);
    });
  });

  group('Diagnóstico', () {
    RespuestaDiagnostico respuesta(bool correcta) =>
        RespuestaDiagnostico()..correcta = correcta;

    test('el nivel cuenta solo los aciertos en orden', () {
      expect(calcularNivel([respuesta(false), respuesta(true), respuesta(true)]),
          UserLevel.preLector);
      expect(calcularNivel([respuesta(true), respuesta(false), respuesta(true)]),
          UserLevel.silabico);
      expect(calcularNivel([respuesta(true), respuesta(true), respuesta(false)]),
          UserLevel.palabras);
      expect(calcularNivel([respuesta(true), respuesta(true), respuesta(true)]),
          UserLevel.textos);
    });

    test('guardar el resultado actualiza el nivel del perfil', () async {
      await crearPerfilActivo();
      final notifier = container.read(diagnosticProvider.notifier);
      notifier.iniciar();
      for (final pregunta in preguntasDiagnostico) {
        notifier.responder(pregunta.respuestaCorrecta);
      }

      await notifier.guardarResultado();

      expect(container.read(perfilActivoProvider)!.nivel, UserLevel.textos);
      final guardado = await isar.diagnosticResults.where().findFirst();
      expect(guardado!.nivelDetectado, UserLevel.textos);
      expect(guardado.respuestas, hasLength(3));
    });
  });
}
