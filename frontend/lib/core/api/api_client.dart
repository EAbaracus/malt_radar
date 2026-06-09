import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class ApiClient {
  static String get baseUrl {
    if (kIsWeb) return 'http://localhost:8080';
    // On native platforms, check if Android for emulator loopback
    return _getNativeBaseUrl();
  }

  static String _getNativeBaseUrl() {
    try {
      // Dynamic import approach: defaultTargetPlatform works on all platforms
      if (defaultTargetPlatform == TargetPlatform.android) {
        return 'http://10.0.2.2:8080';
      }
    } catch (_) {}
    return 'http://localhost:8080';
  }

  final http.Client _client;

  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  Future<List<Map<String, dynamic>>> searchExternalWhiskies(String query) async {
    final uri = Uri.parse('$baseUrl/api/whiskies/search?q=${Uri.encodeComponent(query)}');
    try {
      final response = await _client.get(uri);
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        return data.map((e) => e as Map<String, dynamic>).toList();
      } else {
        throw Exception('API search failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('API connection error: $e');
    }
  }

  Future<List<Map<String, dynamic>>> getWhiskyPrices(String externalId) async {
    final uri = Uri.parse('$baseUrl/api/whiskies/${Uri.encodeComponent(externalId)}/prices');
    try {
      final response = await _client.get(uri);
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        return data.map((e) => e as Map<String, dynamic>).toList();
      } else {
        throw Exception('API prices failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('API connection error: $e');
    }
  }

  Future<Map<String, dynamic>> getWhiskyDetails(String externalId) async {
    final uri = Uri.parse('$baseUrl/api/whiskies/${Uri.encodeComponent(externalId)}');
    try {
      final response = await _client.get(uri);
      if (response.statusCode == 200) {
        return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      } else {
        throw Exception('API details failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('API connection error: $e');
    }
  }
}
