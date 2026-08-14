/// Minimal, server-shaped representation of the authenticated user.
///
/// Only fields the UI needs are surfaced; the password hash never crosses the
/// wire or this model.
class AuthUser {
  final int id;
  final String email;
  final String? displayName;
  final bool emailVerified;
  final bool privacyConsent;
  final String? ageCountry;
  final int? ageMin;
  final String? createdAt;

  const AuthUser({
    required this.id,
    required this.email,
    this.displayName,
    this.emailVerified = false,
    this.privacyConsent = false,
    this.ageCountry,
    this.ageMin,
    this.createdAt,
  });

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: (json['id'] as num).toInt(),
      email: (json['email'] as String?) ?? '',
      displayName: json['display_name'] as String?,
      emailVerified: (json['email_verified'] as num?) == 1,
      privacyConsent: (json['privacy_consent'] as num?) == 1,
      ageCountry: json['age_country'] as String?,
      ageMin: (json['age_min'] as num?)?.toInt(),
      createdAt: json['created_at'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'email': email,
    'display_name': displayName,
    'email_verified': emailVerified ? 1 : 0,
    'privacy_consent': privacyConsent ? 1 : 0,
    'age_country': ageCountry,
    'age_min': ageMin,
    'created_at': createdAt,
  };
}
