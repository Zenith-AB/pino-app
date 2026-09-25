import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

/// Cliente que conecta la app Flutter con la API de ML (FastAPI).
/// Envía audio, trazos y datos del usuario para obtener predicciones.
class MLApiClient {
  final String baseUrl;
  final http.Client _client;

  MLApiClient({
    required this.baseUrl,
    http.Client? client,
  }) : _client = client ?? http.Client();

  // ─── 1. Pronunciación (HU-06) ───

  /// Envía audio grabado para evaluar pronunciación vs texto esperado.
  Future<ResultadoPronunciacionML> evaluarPronunciacion({
    required File archivoAudio,
    required String textoEsperado,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/predict/pronunciacion?texto_esperado=$textoEsperado'),
    );

    request.files.add(
      await http.MultipartFile.fromPath('audio', archivoAudio.path),
    );

    final response = await request.send();
    final body = await response.stream.bytesToString();

    if (response.statusCode != 200) {
      throw MLApiException('Error evaluando pronunciación: $body');
    }

    return ResultadoPronunciacionML.fromJson(json.decode(body));
  }

  /// Evalúa un fonema aislado (HU-03).
  Future<ResultadoFonemaML> evaluarFonema({
    required File archivoAudio,
    required String fonemaEsperado,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/predict/fonema?fonema_esperado=$fonemaEsperado'),
    );

    request.files.add(
      await http.MultipartFile.fromPath('audio', archivoAudio.path),
    );

    final response = await request.send();
    final body = await response.stream.bytesToString();

    if (response.statusCode != 200) {
      throw MLApiException('Error evaluando fonema: $body');
    }

    return ResultadoFonemaML.fromJson(json.decode(body));
  }

  // ─── 2. Siguiente lección (HU-05) ───

  /// Obtiene recomendación de la próxima lección óptima.
  Future<RecomendacionLeccionML> obtenerSiguienteLeccion({
    required List<Map<String, dynamic>> itemsAprendizaje,
    int cantidad = 5,
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/predict/siguiente-leccion'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'items': itemsAprendizaje,
        'cantidad': cantidad,
      }),
    );

    if (response.statusCode != 200) {
      throw MLApiException('Error obteniendo lección: ${response.body}');
    }

    return RecomendacionLeccionML.fromJson(json.decode(response.body));
  }

  // ─── 3. Dificultad de texto (HU-04, HU-17) ───

  /// Analiza la dificultad de un texto en español.
  Future<DificultadTextoML> analizarDificultad({
    required String texto,
    int? nivelObjetivo,
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/predict/dificultad-texto'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'texto': texto,
        'nivel_objetivo': nivelObjetivo,
      }),
    );

    if (response.statusCode != 200) {
      throw MLApiException('Error analizando dificultad: ${response.body}');
    }

    return DificultadTextoML.fromJson(json.decode(response.body));
  }

  // ─── 4. Análisis de trazo (HU-02, HU-13) ───

  /// Envía puntos de trazo para análisis de calidad.
  Future<ResultadoTrazoML> analizarTrazo({
    required List<Map<String, double>> puntos,
    required String letra,
    required double anchoCanvas,
    required double altoCanvas,
    String tolerancia = 'media',
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/analyze/trazo'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'puntos': puntos,
        'letra': letra,
        'ancho_canvas': anchoCanvas,
        'alto_canvas': altoCanvas,
        'tolerancia': tolerancia,
      }),
    );

    if (response.statusCode != 200) {
      throw MLApiException('Error analizando trazo: ${response.body}');
    }

    return ResultadoTrazoML.fromJson(json.decode(response.body));
  }

  // ─── Health check ───

  /// Verifica que la API de ML está disponible.
  Future<bool> estaDisponible() async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/health'))
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

  ResultadoPronunciacionML({
    required this.textoEsperado,
    required this.textoDetectado,
    required this.puntajeGlobal,
    required this.silabasIncorrectas,
    required this.silabasCorrectas,
    required this.correcto,
  });

  factory ResultadoPronunciacionML.fromJson(Map<String, dynamic> json) {
    return ResultadoPronunciacionML(
      textoEsperado: json['texto_esperado'] ?? '',
      textoDetectado: json['texto_detectado'] ?? '',
      puntajeGlobal: (json['puntaje_global'] ?? 0).toDouble(),
      silabasIncorrectas: List<String>.from(json['silabas_incorrectas'] ?? []),
      silabasCorrectas: List<String>.from(json['silabas_correctas'] ?? []),
      correcto: json['correcto'] ?? false,
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
