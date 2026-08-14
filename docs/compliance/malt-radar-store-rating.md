# Malt Radar — Store Age Rating & Content Compliance

Applies to the public build of Malt Radar (alcohol content). Companion to the
in-app age gate at `frontend/lib/features/compliance/`.

## In-app age gate (already implemented)

- First-launch modal (country → legal minimum age) before any content renders.
- Underage → locked, no content.
- Consent persisted in local Drift `UserSettings` (`age_gate` = `<CC>|<minAge>`).
- Re-verify control under **Settings → Legal / Age**.

## Required store listings (store-side, NOT in the binary)

Google Play and App Store compute the rating from a store-side questionnaire.
There is no manifest / Info.plist field to set it; it must be answered when
submitting or updating the app.

### Google Play Console

1. **Store presence → Content → Content rating** → complete the questionnaire:
   - In this app, the **consumer is under the age of 13?** → **No** (17+/adult).
   - Toggle **Yes** for: "The app contains references to alcohol / displays,
     promotes, or makes alcohol purchase easy" → select the **Alcohol**
     descriptor (usage: conspicuous/consumption).
   - Advertises or promotes alcohol → **No** (Malt Radar is a neutral reference /
     discovery catalog, not an advertiser — keep it that way).
2. Resulting rating: **Mature (18+)** for the alcohol descriptor.

### Apple App Store Connect

1. **App Information → Age Rating** questionnaire, **Alcohol, Tobacco, or Drug
   Use or References**:
   - **Consumption / references** → **Frequent/Intense** → results in **17+**.
   - **Advertise/sponsor/promote** → **No**.
2. Resulting rating: **17+**.
3. Add a note in the **Review notes**: *"Age-gated informational catalog of
   whisky expressions; no sales, no advertising, no prices."*

## Regional notes

- **Türkiye:** alcohol promotion is tightly restricted (Law 4250, TADAB
  Regulation arts. 20–21). Keep the app purely informational — no price
  display, no seller referrals, no sponsorship, no incentivizing language. The
  in-app gate + neutral copy support this.
- **US/territories:** legal drinking age is 21; the gate enforces +21 for `US`.

## Product rule (unchanged)

Price information may exist in storage but must **never** be exposed in UI or
API. Do not add price rendering to any screen.

## Accounts & KVKK (added)

Registration/login (`backend/app/auth`) stores account + per-user sync data in
a **separate `users.db`** — never the governed whisky `production.db`. At
registration the server enforces:
- explicit privacy (KVKK) consent — otherwise rejected,
- age gate (country + legal minimum age),
- password ≥ 8 chars; PBKDF2-HMAC-SHA256 hashing; bearer tokens stored hashed.

Account == personal data ⇒ KVKK obligations apply: aydınlatma metni, consent
(captured), owner-level data storage; tie `users.db` to your VERBIS / data
controller record. Transactional email (verify) is currently stubbed to the
server log — wire an SMTP provider before public launch.

