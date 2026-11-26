import 'package:flutter/material.dart';

import '../../data/models/phoneme.dart';

class PhonemeTile extends StatelessWidget {
  const PhonemeTile({super.key, required this.fonema, required this.onTap});

  final Phoneme fonema;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Column(
              children: [
                Text(
                  fonema.grafema,
                  style: const TextStyle(fontSize: 36, fontWeight: FontWeight.bold),
                ),
                Text(fonema.palabraEjemplo),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
