import 'package:flutter/material.dart';

class StreakCounter extends StatelessWidget {
  const StreakCounter({super.key});

  @override
  Widget build(BuildContext context) {
    return const Row(
      children: [
        Icon(Icons.local_fire_department, color: Colors.orange),
        Text('5 Días'),
      ],
    );
  }
}
