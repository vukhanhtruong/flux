from flux_bot.onboarding.handler import OnboardingHandler, OnboardingResult


def make_handler():
    return OnboardingHandler(
        valid_currencies=["VND", "USD", "EUR"],
        valid_timezones=["Asia/Ho_Chi_Minh", "Asia/Singapore"],
    )


def test_start_returns_currency_prompt():
    handler = make_handler()
    result = handler.start()
    assert "currency" in result.reply.lower()
    assert result.next_step == "currency"
    assert result.fields == {}


def test_currency_step_accepts_valid_input():
    handler = make_handler()
    result = handler.handle(step="currency", text="USD", fields={})
    assert result.next_step == "timezone"
    assert result.fields == {"currency": "USD"}


def test_currency_step_accepts_custom_text():
    handler = make_handler()
    result = handler.handle(step="currency", text="SGD", fields={})
    assert result.fields["currency"] == "SGD"
    assert result.next_step == "timezone"


def test_currency_step_rejects_empty():
    handler = make_handler()
    result = handler.handle(step="currency", text="  ", fields={})
    assert result.next_step == "currency"
    assert "currency" in result.reply.lower()


def test_timezone_step_accepts_valid_input():
    handler = make_handler()
    result = handler.handle(
        step="timezone",
        text="Asia/Singapore",
        fields={"currency": "VND"},
    )
    assert result.next_step == "username"
    assert result.fields["timezone"] == "Asia/Singapore"


def test_username_step_valid():
    handler = make_handler()
    result = handler.handle(
        step="username",
        text="truong-vu",
        fields={"currency": "VND", "timezone": "Asia/Ho_Chi_Minh"},
        username_exists=False,
    )
    assert result.next_step is None
    assert result.fields["username"] == "truong-vu"


def test_username_step_taken():
    handler = make_handler()
    result = handler.handle(
        step="username",
        text="truong-vu",
        fields={"currency": "VND", "timezone": "Asia/Ho_Chi_Minh"},
        username_exists=True,
    )
    assert result.next_step == "username"
    assert "taken" in result.reply.lower()


def test_username_step_invalid_format():
    handler = make_handler()
    result = handler.handle(
        step="username",
        text="BAD USER!",
        fields={"currency": "VND", "timezone": "Asia/Ho_Chi_Minh"},
        username_exists=False,
    )
    assert result.next_step == "username"
