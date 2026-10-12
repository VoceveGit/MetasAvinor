"""Snapshot completo da tabela de metas (carrega rápido após o primeiro salvamento)."""

from __future__ import annotations

import json
from pathlib import Path

_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "grid_snapshot_local.json"
_NEON_KEY = "grid_snapshot"
_VERSION = 1


def _empty_root() -> dict:
    return {"version": _VERSION, "months": {}}


def _load_root() -> dict:
    from app.neon_store import kv_get, migrate_json_file_to_neon, neon_enabled

    if neon_enabled():
        migrate_json_file_to_neon(_SNAPSHOT_PATH, _NEON_KEY)
        data = kv_get(_NEON_KEY)
        if not data:
            return _empty_root()
        if "months" not in data:
            data["months"] = {}
        return data
    if not _SNAPSHOT_PATH.exists():
        return _empty_root()
    try:
        data = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        if "months" not in data:
            data["months"] = {}
        return data
    except json.JSONDecodeError:
        return _empty_root()


def _save_root(data: dict) -> None:
    from app.neon_store import kv_set, neon_enabled

    if neon_enabled():
        kv_set(_NEON_KEY, data)
        return
    _SNAPSHOT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _key(ano: int, mes: int) -> str:
    return f"{ano}:{mes:02d}"


def snapshot_token(ano: int, mes: int) -> int:
    try:
        data = _load_root()
        block = data.get("months", {}).get(_key(ano, mes))
        if not block:
            return 0
        return int(block.get("saved_at", 0))
    except (TypeError, ValueError):
        return 0


def load_grid_snapshot(ano: int, mes: int) -> list[dict] | None:
    try:
        data = _load_root()
        block = data.get("months", {}).get(_key(ano, mes))
        if not block or block.get("version") != _VERSION:
            return None
        rows = block.get("rows")
        if not isinstance(rows, list) or not rows:
            return None
        return rows
    except TypeError:
        return None


def save_grid_snapshot(ano: int, mes: int, rows: list[dict]) -> None:
    import time

    data = _load_root()

    clean: list[dict] = []
    for row in rows:
        out = {}
        for k, v in row.items():
            if v is None:
                out[k] = None
            elif hasattr(v, "item"):
                try:
                    out[k] = v.item()
                except (ValueError, AttributeError):
                    out[k] = v
            else:
                out[k] = v
        clean.append(out)

    data["version"] = _VERSION
    data["months"][_key(ano, mes)] = {
        "version": _VERSION,
        "saved_at": int(time.time()),
        "rows": clean,
    }
    _save_root(data)


def row_for_vendedor(ano: int, mes: int, vendedor_id: int) -> dict | None:
    rows = load_grid_snapshot(ano, mes)
    if not rows:
        return None
    for row in rows:
        if int(row.get("vendedor", 0)) == vendedor_id:
            return row
    return None
