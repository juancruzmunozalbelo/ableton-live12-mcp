#!/usr/bin/env python3
"""
Antigravity MCP Registration Utility: Ableton Live 12 MCP Server
================================================================
Programmatically registers and verifies the 'ableton-live12' MCP server in
Antigravity's configuration file (~/.gemini/config/mcp_config.json).

Features:
- Atomic file write via temporary staging and os.replace.
- Idempotency: no disk writes if configuration is already up to date.
- Automatic safety backup creation (.bak).
- Preservation of existing server configurations, key order, and indentation.
- Configurable via CLI arguments and environment variables.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SERVER_KEY = "ableton-live12"
DEFAULT_CONFIG_PATH = Path.home() / ".gemini" / "config" / "mcp_config.json"
PREFERRED_PYTHON = Path(
    "/Users/juancruz/.local/share/uv/python/cpython-3.11-macos-aarch64-none/bin/python3.11"
)
DEFAULT_MODULE = "ableton_live12_mcp"


def resolve_project_root() -> Path:
    """Resolves project root directory."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent


def resolve_python_executable(explicit_path: Optional[str] = None) -> str:
    """Selects python executable in order: CLI arg > PREFERRED_PYTHON > sys.executable."""
    if explicit_path:
        p = Path(explicit_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Specified Python binary not found: {explicit_path}")
        return str(p)
    if PREFERRED_PYTHON.is_file() and os.access(PREFERRED_PYTHON, os.X_OK):
        return str(PREFERRED_PYTHON)
    return sys.executable


def build_server_config(
    python_path: str,
    project_root: Path,
    include_env: bool = True,
) -> Dict[str, Any]:
    """Builds the canonical registration dictionary for ableton-live12."""
    cfg: Dict[str, Any] = {
        "command": python_path,
        "args": ["-m", DEFAULT_MODULE],
        "cwd": str(project_root.resolve()),
    }
    if include_env:
        src_path = str((project_root / "src").resolve())
        cfg["env"] = {
            "PYTHONPATH": src_path,
        }
    return cfg


def load_config_file(config_path: Path) -> Tuple[Dict[str, Any], int, str]:
    """
    Loads JSON config file and detects indentation and trailing newline.
    Returns (data, indent, trailing_newline).
    """
    if not config_path.exists():
        return {"mcpServers": {}}, 2, "\n"

    raw_text = config_path.read_text(encoding="utf-8")
    trailing_newline = "\n" if raw_text.endswith("\n") else ""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON in {config_path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Root object in {config_path} must be a JSON object")

    # Detect indentation: count spaces in second line
    indent = 2
    lines = raw_text.splitlines()
    if len(lines) > 1:
        leading_spaces = len(lines[1]) - len(lines[1].lstrip(" "))
        if leading_spaces > 0:
            indent = leading_spaces

    return data, indent, trailing_newline


def atomic_write_config(
    config_path: Path,
    data: Dict[str, Any],
    indent: int = 2,
    trailing_newline: str = "\n",
) -> None:
    """Writes config atomically via tempfile staging, fsync, and os.replace."""
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Backup existing file if present
    if config_path.exists():
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        shutil.copy2(config_path, backup_path)

    # 2. Stage new content in same directory (guarantees same mount point)
    temp_dir = config_path.parent
    serialized = json.dumps(data, indent=indent, ensure_ascii=False) + trailing_newline
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=temp_dir,
        delete=False,
        prefix=f"{config_path.stem}_tmp_",
        suffix=".json",
    ) as tf:
        tf.write(serialized)
        tf.flush()
        os.fsync(tf.fileno())
        temp_path = Path(tf.name)

    # 3. Atomic rename
    try:
        os.replace(temp_path, config_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def check_registration(
    config_path: Path,
    expected_config: Dict[str, Any],
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Checks if ableton-live12 is registered matching expected config.
    Returns (is_registered, diff_reason, current_entry).
    """
    if not config_path.exists():
        return False, f"Config file does not exist: {config_path}", None

    data, _, _ = load_config_file(config_path)
    servers = data.get("mcpServers", {})
    if SERVER_KEY not in servers:
        return False, f"Server key '{SERVER_KEY}' not found in mcpServers", None

    current = servers[SERVER_KEY]
    # Verify core fields
    if current.get("command") != expected_config.get("command"):
        return False, f"command mismatch: current={current.get('command')}, expected={expected_config.get('command')}", current
    if current.get("args") != expected_config.get("args"):
        return False, f"args mismatch: current={current.get('args')}, expected={expected_config.get('args')}", current
    if current.get("cwd") != expected_config.get("cwd"):
        return False, f"cwd mismatch: current={current.get('cwd')}, expected={expected_config.get('cwd')}", current

    # Verify PYTHONPATH in env if expected
    if "env" in expected_config:
        current_env = current.get("env", {})
        expected_env = expected_config["env"]
        for k, v in expected_env.items():
            if current_env.get(k) != v:
                return False, f"env['{k}'] mismatch: current={current_env.get(k)}, expected={v}", current

    return True, None, current


def register(
    config_path: Path,
    expected_config: Dict[str, Any],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Registers ableton-live12 server in mcpServers."""
    is_reg, reason, current = check_registration(config_path, expected_config)
    if is_reg:
        return {
            "status": "already_registered",
            "server": SERVER_KEY,
            "config_path": str(config_path),
            "configuration": current,
        }

    if dry_run:
        return {
            "status": "dry_run",
            "server": SERVER_KEY,
            "config_path": str(config_path),
            "reason": reason,
            "proposed": expected_config,
        }

    data, indent, newline = load_config_file(config_path)
    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}

    data["mcpServers"][SERVER_KEY] = expected_config
    atomic_write_config(config_path, data, indent=indent, trailing_newline=newline)

    return {
        "status": "registered",
        "server": SERVER_KEY,
        "config_path": str(config_path),
        "configuration": expected_config,
    }


def unregister(config_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    """Unregisters ableton-live12 server from mcpServers."""
    if not config_path.exists():
        return {"status": "not_found", "config_path": str(config_path)}

    data, indent, newline = load_config_file(config_path)
    servers = data.get("mcpServers", {})
    if SERVER_KEY not in servers:
        return {"status": "not_registered", "config_path": str(config_path)}

    if dry_run:
        return {"status": "dry_run_unregistered", "config_path": str(config_path)}

    del servers[SERVER_KEY]
    atomic_write_config(config_path, data, indent=indent, trailing_newline=newline)

    return {"status": "unregistered", "server": SERVER_KEY, "config_path": str(config_path)}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Register and manage Ableton Live 12 MCP server in Antigravity config."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--register", action="store_true", default=False, help="Register or update server")
    group.add_argument("--check", action="store_true", help="Check registration status without writing")
    group.add_argument("--unregister", action="store_true", help="Remove server from configuration")

    parser.add_argument("--config-path", type=str, default=str(DEFAULT_CONFIG_PATH), help="Path to mcp_config.json")
    parser.add_argument("--python-path", type=str, default=None, help="Path to Python 3.11 binary")
    parser.add_argument("--cwd", type=str, default=None, help="Working directory for server")
    parser.add_argument("--dry-run", action="store_true", help="Show proposed changes without writing")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args(argv)

    config_path = Path(args.config_path).expanduser().resolve()
    project_root = Path(args.cwd).resolve() if args.cwd else resolve_project_root()
    python_path = resolve_python_executable(args.python_path)
    expected_config = build_server_config(python_path, project_root)

    # Determine action
    if args.check:
        is_reg, reason, current = check_registration(config_path, expected_config)
        result = {
            "status": "ok" if is_reg else "missing",
            "is_registered": is_reg,
            "reason": reason,
            "config_path": str(config_path),
            "configuration": current,
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if is_reg:
                print(f"✓ '{SERVER_KEY}' is correctly registered in {config_path}")
            else:
                print(f"✗ '{SERVER_KEY}' registration check failed: {reason}")
        return 0 if is_reg else 1

    if args.unregister:
        res = unregister(config_path, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"• Status: {res.get('status')}")
        return 0

    # Default action: register (either explicitly requested with --register or default if neither --check nor --unregister)
    res = register(config_path, expected_config, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        status = res.get("status")
        print(f"• Status: {status}")
        print(f"• Config: {config_path}")
        print(f"• Command: {expected_config['command']}")
        print(f"• Args: {expected_config['args']}")
        print(f"• Cwd: {expected_config['cwd']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
