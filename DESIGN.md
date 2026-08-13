---
name: Malt Radar — "The Modern Cellar"
description: Design system for the Malt Radar whisky-discovery app (Flutter, dark-only). Single source of truth for tokens; syncs with the implemented app_theme + brand medallion identity.
colors:
  # ---- Obsidian base + brand ember (applied 2026-08-09, PR #34) ----
  caskChar: '#1A120B'           # background / darkest ground (replaces old #0F0F0F)
  surface: '#241A10'            # card ground
  surfaceElevated: '#2B1F14'    # gradient top-light / elevated card
  parchment: '#EDE1C8'          # on-surface text, light ground
  parchmentLt: '#F5ECD8'
  inkSoft: '#2B1F14'
  copper: '#A6672C'             # PRIMARY accent (replaces old gold #D4AF37)
  copperDim: '#8A5424'
  verdigris: '#5C7A6E'          # SECONDARY accent / badge (replaces old amber #B8860B)
  brass: '#C9A227'              # amblem (medallion seal ring + needle) ONLY — never general UI
  oxblood: '#6B1E23'            # rare warning / special badge ground
  oxbloodLt: '#D6645C'          # oxblood light shade — icon/text on dark grounds (4.99:1 on caskChar)
  success: '#5C7A6E'            # positive state = verdigris family (NO Material green)
  textPrimary: '#EDE1C8'
  textSecondary: '#BDB2A0'
  textMuted: '#8C8071'
typography:
  display:
    fontFamily: Fraunces
    fontWeights: [500, 600]
    letterSpacing: 0            # no tracking; editorial serif carries the voice
    usage: headlineLarge (32/600), headlineMedium (24/500), titleLarge (20/600)
  body:
    fontFamily: SourceSerif4    # proporcional serif body (replaces Playfair/Inter body split)
    fontWeight: 400
    usage: bodyMedium (16/400)
  ui:
    fontFamily: Inter           # functional / microcopy / labels
    usage: labels, inputs, technical detail (ABV/Region/Age), button text
  medallion:
    fontFamily: CourierPrime    # emblem numeral/letter (moral stamp) only
    usage: Medallion seal characters
  assets: 4 .ttf bundled offline (no google_fonts runtime fetch): Fraunces, SourceSerif4, Inter, CourierPrime
rounded:
  xs: 10
  sm: 12
  md: 16
  lg: 20
  xl: 24
  pill: 999
spacing:
  base: 8                       # all rhythm is multiples of 8
  container-padding: 20
  gutter: 16
  stack-sm: 8
  stack-md: 16
  stack-lg: 24
  section-gap: 32
layout:
  grid: mobile-first Fluid; 4-col mobile, cards span full or 2-col discovery feed
  margin: 20 horizontal main content
  safe-area: bottom nav + FAB respect gesture insets
elevation:
  - tonal layering + hairline borders (1px) over heavy shadows
  - border inner: white 10%; active: copper 40%
  - glass (backdrop blur 20) reserved for overlays/modals/frosted sheets, not default card
---

# Malt Radar Design System

The design concept is **"The Modern Cellar"** — a digital mirror of a premium,
dark, climate-controlled whisky vault: deep obsidian grounds so amber liquid and
the brand ember glow on-screen. Connoisseur-grade craftsmanship, quiet
confidence, tactile quality. Not a "dusty pub" aesthetic.

> **Contract:** Tokens above are normative and match the implemented app
> (`app_theme.dart`, `app_theme_colors.dart`, 2026-08-09). Change the tokens here
> AND in code together; a drift is a bug.

## Colors

Strictly dark-mode (low-light tasting-room feel).

- **caskChar `#1A120B`** — base ground. Backs the radial brand wash.
- **surface `#241A10` / surfaceElevated `#2B1F14`** — cards and elevated ground.
- **copper `#A6672C`** — PRIMARY: high-intent actions, branding, active states.
- **verdigris `#5C7A6E`** — SECONDARY: badges, certification, supporting accents.
- **brass `#C9A227`** — amblem/medallion seal ring + needle ONLY. Grep-guard:
  `grep -rn "C9A227" frontend/lib` must match only `app_theme_colors.dart`.
