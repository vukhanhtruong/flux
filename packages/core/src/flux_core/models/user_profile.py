import re
from dataclasses import dataclass
from pydantic import BaseModel, field_validator

_CHANNEL_PREFIXES = {
    "telegram": "tg",
    "whatsapp": "wa",
}

_USERNAME_RE = re.compile(r'^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$')


class UserProfileCreate(BaseModel):
    username: str
    channel: str
    platform_id: str
    currency: str = "VND"
    timezone: str = "Asia/Ho_Chi_Minh"

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError(
                "Username must be 3-50 chars, lowercase alphanumeric and hyphens only, "
                "cannot start or end with a hyphen"
            )
        return v

    @property
    def user_id(self) -> str:
        prefix = _CHANNEL_PREFIXES.get(self.channel, self.channel)
        return f"{prefix}:{self.username}"


@dataclass
class UserProfile:
    user_id: str
    username: str
    channel: str
    platform_id: str
    currency: str
    timezone: str
