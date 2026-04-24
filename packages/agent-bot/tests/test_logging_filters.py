"""Tests for RedactSecretsFilter and its wiring into configure_logging()."""
import logging

from flux_bot.logging_filters import RedactSecretsFilter


def _emit(caplog, msg: str) -> str:
    logger = logging.getLogger("flux.redact.test")
    logger.addFilter(RedactSecretsFilter())
    with caplog.at_level(logging.INFO, logger="flux.redact.test"):
        logger.info(msg)
    return caplog.records[-1].getMessage()


def test_redacts_sk_ant_keys(caplog):
    out = _emit(caplog, "failed with sk-ant-api-abcdef1234567890XYZ end")
    assert "sk-ant-api-abcdef1234567890XYZ" not in out
    assert "…0XYZ" in out  # last 4 chars preserved (impl uses [-4:])


def test_redacts_api_key_kv(caplog):
    out = _emit(caplog, "request: api_key=verysecret123456")
    assert "verysecret123456" not in out


def test_passes_through_safe_messages(caplog):
    msg = "user signed in"
    out = _emit(caplog, msg)
    assert out == msg


def test_filter_wired_into_root_logger():
    """After configure_logging(), the root handler carries RedactSecretsFilter."""
    from flux_core.logging import configure_logging
    configure_logging()
    root = logging.getLogger()
    filter_sources: list[object] = list(root.filters)
    for h in root.handlers:
        filter_sources.extend(h.filters)
    assert any(isinstance(f, RedactSecretsFilter) for f in filter_sources), (
        "RedactSecretsFilter is not wired into the root logger"
    )


def test_configure_logging_is_idempotent_for_redact_filter():
    """Calling configure_logging() twice must not accumulate RedactSecretsFilter.

    Regression test: root.handlers.clear() does not clear root-level
    filters, so any root.addFilter() in configure_logging() would stack
    on reinvocation.
    """
    from flux_core.logging import configure_logging

    configure_logging()
    configure_logging()

    root = logging.getLogger()
    sources: list[object] = list(root.filters)
    for h in root.handlers:
        sources.extend(h.filters)

    redact_count = sum(1 for f in sources if isinstance(f, RedactSecretsFilter))
    assert redact_count <= 1, (
        f"RedactSecretsFilter attached {redact_count} times after two "
        f"configure_logging() calls; expected at most 1."
    )


def test_redact_filter_mutates_record_message():
    """RedactSecretsFilter masks secrets directly on a LogRecord."""
    record = logging.LogRecord(
        name="flux.test.wiring",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="emit sk-ant-api-AAAAAAAAAA1234 here",
        args=(),
        exc_info=None,
    )
    RedactSecretsFilter().filter(record)
    assert "AAAAAAAAAA1234" not in record.getMessage()
