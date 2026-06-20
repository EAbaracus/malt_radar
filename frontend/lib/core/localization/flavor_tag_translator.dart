final Map<String, String> _enToTrFlavorTags = {
  'apple': 'elma',
  'banana': 'muz',
  'cherry': 'kiraz',
  'citrus': 'narenciye',
  'fruity': 'meyvemsi',
  'lemon': 'limon',
  'orange': 'portakal',
  'pear': 'armut',
  'raisins': 'kuru üzüm',
  'zest': 'narenciye kabuğu',
  'balanced': 'dengeli',
  'complex': 'karmaşık',
  'dry': 'kuru',
  'earthy': 'topraksı',
  'heavy': 'gövdeli',
  'light': 'hafif',
  'lingering': 'kalıcı',
  'mellow': 'yumuşak',
  'mild': 'hafif',
  'old': 'eski',
  'smooth': 'pürüzsüz',
  'barley': 'arpa',
  'buttery': 'tereyağlı',
  'butterscotch': 'karamelize şeker',
  'candy': 'şekerleme',
  'chocolate': 'çikolata',
  'cinnamon': 'tarçın',
  'cocoa': 'kakao',
  'corn': 'mısır',
  'honey': 'bal',
  'tea': 'çay',
  'toffee': 'karamel',
  'clove': 'karanfil',
  'coffee': 'kahve',
  'floral': 'çiçeksi',
  'licorice': 'meyan kökü',
  'malty': 'maltımsı',
  'mint': 'nane',
  'nutmeg': 'muskat',
  'peaty': 'turbalı',
  'peppery': 'biberli',
  'roses': 'gül',
  'spices': 'baharatlar',
  'sugar': 'şeker',
  'tobacco': 'tütün',
  'vanilla': 'vanilya',
  'wood': 'odunsu',
  'sherry': 'şeri',
  'bitter': 'acı',
  'brine': 'tuzlu su',
  'creamy': 'kremsi',
  'ginger': 'zencefil',
  'herbal': 'otsu',
  'maple': 'akçaağaç',
  'nutty': 'fındıksı',
  'oak': 'meşe',
  'rich': 'zengin',
  'salty': 'tuzlu',
  'smokey': 'isli',
  'sour': 'ekşi',
  'spicy': 'baharatlı',
  'sweet': 'tatlı',
  'amber': 'kehribar',
  'brown': 'kahverengi',
  'green': 'yeşil',
  'caramel': 'karamel',
  'pal': 'pal',
};

final Map<String, String> _trToEnFlavorTags = _enToTrFlavorTags.map(
  (key, value) => MapEntry(value, key),
);

final Map<String, String> _trToEnTastingNotes = {
  'Burun': 'Nose',
  'Damak': 'Palate',
  'Bitiş': 'Finish',
  'Zengin vanilya': 'Rich vanilla',
  'portakal marmeladı': 'orange marmalade',
  'bal': 'honey',
  'Pürüzsüz maltsı tatlılık': 'Smooth malty sweetness',
  'baharatlı krema': 'spiced cream',
  'esmer şeker': 'brown sugar',
  'Orta': 'Medium',
  'tatlı meşe': 'sweet oak',
  'akıcı': 'smooth',
};

final Map<String, String> _enToTrTastingNotes = _trToEnTastingNotes.map(
  (key, value) => MapEntry(value, key),
);

String localizeFlavorTag(String tag, String langCode) {
  final cleanTag = tag.trim().toLowerCase();
  String result = cleanTag;
  if (langCode == 'tr') {
    result = _enToTrFlavorTags[cleanTag] ?? cleanTag;
  } else {
    result = _trToEnFlavorTags[cleanTag] ?? cleanTag;
  }
  if (result.isEmpty) return result;
  return result[0].toUpperCase() + result.substring(1);
}

String localizeTastingNote(String note, String langCode) {
  final trimmedNote = note.trim();

  if (langCode == 'en') {
    return _localizeTurkishTastingNoteToEnglish(trimmedNote);
  } else {
    final exactMatch = _enToTrTastingNotes[trimmedNote];
    if (exactMatch != null) return exactMatch;

    if (trimmedNote.startsWith('Nose:')) {
      return trimmedNote.replaceFirst('Nose:', 'Burun:');
    } else if (trimmedNote.startsWith('Palate:')) {
      return trimmedNote.replaceFirst('Palate:', 'Damak:');
    } else if (trimmedNote.startsWith('Finish:')) {
      return trimmedNote.replaceFirst('Finish:', 'Bitiş:');
    }
  }
  return note;
}

String _localizeTurkishTastingNoteToEnglish(String note) {
  final exactMatch = _trToEnTastingNotes[note];
  if (exactMatch != null) return exactMatch;

  final colonIndex = note.indexOf(':');
  if (colonIndex == -1) return note;

  final rawPrefix = note.substring(0, colonIndex).trim();
  final rawBody = note.substring(colonIndex + 1).trim();
  final localizedPrefix = _trToEnTastingNotes[rawPrefix];
  if (localizedPrefix == null) return note;

  final localizedBody = _trToEnTastingNotes[rawBody] ?? rawBody;
  return '$localizedPrefix: $localizedBody';
}
