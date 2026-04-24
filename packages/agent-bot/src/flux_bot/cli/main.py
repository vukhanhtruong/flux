"""flux CLI entry point.

Usage
-----
    flux config llm    — interactive LLM configuration wizard
    flux onboard       — interactive profile setup wizard

Database bootstrap (core migrations + bot migrations) is performed
automatically before any subcommand runs.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from rich.console import Console

from flux_bot.cli.chat import chat, chat_repl
from flux_bot.cli.flush import flush
from flux_bot.cli.wizard import CLI_USER_ID, CliError, config_llm, onboard
from flux_bot.config import load_config
from flux_bot.db.llm_config import UserLlmConfigRepository
from flux_bot.db.migrate import run_migrations
from flux_bot.db.outbound import OutboundRepository
from flux_bot.db.profile import ProfileRepository
from flux_bot.db.sessions import SessionRepository
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate as run_core_migrations

console = Console()
err_console = Console(stderr=True)


# ──────────────────────────────────────────────────────────────────────────────
# Database bootstrap
# ──────────────────────────────────────────────────────────────────────────────

def _setup_db(database_path: str) -> Database:
    """Connect to SQLite and apply all migrations."""
    db = Database(database_path)
    db.connect()
    run_core_migrations(db)
    asyncio.run(run_migrations(database_path))
    return db


# ──────────────────────────────────────────────────────────────────────────────
# Subcommand handlers
# ──────────────────────────────────────────────────────────────────────────────

def _cmd_config_llm(args: argparse.Namespace) -> int:
    """Handle: flux config llm"""
    config = load_config()
    db = _setup_db(config.database_path)
    try:
        repo = UserLlmConfigRepository(db)
        asyncio.run(config_llm(repo))
        return 0
    except CliError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        return 1
    finally:
        db.disconnect()


def _cmd_onboard(args: argparse.Namespace) -> int:
    """Handle: flux onboard"""
    config = load_config()
    db = _setup_db(config.database_path)
    try:
        repo = ProfileRepository(db)
        asyncio.run(onboard(repo))
        return 0
    except CliError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        return 1
    finally:
        db.disconnect()


def _cmd_chat(args: argparse.Namespace) -> int:
    """Handle: flux chat [prompt] [--reset] [--user user_id]"""
    from flux_bot.main import build_runner

    config = load_config()
    db = _setup_db(config.database_path)
    try:
        llm_config_repo = UserLlmConfigRepository(db)
        session_repo = SessionRepository(db)
        profile_repo = ProfileRepository(db)
        runner = build_runner(config, db=db, flux_db_path=config.database_path)

        prompt: str | None = getattr(args, "prompt", None)
        reset: bool = getattr(args, "reset", False)
        user_id: str = getattr(args, "user_id", None) or CLI_USER_ID

        if prompt is not None:
            # One-shot: prompt supplied as CLI argument
            return asyncio.run(
                chat(
                    prompt,
                    llm_config_repo=llm_config_repo,
                    session_repo=session_repo,
                    profile_repo=profile_repo,
                    runner=runner,
                    reset=reset,
                    user_id=user_id,
                )
            )
        elif not sys.stdin.isatty():
            # Piped stdin: read the whole pipe as a single prompt
            piped = sys.stdin.read().strip()
            if piped:
                return asyncio.run(
                    chat(
                        piped,
                        llm_config_repo=llm_config_repo,
                        session_repo=session_repo,
                        profile_repo=profile_repo,
                        runner=runner,
                        reset=reset,
                        user_id=user_id,
                    )
                )
            return 0
        else:
            # Interactive REPL
            return asyncio.run(
                chat_repl(
                    llm_config_repo=llm_config_repo,
                    session_repo=session_repo,
                    profile_repo=profile_repo,
                    runner=runner,
                    reset=reset,
                    user_id=user_id,
                )
            )
    except CliError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        return 1
    finally:
        db.disconnect()


def _cmd_flush(args: argparse.Namespace) -> int:
    """Handle: flux flush [--user user_id]"""
    config = load_config()
    db = _setup_db(config.database_path)
    try:
        outbound_repo = OutboundRepository(db)
        user_id: str = getattr(args, "user_id", None) or CLI_USER_ID
        asyncio.run(flush(outbound_repo, user_id=user_id))
        return 0  # count is informational; non-zero count is not a failure
    except CliError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        return 1
    finally:
        db.disconnect()


# ──────────────────────────────────────────────────────────────────────────────
# Argument parser
# ──────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flux",
        description="flux personal finance AI agent — CLI",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # config
    config_parser = sub.add_parser("config", help="Manage configuration")
    config_sub = config_parser.add_subparsers(dest="config_command", metavar="<subcommand>")
    config_sub.add_parser("llm", help="Configure LLM provider and API key")

    # onboard
    sub.add_parser("onboard", help="Set up your profile (currency, timezone, username)")

    # chat
    chat_parser = sub.add_parser("chat", help="Chat with the AI agent")
    chat_parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Message to send (omit for REPL mode)",
    )
    chat_parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help="Clear conversation history and start a fresh session",
    )
    chat_parser.add_argument(
        "--user",
        dest="user_id",
        default=None,
        help="User ID to chat as (default: cli:local)",
    )

    # flush
    flush_parser = sub.add_parser(
        "flush", help="Print and clear pending agent-initiated messages"
    )
    flush_parser.add_argument(
        "--user",
        dest="user_id",
        default=None,
        help="User ID to flush messages for (default: cli:local)",
    )

    return parser


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "config":
        if getattr(args, "config_command", None) == "llm":
            sys.exit(_cmd_config_llm(args))
        else:
            parser.parse_args(["config", "--help"])
    elif args.command == "onboard":
        sys.exit(_cmd_onboard(args))
    elif args.command == "chat":
        sys.exit(_cmd_chat(args))
    elif args.command == "flush":
        sys.exit(_cmd_flush(args))
    else:
        parser.print_help()
        sys.exit(0)
