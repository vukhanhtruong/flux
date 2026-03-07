from dataclasses import dataclass
from pydantic import BaseModel, field_validator

_CHANNEL_PREFIXES = {
    "telegram": "tg",
    "whatsapp": "wa",
}


class UserProfileCreate(BaseModel):
    username: str
    channel: str
    platform_id: str
    currency: str = "VND"
    timezone: str = "Asia/Ho_Chi_Minh"
    locale: str = "vi-VN"

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Username cannot be empty")
        return v

    @property
    def user_id(self) -> str:
        prefix = _CHANNEL_PREFIXES.get(self.channel, self.channel)
        return f"{prefix}:{self.platform_id}"


@dataclass
class UserProfile:
    user_id: str
    username: str
    channel: str
    platform_id: str
    currency: str
    timezone: str
    locale: str
