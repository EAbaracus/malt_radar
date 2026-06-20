# Whiskey Mapper Specific Endpoint Schema Report

## Safety
- Production DB write: NO
- Raw inspection only: YES

## Endpoint
- `POST https://whiskeymapper.com/api/whiskey_specific`
- Body example: `{"whiskey":"Aberlour 10"}`

## Top-level keys
- `descriptive`: `list`
- `flavors`: `list`
- `similars`: `list`
- `stats`: `list`

## Descriptive
- Raw length: 40
- Term count: 20
- Weight count: 20

### Term weights
- `sherry`: 1.44
- `fruit`: 1.16
- `spicy`: 1.08
- `honey`: 0.92
- `vanilla`: 0.6
- `raisin`: 0.6
- `apple`: 0.56
- `malt`: 0.48
- `toffee`: 0.4
- `cask`: 0.36
- `dry`: 0.36
- `wood`: 0.36
- `winey`: 0.32
- `rich`: 0.32
- `chocolate`: 0.28
- `oak`: 0.28
- `cinnamon`: 0.28
- `orange`: 0.24
- `smoky`: 0.24
- `caramel`: 0.24

## Flavors
- Vector length: 13
- Values: `[3.8222222222222224, 5.481481481481482, 3.286624203821655, 2.8056258790436006, 6.240074250861842, 8.46137566137566, 2.977777777777778, 1.3555555555555554, 2.9841269841269833, 2.2024691358024695, 2.469160997732427, 4.229828850855745, 2.6222222222222227]`

## Similars
- Raw length: 40
- Pair count: 20

- `Glenfarclas 12`: 0.9222483729031841
- `Balvenie 12 Doublewood`: 0.8922823718610917
- `Aberlour 12 Double Cask Matured`: 0.8856782473611654
- `Aberlour 16`: 0.852212939007299
- `Glenfiddich 15`: 0.8478143064383248
- `Glenfarclas 15`: 0.8469377983516547
- `Aberlour A'bunadh`: 0.8443264011308933
- `BenRiach 12 Sherry Matured`: 0.839534684169597
- `Glenfarclas 105 Cask Strength`: 0.8322850195129642
- `Glenfarclas 10`: 0.831906208513091
- `GlenDronach 12 Original`: 0.8314027103107927
- `Aberlour 12 Non Chill Filtered`: 0.8213174663746539
- `Tomatin 12`: 0.819127497699482
- `Dalmore 15`: 0.8173513196231169
- `Bunnahabhain 12`: 0.8124443989223343
- `Glenfarclas 21`: 0.8086421109123663
- `Macallan 18 Sherry`: 0.8065264495923629
- `Macallan 12 Sherry`: 0.7979656104417
- `Glenfarclas 17`: 0.7971467489057619
- `Glenfiddich 18`: 0.7964710864485722

## Stats
- Raw length: 11
- Values: `['Aberlour 10', 32, 78.97, 7.08, 'Scotch (Speyside)', 'Aberlour', 'Aberlour', 'Pernod Ricard', 57.467053, -3.228199, 17]`

## Interpretation
- `descriptive` can be used as weighted tasting tags.
- `flavors` can be stored as a source vector candidate, but axis meanings are unknown.
- `similars` can be used for recommendation validation/dry-run only.
- `stats` can be joined with `whiskey_table`.