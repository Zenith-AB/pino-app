import 'package:flutter/material.dart';

class PhonemeExplorerScreen extends StatelessWidget {
  const PhonemeExplorerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Explorador de Fonemas')),
      body: const Center(
        child: Text('Grid de letras/sílabas con botones de audio'),
      ),
    );
  }
}
