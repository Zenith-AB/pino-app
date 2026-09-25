import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class ProfileCreationScreen extends StatelessWidget {
  const ProfileCreationScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Crear Perfil')),
      body: Column(
        children: [
          const Text('1. Elige tu avatar'),
          const Text('2. Ingresa tu nombre'),
          const Text('3. Selecciona tu modo (Infantil/Adulto)'),
          ElevatedButton(
            onPressed: () => context.push('/diagnostic'),
            child: const Text('Continuar a Diagnóstico'),
          ),
        ],
      ),
    );
  }
}
