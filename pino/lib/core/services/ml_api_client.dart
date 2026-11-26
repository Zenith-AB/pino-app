import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

/// Cliente que conecta la app Flutter con la API de ML (FastAPI).
/// Envía audio, trazos y datos del usuario para obtener predicciones.
class MLApiClient {
  /// Tiempo máximo para endpoints rápidos (trazo, lección, dificultad).
  static const timeoutJson = Duration(seconds: 15);

  /// Tiempo máximo para endpoints de audio (Whisper puede tardar).
  static const timeoutAudio = Duration(seconds: 60);

  final String baseUrl;
  final http.Client _client;

  MLApiClient({
    required this.baseUrl,
    http.Client? client,
  }) : _client = client ?? http.Client();

  /// Construye la URL codificando los parámetros (tildes, espacios, "&"...).
  Uri _uri(String ruta, [Map<String, String>? query]) {
    return Uri.parse('$baseUrl$ruta').replace(queryParameters: query);
  }

  /// La API responde JSON en UTF-8 sin indicar charset; `response.body`
  /// lo decodificaría como latin1 y rompería las tildes.
  static dynamic _decodificar(List<int> bytes) => json.decode(utf8.decode(bytes));

  Future<dynamic> _postJson(
    String ruta,
    Map<String, dynamic> cuerpo,
    String error,
  ) async {
    final response = await _client
        .post(
          _uri(ruta),
          headers: {'Content-Type': 'application/json'},
          body: json.encode(cuerpo),
        )
        .timeout(timeoutJson);

    if (response.statusCode != 200) {
      throw MLApiException('$error (${response.statusCode}): ${utf8.decode(response.bodyBytes)}');
    }
    return _decodificar(response.bodyBytes);
  }

  Future<dynamic> _postAudio(
    String ruta,
    Map<String, String> query,
    File archivoAudio,
    String error,
  ) async {
    final request = http.MultipartRequest('POST', _uri(ruta, query))
      ..files.add(await http.MultipartFile.fromPath('audio', archivoAudio.path));

    final response = await http.Response.fromStream(
      await _client.send(request).timeout(timeoutAudio),
    );

    if (response.statusCode != 200) {
      throw MLApiException('$error (${response.statusCode}): ${utf8.decode(response.bodyBytes)}');
    }
    return _decodificar(response.bodyBytes);
  }

  // ─── 1. Pronunciación (HU-06) ───

  /// Envía audio grabado para evaluar pronunciación vs texto esperado.
  Future<ResultadoPronunciacionML> evaluarPronunciacion({
    required File archivoAudio,
    required String textoEsperado,
    String idioma = 'es',
  }) async {
    final json = await _postAudio(
      '/predict/pronunciacion',
      {'texto_esperado': textoEsperado, 'idioma': idioma},
      archivoAudio,
      'Error evaluando pronunciación',
    );
    return ResultadoPronunciacionML.fromJson(json);
  }

  /// Evalúa un fonema aislado (HU-03).
  Future<ResultadoFonemaML> evaluarFonema({
    required File archivoAudio,
    required String fonemaEsperado,
  }) async {
    final json = await _postAudio(
      '/predict/fonema',
      {'fonema_esperado': fonemaEsperado},
      archivoAudio,
      'Error evaluando fonema',
    );
    return ResultadoFonemaML.fromJson(json);
  }

  // ─── Edad de adquisición de palabras ───

  /// Edad a la que se suele aprender una palabra y su nivel en Pino.
  Future<EdadPalabraML> analizarPalabra({required String palabra, String idioma = 'es'}) async {
    final response = await _client
        .get(_uri('/predict/aoa-palabra', {'palabra': palabra, 'idioma': idioma}))
        .timeout(timeoutJson);
    if (response.statusCode != 200) {
      throw MLApiException('Error analizando la palabra (${response.statusCode})');
    }
    return EdadPalabraML.fromJson(_decodificar(response.bodyBytes));
  }

  // ─── 2. Siguiente lección (HU-05) ───

