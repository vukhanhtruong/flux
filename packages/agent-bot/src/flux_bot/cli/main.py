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

from flux_bot.cli.wizard import CliError, config_llm, onboard
from flux_bot.config import load_config
from flux_bot.db.llm_config import UserLlmConfigRepository
from flux_bot.db.migrate import run_migrations
from flux_bot.db.profile import ProfileRepository
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
    else:
        parser.print_help()
        sys.exit(0)
