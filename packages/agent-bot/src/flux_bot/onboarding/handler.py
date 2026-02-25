"""Onboarding state machine — pure logic, no DB access."""

import re
from dataclasses import dataclass, field

_USERNAME_RE = re.compile(r'^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$')


@dataclass
class OnboardingResult:
    reply: str
    next_step: str | None  # None = complete
    fields: dict = field(default_factory=dict)


class OnboardingHandler:
    def __init__(
        self,
        valid_currencies: list[str] | None = None,
        valid_timezones: list[str] | None = None,
    ):
        self.valid_currencies = valid_currencies or ["VND", "USD", "EUR", "GBP", "JPY", "SGD"]
        self.valid_timezones = valid_timezones or [
            "Asia/Ho_Chi_Minh", "Asia/Singapore", "Asia/Bangkok",
            "Asia/Tokyo", "Europe/London", "America/New_York",
        ]

    def start(self) -> OnboardingResult:
        """Return the opening prompt for a new user."""
        currency_list = " / ".join(self.valid_currencies)
        return OnboardingResult(
            reply=(
                "Welcome to flux! Let's set up your profile.\n\n"
                f"Step 1/3 — What's your preferred currency?\n"
                f"Common choices: {currency_list}\n"
                "(Default: VND — just press Enter or type your currency code)"
            ),
            next_step="currency",
            fields={},
        )

    def handle(
        self,
        step: str,
        text: str,
        fields: dict,
        username_exists: bool = False,
    ) -> OnboardingResult:
        text = (text or "").strip()
        if step == "currency":
            return self._handle_currency(text, fields)
        if step == "timezone":
            return self._handle_timezone(text, fields)
        if step == "username":
            return self._handle_username(text, fields, username_exists)
        return OnboardingResult(reply="Unknown step.", next_step=step, fields=fields)

    def _handle_currency(self, text: str, fields: dict) -> OnboardingResult:
        if not text:
            return OnboardingResult(
                reply="Please enter a currency code (e.g. VND, USD, EUR).",
                next_step="currency",
                fields=fields,
            )
        currency = text.upper()
        new_fields = {**fields, "currency": currency}
        tz_list = " / ".join(self.valid_timezones)
        return OnboardingResult(
            reply=(
                f"Got it — {currency}.\n\n"
                f"Step 2/3 — Your timezone?\n"
                f"Common choices: {tz_list}\n"
                "(Default: Asia/Ho_Chi_Minh — type your timezone or press Enter)"
            ),
            next_step="timezone",
            fields=new_fields,
        )

    def _handle_timezone(self, text: str, fields: dict) -> OnboardingResult:
        timezone = text if text else "Asia/Ho_Chi_Minh"
        new_fields = {**fields, "timezone": timezone}
        return OnboardingResult(
            reply=(
                f"Timezone set to {timezone}.\n\n"
                "Step 3/3 — Choose a username.\n"
                "Rules: lowercase letters, numbers, hyphens. At least 3 chars.\n"
                "Example: truong-vu"
            ),
            next_step="username",
            fields=new_fields,
        )

    def _handle_username(self, text: str, fields: dict, username_exists: bool) -> OnboardingResult:
        username = text.lower()
        if not _USERNAME_RE.match(username):
            return OnboardingResult(
                reply=(
                    "Invalid username. Use lowercase letters, numbers, hyphens. "
                    "At least 3 characters, no leading/trailing hyphens.\nTry again:"
                ),
                next_step="username",
                fields=fields,
            )
        if username_exists:
            return OnboardingResult(
                reply=f"Sorry, '{username}' is already taken. Please choose another username:",
                next_step="username",
                fields=fields,
            )
        new_fields = {**fields, "username": username}
        currency = fields.get("currency", "VND")
        timezone = fields.get("timezone", "Asia/Ho_Chi_Minh")
        return OnboardingResult(
            reply=(
                f"All set! Welcome, {username}.\n"
                f"Currency: {currency} | Timezone: {timezone}\n\n"
                "You're ready to track your finances. Just tell me about any transaction!"
            ),
            next_step=None,
            fields=new_fields,
        )