  /// Obtiene recomendación de la próxima lección óptima.
  /// Cada ítem: item_id, tipo, aciertos, fallos, racha_actual,
  /// factor_facilidad, intervalo_dias, ultima_practica (ISO 8601),
  /// proxima_revision (ISO 8601), errores_tipo.
  Future<RecomendacionLeccionML> obtenerSiguienteLeccion({
    required List<Map<String, dynamic>> itemsAprendizaje,
    int cantidad = 5,
  }) async {
    final json = await _postJson(
      '/predict/siguiente-leccion',
      {'items': itemsAprendizaje, 'cantidad': cantidad},
      'Error obteniendo lección',
    );
    return RecomendacionLeccionML.fromJson(json);
  }

  // ─── 3. Dificultad de texto (HU-04, HU-17) ───

  /// Analiza la dificultad de un texto en español.
  Future<DificultadTextoML> analizarDificultad({
    required String texto,
    int? nivelObjetivo,
  }) async {
    final json = await _postJson(
      '/predict/dificultad-texto',
      {'texto': texto, 'nivel_objetivo': nivelObjetivo},
      'Error analizando dificultad',
    );
    return DificultadTextoML.fromJson(json);
  }

  // ─── 4. Análisis de trazo (HU-02, HU-13) ───

  /// Envía puntos de trazo para análisis de calidad.
  /// Coordenadas en píxeles del canvas, con y hacia abajo (como en Flutter).
  Future<ResultadoTrazoML> analizarTrazo({
    required List<Map<String, double>> puntos,
    required String letra,
    required double anchoCanvas,
    required double altoCanvas,
    String tolerancia = 'media',
  }) async {
    final json = await _postJson(
      '/analyze/trazo',
      {
        'puntos': puntos,
        'letra': letra,
        'ancho_canvas': anchoCanvas,
        'alto_canvas': altoCanvas,
        'tolerancia': tolerancia,
      },
      'Error analizando trazo',
    );
    return ResultadoTrazoML.fromJson(json);
  }

  // ─── Health check ───

