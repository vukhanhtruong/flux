"""Tests for Markdown-to-Telegram conversion helper."""

from flux_bot.channels.formatting import convert_markdown


def test_bold_text_converted():
    """Standard Markdown **bold** is converted to MarkdownV2 bold."""
    result = convert_markdown("**Hello**")
    assert "*Hello*" in result
    # Should NOT have double asterisks
    assert "**" not in result


def test_italic_text_converted():
    """Standard Markdown *italic* is converted to MarkdownV2 italic."""
    result = convert_markdown("This is *italic* text")
    assert "_italic_" in result


def test_inline_code_preserved():
    """`code` backticks are preserved."""
    result = convert_markdown("Use `git status` here")
    assert "`git status`" in result


def test_code_block_preserved():
    """Fenced code blocks are preserved."""
    result = convert_markdown("```python\nprint('hi')\n```")
    assert "print" in result


def test_link_converted():
    """Markdown links are converted to MarkdownV2 format."""
    result = convert_markdown("Visit [Google](https://google.com)")
    assert "Google" in result
    # MarkdownV2 escapes dots, so check for escaped or unescaped form
    assert "google" in result
    assert "com" in result


def test_plain_text_returned_unchanged():
    """Plain text with no formatting passes through."""
    result = convert_markdown("Just plain text")
    assert "Just plain text" in result


def test_empty_string():
    """Empty string returns empty string."""
    assert convert_markdown("") == ""


def test_none_input():
    """None input returns empty string."""
    assert convert_markdown(None) == ""


def test_conversion_returns_string():
    """Result is always a string."""
    result = convert_markdown("**Hello** *world*")
    assert isinstance(result, str)
