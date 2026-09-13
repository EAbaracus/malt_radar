import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/features/auth/presentation/auth_screen.dart';

void main() {
  testWidgets('AuthScreen displays Guest Mode button', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;

    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: AuthScreen()),
      ),
    );
    await tester.pumpAndSettle();
    // Count is now 3: mode toggle, "Forgot password?" (added with the reset
    // flow), and the guest link. The intent of this test is the guest entry
    // point, so it is asserted by label below; the count just guards against
    // losing a control.
    expect(find.byType(TextButton), findsNWidgets(3));
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Text &&
            (widget.data == 'Misafir Olarak İncele' ||
                widget.data == 'Explore as Guest'),
      ),
      findsOneWidget,
    );
  });
}
