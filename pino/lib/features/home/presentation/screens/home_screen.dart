import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Inicio - Pino')),
      body: Column(
        children: const [
          Text('Bienvenido (Nombre del Perfil)'),
          Text('Racha: 5 días'),
          Expanded(
            child: Center(child: Text('Módulos de Lecciones')),
          ),
        ],
      ),
    );
  }
}
