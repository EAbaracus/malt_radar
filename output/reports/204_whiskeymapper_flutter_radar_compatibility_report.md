# Whiskey Mapper Flutter Radar Compatibility Report

## Finding
The imported Whiskey Mapper rows store quantitative component profiles, not native Malt Radar 7-axis profiles.

Whiskey Mapper format:
```json
{
  "component_1": "0.25598895504360725",
  "component_2": "0.4537593859035136",
  "component_3": "0.46744839881686595"
}
```

Malt Radar production format:
```json
{
  "fruity": 0.0,
  "sweet": 9.0,
  "spicy": 0.0,
  "smoky_peaty": 2.0,
  "oak_cask": 1.0,
  "floral_herbal": 0.0,
  "malty_cereal": 7.0
}
```

## Risk
- The previous radar chart did not crash on missing 7-axis keys, but component-only profiles rendered as all-zero radar values.
- Similar flavor comparison could compare only overlapping raw keys, which is not useful when production rows use 7 axes and Whiskey Mapper rows use 3 components.

## Mitigation
- `normalizeFlavorProfileJson` was added as a shared Flutter normalization layer.
- Existing 7-axis profile values are preserved.
- Whiskey Mapper component profiles are converted to safe 7-axis values for display and similarity calculations:
  - `component_1` contributes to fruity, sweet, malty, floral
  - `component_2` contributes to sweet, spicy, oak
  - `component_3` contributes to smoky, oak, malty
- Component values in the imported 0-1 range are scaled to the radar's existing 0-10 display range.

## Test Coverage
- Added `frontend/test/flavor_profile_normalizer_test.dart`.
- The test verifies that 7-axis profiles remain unchanged.
- The test verifies that Whiskey Mapper `component_1/2/3` profiles produce all 7 radar axes with non-zero values.

## Result
Radar chart compatibility is safe. Whiskey Mapper profiles are parseable and renderable without DB mutation.
