import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/profile/presentation/providers/profile_provider.dart';
import 'features/profile/data/models/user_profile.dart';

class PinoApp extends ConsumerWidget {
  const PinoApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);
    final modo = ref.watch(modoActualProvider);
    final isInfantil = modo == ProfileMode.infantil;

    return MaterialApp.router(
      title: 'Pino',
      debugShowCheckedModeBanner: false,
      theme: isInfantil ? AppTheme.infantilTheme() : AppTheme.adultoTheme(),
      routerConfig: router,
    );
  }
}
