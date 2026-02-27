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