- **oxblood `#6B1E23`** — rare warning/special badge **ground only**. As TEXT
  or icon color on dark grounds it fails WCAG (1.62:1) — use `oxbloodLt`
  `#D6645C` (4.99:1) for on-dark error glyphs/text. `success` lives in the
  verdigris family, never a Material green.
- **Neutral text ramp:** parchment → textSecondary → textMuted for hierarchy.

Gradient wash used by home/detail/lists:
`RadialGradient([surfaceElevated, caskChar, surface])` — warm obsidian, no cold
blue-grey (`#1E1E2C`/`#040406`) and no Material green (`#4CAF50`; certification
uses verdigris now).

## Typography

High-contrast editorial + functional pairing (applied in `app_theme.dart`):

- **Headlines:** `Fraunces` (serif, editorial). Use sparingly — heroes, bottle
  names, section titles. Letter spacing 0.
- **Body:** `SourceSerif4` — readable proposional serif for lists and detail.
- **UI/microcopy:** `Inter` — neutral, high-readability on small screens;
  technical spec labels (ABV, Region, Age) use tighter spacing/uppercase feel.
- **Medallion:** `CourierPrime` — emblem character only.

All four faces are bundled `.ttf` under `assets/fonts/`; there is **no
google_fonts runtime fetch** (offline-safe, faster web boot).

## Layout & Spacing

- **Fluid grid**, mobile-first, Material 3 structure with luxury whitespace.
- **Margin:** 20px horizontal on main content. **Rhythm:** multiples of 8
  (stack 8/16/24; section gap 32). **Cards:** full-width or 2-col discovery.
- **Safe areas:** bottom nav / FAB respect gesture insets.

## Elevation & Depth

Hierarchy via **tonal layering + hairline borders**, not heavy shadow:

- base → surface → overlay (modals/sheets get `BackdropFilter` blur ~20 +
  10% white tint = "frosted obsidian").
- Hairline borders: inner white 10%; active copper 40%.
- **Glow** kept subtle and rare (e.g. tasting-note primary action), 15% opacity.

## Shapes

Generous, approachable to contrast the serious palette (weights measured in
code: radius 12/16/20/24 dominate):

- **Cards/containers:** `md 16` default, `lg 20`/`xl 24` for hero surfaces.
- **Buttons:** `lg 16-20`; secondary pill.
- **Inputs:** `sm 12`.
- **Images/highlights:** min `sm 12-16` mask unless full-bleed hero.

## Components

### Buttons
- **Primary:** solid `copper`, dark text (`onPrimary=background`), radius 16-20.
- **Secondary:** transparent + 1px copper border, light text.
- **Ghost:** no border, `textSecondary`, for Cancel/Back.

### Cask Card
Surface `#241A10`, radius 20-24, hairline border white 8-10%, padding 20;
imagery high-contrast with a subtle bottom dark gradient so light text stays
legible.

### Inputs
`#1F170E` ground (caskChar-family inset step: caskChar `#1A120B` → input
`#1F170E` → surface `#241A10`; NOT generic `#121212`), hairline border,
focused state = copper
border + subtle glow; prefix icon copper.

### Tasting Chips
Pill, white 5-10% ground/border, `Inter` label, `textSecondary`.

### Navigation
Bottom nav: active = copper icon, inactive = muted gray; glass/tonal ground.
(Current impl is a Material `BottomNavigationBar` — upgrade to the glassmorphic
fill once the login/UI pass lands, keeping copper active state.)

### Medallion
`CustomPainter` brand seal (master/icon/micro). Brass ring + needle only.
One-shot sweep animation (0→410→360), loop forbidden. Shown on age gate,
loading, list-empty/hero.

## Do's and Don'ts

- DO use only tokens above in UI code — no stray hardcoded hex outside
  `app_theme_colors.dart`/`app_theme.dart`. `grep -rn "0xFF" lib` should
  surface only theme files.
- DO keep `brass` to the amblem; UI emphasis is copper + verdigris.
- DO use `Fraunces` for headlines and `SourceSerif4`/`Inter` per role.
- DON'T introduce cold blue-grey gradients or Material-500 greens.
- DON'T render price anywhere (Product Rule — UI and API both).
- DON'T scale text with viewport width; keep font sizes stable.
- DON'T use nested cards, decorative blobs, or atmospheric filler assets.
