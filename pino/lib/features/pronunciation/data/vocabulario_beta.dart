import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class PalabraBeta {
  const PalabraBeta({required this.palabra, required this.nivel, this.silabas = const []});

  final String palabra;
  final int nivel;

  /// Solo en español.
  final List<String> silabas;

  factory PalabraBeta.fromJson(Map<String, dynamic> json) => PalabraBeta(
    palabra: json['palabra'] as String,
    nivel: json['nivel'] as int,
    silabas: List<String>.from(json['silabas'] as List),
  );
}

typedef VocabularioBeta = Map<String, List<PalabraBeta>>;

VocabularioBeta leerVocabularioBeta(String contenido) =>
    (json.decode(contenido) as Map<String, dynamic>).map(
      (idioma, lista) => MapEntry(idioma, [
        for (final item in lista as List) PalabraBeta.fromJson(item as Map<String, dynamic>),
      ]),
    );

/// Vocabulario nivelado, incluido en la app para funcionar sin conexión.
final vocabularioBetaProvider = FutureProvider<VocabularioBeta>((ref) async {
  return leerVocabularioBeta(await rootBundle.loadString('assets/data/vocabulario_beta.json'));
});
