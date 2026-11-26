import '../../data/models/user_profile.dart';

String nombreNivel(UserLevel nivel) => switch (nivel) {
  UserLevel.preLector => 'Pre-lector',
  UserLevel.silabico => 'Silábico',
  UserLevel.palabras => 'Palabras',
  UserLevel.textos => 'Textos',
};

/// Nivel de vocabulario (1 a 4) con el que empieza la práctica de palabras.
int nivelDeVocabulario(UserLevel nivel) => nivel.index + 1;
