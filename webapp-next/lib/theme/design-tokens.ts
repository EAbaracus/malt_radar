// Design tokens ported from DESIGN.md — "Modern Cellar" dark theme
// These must EXACTLY match the Flutter app's app_theme_colors.dart
// Grep guard: no hardcoded hex outside this file in components
export const designTokens = {
  colors: {
    caskChar: '#1A120B',         // background / darkest ground
    surface: '#241A10',          // card ground
    surfaceElevated: '#2B1F14',  // elevated surfaces
    parchment: '#EDE1C8',        // text primary
    parchmentLt: '#F5ECD8',      // text light
    inkSoft: '#2B1F14',          // ink
    copper: '#A6672C',           // PRIMARY accent
    copperDim: '#8A5424',        // copper dimmer
    verdigris: '#5C7A6E',        // SECONDARY accent / badges
    brass: '#C9A227',            // amblem (medallion only)
    oxblood: '#6B1E23',          // warning / special badges (ground only)
    oxbloodLt: '#D6645C',        // oxblood text on dark
    textPrimary: '#EDE1C8',
    textSecondary: '#BDB2A0',
    textMuted: '#8C8071',
    success: '#5C7A6E',          // verdigris family
  },
  spacing: {
    base: 8,
    containerPadding: 20,
    gutter: 16,
    stackSm: 8,
    stackMd: 16,
    stackLg: 24,
    sectionGap: 32,
  },
  borderRadius: {
    xs: 10,
    sm: 12,
    md: 16,
    lg: 20,
    xl: 24,
    pill: 999,
  },
} as const;

export type DesignTokens = typeof designTokens;