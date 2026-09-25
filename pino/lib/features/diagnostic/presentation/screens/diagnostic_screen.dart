import 'package:flutter/material.dart';

class DiagnosticScreen extends StatelessWidget {
  const DiagnosticScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Evaluación Inicial')),
      body: PageView(
        children: const [
          Center(child: Text('Pregunta 1: ¿Puedes encontrar la letra A?')),
          Center(child: Text('Pregunta 2: ¿Cuál dice "mama"?')),
          Center(child: Text('Pregunta 3: ¿De qué trata este texto?')),
        ],
      ),
    );
  }
}
