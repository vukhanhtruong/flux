# Web UI Profile Preferences Design

Date: 2026-02-25
Status: Approved (brainstorming)

## Context

User onboarding already stores profile preferences (`currency`, `timezone`) in backend user profile data. However, the web UI currently hardcodes currency display with `$` and uses generic date rendering without user preference control.

The product goal is to make backend profile the single source of truth for display preferences and add editable settings in the web UI.

## Requirements

1. Backend profile is source of truth.
2. Web UI must show amounts using profile currency.
3. For VND, format amounts as `VND 1,200,000` (code prefix, no decimals).
4. Date format must follow user language choice:
- Vietnamese locale (`vi-VN`) => `dd/mm/yyyy`
- English locale (`en-US`) => `mm/dd/yyyy`
5. Add settings controls in web UI for at least:
- Currency
- Timezone
- Language/Locale

## Proposed Solution

### Architecture

#### Backend (`packages/api-server`)

Add profile endpoints:

- `GET /profile?user_id=<id>`
- `PATCH /profile?user_id=<id>`

The route layer remains thin and delegates to `UserProfileRepository` in `core`.

#### Data model (`packages/core`)

Extend user profile to include a locale field:

- `locale` (default `vi-VN`)

This field is persisted in DB and returned to clients with `currency` and `timezone`.

#### Frontend (`packages/web-ui`)

Add a profile state provider loaded from backend and consumed across pages.

Introduce shared format utilities:

- `formatCurrency(amount, currency, locale)`
- `formatDate(date, locale, timezone)`

All pages replace hardcoded `$` and direct `toLocaleDateString()` with these helpers.

Settings page is upgraded from static info to editable preferences with save behavior wired to `PATCH /profile`.

## Components And Data Flow

### Backend

1. Add `profile.py` router:
- `GET /profile`: fetch by `user_id`, return full profile.
- `PATCH /profile`: update mutable fields (`currency`, `timezone`, `locale`), return updated profile.

2. Register router in `app.py`.

3. Core model/repository updates:
- `UserProfile` and `UserProfileCreate` include `locale`.
- `UserProfileRepository` selects, inserts, and updates `locale`.
- Add migration to append `locale` column with default.

### Frontend

1. Types:
- `UserProfile`
- `UserProfileUpdate`

2. API client:
- `getProfile(userId)`
- `updateProfile(userId, payload)`

3. Profile context/provider:
- `profile`
- `loading`
- `refreshProfile()`
- `saveProfile(update)`

4. Formatting:
- VND special rule: `VND 1,200,000`.
- Date format from `locale`:
  - `vi-VN` -> `dd/mm/yyyy`
  - `en-US` -> `mm/dd/yyyy`

5. App integration:
- Wrap app with provider once.
- Existing pages consume profile-driven formatters.

## Error Handling

### Backend

- `GET /profile`:
  - `400` invalid/missing `user_id`
  - `404` user not found
  - `500` unexpected errors

- `PATCH /profile`:
  - `400` no updatable fields
  - `400` invalid empty values
  - `404` user not found

### Frontend

- Profile load failure does not block app usage.
- Use temporary display fallbacks when profile is unavailable:
  - currency `USD`
  - timezone `UTC`
  - locale `en-US`
- Save button disabled while request is in flight.
- Show inline success/failure feedback in Settings.
- Formatting helpers degrade safely on malformed values.

## Testing Strategy

### Backend tests (`packages/api-server/tests`)

Add `test_routes_profile.py`:

1. GET success
2. GET not found
3. PATCH success (`currency/timezone/locale`)
4. PATCH invalid body
5. PATCH user not found

Update route registration assertions to include `/profile`.

### Core tests (`packages/core/tests`)

1. Model tests for `locale` default and custom values.
2. Repository tests for create/get/update including `locale` persistence.

### Frontend tests (`packages/web-ui`)

1. Unit tests:
- `formatCurrency` VND and non-VND behavior.
- `formatDate` locale-based output (`vi-VN`, `en-US`).

2. Component tests:
- Settings reads and updates profile.
- Key views render amounts without hardcoded `$` and dates via locale format.

3. Manual verification:
- With profile `{ currency: VND, locale: vi-VN }`, UI shows `VND ...` and `dd/mm/yyyy`.
- Switch locale to `en-US`, date display changes to `mm/dd/yyyy`.

## Alternatives Considered

1. UI-only preferences (localStorage): rejected because it violates backend single source of truth.
2. Per-page profile fetching: rejected due to duplication and inconsistency risk.
3. Backend-preformatted strings: rejected because it mixes presentation concerns into API and reduces UI flexibility.

## Recommended Approach

Implement backend profile endpoints + locale field, then wire a single profile provider in web UI and centralize formatting helpers. This gives consistent display rules, easy settings management, and extensibility for future i18n.
