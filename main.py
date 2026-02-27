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
