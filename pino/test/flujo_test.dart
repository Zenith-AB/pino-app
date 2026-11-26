import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:isar/isar.dart';
import 'package:pino/core/database/database_service.dart';
import 'package:pino/core/router/app_router.dart';
import 'package:pino/core/services/grabador_voz.dart';
import 'package:pino/core/services/ml_api_client.dart';
import 'package:pino/core/services/tts_service.dart';
import 'package:pino/features/home/presentation/widgets/streak_counter.dart';
import 'package:pino/features/phoneme/data/models/exercise_result.dart';
import 'package:pino/features/phoneme/presentation/providers/phoneme_provider.dart';
import 'package:pino/features/profile/data/models/user_profile.dart';
import 'package:pino/features/profile/presentation/providers/profile_provider.dart';
import 'package:pino/features/pronunciation/data/vocabulario_beta.dart';
import 'package:pino/features/pronunciation/presentation/providers/practica_provider.dart';
import 'package:pino/features/pronunciation/presentation/widgets/analizar_palabra.dart';

import 'helpers/isar_test_helper.dart';
import 'pino_beta_test.dart' show GrabadorFalso, VozFalsa;

MLApiClient apiFalsa() => MLApiClient(
  baseUrl: 'http://pino.test',
  client: MockClient((peticion) async {
    final cuerpo = peticion.url.path == '/predict/aoa-palabra'
        ? {
            'palabra': 'palta',
            'edad_anios': 8.18,
            'nivel': 4,
            'origen': 'modelo',
            'silabas': ['pal', 'ta'],
          }
        : {'texto_detectado': 'casa', 'correcto': true, 'puntaje_global': 1};
    return http.Response.bytes(utf8.encode(json.encode(cuerpo)), 200);
  }),
);

