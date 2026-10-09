import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:pino/core/services/ml_api_client.dart';

void main() {
  test('codifica el texto esperado en la URL', () async {
    late Uri pedida;
    final cliente = MLApiClient(
      baseUrl: 'http://api',
      client: MockClient.streaming((request, _) async {
        pedida = request.url;
        return http.StreamedResponse(
          Stream.value(utf8.encode(json.encode({'correcto': true}))),
          200,
        );
      }),
    );
    final audio = File('${Directory.systemTemp.path}/pino_audio_test.wav')
      ..writeAsBytesSync([0, 1, 2]);
    addTearDown(audio.deleteSync);

    await cliente.evaluarPronunciacion(
      archivoAudio: audio,
      textoEsperado: 'el niño & mamá',
    );

    expect(pedida.path, '/predict/pronunciacion');
    expect(pedida.queryParameters['texto_esperado'], 'el niño & mamá');
  });

  test('decodifica la respuesta como UTF-8 aunque no indique charset', () async {
    final cliente = MLApiClient(
      baseUrl: 'http://api',
      client: MockClient((_) async => http.Response.bytes(
            utf8.encode(json.encode({
              'nivel_dificultad': 2,
              'sugerencias': ['Simplificar palabras: árbol, camión'],
            })),
            200,
            headers: {'content-type': 'application/json'},
          )),
    );

    final r = await cliente.analizarDificultad(texto: 'El camión');

    expect(r.sugerencias.single, 'Simplificar palabras: árbol, camión');
  });

  test('un error de la API lanza MLApiException con el código', () async {
    final cliente = MLApiClient(
      baseUrl: 'http://api',
      client: MockClient((_) async => http.Response('{"detail":"no"}', 503)),
    );

    expect(
      () => cliente.analizarTrazo(
        puntos: const [],
        letra: 'A',
        anchoCanvas: 100,
        altoCanvas: 100,
      ),
      throwsA(isA<MLApiException>()
          .having((e) => e.mensaje, 'mensaje', contains('503'))),
    );
  });
}
