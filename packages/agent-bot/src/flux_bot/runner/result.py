from dataclasses import dataclass


@dataclass
class AgentResult:
    text: str | None
    thread_id: str | None
    error: str | None = None
