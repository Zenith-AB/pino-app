import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/services/ml_api_client.dart';
import '../../../../core/services/tts_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../data/vocabulario_beta.dart';
import '../providers/practica_provider.dart';
import '../widgets/analizar_palabra.dart';

const _niveles = {
  1: 'Primeras palabras',
  2: 'Preescolar',
  3: 'Lectura inicial',
  4: 'En desarrollo',
};

/// Escuchar una palabra y practicar su pronunciación.
class PinoBetaScreen extends ConsumerStatefulWidget {
  const PinoBetaScreen({super.key, this.nivelInicial = 1});

  final int nivelInicial;

  @override
  ConsumerState<PinoBetaScreen> createState() => _PinoBetaScreenState();
}

class _PinoBetaScreenState extends ConsumerState<PinoBetaScreen> {
  String _idioma = 'es';
  late int _nivel = widget.nivelInicial;
  int _indice = 0;

  /// Palabra escrita por el usuario; `null` si se recorre el vocabulario.
  PalabraBeta? _propia;

  void _usarPropia(PalabraBeta palabra) {
    ref.read(practicaProvider.notifier).reiniciar();
    setState(() => _propia = palabra);
  }

  void _cambiar({String? idioma, int? nivel, int? indice}) {
    ref.read(practicaProvider.notifier).reiniciar();
    setState(() {
      _idioma = idioma ?? _idioma;
      _nivel = nivel ?? _nivel;
      _indice = indice ?? 0;
      _propia = null;
    });
  }

  Future<void> _escuchar(String texto, {bool lento = false}) async {
    final hayVoz = await ref.read(ttsServiceProvider).hablar(texto, idioma: _idioma, lento: lento);
    if (!hayVoz && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Este dispositivo no tiene voz instalada para ese idioma.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final vocabulario = ref.watch(vocabularioBetaProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Pino Beta')),
      body: SafeArea(
        child: vocabulario.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => const Center(child: Text('No se pudo cargar el vocabulario.')),
          data: (datos) => _contenido(datos[_idioma]!.where((p) => p.nivel == _nivel).toList()),
        ),
      ),
    );
  }

