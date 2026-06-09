import 'package:drift/drift.dart' hide Column;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/features/whisky/domain/models/whisky.dart';
import '../controllers/whisky_providers.dart';
import 'home_screen.dart';
import '../../../../core/localization/localization_provider.dart';

class SetupScreen extends ConsumerStatefulWidget {
  const SetupScreen({super.key});

  @override
  ConsumerState<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends ConsumerState<SetupScreen> {
  final _searchController = TextEditingController();
  List<Whisky> _searchResults = [];
  bool _isLoading = false;
  bool _searchedOnline = false;

  Whisky? _selectedWhisky;
  int _absoluteScore = 90; // Default absolute rating for reference

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _searchWhiskies(String query) async {
    if (query.isEmpty) {
      setState(() {
        _searchResults = [];
        _searchedOnline = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
    });

    final repository = ref.read(whiskyRepositoryProvider);
    
    // First query local database
    final db = ref.read(appDatabaseProvider);
    final localList = await (db.select(db.whiskies)..where((tbl) => tbl.name.like('%$query%'))).get();
    
    if (localList.isNotEmpty) {
      setState(() {
        _searchResults = localList.map((e) => Whisky.fromEntities(whisky: e)).toList();
        _isLoading = false;
        _searchedOnline = false;
      });
    } else {
      // No local results, search backend online
      final externalList = await repository.searchExternalWhiskies(query);
      setState(() {
        _searchResults = externalList;
        _isLoading = false;
        _searchedOnline = true;
      });
    }
  }

  void _completeSetup() async {
    if (_selectedWhisky == null) return;

    setState(() {
      _isLoading = true;
    });

    final repository = ref.read(whiskyRepositoryProvider);
    
    // If the whisky was fetched from external API, add it to library first
    int localId = _selectedWhisky!.id;
    if (localId == 0) {
      localId = await repository.addWhiskyToLibrary(_selectedWhisky!);
    }

    // Set as reference whisky
    await repository.setReferenceWhisky(localId, _absoluteScore);
    // Auto-favorite it
    await repository.toggleFavorite(localId);
    // Give it the absolute score in scores table
    await repository.updatePersonalScore(localId, _absoluteScore);
    // Add a default personal note
    await repository.updatePersonalNotes(localId, 'Bu viski benim 100 puanlık referans viskimdir.');

    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const HomeScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final tr = ref.watch(trProvider);
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 24),
              // App Logo / Header
              Center(
                child: Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.08),
                        shape: BoxShape.circle,
                        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2), width: 2),
                      ),
                      child: const Icon(Icons.local_bar, color: AppTheme.primary, size: 48),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'MALT RADAR',
                      style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                            color: AppTheme.primary,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 2.0,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      tr('setup_subtitle'),
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: AppTheme.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),

              if (_selectedWhisky == null) ...[
                // Instruction
                Text(
                  tr('setup_reference_desc'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
                ),
                const SizedBox(height: 24),

                // Search Bar
                TextField(
                  controller: _searchController,
                  onChanged: _searchWhiskies,
                  decoration: InputDecoration(
                    hintText: tr('setup_search_hint'),
                    prefixIcon: const Icon(Icons.search, color: AppTheme.textSecondary),
                  ),
                ),
                const SizedBox(height: 16),

                // Search Results
                Expanded(
                  child: _isLoading
                      ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
                      : _searchResults.isEmpty
                          ? Center(
                              child: Text(
                                _searchController.text.isEmpty
                                    ? tr('setup_type_to_search')
                                    : tr('setup_no_results'),
                                style: const TextStyle(color: AppTheme.textMuted),
                              ),
                            )
                          : ListView.builder(
                              itemCount: _searchResults.length,
                              itemBuilder: (context, index) {
                                final whisky = _searchResults[index];
                                return ListTile(
                                  leading: const Icon(Icons.local_offer, color: AppTheme.secondary),
                                  title: Text(whisky.name),
                                  subtitle: Text(_searchedOnline
                                      ? '${whisky.country ?? tr('unknown')} (${tr('setup_internet')})'
                                      : '${whisky.country ?? tr('unknown')} (${tr('setup_local')})'),
                                  trailing: const Icon(Icons.chevron_right, color: AppTheme.primary),
                                  onTap: () {
                                    setState(() {
                                      _selectedWhisky = whisky;
                                    });
                                  },
                                );
                              },
                            ),
                ),
              ] else ...[
                // Configuration screen for selected reference
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          tr('setup_selected_ref'),
                          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _selectedWhisky!.name,
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                color: AppTheme.primary,
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                        if (_selectedWhisky!.country != null) ...[
                          const SizedBox(height: 4),
                          Text(
                            '${tr('preview_origin')}: ${_selectedWhisky!.country}',
                            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 32),

                // Absolute Score Selection
                Text(
                  tr('setup_absolute_score_q'),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  tr('setup_absolute_score_desc'),
                  style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
                ),
                const SizedBox(height: 24),

                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(tr('setup_absolute_score'), style: const TextStyle(fontWeight: FontWeight.bold)),
                    Text(
                      '$_absoluteScore / 100',
                      style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold, fontSize: 20),
                    ),
                  ],
                ),
                Slider(
                  value: _absoluteScore.toDouble(),
                  min: 50,
                  max: 100,
                  divisions: 50,
                  label: _absoluteScore.toString(),
                  onChanged: (val) {
                    setState(() {
                      _absoluteScore = val.round();
                    });
                  },
                ),
                const Spacer(),

                // Buttons
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () {
                          setState(() {
                            _selectedWhisky = null;
                          });
                        },
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          side: const BorderSide(color: AppTheme.textSecondary),
                        ),
                        child: Text(tr('setup_change'), style: const TextStyle(color: AppTheme.textSecondary)),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _completeSetup,
                        child: _isLoading
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(color: AppTheme.background, strokeWidth: 2),
                              )
                            : Text(tr('setup_finish')),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
