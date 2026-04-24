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


def test_redact_filter_dict_msg_preserves_dict():
    """When record.msg is a structlog event dict, filter must not convert it to a string."""
    event_dict = {
        "event": "api_key=sk-ant-api-AAAAAAAAAA1234 received",
        "logger": "test",
        "level": "info",
    }
    record = logging.LogRecord(
        name="flux.test.dict",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=event_dict,
        args=(),
        exc_info=None,
    )
    RedactSecretsFilter().filter(record)
    assert isinstance(record.msg, dict), "msg must remain a dict (not be converted to str)"
    assert "AAAAAAAAAA1234" not in record.msg["event"]


def test_redact_filter_dict_msg_no_secret_unchanged():
    """When record.msg is a dict with no secret, the dict object is unchanged."""
    event_dict = {"event": "safe message", "logger": "test"}
    record = logging.LogRecord(
        name="flux.test.dict",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=event_dict,
        args=(),
        exc_info=None,
    )
    RedactSecretsFilter().filter(record)
    assert record.msg is event_dict  # no copy made when nothing to redact


def test_structlog_configure_logging_no_crash():
    """configure_logging() + structlog logger.info() must not emit a Logging error."""
    import structlog
    from flux_core.logging import configure_logging

    configure_logging()
    logger = structlog.get_logger("flux.test.no_crash")
    # Should not raise or print --- Logging error ---
    logger.info("hello %s", "world", foo="bar")
