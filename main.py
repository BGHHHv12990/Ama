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
    u.add_argument("--context", default="", help="Context string")
    u.add_argument("--file", help="Read context from file")
    u.set_defaults(func=main_update_context)

    # stats, config, health, demo, cleanup
    sub.add_parser("stats", help="Show stats").set_defaults(func=main_stats)
    sub.add_parser("config", help="Show config").set_defaults(func=main_config)
    sub.add_parser("health", help="Health check").set_defaults(func=main_health)
    sub.add_parser("demo", help="Run demo").set_defaults(func=main_demo)
    sub.add_parser("cleanup", help="Cleanup stale sessions").set_defaults(func=main_cleanup)
    sub.add_parser("uniqueness", help="Confirm addresses/hex unique").set_defaults(func=main_uniqueness)
    sub.add_parser("constants", help="List all constants").set_defaults(func=main_constants)
    sub.add_parser("methods", help="List API methods").set_defaults(func=main_methods)
    sub.add_parser("templates", help="Request templates").set_defaults(func=main_templates)
    sub.add_parser("show-config", help="Show loaded config path and effective caller/user_ref").set_defaults(func=main_show_config)
    sub.add_parser("reference", help="Print CLI reference").set_defaults(func=main_reference)
    sub.add_parser("interactive", help="Interactive mode").set_defaults(func=main_interactive)

    batch_p = sub.add_parser("batch", help="Batch from file or stdin")
    batch_p.add_argument("--file", help="Read commands from file (one per line)")
    batch_p.set_defaults(func=main_batch)

    sim = sub.add_parser("simulation", help="Run run_ariva_simulation")
    sim.add_argument("--num-sessions", type=int, default=5, help="Number of sessions")
    sim.set_defaults(func=main_simulation)

    sim2 = sub.add_parser("simulation-v2", help="Run run_ariva_simulation_v2")
    sim2.add_argument("--num-users", type=int, default=8, help="Number of users")
    sim2.set_defaults(func=main_simulation_v2)

    return p


def main_simulation(platform, args):
    num = getattr(args, "num_sessions", 5)
    r = run_ariva_simulation(platform, num_sessions=num)
    print(json.dumps(r, indent=2))
    return 0


def main_simulation_v2(platform, args):
    num_users = getattr(args, "num_users", 8)
    r = run_ariva_simulation_v2(platform, num_users=num_users)
    print(json.dumps(r, indent=2))
    return 0


def main():
    parser = build_parser()
    args = parser.parse_args()
    platform = create_ariva()
    return args.func(platform, args)


# -----------------------------------------------------------------------------
# Interactive mode (optional)
# -----------------------------------------------------------------------------
def read_input(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def run_interactive(platform):
    """Simple interactive loop: create session, then validate/completions/suggestions."""
    print("Ama — AriVa CLI. Commands: create, validate <code>, completions <sid> <prefix>, suggestions <sid> <query>, stats, config, quit")
    session_id = None
    while True:
        line = read_input("ama> ")
        if not line or line == "quit":
            break
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        if cmd == "create":
            r = handle_ariva_request(platform, "create_session", {"user_ref": "ama_interactive", "caller": ARIVA_COORDINATOR})
            if "error" in r:
                print("Error:", r, file=sys.stderr)
            else:
                session_id = r["session_id"]
                print("Session:", session_id)
        elif cmd == "validate":
            r = handle_ariva_request(platform, "validate_code", {"code": rest or "def x(): pass"})
            print(json.dumps(r, indent=2))
        elif cmd == "completions" and rest:
            sid, _, prefix = (rest + "  ").partition(" ")[0], "", (rest + "  ").split(maxsplit=2)[-1].strip() or "im"
            sid = sid or session_id
            if not sid:
                print("No session_id. Run create first.", file=sys.stderr)
                continue
            r = handle_ariva_request(platform, "get_completions", {"session_id": sid, "prefix": prefix, "line_context": prefix, "language": "py", "max_n": 5})
            print(json.dumps(r, indent=2))
        elif cmd == "suggestions" and rest:
