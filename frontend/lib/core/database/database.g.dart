// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'database.dart';

// ignore_for_file: type=lint
class $WhiskiesTable extends Whiskies
    with TableInfo<$WhiskiesTable, WhiskyEntity> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $WhiskiesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _externalIdMeta = const VerificationMeta(
    'externalId',
  );
  @override
  late final GeneratedColumn<String> externalId = GeneratedColumn<String>(
    'external_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    false,
    additionalChecks: GeneratedColumn.checkTextLength(
      minTextLength: 1,
      maxTextLength: 100,
    ),
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _countryMeta = const VerificationMeta(
    'country',
  );
  @override
  late final GeneratedColumn<String> country = GeneratedColumn<String>(
    'country',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _regionMeta = const VerificationMeta('region');
  @override
  late final GeneratedColumn<String> region = GeneratedColumn<String>(
    'region',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _categoryMeta = const VerificationMeta(
    'category',
  );
  @override
  late final GeneratedColumn<String> category = GeneratedColumn<String>(
    'category',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _distilleryMeta = const VerificationMeta(
    'distillery',
  );
  @override
  late final GeneratedColumn<String> distillery = GeneratedColumn<String>(
    'distillery',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _ageMeta = const VerificationMeta('age');
  @override
  late final GeneratedColumn<int> age = GeneratedColumn<int>(
    'age',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _abvMeta = const VerificationMeta('abv');
  @override
  late final GeneratedColumn<double> abv = GeneratedColumn<double>(
    'abv',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _caskTypeMeta = const VerificationMeta(
    'caskType',
  );
  @override
  late final GeneratedColumn<String> caskType = GeneratedColumn<String>(
    'cask_type',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _defaultPriceMeta = const VerificationMeta(
    'defaultPrice',
  );
  @override
  late final GeneratedColumn<double> defaultPrice = GeneratedColumn<double>(
    'default_price',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _currencyMeta = const VerificationMeta(
    'currency',
  );
  @override
  late final GeneratedColumn<String> currency = GeneratedColumn<String>(
    'currency',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _sourceNameMeta = const VerificationMeta(
    'sourceName',
  );
  @override
  late final GeneratedColumn<String> sourceName = GeneratedColumn<String>(
    'source_name',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _sourceUrlMeta = const VerificationMeta(
    'sourceUrl',
  );
  @override
  late final GeneratedColumn<String> sourceUrl = GeneratedColumn<String>(
    'source_url',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _fetchedAtMeta = const VerificationMeta(
    'fetchedAt',
  );
  @override
  late final GeneratedColumn<String> fetchedAt = GeneratedColumn<String>(
    'fetched_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _tastingNotesMeta = const VerificationMeta(
    'tastingNotes',
  );
  @override
  late final GeneratedColumn<String> tastingNotes = GeneratedColumn<String>(
    'tasting_notes',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant(''),
  );
  static const VerificationMeta _companionSuggestionsMeta =
      const VerificationMeta('companionSuggestions');
  @override
  late final GeneratedColumn<String> companionSuggestions =
      GeneratedColumn<String>(
        'companion_suggestions',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
        defaultValue: const Constant(''),
      );
  static const VerificationMeta _globalScoreMeta = const VerificationMeta(
    'globalScore',
  );
  @override
  late final GeneratedColumn<double> globalScore = GeneratedColumn<double>(
    'global_score',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    externalId,
    name,
    country,
    region,
    category,
    distillery,
    age,
    abv,
    caskType,
    defaultPrice,
    currency,
    sourceName,
    sourceUrl,
    fetchedAt,
    tastingNotes,
    companionSuggestions,
    globalScore,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'whiskies';
  @override
  VerificationContext validateIntegrity(
    Insertable<WhiskyEntity> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('external_id')) {
      context.handle(
        _externalIdMeta,
        externalId.isAcceptableOrUnknown(data['external_id']!, _externalIdMeta),
      );
    }
    if (data.containsKey('name')) {
      context.handle(
        _nameMeta,
        name.isAcceptableOrUnknown(data['name']!, _nameMeta),
      );
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('country')) {
      context.handle(
        _countryMeta,
        country.isAcceptableOrUnknown(data['country']!, _countryMeta),
      );
    }
    if (data.containsKey('region')) {
      context.handle(
        _regionMeta,
        region.isAcceptableOrUnknown(data['region']!, _regionMeta),
      );
    }
    if (data.containsKey('category')) {
      context.handle(
        _categoryMeta,
        category.isAcceptableOrUnknown(data['category']!, _categoryMeta),
      );
    }
    if (data.containsKey('distillery')) {
      context.handle(
        _distilleryMeta,
        distillery.isAcceptableOrUnknown(data['distillery']!, _distilleryMeta),
      );
    }
    if (data.containsKey('age')) {
      context.handle(
        _ageMeta,
        age.isAcceptableOrUnknown(data['age']!, _ageMeta),
      );
    }
    if (data.containsKey('abv')) {
      context.handle(
        _abvMeta,
        abv.isAcceptableOrUnknown(data['abv']!, _abvMeta),
      );
    }
    if (data.containsKey('cask_type')) {
      context.handle(
        _caskTypeMeta,
        caskType.isAcceptableOrUnknown(data['cask_type']!, _caskTypeMeta),
      );
    }
    if (data.containsKey('default_price')) {
      context.handle(
        _defaultPriceMeta,
        defaultPrice.isAcceptableOrUnknown(
          data['default_price']!,
          _defaultPriceMeta,
        ),
      );
    }
    if (data.containsKey('currency')) {
      context.handle(
        _currencyMeta,
        currency.isAcceptableOrUnknown(data['currency']!, _currencyMeta),
      );
    }
    if (data.containsKey('source_name')) {
      context.handle(
        _sourceNameMeta,
        sourceName.isAcceptableOrUnknown(data['source_name']!, _sourceNameMeta),
      );
    }
    if (data.containsKey('source_url')) {
      context.handle(
        _sourceUrlMeta,
        sourceUrl.isAcceptableOrUnknown(data['source_url']!, _sourceUrlMeta),
      );
    }
    if (data.containsKey('fetched_at')) {
      context.handle(
        _fetchedAtMeta,
        fetchedAt.isAcceptableOrUnknown(data['fetched_at']!, _fetchedAtMeta),
      );
    }
    if (data.containsKey('tasting_notes')) {
      context.handle(
        _tastingNotesMeta,
        tastingNotes.isAcceptableOrUnknown(
          data['tasting_notes']!,
          _tastingNotesMeta,
        ),
      );
    }
    if (data.containsKey('companion_suggestions')) {
      context.handle(
        _companionSuggestionsMeta,
        companionSuggestions.isAcceptableOrUnknown(
          data['companion_suggestions']!,
          _companionSuggestionsMeta,
        ),
      );
    }
    if (data.containsKey('global_score')) {
      context.handle(
        _globalScoreMeta,
        globalScore.isAcceptableOrUnknown(
          data['global_score']!,
          _globalScoreMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  WhiskyEntity map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return WhiskyEntity(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      externalId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}external_id'],
      ),
      name: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}name'],
      )!,
      country: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}country'],
      ),
      region: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}region'],
      ),
      category: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}category'],
      ),
      distillery: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}distillery'],
      ),
      age: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}age'],
      ),
      abv: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}abv'],
      ),
      caskType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}cask_type'],
      ),
      defaultPrice: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}default_price'],
      ),
      currency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}currency'],
      ),
      sourceName: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source_name'],
      ),
      sourceUrl: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source_url'],
      ),
      fetchedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}fetched_at'],
      ),
      tastingNotes: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}tasting_notes'],
      )!,
      companionSuggestions: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}companion_suggestions'],
      )!,
      globalScore: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}global_score'],
      ),
    );
  }

  @override
  $WhiskiesTable createAlias(String alias) {
    return $WhiskiesTable(attachedDatabase, alias);
  }
}

