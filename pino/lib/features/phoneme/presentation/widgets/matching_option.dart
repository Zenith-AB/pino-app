import 'package:flutter/material.dart';

class MatchingOption extends StatelessWidget {
  const MatchingOption({super.key, required this.grafema, this.onTap});

  final String grafema;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 96,
      height: 96,
      child: ElevatedButton(
        onPressed: onTap,
        style: ElevatedButton.styleFrom(padding: EdgeInsets.zero),
        child: Text(grafema, style: const TextStyle(fontSize: 36)),
      ),
    );
  }
}
