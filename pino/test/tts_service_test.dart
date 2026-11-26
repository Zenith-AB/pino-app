import 'package:flutter_test/flutter_test.dart';
import 'package:pino/core/services/tts_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('sin motor de voz avisa en vez de fallar', () async {
    final voz = TtsService();
    expect(await voz.hablar('casa'), isFalse);
    await voz.detener();
  });
}
