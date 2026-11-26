import 'package:flutter/material.dart';

class LessonCard extends StatelessWidget {
  const LessonCard({
    super.key,
    required this.icono,
    required this.titulo,
    required this.detalle,
    required this.onTap,
  });

  final IconData icono;
  final String titulo;
  final String detalle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: Icon(icono, size: 40, color: Theme.of(context).colorScheme.primary),
        title: Text(titulo),
        subtitle: Text(detalle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
