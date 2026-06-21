import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/utils/source_guard.dart';

void main() {
  test('SourceGuard removes external source fields', () {
    final externalItem = {
      'name': 'Lagavulin 16',
      'source_name': 'Master of Malt',
      'source_url': 'https://masterofmalt.example',
      'source_id': 'mom',
      'internal_source_url': 'https://internal.example',
      'price': 50.0,
    };

    final sanitized = SourceGuard.sanitizePublicItem(externalItem);

    expect(sanitized['name'], 'Lagavulin 16');
    expect(sanitized['price'], 50.0);
    expect(sanitized.containsKey('source_name'), false);
    expect(sanitized.containsKey('source_url'), false);
    expect(sanitized.containsKey('source_id'), false);
    expect(sanitized.containsKey('internal_source_url'), false);
  });

  test('SourceGuard does not mutate original item', () {
    final externalItem = {
      'source_name': 'Master of Malt',
      'source_url': 'https://masterofmalt.example',
      'price': 50.0,
    };

    final sanitized = SourceGuard.sanitizePublicItem(externalItem);

    expect(externalItem.containsKey('source_name'), true);
    expect(externalItem.containsKey('source_url'), true);
    expect(sanitized.containsKey('source_name'), false);
    expect(sanitized.containsKey('source_url'), false);
  });

  test('SourceGuard keeps manual item when explicitly allowed', () {
    final manualItem = {
      'source_name': 'Kişisel Takip',
      'source_url': '',
      'price': 50.0,
    };

    final sanitized = SourceGuard.sanitizePublicItem(
      manualItem,
      isManual: true,
    );

    expect(sanitized['source_name'], 'Kişisel Takip');
    expect(sanitized['source_url'], '');
    expect(sanitized['price'], 50.0);
  });

  test('SourceGuard detects public source fields', () {
    expect(
      SourceGuard.hasPublicSourceFields({'source_url': 'https://example.com'}),
      true,
    );

    expect(
      SourceGuard.hasPublicSourceFields({'name': 'Lagavulin 16'}),
      false,
    );
  });
}