import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/profile/presentation/screens/profile_selection_screen.dart';
import '../../features/profile/presentation/screens/profile_creation_screen.dart';
import '../../features/diagnostic/presentation/screens/diagnostic_screen.dart';
import '../../features/home/presentation/screens/home_screen.dart';
import '../../features/phoneme/presentation/screens/phoneme_explorer_screen.dart';
import '../../features/phoneme/presentation/screens/phoneme_matching_screen.dart';
import '../../features/tracing/presentation/screens/tracing_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const ProfileSelectionScreen(),
      ),
      GoRoute(
        path: '/create-profile',
        builder: (context, state) => const ProfileCreationScreen(),
      ),
      GoRoute(
        path: '/diagnostic',
        builder: (context, state) => const DiagnosticScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/phoneme/explore',
        builder: (context, state) => const PhonemeExplorerScreen(),
      ),
      GoRoute(
        path: '/phoneme/match',
        builder: (context, state) => const PhonemeMatchingScreen(),
      ),
      GoRoute(
        path: '/trace/:letterId',
        builder: (context, state) {
          final letterId = state.pathParameters['letterId'] ?? 'a';
          return TracingScreen(letterId: letterId);
        },
      ),
    ],
  );
});
