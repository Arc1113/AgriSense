import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../services/storage/scan_history_service.dart';

/// Displays saved scan history from local storage
class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgLight,
      appBar: AppBar(
        backgroundColor: AppColors.bgLight,
        title: const Text(
          'Scan History',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        actions: [
          Consumer<ScanHistoryService>(
            builder: (context, history, _) {
              if (history.count == 0) return const SizedBox();
              return IconButton(
                icon: const Icon(Icons.delete_outline),
                onPressed: () => _confirmClear(context, history),
              );
            },
          ),
        ],
      ),
      body: Consumer<ScanHistoryService>(
        builder: (context, historyService, _) {
          final items = historyService.history;

          if (items.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.history_rounded,
                    size: 64,
                    color: AppColors.textMuted.withOpacity(0.3),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'No scan history yet',
                    style: TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Your scan results will appear here',
                    style: TextStyle(
                      color: AppColors.textMuted.withOpacity(0.6),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              final result = item['result'] as Map<String, dynamic>?;
              final comparison = item['comparison'] as Map<String, dynamic>?;
              final savedAt = item['saved_at'] as String?;

              if (result == null) return const SizedBox();

              final disease = result['disease'] ?? 'Unknown';
              final confidence = (result['confidence'] ?? 0.0) as double;
              final modelUsed = result['model_used'] ?? 'Unknown';
              final isHealthy = result['is_healthy'] ?? false;
              final inferenceTime = result['inference_time_ms'] ?? 0.0;

              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.bgCard,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: isHealthy
                          ? AppColors.success.withOpacity(0.2)
                          : AppColors.error.withOpacity(0.1),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 40,
                            height: 40,
                            decoration: BoxDecoration(
                              color: (isHealthy
                                      ? AppColors.success
                                      : AppColors.error)
                                  .withOpacity(0.15),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Icon(
                              isHealthy
                                  ? Icons.eco_rounded
                                  : Icons.bug_report_rounded,
                              color: isHealthy
                                  ? AppColors.success
                                  : AppColors.error,
                              size: 22,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  disease,
                                  style: const TextStyle(
                                    color: AppColors.textPrimary,
                                    fontSize: 16,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                Text(
                                  '$modelUsed • ${(confidence * 100).toStringAsFixed(1)}% • ${(inferenceTime as num).toStringAsFixed(0)} ms',
                                  style: const TextStyle(
                                    color: AppColors.textMuted,
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          if (comparison != null)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 3,
                              ),
                              decoration: BoxDecoration(
                                color: AppColors.accent.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: const Text(
                                'VS',
                                style: TextStyle(
                                  color: AppColors.accent,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          IconButton(
                            icon: const Icon(
                              Icons.delete_outline,
                              color: AppColors.textMuted,
                              size: 18,
                            ),
                            onPressed: () {
                              historyService.deleteScan(item['id']);
                            },
                          ),
                        ],
                      ),
                      if (savedAt != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          _formatDate(savedAt),
                          style: TextStyle(
                            color: AppColors.textMuted.withOpacity(0.5),
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }

  String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      final now = DateTime.now();
      final diff = now.difference(dt);

      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays < 7) return '${diff.inDays}d ago';
      return '${dt.month}/${dt.day}/${dt.year}';
    } catch (_) {
      return '';
    }
  }

  void _confirmClear(BuildContext context, ScanHistoryService history) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.bgWhite,
        title: const Text('Clear History?', style: TextStyle(color: AppColors.textPrimary)),
        content: const Text(
          'This will delete all saved scan results.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              history.clearHistory();
              Navigator.pop(ctx);
            },
            child: const Text('Clear', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
  }
}
