"""Tests for flux CLI: config llm command wizard logic."""
import pytest

from flux_bot.db.llm_config import UserLlmConfigRepository


CLI_USER_ID = "cli:local"
SECRET_KEY = "test-secret-key-0123456789abcdef"  # 32+ chars


# ---------------------------------------------------------------------------
# Happy path: all inputs provided
# ---------------------------------------------------------------------------

async def test_config_llm_anthropic_happy_path(cli_db, monkeypatch):
    """config_llm saves anthropic config when all inputs are provided."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm

    inputs = iter(["anthropic", "claude-sonnet-4-6", "sk-ant-api-TEST", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    llm_config_repo = UserLlmConfigRepository(cli_db)
    await config_llm(llm_config_repo)

    saved = await llm_config_repo.get(CLI_USER_ID)
    assert saved is not None
    assert saved.provider == "anthropic"
    assert saved.model == "claude-sonnet-4-6"
    assert saved.api_key == "sk-ant-api-TEST"
    assert saved.base_url is None


async def test_config_llm_openai_happy_path(cli_db, monkeypatch):
    """config_llm saves openai config correctly."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm

    inputs = iter(["openai", "gpt-4o", "sk-openai-KEY", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    llm_config_repo = UserLlmConfigRepository(cli_db)
    await config_llm(llm_config_repo)

    saved = await llm_config_repo.get(CLI_USER_ID)
    assert saved is not None
    assert saved.provider == "openai"
    assert saved.model == "gpt-4o"
    assert saved.api_key == "sk-openai-KEY"
    assert saved.base_url is None


async def test_config_llm_groq_happy_path(cli_db, monkeypatch):
    """config_llm saves groq config correctly."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm

    inputs = iter(["groq", "llama-3.1-70b-versatile", "gsk_KEY", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    llm_config_repo = UserLlmConfigRepository(cli_db)
    await config_llm(llm_config_repo)

    saved = await llm_config_repo.get(CLI_USER_ID)
    assert saved is not None
    assert saved.provider == "groq"
    assert saved.model == "llama-3.1-70b-versatile"
    assert saved.api_key == "gsk_KEY"


async def test_config_llm_custom_with_base_url(cli_db, monkeypatch):
    """config_llm saves custom provider config with base_url."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm

    inputs = iter(["custom", "my-model", "my-api-key", "https://my.api.com/v1"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    llm_config_repo = UserLlmConfigRepository(cli_db)
    await config_llm(llm_config_repo)

    saved = await llm_config_repo.get(CLI_USER_ID)
    assert saved is not None
    assert saved.provider == "custom"
    assert saved.model == "my-model"
    assert saved.api_key == "my-api-key"
    assert saved.base_url == "https://my.api.com/v1"


async def test_config_llm_openrouter_with_base_url(cli_db, monkeypatch):
    """config_llm saves openrouter config with base_url."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm

    inputs = iter(["openrouter", "mistral/mistral-large", "sk-or-KEY", "https://openrouter.ai/api/v1"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    llm_config_repo = UserLlmConfigRepository(cli_db)
    await config_llm(llm_config_repo)

    saved = await llm_config_repo.get(CLI_USER_ID)
    assert saved is not None
    assert saved.provider == "openrouter"
    assert saved.model == "mistral/mistral-large"
    assert saved.api_key == "sk-or-KEY"
    assert saved.base_url == "https://openrouter.ai/api/v1"


# ---------------------------------------------------------------------------
# Default values used when user enters empty string
# ---------------------------------------------------------------------------

async def test_config_llm_anthropic_default_model(cli_db, monkeypatch):
    """Pressing Enter on model prompt uses default for anthropic."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm

    # Empty model input → should use default "claude-sonnet-4-6"
    inputs = iter(["anthropic", "", "sk-ant-api-KEY", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    llm_config_repo = UserLlmConfigRepository(cli_db)
    await config_llm(llm_config_repo)

    saved = await llm_config_repo.get(CLI_USER_ID)
    assert saved is not None
    assert saved.model == "claude-sonnet-4-6"


async def test_config_llm_openai_default_model(cli_db, monkeypatch):
    """Pressing Enter on model prompt uses default for openai."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm

    inputs = iter(["openai", "", "sk-openai-KEY", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    llm_config_repo = UserLlmConfigRepository(cli_db)
    await config_llm(llm_config_repo)

    saved = await llm_config_repo.get(CLI_USER_ID)
    assert saved is not None
    assert saved.model == "gpt-4o"


async def test_config_llm_groq_default_model(cli_db, monkeypatch):
    """Pressing Enter on model prompt uses default for groq."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm

    inputs = iter(["groq", "", "gsk_KEY", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    llm_config_repo = UserLlmConfigRepository(cli_db)
    await config_llm(llm_config_repo)

    saved = await llm_config_repo.get(CLI_USER_ID)
    assert saved is not None
    assert saved.model == "llama-3.1-70b-versatile"


# ---------------------------------------------------------------------------
# Missing FLUX_SECRET_KEY raises friendly error
# ---------------------------------------------------------------------------

async def test_config_llm_missing_secret_key_raises(cli_db, monkeypatch):
    """config_llm raises a user-friendly error when FLUX_SECRET_KEY is not set."""
    monkeypatch.delenv("FLUX_SECRET_KEY", raising=False)

    from flux_bot.cli.wizard import config_llm, CliError

    with pytest.raises(CliError, match="FLUX_SECRET_KEY"):
        await config_llm(UserLlmConfigRepository(cli_db))


# ---------------------------------------------------------------------------
# Invalid provider is rejected
# ---------------------------------------------------------------------------

async def test_config_llm_invalid_provider_raises(cli_db, monkeypatch):
    """config_llm raises CliError when an unknown provider is entered."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm, CliError

    inputs = iter(["badprovider", "some-model", "some-key", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    with pytest.raises(CliError, match="provider"):
        await config_llm(UserLlmConfigRepository(cli_db))


# ---------------------------------------------------------------------------
# Upsert behaviour: second run overwrites first
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Empty provider defaults to anthropic
# ---------------------------------------------------------------------------

async def test_config_llm_empty_provider_defaults_to_anthropic(cli_db, monkeypatch):
    """Empty provider input defaults to 'anthropic' with its default model."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm

    # Empty provider → anthropic; empty model → claude-sonnet-4-6
    inputs = iter(["", "", "sk-ant-api-KEY", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    llm_config_repo = UserLlmConfigRepository(cli_db)
    await config_llm(llm_config_repo)

    saved = await llm_config_repo.get(CLI_USER_ID)
    assert saved is not None
    assert saved.provider == "anthropic"
    assert saved.model == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Empty api_key raises CliError
# ---------------------------------------------------------------------------

async def test_config_llm_empty_api_key_raises(cli_db, monkeypatch):
    """Empty api_key raises CliError."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm, CliError

    inputs = iter(["anthropic", "claude-sonnet-4-6", "", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    with pytest.raises(CliError, match="API key"):
        await config_llm(UserLlmConfigRepository(cli_db))


# ---------------------------------------------------------------------------
# custom provider with empty base_url raises CliError
# ---------------------------------------------------------------------------

async def test_config_llm_custom_empty_base_url_raises(cli_db, monkeypatch):
    """custom provider with empty base_url raises CliError."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm, CliError

    inputs = iter(["custom", "my-model", "my-api-key", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    with pytest.raises(CliError, match="Base URL"):
        await config_llm(UserLlmConfigRepository(cli_db))


# ---------------------------------------------------------------------------
# Upsert behaviour: second run overwrites first
# ---------------------------------------------------------------------------

async def test_config_llm_upsert_overwrites_previous(cli_db, monkeypatch):
    """Running config_llm twice overwrites the previous config."""
    monkeypatch.setenv("FLUX_SECRET_KEY", SECRET_KEY)

    from flux_bot.cli.wizard import config_llm

    llm_config_repo = UserLlmConfigRepository(cli_db)

    # First run: anthropic
    inputs = iter(["anthropic", "claude-sonnet-4-6", "sk-ant-api-FIRST", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))
    await config_llm(llm_config_repo)

    # Second run: openai
    inputs = iter(["openai", "gpt-4o", "sk-openai-SECOND", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))
    await config_llm(llm_config_repo)

    saved = await llm_config_repo.get(CLI_USER_ID)
    assert saved is not None
    assert saved.provider == "openai"
    assert saved.api_key == "sk-openai-SECOND"
