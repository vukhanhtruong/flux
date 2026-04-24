"""Map LLM provider error strings to user-facing messages."""


def map_runner_error(error_text: str) -> str:
    """Convert a raw exception message to a user-friendly reply."""
    t = error_text.lower()
    if "authentication" in t or "invalid api key" in t:
        return "Your LLM API key was rejected. Run /settings llm to update it."
    if "rate" in t and ("limit" in t or "429" in t):
        return "The LLM provider is rate-limiting us. Try again in a moment."
    if "timeout" in t:
        return "The agent took too long. Try a shorter question."
    if "badrequest" in t or "prompt too long" in t or "context" in t:
        return "The conversation got too long. Start fresh with /reset."
    return "Something broke on my side. The admin has been notified."
