from flux_bot.agent.checkpointer import build_checkpointer


async def test_checkpointer_can_put_and_get(tmp_path):
    db_path = str(tmp_path / "flux.db")
    async with build_checkpointer(db_path) as saver:
        cfg = {"configurable": {"thread_id": "t1", "checkpoint_ns": ""}}
        checkpoint = {
            "v": 1,
            "ts": "2026-04-23T00:00:00+00:00",
            "id": "chk-1",
            "channel_values": {},
            "channel_versions": {},
            "versions_seen": {},
            "pending_sends": [],
        }
        await saver.aput(cfg, checkpoint, {}, {})
        latest = await saver.aget(cfg)
        assert latest is not None
