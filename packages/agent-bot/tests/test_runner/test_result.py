from flux_bot.runner.result import AgentResult


def test_agent_result_defaults():
    r = AgentResult(text="hi", thread_id="t1")
    assert r.text == "hi"
    assert r.thread_id == "t1"
    assert r.error is None


def test_agent_result_error():
    r = AgentResult(text=None, thread_id="t1", error="timeout")
    assert r.text is None
    assert r.error == "timeout"
