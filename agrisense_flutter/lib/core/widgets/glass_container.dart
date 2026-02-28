import 'package:agrisense_flutter/core/theme/app_theme.dart';
import 'package:flutter/material.dart';

/// Soft card container with subtle shadow for light theme
class GlassContainer extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final BorderRadiusGeometry? borderRadius;
  final Color? color;

  const GlassContainer({
    super.key,
    required this.child,
    this.padding,
    this.borderRadius,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding ?? const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color ?? AppColors.bgWhite,
        borderRadius: borderRadius ?? BorderRadius.circular(16),
        border: Border.all(
          color: AppColors.primary.withOpacity(0.08),
        ),
        boxShadow: AppColors.softShadow,
      ),
      child: child,
    );
  }
}
