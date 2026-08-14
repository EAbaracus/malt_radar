import os

path = r'C:\Users\eltun\Documents\malt radar CLEAN\frontend\lib\features\whisky\presentation\screens\detail_screen.dart'

with open(path, 'rb') as f:
    content = f.read()

insert_marker = b'  @override\r\n  Widget build(BuildContext context)'

cert_section = b'''
  Widget _buildCertificationSection(BuildContext context, String Function(String) tr, Whisky whisky) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Container(
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF1A3A1A), Color(0xFF0D260D)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFF2D5A2D), width: 1),
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.verified, color: Color(0xFF4CAF50), size: 20),
                const SizedBox(width: 8),
                Text(
                  tr('certified_whisky'),
                  style: const TextStyle(
                    color: Color(0xFF4CAF50),
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              tr('certified_description'),
              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEvidenceSection(BuildContext context, String Function(String) tr, WidgetRef ref, Whisky whisky) {
    if (_isLoadingEvidence) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
      );
    }
    if (_evidence.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: GlassContainer(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SectionHeader(
              icon: Icons.source,
              title: tr('official_sources'),
              subtitle: '${_evidence.length} ${tr('verified_fields')}',
            ),
            const SizedBox(height: 12),
            ..._evidence.map((e) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.check_circle_outline, size: 16, color: AppTheme.textMuted),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${e['field_name'] ?? ''}: ${e['field_value'] ?? ''}',
                          style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
                        ),
                        Text(
                          'Source: ${e['source_name'] ?? '\u2014'}',
                          style: const TextStyle(color: AppTheme.textMuted, fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  if (e['source_url'] != null && (e['source_url'] as String).isNotEmpty)
                    GestureDetector(
                      onTap: () => {},
                      child: const Icon(Icons.open_in_new, size: 14, color: AppTheme.accent),
                    ),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context)
'''

idx = content.find(insert_marker)
if idx >= 0:
    new_content = content[:idx] + cert_section + content[idx:]
    with open(path, 'wb') as f:
        f.write(new_content)
    print(f'Inserted at offset {idx}')
    print('File size:', os.path.getsize(path))
else:
    print('Marker not found')
    # search for '@override\n  Widget build' to check
    idx2 = content.find(b'@override\r\n  Widget build')
    print('Second try:', idx2)