class WhiskyEntity extends DataClass implements Insertable<WhiskyEntity> {
  final int id;
  final String? externalId;
  final String name;
  final String? country;
  final String? region;
  final String? category;
  final String? distillery;
  final int? age;
  final double? abv;
  final String? caskType;
  final double? defaultPrice;
  final String? currency;
  final String? sourceName;
  final String? sourceUrl;
  final String? fetchedAt;
  final String tastingNotes;
  final String companionSuggestions;
  final double? globalScore;
  const WhiskyEntity({
    required this.id,
    this.externalId,
    required this.name,
    this.country,
    this.region,
    this.category,
    this.distillery,
    this.age,
    this.abv,
    this.caskType,
    this.defaultPrice,
    this.currency,
    this.sourceName,
    this.sourceUrl,
    this.fetchedAt,
    required this.tastingNotes,
    required this.companionSuggestions,
    this.globalScore,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    if (!nullToAbsent || externalId != null) {
      map['external_id'] = Variable<String>(externalId);
    }
    map['name'] = Variable<String>(name);
    if (!nullToAbsent || country != null) {
      map['country'] = Variable<String>(country);
    }
    if (!nullToAbsent || region != null) {
      map['region'] = Variable<String>(region);
    }
    if (!nullToAbsent || category != null) {
      map['category'] = Variable<String>(category);
    }
    if (!nullToAbsent || distillery != null) {
      map['distillery'] = Variable<String>(distillery);
    }
    if (!nullToAbsent || age != null) {
      map['age'] = Variable<int>(age);
    }
    if (!nullToAbsent || abv != null) {
      map['abv'] = Variable<double>(abv);
    }
    if (!nullToAbsent || caskType != null) {
      map['cask_type'] = Variable<String>(caskType);
    }
    if (!nullToAbsent || defaultPrice != null) {
      map['default_price'] = Variable<double>(defaultPrice);
    }
    if (!nullToAbsent || currency != null) {
      map['currency'] = Variable<String>(currency);
    }
    if (!nullToAbsent || sourceName != null) {
      map['source_name'] = Variable<String>(sourceName);
    }
    if (!nullToAbsent || sourceUrl != null) {
      map['source_url'] = Variable<String>(sourceUrl);
    }
    if (!nullToAbsent || fetchedAt != null) {
      map['fetched_at'] = Variable<String>(fetchedAt);
    }
    map['tasting_notes'] = Variable<String>(tastingNotes);
    map['companion_suggestions'] = Variable<String>(companionSuggestions);
    if (!nullToAbsent || globalScore != null) {
      map['global_score'] = Variable<double>(globalScore);
    }
    return map;
  }

  WhiskiesCompanion toCompanion(bool nullToAbsent) {
    return WhiskiesCompanion(
      id: Value(id),
      externalId: externalId == null && nullToAbsent
          ? const Value.absent()
          : Value(externalId),
      name: Value(name),
      country: country == null && nullToAbsent
          ? const Value.absent()
          : Value(country),
      region: region == null && nullToAbsent
          ? const Value.absent()
          : Value(region),
      category: category == null && nullToAbsent
          ? const Value.absent()
          : Value(category),
      distillery: distillery == null && nullToAbsent
          ? const Value.absent()
          : Value(distillery),
      age: age == null && nullToAbsent ? const Value.absent() : Value(age),
      abv: abv == null && nullToAbsent ? const Value.absent() : Value(abv),
      caskType: caskType == null && nullToAbsent
          ? const Value.absent()
          : Value(caskType),
      defaultPrice: defaultPrice == null && nullToAbsent
          ? const Value.absent()
          : Value(defaultPrice),
      currency: currency == null && nullToAbsent
          ? const Value.absent()
          : Value(currency),
      sourceName: sourceName == null && nullToAbsent
          ? const Value.absent()
          : Value(sourceName),
      sourceUrl: sourceUrl == null && nullToAbsent
          ? const Value.absent()
          : Value(sourceUrl),
      fetchedAt: fetchedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(fetchedAt),
      tastingNotes: Value(tastingNotes),
      companionSuggestions: Value(companionSuggestions),
      globalScore: globalScore == null && nullToAbsent
          ? const Value.absent()
          : Value(globalScore),
    );
  }

  factory WhiskyEntity.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return WhiskyEntity(
      id: serializer.fromJson<int>(json['id']),
      externalId: serializer.fromJson<String?>(json['externalId']),
      name: serializer.fromJson<String>(json['name']),
      country: serializer.fromJson<String?>(json['country']),
      region: serializer.fromJson<String?>(json['region']),
      category: serializer.fromJson<String?>(json['category']),
      distillery: serializer.fromJson<String?>(json['distillery']),
      age: serializer.fromJson<int?>(json['age']),
      abv: serializer.fromJson<double?>(json['abv']),
      caskType: serializer.fromJson<String?>(json['caskType']),
      defaultPrice: serializer.fromJson<double?>(json['defaultPrice']),
      currency: serializer.fromJson<String?>(json['currency']),
      sourceName: serializer.fromJson<String?>(json['sourceName']),
      sourceUrl: serializer.fromJson<String?>(json['sourceUrl']),
      fetchedAt: serializer.fromJson<String?>(json['fetchedAt']),
      tastingNotes: serializer.fromJson<String>(json['tastingNotes']),
      companionSuggestions: serializer.fromJson<String>(
        json['companionSuggestions'],
      ),
      globalScore: serializer.fromJson<double?>(json['globalScore']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'externalId': serializer.toJson<String?>(externalId),
      'name': serializer.toJson<String>(name),
      'country': serializer.toJson<String?>(country),
      'region': serializer.toJson<String?>(region),
      'category': serializer.toJson<String?>(category),
      'distillery': serializer.toJson<String?>(distillery),
      'age': serializer.toJson<int?>(age),
      'abv': serializer.toJson<double?>(abv),
      'caskType': serializer.toJson<String?>(caskType),
      'defaultPrice': serializer.toJson<double?>(defaultPrice),
      'currency': serializer.toJson<String?>(currency),
      'sourceName': serializer.toJson<String?>(sourceName),
      'sourceUrl': serializer.toJson<String?>(sourceUrl),
      'fetchedAt': serializer.toJson<String?>(fetchedAt),
      'tastingNotes': serializer.toJson<String>(tastingNotes),
      'companionSuggestions': serializer.toJson<String>(companionSuggestions),
      'globalScore': serializer.toJson<double?>(globalScore),
    };
  }

  WhiskyEntity copyWith({
    int? id,
    Value<String?> externalId = const Value.absent(),
    String? name,
    Value<String?> country = const Value.absent(),
    Value<String?> region = const Value.absent(),
    Value<String?> category = const Value.absent(),
    Value<String?> distillery = const Value.absent(),
    Value<int?> age = const Value.absent(),
    Value<double?> abv = const Value.absent(),
    Value<String?> caskType = const Value.absent(),
    Value<double?> defaultPrice = const Value.absent(),
    Value<String?> currency = const Value.absent(),
    Value<String?> sourceName = const Value.absent(),
    Value<String?> sourceUrl = const Value.absent(),
    Value<String?> fetchedAt = const Value.absent(),
    String? tastingNotes,
    String? companionSuggestions,
    Value<double?> globalScore = const Value.absent(),
  }) => WhiskyEntity(
    id: id ?? this.id,
    externalId: externalId.present ? externalId.value : this.externalId,
    name: name ?? this.name,
    country: country.present ? country.value : this.country,
    region: region.present ? region.value : this.region,
    category: category.present ? category.value : this.category,
    distillery: distillery.present ? distillery.value : this.distillery,
    age: age.present ? age.value : this.age,
    abv: abv.present ? abv.value : this.abv,
    caskType: caskType.present ? caskType.value : this.caskType,
    defaultPrice: defaultPrice.present ? defaultPrice.value : this.defaultPrice,
    currency: currency.present ? currency.value : this.currency,
    sourceName: sourceName.present ? sourceName.value : this.sourceName,
    sourceUrl: sourceUrl.present ? sourceUrl.value : this.sourceUrl,
    fetchedAt: fetchedAt.present ? fetchedAt.value : this.fetchedAt,
    tastingNotes: tastingNotes ?? this.tastingNotes,
    companionSuggestions: companionSuggestions ?? this.companionSuggestions,
    globalScore: globalScore.present ? globalScore.value : this.globalScore,
  );
  WhiskyEntity copyWithCompanion(WhiskiesCompanion data) {
    return WhiskyEntity(
      id: data.id.present ? data.id.value : this.id,
      externalId: data.externalId.present
          ? data.externalId.value
          : this.externalId,
      name: data.name.present ? data.name.value : this.name,
      country: data.country.present ? data.country.value : this.country,
      region: data.region.present ? data.region.value : this.region,
      category: data.category.present ? data.category.value : this.category,
      distillery: data.distillery.present
          ? data.distillery.value
          : this.distillery,
      age: data.age.present ? data.age.value : this.age,
      abv: data.abv.present ? data.abv.value : this.abv,
      caskType: data.caskType.present ? data.caskType.value : this.caskType,
      defaultPrice: data.defaultPrice.present
          ? data.defaultPrice.value
          : this.defaultPrice,
      currency: data.currency.present ? data.currency.value : this.currency,
      sourceName: data.sourceName.present
          ? data.sourceName.value
          : this.sourceName,
      sourceUrl: data.sourceUrl.present ? data.sourceUrl.value : this.sourceUrl,
      fetchedAt: data.fetchedAt.present ? data.fetchedAt.value : this.fetchedAt,
      tastingNotes: data.tastingNotes.present
          ? data.tastingNotes.value
          : this.tastingNotes,
      companionSuggestions: data.companionSuggestions.present
          ? data.companionSuggestions.value
          : this.companionSuggestions,
      globalScore: data.globalScore.present
          ? data.globalScore.value
          : this.globalScore,
    );
  }

  @override
  String toString() {
    return (StringBuffer('WhiskyEntity(')
          ..write('id: $id, ')
          ..write('externalId: $externalId, ')
          ..write('name: $name, ')
          ..write('country: $country, ')
          ..write('region: $region, ')
          ..write('category: $category, ')
          ..write('distillery: $distillery, ')
          ..write('age: $age, ')
          ..write('abv: $abv, ')
          ..write('caskType: $caskType, ')
          ..write('defaultPrice: $defaultPrice, ')
          ..write('currency: $currency, ')
          ..write('sourceName: $sourceName, ')
          ..write('sourceUrl: $sourceUrl, ')
          ..write('fetchedAt: $fetchedAt, ')
          ..write('tastingNotes: $tastingNotes, ')
          ..write('companionSuggestions: $companionSuggestions, ')
          ..write('globalScore: $globalScore')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    externalId,
    name,
    country,
    region,
    category,
    distillery,
    age,
    abv,
    caskType,
    defaultPrice,
    currency,
    sourceName,
    sourceUrl,
    fetchedAt,
    tastingNotes,
    companionSuggestions,
    globalScore,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is WhiskyEntity &&
          other.id == this.id &&
          other.externalId == this.externalId &&
          other.name == this.name &&
          other.country == this.country &&
          other.region == this.region &&
          other.category == this.category &&
          other.distillery == this.distillery &&
          other.age == this.age &&
          other.abv == this.abv &&
          other.caskType == this.caskType &&
          other.defaultPrice == this.defaultPrice &&
          other.currency == this.currency &&
          other.sourceName == this.sourceName &&
          other.sourceUrl == this.sourceUrl &&
          other.fetchedAt == this.fetchedAt &&
          other.tastingNotes == this.tastingNotes &&
          other.companionSuggestions == this.companionSuggestions &&
          other.globalScore == this.globalScore);
}

class WhiskiesCompanion extends UpdateCompanion<WhiskyEntity> {
  final Value<int> id;
  final Value<String?> externalId;
  final Value<String> name;
  final Value<String?> country;
  final Value<String?> region;
  final Value<String?> category;
  final Value<String?> distillery;
  final Value<int?> age;
  final Value<double?> abv;
  final Value<String?> caskType;
  final Value<double?> defaultPrice;
  final Value<String?> currency;
  final Value<String?> sourceName;
  final Value<String?> sourceUrl;
  final Value<String?> fetchedAt;
  final Value<String> tastingNotes;
  final Value<String> companionSuggestions;
  final Value<double?> globalScore;
  const WhiskiesCompanion({
    this.id = const Value.absent(),
    this.externalId = const Value.absent(),
    this.name = const Value.absent(),
    this.country = const Value.absent(),
    this.region = const Value.absent(),
    this.category = const Value.absent(),
    this.distillery = const Value.absent(),
    this.age = const Value.absent(),
    this.abv = const Value.absent(),
    this.caskType = const Value.absent(),
    this.defaultPrice = const Value.absent(),
    this.currency = const Value.absent(),
    this.sourceName = const Value.absent(),
    this.sourceUrl = const Value.absent(),
    this.fetchedAt = const Value.absent(),
    this.tastingNotes = const Value.absent(),
    this.companionSuggestions = const Value.absent(),
    this.globalScore = const Value.absent(),
  });
  WhiskiesCompanion.insert({
    this.id = const Value.absent(),
    this.externalId = const Value.absent(),
    required String name,
    this.country = const Value.absent(),
    this.region = const Value.absent(),
    this.category = const Value.absent(),
    this.distillery = const Value.absent(),
    this.age = const Value.absent(),
    this.abv = const Value.absent(),
    this.caskType = const Value.absent(),
    this.defaultPrice = const Value.absent(),
    this.currency = const Value.absent(),
    this.sourceName = const Value.absent(),
    this.sourceUrl = const Value.absent(),
    this.fetchedAt = const Value.absent(),
    this.tastingNotes = const Value.absent(),
    this.companionSuggestions = const Value.absent(),
    this.globalScore = const Value.absent(),
  }) : name = Value(name);
  static Insertable<WhiskyEntity> custom({
    Expression<int>? id,
    Expression<String>? externalId,
    Expression<String>? name,
    Expression<String>? country,
    Expression<String>? region,
    Expression<String>? category,
    Expression<String>? distillery,
    Expression<int>? age,
    Expression<double>? abv,
    Expression<String>? caskType,
    Expression<double>? defaultPrice,
    Expression<String>? currency,
    Expression<String>? sourceName,
    Expression<String>? sourceUrl,
    Expression<String>? fetchedAt,
    Expression<String>? tastingNotes,
    Expression<String>? companionSuggestions,
    Expression<double>? globalScore,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (externalId != null) 'external_id': externalId,
      if (name != null) 'name': name,
      if (country != null) 'country': country,
      if (region != null) 'region': region,
      if (category != null) 'category': category,
      if (distillery != null) 'distillery': distillery,
      if (age != null) 'age': age,
      if (abv != null) 'abv': abv,
      if (caskType != null) 'cask_type': caskType,
      if (defaultPrice != null) 'default_price': defaultPrice,
      if (currency != null) 'currency': currency,
      if (sourceName != null) 'source_name': sourceName,
      if (sourceUrl != null) 'source_url': sourceUrl,
      if (fetchedAt != null) 'fetched_at': fetchedAt,
      if (tastingNotes != null) 'tasting_notes': tastingNotes,
      if (companionSuggestions != null)
        'companion_suggestions': companionSuggestions,
      if (globalScore != null) 'global_score': globalScore,
    });
  }

  WhiskiesCompanion copyWith({
    Value<int>? id,
    Value<String?>? externalId,
    Value<String>? name,
    Value<String?>? country,
    Value<String?>? region,
    Value<String?>? category,
    Value<String?>? distillery,
    Value<int?>? age,
    Value<double?>? abv,
    Value<String?>? caskType,
    Value<double?>? defaultPrice,
    Value<String?>? currency,
    Value<String?>? sourceName,
    Value<String?>? sourceUrl,
    Value<String?>? fetchedAt,
    Value<String>? tastingNotes,
    Value<String>? companionSuggestions,
    Value<double?>? globalScore,
  }) {
    return WhiskiesCompanion(
      id: id ?? this.id,
      externalId: externalId ?? this.externalId,
      name: name ?? this.name,
      country: country ?? this.country,
      region: region ?? this.region,
      category: category ?? this.category,
      distillery: distillery ?? this.distillery,
      age: age ?? this.age,
      abv: abv ?? this.abv,
      caskType: caskType ?? this.caskType,
      defaultPrice: defaultPrice ?? this.defaultPrice,
      currency: currency ?? this.currency,
      sourceName: sourceName ?? this.sourceName,
      sourceUrl: sourceUrl ?? this.sourceUrl,
      fetchedAt: fetchedAt ?? this.fetchedAt,
      tastingNotes: tastingNotes ?? this.tastingNotes,
      companionSuggestions: companionSuggestions ?? this.companionSuggestions,
      globalScore: globalScore ?? this.globalScore,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (externalId.present) {
      map['external_id'] = Variable<String>(externalId.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (country.present) {
      map['country'] = Variable<String>(country.value);
    }
    if (region.present) {
      map['region'] = Variable<String>(region.value);
    }
    if (category.present) {
      map['category'] = Variable<String>(category.value);
    }
    if (distillery.present) {
      map['distillery'] = Variable<String>(distillery.value);
    }
    if (age.present) {
      map['age'] = Variable<int>(age.value);
    }
    if (abv.present) {
      map['abv'] = Variable<double>(abv.value);
    }
    if (caskType.present) {
      map['cask_type'] = Variable<String>(caskType.value);
    }
    if (defaultPrice.present) {
      map['default_price'] = Variable<double>(defaultPrice.value);
    }
    if (currency.present) {
      map['currency'] = Variable<String>(currency.value);
    }
    if (sourceName.present) {
      map['source_name'] = Variable<String>(sourceName.value);
    }
    if (sourceUrl.present) {
      map['source_url'] = Variable<String>(sourceUrl.value);
    }
    if (fetchedAt.present) {
      map['fetched_at'] = Variable<String>(fetchedAt.value);
    }
    if (tastingNotes.present) {
      map['tasting_notes'] = Variable<String>(tastingNotes.value);
    }
    if (companionSuggestions.present) {
      map['companion_suggestions'] = Variable<String>(
        companionSuggestions.value,
      );
    }
    if (globalScore.present) {
      map['global_score'] = Variable<double>(globalScore.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('WhiskiesCompanion(')
          ..write('id: $id, ')
          ..write('externalId: $externalId, ')
          ..write('name: $name, ')
          ..write('country: $country, ')
          ..write('region: $region, ')
          ..write('category: $category, ')
          ..write('distillery: $distillery, ')
          ..write('age: $age, ')
          ..write('abv: $abv, ')
          ..write('caskType: $caskType, ')
          ..write('defaultPrice: $defaultPrice, ')
          ..write('currency: $currency, ')
          ..write('sourceName: $sourceName, ')
          ..write('sourceUrl: $sourceUrl, ')
          ..write('fetchedAt: $fetchedAt, ')
          ..write('tastingNotes: $tastingNotes, ')
          ..write('companionSuggestions: $companionSuggestions, ')
          ..write('globalScore: $globalScore')
          ..write(')'))
        .toString();
  }
}

class $UserSettingsTable extends UserSettings
    with TableInfo<$UserSettingsTable, UserSetting> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $UserSettingsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _keyMeta = const VerificationMeta('key');
  @override
  late final GeneratedColumn<String> key = GeneratedColumn<String>(
    'key',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _valueMeta = const VerificationMeta('value');
  @override
  late final GeneratedColumn<String> value = GeneratedColumn<String>(
    'value',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [key, value];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'user_settings';
  @override
  VerificationContext validateIntegrity(
    Insertable<UserSetting> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('key')) {
      context.handle(
        _keyMeta,
        key.isAcceptableOrUnknown(data['key']!, _keyMeta),
      );
    } else if (isInserting) {
      context.missing(_keyMeta);
    }
    if (data.containsKey('value')) {
      context.handle(
        _valueMeta,
        value.isAcceptableOrUnknown(data['value']!, _valueMeta),
      );
    } else if (isInserting) {
      context.missing(_valueMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {key};
  @override
  UserSetting map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return UserSetting(
      key: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}key'],
      )!,
      value: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}value'],
      )!,
    );
  }

  @override
  $UserSettingsTable createAlias(String alias) {
    return $UserSettingsTable(attachedDatabase, alias);
  }
}

class UserSetting extends DataClass implements Insertable<UserSetting> {
  final String key;
  final String value;
  const UserSetting({required this.key, required this.value});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['key'] = Variable<String>(key);
    map['value'] = Variable<String>(value);
    return map;
  }

  UserSettingsCompanion toCompanion(bool nullToAbsent) {
    return UserSettingsCompanion(key: Value(key), value: Value(value));
  }

  factory UserSetting.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return UserSetting(
      key: serializer.fromJson<String>(json['key']),
      value: serializer.fromJson<String>(json['value']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'key': serializer.toJson<String>(key),
      'value': serializer.toJson<String>(value),
    };
  }

  UserSetting copyWith({String? key, String? value}) =>
      UserSetting(key: key ?? this.key, value: value ?? this.value);
  UserSetting copyWithCompanion(UserSettingsCompanion data) {
    return UserSetting(
      key: data.key.present ? data.key.value : this.key,
      value: data.value.present ? data.value.value : this.value,
    );
  }

  @override
  String toString() {
    return (StringBuffer('UserSetting(')
          ..write('key: $key, ')
          ..write('value: $value')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(key, value);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is UserSetting &&
          other.key == this.key &&
          other.value == this.value);
}

class UserSettingsCompanion extends UpdateCompanion<UserSetting> {
  final Value<String> key;
  final Value<String> value;
  final Value<int> rowid;
  const UserSettingsCompanion({
    this.key = const Value.absent(),
    this.value = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  UserSettingsCompanion.insert({
    required String key,
    required String value,
    this.rowid = const Value.absent(),
  }) : key = Value(key),
       value = Value(value);
  static Insertable<UserSetting> custom({
    Expression<String>? key,
    Expression<String>? value,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (key != null) 'key': key,
      if (value != null) 'value': value,
      if (rowid != null) 'rowid': rowid,
    });
  }

  UserSettingsCompanion copyWith({
    Value<String>? key,
    Value<String>? value,
    Value<int>? rowid,
  }) {
    return UserSettingsCompanion(
      key: key ?? this.key,
      value: value ?? this.value,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (key.present) {
      map['key'] = Variable<String>(key.value);
    }
    if (value.present) {
      map['value'] = Variable<String>(value.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('UserSettingsCompanion(')
          ..write('key: $key, ')
          ..write('value: $value, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $UserWhiskyScoresTable extends UserWhiskyScores
    with TableInfo<$UserWhiskyScoresTable, UserWhiskyScore> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $UserWhiskyScoresTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _whiskyIdMeta = const VerificationMeta(
    'whiskyId',
  );
  @override
  late final GeneratedColumn<int> whiskyId = GeneratedColumn<int>(
    'whisky_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _scoreMeta = const VerificationMeta('score');
  @override
  late final GeneratedColumn<int> score = GeneratedColumn<int>(
    'score',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _ratedAtMeta = const VerificationMeta(
    'ratedAt',
  );
  @override
  late final GeneratedColumn<String> ratedAt = GeneratedColumn<String>(
    'rated_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [whiskyId, score, ratedAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'user_whisky_scores';
  @override
  VerificationContext validateIntegrity(
    Insertable<UserWhiskyScore> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('whisky_id')) {
      context.handle(
        _whiskyIdMeta,
        whiskyId.isAcceptableOrUnknown(data['whisky_id']!, _whiskyIdMeta),
      );
    }
    if (data.containsKey('score')) {
      context.handle(
        _scoreMeta,
        score.isAcceptableOrUnknown(data['score']!, _scoreMeta),
      );
    } else if (isInserting) {
      context.missing(_scoreMeta);
    }
    if (data.containsKey('rated_at')) {
      context.handle(
        _ratedAtMeta,
        ratedAt.isAcceptableOrUnknown(data['rated_at']!, _ratedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_ratedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {whiskyId};
  @override
  UserWhiskyScore map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return UserWhiskyScore(
      whiskyId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}whisky_id'],
      )!,
      score: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}score'],
      )!,
      ratedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}rated_at'],
      )!,
    );
  }

  @override
  $UserWhiskyScoresTable createAlias(String alias) {
    return $UserWhiskyScoresTable(attachedDatabase, alias);
  }
}

class UserWhiskyScore extends DataClass implements Insertable<UserWhiskyScore> {
  final int whiskyId;
  final int score;
  final String ratedAt;
  const UserWhiskyScore({
    required this.whiskyId,
    required this.score,
    required this.ratedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['whisky_id'] = Variable<int>(whiskyId);
    map['score'] = Variable<int>(score);
    map['rated_at'] = Variable<String>(ratedAt);
    return map;
  }

  UserWhiskyScoresCompanion toCompanion(bool nullToAbsent) {
    return UserWhiskyScoresCompanion(
      whiskyId: Value(whiskyId),
      score: Value(score),
      ratedAt: Value(ratedAt),
    );
  }

  factory UserWhiskyScore.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return UserWhiskyScore(
      whiskyId: serializer.fromJson<int>(json['whiskyId']),
      score: serializer.fromJson<int>(json['score']),
      ratedAt: serializer.fromJson<String>(json['ratedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'whiskyId': serializer.toJson<int>(whiskyId),
      'score': serializer.toJson<int>(score),
      'ratedAt': serializer.toJson<String>(ratedAt),
    };
  }

  UserWhiskyScore copyWith({int? whiskyId, int? score, String? ratedAt}) =>
      UserWhiskyScore(
        whiskyId: whiskyId ?? this.whiskyId,
        score: score ?? this.score,
        ratedAt: ratedAt ?? this.ratedAt,
      );
  UserWhiskyScore copyWithCompanion(UserWhiskyScoresCompanion data) {
    return UserWhiskyScore(
      whiskyId: data.whiskyId.present ? data.whiskyId.value : this.whiskyId,
      score: data.score.present ? data.score.value : this.score,
      ratedAt: data.ratedAt.present ? data.ratedAt.value : this.ratedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('UserWhiskyScore(')
          ..write('whiskyId: $whiskyId, ')
          ..write('score: $score, ')
          ..write('ratedAt: $ratedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(whiskyId, score, ratedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is UserWhiskyScore &&
          other.whiskyId == this.whiskyId &&
          other.score == this.score &&
          other.ratedAt == this.ratedAt);
}

class UserWhiskyScoresCompanion extends UpdateCompanion<UserWhiskyScore> {
  final Value<int> whiskyId;
  final Value<int> score;
  final Value<String> ratedAt;
  const UserWhiskyScoresCompanion({
    this.whiskyId = const Value.absent(),
    this.score = const Value.absent(),
    this.ratedAt = const Value.absent(),
  });
  UserWhiskyScoresCompanion.insert({
    this.whiskyId = const Value.absent(),
    required int score,
    required String ratedAt,
  }) : score = Value(score),
       ratedAt = Value(ratedAt);
  static Insertable<UserWhiskyScore> custom({
    Expression<int>? whiskyId,
    Expression<int>? score,
    Expression<String>? ratedAt,
  }) {
    return RawValuesInsertable({
      if (whiskyId != null) 'whisky_id': whiskyId,
      if (score != null) 'score': score,
      if (ratedAt != null) 'rated_at': ratedAt,
    });
  }

  UserWhiskyScoresCompanion copyWith({
    Value<int>? whiskyId,
    Value<int>? score,
    Value<String>? ratedAt,
  }) {
    return UserWhiskyScoresCompanion(
      whiskyId: whiskyId ?? this.whiskyId,
      score: score ?? this.score,
      ratedAt: ratedAt ?? this.ratedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (whiskyId.present) {
      map['whisky_id'] = Variable<int>(whiskyId.value);
    }
    if (score.present) {
      map['score'] = Variable<int>(score.value);
    }
    if (ratedAt.present) {
      map['rated_at'] = Variable<String>(ratedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('UserWhiskyScoresCompanion(')
          ..write('whiskyId: $whiskyId, ')
          ..write('score: $score, ')
          ..write('ratedAt: $ratedAt')
          ..write(')'))
        .toString();
  }
}

class $FavoritesTable extends Favorites
    with TableInfo<$FavoritesTable, Favorite> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $FavoritesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _whiskyIdMeta = const VerificationMeta(
    'whiskyId',
  );
  @override
  late final GeneratedColumn<int> whiskyId = GeneratedColumn<int>(
    'whisky_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _addedAtMeta = const VerificationMeta(
    'addedAt',
  );
  @override
  late final GeneratedColumn<String> addedAt = GeneratedColumn<String>(
    'added_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [whiskyId, addedAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'favorites';
  @override
  VerificationContext validateIntegrity(
    Insertable<Favorite> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('whisky_id')) {
      context.handle(
        _whiskyIdMeta,
        whiskyId.isAcceptableOrUnknown(data['whisky_id']!, _whiskyIdMeta),
      );
    }
    if (data.containsKey('added_at')) {
      context.handle(
        _addedAtMeta,
        addedAt.isAcceptableOrUnknown(data['added_at']!, _addedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_addedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {whiskyId};
  @override
  Favorite map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Favorite(
      whiskyId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}whisky_id'],
      )!,
      addedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}added_at'],
      )!,
    );
  }

  @override
  $FavoritesTable createAlias(String alias) {
    return $FavoritesTable(attachedDatabase, alias);
  }
}

class Favorite extends DataClass implements Insertable<Favorite> {
  final int whiskyId;
  final String addedAt;
  const Favorite({required this.whiskyId, required this.addedAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['whisky_id'] = Variable<int>(whiskyId);
    map['added_at'] = Variable<String>(addedAt);
    return map;
  }

  FavoritesCompanion toCompanion(bool nullToAbsent) {
    return FavoritesCompanion(
      whiskyId: Value(whiskyId),
      addedAt: Value(addedAt),
    );
  }

  factory Favorite.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Favorite(
      whiskyId: serializer.fromJson<int>(json['whiskyId']),
      addedAt: serializer.fromJson<String>(json['addedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'whiskyId': serializer.toJson<int>(whiskyId),
      'addedAt': serializer.toJson<String>(addedAt),
    };
  }

  Favorite copyWith({int? whiskyId, String? addedAt}) => Favorite(
    whiskyId: whiskyId ?? this.whiskyId,
    addedAt: addedAt ?? this.addedAt,
  );
  Favorite copyWithCompanion(FavoritesCompanion data) {
    return Favorite(
      whiskyId: data.whiskyId.present ? data.whiskyId.value : this.whiskyId,
      addedAt: data.addedAt.present ? data.addedAt.value : this.addedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Favorite(')
          ..write('whiskyId: $whiskyId, ')
          ..write('addedAt: $addedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(whiskyId, addedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Favorite &&
          other.whiskyId == this.whiskyId &&
          other.addedAt == this.addedAt);
}

class FavoritesCompanion extends UpdateCompanion<Favorite> {
  final Value<int> whiskyId;
  final Value<String> addedAt;
  const FavoritesCompanion({
    this.whiskyId = const Value.absent(),
    this.addedAt = const Value.absent(),
  });
  FavoritesCompanion.insert({
    this.whiskyId = const Value.absent(),
    required String addedAt,
  }) : addedAt = Value(addedAt);
  static Insertable<Favorite> custom({
    Expression<int>? whiskyId,
    Expression<String>? addedAt,
  }) {
    return RawValuesInsertable({
      if (whiskyId != null) 'whisky_id': whiskyId,
      if (addedAt != null) 'added_at': addedAt,
    });
  }

  FavoritesCompanion copyWith({Value<int>? whiskyId, Value<String>? addedAt}) {
    return FavoritesCompanion(
      whiskyId: whiskyId ?? this.whiskyId,
      addedAt: addedAt ?? this.addedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (whiskyId.present) {
      map['whisky_id'] = Variable<int>(whiskyId.value);
    }
    if (addedAt.present) {
      map['added_at'] = Variable<String>(addedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('FavoritesCompanion(')
          ..write('whiskyId: $whiskyId, ')
          ..write('addedAt: $addedAt')
          ..write(')'))
        .toString();
  }
}

class $UserNotesTable extends UserNotes
    with TableInfo<$UserNotesTable, UserNote> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $UserNotesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _whiskyIdMeta = const VerificationMeta(
    'whiskyId',
  );
  @override
  late final GeneratedColumn<int> whiskyId = GeneratedColumn<int>(
    'whisky_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _noteMeta = const VerificationMeta('note');
  @override
  late final GeneratedColumn<String> note = GeneratedColumn<String>(
    'note',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta(
    'updatedAt',
  );
  @override
  late final GeneratedColumn<String> updatedAt = GeneratedColumn<String>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [whiskyId, note, updatedAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'user_notes';
  @override
  VerificationContext validateIntegrity(
    Insertable<UserNote> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('whisky_id')) {
      context.handle(
        _whiskyIdMeta,
        whiskyId.isAcceptableOrUnknown(data['whisky_id']!, _whiskyIdMeta),
      );
    }
    if (data.containsKey('note')) {
      context.handle(
        _noteMeta,
        note.isAcceptableOrUnknown(data['note']!, _noteMeta),
      );
    } else if (isInserting) {
      context.missing(_noteMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(
        _updatedAtMeta,
        updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {whiskyId};
  @override
  UserNote map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return UserNote(
      whiskyId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}whisky_id'],
      )!,
      note: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}note'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}updated_at'],
      )!,
    );
  }

  @override
  $UserNotesTable createAlias(String alias) {
    return $UserNotesTable(attachedDatabase, alias);
  }
}

class UserNote extends DataClass implements Insertable<UserNote> {
  final int whiskyId;
  final String note;
  final String updatedAt;
  const UserNote({
    required this.whiskyId,
    required this.note,
    required this.updatedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['whisky_id'] = Variable<int>(whiskyId);
    map['note'] = Variable<String>(note);
    map['updated_at'] = Variable<String>(updatedAt);
    return map;
  }

  UserNotesCompanion toCompanion(bool nullToAbsent) {
    return UserNotesCompanion(
      whiskyId: Value(whiskyId),
      note: Value(note),
      updatedAt: Value(updatedAt),
    );
  }

  factory UserNote.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return UserNote(
      whiskyId: serializer.fromJson<int>(json['whiskyId']),
      note: serializer.fromJson<String>(json['note']),
      updatedAt: serializer.fromJson<String>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'whiskyId': serializer.toJson<int>(whiskyId),
      'note': serializer.toJson<String>(note),
      'updatedAt': serializer.toJson<String>(updatedAt),
    };
  }

  UserNote copyWith({int? whiskyId, String? note, String? updatedAt}) =>
      UserNote(
        whiskyId: whiskyId ?? this.whiskyId,
        note: note ?? this.note,
        updatedAt: updatedAt ?? this.updatedAt,
      );
  UserNote copyWithCompanion(UserNotesCompanion data) {
    return UserNote(
      whiskyId: data.whiskyId.present ? data.whiskyId.value : this.whiskyId,
      note: data.note.present ? data.note.value : this.note,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('UserNote(')
          ..write('whiskyId: $whiskyId, ')
          ..write('note: $note, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(whiskyId, note, updatedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is UserNote &&
          other.whiskyId == this.whiskyId &&
          other.note == this.note &&
          other.updatedAt == this.updatedAt);
}

class UserNotesCompanion extends UpdateCompanion<UserNote> {
  final Value<int> whiskyId;
  final Value<String> note;
  final Value<String> updatedAt;
  const UserNotesCompanion({
    this.whiskyId = const Value.absent(),
    this.note = const Value.absent(),
    this.updatedAt = const Value.absent(),
  });
  UserNotesCompanion.insert({
    this.whiskyId = const Value.absent(),
    required String note,
    required String updatedAt,
  }) : note = Value(note),
       updatedAt = Value(updatedAt);
  static Insertable<UserNote> custom({
    Expression<int>? whiskyId,
    Expression<String>? note,
    Expression<String>? updatedAt,
  }) {
    return RawValuesInsertable({
      if (whiskyId != null) 'whisky_id': whiskyId,
      if (note != null) 'note': note,
      if (updatedAt != null) 'updated_at': updatedAt,
    });
  }

  UserNotesCompanion copyWith({
    Value<int>? whiskyId,
    Value<String>? note,
    Value<String>? updatedAt,
  }) {
    return UserNotesCompanion(
      whiskyId: whiskyId ?? this.whiskyId,
      note: note ?? this.note,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (whiskyId.present) {
      map['whisky_id'] = Variable<int>(whiskyId.value);
    }
    if (note.present) {
      map['note'] = Variable<String>(note.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<String>(updatedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('UserNotesCompanion(')
          ..write('whiskyId: $whiskyId, ')
          ..write('note: $note, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }
}

class $WhiskyPricesTable extends WhiskyPrices
    with TableInfo<$WhiskyPricesTable, WhiskyPrice> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $WhiskyPricesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _whiskyIdMeta = const VerificationMeta(
    'whiskyId',
  );
  @override
  late final GeneratedColumn<int> whiskyId = GeneratedColumn<int>(
    'whisky_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sourceNameMeta = const VerificationMeta(
    'sourceName',
  );
  @override
  late final GeneratedColumn<String> sourceName = GeneratedColumn<String>(
    'source_name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _priceMeta = const VerificationMeta('price');
  @override
  late final GeneratedColumn<double> price = GeneratedColumn<double>(
    'price',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _currencyMeta = const VerificationMeta(
    'currency',
  );
  @override
  late final GeneratedColumn<String> currency = GeneratedColumn<String>(
    'currency',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _countryMeta = const VerificationMeta(
    'country',
  );
  @override
  late final GeneratedColumn<String> country = GeneratedColumn<String>(
    'country',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sourceUrlMeta = const VerificationMeta(
    'sourceUrl',
  );
  @override
  late final GeneratedColumn<String> sourceUrl = GeneratedColumn<String>(
    'source_url',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _fetchedAtMeta = const VerificationMeta(
    'fetchedAt',
  );
  @override
  late final GeneratedColumn<String> fetchedAt = GeneratedColumn<String>(
    'fetched_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _isManualMeta = const VerificationMeta(
    'isManual',
  );
  @override
  late final GeneratedColumn<bool> isManual = GeneratedColumn<bool>(
    'is_manual',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_manual" IN (0, 1))',
    ),
    defaultValue: const Constant(false),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    whiskyId,
    sourceName,
    price,
    currency,
    country,
    sourceUrl,
    fetchedAt,
    isManual,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'whisky_prices';
  @override
  VerificationContext validateIntegrity(
    Insertable<WhiskyPrice> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('whisky_id')) {
      context.handle(
        _whiskyIdMeta,
        whiskyId.isAcceptableOrUnknown(data['whisky_id']!, _whiskyIdMeta),
      );
    } else if (isInserting) {
      context.missing(_whiskyIdMeta);
    }
    if (data.containsKey('source_name')) {
      context.handle(
        _sourceNameMeta,
        sourceName.isAcceptableOrUnknown(data['source_name']!, _sourceNameMeta),
      );
    } else if (isInserting) {
      context.missing(_sourceNameMeta);
    }
    if (data.containsKey('price')) {
      context.handle(
        _priceMeta,
        price.isAcceptableOrUnknown(data['price']!, _priceMeta),
      );
    } else if (isInserting) {
      context.missing(_priceMeta);
    }
    if (data.containsKey('currency')) {
      context.handle(
        _currencyMeta,
        currency.isAcceptableOrUnknown(data['currency']!, _currencyMeta),
      );
    } else if (isInserting) {
      context.missing(_currencyMeta);
    }
    if (data.containsKey('country')) {
      context.handle(
        _countryMeta,
        country.isAcceptableOrUnknown(data['country']!, _countryMeta),
      );
    } else if (isInserting) {
      context.missing(_countryMeta);
    }
    if (data.containsKey('source_url')) {
      context.handle(
        _sourceUrlMeta,
        sourceUrl.isAcceptableOrUnknown(data['source_url']!, _sourceUrlMeta),
      );
    } else if (isInserting) {
      context.missing(_sourceUrlMeta);
    }
    if (data.containsKey('fetched_at')) {
      context.handle(
        _fetchedAtMeta,
        fetchedAt.isAcceptableOrUnknown(data['fetched_at']!, _fetchedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_fetchedAtMeta);
    }
    if (data.containsKey('is_manual')) {
      context.handle(
        _isManualMeta,
        isManual.isAcceptableOrUnknown(data['is_manual']!, _isManualMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  WhiskyPrice map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return WhiskyPrice(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      whiskyId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}whisky_id'],
      )!,
      sourceName: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source_name'],
      )!,
      price: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}price'],
      )!,
      currency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}currency'],
      )!,
      country: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}country'],
      )!,
      sourceUrl: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source_url'],
      )!,
      fetchedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}fetched_at'],
      )!,
      isManual: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_manual'],
      )!,
    );
  }

  @override
  $WhiskyPricesTable createAlias(String alias) {
    return $WhiskyPricesTable(attachedDatabase, alias);
  }
}

class WhiskyPrice extends DataClass implements Insertable<WhiskyPrice> {
  final int id;
  final int whiskyId;
  final String sourceName;
  final double price;
  final String currency;
  final String country;
  final String sourceUrl;
  final String fetchedAt;
  final bool isManual;
  const WhiskyPrice({
    required this.id,
    required this.whiskyId,
    required this.sourceName,
    required this.price,
    required this.currency,
    required this.country,
    required this.sourceUrl,
    required this.fetchedAt,
    required this.isManual,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['whisky_id'] = Variable<int>(whiskyId);
    map['source_name'] = Variable<String>(sourceName);
    map['price'] = Variable<double>(price);
    map['currency'] = Variable<String>(currency);
    map['country'] = Variable<String>(country);
    map['source_url'] = Variable<String>(sourceUrl);
    map['fetched_at'] = Variable<String>(fetchedAt);
    map['is_manual'] = Variable<bool>(isManual);
    return map;
  }

  WhiskyPricesCompanion toCompanion(bool nullToAbsent) {
    return WhiskyPricesCompanion(
      id: Value(id),
      whiskyId: Value(whiskyId),
      sourceName: Value(sourceName),
      price: Value(price),
      currency: Value(currency),
      country: Value(country),
      sourceUrl: Value(sourceUrl),
      fetchedAt: Value(fetchedAt),
      isManual: Value(isManual),
    );
  }

  factory WhiskyPrice.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return WhiskyPrice(
      id: serializer.fromJson<int>(json['id']),
      whiskyId: serializer.fromJson<int>(json['whiskyId']),
      sourceName: serializer.fromJson<String>(json['sourceName']),
      price: serializer.fromJson<double>(json['price']),
      currency: serializer.fromJson<String>(json['currency']),
      country: serializer.fromJson<String>(json['country']),
      sourceUrl: serializer.fromJson<String>(json['sourceUrl']),
      fetchedAt: serializer.fromJson<String>(json['fetchedAt']),
      isManual: serializer.fromJson<bool>(json['isManual']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'whiskyId': serializer.toJson<int>(whiskyId),
      'sourceName': serializer.toJson<String>(sourceName),
      'price': serializer.toJson<double>(price),
      'currency': serializer.toJson<String>(currency),
      'country': serializer.toJson<String>(country),
      'sourceUrl': serializer.toJson<String>(sourceUrl),
      'fetchedAt': serializer.toJson<String>(fetchedAt),
      'isManual': serializer.toJson<bool>(isManual),
    };
  }

  WhiskyPrice copyWith({
    int? id,
    int? whiskyId,
    String? sourceName,
    double? price,
    String? currency,
    String? country,
    String? sourceUrl,
    String? fetchedAt,
    bool? isManual,
  }) => WhiskyPrice(
    id: id ?? this.id,
    whiskyId: whiskyId ?? this.whiskyId,
    sourceName: sourceName ?? this.sourceName,
    price: price ?? this.price,
    currency: currency ?? this.currency,
    country: country ?? this.country,
    sourceUrl: sourceUrl ?? this.sourceUrl,
    fetchedAt: fetchedAt ?? this.fetchedAt,
    isManual: isManual ?? this.isManual,
  );
  WhiskyPrice copyWithCompanion(WhiskyPricesCompanion data) {
    return WhiskyPrice(
      id: data.id.present ? data.id.value : this.id,
      whiskyId: data.whiskyId.present ? data.whiskyId.value : this.whiskyId,
      sourceName: data.sourceName.present
          ? data.sourceName.value
          : this.sourceName,
      price: data.price.present ? data.price.value : this.price,
      currency: data.currency.present ? data.currency.value : this.currency,
      country: data.country.present ? data.country.value : this.country,
      sourceUrl: data.sourceUrl.present ? data.sourceUrl.value : this.sourceUrl,
      fetchedAt: data.fetchedAt.present ? data.fetchedAt.value : this.fetchedAt,
      isManual: data.isManual.present ? data.isManual.value : this.isManual,
    );
  }

  @override
  String toString() {
    return (StringBuffer('WhiskyPrice(')
          ..write('id: $id, ')
          ..write('whiskyId: $whiskyId, ')
          ..write('sourceName: $sourceName, ')
          ..write('price: $price, ')
          ..write('currency: $currency, ')
          ..write('country: $country, ')
          ..write('sourceUrl: $sourceUrl, ')
          ..write('fetchedAt: $fetchedAt, ')
          ..write('isManual: $isManual')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    whiskyId,
    sourceName,
    price,
    currency,
    country,
    sourceUrl,
    fetchedAt,
    isManual,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is WhiskyPrice &&
          other.id == this.id &&
          other.whiskyId == this.whiskyId &&
          other.sourceName == this.sourceName &&
          other.price == this.price &&
          other.currency == this.currency &&
          other.country == this.country &&
          other.sourceUrl == this.sourceUrl &&
          other.fetchedAt == this.fetchedAt &&
          other.isManual == this.isManual);
}

class WhiskyPricesCompanion extends UpdateCompanion<WhiskyPrice> {
  final Value<int> id;
  final Value<int> whiskyId;
  final Value<String> sourceName;
  final Value<double> price;
  final Value<String> currency;
  final Value<String> country;
  final Value<String> sourceUrl;
  final Value<String> fetchedAt;
  final Value<bool> isManual;
  const WhiskyPricesCompanion({
    this.id = const Value.absent(),
    this.whiskyId = const Value.absent(),
    this.sourceName = const Value.absent(),
    this.price = const Value.absent(),
    this.currency = const Value.absent(),
    this.country = const Value.absent(),
    this.sourceUrl = const Value.absent(),
    this.fetchedAt = const Value.absent(),
    this.isManual = const Value.absent(),
  });
  WhiskyPricesCompanion.insert({
    this.id = const Value.absent(),
    required int whiskyId,
    required String sourceName,
    required double price,
    required String currency,
    required String country,
    required String sourceUrl,
    required String fetchedAt,
    this.isManual = const Value.absent(),
  }) : whiskyId = Value(whiskyId),
       sourceName = Value(sourceName),
       price = Value(price),
       currency = Value(currency),
       country = Value(country),
       sourceUrl = Value(sourceUrl),
       fetchedAt = Value(fetchedAt);
  static Insertable<WhiskyPrice> custom({
    Expression<int>? id,
    Expression<int>? whiskyId,
    Expression<String>? sourceName,
    Expression<double>? price,
    Expression<String>? currency,
    Expression<String>? country,
    Expression<String>? sourceUrl,
    Expression<String>? fetchedAt,
    Expression<bool>? isManual,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (whiskyId != null) 'whisky_id': whiskyId,
      if (sourceName != null) 'source_name': sourceName,
      if (price != null) 'price': price,
      if (currency != null) 'currency': currency,
      if (country != null) 'country': country,
      if (sourceUrl != null) 'source_url': sourceUrl,
      if (fetchedAt != null) 'fetched_at': fetchedAt,
      if (isManual != null) 'is_manual': isManual,
    });
  }

  WhiskyPricesCompanion copyWith({
    Value<int>? id,
    Value<int>? whiskyId,
    Value<String>? sourceName,
    Value<double>? price,
    Value<String>? currency,
    Value<String>? country,
    Value<String>? sourceUrl,
    Value<String>? fetchedAt,
    Value<bool>? isManual,
  }) {
    return WhiskyPricesCompanion(
      id: id ?? this.id,
      whiskyId: whiskyId ?? this.whiskyId,
      sourceName: sourceName ?? this.sourceName,
      price: price ?? this.price,
      currency: currency ?? this.currency,
      country: country ?? this.country,
      sourceUrl: sourceUrl ?? this.sourceUrl,
      fetchedAt: fetchedAt ?? this.fetchedAt,
      isManual: isManual ?? this.isManual,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (whiskyId.present) {
      map['whisky_id'] = Variable<int>(whiskyId.value);
    }
    if (sourceName.present) {
      map['source_name'] = Variable<String>(sourceName.value);
    }
    if (price.present) {
      map['price'] = Variable<double>(price.value);
    }
    if (currency.present) {
      map['currency'] = Variable<String>(currency.value);
    }
    if (country.present) {
      map['country'] = Variable<String>(country.value);
    }
    if (sourceUrl.present) {
      map['source_url'] = Variable<String>(sourceUrl.value);
    }
    if (fetchedAt.present) {
      map['fetched_at'] = Variable<String>(fetchedAt.value);
    }
    if (isManual.present) {
      map['is_manual'] = Variable<bool>(isManual.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('WhiskyPricesCompanion(')
          ..write('id: $id, ')
          ..write('whiskyId: $whiskyId, ')
          ..write('sourceName: $sourceName, ')
          ..write('price: $price, ')
          ..write('currency: $currency, ')
          ..write('country: $country, ')
          ..write('sourceUrl: $sourceUrl, ')
          ..write('fetchedAt: $fetchedAt, ')
          ..write('isManual: $isManual')
          ..write(')'))
        .toString();
  }
}

class $ExternalSourcesTable extends ExternalSources
    with TableInfo<$ExternalSourcesTable, ExternalSource> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ExternalSourcesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _whiskyIdMeta = const VerificationMeta(
    'whiskyId',
  );
  @override
  late final GeneratedColumn<int> whiskyId = GeneratedColumn<int>(
    'whisky_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sourceNameMeta = const VerificationMeta(
    'sourceName',
  );
  @override
  late final GeneratedColumn<String> sourceName = GeneratedColumn<String>(
    'source_name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sourceUrlMeta = const VerificationMeta(
    'sourceUrl',
  );
  @override
  late final GeneratedColumn<String> sourceUrl = GeneratedColumn<String>(
    'source_url',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _externalIdMeta = const VerificationMeta(
    'externalId',
  );
  @override
  late final GeneratedColumn<String> externalId = GeneratedColumn<String>(
    'external_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _fetchedAtMeta = const VerificationMeta(
    'fetchedAt',
  );
  @override
  late final GeneratedColumn<String> fetchedAt = GeneratedColumn<String>(
    'fetched_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    whiskyId,
    sourceName,
    sourceUrl,
    externalId,
    fetchedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'external_sources';
  @override
  VerificationContext validateIntegrity(
    Insertable<ExternalSource> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('whisky_id')) {
      context.handle(
        _whiskyIdMeta,
        whiskyId.isAcceptableOrUnknown(data['whisky_id']!, _whiskyIdMeta),
      );
    } else if (isInserting) {
      context.missing(_whiskyIdMeta);
    }
    if (data.containsKey('source_name')) {
      context.handle(
        _sourceNameMeta,
        sourceName.isAcceptableOrUnknown(data['source_name']!, _sourceNameMeta),
      );
    } else if (isInserting) {
      context.missing(_sourceNameMeta);
    }
    if (data.containsKey('source_url')) {
      context.handle(
        _sourceUrlMeta,
        sourceUrl.isAcceptableOrUnknown(data['source_url']!, _sourceUrlMeta),
      );
    } else if (isInserting) {
      context.missing(_sourceUrlMeta);
    }
    if (data.containsKey('external_id')) {
      context.handle(
        _externalIdMeta,
        externalId.isAcceptableOrUnknown(data['external_id']!, _externalIdMeta),
      );
    } else if (isInserting) {
      context.missing(_externalIdMeta);
    }
    if (data.containsKey('fetched_at')) {
      context.handle(
        _fetchedAtMeta,
        fetchedAt.isAcceptableOrUnknown(data['fetched_at']!, _fetchedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_fetchedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  ExternalSource map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ExternalSource(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      whiskyId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}whisky_id'],
      )!,
      sourceName: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source_name'],
      )!,
      sourceUrl: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source_url'],
      )!,
      externalId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}external_id'],
      )!,
      fetchedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}fetched_at'],
      )!,
    );
  }

  @override
  $ExternalSourcesTable createAlias(String alias) {
    return $ExternalSourcesTable(attachedDatabase, alias);
  }
}

class ExternalSource extends DataClass implements Insertable<ExternalSource> {
  final int id;
  final int whiskyId;
  final String sourceName;
  final String sourceUrl;
  final String externalId;
  final String fetchedAt;
  const ExternalSource({
    required this.id,
    required this.whiskyId,
    required this.sourceName,
    required this.sourceUrl,
    required this.externalId,
    required this.fetchedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['whisky_id'] = Variable<int>(whiskyId);
    map['source_name'] = Variable<String>(sourceName);
    map['source_url'] = Variable<String>(sourceUrl);
    map['external_id'] = Variable<String>(externalId);
    map['fetched_at'] = Variable<String>(fetchedAt);
    return map;
  }

  ExternalSourcesCompanion toCompanion(bool nullToAbsent) {
    return ExternalSourcesCompanion(
      id: Value(id),
      whiskyId: Value(whiskyId),
      sourceName: Value(sourceName),
      sourceUrl: Value(sourceUrl),
      externalId: Value(externalId),
      fetchedAt: Value(fetchedAt),
    );
  }

  factory ExternalSource.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ExternalSource(
      id: serializer.fromJson<int>(json['id']),
      whiskyId: serializer.fromJson<int>(json['whiskyId']),
      sourceName: serializer.fromJson<String>(json['sourceName']),
      sourceUrl: serializer.fromJson<String>(json['sourceUrl']),
      externalId: serializer.fromJson<String>(json['externalId']),
      fetchedAt: serializer.fromJson<String>(json['fetchedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'whiskyId': serializer.toJson<int>(whiskyId),
      'sourceName': serializer.toJson<String>(sourceName),
      'sourceUrl': serializer.toJson<String>(sourceUrl),
      'externalId': serializer.toJson<String>(externalId),
      'fetchedAt': serializer.toJson<String>(fetchedAt),
    };
  }

  ExternalSource copyWith({
    int? id,
    int? whiskyId,
    String? sourceName,
    String? sourceUrl,
    String? externalId,
    String? fetchedAt,
  }) => ExternalSource(
    id: id ?? this.id,
    whiskyId: whiskyId ?? this.whiskyId,
    sourceName: sourceName ?? this.sourceName,
    sourceUrl: sourceUrl ?? this.sourceUrl,
    externalId: externalId ?? this.externalId,
    fetchedAt: fetchedAt ?? this.fetchedAt,
  );
  ExternalSource copyWithCompanion(ExternalSourcesCompanion data) {
    return ExternalSource(
      id: data.id.present ? data.id.value : this.id,
      whiskyId: data.whiskyId.present ? data.whiskyId.value : this.whiskyId,
      sourceName: data.sourceName.present
          ? data.sourceName.value
          : this.sourceName,
      sourceUrl: data.sourceUrl.present ? data.sourceUrl.value : this.sourceUrl,
      externalId: data.externalId.present
          ? data.externalId.value
          : this.externalId,
      fetchedAt: data.fetchedAt.present ? data.fetchedAt.value : this.fetchedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ExternalSource(')
          ..write('id: $id, ')
          ..write('whiskyId: $whiskyId, ')
          ..write('sourceName: $sourceName, ')
          ..write('sourceUrl: $sourceUrl, ')
          ..write('externalId: $externalId, ')
          ..write('fetchedAt: $fetchedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, whiskyId, sourceName, sourceUrl, externalId, fetchedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ExternalSource &&
          other.id == this.id &&
          other.whiskyId == this.whiskyId &&
          other.sourceName == this.sourceName &&
          other.sourceUrl == this.sourceUrl &&
          other.externalId == this.externalId &&
          other.fetchedAt == this.fetchedAt);
}

class ExternalSourcesCompanion extends UpdateCompanion<ExternalSource> {
  final Value<int> id;
  final Value<int> whiskyId;
  final Value<String> sourceName;
  final Value<String> sourceUrl;
  final Value<String> externalId;
  final Value<String> fetchedAt;
  const ExternalSourcesCompanion({
    this.id = const Value.absent(),
    this.whiskyId = const Value.absent(),
    this.sourceName = const Value.absent(),
    this.sourceUrl = const Value.absent(),
    this.externalId = const Value.absent(),
    this.fetchedAt = const Value.absent(),
  });
  ExternalSourcesCompanion.insert({
    this.id = const Value.absent(),
    required int whiskyId,
    required String sourceName,
    required String sourceUrl,
    required String externalId,
    required String fetchedAt,
  }) : whiskyId = Value(whiskyId),
       sourceName = Value(sourceName),
       sourceUrl = Value(sourceUrl),
       externalId = Value(externalId),
       fetchedAt = Value(fetchedAt);
  static Insertable<ExternalSource> custom({
    Expression<int>? id,
    Expression<int>? whiskyId,
    Expression<String>? sourceName,
    Expression<String>? sourceUrl,
    Expression<String>? externalId,
    Expression<String>? fetchedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (whiskyId != null) 'whisky_id': whiskyId,
      if (sourceName != null) 'source_name': sourceName,
      if (sourceUrl != null) 'source_url': sourceUrl,
      if (externalId != null) 'external_id': externalId,
      if (fetchedAt != null) 'fetched_at': fetchedAt,
    });
  }

  ExternalSourcesCompanion copyWith({
    Value<int>? id,
    Value<int>? whiskyId,
    Value<String>? sourceName,
    Value<String>? sourceUrl,
    Value<String>? externalId,
    Value<String>? fetchedAt,
  }) {
    return ExternalSourcesCompanion(
      id: id ?? this.id,
      whiskyId: whiskyId ?? this.whiskyId,
      sourceName: sourceName ?? this.sourceName,
      sourceUrl: sourceUrl ?? this.sourceUrl,
      externalId: externalId ?? this.externalId,
      fetchedAt: fetchedAt ?? this.fetchedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (whiskyId.present) {
      map['whisky_id'] = Variable<int>(whiskyId.value);
    }
    if (sourceName.present) {
      map['source_name'] = Variable<String>(sourceName.value);
    }
    if (sourceUrl.present) {
      map['source_url'] = Variable<String>(sourceUrl.value);
    }
    if (externalId.present) {
      map['external_id'] = Variable<String>(externalId.value);
    }
    if (fetchedAt.present) {
      map['fetched_at'] = Variable<String>(fetchedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ExternalSourcesCompanion(')
          ..write('id: $id, ')
          ..write('whiskyId: $whiskyId, ')
          ..write('sourceName: $sourceName, ')
          ..write('sourceUrl: $sourceUrl, ')
          ..write('externalId: $externalId, ')
          ..write('fetchedAt: $fetchedAt')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $WhiskiesTable whiskies = $WhiskiesTable(this);
  late final $UserSettingsTable userSettings = $UserSettingsTable(this);
  late final $UserWhiskyScoresTable userWhiskyScores = $UserWhiskyScoresTable(
    this,
  );
  late final $FavoritesTable favorites = $FavoritesTable(this);
  late final $UserNotesTable userNotes = $UserNotesTable(this);
  late final $WhiskyPricesTable whiskyPrices = $WhiskyPricesTable(this);
  late final $ExternalSourcesTable externalSources = $ExternalSourcesTable(
    this,
  );
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    whiskies,
    userSettings,
    userWhiskyScores,
    favorites,
    userNotes,
    whiskyPrices,
    externalSources,
  ];
}

typedef $$WhiskiesTableCreateCompanionBuilder =
    WhiskiesCompanion Function({
      Value<int> id,
      Value<String?> externalId,
      required String name,
      Value<String?> country,
      Value<String?> region,
      Value<String?> category,
      Value<String?> distillery,
      Value<int?> age,
      Value<double?> abv,
      Value<String?> caskType,
      Value<double?> defaultPrice,
      Value<String?> currency,
      Value<String?> sourceName,
      Value<String?> sourceUrl,
      Value<String?> fetchedAt,
      Value<String> tastingNotes,
      Value<String> companionSuggestions,
      Value<double?> globalScore,
    });
typedef $$WhiskiesTableUpdateCompanionBuilder =
    WhiskiesCompanion Function({
      Value<int> id,
      Value<String?> externalId,
      Value<String> name,
      Value<String?> country,
      Value<String?> region,
      Value<String?> category,
      Value<String?> distillery,
      Value<int?> age,
      Value<double?> abv,
      Value<String?> caskType,
      Value<double?> defaultPrice,
      Value<String?> currency,
      Value<String?> sourceName,
      Value<String?> sourceUrl,
      Value<String?> fetchedAt,
      Value<String> tastingNotes,
      Value<String> companionSuggestions,
      Value<double?> globalScore,
    });

class $$WhiskiesTableFilterComposer
    extends Composer<_$AppDatabase, $WhiskiesTable> {
  $$WhiskiesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get externalId => $composableBuilder(
    column: $table.externalId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get country => $composableBuilder(
    column: $table.country,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get region => $composableBuilder(
    column: $table.region,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get category => $composableBuilder(
    column: $table.category,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get distillery => $composableBuilder(
    column: $table.distillery,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get age => $composableBuilder(
    column: $table.age,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get abv => $composableBuilder(
    column: $table.abv,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get caskType => $composableBuilder(
    column: $table.caskType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get defaultPrice => $composableBuilder(
    column: $table.defaultPrice,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get currency => $composableBuilder(
    column: $table.currency,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sourceName => $composableBuilder(
    column: $table.sourceName,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sourceUrl => $composableBuilder(
    column: $table.sourceUrl,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get fetchedAt => $composableBuilder(
    column: $table.fetchedAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get tastingNotes => $composableBuilder(
    column: $table.tastingNotes,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get companionSuggestions => $composableBuilder(
    column: $table.companionSuggestions,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get globalScore => $composableBuilder(
    column: $table.globalScore,
    builder: (column) => ColumnFilters(column),
  );
}

class $$WhiskiesTableOrderingComposer
    extends Composer<_$AppDatabase, $WhiskiesTable> {
  $$WhiskiesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get externalId => $composableBuilder(
    column: $table.externalId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get country => $composableBuilder(
    column: $table.country,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get region => $composableBuilder(
    column: $table.region,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get category => $composableBuilder(
    column: $table.category,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get distillery => $composableBuilder(
    column: $table.distillery,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get age => $composableBuilder(
    column: $table.age,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get abv => $composableBuilder(
    column: $table.abv,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get caskType => $composableBuilder(
    column: $table.caskType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get defaultPrice => $composableBuilder(
    column: $table.defaultPrice,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get currency => $composableBuilder(
    column: $table.currency,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sourceName => $composableBuilder(
    column: $table.sourceName,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sourceUrl => $composableBuilder(
    column: $table.sourceUrl,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get fetchedAt => $composableBuilder(
    column: $table.fetchedAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get tastingNotes => $composableBuilder(
    column: $table.tastingNotes,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get companionSuggestions => $composableBuilder(
    column: $table.companionSuggestions,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get globalScore => $composableBuilder(
    column: $table.globalScore,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$WhiskiesTableAnnotationComposer
    extends Composer<_$AppDatabase, $WhiskiesTable> {
  $$WhiskiesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get externalId => $composableBuilder(
    column: $table.externalId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<String> get country =>
      $composableBuilder(column: $table.country, builder: (column) => column);

  GeneratedColumn<String> get region =>
      $composableBuilder(column: $table.region, builder: (column) => column);

  GeneratedColumn<String> get category =>
      $composableBuilder(column: $table.category, builder: (column) => column);

  GeneratedColumn<String> get distillery => $composableBuilder(
    column: $table.distillery,
    builder: (column) => column,
  );

  GeneratedColumn<int> get age =>
      $composableBuilder(column: $table.age, builder: (column) => column);

  GeneratedColumn<double> get abv =>
      $composableBuilder(column: $table.abv, builder: (column) => column);

  GeneratedColumn<String> get caskType =>
      $composableBuilder(column: $table.caskType, builder: (column) => column);

  GeneratedColumn<double> get defaultPrice => $composableBuilder(
    column: $table.defaultPrice,
    builder: (column) => column,
  );

  GeneratedColumn<String> get currency =>
      $composableBuilder(column: $table.currency, builder: (column) => column);

  GeneratedColumn<String> get sourceName => $composableBuilder(
    column: $table.sourceName,
    builder: (column) => column,
  );

  GeneratedColumn<String> get sourceUrl =>
      $composableBuilder(column: $table.sourceUrl, builder: (column) => column);

  GeneratedColumn<String> get fetchedAt =>
      $composableBuilder(column: $table.fetchedAt, builder: (column) => column);

  GeneratedColumn<String> get tastingNotes => $composableBuilder(
    column: $table.tastingNotes,
    builder: (column) => column,
  );

  GeneratedColumn<String> get companionSuggestions => $composableBuilder(
    column: $table.companionSuggestions,
    builder: (column) => column,
  );

  GeneratedColumn<double> get globalScore => $composableBuilder(
    column: $table.globalScore,
    builder: (column) => column,
  );
}

class $$WhiskiesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $WhiskiesTable,
          WhiskyEntity,
          $$WhiskiesTableFilterComposer,
          $$WhiskiesTableOrderingComposer,
          $$WhiskiesTableAnnotationComposer,
          $$WhiskiesTableCreateCompanionBuilder,
          $$WhiskiesTableUpdateCompanionBuilder,
          (
            WhiskyEntity,
            BaseReferences<_$AppDatabase, $WhiskiesTable, WhiskyEntity>,
          ),
          WhiskyEntity,
          PrefetchHooks Function()
        > {
  $$WhiskiesTableTableManager(_$AppDatabase db, $WhiskiesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$WhiskiesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$WhiskiesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$WhiskiesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String?> externalId = const Value.absent(),
                Value<String> name = const Value.absent(),
                Value<String?> country = const Value.absent(),
                Value<String?> region = const Value.absent(),
                Value<String?> category = const Value.absent(),
                Value<String?> distillery = const Value.absent(),
                Value<int?> age = const Value.absent(),
                Value<double?> abv = const Value.absent(),
                Value<String?> caskType = const Value.absent(),
                Value<double?> defaultPrice = const Value.absent(),
                Value<String?> currency = const Value.absent(),
                Value<String?> sourceName = const Value.absent(),
                Value<String?> sourceUrl = const Value.absent(),
                Value<String?> fetchedAt = const Value.absent(),
                Value<String> tastingNotes = const Value.absent(),
                Value<String> companionSuggestions = const Value.absent(),
                Value<double?> globalScore = const Value.absent(),
              }) => WhiskiesCompanion(
                id: id,
                externalId: externalId,
                name: name,
                country: country,
                region: region,
                category: category,
                distillery: distillery,
                age: age,
                abv: abv,
                caskType: caskType,
                defaultPrice: defaultPrice,
                currency: currency,
                sourceName: sourceName,
                sourceUrl: sourceUrl,
                fetchedAt: fetchedAt,
                tastingNotes: tastingNotes,
                companionSuggestions: companionSuggestions,
                globalScore: globalScore,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String?> externalId = const Value.absent(),
                required String name,
                Value<String?> country = const Value.absent(),
                Value<String?> region = const Value.absent(),
                Value<String?> category = const Value.absent(),
                Value<String?> distillery = const Value.absent(),
                Value<int?> age = const Value.absent(),
                Value<double?> abv = const Value.absent(),
                Value<String?> caskType = const Value.absent(),
                Value<double?> defaultPrice = const Value.absent(),
                Value<String?> currency = const Value.absent(),
                Value<String?> sourceName = const Value.absent(),
                Value<String?> sourceUrl = const Value.absent(),
                Value<String?> fetchedAt = const Value.absent(),
                Value<String> tastingNotes = const Value.absent(),
                Value<String> companionSuggestions = const Value.absent(),
                Value<double?> globalScore = const Value.absent(),
              }) => WhiskiesCompanion.insert(
                id: id,
                externalId: externalId,
                name: name,
                country: country,
                region: region,
                category: category,
                distillery: distillery,
                age: age,
                abv: abv,
                caskType: caskType,
                defaultPrice: defaultPrice,
                currency: currency,
                sourceName: sourceName,
                sourceUrl: sourceUrl,
                fetchedAt: fetchedAt,
                tastingNotes: tastingNotes,
                companionSuggestions: companionSuggestions,
                globalScore: globalScore,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$WhiskiesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $WhiskiesTable,
      WhiskyEntity,
      $$WhiskiesTableFilterComposer,
      $$WhiskiesTableOrderingComposer,
      $$WhiskiesTableAnnotationComposer,
      $$WhiskiesTableCreateCompanionBuilder,
      $$WhiskiesTableUpdateCompanionBuilder,
      (
        WhiskyEntity,
        BaseReferences<_$AppDatabase, $WhiskiesTable, WhiskyEntity>,
      ),
      WhiskyEntity,
      PrefetchHooks Function()
    >;
typedef $$UserSettingsTableCreateCompanionBuilder =
    UserSettingsCompanion Function({
      required String key,
      required String value,
      Value<int> rowid,
    });
typedef $$UserSettingsTableUpdateCompanionBuilder =
    UserSettingsCompanion Function({
      Value<String> key,
      Value<String> value,
      Value<int> rowid,
    });

class $$UserSettingsTableFilterComposer
    extends Composer<_$AppDatabase, $UserSettingsTable> {
  $$UserSettingsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get key => $composableBuilder(
    column: $table.key,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get value => $composableBuilder(
    column: $table.value,
    builder: (column) => ColumnFilters(column),
  );
}

class $$UserSettingsTableOrderingComposer
    extends Composer<_$AppDatabase, $UserSettingsTable> {
  $$UserSettingsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get key => $composableBuilder(
    column: $table.key,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get value => $composableBuilder(
    column: $table.value,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$UserSettingsTableAnnotationComposer
    extends Composer<_$AppDatabase, $UserSettingsTable> {
  $$UserSettingsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get key =>
      $composableBuilder(column: $table.key, builder: (column) => column);

  GeneratedColumn<String> get value =>
      $composableBuilder(column: $table.value, builder: (column) => column);
}

class $$UserSettingsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $UserSettingsTable,
          UserSetting,
          $$UserSettingsTableFilterComposer,
          $$UserSettingsTableOrderingComposer,
          $$UserSettingsTableAnnotationComposer,
          $$UserSettingsTableCreateCompanionBuilder,
          $$UserSettingsTableUpdateCompanionBuilder,
          (
            UserSetting,
            BaseReferences<_$AppDatabase, $UserSettingsTable, UserSetting>,
          ),
          UserSetting,
          PrefetchHooks Function()
        > {
  $$UserSettingsTableTableManager(_$AppDatabase db, $UserSettingsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$UserSettingsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$UserSettingsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$UserSettingsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> key = const Value.absent(),
                Value<String> value = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => UserSettingsCompanion(key: key, value: value, rowid: rowid),
          createCompanionCallback:
              ({
                required String key,
                required String value,
                Value<int> rowid = const Value.absent(),
              }) => UserSettingsCompanion.insert(
                key: key,
                value: value,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$UserSettingsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $UserSettingsTable,
      UserSetting,
      $$UserSettingsTableFilterComposer,
      $$UserSettingsTableOrderingComposer,
      $$UserSettingsTableAnnotationComposer,
      $$UserSettingsTableCreateCompanionBuilder,
      $$UserSettingsTableUpdateCompanionBuilder,
      (
        UserSetting,
        BaseReferences<_$AppDatabase, $UserSettingsTable, UserSetting>,
      ),
      UserSetting,
      PrefetchHooks Function()
    >;
typedef $$UserWhiskyScoresTableCreateCompanionBuilder =
    UserWhiskyScoresCompanion Function({
      Value<int> whiskyId,
      required int score,
      required String ratedAt,
    });
typedef $$UserWhiskyScoresTableUpdateCompanionBuilder =
    UserWhiskyScoresCompanion Function({
      Value<int> whiskyId,
      Value<int> score,
      Value<String> ratedAt,
    });

class $$UserWhiskyScoresTableFilterComposer
    extends Composer<_$AppDatabase, $UserWhiskyScoresTable> {
  $$UserWhiskyScoresTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get whiskyId => $composableBuilder(
    column: $table.whiskyId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get score => $composableBuilder(
    column: $table.score,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get ratedAt => $composableBuilder(
    column: $table.ratedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$UserWhiskyScoresTableOrderingComposer
    extends Composer<_$AppDatabase, $UserWhiskyScoresTable> {
  $$UserWhiskyScoresTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get whiskyId => $composableBuilder(
    column: $table.whiskyId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get score => $composableBuilder(
    column: $table.score,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get ratedAt => $composableBuilder(
    column: $table.ratedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$UserWhiskyScoresTableAnnotationComposer
    extends Composer<_$AppDatabase, $UserWhiskyScoresTable> {
  $$UserWhiskyScoresTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get whiskyId =>
      $composableBuilder(column: $table.whiskyId, builder: (column) => column);

  GeneratedColumn<int> get score =>
      $composableBuilder(column: $table.score, builder: (column) => column);

  GeneratedColumn<String> get ratedAt =>
      $composableBuilder(column: $table.ratedAt, builder: (column) => column);
}

class $$UserWhiskyScoresTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $UserWhiskyScoresTable,
          UserWhiskyScore,
          $$UserWhiskyScoresTableFilterComposer,
          $$UserWhiskyScoresTableOrderingComposer,
          $$UserWhiskyScoresTableAnnotationComposer,
          $$UserWhiskyScoresTableCreateCompanionBuilder,
          $$UserWhiskyScoresTableUpdateCompanionBuilder,
          (
            UserWhiskyScore,
            BaseReferences<
              _$AppDatabase,
              $UserWhiskyScoresTable,
              UserWhiskyScore
            >,
          ),
          UserWhiskyScore,
          PrefetchHooks Function()
        > {
  $$UserWhiskyScoresTableTableManager(
    _$AppDatabase db,
    $UserWhiskyScoresTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$UserWhiskyScoresTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$UserWhiskyScoresTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$UserWhiskyScoresTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> whiskyId = const Value.absent(),
                Value<int> score = const Value.absent(),
                Value<String> ratedAt = const Value.absent(),
              }) => UserWhiskyScoresCompanion(
                whiskyId: whiskyId,
                score: score,
                ratedAt: ratedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> whiskyId = const Value.absent(),
                required int score,
                required String ratedAt,
              }) => UserWhiskyScoresCompanion.insert(
                whiskyId: whiskyId,
                score: score,
                ratedAt: ratedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$UserWhiskyScoresTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $UserWhiskyScoresTable,
      UserWhiskyScore,
      $$UserWhiskyScoresTableFilterComposer,
      $$UserWhiskyScoresTableOrderingComposer,
      $$UserWhiskyScoresTableAnnotationComposer,
      $$UserWhiskyScoresTableCreateCompanionBuilder,
      $$UserWhiskyScoresTableUpdateCompanionBuilder,
      (
        UserWhiskyScore,
        BaseReferences<_$AppDatabase, $UserWhiskyScoresTable, UserWhiskyScore>,
      ),
      UserWhiskyScore,
      PrefetchHooks Function()
    >;
typedef $$FavoritesTableCreateCompanionBuilder =
    FavoritesCompanion Function({Value<int> whiskyId, required String addedAt});
typedef $$FavoritesTableUpdateCompanionBuilder =
    FavoritesCompanion Function({Value<int> whiskyId, Value<String> addedAt});

class $$FavoritesTableFilterComposer
    extends Composer<_$AppDatabase, $FavoritesTable> {
  $$FavoritesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get whiskyId => $composableBuilder(
    column: $table.whiskyId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get addedAt => $composableBuilder(
    column: $table.addedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$FavoritesTableOrderingComposer
    extends Composer<_$AppDatabase, $FavoritesTable> {
  $$FavoritesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get whiskyId => $composableBuilder(
    column: $table.whiskyId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get addedAt => $composableBuilder(
    column: $table.addedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$FavoritesTableAnnotationComposer
    extends Composer<_$AppDatabase, $FavoritesTable> {
  $$FavoritesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get whiskyId =>
      $composableBuilder(column: $table.whiskyId, builder: (column) => column);

  GeneratedColumn<String> get addedAt =>
      $composableBuilder(column: $table.addedAt, builder: (column) => column);
}

class $$FavoritesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $FavoritesTable,
          Favorite,
          $$FavoritesTableFilterComposer,
          $$FavoritesTableOrderingComposer,
          $$FavoritesTableAnnotationComposer,
          $$FavoritesTableCreateCompanionBuilder,
          $$FavoritesTableUpdateCompanionBuilder,
          (Favorite, BaseReferences<_$AppDatabase, $FavoritesTable, Favorite>),
          Favorite,
          PrefetchHooks Function()
        > {
  $$FavoritesTableTableManager(_$AppDatabase db, $FavoritesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$FavoritesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$FavoritesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$FavoritesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> whiskyId = const Value.absent(),
                Value<String> addedAt = const Value.absent(),
              }) => FavoritesCompanion(whiskyId: whiskyId, addedAt: addedAt),
          createCompanionCallback:
              ({
                Value<int> whiskyId = const Value.absent(),
                required String addedAt,
              }) => FavoritesCompanion.insert(
                whiskyId: whiskyId,
                addedAt: addedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$FavoritesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $FavoritesTable,
      Favorite,
      $$FavoritesTableFilterComposer,
      $$FavoritesTableOrderingComposer,
      $$FavoritesTableAnnotationComposer,
      $$FavoritesTableCreateCompanionBuilder,
      $$FavoritesTableUpdateCompanionBuilder,
      (Favorite, BaseReferences<_$AppDatabase, $FavoritesTable, Favorite>),
      Favorite,
      PrefetchHooks Function()
    >;
typedef $$UserNotesTableCreateCompanionBuilder =
    UserNotesCompanion Function({
      Value<int> whiskyId,
      required String note,
      required String updatedAt,
    });
typedef $$UserNotesTableUpdateCompanionBuilder =
    UserNotesCompanion Function({
      Value<int> whiskyId,
      Value<String> note,
      Value<String> updatedAt,
    });

class $$UserNotesTableFilterComposer
    extends Composer<_$AppDatabase, $UserNotesTable> {
  $$UserNotesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get whiskyId => $composableBuilder(
    column: $table.whiskyId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get note => $composableBuilder(
    column: $table.note,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$UserNotesTableOrderingComposer
    extends Composer<_$AppDatabase, $UserNotesTable> {
  $$UserNotesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get whiskyId => $composableBuilder(
    column: $table.whiskyId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get note => $composableBuilder(
    column: $table.note,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$UserNotesTableAnnotationComposer
    extends Composer<_$AppDatabase, $UserNotesTable> {
  $$UserNotesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get whiskyId =>
      $composableBuilder(column: $table.whiskyId, builder: (column) => column);

  GeneratedColumn<String> get note =>
      $composableBuilder(column: $table.note, builder: (column) => column);

  GeneratedColumn<String> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$UserNotesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $UserNotesTable,
          UserNote,
          $$UserNotesTableFilterComposer,
          $$UserNotesTableOrderingComposer,
          $$UserNotesTableAnnotationComposer,
          $$UserNotesTableCreateCompanionBuilder,
          $$UserNotesTableUpdateCompanionBuilder,
          (UserNote, BaseReferences<_$AppDatabase, $UserNotesTable, UserNote>),
          UserNote,
          PrefetchHooks Function()
        > {
  $$UserNotesTableTableManager(_$AppDatabase db, $UserNotesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$UserNotesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$UserNotesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$UserNotesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> whiskyId = const Value.absent(),
                Value<String> note = const Value.absent(),
                Value<String> updatedAt = const Value.absent(),
              }) => UserNotesCompanion(
                whiskyId: whiskyId,
                note: note,
                updatedAt: updatedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> whiskyId = const Value.absent(),
                required String note,
                required String updatedAt,
              }) => UserNotesCompanion.insert(
                whiskyId: whiskyId,
                note: note,
                updatedAt: updatedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$UserNotesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $UserNotesTable,
      UserNote,
      $$UserNotesTableFilterComposer,
      $$UserNotesTableOrderingComposer,
      $$UserNotesTableAnnotationComposer,
      $$UserNotesTableCreateCompanionBuilder,
      $$UserNotesTableUpdateCompanionBuilder,
      (UserNote, BaseReferences<_$AppDatabase, $UserNotesTable, UserNote>),
      UserNote,
      PrefetchHooks Function()
    >;
typedef $$WhiskyPricesTableCreateCompanionBuilder =
    WhiskyPricesCompanion Function({
      Value<int> id,
      required int whiskyId,
      required String sourceName,
      required double price,
      required String currency,
      required String country,
      required String sourceUrl,
      required String fetchedAt,
      Value<bool> isManual,
    });
typedef $$WhiskyPricesTableUpdateCompanionBuilder =
    WhiskyPricesCompanion Function({
      Value<int> id,
      Value<int> whiskyId,
      Value<String> sourceName,
      Value<double> price,
      Value<String> currency,
      Value<String> country,
      Value<String> sourceUrl,
      Value<String> fetchedAt,
      Value<bool> isManual,
    });

class $$WhiskyPricesTableFilterComposer
    extends Composer<_$AppDatabase, $WhiskyPricesTable> {
  $$WhiskyPricesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get whiskyId => $composableBuilder(
    column: $table.whiskyId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sourceName => $composableBuilder(
    column: $table.sourceName,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get price => $composableBuilder(
    column: $table.price,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get currency => $composableBuilder(
    column: $table.currency,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get country => $composableBuilder(
    column: $table.country,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sourceUrl => $composableBuilder(
    column: $table.sourceUrl,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get fetchedAt => $composableBuilder(
    column: $table.fetchedAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get isManual => $composableBuilder(
    column: $table.isManual,
    builder: (column) => ColumnFilters(column),
  );
}

class $$WhiskyPricesTableOrderingComposer
    extends Composer<_$AppDatabase, $WhiskyPricesTable> {
  $$WhiskyPricesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get whiskyId => $composableBuilder(
    column: $table.whiskyId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sourceName => $composableBuilder(
    column: $table.sourceName,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get price => $composableBuilder(
    column: $table.price,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get currency => $composableBuilder(
    column: $table.currency,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get country => $composableBuilder(
    column: $table.country,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sourceUrl => $composableBuilder(
    column: $table.sourceUrl,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get fetchedAt => $composableBuilder(
    column: $table.fetchedAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get isManual => $composableBuilder(
    column: $table.isManual,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$WhiskyPricesTableAnnotationComposer
    extends Composer<_$AppDatabase, $WhiskyPricesTable> {
  $$WhiskyPricesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get whiskyId =>
      $composableBuilder(column: $table.whiskyId, builder: (column) => column);

  GeneratedColumn<String> get sourceName => $composableBuilder(
    column: $table.sourceName,
    builder: (column) => column,
  );

  GeneratedColumn<double> get price =>
      $composableBuilder(column: $table.price, builder: (column) => column);

  GeneratedColumn<String> get currency =>
      $composableBuilder(column: $table.currency, builder: (column) => column);

  GeneratedColumn<String> get country =>
      $composableBuilder(column: $table.country, builder: (column) => column);

  GeneratedColumn<String> get sourceUrl =>
      $composableBuilder(column: $table.sourceUrl, builder: (column) => column);

  GeneratedColumn<String> get fetchedAt =>
      $composableBuilder(column: $table.fetchedAt, builder: (column) => column);

  GeneratedColumn<bool> get isManual =>
      $composableBuilder(column: $table.isManual, builder: (column) => column);
}

class $$WhiskyPricesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $WhiskyPricesTable,
          WhiskyPrice,
          $$WhiskyPricesTableFilterComposer,
          $$WhiskyPricesTableOrderingComposer,
          $$WhiskyPricesTableAnnotationComposer,
          $$WhiskyPricesTableCreateCompanionBuilder,
          $$WhiskyPricesTableUpdateCompanionBuilder,
          (
            WhiskyPrice,
            BaseReferences<_$AppDatabase, $WhiskyPricesTable, WhiskyPrice>,
          ),
          WhiskyPrice,
          PrefetchHooks Function()
        > {
  $$WhiskyPricesTableTableManager(_$AppDatabase db, $WhiskyPricesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$WhiskyPricesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$WhiskyPricesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$WhiskyPricesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> whiskyId = const Value.absent(),
                Value<String> sourceName = const Value.absent(),
                Value<double> price = const Value.absent(),
                Value<String> currency = const Value.absent(),
                Value<String> country = const Value.absent(),
                Value<String> sourceUrl = const Value.absent(),
                Value<String> fetchedAt = const Value.absent(),
                Value<bool> isManual = const Value.absent(),
              }) => WhiskyPricesCompanion(
                id: id,
                whiskyId: whiskyId,
                sourceName: sourceName,
                price: price,
                currency: currency,
                country: country,
                sourceUrl: sourceUrl,
                fetchedAt: fetchedAt,
                isManual: isManual,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int whiskyId,
                required String sourceName,
                required double price,
                required String currency,
                required String country,
                required String sourceUrl,
                required String fetchedAt,
                Value<bool> isManual = const Value.absent(),
              }) => WhiskyPricesCompanion.insert(
                id: id,
                whiskyId: whiskyId,
                sourceName: sourceName,
                price: price,
                currency: currency,
                country: country,
                sourceUrl: sourceUrl,
                fetchedAt: fetchedAt,
                isManual: isManual,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$WhiskyPricesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $WhiskyPricesTable,
      WhiskyPrice,
      $$WhiskyPricesTableFilterComposer,
      $$WhiskyPricesTableOrderingComposer,
      $$WhiskyPricesTableAnnotationComposer,
      $$WhiskyPricesTableCreateCompanionBuilder,
      $$WhiskyPricesTableUpdateCompanionBuilder,
      (
        WhiskyPrice,
        BaseReferences<_$AppDatabase, $WhiskyPricesTable, WhiskyPrice>,
      ),
      WhiskyPrice,
      PrefetchHooks Function()
    >;
typedef $$ExternalSourcesTableCreateCompanionBuilder =
    ExternalSourcesCompanion Function({
      Value<int> id,
      required int whiskyId,
      required String sourceName,
      required String sourceUrl,
      required String externalId,
      required String fetchedAt,
    });
typedef $$ExternalSourcesTableUpdateCompanionBuilder =
    ExternalSourcesCompanion Function({
      Value<int> id,
      Value<int> whiskyId,
      Value<String> sourceName,
      Value<String> sourceUrl,
      Value<String> externalId,
      Value<String> fetchedAt,
    });

class $$ExternalSourcesTableFilterComposer
    extends Composer<_$AppDatabase, $ExternalSourcesTable> {
  $$ExternalSourcesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get whiskyId => $composableBuilder(
    column: $table.whiskyId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sourceName => $composableBuilder(
    column: $table.sourceName,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sourceUrl => $composableBuilder(
    column: $table.sourceUrl,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get externalId => $composableBuilder(
    column: $table.externalId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get fetchedAt => $composableBuilder(
    column: $table.fetchedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$ExternalSourcesTableOrderingComposer
    extends Composer<_$AppDatabase, $ExternalSourcesTable> {
  $$ExternalSourcesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get whiskyId => $composableBuilder(
    column: $table.whiskyId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sourceName => $composableBuilder(
    column: $table.sourceName,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sourceUrl => $composableBuilder(
    column: $table.sourceUrl,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get externalId => $composableBuilder(
    column: $table.externalId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get fetchedAt => $composableBuilder(
    column: $table.fetchedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$ExternalSourcesTableAnnotationComposer
    extends Composer<_$AppDatabase, $ExternalSourcesTable> {
  $$ExternalSourcesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get whiskyId =>
      $composableBuilder(column: $table.whiskyId, builder: (column) => column);

  GeneratedColumn<String> get sourceName => $composableBuilder(
    column: $table.sourceName,
    builder: (column) => column,
  );

  GeneratedColumn<String> get sourceUrl =>
      $composableBuilder(column: $table.sourceUrl, builder: (column) => column);

  GeneratedColumn<String> get externalId => $composableBuilder(
    column: $table.externalId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get fetchedAt =>
      $composableBuilder(column: $table.fetchedAt, builder: (column) => column);
}

class $$ExternalSourcesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $ExternalSourcesTable,
          ExternalSource,
          $$ExternalSourcesTableFilterComposer,
          $$ExternalSourcesTableOrderingComposer,
          $$ExternalSourcesTableAnnotationComposer,
          $$ExternalSourcesTableCreateCompanionBuilder,
          $$ExternalSourcesTableUpdateCompanionBuilder,
          (
            ExternalSource,
            BaseReferences<
              _$AppDatabase,
              $ExternalSourcesTable,
              ExternalSource
            >,
          ),
          ExternalSource,
          PrefetchHooks Function()
        > {
  $$ExternalSourcesTableTableManager(
    _$AppDatabase db,
    $ExternalSourcesTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$ExternalSourcesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$ExternalSourcesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$ExternalSourcesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> whiskyId = const Value.absent(),
                Value<String> sourceName = const Value.absent(),
                Value<String> sourceUrl = const Value.absent(),
                Value<String> externalId = const Value.absent(),
                Value<String> fetchedAt = const Value.absent(),
              }) => ExternalSourcesCompanion(
                id: id,
                whiskyId: whiskyId,
                sourceName: sourceName,
                sourceUrl: sourceUrl,
                externalId: externalId,
                fetchedAt: fetchedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int whiskyId,
                required String sourceName,
                required String sourceUrl,
                required String externalId,
                required String fetchedAt,
              }) => ExternalSourcesCompanion.insert(
                id: id,
                whiskyId: whiskyId,
                sourceName: sourceName,
                sourceUrl: sourceUrl,
                externalId: externalId,
                fetchedAt: fetchedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$ExternalSourcesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $ExternalSourcesTable,
      ExternalSource,
      $$ExternalSourcesTableFilterComposer,
      $$ExternalSourcesTableOrderingComposer,
      $$ExternalSourcesTableAnnotationComposer,
      $$ExternalSourcesTableCreateCompanionBuilder,
      $$ExternalSourcesTableUpdateCompanionBuilder,
      (
        ExternalSource,
        BaseReferences<_$AppDatabase, $ExternalSourcesTable, ExternalSource>,
      ),
      ExternalSource,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$WhiskiesTableTableManager get whiskies =>
      $$WhiskiesTableTableManager(_db, _db.whiskies);
  $$UserSettingsTableTableManager get userSettings =>
      $$UserSettingsTableTableManager(_db, _db.userSettings);
  $$UserWhiskyScoresTableTableManager get userWhiskyScores =>
      $$UserWhiskyScoresTableTableManager(_db, _db.userWhiskyScores);
  $$FavoritesTableTableManager get favorites =>
      $$FavoritesTableTableManager(_db, _db.favorites);
  $$UserNotesTableTableManager get userNotes =>
      $$UserNotesTableTableManager(_db, _db.userNotes);
  $$WhiskyPricesTableTableManager get whiskyPrices =>
      $$WhiskyPricesTableTableManager(_db, _db.whiskyPrices);
  $$ExternalSourcesTableTableManager get externalSources =>
      $$ExternalSourcesTableTableManager(_db, _db.externalSources);
}
