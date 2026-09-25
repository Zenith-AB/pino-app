class AudioService {
  // TODO: Inicializar audioplayers

  Future<void> playPhoneme(String phonemeId) async {
    // TODO: Implementar reproducción de fonema desde assets locales
  }

  Future<void> playFeedback(FeedbackType type) async {
    // TODO: Implementar sonidos de éxito/error
  }

  void stop() {
    // TODO: Detener audio
  }

  void dispose() {
    // TODO: Liberar recursos
  }
}

enum FeedbackType { success, error }
