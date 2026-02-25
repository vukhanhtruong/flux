from flux_bot.config import load_config, BotConfig


def test_default_config():
    config = load_config()
    assert isinstance(config, BotConfig)
    assert config.database_url == "postgresql://localhost/flux"
    assert config.poll_interval == 2.0
    assert config.fallback_poll_interval == 30.0
    assert config.runner.timeout == 300
    assert config.runner.max_turns == 10


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://custom/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("POLL_INTERVAL", "5")
    monkeypatch.setenv("CLAUDE_TIMEOUT", "600")

    config = load_config()
    assert config.database_url == "postgresql://custom/db"
    assert config.telegram.enabled is True
    assert config.telegram.bot_token == "123:ABC"
    assert config.poll_interval == 5.0
    assert config.runner.timeout == 600


def test_fallback_poll_interval_env_override(monkeypatch):
    monkeypatch.setenv("FALLBACK_POLL_INTERVAL", "60")
    config = load_config()
    assert config.fallback_poll_interval == 60.0
