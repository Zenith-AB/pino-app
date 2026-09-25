import 'package:isar/isar.dart';

part 'phoneme.g.dart';

/// Tipos de fonema en español.
enum TipoFonema { vocal, consonante, silaba, digrafo }

/// Modelo de un fonema o sílaba con su información pedagógica.
/// Precargado en la base de datos local al instalar la app.
@collection
class Phoneme {
  Id id = Isar.autoIncrement;

  /// Representación escrita del fonema (ej. "m", "rr", "ch", "ma", "me").
  @Index(unique: true)
  late String grafema;

  /// Tipo de fonema.
  @enumerated
  late TipoFonema tipo;

  /// Ruta al archivo de audio del fonema puro en assets locales.
  late String rutaAudio;

  /// Descripción fonética para el motor de voz (ej. "sonido /m/").
  late String descripcionFonetica;

  /// Palabra ejemplo asociada al fonema (ej. "mamá" para "m").
  late String palabraEjemplo;

  /// Ruta a la imagen ejemplo (opcional).
  late String? rutaImagenEjemplo;

  /// Orden de presentación en el currículo.
  @Index()
  late int ordenCurriculo;

  /// Si este fonema está desbloqueado por defecto o requiere progreso.
  late bool desbloqueadoPorDefecto;

  /// Fonemas que suelen confundirse con este (ej. "b" ↔ "d").
  late List<String> confusionesComunes;

  /// Variantes regionales del ejemplo.
  /// Mapa flexible: {"MX": "fresa", "CL": "frutilla", "AR": "frutilla"}
  late List<VarianteRegional> variantes;
}

/// Variante regional de un fonema — vocabulario adaptado por país (HU-22).
@embedded
class VarianteRegional {
  /// Código de país (ej. "MX", "CL", "AR", "CO").
  late String codigoPais;

  /// Palabra ejemplo en la variante regional.
  late String palabraEjemplo;

  /// Ruta de audio específica para esta variante (opcional).
  late String? rutaAudioVariante;

  VarianteRegional() {
    codigoPais = '';
    palabraEjemplo = '';
  }
}
