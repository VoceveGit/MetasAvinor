"""Snapshot completo da tabela de metas (carrega rápido após o primeiro salvamento).

No Neon cada mês é uma chave própria (``grid_snapshot:2026:10``): salvar um mês
não reescreve os outros. Sem Neon, tudo fica em ``grid_snapshot_local.json``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "grid_snapshot_local.json"
_VERSION = 3


def _key(ano: int, mes: int) -> str:
    return f"{ano}:{mes:02d}"


def _neon_key(ano: int, mes: int) -> str:
    return f"grid_snapshot:{_key(ano, mes)}"


def _load_local_root() -> dict:
    if not _SNAPSHOT_PATH.exists():
        return {"version": _VERSION, "months": {}}
    try:
        data = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": _VERSION, "months": {}}
    data.setdefault("months", {})
    return data


def _load_block(ano: int, mes: int) -> dict | None:
    from app.neon_store import kv_get, neon_enabled

    if neon_enabled():
        return kv_get(_neon_key(ano, mes)) or None
    return _load_local_root()["months"].get(_key(ano, mes))


def _save_block(ano: int, mes: int, block: dict) -> None:
    from app.neon_store import kv_set, neon_enabled

    if neon_enabled():
        kv_set(_neon_key(ano, mes), block)
        return
    data = _load_local_root()
    data["version"] = _VERSION
    data["months"][_key(ano, mes)] = block
    _SNAPSHOT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def snapshot_token(ano: int, mes: int) -> int:
    try:
        block = _load_block(ano, mes)
        return int(block.get("saved_at", 0)) if block else 0
    except (TypeError, ValueError):
        return 0


def load_grid_snapshot(ano: int, mes: int) -> list[dict] | None:
    try:
        block = _load_block(ano, mes)
    except TypeError:
        return None
    if not block or block.get("version") != _VERSION:
        return None
    rows = block.get("rows")
    if not isinstance(rows, list) or not rows:
        return None
    return rows


def _clean_value(v):
    if v is None:
        return None
    if hasattr(v, "item"):
        try:
            v = v.item()
        except (ValueError, AttributeError):
            return v
    if isinstance(v, float):
        if v != v:
            return None
        return round(v, 4)
    return v


def save_grid_snapshot(ano: int, mes: int, rows: list[dict]) -> None:
    clean = [{k: _clean_value(v) for k, v in row.items()} for row in rows]
    _save_block(
        ano,
        mes,
        {"version": _VERSION, "saved_at": int(time.time()), "rows": clean},
    )


def row_for_vendedor(ano: int, mes: int, vendedor_id: int) -> dict | None:
    rows = load_grid_snapshot(ano, mes)
    if not rows:
        return None
    for row in rows:
        if int(row.get("vendedor", 0)) == vendedor_id:
            return row
    return None
