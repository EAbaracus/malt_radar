import 'dart:convert';

const List<String> maltRadarFlavorAxes = [
  'fruity',
  'sweet',
  'spicy',
  'smoky_peaty',
  'oak_cask',
  'malty_cereal',
  'floral_herbal',
];

Map<String, double> normalizeFlavorProfileJson(String flavorProfileJson) {
  final decoded = jsonDecode(flavorProfileJson);
  if (decoded is! Map<String, dynamic>) {
    return {};
  }
  return normalizeFlavorProfileMap(decoded);
}

Map<String, double> normalizeFlavorProfileMap(Map<String, dynamic> profile) {
  final axisProfile = <String, double>{};
  var hasAxisValue = false;

  for (final axis in maltRadarFlavorAxes) {
    final value = _numValue(profile[axis]);
    axisProfile[axis] = value;
    hasAxisValue = hasAxisValue || value > 0;
  }

  if (hasAxisValue) {
    return axisProfile;
  }

  if (_hasWhiskeyMapperComponents(profile)) {
    return _mapWhiskeyMapperComponents(profile);
  }

  return axisProfile;
}

bool _hasWhiskeyMapperComponents(Map<String, dynamic> profile) {
  return profile.containsKey('component_1') &&
      profile.containsKey('component_2') &&
      profile.containsKey('component_3');
}

Map<String, double> _mapWhiskeyMapperComponents(Map<String, dynamic> profile) {
  final component1 = _numValue(profile['component_1']);
  final component2 = _numValue(profile['component_2']);
  final component3 = _numValue(profile['component_3']);

  return {
    'fruity': _scale(component1),
    'sweet': _scale((component1 + component2) / 2),
    'spicy': _scale(component2),
    'smoky_peaty': _scale(component3),
    'oak_cask': _scale((component2 + component3) / 2),
    'malty_cereal': _scale((component1 + component3) / 2),
    'floral_herbal': _scale(component1 * 0.5),
  };
}

double _numValue(Object? value) {
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value) ?? 0.0;
  }
  return 0.0;
}

double _scale(double value) {
  if (value <= 0) {
    return 0.0;
  }
  if (value <= 1) {
    return value * 10;
  }
  return value;
}