void main() {
  late Isar isar;
  late ProviderContainer contenedor;
  late VozFalsa voz;

  setUp(() async {
    isar = await abrirIsarDePrueba();
    voz = VozFalsa();
    final vocabulario = leerVocabularioBeta(
      File('assets/data/vocabulario_beta.json').readAsStringSync(),
    );
    contenedor = ProviderContainer(
      overrides: [
        databaseServiceProvider.overrideWithValue(DatabaseService.desde(isar)),
        ttsServiceProvider.overrideWithValue(voz),
        grabadorVozProvider.overrideWithValue(GrabadorFalso()),
        mlApiClientProvider.overrideWithValue(apiFalsa()),
        vocabularioBetaProvider.overrideWith((ref) async => vocabulario),
      ],
    );
  });

  tearDown(() async {
    contenedor.dispose();
    await cerrarIsarDePrueba(isar);
  });

  testWidgets('crear perfil, diagnóstico, inicio y lecciones', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);

    // La base de datos responde fuera del reloj simulado de las pruebas.
    Future<void> esperar() async {
      for (var i = 0; i < 20; i++) {
        await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 40)));
        await tester.pump(const Duration(milliseconds: 100));
      }
    }

    Future<void> tocar(Finder objetivo) async {
      await tester.ensureVisible(objetivo);
      await tester.pump();
      await tester.tap(objetivo);
      await esperar();
    }

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: contenedor,
        child: MaterialApp.router(routerConfig: contenedor.read(appRouterProvider)),
      ),
    );
    await esperar();
    expect(find.textContaining('crear tu primer perfil'), findsOneWidget);

    // Crear perfil
    await tocar(find.byTooltip('Crear perfil'));
    await tester.enterText(find.byType(TextField), 'Ana');
    await tester.pump();
    await tocar(find.text('Continuar'));

    // Diagnóstico: dos aciertos y un error
    expect(find.text('Evaluación inicial'), findsOneWidget);
    await tocar(find.text('A'));
    await tocar(find.text('mamá'));
    await tocar(find.text('En la mesa'));
    expect(find.text('Tu punto de partida: Palabras'), findsOneWidget);
    await tocar(find.text('Empezar'));

    // Inicio
    expect(find.textContaining('¡Hola, Ana!'), findsOneWidget);
    expect(find.text('Nivel: Palabras'), findsOneWidget);
    expect(find.text('0 días seguidos'), findsOneWidget);

    // Práctica de palabras: empieza en el nivel del perfil y guarda el intento
    await tocar(find.text('Practicar palabras'));
    expect(
      tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Lectura inicial')).selected,
      isTrue,
    );
    await tocar(find.byTooltip('Grabar mi voz'));
    await tocar(find.byTooltip('Terminar grabación'));
    expect(find.text('¡Muy bien!'), findsOneWidget);
    final intentos = await tester.runAsync(() => isar.exerciseResults.where().findAll());
    expect(intentos!.single.tipo, TipoEjercicio.lecturaVozAlta);
    expect(contenedor.read(perfilActivoProvider)!.racha.diasConsecutivos, 1);
    await tocar(find.byType(BackButton));
    expect(find.text('1 día seguido'), findsOneWidget);

    // Explorar letras
    await tocar(find.text('Explorar letras'));
    await tocar(find.text('agua'));
    expect(voz.dicho.last.$1, 'agua');
    await tocar(find.byType(BackButton));

    // Juego de relacionar
    await tocar(find.text('Juego de relacionar'));
    final objetivo = contenedor.read(phonemeProvider).fonemaActual!;
    await tocar(find.widgetWithText(ElevatedButton, objetivo.grafema));
    expect(find.text('Siguiente'), findsOneWidget);
    await tocar(find.text('Siguiente'));
    await tocar(find.byType(BackButton));

    // Cambiar de perfil: Ana sigue guardada
    await tocar(find.byTooltip('Cambiar de perfil'));
    expect(find.text('Ana'), findsOneWidget);
    await tocar(find.text('Ana'));
    expect(find.textContaining('¡Hola, Ana!'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('el juego solo plantea preguntas sin ambigüedad', () async {
    final notifier = contenedor.read(phonemeProvider.notifier);
    await notifier.cargarFonemas();
    for (var i = 0; i < 150; i++) {
      await notifier.generarEjercicioEmparejamiento();
      final estado = contenedor.read(phonemeProvider);
      final objetivo = estado.fonemaActual!;
      final otras = estado.opcionesEmparejamiento.where((o) => o.grafema != objetivo.grafema);
      expect(otras, hasLength(2));
      expect(objetivo.palabraEjemplo, startsWith(objetivo.grafema));
      for (final o in otras) {
        expect(
          objetivo.palabraEjemplo.startsWith(o.grafema),
          isFalse,
          reason: '${objetivo.palabraEjemplo} también empieza con ${o.grafema}',
        );
      }
      if (objetivo.grafema == 'v') expect(otras.map((o) => o.grafema), isNot(contains('b')));
    }
  });

  test('sin perfil, practicar no guarda nada', () async {
    final notifier = contenedor.listen(practicaProvider.notifier, (_, __) {}).read();
    await notifier.alternarGrabacion(palabra: 'casa', idioma: 'es');
    await notifier.alternarGrabacion(palabra: 'casa', idioma: 'es');
    expect(await isar.exerciseResults.count(), 0);
  });

  test('la racha solo cuenta si se practicó hoy o ayer', () {
    final racha = RachaUsuario()
      ..diasConsecutivos = 4
      ..diasCompletados = ['2026-11-20'];
    expect(rachaVigente(racha, DateTime(2026, 11, 20, 23)), 4);
    expect(rachaVigente(racha, DateTime(2026, 11, 21, 1)), 4);
    expect(rachaVigente(racha, DateTime(2026, 11, 22)), 0);
  });

  testWidgets('consultar una palabra muestra su edad y permite practicarla', (tester) async {
    PalabraBeta? elegida;
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: contenedor,
        child: MaterialApp(
          home: Scaffold(
            body: AnalizarPalabra(idioma: 'es', onPracticar: (p) => elegida = p),
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'dos palabras');
    await tester.tap(find.byTooltip('Consultar'));
    await tester.pump();
    expect(find.textContaining('una sola palabra'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'Palta');
    await tester.tap(find.byTooltip('Consultar'));
    await tester.pumpAndSettle();
    expect(find.textContaining('8,2 años · Nivel 4'), findsOneWidget);
    expect(find.textContaining('Estimación del modelo'), findsOneWidget);
    await tester.tap(find.text('Practicar esta palabra'));
    expect(elegida!.silabas, ['pal', 'ta']);
  });
}
