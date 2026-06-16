import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_client.dart'; // for baseUrl

class DbPaginatedResponse<T> {
  final List<T> items;
  final int totalCount;
  final int? limit;
  final int? offset;

  DbPaginatedResponse({
    required this.items,
    required this.totalCount,
    this.limit,
    this.offset,
  });

  factory DbPaginatedResponse.fromJson(Map<String, dynamic> json) {
    return DbPaginatedResponse(
      items: (json['items'] as List?)?.cast<T>() ?? <T>[],
      totalCount: json['total_count'] ?? (json['items'] as List?)?.length ?? 0,
      limit: json['limit'],
      offset: json['offset'],
    );
  }
}

class DbWhiskyApiClient {
  final http.Client _client;

  DbWhiskyApiClient({http.Client? client}) : _client = client ?? http.Client();

  Future<Map<String, dynamic>> health() async {
    final uri = Uri.parse('${ApiClient.baseUrl}/api/db/health');
    final response = await _client.get(uri);
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    }
    throw Exception('API db/health failed: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> schema() async {
    final uri = Uri.parse('${ApiClient.baseUrl}/api/db/schema');
    final response = await _client.get(uri);
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    }
    throw Exception('API db/schema failed: ${response.statusCode}');
  }

  Future<DbPaginatedResponse<Map<String, dynamic>>> getWhiskies({int limit = 50, int offset = 0, String? q}) async {
    String url = '${ApiClient.baseUrl}/api/db/whiskies?limit=$limit&offset=$offset';
    if (q != null && q.isNotEmpty) {
      url += '&q=${Uri.encodeComponent(q)}';
    }
    final response = await _client.get(Uri.parse(url));
    if (response.statusCode == 200) {
      final Map<String, dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
      final items = (data['items'] as List?)?.map((e) => e as Map<String, dynamic>).toList() ?? [];
      return DbPaginatedResponse<Map<String, dynamic>>(
        items: items,
        totalCount: data['total_count'] ?? items.length,
        limit: data['limit'],
        offset: data['offset'],
      );
    } else if (response.statusCode == 404) {
      return DbPaginatedResponse<Map<String, dynamic>>(
        items: [],
        totalCount: 0,
        limit: limit,
        offset: offset,
      );
    }
    throw Exception('API db/whiskies failed: ${response.statusCode}');
  }

  Future<Map<String, dynamic>?> getWhiskyById(String id) async {
    final uri = Uri.parse('${ApiClient.baseUrl}/api/db/whiskies/${Uri.encodeComponent(id)}');
    final response = await _client.get(uri);
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    } else if (response.statusCode == 404) {
      return null;
    }
    throw Exception('API db/whiskies/id failed: ${response.statusCode}');
  }

  Future<DbPaginatedResponse<Map<String, dynamic>>> getDistilleries({int limit = 50, int offset = 0, String? q}) async {
    String url = '${ApiClient.baseUrl}/api/db/distilleries?limit=$limit&offset=$offset';
    if (q != null && q.isNotEmpty) {
      url += '&q=${Uri.encodeComponent(q)}';
    }
    final response = await _client.get(Uri.parse(url));
    if (response.statusCode == 200) {
      final Map<String, dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
      final items = (data['items'] as List?)?.map((e) => e as Map<String, dynamic>).toList() ?? [];
      return DbPaginatedResponse<Map<String, dynamic>>(
        items: items,
        totalCount: data['total_count'] ?? items.length,
        limit: data['limit'],
        offset: data['offset'],
      );
    } else if (response.statusCode == 404) {
      return DbPaginatedResponse<Map<String, dynamic>>(
        items: [],
        totalCount: 0,
        limit: limit,
        offset: offset,
      );
    }
    throw Exception('API db/distilleries failed: ${response.statusCode}');
  }

  Future<Map<String, dynamic>?> getDistilleryById(String id) async {
    final uri = Uri.parse('${ApiClient.baseUrl}/api/db/distilleries/${Uri.encodeComponent(id)}');
    final response = await _client.get(uri);
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    } else if (response.statusCode == 404) {
      return null;
    }
    throw Exception('API db/distilleries/id failed: ${response.statusCode}');
  }

  Future<Map<String, dynamic>?> getFlavorProfile(String whiskyId) async {
    final uri = Uri.parse('${ApiClient.baseUrl}/api/db/whiskies/${Uri.encodeComponent(whiskyId)}/flavor-profile');
    final response = await _client.get(uri);
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    } else if (response.statusCode == 404) {
      return null; // DB spec explicitly returns 404 if no profile exists
    }
    throw Exception('API flavor-profile failed: ${response.statusCode}');
  }

  Future<List<Map<String, dynamic>>> getTastingNotes(String whiskyId) async {
    final uri = Uri.parse('${ApiClient.baseUrl}/api/db/whiskies/${Uri.encodeComponent(whiskyId)}/tasting-notes');
    final response = await _client.get(uri);
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.map((e) => e as Map<String, dynamic>).toList();
    } else if (response.statusCode == 404) {
      return []; // Fallback empty
    }
    throw Exception('API tasting-notes failed: ${response.statusCode}');
  }

  Future<List<Map<String, dynamic>>> getPriceHistory(String whiskyId) async {
    final uri = Uri.parse('${ApiClient.baseUrl}/api/db/whiskies/${Uri.encodeComponent(whiskyId)}/price-history');
    final response = await _client.get(uri);
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.map((e) => e as Map<String, dynamic>).toList();
    } else if (response.statusCode == 404) {
      return []; // Fallback empty
    }
    throw Exception('API price-history failed: ${response.statusCode}');
  }
}
