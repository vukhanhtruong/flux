"""Tests for flux CLI: onboard command wizard logic."""
from flux_bot.db.profile import ProfileRepository


CLI_USER_ID = "cli:local"


# ---------------------------------------------------------------------------
# Happy path: all inputs provided
# ---------------------------------------------------------------------------

async def test_onboard_happy_path(cli_db, monkeypatch):
    """onboard stores provided username, currency, timezone."""
    from flux_bot.cli.wizard import onboard

    inputs = iter(["Alice", "EUR", "Europe/Paris"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    profile_repo = ProfileRepository(cli_db)
    await onboard(cli_db, profile_repo)

    saved = await profile_repo.get_by_user_id(CLI_USER_ID)
    assert saved is not None
    assert saved.username == "Alice"
    assert saved.currency == "EUR"
    assert saved.timezone == "Europe/Paris"


async def test_onboard_with_all_explicit_inputs(cli_db, monkeypatch):
    """onboard saves all user-provided values exactly."""
    from flux_bot.cli.wizard import onboard

    inputs = iter(["Bob", "GBP", "Europe/London"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    profile_repo = ProfileRepository(cli_db)
    await onboard(cli_db, profile_repo)

    saved = await profile_repo.get_by_user_id(CLI_USER_ID)
    assert saved is not None
    assert saved.username == "Bob"
    assert saved.currency == "GBP"
    assert saved.timezone == "Europe/London"


# ---------------------------------------------------------------------------
# Default values used when user enters empty string
# ---------------------------------------------------------------------------

async def test_onboard_defaults_on_empty_input(cli_db, monkeypatch):
    """Empty input for all fields uses defaults: username=cli:local, currency=USD, timezone=UTC."""
    from flux_bot.cli.wizard import onboard

    inputs = iter(["", "", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    profile_repo = ProfileRepository(cli_db)
    await onboard(cli_db, profile_repo)

    saved = await profile_repo.get_by_user_id(CLI_USER_ID)
    assert saved is not None
    assert saved.username == CLI_USER_ID
    assert saved.currency == "USD"
    assert saved.timezone == "UTC"


async def test_onboard_default_username_only(cli_db, monkeypatch):
    """Empty username falls back to 'cli:local'."""
    from flux_bot.cli.wizard import onboard

    inputs = iter(["", "JPY", "Asia/Tokyo"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    profile_repo = ProfileRepository(cli_db)
    await onboard(cli_db, profile_repo)

    saved = await profile_repo.get_by_user_id(CLI_USER_ID)
    assert saved is not None
    assert saved.username == CLI_USER_ID
    assert saved.currency == "JPY"
    assert saved.timezone == "Asia/Tokyo"


async def test_onboard_default_currency_only(cli_db, monkeypatch):
    """Empty currency falls back to 'USD'."""
    from flux_bot.cli.wizard import onboard

    inputs = iter(["Charlie", "", "US/Eastern"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    profile_repo = ProfileRepository(cli_db)
    await onboard(cli_db, profile_repo)

    saved = await profile_repo.get_by_user_id(CLI_USER_ID)
    assert saved is not None
    assert saved.currency == "USD"


async def test_onboard_default_timezone_only(cli_db, monkeypatch):
    """Empty timezone falls back to 'UTC'."""
    from flux_bot.cli.wizard import onboard

    inputs = iter(["Dave", "CAD", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    profile_repo = ProfileRepository(cli_db)
    await onboard(cli_db, profile_repo)

    saved = await profile_repo.get_by_user_id(CLI_USER_ID)
    assert saved is not None
    assert saved.timezone == "UTC"


# ---------------------------------------------------------------------------
# Idempotency: second run updates profile, not duplicates
# ---------------------------------------------------------------------------

async def test_onboard_twice_updates_not_duplicates(cli_db, monkeypatch):
    """Running onboard twice overwrites instead of creating duplicates."""
    from flux_bot.cli.wizard import onboard

    profile_repo = ProfileRepository(cli_db)

    # First run
    inputs = iter(["Alice", "USD", "UTC"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))
    await onboard(cli_db, profile_repo)

    # Second run with different values
    inputs = iter(["AliceUpdated", "EUR", "Europe/Berlin"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))
    await onboard(cli_db, profile_repo)

    saved = await profile_repo.get_by_user_id(CLI_USER_ID)
    assert saved is not None
    assert saved.username == "AliceUpdated"
    assert saved.currency == "EUR"
    assert saved.timezone == "Europe/Berlin"

    # Should be only one record
    rows = cli_db.fetchall("SELECT COUNT(*) as cnt FROM users WHERE id = ?", (CLI_USER_ID,))
    assert rows[0]["cnt"] == 1


# ---------------------------------------------------------------------------
# user_id follows cli:local convention
# ---------------------------------------------------------------------------

async def test_onboard_user_id_is_cli_local(cli_db, monkeypatch):
    """Profile is stored under user_id='cli:local'."""
    from flux_bot.cli.wizard import onboard

    inputs = iter(["TestUser", "USD", "UTC"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    profile_repo = ProfileRepository(cli_db)
    await onboard(cli_db, profile_repo)

    saved = await profile_repo.get_by_user_id(CLI_USER_ID)
    assert saved is not None
    assert saved.user_id == CLI_USER_ID
