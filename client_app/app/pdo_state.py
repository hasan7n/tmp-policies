"""PDO state singleton for the webui.

The decentralized helpers all take ``state`` as their first argument. We
build it the first time it's needed and hand the same instance out
thereafter. Init is guarded by a lock so concurrent callers don't race.
"""

import sys
import threading

from pdo.client.builder.shell import parse_shell_command_line

from .pdo_config import (
    F_LOGFILE,
    F_LOGLEVEL,
    F_SERVICE_DB_FILE,
    F_SERVICE_GROUPS_DB_FILE,
    PDO_LEDGER_URL,
    SCRATCH_DIR,
)

_lock = threading.Lock()
_state = None
_bindings = None


def _initialize():
    args = [
        "--logfile",
        F_LOGFILE,
        "--loglevel",
        F_LOGLEVEL,
        "--ledger",
        PDO_LEDGER_URL,
        "--groups-db",
        F_SERVICE_GROUPS_DB_FILE,
        "--service-db",
        F_SERVICE_DB_FILE,
        "--data-dir",
        SCRATCH_DIR,
    ]
    env = parse_shell_command_line(args)
    if env is None:
        sys.exit("failed to initialize PDO environment")
    state, bindings, _ = env
    return state, bindings


def _ensure():
    global _state, _bindings
    if _state is not None:
        return
    with _lock:
        if _state is None:
            _state, _bindings = _initialize()


def get_state():
    _ensure()
    return _state


def get_bindings():
    _ensure()
    return _bindings
