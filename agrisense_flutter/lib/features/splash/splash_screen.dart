import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../services/ml/disease_classifier.dart';
import '../home/home_screen.dart';

/// Animated splash screen matching the web app's splash
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  late AnimationController _progressController;
  late AnimationController _pulseController;
  late AnimationController _fadeController;
  String _statusText = 'Initializing AI...';

  @override
  void initState() {
    super.initState();

    _progressController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    );

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );

    _startLoading();
  }

  Future<void> _startLoading() async {
    _progressController.forward();

    // Simulate progress stages
    await Future.delayed(const Duration(milliseconds: 500));
    if (!mounted) return;
    setState(() => _statusText = 'Loading ML models...');

    // Actually load models
    final classifier = context.read<DiseaseClassifier>();
    await classifier.initialize();

    if (!mounted) return;
    setState(() {
      _statusText = 'Preparing camera...';
    });

    await Future.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    setState(() => _statusText = 'Ready!');

    // Wait for progress bar to finish
    await Future.delayed(const Duration(milliseconds: 500));

    // Navigate to home
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (_, __, ___) => const HomeScreen(),
        transitionsBuilder: (_, animation, __, child) {
          return FadeTransition(opacity: animation, child: child);
        },
        transitionDuration: const Duration(milliseconds: 600),
      ),
    );
  }

  @override
  void dispose() {
    _progressController.dispose();
    _pulseController.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgLight,
      body: Stack(
        children: [
          // Background gradient orbs
          Positioned(
            top: MediaQuery.of(context).size.height * 0.15,
            left: -60,
            child: _buildGlowOrb(AppColors.primary.withOpacity(0.08), 250),
          ),
          Positioned(
            bottom: MediaQuery.of(context).size.height * 0.2,
            right: -40,
            child: _buildGlowOrb(AppColors.accent.withOpacity(0.06), 200),
          ),
          Positioned(
            top: MediaQuery.of(context).size.height * 0.5,
            left: MediaQuery.of(context).size.width * 0.3,
            child: _buildGlowOrb(AppColors.primaryLight.withOpacity(0.06), 150),
          ),

          // Main content
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Spacer(flex: 3),

                // Animated logo
                AnimatedBuilder(
                  animation: _pulseController,
                  builder: (_, __) {
                    return Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            AppColors.primary,
                            AppColors.primaryDark,
                          ],
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.primary
                                .withOpacity(0.3 + _pulseController.value * 0.2),
                            blurRadius: 30 + _pulseController.value * 20,
                            spreadRadius: 5,
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.eco_rounded,
                        size: 56,
                        color: Colors.white,
                      ),
                    );
                  },
                ),

                const SizedBox(height: 32),

                // App name
                RichText(
                  text: const TextSpan(
                    style: TextStyle(
                      fontSize: 36,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.5,
                    ),
                    children: [
                      TextSpan(
                        text: 'Agri',
                        style: TextStyle(color: AppColors.textPrimary),
                      ),
                      TextSpan(
                        text: 'Sense',
                        style: TextStyle(color: AppColors.primary),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 8),

                const Text(
                  'AI-Powered Plant Health Analysis',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),

                const SizedBox(height: 48),

                // Progress bar
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 60),
                  child: Column(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: AnimatedBuilder(
                          animation: _progressController,
                          builder: (_, __) {
                            return LinearProgressIndicator(
                              value: _progressController.value,
                              minHeight: 4,
                              backgroundColor:
                                  AppColors.textMuted.withOpacity(0.2),
                              valueColor: const AlwaysStoppedAnimation<Color>(
                                AppColors.primary,
                              ),
                            );
                          },
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        _statusText,
                        style: const TextStyle(
                          color: AppColors.textMuted,
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),

                const Spacer(flex: 2),

                // Footer
                Text(
                  'Powered by Deep Learning',
                  style: TextStyle(
                    color: AppColors.textMuted.withOpacity(0.5),
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 40),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGlowOrb(Color color, double size) {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (_, __) {
        return Container(
          width: size + _pulseController.value * 20,
          height: size + _pulseController.value * 20,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color,
          ),
        );
      },
    );
  }
}
