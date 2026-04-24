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
    # At least one filter on the root or on a handler must be RedactSecretsFilter.
    filter_sources = list(root.filters)
    for h in root.handlers:
        filter_sources.extend(h.filters)
    assert any(isinstance(f, RedactSecretsFilter) for f in filter_sources), (
        "RedactSecretsFilter is not wired into the root logger"
    )

    # And it actually redacts when a record is emitted.
    record = logging.LogRecord(
        name="flux.test.wiring",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="emit sk-ant-api-AAAAAAAAAA1234 here",
        args=(),
        exc_info=None,
    )
    # Apply every filter in the chain.
    for f in filter_sources:
        if isinstance(f, RedactSecretsFilter):
            f.filter(record)
    assert "AAAAAAAAAA1234" not in record.getMessage()
