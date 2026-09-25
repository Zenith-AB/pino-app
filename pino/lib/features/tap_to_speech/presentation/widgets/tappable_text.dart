import 'package:flutter/material.dart';

class TappableText extends StatelessWidget {
  final String text;

  const TappableText({super.key, required this.text});

  @override
  Widget build(BuildContext context) {
    return Text(text); // TODO: Implementar interactividad
  }
}
