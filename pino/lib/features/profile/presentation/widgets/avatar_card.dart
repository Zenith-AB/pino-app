import 'package:flutter/material.dart';

/// Avatares disponibles. El perfil guarda la posición en esta lista.
const avatares = ['🦊', '🐻', '🐸', '🐼', '🦁', '🐰', '🐢', '🦉'];

String avatarDe(int indice) => avatares[indice % avatares.length];

class AvatarCard extends StatelessWidget {
  const AvatarCard({
    super.key,
    required this.indice,
    this.nombre,
    this.seleccionado = false,
    this.onTap,
    this.onLongPress,
  });

  final int indice;
  final String? nombre;
  final bool seleccionado;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) {
    final colores = Theme.of(context).colorScheme;
    return Card(
      color: seleccionado ? colores.primaryContainer : null,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        onLongPress: onLongPress,
        child: Semantics(
          selected: seleccionado,
          label: nombre ?? 'Avatar ${indice + 1}',
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Flexible(
                child: FittedBox(
                  child: Text(avatarDe(indice), style: const TextStyle(fontSize: 48)),
                ),
              ),
              if (nombre != null)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  child: Text(nombre!, maxLines: 1, overflow: TextOverflow.ellipsis),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
