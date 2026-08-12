import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';

/// Thrown for non-2xx responses or connectivity failures.
class AuthApiException implements Exception {
  final String message;
  final int? statusCode;
  AuthApiException(this.message, {this.statusCode});
  @override
  String toString() => message;
}

/// Thin HTTP client for the `/api/auth/*` + `/api/auth/sync/*` backend endpoints.
/// Auth endpoints are anonymous where required (register/login) or carry a
/// bearer token explicitly (logout/me/sync). No prices are ever sent or
/// rendered here (Product Rule).
class AuthApi {
  static String get baseUrl => AppConfig.baseUrl;
  static const Duration _timeout = Duration(seconds: 15);
  final http.Client _client;

  AuthApi([http.Client? client]) : _client = client ?? http.Client();

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    String? displayName,
    required String ageCountry,
    required int ageMin,
    required bool privacyConsent,
  }) async {
    final body = await _send(
      'POST',
      '/api/auth/register',
      body: {
        'email': email,
        'password': password,
        'display_name': displayName,
        'age_country': ageCountry,
        'age_min': ageMin,
        'privacy_consent': privacyConsent,
      },
    );
    return body as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    final body = await _send(
      'POST',
      '/api/auth/login',
      body: {'email': email, 'password': password},
    );
    return body as Map<String, dynamic>;
  }

  Future<void> logout(String token) async {
    await _send('POST', '/api/auth/logout', token: token);
  }

  Future<Map<String, dynamic>> me(String token) async {
    final body = await _send('GET', '/api/auth/me', token: token);
    return body as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateProfile(
    String token, {
    String? displayName,
  }) async {
    final body = await _send(
      'PATCH',
      '/api/auth/me',
      token: token,
      body: {'display_name': displayName},
    );
    return body as Map<String, dynamic>;
  }

  /// Exchanges a Google OAuth ID token for a Malt Radar session.
  ///
  /// Contract (parallel backend task): `POST /api/auth/google` with body
  /// `{"id_token": ...}` -> 200 `{token, user{id,email,display_name,email_verified}}`.
  /// 401 (invalid token) / 400 (popup dismissed) surface as [AuthApiException].
  Future<Map<String, dynamic>> signInWithGoogle(String idToken) async {
    final body = await _send(
      'POST',
      '/api/auth/google',
      body: {'id_token': idToken},
    );
    return body as Map<String, dynamic>;
  }

  Future<void> verifyEmail(int userId, String token) async {
    await _send(
      'POST',
      '/api/auth/verify-email',
      body: {'user_id': userId, 'token': token},
    );
  }

  Future<Map<String, dynamic>> syncPush(
    String token,
    Map<String, List<Map<String, dynamic>>> payload,
  ) async {
    final body = await _send(
      'POST',
      '/api/auth/sync/push',
      token: token,
      body: payload,
    );
    return body as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> syncPull(String token) async {
    final body = await _send('GET', '/api/auth/sync/pull', token: token);
    return body as Map<String, dynamic>;
  }

  Future<dynamic> _send(
    String method,
    String path, {
    String? token,
    Map<String, dynamic>? body,
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    final headers = <String, String>{
      'Accept': 'application/json',
      if (body != null) 'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
    http.Response res;
    try {
      res = await switch (method) {
        'POST' => _client.post(
          uri,
          headers: headers,
          body: body == null ? null : jsonEncode(body),
        ),
        'PATCH' => _client.patch(
          uri,
          headers: headers,
          body: body == null ? null : jsonEncode(body),
        ),
        _ => _client.get(uri, headers: headers),
      }.timeout(_timeout);
    } catch (e) {
      throw AuthApiException(
        'Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol ediniz.',
      );
    }
    return _decode(res);
  }

  dynamic _decode(http.Response res) {
    dynamic data;
    try {
      data = jsonDecode(utf8.decode(res.bodyBytes));
    } catch (_) {
      data = null;
    }
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return data;
    }
    final detail = (data is Map && data['detail'] != null)
        ? data['detail'].toString()
        : 'İstek başarısız (${res.statusCode})';
    throw AuthApiException(detail, statusCode: res.statusCode);
  }
}
