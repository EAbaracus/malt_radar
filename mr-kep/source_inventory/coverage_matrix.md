# Coverage Matrix — MR-KEP P62

Source × Field coverage. Legend: **Tam** = full/reliable coverage · **Kısmi** = partial/conditional · **Yok** = not covered.

> Statuses are **reasoned assessments**, not crawled evidence (no data fetched this phase). `Kısmi` marks fields a source touches incidentally or with lower trust; `Yok` means it does not address the field at all.

| Source | flavor_profile | tasting_notes | abv | cask_type | age | distillery | region | country | image | awards | limited_release | bottler |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Official Distillery Websites | Kısmi | Kısmi | Tam | Tam | Tam | Tam | Tam | Tam | Tam | Kısmi | Tam | Tam |
| Scotch Whisky Association | Yok | Yok | Yok | Yok | Yok | Kısmi | Tam | Tam | Yok | Yok | Yok | Yok |
| World Atlas of Whisky | Tam | Tam | Kısmi | Kısmi | Kısmi | Tam | Tam | Tam | Yok | Yok | Kısmi | Kısmi |
| Michael Jackson Complete Guide | Tam | Tam | Kısmi | Kısmi | Kısmi | Tam | Tam | Tam | Yok | Kısmi | Kısmi | Kısmi |
| Dave Broom sources | Tam | Tam | Kısmi | Kısmi | Kısmi | Tam | Tam | Tam | Yok | Yok | Kısmi | Kısmi |
| WhiskyFun | Tam | Tam | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Yok | Yok | Kısmi | Kısmi |
| Whisky Advocate | Kısmi | Tam | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Yok | Tam | Kısmi | Kısmi |
| Whiskybase | Kısmi | Kısmi | Tam | Tam | Tam | Tam | Tam | Tam | Kısmi | Kısmi | Tam | Tam |
| Master of Malt | Kısmi | Tam | Tam | Tam | Tam | Kısmi | Kısmi | Kısmi | Tam | Yok | Tam | Tam |
| The Whisky Exchange | Kısmi | Tam | Tam | Tam | Tam | Kısmi | Kısmi | Kısmi | Tam | Yok | Tam | Tam |
| Distiller magazines | Kısmi | Tam | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Tam | Kısmi | Kısmi |
| Whisky Auctioneer | Yok | Kısmi | Tam | Tam | Tam | Kısmi | Kısmi | Kısmi | Tam | Yok | Tam | Tam |
| Wayback Machine | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Kısmi | Kısmı | Kısmi |

## Reading the matrix

- **Identity row (distillery/region/country):** only T1 sources show `Tam`. T2/T3 show `Kısmi` (named, not certifying — T1 ceiling applies).
- **Sensory row (flavor/tasting):** T2 experts + T1 reference authors dominate; retailers `Kısmi`.
- **Specs row (abv/cask/age/bottler):** T1 official + structured T2 (Whiskybase, retailers) `Tam`; experts `Kısmi` (incidental).
- **awards:** Whisky Advocate + Distiller magazines `Tam`.
- **image:** T1 + retailers `Tam`/`Kısmi` but copyright-restricted (see `licensing_notes.md`).
- **Wayback Machine:** `Kısmi` everywhere — it proxies whatever was captured, used only to verify/snapshot.
