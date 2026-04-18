"""CLI entry points for the ATLAS backend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import auth, db, seed
from .database import SessionLocal


def seed_main(argv: list[str] | None = None) -> int:
    """``atlas-backend-seed`` — load raw experiment data into the DB."""
    parser = argparse.ArgumentParser(
        prog="atlas-backend-seed",
        description=(
            "Seed the ATLAS backend PostgreSQL DB from a raw experiment directory "
            "(containing experiment_meta.json and model/probe/scan_*.json files)."
        ),
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Path to a raw experiment directory (with experiment_meta.json), "
        "or (with --recursive) a parent folder (e.g. docs/experiment/) "
        "containing several such directories.",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Seed every immediate subdirectory that contains an experiment_meta.json.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit results as JSON instead of human-readable text.",
    )
    args = parser.parse_args(argv)

    session = SessionLocal()
    try:
        progress = seed.cli_progress if not args.json else seed._noop_progress
        results = seed.seed_from_directory(
            session, args.directory, recursive=args.recursive, progress=progress,
        )
        session.commit()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        session.rollback()
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        for r in results:
            warns = f" ({len(r.warnings)} warnings)" if r.warnings else ""
            print(
                f"  seeded experiment {r.experiment_id!r}"
                f" (timestamp={r.timestamp})"
                f" — {r.scans_seeded} scans, {r.findings_seeded} findings{warns}"
            )
        print(f"Seeded {len(results)} experiment(s).")
    return 0


def list_experiments_main(argv: list[str] | None = None) -> int:
    """``atlas-backend-experiments`` — list persisted experiments."""
    parser = argparse.ArgumentParser(
        prog="atlas-backend-experiments",
        description="List experiments stored in the ATLAS backend DB.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    session = SessionLocal()
    try:
        rows = db.list_experiments(session)
    finally:
        session.close()

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        if not rows:
            print("No experiments in database")
            return 0
        print(f"{'ID':<30} {'TIMESTAMP':<25} FINDINGS  MODELS")
        for r in rows:
            models = ", ".join(r.get("models") or [])
            print(f"{r['id']:<30} {r.get('timestamp',''):<25} {r['finding_count']:<8}  {models}")
    return 0


def adduser_main(argv: list[str] | None = None) -> int:
    """``atlas-backend-adduser`` — create a user account."""
    import getpass

    parser = argparse.ArgumentParser(
        prog="atlas-backend-adduser",
        description="Create a new user account in the ATLAS backend DB.",
    )
    parser.add_argument("username", help="Username for the new account")
    parser.add_argument(
        "--password",
        default=None,
        help="Password (will prompt interactively if omitted)",
    )
    args = parser.parse_args(argv)

    password = args.password
    if password is None:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("error: passwords do not match", file=sys.stderr)
            return 1

    session = SessionLocal()
    try:
        user = auth.register_user(session, args.username, password)
        session.commit()
    except ValueError as e:
        session.rollback()
        print(f"error: {e}", file=sys.stderr)
        return 1
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Created user {user['username']!r} (id={user['id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(seed_main())
