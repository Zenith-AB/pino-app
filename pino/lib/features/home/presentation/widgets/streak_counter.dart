import 'package:flutter/material.dart';

import '../../../profile/data/models/user_profile.dart';

/// Días seguidos practicando. Vale 0 si no se practicó ni hoy ni ayer.
int rachaVigente(RachaUsuario racha, DateTime ahora) {
  String dia(DateTime f) => f.toIso8601String().substring(0, 10);
  final recientes = [dia(ahora), dia(DateTime(ahora.year, ahora.month, ahora.day - 1))];
  return recientes.any(racha.diasCompletados.contains) ? racha.diasConsecutivos : 0;
}

class StreakCounter extends StatelessWidget {
  const StreakCounter({super.key, required this.dias});

  final int dias;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.local_fire_department, color: Colors.orange),
        Text(dias == 1 ? '1 día seguido' : '$dias días seguidos'),
      ],
    );
  }
}