  /// Verifica que la API de ML está disponible.
  Future<bool> estaDisponible() async {
    try {
      final response = await _client
          .get(_uri('/health'))
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  void dispose() => _client.close();
}

// ─── Modelos de respuesta ───

class ResultadoPronunciacionML {
  final String textoEsperado;
  final String textoDetectado;
  final double puntajeGlobal;
  final List<String> silabasIncorrectas;
  final List<String> silabasCorrectas;
  final bool correcto;
  final double similitudFonetica;

  ResultadoPronunciacionML({
    required this.textoEsperado,
    required this.textoDetectado,
    required this.puntajeGlobal,
    required this.silabasIncorrectas,
    required this.silabasCorrectas,
    required this.correcto,
    this.similitudFonetica = 0,
  });

  factory ResultadoPronunciacionML.fromJson(Map<String, dynamic> json) {
    return ResultadoPronunciacionML(
      textoEsperado: json['texto_esperado'] ?? '',
      textoDetectado: json['texto_detectado'] ?? '',
      puntajeGlobal: (json['puntaje_global'] ?? 0).toDouble(),
      silabasIncorrectas: List<String>.from(json['silabas_incorrectas'] ?? []),
      silabasCorrectas: List<String>.from(json['silabas_correctas'] ?? []),
      correcto: json['correcto'] ?? false,
      similitudFonetica: (json['similitud_fonetica_global'] ?? 0).toDouble(),
    );
  }
}

class EdadPalabraML {
  final String palabra;
  final double edadAnios;

  /// 1 a 4: niveles de Pino. 5: fuera del rango infantil.
  final int nivel;

  /// `true` si la edad viene de un estudio publicado y `false` si la estimó el modelo.
  final bool tieneNorma;
  final List<String> silabas;

  EdadPalabraML({
    required this.palabra,
    required this.edadAnios,
    required this.nivel,
    required this.tieneNorma,
    required this.silabas,
  });

  factory EdadPalabraML.fromJson(Map<String, dynamic> json) {
    return EdadPalabraML(
      palabra: json['palabra'] as String,
      edadAnios: (json['edad_anios'] as num).toDouble(),
      nivel: json['nivel'] as int,
      tieneNorma: json['origen'] == 'norma',
      silabas: List<String>.from(json['silabas'] ?? []),
    );
  }
}

class ResultadoFonemaML {
  final bool correcto;
  final double confianza;
  final String fonemaEsperado;

  ResultadoFonemaML({
    required this.correcto,
    required this.confianza,
    required this.fonemaEsperado,
  });

  factory ResultadoFonemaML.fromJson(Map<String, dynamic> json) {
    return ResultadoFonemaML(
      correcto: json['correcto'] ?? false,
      confianza: (json['confianza'] ?? 0).toDouble(),
      fonemaEsperado: json['fonema_esperado'] ?? '',
    );
  }
}

class RecomendacionLeccionML {
  final List<Map<String, dynamic>> itemsRecomendados;
  final bool desbloquearNivel;

  RecomendacionLeccionML({
    required this.itemsRecomendados,
    required this.desbloquearNivel,
  });

  factory RecomendacionLeccionML.fromJson(Map<String, dynamic> json) {
    return RecomendacionLeccionML(
      itemsRecomendados: List<Map<String, dynamic>>.from(
        json['items_recomendados'] ?? [],
      ),
      desbloquearNivel: json['desbloquear_nivel'] ?? false,
    );
  }
}

class DificultadTextoML {
  final int nivelDificultad;
  final String etiqueta;
  final double puntajeLegibilidad;
  final List<String> palabrasComplejas;
  final bool requiereAdaptacion;
  final List<String> sugerencias;

  DificultadTextoML({
    required this.nivelDificultad,
    required this.etiqueta,
    required this.puntajeLegibilidad,
    required this.palabrasComplejas,
    required this.requiereAdaptacion,
    required this.sugerencias,
  });

  factory DificultadTextoML.fromJson(Map<String, dynamic> json) {
    return DificultadTextoML(
      nivelDificultad: json['nivel_dificultad'] ?? 1,
      etiqueta: json['etiqueta'] ?? '',
      puntajeLegibilidad: (json['puntaje_legibilidad'] ?? 0).toDouble(),
      palabrasComplejas: List<String>.from(json['palabras_complejas'] ?? []),
      requiereAdaptacion: json['requiere_adaptacion'] ?? false,
      sugerencias: List<String>.from(json['sugerencias'] ?? []),
    );
  }
}

class ResultadoTrazoML {
  final String letraDetectada;
  final double confianza;
  final double desviacionPromedio;
  final double porcentajeDentroMargen;
  final bool trazoCompleto;
  final String toleranciaSugerida;
  final bool correcto;

  ResultadoTrazoML({
    required this.letraDetectada,
    required this.confianza,
    required this.desviacionPromedio,
    required this.porcentajeDentroMargen,
    required this.trazoCompleto,
    required this.toleranciaSugerida,
    required this.correcto,
  });

  factory ResultadoTrazoML.fromJson(Map<String, dynamic> json) {
    return ResultadoTrazoML(
      letraDetectada: json['letra_detectada'] ?? '',
      confianza: (json['confianza'] ?? 0).toDouble(),
      desviacionPromedio: (json['desviacion_promedio'] ?? 0).toDouble(),
      porcentajeDentroMargen: (json['porcentaje_dentro_margen'] ?? 0).toDouble(),
      trazoCompleto: json['trazo_completo'] ?? false,
      toleranciaSugerida: json['tolerancia_sugerida'] ?? 'media',
      correcto: json['correcto'] ?? false,
    );
  }
}

class MLApiException implements Exception {
  final String mensaje;
  MLApiException(this.mensaje);

  @override
  String toString() => 'MLApiException: $mensaje';
}

// ─── Provider ───

final mlApiClientProvider = Provider<MLApiClient>((ref) {
  return MLApiClient(
    baseUrl: const String.fromEnvironment(
      'ML_API_URL',
      defaultValue: 'http://10.0.2.2:8000', // Android emulator → localhost
    ),
  );
});
