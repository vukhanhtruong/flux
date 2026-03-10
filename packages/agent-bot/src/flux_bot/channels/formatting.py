"""Convert standard Markdown to Telegram MarkdownV2 format."""

import structlog

logger = structlog.get_logger(__name__)


def convert_markdown(text: str | None) -> str:
    """Convert standard Markdown to Telegram MarkdownV2 format.

    Uses telegramify-markdown library. Falls back to original text if conversion fails.
    """
    if not text:
        return ""

    try:
        from telegramify_markdown import markdownify

        return markdownify(text)
    except Exception as e:
        logger.warning("Markdown conversion failed, sending as plain text", error=str(e))
        return text
