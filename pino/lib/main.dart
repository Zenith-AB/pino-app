import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/database/database_service.dart';
import 'app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Inicializar base de datos NoSQL (Isar)
  final dbService = DatabaseService();
  await dbService.inicializar();

  // TODO: Inicializar Firebase
  // await Firebase.initializeApp();

  runApp(
    ProviderScope(
      overrides: [
        // Inyectar la instancia real de DatabaseService
        databaseServiceProvider.overrideWithValue(dbService),
      ],
      child: const PinoApp(),
    ),
  );
}
