import 'package:agrisense_flutter/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('App renders smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const AgriSenseApp());
    await tester.pump();

    // Verify the app renders
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
