import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/services/ml_api_client.dart';
import '../../data/vocabulario_beta.dart';

/// Consulta al modelo de edad de adquisición por cualquier palabra.
class AnalizarPalabra extends ConsumerStatefulWidget {
  const AnalizarPalabra({super.key, required this.idioma, required this.onPracticar});

  final String idioma;
  final ValueChanged<PalabraBeta> onPracticar;

  @override
  ConsumerState<AnalizarPalabra> createState() => _AnalizarPalabraState();
}

class _AnalizarPalabraState extends ConsumerState<AnalizarPalabra> {
  static final _soloLetras = RegExp(r'^[a-záéíóúüñ]{1,40}$');

  final _texto = TextEditingController();
  EdadPalabraML? _resultado;
  String? _error;
  bool _consultando = false;

  @override
  void dispose() {
    _texto.dispose();
    super.dispose();
  }

  Future<void> _consultar() async {
    if (_consultando) return;
    final palabra = _texto.text.trim().toLowerCase();
    if (!_soloLetras.hasMatch(palabra)) {
      setState(() {
        _resultado = null;
        _error = 'Escribe una sola palabra, solo con letras.';
      });
      return;
    }
    setState(() {
      _consultando = true;
      _resultado = null;
      _error = null;
    });
    EdadPalabraML? resultado;
    String? error;
    try {
      resultado = await ref
          .read(mlApiClientProvider)
          .analizarPalabra(palabra: palabra, idioma: widget.idioma);
    } catch (_) {
      error = 'No se pudo consultar. Revisa la conexión con Pino.';
    }
    if (mounted) {
      setState(() {
        _consultando = false;
        _resultado = resultado;
        _error = error;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = _resultado;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('¿A qué edad se aprende una palabra?'),
            TextField(
              controller: _texto,
              maxLength: 40,
              autocorrect: false,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _consultar(),
              decoration: InputDecoration(
                hintText: widget.idioma == 'es'
                    ? 'Escribe una palabra'
                    : 'Escribe una palabra en inglés',
                suffixIcon: IconButton(
                  tooltip: 'Consultar',
                  icon: const Icon(Icons.search),
                  onPressed: _consultando ? null : _consultar,
                ),
              ),
            ),
            if (_consultando) const LinearProgressIndicator(),
            if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
            if (r != null) ...[
              Text(
                '«${r.palabra}»: cerca de los ${r.edadAnios.toStringAsFixed(1).replaceAll('.', ',')} años · '
                '${r.nivel <= 4 ? 'Nivel ${r.nivel}' : 'Fuera del rango infantil'}',
              ),
              Text(
                r.tieneNorma ? 'Dato de un estudio publicado.' : 'Estimación del modelo: puede errar en más de un año. La valida una educadora.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              TextButton.icon(
                onPressed: () => widget.onPracticar(
                  PalabraBeta(palabra: r.palabra, nivel: r.nivel, silabas: r.silabas),
                ),
                icon: const Icon(Icons.record_voice_over),
                label: const Text('Practicar esta palabra'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
