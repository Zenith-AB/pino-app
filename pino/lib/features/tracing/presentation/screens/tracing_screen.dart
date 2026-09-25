import 'package:flutter/material.dart';

class TracingScreen extends StatelessWidget {
  final String letterId;

  const TracingScreen({super.key, required this.letterId});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Trazo: $letterId')),
      body: const Center(
        child: Text('Canvas para trazado de letras'),
      ),
    );
  }
}
