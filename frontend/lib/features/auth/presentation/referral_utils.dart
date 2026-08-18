/// Extracts referral source from URL query parameters.
/// Checks for: ref, referral, utm_source, source
/// Returns null if no referral source found.
String? extractReferralSource() {
  try {
    // Uri.base works on web and provides current URL with query params
    final uri = Uri.base;
    final params = uri.queryParameters;
    
    // Check common referral parameter names
    return params['ref'] ?? 
           params['referral'] ?? 
           params['utm_source'] ?? 
           params['source'];
  } catch (_) {
    return null;
  }
}
