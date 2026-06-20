# Flutter and Android App Proguard Rules
# By default, Flutter handles obfuscation of Dart code at compile-time.
# These rules manage the Java/Kotlin Android wrapper code.

# Keep Flutter embedding and plugin classes
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.embedding.** { *; }
-keep class io.flutter.plugins.** { *; }

# Prevent obfuscation of platform channel classes or native entry points if any
-keep class com.example.malt_radar.MainActivity { *; }

# Suppress warnings for missing com.google.android.play.core classes
-dontwarn com.google.android.play.core.**

