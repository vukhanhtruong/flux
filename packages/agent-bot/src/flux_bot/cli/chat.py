"""flux chat — one-shot and REPL chat with the DeepAgentRunner.

Public API
----------
chat(prompt, *, llm_config_repo, session_repo, profile_repo, runner, reset=False) -> int
    One-shot: send a single prompt and return an exit code.

chat_repl(*, llm_config_repo, session_repo, profile_repo, runner) -> int
    REPL: read lines from stdin until EOF, running one chat() per line.

Both functions raise CliError when LLM config is missing.
"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from rich.console import Console

from flux_bot.cli.wizard import CLI_CHANNEL, CLI_USER_ID, CliError

if TYPE_CHECKING:
    from flux_bot.db.llm_config import UserLlmConfigRepository
    from flux_bot.db.profile import ProfileRepository
    from flux_bot.db.sessions import SessionRepository

console = Console()
err_console = Console(stderr=True)


async def chat(
    prompt: str,
    *,
    llm_config_repo: "UserLlmConfigRepository",
    session_repo: "SessionRepository",
    profile_repo: "ProfileRepository",
    runner,
    reset: bool = False,
    user_id: str = CLI_USER_ID,
    channel: str = CLI_CHANNEL,
) -> int:
    """Send a single prompt to the runner and print the response.

    Parameters
    ----------
    prompt:
        The user's message.
    llm_config_repo, session_repo, profile_repo:
        Pre-constructed repository instances.
    runner:
        A DeepAgentRunner (or compatible) instance.
    reset:
        If True, delete the existing thread before running so a fresh
        conversation is started.
    user_id:
        The user to chat as (default: CLI_USER_ID).
    channel:
        The channel name used for thread key namespacing (default: CLI_CHANNEL).

    Returns
    -------
    int
        0 on success, 1 on runner error.

    Raises
    ------
    CliError
        When no LLM config is found for the user.
    """
    thread_key = f"thread:{user_id}:{channel}"

    # 1. Require LLM config — clear user-facing message if missing.
    llm_cfg = await llm_config_repo.get(user_id)
    if llm_cfg is None:
        raise CliError("Run `flux config llm` to configure an LLM first.")

    # 2. Require profile — runner accesses profile.timezone / profile.username.
    profile = await profile_repo.get_by_user_id(user_id)
    if profile is None:
        raise CliError("Run `flux onboard` to set up your profile first.")

    # 3. Optionally reset the thread.
    if reset:
        await session_repo.delete(thread_key)

    # 4. Fetch (or create) stable thread_id.
    thread_id = await session_repo.get_thread_id(user_id, channel)

    # 5. Run the agent.
    result = await runner.run(
        prompt=prompt,
        user_id=user_id,
        thread_id=thread_id,
        profile=profile,
        llm_config=llm_cfg,
    )

    # 6. Output.
    if result.error:
        err_console.print(f"[red]Error:[/red] {result.error}")
        return 1

    if result.text:
        console.print(result.text)

    return 0


async def chat_repl(
    *,
    llm_config_repo: "UserLlmConfigRepository",
    session_repo: "SessionRepository",
    profile_repo: "ProfileRepository",
    runner,
    reset: bool = False,
    user_id: str = CLI_USER_ID,
    channel: str = CLI_CHANNEL,
) -> int:
    """Interactive REPL: read lines from stdin and call chat() for each.

    Prints a ``> `` prompt to stderr (so pipeline output stays clean).
    Exits cleanly on EOF (Ctrl+D) or when an empty line is entered.

    Parameters
    ----------
    reset:
        If True, delete the existing thread before entering the loop so a
        fresh conversation is started.
    user_id:
        The user to chat as (default: CLI_USER_ID).
    channel:
        The channel name used for thread key namespacing (default: CLI_CHANNEL).

    Returns
    -------
    int
        0 when the loop exits normally; 1 if any turn returned an error.
    """
    if reset:
        thread_key = f"thread:{user_id}:{channel}"
        await session_repo.delete(thread_key)

    last_rc = 0
    while True:
        # Print prompt to stderr so it doesn't pollute pipeline output.
        sys.stderr.write("> ")
        sys.stderr.flush()

        try:
            line = sys.stdin.readline()
        except (KeyboardInterrupt, EOFError):
            break

        if not line:
            # readline() returns '' on EOF.
            break

        stripped = line.rstrip("\n").strip()
        if not stripped:
            continue

        rc = await chat(
            stripped,
            llm_config_repo=llm_config_repo,
            session_repo=session_repo,
            profile_repo=profile_repo,
            runner=runner,
            user_id=user_id,
            channel=channel,
        )
        if rc != 0:
            last_rc = rc

    return last_rc
