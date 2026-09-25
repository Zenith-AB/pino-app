import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class ProfileSelectionScreen extends StatelessWidget {
  const ProfileSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Seleccionar Perfil')),
      body: Center(
        child: const Text('Grid de avatares aquí'),
        // TODO: Implementar GridView con perfiles
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push('/create-profile'),
        child: const Icon(Icons.add),
      ),
    );
  }
}
