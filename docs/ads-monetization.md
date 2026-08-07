# Malt Radar — Ads & Monetization

Status: **AdMob banner configured · payments profile = individual · identity verification pending.**

---

## 1. AdMob IDs

> AdUnit/App IDs are **not secrets** — they are embedded in every compiled client by necessity (the SDK must know them at runtime). Committing them is safe.

| Item | Value | Where |
|------|-------|-------|
| **App ID** | `ca-app-pub-4569028808710145~3740329219` | `frontend/android/app/src/main/AndroidManifest.xml` → `<meta-data android:name="com.google.android.gms.ads.APPLICATION_ID">` |
| **Banner ad unit (LIVE)** | `ca-app-pub-4569028808710145/4150292677` | `frontend/lib/features/ads/ads_config.dart` → `productionBannerUnitId` |
| **Test banner unit** (dev) | `ca-app-pub-3940256099942544/6300978111` | Google's safe dev unit |

Build-time override (canary/test): `--dart-define=ADMOB_BANNER_ID=<unit>`.

## 2. Placement & format

- **Format: standard banner only.** No interstitial, no rewarded, no app-open.
- **Placement: pinned to the bottom of the main whisky list** (the primary content list) only.
- **NOT** placed on: detail screen, settings, auth, age gate, or any secondary surface.
- Rendered via `AdaptiveBanner` (frontend/lib/features/ads/) driven by `adsControllerProvider`.
- **Fail-soft:** if not Android (or ad fails to load) it renders a zero-height no-op — no blank box, no layout jump.
- **Platform:** ads render on **Android only**. `AdsConfig.platformEnabled` is `!kIsWeb && Android` → **no ads on the webapp**.

## 3. Compliance gating (age-gate + TR)

- Ads render **only after the age gate is `consented`** — the banner lives in `home_screen.dart`, reachable only past `AgeGateStatus.consented`. Minor users never see an ad.
- Alcohol/mature product: store ratings are **Play 18+/Mature**, **App Store 17+**.
- Editorial/ad copy stays **neutral, non-incentivizing** (no "mutlaka dene", no "senin için seçtik").
- No pricing data is rendered anywhere (product rule).
- Ad display begins after age-gate approval; AdMob mediation serves age-appropriate creative for a mature app.

## 4. Payments identity — D‑U‑N‑S decision tree

**Current decision: INDIVIDUAL (bireysel) payments profile → D‑U‑N‑S NOT required.** Identity verification is in progress.

| Payments profile | D‑U‑N‑S required? | Path | Cost / time |
|------------------|-------------------|------|-------------|
| **Individual** (current) | ❌ **No** | Verify with national ID + **W-8BEN** (TR) | $0 · ~days |
| **Business / Organization** | ✅ Yes | D‑U‑N‑S number | see below |

### If a business is ever required

- **D‑U‑N‑S request itself is free.** D&B earns from credit/identity-upsell products — the number alone costs nothing; do **not** pay for "credit builder" / "identity protection" extras.
- **Free official registration form** → 2–4 weeks.
- **Paid express** → ~$1xx · same day (only if time-critical).
- A D‑U‑N‑S is tied to a registered legal entity with a verifiable address; a sole natural person cannot obtain one for a "business verification".

**Next action (pending):** complete individual identity verification; fill W-8BEN tax info when prompted. No D‑U‑N‑S purchase needed.

## 5. Go-live checklist

1. Keep dev using the **Google test unit** `6300978111` (set via `--dart-define=ADMOB_BANNER_ID`).
2. Release build uses the live unit `4150292677` (default in `ads_config.dart`).
3. Confirm banner only on main-list bottom; age-gate-gated.
4. Complete individual payments verification → ads start filling once the app is live on Play.

---

_Last updated: 2026-08-06 · This file is the monetization reference; code truth lives in `ads_config.dart` + `AndroidManifest.xml`._
