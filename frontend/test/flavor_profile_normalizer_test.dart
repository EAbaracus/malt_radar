import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/features/flavor/domain/flavor_profile_normalizer.dart';

void main() {
  test('keeps existing seven-axis flavor profile values', () {
    final profile = normalizeFlavorProfileJson(jsonEncode({
      'fruity': 1,
      'sweet': 2,
      'spicy': 3,
      'smoky_peaty': 4,
      'oak_cask': 5,
      'malty_cereal': 6,
      'floral_herbal': 7,
    }));

    expect(profile['fruity'], 1);
    expect(profile['sweet'], 2);
    expect(profile['floral_herbal'], 7);
    expect(profile.keys, containsAll(maltRadarFlavorAxes));
  });

  test('maps Whiskey Mapper component profile to seven radar axes', () {
    final profile = normalizeFlavorProfileJson(jsonEncode({
      'component_1': '0.4',
      'component_2': '0.2',
      'component_3': '0.8',
    }));

    expect(profile.keys, containsAll(maltRadarFlavorAxes));
    expect(profile.values.any((value) => value > 0), isTrue);
    expect(profile['fruity'], 4);
    expect(profile['smoky_peaty'], 8);
  });
}
