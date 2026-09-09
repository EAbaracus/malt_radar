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
# NOTE: Kotlin source still lives under com.example.malt_radar even though
# applicationId/namespace is com.maltradar.app — keep the real class path.
-keep class com.maltradar.app.MainActivity { *; }

# WorkManager + Room (pulled in via google_mobile_ads): R8 full-mode breaks
# reflective RoomDatabase instantiation -> "Failed to create WorkDatabase"
-keep class androidx.work.** { *; }
-keep class * extends androidx.room.RoomDatabase
-keep @androidx.room.Entity class *
-dontwarn androidx.work.**

# Suppress warnings for missing com.google.android.play.core classes
-dontwarn com.google.android.play.core.**

