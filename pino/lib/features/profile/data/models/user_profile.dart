import 'package:isar/isar.dart';

part 'user_profile.g.dart';

/// Modos de interfaz disponibles.
enum ProfileMode { infantil, adulto }

/// Niveles de competencia lectora.
enum UserLevel { preLector, silabico, palabras, textos }

/// Modelo principal del perfil de usuario.
/// Se almacena como documento NoSQL en Isar — toda la información
/// del usuario está autocontenida en un solo objeto, sin JOINs.
@collection
class UserProfile {
  Id id = Isar.autoIncrement;

  late String nombre;
  late int avatarIndex;

  @enumerated
  late ProfileMode modo;

  @enumerated
  late UserLevel nivel;

  late DateTime creadoEn;

  /// Progreso completo del usuario — anidado dentro del perfil.
  late ProgresoUsuario progreso;

  /// Configuración personalizada según el modo (infantil/adulto).
  late ConfiguracionPerfil configuracion;

  /// Lista de errores frecuentes para el algoritmo adaptativo (HU-05).
  late List<ErrorFrecuente> erroresFrecuentes;

  /// Historial de racha diaria (HU-08).
  late RachaUsuario racha;
}

/// Progreso general del usuario — se lee en una sola operación.
@embedded
class ProgresoUsuario {
  /// Mapa de fonemas practicados: cada fonema tiene sus métricas.
  late List<ProgresoFonema> fonemas;

  /// Letras cuyo trazado fue completado correctamente.
  late List<String> trazosCompletados;

  /// Total de lecciones terminadas.
  late int leccionesTerminadas;

  /// Porcentaje general de aciertos (0-100).
  late double porcentajeAciertoGlobal;

  ProgresoUsuario() {
    fonemas = [];
    trazosCompletados = [];
    leccionesTerminadas = 0;
    porcentajeAciertoGlobal = 0.0;
  }
}

/// Métricas de un fonema individual dentro del progreso.
@embedded
class ProgresoFonema {
  /// Identificador del fonema (ej. "m", "rr", "ch").
  late String fonemaId;

  late int aciertos;
  late int fallos;

  /// Última vez que se practicó este fonema.
  late DateTime? ultimaPractica;

  /// Nivel de dominio: 0.0 (nulo) a 1.0 (dominado).
  late double nivelDominio;

  ProgresoFonema() {
    fonemaId = '';
    aciertos = 0;
    fallos = 0;
    nivelDominio = 0.0;
  }

  /// Tasa de acierto calculada.
  double get tasaAcierto {
    final total = aciertos + fallos;
    if (total == 0) return 0.0;
    return aciertos / total;
  }
}

/// Error recurrente clasificado por tipo (HU-05).
@embedded
class ErrorFrecuente {
  /// Tipo de error: "confusión", "longitud", "inferencia".
  late String tipo;

  /// Detalle del error (ej. par de letras confundidas: "b-d").
  late String detalle;

  /// Número de veces que ocurrió.
  late int frecuencia;

  /// Última ocurrencia.
  late DateTime? ultimaOcurrencia;

  ErrorFrecuente() {
    tipo = '';
    detalle = '';
    frecuencia = 0;
  }
}

/// Configuración personalizada del perfil.
@embedded
class ConfiguracionPerfil {
  /// Tolerancia de trazo para grafomotricidad (HU-13): "baja", "media", "alta".
  late String toleranciaTrazo;

  /// Límite de tiempo en minutos por sesión — solo para modo infantil (HU-16).
  late int? tiempoMaximoMinutos;

  /// Variante dialectal seleccionada (HU-22) — solo para modo adulto.
  late String? varianteDialectal;

  /// Si la navegación por voz está activada (HU-07).
  late bool navegacionPorVoz;

  ConfiguracionPerfil() {
    toleranciaTrazo = 'media';
    navegacionPorVoz = false;
  }
}

/// Datos de la racha diaria del usuario (HU-08).
@embedded
class RachaUsuario {
  /// Días consecutivos actuales.
  late int diasConsecutivos;

  /// Máxima racha histórica.
  late int mejorRacha;

  /// Fechas en que se completó una sesión (formato ISO string).
  late List<String> diasCompletados;

  /// Hitos desbloqueados (IDs de logros).
  late List<String> hitosDesbloqueados;

  RachaUsuario() {
    diasConsecutivos = 0;
    mejorRacha = 0;
    diasCompletados = [];
    hitosDesbloqueados = [];
  }
}
