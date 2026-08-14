import 'package:flutter/widgets.dart';

/// Near-bottom detection for the paginated catalog list (D-hardening H1
/// Task 2).
///
/// Returns true when the scroll position has reached within [thresholdPx]
/// pixels of the end of the scrollable content — the signal that should fire
/// `catalogPaginationProvider.notifier.loadMore()`. Lists with no scrollable
/// extent (everything fits on screen) and metrics without valid dimensions
/// never trigger.
bool shouldLoadMoreCatalog(ScrollMetrics metrics, {double thresholdPx = 400}) {
  if (!metrics.hasContentDimensions) return false;
  final maxExtent = metrics.maxScrollExtent;
  if (maxExtent <= 0) return false;
  return metrics.pixels >= maxExtent - thresholdPx;
}
