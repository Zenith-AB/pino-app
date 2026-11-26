import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../data/models/user_profile.dart';
import '../providers/profile_provider.dart';
import '../widgets/avatar_card.dart';

class ProfileSelectionScreen extends ConsumerStatefulWidget {
  const ProfileSelectionScreen({super.key});

  @override
  ConsumerState<ProfileSelectionScreen> createState() => _ProfileSelectionScreenState();
}

class _ProfileSelectionScreenState extends ConsumerState<ProfileSelectionScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) ref.read(profileProvider.notifier).cargarPerfiles();
    });
  }

  Future<void> _eliminar(UserProfile perfil) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('¿Eliminar a ${perfil.nombre}?'),
        content: const Text('Se borrará todo su progreso en este dispositivo.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Eliminar')),
        ],
      ),
    );
    if (confirmado == true && mounted) {
      await ref.read(profileProvider.notifier).eliminarPerfil(perfil.id);
    }
  }

  @override
  Widget build(BuildContext context) {
    final estado = ref.watch(profileProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('¿Quién va a aprender?')),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: estado.cargando
                  ? const Center(child: CircularProgressIndicator())
                  : estado.perfiles.isEmpty
                  ? const Center(child: Text('Toca + para crear tu primer perfil'))
                  : GridView.extent(
                      maxCrossAxisExtent: 160,
                      padding: const EdgeInsets.all(16),
                      children: [
                        for (final perfil in estado.perfiles)
                          AvatarCard(
                            indice: perfil.avatarIndex,
                            nombre: perfil.nombre,
                            onTap: () {
                              ref.read(profileProvider.notifier).seleccionarPerfil(perfil);
                              context.go('/home');
                            },
                            onLongPress: () => _eliminar(perfil),
                          ),
                      ],
                    ),
            ),
            if (estado.perfiles.isNotEmpty)
              const Text('Mantén presionado un perfil para eliminarlo'),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 88),
              child: OutlinedButton.icon(
                onPressed: () => context.push('/beta'),
                icon: const Icon(Icons.record_voice_over),
                label: const Text('Practicar sin perfil'),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        tooltip: 'Crear perfil',
        onPressed: () => context.push('/create-profile'),
        child: const Icon(Icons.add),
      ),
    );
  }
}
