import 'package:flutter/material.dart';

class PhonemeMatchingScreen extends StatelessWidget {
  const PhonemeMatchingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Juego de Relacionar')),
      body: Column(
        children: const [
          Text('Escucha el sonido'),
          Text('Elige la letra correcta (2-3 opciones)'),
        ],
      ),
    );
  }
}
