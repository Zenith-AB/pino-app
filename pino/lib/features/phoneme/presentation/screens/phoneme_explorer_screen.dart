import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/services/tts_service.dart';
import '../providers/phoneme_provider.dart';
import '../widgets/phoneme_tile.dart';

class PhonemeExplorerScreen extends ConsumerStatefulWidget {
  const PhonemeExplorerScreen({super.key});

  @override
  ConsumerState<PhonemeExplorerScreen> createState() => _PhonemeExplorerScreenState();
}

class _PhonemeExplorerScreenState extends ConsumerState<PhonemeExplorerScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) ref.read(phonemeProvider.notifier).cargarFonemas();
    });
  }

  @override
  Widget build(BuildContext context) {
    final estado = ref.watch(phonemeProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Explorar letras')),
      body: estado.cargando
          ? const Center(child: CircularProgressIndicator())
          : GridView.extent(
              maxCrossAxisExtent: 120,
              padding: const EdgeInsets.all(12),
              children: [
                for (final fonema in estado.fonemas)
                  PhonemeTile(
                    fonema: fonema,
                    onTap: () => ref.read(ttsServiceProvider).hablar(fonema.palabraEjemplo),
                  ),
              ],
            ),
    );
  }
}
