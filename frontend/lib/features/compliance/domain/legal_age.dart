import 'package:flutter/foundation.dart';

/// Minimum legal drinking / purchase age per country.
///
/// This is a curated, non-exhaustive reference table used only to set the
/// age-gate threshold in the UI. It is NOT legal advice and individual
/// jurisdictions (e.g. Canadian provinces, some Indian/UAE emirates) may
/// differ. Unlisted countries fall back to [defaultMinAge]. +18 additive,
/// +20/+21 hard thresholds reflect the notable variance across markets.
@immutable
class LegalEntry {
  final String name;
  final String code;
  final int minAge;

  const LegalEntry(this.name, this.code, this.minAge);
}

const int defaultMinAge = 18;

/// (English display name, ISO-2 code, minimum legal drinking age).
const List<LegalEntry> legalDrinkingAges = <LegalEntry>[
  // 21 — highest threshold
  LegalEntry('United States', 'US', 21),
  LegalEntry('United Arab Emirates', 'AE', 21),
  LegalEntry('Saudi Arabia', 'SA', 21),
  LegalEntry('Pakistan', 'PK', 21),
  LegalEntry('Bahrain', 'BH', 21),
  LegalEntry('Qatar', 'QA', 21),
  LegalEntry('Kuwait', 'KW', 21),
  LegalEntry('Oman', 'OM', 21),
  LegalEntry('Nigeria', 'NG', 21),
  LegalEntry('Dominican Republic', 'DO', 21),
  // 20 — Japan, Iceland
  LegalEntry('Japan', 'JP', 20),
  LegalEntry('Iceland', 'IS', 20),
  LegalEntry('Paraguay', 'PY', 20),
  // 19 — South Korea
  LegalEntry('South Korea', 'KR', 19),
  // 18 — default majority
  LegalEntry('Türkiye', 'TR', 18),
  LegalEntry('United Kingdom', 'GB', 18),
  LegalEntry('Ireland', 'IE', 18),
  LegalEntry('Spain', 'ES', 18),
  LegalEntry('France', 'FR', 18),
  LegalEntry('Germany', 'DE', 18),
  LegalEntry('Italy', 'IT', 18),
  LegalEntry('Netherlands', 'NL', 18),
  LegalEntry('Belgium', 'BE', 18),
  LegalEntry('Switzerland', 'CH', 18),
  LegalEntry('Austria', 'AT', 18),
  LegalEntry('Portugal', 'PT', 18),
  LegalEntry('Greece', 'GR', 18),
  LegalEntry('Sweden', 'SE', 18),
  LegalEntry('Norway', 'NO', 18),
  LegalEntry('Denmark', 'DK', 18),
  LegalEntry('Poland', 'PL', 18),
  LegalEntry('Czechia', 'CZ', 18),
  LegalEntry('Hungary', 'HU', 18),
  LegalEntry('Romania', 'RO', 18),
  LegalEntry('Russia', 'RU', 18),
  LegalEntry('China', 'CN', 18),
  LegalEntry('Brazil', 'BR', 18),
  LegalEntry('Mexico', 'MX', 18),
  LegalEntry('Argentina', 'AR', 18),
  LegalEntry('Colombia', 'CO', 18),
  LegalEntry('Chile', 'CL', 18),
  LegalEntry('Peru', 'PE', 18),
  LegalEntry('South Africa', 'ZA', 18),
  LegalEntry('Australia', 'AU', 18),
  LegalEntry('New Zealand', 'NZ', 18),
  // Canada varies 18/19 by province → represent as majority default; gate is advisory.
  LegalEntry('Canada', 'CA', 18),
];

/// Looks up the minimum legal drinking age for an ISO-2 country code.
int legalAgeFor(String code) {
  for (final entry in legalDrinkingAges) {
    if (entry.code == code) return entry.minAge;
  }
  return defaultMinAge;
}

/// The country currently selected in the gate; defaults to the first entry.
List<LegalEntry> sortedEntries() {
  final list = List<LegalEntry>.from(legalDrinkingAges);
  list.sort((a, b) => a.name.compareTo(b.name));
  return list;
}
