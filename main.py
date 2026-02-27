#!/usr/bin/env python3
# Ama — CLI app for AriVa code assistant. Uses contracts/AriVa.py (same addresses/hex).
#
# Usage:
#   python ama_app.py create-session --user-ref myuser
#   python ama_app.py get-session --session-id <sid>
#   python ama_app.py close-session --session-id <sid>
#   python ama_app.py validate --code "def f(): pass"   OR  --file path/to/file.py
#   python ama_app.py completions --session-id <sid> --prefix "im" --language py
#   python ama_app.py suggestions --session-id <sid> --query "fix" --kind 0
#   python ama_app.py update-context --session-id <sid> --context "project: lib"
#   python ama_app.py stats | config | health | demo | cleanup | uniqueness | constants | methods | templates
#   python ama_app.py interactive   # REPL
#   python ama_app.py batch [--file cmds.txt]   # or stdin
#   python ama_app.py simulation [--num-sessions 5]
#   python ama_app.py simulation-v2 [--num-users 8]

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent so contracts.AriVa can be imported
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from contracts.AriVa import (
    ARIVA_COORDINATOR,
    create_ariva,
    handle_ariva_request,
    run_ariva_demo,
    run_ariva_simulation,
    run_ariva_simulation_v2,
    health_check_ariva,
    confirm_ariva_addresses_unique,
    confirm_ariva_hex_unique,
    get_all_ariva_constants,
    list_ariva_methods,
    get_request_templates,
)

# Default config path (optional JSON: {"user_ref": "...", "caller_override": "0x..."})
AMA_CONFIG_ENV = "AMA_CONFIG"
AMA_CONFIG_DEFAULT = "ama_config.json"


def load_ama_config() -> dict:
    path = os.environ.get(AMA_CONFIG_ENV) or AMA_CONFIG_DEFAULT
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def get_caller_from_config() -> str:
    cfg = load_ama_config()
    return cfg.get("caller_override") or ARIVA_COORDINATOR


def get_user_ref_from_config() -> str:
    cfg = load_ama_config()
    return cfg.get("user_ref") or "ama_cli"


def format_session_line(session_id: str, user_ref: str, created_at: str) -> str:
    return f"{session_id}\t{user_ref}\t{created_at}"


def format_validation_errors(errors: list) -> str:
    if not errors:
        return "OK"
    return "\n".join(f"  - {e.get('rule', '?')}: {e.get('message', '')}" for e in errors)


def format_constants_table(constants: dict) -> str:
    lines = []
    for k, v in sorted(constants.items()):
        lines.append(f"  {k}: {v}")
    return "\n".join(lines) if lines else "  (none)"


def format_methods_list(methods: list) -> str:
    return "\n".join(f"  - {m}" for m in methods) if methods else "  (none)"


def write_json_or_fail(obj, indent=2):
    print(json.dumps(obj, indent=indent))
    return 0


def write_error_and_exit(obj, exit_code=1):
    print(json.dumps(obj, indent=2), file=sys.stderr)
    return exit_code


