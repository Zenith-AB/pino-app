import 'package:flutter/material.dart';

import '../providers/diagnostic_provider.dart';

class DiagnosticQuestionWidget extends StatelessWidget {
  const DiagnosticQuestionWidget({
    super.key,
    required this.pregunta,
    required this.onRespuesta,
    required this.onEscuchar,
  });

  final PreguntaDiagnostico pregunta;
  final ValueChanged<String> onRespuesta;
  final VoidCallback onEscuchar;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          pregunta.pregunta,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        Center(
          child: IconButton(
            tooltip: 'Escuchar la pregunta',
            iconSize: 40,
            icon: const Icon(Icons.volume_up),
            onPressed: onEscuchar,
          ),
        ),
        const SizedBox(height: 16),
        for (final opcion in pregunta.opciones)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: ElevatedButton(
              onPressed: () => onRespuesta(opcion),
              child: Text(opcion, style: const TextStyle(fontSize: 24)),
            ),
          ),
      ],
    );
  }
}
