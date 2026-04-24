"""Logging filters that redact secrets from log records before emission.

Lives in flux_core so flux_core.logging.configure_logging() can attach it
without creating a core → bot import cycle. Re-exported from
flux_bot.logging_filters for backward-compatibility.
"""
import logging
import re

_PATTERNS = [
    # sk-ant-xxx, sk-openai-xxx, etc. Keep last 4 chars as "…XYZ".
    (re.compile(r"(sk-[A-Za-z0-9_-]{10,})"), lambda m: f"…{m.group(1)[-4:]}"),
    # api_key=secret or api_key: secret
    (re.compile(r"(api[_-]?key\s*[=:]\s*)\S+", re.IGNORECASE), lambda m: f"{m.group(1)}<redacted>"),
]


class RedactSecretsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, dict):
            # structlog record: msg is the event_dict; redact only the event string
            # to avoid converting the dict to a string (which breaks ProcessorFormatter)
            event = record.msg.get("event", "")
            if isinstance(event, str):
                redacted = event
                for pattern, repl in _PATTERNS:
                    redacted = pattern.sub(repl, redacted)
                if redacted != event:
                    record.msg = {**record.msg, "event": redacted}
        else:
            msg = record.getMessage()
            for pattern, repl in _PATTERNS:
                msg = pattern.sub(repl, msg)
            record.msg = msg
            record.args = ()
        return True
