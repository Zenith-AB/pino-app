import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/services/tts_service.dart';
import '../../../profile/presentation/providers/profile_provider.dart';
import '../../../profile/presentation/widgets/nombre_nivel.dart';
import '../providers/diagnostic_provider.dart';
import '../widgets/diagnostic_question_widget.dart';

class DiagnosticScreen extends ConsumerStatefulWidget {
  const DiagnosticScreen({super.key});

  @override
  ConsumerState<DiagnosticScreen> createState() => _DiagnosticScreenState();
}

class _DiagnosticScreenState extends ConsumerState<DiagnosticScreen> {
  bool _listo = false;
  bool _guardando = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (ref.read(perfilActivoProvider) == null) {
        context.go('/');
        return;
      }
      ref.read(diagnosticProvider.notifier).iniciar();
      setState(() => _listo = true);
    });
  }

  Future<void> _terminar() async {
    setState(() => _guardando = true);
    await ref.read(diagnosticProvider.notifier).guardarResultado();
    if (mounted) context.go('/home');
  }

  @override
  Widget build(BuildContext context) {
    final estado = ref.watch(diagnosticProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Evaluación inicial')),
      body: !_listo
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(24),
              children: estado.completado
                  ? [
                      const Icon(Icons.emoji_events, size: 80, color: Colors.amber),
                      const SizedBox(height: 16),
                      Text(
                        'Tu punto de partida: ${nombreNivel(estado.nivelDetectado!)}',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 24),
                      ElevatedButton(
                        onPressed: _guardando ? null : _terminar,
                        child: const Text('Empezar'),
                      ),
                    ]
                  : [
                      LinearProgressIndicator(
                        value: estado.preguntaActual / preguntasDiagnostico.length,
                      ),
                      const SizedBox(height: 24),
                      DiagnosticQuestionWidget(
                        pregunta: preguntasDiagnostico[estado.preguntaActual],
                        onRespuesta: ref.read(diagnosticProvider.notifier).responder,
                        onEscuchar: () => ref
                            .read(ttsServiceProvider)
                            .hablar(preguntasDiagnostico[estado.preguntaActual].pregunta),
                      ),
                    ],
            ),
    );
  }
}
