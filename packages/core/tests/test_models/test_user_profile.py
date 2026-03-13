import pytest
from pydantic import ValidationError
from flux_core.models.user_profile import UserProfileCreate


def test_user_profile_create_defaults():
    p = UserProfileCreate(
        username="truong-vu",
        channel="telegram",
        platform_id="12345",
    )
    assert p.currency == "VND"
    assert p.timezone == "Asia/Ho_Chi_Minh"
    assert p.locale == "vi-VN"
    assert p.user_id == "tg:12345"


def test_user_profile_create_custom():
    p = UserProfileCreate(
        username="my-wife",
        channel="whatsapp",
        platform_id="84901234567",
        currency="USD",
        timezone="America/New_York",
        locale="en-US",
    )
    assert p.user_id == "wa:84901234567"
    assert p.locale == "en-US"


def test_username_freeform_allowed():
    p = UserProfileCreate(username="Truong Vu!", channel="telegram", platform_id="1")
    assert p.username == "Truong Vu!"


def test_username_empty_rejected():
    with pytest.raises(ValidationError):
        UserProfileCreate(username="", channel="telegram", platform_id="1")


def test_username_whitespace_only_rejected():
    with pytest.raises(ValidationError):
        UserProfileCreate(username="   ", channel="telegram", platform_id="1")
