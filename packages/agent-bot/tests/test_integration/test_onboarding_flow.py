"""Integration: new user → onboarding steps → profile created → onboarding cleaned up."""
import asyncpg
from flux_bot.db.migrate import run_migrations
from flux_bot.db.onboarding import OnboardingRepository
from flux_bot.onboarding.handler import OnboardingHandler
from flux_core.db.connection import Database
from flux_core.db.user_profile_repo import UserProfileRepository
from flux_core.migrations.migrate import migrate
from flux_core.models.user_profile import UserProfileCreate


async def test_full_onboarding_creates_profile(pg_url):
    await run_migrations(pg_url)
    await migrate(pg_url)

    pool = await asyncpg.create_pool(pg_url)
    core_db = Database(pg_url)
    await core_db.connect()

    onboarding_repo = OnboardingRepository(pool)
    profile_repo = UserProfileRepository(core_db)
    handler = OnboardingHandler()

    platform_id = "55555"
    channel = "telegram"

    # New user — no profile, no onboarding row
    profile = await profile_repo.get_by_platform_id(channel, platform_id)
    assert profile is None

    # Start onboarding
    result = handler.start()
    assert result.next_step == "currency"
    await onboarding_repo.upsert(platform_id, channel, result.next_step)

    # Step 1: currency
    row = await onboarding_repo.get(platform_id, channel)
    assert row["step"] == "currency"
    result = handler.handle(step=row["step"], text="VND", fields={})
    assert result.next_step == "timezone"
    await onboarding_repo.upsert(platform_id, channel, result.next_step, currency=result.fields.get("currency"))

    # Step 2: timezone
    row = await onboarding_repo.get(platform_id, channel)
    assert row["step"] == "timezone"
    assert row["currency"] == "VND"
    result = handler.handle(
        step=row["step"], text="Asia/Ho_Chi_Minh",
        fields={k: row[k] for k in ("currency",) if row.get(k)},
    )
    assert result.next_step == "username"
    await onboarding_repo.upsert(
        platform_id, channel, result.next_step, timezone=result.fields.get("timezone"),
    )

    # Step 3: username (not taken)
    row = await onboarding_repo.get(platform_id, channel)
    assert row["step"] == "username"
    assert row["timezone"] == "Asia/Ho_Chi_Minh"
    fields = {k: row[k] for k in ("currency", "timezone") if row.get(k)}
    result = handler.handle(step=row["step"], text="test-user", fields=fields, username_exists=False)
    assert result.next_step is None  # complete

    # Create profile
    f = result.fields
    create = UserProfileCreate(
        username=f["username"],
        channel=channel,
        platform_id=platform_id,
        currency=f.get("currency", "VND"),
        timezone=f.get("timezone", "Asia/Ho_Chi_Minh"),
    )
    profile = await profile_repo.create(create)
    await onboarding_repo.delete(platform_id, channel)

    # Verify profile — user_id format is tg:<platform_id> (not username)
    assert profile.user_id == f"tg:{platform_id}"
    assert profile.currency == "VND"
    assert profile.timezone == "Asia/Ho_Chi_Minh"
    assert profile.platform_id == platform_id

    # Verify lookup by platform_id works
    fetched = await profile_repo.get_by_platform_id(channel, platform_id)
    assert fetched is not None
    assert fetched.user_id == f"tg:{platform_id}"

    # Verify onboarding row cleaned up
    row = await onboarding_repo.get(platform_id, channel)
    assert row is None

    await core_db.disconnect()
    await pool.close()


async def test_username_taken_stays_on_username_step(pg_url):
    await run_migrations(pg_url)
    await migrate(pg_url)

    pool = await asyncpg.create_pool(pg_url)
    core_db = Database(pg_url)
    await core_db.connect()

    profile_repo = UserProfileRepository(core_db)
    handler = OnboardingHandler()

    # Create an existing user with the username we'll try to take
    await profile_repo.create(UserProfileCreate(
        username="taken-user", channel="telegram", platform_id="66666",
    ))

    # Now try to register with the same username
    fields = {"currency": "VND", "timezone": "Asia/Ho_Chi_Minh"}
    username_taken = await profile_repo.username_exists("telegram", "taken-user")
    result = handler.handle(step="username", text="taken-user", fields=fields, username_exists=username_taken)

    assert result.next_step == "username"
    assert "taken" in result.reply.lower()

    await core_db.disconnect()
    await pool.close()
