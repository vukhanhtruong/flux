"""Logging filters that redact secrets from log records before emission."""
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
        msg = record.getMessage()
        for pattern, repl in _PATTERNS:
            msg = pattern.sub(repl, msg)
        record.msg = msg
        record.args = ()
        return True