def main_create_session(platform, args):
    user_ref = args.user_ref or get_user_ref_from_config()
    caller = getattr(args, "caller", None) or get_caller_from_config()
    r = handle_ariva_request(
        platform,
        "create_session",
        {"user_ref": user_ref, "caller": caller},
    )
    if "error" in r:
        print(json.dumps(r, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(r, indent=2))
    return 0


def main_get_session(platform, args):
    r = handle_ariva_request(platform, "get_session", {"session_id": args.session_id})
    if "error" in r:
        print(json.dumps(r, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(r, indent=2))
    return 0


def main_close_session(platform, args):
    r = handle_ariva_request(
        platform,
        "close_session",
        {"session_id": args.session_id, "caller": ARIVA_COORDINATOR},
    )
    if "error" in r:
        print(json.dumps(r, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(r, indent=2))
    return 0


def main_validate(platform, args):
    code = args.code
    if args.file:
        code = Path(args.file).read_text(encoding="utf-8", errors="replace")
    r = handle_ariva_request(platform, "validate_code", {"code": code})
    if "error" in r:
        print(json.dumps(r, indent=2), file=sys.stderr)
        return 1
    if getattr(args, "human", False):
        print_validation_human(r)
    else:
        print(json.dumps(r, indent=2))
    return 0


def main_completions(platform, args):
    r = handle_ariva_request(
        platform,
        "get_completions",
        {
            "session_id": args.session_id,
            "prefix": args.prefix,
            "line_context": args.line_context or args.prefix,
            "language": args.language,
            "max_n": args.max_n,
        },
    )
    if "error" in r:
        print(json.dumps(r, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(r, indent=2))
    return 0


def main_suggestions(platform, args):
    r = handle_ariva_request(
        platform,
        "get_suggestions",
        {
            "session_id": args.session_id,
            "query": args.query,
            "kind": args.kind,
            "max_n": args.max_n,
        },
    )
    if "error" in r:
        print(json.dumps(r, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(r, indent=2))
    return 0


def main_update_context(platform, args):
    context = args.context
    if args.file:
        context = Path(args.file).read_text(encoding="utf-8", errors="replace")
    r = handle_ariva_request(
        platform,
        "update_context",
        {"session_id": args.session_id, "context": context, "caller": ARIVA_COORDINATOR},
    )
    if "error" in r:
        print(json.dumps(r, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(r, indent=2))
    return 0


def main_stats(platform, _args):
    r = handle_ariva_request(platform, "stats", {})
    if "error" in r:
        print(json.dumps(r, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(r, indent=2))
    return 0


def main_config(platform, _args):
    r = handle_ariva_request(platform, "config", {})
    if "error" in r:
        print(json.dumps(r, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(r, indent=2))
    return 0


def main_health(platform, _args):
    r = health_check_ariva(platform)
    print(json.dumps(r, indent=2))
    return 0


def main_demo(platform, _args):
    r = run_ariva_demo(platform)
    print(json.dumps(r, indent=2))
    return 0


def main_cleanup(platform, _args):
    r = handle_ariva_request(platform, "cleanup_stale", {})
    if "error" in r:
        print(json.dumps(r, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(r, indent=2))
    return 0


def main_uniqueness(_platform, _args):
    addrs = confirm_ariva_addresses_unique()
    hex_ok = confirm_ariva_hex_unique()
    print(json.dumps({"addresses_unique": addrs, "hex_unique": hex_ok}, indent=2))
    return 0


def main_constants(_platform, _args):
    print(json.dumps(get_all_ariva_constants(), indent=2))
    return 0


def main_methods(_platform, _args):
    print(json.dumps(list_ariva_methods(), indent=2))
    return 0


def main_templates(_platform, _args):
    print(json.dumps(get_request_templates(), indent=2))
    return 0


def main_show_config(_platform, _args):
    path = os.environ.get(AMA_CONFIG_ENV) or AMA_CONFIG_DEFAULT
    cfg = load_ama_config()
    out = {"config_path": path, "config_found": bool(cfg), "config": cfg}
    out["effective_caller"] = get_caller_from_config()
    out["effective_user_ref"] = get_user_ref_from_config()
    print(json.dumps(out, indent=2))
    return 0


def main_reference(_platform, _args):
    print(AMA_REFERENCE.strip())
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="Ama — AriVa code assistant CLI")
    sub = p.add_subparsers(dest="command", required=True)

    # create_session
    c = sub.add_parser("create-session", help="Create a new session")
    c.add_argument("--user-ref", default="", help="User reference (default from AMA config or ama_cli)")
    c.set_defaults(func=main_create_session)

    # get_session
    g = sub.add_parser("get-session", help="Get session by id")
    g.add_argument("session_id", help="Session ID")
    g.set_defaults(func=main_get_session)

    # close_session
    cl = sub.add_parser("close-session", help="Close session")
    cl.add_argument("session_id", help="Session ID")
    cl.set_defaults(func=main_close_session)

    # validate
    v = sub.add_parser("validate", help="Validate code")
    v.add_argument("--code", default="", help="Code string")
    v.add_argument("--file", help="Read code from file")
    v.add_argument("--human", action="store_true", help="Human-readable validation output")
    v.set_defaults(func=main_validate)

    # completions
    co = sub.add_parser("completions", help="Get completions")
    co.add_argument("session_id", help="Session ID")
    co.add_argument("--prefix", default="", help="Prefix")
    co.add_argument("--line-context", default="", help="Line context")
    co.add_argument("--language", default="py", help="Language")
    co.add_argument("--max-n", type=int, default=12, help="Max completions")
    co.set_defaults(func=main_completions)

    # suggestions
    s = sub.add_parser("suggestions", help="Get suggestions")
    s.add_argument("session_id", help="Session ID")
    s.add_argument("--query", default="", help="Query")
    s.add_argument("--kind", type=int, default=0, help="Kind 0-3")
    s.add_argument("--max-n", type=int, default=24, help="Max suggestions")
    s.set_defaults(func=main_suggestions)

    # update_context
    u = sub.add_parser("update-context", help="Update session context")
    u.add_argument("session_id", help="Session ID")
