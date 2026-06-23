import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';

class ApiClientException implements Exception {
  final String message;
  ApiClientException(this.message);

  @override
  String toString() => message;
}

class ApiClient {
  static String get baseUrl => AppConfig.baseUrl;

  final http.Client _client;
  static const Duration _timeout = Duration(seconds: 15);

  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  Future<List<Map<String, dynamic>>> searchExternalWhiskies(String query) async {
    final uri = Uri.parse('$baseUrl/api/whiskies/search?q=${Uri.encodeComponent(query)}');
    try {
      final response = await _client.get(uri).timeout(_timeout);
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        return data.map((e) => e as Map<String, dynamic>).toList();
      } else {
        debugPrint('API search failed with status: ${response.statusCode}');
        throw ApiClientException('Arama işlemi başarısız oldu. Lütfen tekrar deneyin.');
      }
    } catch (e) {
      debugPrint('API connection error (searchExternalWhiskies): $e');
      throw ApiClientException('Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol ediniz.');
    }
  }

  Future<List<Map<String, dynamic>>> getWhiskyPrices(String externalId) async {
    final uri = Uri.parse('$baseUrl/api/whiskies/${Uri.encodeComponent(externalId)}/prices');
    try {
      final response = await _client.get(uri).timeout(_timeout);
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        return data.map((e) => e as Map<String, dynamic>).toList();
      } else {
        debugPrint('API prices failed with status: ${response.statusCode}');
        throw ApiClientException('Fiyat bilgisi alınamadı. Lütfen tekrar deneyin.');
      }
    } catch (e) {
      debugPrint('API connection error (getWhiskyPrices): $e');
      throw ApiClientException('Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol ediniz.');
    }
  }

  Future<Map<String, dynamic>> getWhiskyDetails(String externalId) async {
    final uri = Uri.parse('$baseUrl/api/whiskies/${Uri.encodeComponent(externalId)}');
    try {
      final response = await _client.get(uri).timeout(_timeout);
      if (response.statusCode == 200) {
        return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      } else {
        debugPrint('API details failed with status: ${response.statusCode}');
        throw ApiClientException('Viski detayları alınamadı. Lütfen tekrar deneyin.');
      }
    } catch (e) {
      debugPrint('API connection error (getWhiskyDetails): $e');
      throw ApiClientException('Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol ediniz.');
    }
  }
}
