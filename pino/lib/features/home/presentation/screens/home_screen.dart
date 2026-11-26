import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../profile/presentation/providers/profile_provider.dart';
import '../../../profile/presentation/widgets/avatar_card.dart';
import '../../../profile/presentation/widgets/nombre_nivel.dart';
import '../widgets/lesson_card.dart';
import '../widgets/streak_counter.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final perfil = ref.watch(perfilActivoProvider);
    if (perfil == null) {
      return Scaffold(
        body: Center(
          child: ElevatedButton(
            onPressed: () => context.go('/'),
            child: const Text('Elegir perfil'),
          ),
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pino'),
        actions: [
          IconButton(
            tooltip: 'Cambiar de perfil',
            icon: const Icon(Icons.switch_account),
            onPressed: () => context.go('/'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            '${avatarDe(perfil.avatarIndex)} ¡Hola, ${perfil.nombre}!',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          Text('Nivel: ${nombreNivel(perfil.nivel)}'),
          StreakCounter(dias: rachaVigente(perfil.racha, DateTime.now())),
          const SizedBox(height: 16),
          LessonCard(
            icono: Icons.record_voice_over,
            titulo: 'Practicar palabras',
            detalle: 'Escucha, repite y revisa tu pronunciación',
            onTap: () => context.push('/beta?nivel=${nivelDeVocabulario(perfil.nivel)}'),
          ),
          LessonCard(
            icono: Icons.grid_view,
            titulo: 'Explorar letras',
            detalle: 'Toca una letra y escucha una palabra',
            onTap: () => context.push('/phoneme/explore'),
          ),
          LessonCard(
            icono: Icons.extension,
            titulo: 'Juego de relacionar',
            detalle: '¿Con qué letra empieza?',
            onTap: () => context.push('/phoneme/match'),
          ),
          TextButton(
            onPressed: () => context.go('/diagnostic'),
            child: const Text('Repetir la evaluación inicial'),
          ),
        ],
      ),
    );
  }
}
