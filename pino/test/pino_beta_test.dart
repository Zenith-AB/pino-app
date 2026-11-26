import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:pino/core/services/grabador_voz.dart';
import 'package:pino/core/services/ml_api_client.dart';
import 'package:pino/core/services/tts_service.dart';
import 'package:pino/features/pronunciation/data/vocabulario_beta.dart';
import 'package:pino/features/pronunciation/presentation/providers/practica_provider.dart';
import 'package:pino/features/pronunciation/presentation/screens/pino_beta_screen.dart';

class GrabadorFalso implements GrabadorVoz {
  GrabadorFalso({this.permiso = true});

  final bool permiso;
  bool grabando = false;
  File? ultimo;

  @override
  Future<bool> iniciar() async => grabando = permiso;

  @override
  Future<File?> detener() async {
    grabando = false;
    final carpeta = Directory.systemTemp.createTempSync('pino_test');
    return ultimo = File('${carpeta.path}/voz.wav')..writeAsBytesSync([0, 1, 2]);
  }

  @override
  Future<void> cerrar() async {}
}

class VozFalsa implements TtsService {
  final dicho = <(String, String, bool)>[];

  @override
  Future<bool> hablar(String texto, {String idioma = 'es', bool lento = false}) async {
    dicho.add((texto, idioma, lento));
    return true;
  }

  @override
  Future<void> detener() async {}
}

MLApiClient apiQueResponde(Map<String, dynamic> cuerpo, {int estado = 200, List<Uri>? urls}) {
  return MLApiClient(
    baseUrl: 'http://pino.test',
    client: MockClient((peticion) async {
      urls?.add(peticion.url);
      return http.Response.bytes(utf8.encode(json.encode(cuerpo)), estado);
    }),
  );
}

ResultadoPronunciacionML resultado({
  String oido = 'casa',
  bool correcto = false,
  double similitud = 0,
}) => ResultadoPronunciacionML(
  textoEsperado: 'casa',
  textoDetectado: oido,
  puntajeGlobal: correcto ? 1 : 0,
  silabasIncorrectas: const [],
  silabasCorrectas: const [],
  correcto: correcto,
  similitudFonetica: similitud,
);

const vocabulario = {
  'es': [
    PalabraBeta(palabra: 'casa', nivel: 1, silabas: ['ca', 'sa']),
    PalabraBeta(palabra: 'mano', nivel: 1, silabas: ['ma', 'no']),
    PalabraBeta(palabra: 'dinero', nivel: 2, silabas: ['di', 'ne', 'ro']),
  ],
  'en': [PalabraBeta(palabra: 'house', nivel: 1)],
};

void main() {
  test('el veredicto distingue bien, casi, otra y sin voz', () {
    expect(veredictoDe(resultado(correcto: true, similitud: 1)), Veredicto.bien);
    expect(veredictoDe(resultado(oido: 'cata', similitud: 0.75)), Veredicto.casi);
    expect(veredictoDe(resultado(oido: 'elefante', similitud: 0.1)), Veredicto.otra);
    expect(veredictoDe(resultado(oido: '')), Veredicto.sinVoz);
  });

  test('el vocabulario incluido tiene los cuatro niveles en ambos idiomas', () {
    final datos = leerVocabularioBeta(File('assets/data/vocabulario_beta.json').readAsStringSync());
    for (final idioma in ['es', 'en']) {
      for (var nivel = 1; nivel <= 4; nivel++) {
        expect(datos[idioma]!.where((p) => p.nivel == nivel), isNotEmpty, reason: '$idioma $nivel');
      }
    }
    expect(datos['es']!.every((p) => p.silabas.isNotEmpty), isTrue);
    expect(datos['en']!.map((p) => p.palabra), isNot(contains('pussy')));
  });

  test('envía el audio con el idioma y lo borra al terminar', () async {
    final grabador = GrabadorFalso();
    final urls = <Uri>[];
    final notifier = PracticaNotifier(
      grabador,
      apiQueResponde({'texto_detectado': 'house', 'correcto': true}, urls: urls),
    );

    await notifier.alternarGrabacion(palabra: 'house', idioma: 'en');
    expect(notifier.state.fase, FasePractica.grabando);
    await notifier.alternarGrabacion(palabra: 'house', idioma: 'en');

    expect(urls.single.queryParameters, {'texto_esperado': 'house', 'idioma': 'en'});
    expect(notifier.state.resultado!.correcto, isTrue);
    expect(grabador.ultimo!.existsSync(), isFalse);
  });

  test('si la API falla muestra un error y borra el audio', () async {
    final grabador = GrabadorFalso();
    final notifier = PracticaNotifier(grabador, apiQueResponde({}, estado: 503));

    await notifier.alternarGrabacion(palabra: 'casa', idioma: 'es');
    await notifier.alternarGrabacion(palabra: 'casa', idioma: 'es');

    expect(notifier.state.error, isNotNull);
    expect(notifier.state.fase, FasePractica.lista);
    expect(grabador.ultimo!.existsSync(), isFalse);
  });

  test('sin permiso de micrófono no graba', () async {
    final notifier = PracticaNotifier(GrabadorFalso(permiso: false), apiQueResponde({}));
    await notifier.alternarGrabacion(palabra: 'casa', idioma: 'es');
    expect(notifier.state.fase, FasePractica.lista);
    expect(notifier.state.error, contains('micrófono'));
  });

  test('cambiar de palabra mientras arranca el micrófono descarta la grabación', () async {
    final grabador = GrabadorFalso();
    final notifier = PracticaNotifier(grabador, apiQueResponde({}));

    final inicio = notifier.alternarGrabacion(palabra: 'casa', idioma: 'es');
    await notifier.reiniciar();
    await inicio;

    expect(grabador.grabando, isFalse);
    expect(notifier.state.fase, FasePractica.lista);
  });

  testWidgets('la pantalla permite escuchar, cambiar de palabra y de idioma', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);
    final voz = VozFalsa();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          ttsServiceProvider.overrideWithValue(voz),
          grabadorVozProvider.overrideWithValue(GrabadorFalso()),
          vocabularioBetaProvider.overrideWith((ref) async => vocabulario),
        ],
        child: const MaterialApp(home: PinoBetaScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('casa'), findsOneWidget);
    expect(find.text('ca · sa'), findsOneWidget);
    await tester.tap(find.text('Sílabas'));
    expect(voz.dicho.last, ('ca, sa', 'es', true));

    await tester.tap(find.byTooltip('Palabra siguiente'));
    await tester.pump();
    expect(find.text('mano'), findsOneWidget);

    await tester.tap(find.text('Inglés'));
    await tester.pumpAndSettle();
    expect(find.text('house'), findsOneWidget);
    expect(find.text('Sílabas'), findsNothing);
    await tester.tap(find.text('Escuchar'));
    expect(voz.dicho.last, ('house', 'en', false));

    await tester.tap(find.byTooltip('Grabar mi voz'));
    await tester.pump();
    expect(find.byTooltip('Terminar grabación'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
