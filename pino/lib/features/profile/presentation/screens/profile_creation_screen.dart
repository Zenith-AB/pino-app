import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../data/models/user_profile.dart';
import '../providers/profile_provider.dart';
import '../widgets/avatar_card.dart';

class ProfileCreationScreen extends ConsumerStatefulWidget {
  const ProfileCreationScreen({super.key});

  @override
  ConsumerState<ProfileCreationScreen> createState() => _ProfileCreationScreenState();
}

class _ProfileCreationScreenState extends ConsumerState<ProfileCreationScreen> {
  final _nombre = TextEditingController();
  int _avatar = 0;
  ProfileMode _modo = ProfileMode.infantil;
  bool _guardando = false;

  @override
  void dispose() {
    _nombre.dispose();
    super.dispose();
  }

  Future<void> _crear() async {
    setState(() => _guardando = true);
    final notifier = ref.read(profileProvider.notifier);
    final id = await notifier.crearPerfil(
      nombre: _nombre.text.trim(),
      avatarIndex: _avatar,
      modo: _modo,
    );
    if (!mounted) return;
    notifier.seleccionarPerfil(ref.read(profileProvider).perfiles.firstWhere((p) => p.id == id));
    context.go('/diagnostic');
  }

  @override
  Widget build(BuildContext context) {
    final valido = _nombre.text.trim().isNotEmpty && !_guardando;
    return Scaffold(
      appBar: AppBar(title: const Text('Crear perfil')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('1. Elige tu avatar'),
          GridView.count(
            crossAxisCount: 4,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            children: [
              for (var i = 0; i < avatares.length; i++)
                AvatarCard(
                  indice: i,
                  seleccionado: i == _avatar,
                  onTap: () => setState(() => _avatar = i),
                ),
            ],
          ),
          const SizedBox(height: 16),
          const Text('2. Escribe tu nombre o apodo'),
          TextField(
            controller: _nombre,
            maxLength: 20,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(hintText: 'Nombre o apodo'),
            onChanged: (_) => setState(() {}),
          ),
          const Text('3. Elige el modo'),
          const SizedBox(height: 8),
          SegmentedButton<ProfileMode>(
            segments: const [
              ButtonSegment(value: ProfileMode.infantil, label: Text('Infantil')),
              ButtonSegment(value: ProfileMode.adulto, label: Text('Adulto')),
            ],
            selected: {_modo},
            onSelectionChanged: (s) => setState(() => _modo = s.first),
          ),
          const SizedBox(height: 24),
          ElevatedButton(onPressed: valido ? _crear : null, child: const Text('Continuar')),
        ],
      ),
    );
  }
}
