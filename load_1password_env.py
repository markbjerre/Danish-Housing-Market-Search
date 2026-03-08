"""
Load env from .env and .env.1password (op:// refs) into os.environ.
Place in project root. Call load_1password_env() before other config.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _find_file(name: str, start: Path) -> Path | None:
    """Search upward from start for name."""
    p = start.resolve()
    for _ in range(10):
        if (p / name).exists():
            return p / name
        parent = p.parent
        if parent == p:
            break
        p = parent
    return None


def _find_workspace_root(start: Path) -> Path:
    """Find workspace root (has CLAUDE.md or AGENTS.md)."""
    p = start.resolve()
    for _ in range(10):
        if (p / "CLAUDE.md").exists() or (p / "AGENTS.md").exists():
            return p
        parent = p.parent
        if parent == p:
            break
        p = parent
    return start


def load_1password_env(base_dir: Path | None = None) -> None:
    """
    Load .env (for OPS_API_KEY) then .env.1password (op:// refs) into os.environ.
    Call before load_dotenv or other config. base_dir: project root (default: cwd).
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    base = base.resolve()
    root = _find_workspace_root(base)

    # 1. Load root .env (OPS_API_KEY for op auth)
    env_path = root / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, rest = line.partition("=")
            key, val = key.strip(), rest.strip()
            if key and val and not val.startswith("op://"):
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                os.environ.setdefault(key, val)

    # 2. Set op auth from OPS_API_KEY if present
    ops = os.environ.get("OPS_API_KEY") or os.environ.get("OP_SERVICE_ACCOUNT_TOKEN")
    if ops:
        os.environ["OP_SERVICE_ACCOUNT_TOKEN"] = ops

    # 3. Load .env.1password
    op_env = _find_file(".env.1password", base)
    if not op_env:
        return

    for line in op_env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key, val = key.strip(), rest.strip()
        if not key:
            continue
        if val.startswith("op://"):
            try:
                out = subprocess.run(
                    ["op", "read", val],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if out.returncode == 0:
                    os.environ[key] = out.stdout.strip()
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        else:
            os.environ.setdefault(key, val)
