def test_build_runner_claude(monkeypatch):
    monkeypatch.setenv("FLUX_RUNNER", "claude")
    from flux_bot.runner.sdk import ClaudeRunner
    from flux_bot.config import load_config
    from flux_bot.main import build_runner

    r = build_runner(load_config(), db=None, flux_db_path=":memory:")
    assert isinstance(r, ClaudeRunner)


def test_build_runner_deepagent(monkeypatch):
    monkeypatch.setenv("FLUX_RUNNER", "deepagent")
    from flux_bot.runner.deepagent import DeepAgentRunner
    from flux_bot.config import load_config
    from flux_bot.main import build_runner

    r = build_runner(load_config(), db=None, flux_db_path=":memory:")
    assert isinstance(r, DeepAgentRunner)
