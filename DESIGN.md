---
name: Obsidian & Amber
colors:
  surface: '#16130b'
  surface-dim: '#16130b'
  surface-bright: '#3d392f'
  surface-container-lowest: '#110e07'
  surface-container-low: '#1f1b13'
  surface-container: '#231f17'
  surface-container-high: '#2d2a21'
  surface-container-highest: '#38342b'
  on-surface: '#eae1d4'
  on-surface-variant: '#d0c5af'
  inverse-surface: '#eae1d4'
  inverse-on-surface: '#343027'
  outline: '#99907c'
  outline-variant: '#4d4635'
  surface-tint: '#e9c349'
  primary: '#f2ca50'
  on-primary: '#3c2f00'
  primary-container: '#d4af37'
  on-primary-container: '#554300'
  inverse-primary: '#735c00'
  secondary: '#f7bd48'
  on-secondary: '#412d00'
  secondary-container: '#ba880f'
  on-secondary-container: '#392700'
  tertiary: '#bfcdff'
  on-tertiary: '#082b72'
  tertiary-container: '#97b0ff'
  on-tertiary-container: '#254188'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffe088'
  primary-fixed-dim: '#e9c349'
  on-primary-fixed: '#241a00'
  on-primary-fixed-variant: '#574500'
  secondary-fixed: '#ffdea6'
  secondary-fixed-dim: '#f7bd48'
  on-secondary-fixed: '#271900'
  on-secondary-fixed-variant: '#5d4200'
  tertiary-fixed: '#dbe1ff'
  tertiary-fixed-dim: '#b4c5ff'
  on-tertiary-fixed: '#00174b'
  on-tertiary-fixed-variant: '#27438a'
  background: '#16130b'
  on-background: '#eae1d4'
  surface-variant: '#38342b'
typography:
  display-lg:
    fontFamily: Playfair Display
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: Playfair Display
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Playfair Display
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.1em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding: 20px
  gutter: 16px
  stack-sm: 4px
  stack-md: 12px
  stack-lg: 24px
  section-gap: 40px
---

## Brand & Style

The design system is centered on the concept of "The Modern Cellar"—a digital environment that mirrors the sophisticated, dark, and climate-controlled atmosphere of a premium whisky vault. It targets connoisseurs and enthusiasts who value craftsmanship, precision, and luxury without the weight of traditional, "dusty" pub aesthetics.

The visual style is **Modern Minimalist with Glassmorphic accents**. It utilizes deep obsidian backgrounds to allow high-quality product photography of amber liquids to "glow" from within the screen. The emotional response is one of exclusivity, quiet confidence, and tactile quality. By combining sharp typographic hierarchies with soft, translucent surfaces, the interface feels both technologically advanced and timelessly elegant.

## Colors

The palette is strictly dark-mode to emphasize the "discovery" aspect of the product, mimicking low-light tasting rooms. 

- **Obsidian (#0F0F0F):** The foundational base. It provides infinite depth and high contrast for gold accents.
- **Surface (#1A1A1A):** Used for primary containers, elevating them slightly from the background.
- **Primary Gold (#D4AF37):** Reserved for high-intent actions, branding elements, and rating indicators.
- **Amber Secondary (#B8860B):** Used for subtle accents, active states, and decorative borders.
- **Functional Grays:** A range of desaturated neutrals used to maintain hierarchy without distracting from the golden focus.

## Typography

This design system uses a high-contrast typographic pairing to bridge the gap between editorial luxury and functional clarity.

- **Headlines:** Playfair Display provides a serif elegance that evokes premium spirit labels and high-end journalism. Use "Display" sizes sparingly for hero sections and bottle names.
- **Body & UI:** Inter is used for all functional text. Its neutral, systematic nature ensures high readability on small screens.
- **Labels:** Small labels use increased letter spacing and uppercase styling to provide a modern, "technical specification" feel, ideal for distillery details (ABV, Region, Age).

## Layout & Spacing

The layout follows a **Fluid Grid** model optimized for mobile devices, adhering to Material 3's structural foundations while increasing whitespace for a luxury feel.

- **Margins:** A standard 20px horizontal margin is maintained for all main content.
- **Vertical Rhythm:** Elements are spaced in multiples of 8px. Content groups use 24px spacing, while distinct sections use 40px to provide visual "breathing room."
- **Grids:** Use a 4-column grid for mobile screens. Content cards typically span the full width or 2 columns for "discovery" feeds.
- **Safe Areas:** Ensure bottom navigation and floating action buttons respect the system gesture areas.

## Elevation & Depth

Hierarchy is established through **Glassmorphism** and **Tonal Layering** rather than traditional heavy shadows.

- **The Base:** Background (#0F0F0F).
- **The Surface:** Cards and containers use #1A1A1A.
- **The Overlay:** Modal sheets and floating menus use a semi-transparent blur (Backdrop Filter: blur 20px) with a 10% white tint to create a "frosted obsidian" effect.
- **Borders:** Instead of shadows, use 1px "Hairline" borders. 
    - Inner borders: #FFFFFF at 10% opacity.
    - Active/Selected borders: #D4AF37 at 40% opacity.
- **Glow:** For primary elements like the "Tasting Note" button, a subtle amber outer glow (spread 10px, 15% opacity) can be used to simulate light passing through whisky.

## Shapes

The shape language is generous and approachable, contrasting with the dark, serious color palette.

- **Primary Cards:** Use a 24px corner radius (Rounded-XL) to create a soft, high-end furniture-like feel.
- **Buttons:** Use 16px (Rounded-LG) or full-pill shapes for secondary actions.
- **Input Fields:** Use 12px (Soft/Rounded) to maintain a modern look.
- **Images:** Bottle photography should always be masked with a minimum of 16px radius unless it is a full-bleed hero element.

## Components

### Buttons
- **Primary:** Solid Gold (#D4AF37) with Obsidian text. 16px radius.
- **Secondary:** Transparent with 1px Gold border. White text.
- **Ghost:** No border, secondary text color, used for "Cancel" or "Back."

### Cards (The "Cask" Card)
- Surface: #1A1A1A.
- Corner Radius: 24px.
- Border: 1px #FFFFFF (8% opacity).
- Padding: 20px.
- Imagery: Should feature high-contrast photography with a slight dark gradient at the bottom to ensure white text overlay is legible.

### Inputs
- Background: #121212.
- Border: 1px #A0A0A0 (20% opacity).
- Focused State: Border changes to #D4AF37 with a subtle glow.

### Tasting Chips
- Small, pill-shaped elements for flavor profiles (e.g., "Peaty", "Sherry").
- Background: #FFFFFF (5% opacity).
- Border: 1px #FFFFFF (10% opacity).
- Text: Label-sm, Secondary text color.

### Navigation
- Follows Material 3 Navigation Bar specs but with a glassmorphic background blur.
- Active icon: Gold (#D4AF37).
- Inactive icon: Gray (#A0A0A0).
