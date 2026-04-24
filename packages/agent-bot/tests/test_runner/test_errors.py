from flux_bot.runner.errors import map_runner_error


def test_auth_error_mapped():
    msg = map_runner_error("AuthenticationError: invalid api key")
    assert "rejected" in msg.lower()
    assert "/settings llm" in msg


def test_rate_limit_mapped():
    msg = map_runner_error("RateLimitError: 429")
    assert "rate" in msg.lower()


def test_context_overflow_mapped():
    msg = map_runner_error("BadRequestError: prompt too long")
    assert "/reset" in msg


def test_timeout_mapped():
    msg = map_runner_error("TimeoutError: request timed out")
    assert "too long" in msg.lower()


def test_unknown_passes_through():
    msg = map_runner_error("SomeWeirdError: exploding")
    assert "something broke" in msg.lower()