  Widget _contenido(List<PalabraBeta> palabras) {
    final actual = _propia ?? palabras[_indice % palabras.length];
    final practica = ref.watch(practicaProvider);
    final grabando = practica.fase == FasePractica.grabando;
    final evaluando = practica.fase == FasePractica.evaluando;
    final textos = Theme.of(context).textTheme;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Center(
          child: SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'es', label: Text('Español')),
              ButtonSegment(value: 'en', label: Text('Inglés')),
            ],
            selected: {_idioma},
            onSelectionChanged: (s) => _cambiar(idioma: s.first),
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 8,
          children: [
            for (final nivel in _niveles.entries)
              ChoiceChip(
                label: Text(nivel.value),
                selected: _nivel == nivel.key,
                onSelected: (_) => _cambiar(nivel: nivel.key),
              ),
          ],
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 8),
            child: Row(
              children: [
                IconButton(
                  tooltip: 'Palabra anterior',
                  iconSize: 32,
                  icon: const Icon(Icons.chevron_left),
                  onPressed: () => _cambiar(indice: (_indice - 1) % palabras.length),
                ),
                Expanded(
                  child: Column(
                    children: [
                      FittedBox(
                        child: Text(
                          actual.palabra,
                          key: const Key('palabra'),
                          style: textos.displayMedium?.copyWith(fontWeight: FontWeight.bold),
                        ),
                      ),
                      if (actual.silabas.length > 1)
                        Text(actual.silabas.join(' · '), style: textos.titleLarge),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Palabra siguiente',
                  iconSize: 32,
                  icon: const Icon(Icons.chevron_right),
                  onPressed: () => _cambiar(indice: (_indice + 1) % palabras.length),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 8,
          runSpacing: 8,
          children: [
            // No se puede escuchar mientras se graba: el micrófono captaría la voz del teléfono.
            ElevatedButton.icon(
              onPressed: grabando ? null : () => _escuchar(actual.palabra),
              icon: const Icon(Icons.volume_up),
              label: const Text('Escuchar'),
            ),
            ElevatedButton.icon(
              onPressed: grabando ? null : () => _escuchar(actual.palabra, lento: true),
              icon: const Icon(Icons.slow_motion_video),
              label: const Text('Lento'),
            ),
            if (actual.silabas.length > 1)
              ElevatedButton.icon(
                onPressed: grabando
                    ? null
                    : () => _escuchar(actual.silabas.join(', '), lento: true),
                icon: const Icon(Icons.more_horiz),
                label: const Text('Sílabas'),
              ),
          ],
        ),
        const SizedBox(height: 24),
        Center(
          child: FloatingActionButton.large(
            heroTag: 'microfono',
            tooltip: grabando ? 'Terminar grabación' : 'Grabar mi voz',
            backgroundColor: grabando ? AppColors.error : AppColors.secondary,
            onPressed: evaluando
                ? null
                : () async {
                    await ref.read(ttsServiceProvider).detener();
                    await ref
                        .read(practicaProvider.notifier)
                        .alternarGrabacion(palabra: actual.palabra, idioma: _idioma);
                  },
            child: evaluando
                ? const CircularProgressIndicator()
                : Icon(grabando ? Icons.stop : Icons.mic),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          grabando
              ? 'Di la palabra y toca para terminar'
              : evaluando
              ? 'Escuchando…'
              : 'Toca y di la palabra',
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
        if (practica.error != null)
          Text(
            practica.error!,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.red),
          ),
        if (practica.resultado != null) _Resultado(practica, actual),
        const SizedBox(height: 16),
        AnalizarPalabra(key: ValueKey(_idioma), idioma: _idioma, onPracticar: _usarPropia),
        const SizedBox(height: 16),
        Text(
          'Versión de prueba: puede equivocarse. Tu voz se envía al servidor de Pino '
          'para evaluarla y no se guarda.',
          textAlign: TextAlign.center,
          style: textos.bodySmall,
        ),
      ],
    );
  }
}

class _Resultado extends StatelessWidget {
  const _Resultado(this.estado, this.palabra);

  final EstadoPractica estado;
  final PalabraBeta palabra;

  @override
  Widget build(BuildContext context) {
    final r = estado.resultado!;
    final veredicto = veredictoDe(r);
    final (icono, color, mensaje) = switch (veredicto) {
      Veredicto.bien => (Icons.check_circle, AppColors.success, '¡Muy bien!'),
      Veredicto.casi => (Icons.adjust, AppColors.warning, 'Casi. Escuché «${r.textoDetectado}».'),
      Veredicto.otra => (
        Icons.replay,
        AppColors.error,
        'Escuché «${r.textoDetectado}». Inténtalo otra vez.',
      ),
      Veredicto.sinVoz => (Icons.mic_off, Colors.grey, 'No escuché ninguna palabra.'),
    };

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(icono, color: color, size: 48),
            const SizedBox(height: 8),
            Text(mensaje, textAlign: TextAlign.center),
            if (veredicto != Veredicto.sinVoz && palabra.silabas.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  for (final silaba in _marcas(r))
                    Chip(
                      label: Text(silaba.$1),
                      avatar: Icon(
                        silaba.$2 ? Icons.check : Icons.close,
                        color: silaba.$2 ? AppColors.success : AppColors.error,
                      ),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// Cada sílaba de la palabra con su acierto. La API entrega las correctas e
  /// incorrectas en el orden de la palabra.
  List<(String, bool)> _marcas(ResultadoPronunciacionML r) {
    if (r.correcto) return [for (final s in palabra.silabas) (s, true)];
    final falladas = List<String>.of(r.silabasIncorrectas);
    return [for (final s in palabra.silabas) (s, !falladas.remove(s))];
  }
}
