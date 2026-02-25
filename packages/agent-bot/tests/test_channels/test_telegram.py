from unittest.mock import AsyncMock, MagicMock

from flux_bot.channels.telegram import TelegramChannel
from flux_core.models.user_profile import UserProfile


def _make_channel(profile=None):
    profile_repo = AsyncMock()
    profile_repo.get_by_platform_id.return_value = profile
    profile_repo.username_exists = AsyncMock(return_value=False)
    profile_repo.create = AsyncMock()

    onboarding_repo = AsyncMock()
    onboarding_repo.get.return_value = None
    onboarding_repo.upsert = AsyncMock()
    onboarding_repo.delete = AsyncMock()

    msg_repo = AsyncMock()
    msg_repo.insert = AsyncMock(return_value=1)

    ch = TelegramChannel(
        bot_token="123:ABC",
        message_repo=msg_repo,
        profile_repo=profile_repo,
        onboarding_repo=onboarding_repo,
        allow_from=None,
        image_dir="/tmp",
    )
    ch._app = MagicMock()
    ch._app.bot.send_message = AsyncMock()
    return ch, msg_repo, profile_repo, onboarding_repo


def _make_update(user_id=12345, text="hello"):
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = text
    update.message.caption = None
    update.message.photo = None
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


async def test_known_user_stores_message():
    """Onboarded user's message is stored via MessageRepository."""
    profile = UserProfile(
        user_id="tg:truong-vu", username="truong-vu",
        channel="telegram", platform_id="12345",
        currency="VND", timezone="Asia/Ho_Chi_Minh",
        locale="vi-VN",
    )
    ch, msg_repo, _, _ = _make_channel(profile=profile)
    update = _make_update(user_id=12345, text="spent 20k lunch")

    await ch._handle_message(update, MagicMock())

    msg_repo.insert.assert_called_once_with(
        user_id="tg:truong-vu",
        channel="telegram",
        platform_id="12345",
        text="spent 20k lunch",
        image_path=None,
    )


async def test_new_user_starts_onboarding():
    """New user (no profile) triggers onboarding, no message stored."""
    ch, msg_repo, _, onboarding_repo = _make_channel(profile=None)
    update = _make_update(user_id=99999, text="hello")

    await ch._handle_message(update, MagicMock())

    msg_repo.insert.assert_not_called()
    onboarding_repo.upsert.assert_called_once()
    update.message.reply_text.assert_called_once()


async def test_send_message_uses_platform_id():
    """send_message routes via numeric platform_id as chat_id."""
    ch, _, _, _ = _make_channel()
    await ch.send_message(platform_id="12345", text="Hello!")
    ch._app.bot.send_message.assert_called_once_with(chat_id=12345, text="Hello!")


async def test_allowlist_blocks_unauthorized():
    """Messages from users not in allowlist are rejected."""
    profile_repo = AsyncMock()
    onboarding_repo = AsyncMock()
    msg_repo = AsyncMock()

    ch = TelegramChannel(
        bot_token="123:ABC",
        message_repo=msg_repo,
        profile_repo=profile_repo,
        onboarding_repo=onboarding_repo,
        allow_from=["99999"],
        image_dir="/tmp",
    )

    update = _make_update(user_id=12345, text="hello")
    await ch._handle_message(update, MagicMock())

    msg_repo.insert.assert_not_called()
    update.message.reply_text.assert_called_once()


async def test_handle_photo_message_stores_image_path():
    """Photo message downloads image and stores path in bot_messages."""
    profile = UserProfile(
        user_id="tg:photo-user", username="photo-user",
        channel="telegram", platform_id="456",
        currency="VND", timezone="Asia/Ho_Chi_Minh",
        locale="vi-VN",
    )
    ch, msg_repo, _, _ = _make_channel(profile=profile)

    mock_file = AsyncMock()
    mock_file.download_to_drive = AsyncMock()

    update = MagicMock()
    update.message.text = None
    update.message.caption = "receipt"
    update.message.photo = [MagicMock(file_id="photo1"), MagicMock(file_id="photo2")]
    update.effective_user.id = 456
    context = MagicMock()
    context.bot.get_file = AsyncMock(return_value=mock_file)

    await ch._handle_message(update, context)

    msg_repo.insert.assert_called_once()
    kwargs = msg_repo.insert.call_args[1]
    assert kwargs["user_id"] == "tg:photo-user"
    assert kwargs["platform_id"] == "456"
    assert kwargs["image_path"] is not None


async def test_send_typing_action_calls_send_chat_action():
    """send_typing_action calls Telegram sendChatAction with action=typing."""
    ch, _, _, _ = _make_channel()
    ch._app.bot.send_chat_action = AsyncMock()

    await ch.send_typing_action(platform_id="12345")

    ch._app.bot.send_chat_action.assert_called_once_with(chat_id=12345, action="typing")
