import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/services/tts_service.dart';
import '../../../profile/presentation/providers/profile_provider.dart';
import '../../data/models/phoneme.dart';
import '../providers/phoneme_provider.dart';
import '../widgets/matching_option.dart';

class PhonemeMatchingScreen extends ConsumerStatefulWidget {
  const PhonemeMatchingScreen({super.key});

  @override
  ConsumerState<PhonemeMatchingScreen> createState() => _PhonemeMatchingScreenState();
}

class _PhonemeMatchingScreenState extends ConsumerState<PhonemeMatchingScreen> {
  bool _ocupado = true;
  bool _acertado = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      await ref.read(phonemeProvider.notifier).cargarFonemas();
      await _nuevo();
    });
  }

  Future<void> _nuevo() async {
    if (!mounted) return;
    await ref.read(phonemeProvider.notifier).generarEjercicioEmparejamiento();
    if (mounted) {
      setState(() {
        _ocupado = false;
        _acertado = false;
      });
    }
  }

  Future<void> _responder(Phoneme opcion) async {
    // Un intento a la vez: dos toques rápidos no se registran dos veces.
    setState(() => _ocupado = true);
    final correcto = opcion.grafema == ref.read(phonemeProvider).fonemaActual?.grafema;
    await ref.read(phonemeProvider.notifier).verificarRespuesta(opcion);
    if (!mounted) return;
    await ref.read(profileProvider.notifier).completarDia();
    if (mounted) {
      setState(() {
        _acertado = correcto;
        _ocupado = correcto;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final estado = ref.watch(phonemeProvider);
    final actual = estado.fonemaActual;
    return Scaffold(
      appBar: AppBar(title: const Text('Juego de relacionar')),
      body: actual == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(24),
              children: [
                const Text(
                  'Escucha la palabra. ¿Con qué letra empieza?',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                Center(
                  child: IconButton.filled(
                    tooltip: 'Escuchar la palabra',
                    iconSize: 64,
                    icon: const Icon(Icons.volume_up),
                    onPressed: () => ref.read(ttsServiceProvider).hablar(actual.palabraEjemplo),
                  ),
                ),
                const SizedBox(height: 32),
                Wrap(
                  alignment: WrapAlignment.center,
                  spacing: 16,
                  runSpacing: 16,
                  children: [
                    for (final opcion in estado.opcionesEmparejamiento)
                      MatchingOption(
                        grafema: opcion.grafema,
                        onTap: _ocupado ? null : () => _responder(opcion),
                      ),
                  ],
                ),
                const SizedBox(height: 24),
                if (estado.feedback != null) Text(estado.feedback!, textAlign: TextAlign.center),
                if (_acertado) ...[
                  const SizedBox(height: 16),
                  ElevatedButton(onPressed: _nuevo, child: const Text('Siguiente')),
                ],
              ],
            ),
    );
  }
}
