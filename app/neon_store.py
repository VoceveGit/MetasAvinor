"""Persistência de premissas/snapshot no Neon (Postgres). Fallback: JSON local."""

from __future__ import annotations

import copy
import json
import os
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_SCHEMA_READY = False

# Uma instância no Render: cache em memória evita uma conexão ao Neon por leitura.
# Escritas atualizam o cache na hora; o TTL cobre edições feitas fora do app.
_CACHE_TTL_S = 60.0
_CACHE_LOCK = threading.Lock()
_DOC_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_VERSION_CACHE: dict[str, tuple[float, int]] = {}
_MIGRATED: set[str] = set()


def neon_enabled() -> bool:
    url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("DATABASE_URL")
    return bool(url and url.strip().startswith("postgres"))


def _database_url() -> str:
    url = os.environ.get("NEON_DATABASE_URL") or os.environ.get("DATABASE_URL") or ""
    url = url.strip()
    if not url:
        raise RuntimeError("NEON_DATABASE_URL não configurada.")
    return url


def _connect():
    import psycopg2

    return psycopg2.connect(_database_url(), connect_timeout=15)


def ensure_neon_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY or not neon_enabled():
        return
    sql_path = _PROJECT_ROOT / "sql" / "neon_app_state.sql"
    if not sql_path.exists():
        _SCHEMA_READY = True
        return
    ddl = sql_path.read_text(encoding="utf-8")
    conn = _connect()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(ddl)
        _SCHEMA_READY = True
    finally:
        conn.close()


def _fetch_doc(key: str) -> dict[str, Any]:
    ensure_neon_schema()
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT metas_kv_get(%s)", (key,))
            row = cur.fetchone()
            payload = row[0] if row else {}
            if isinstance(payload, str):
                payload = json.loads(payload)
            return payload if isinstance(payload, dict) else {}
    finally:
        conn.close()


def kv_get(key: str) -> dict[str, Any]:
    if not neon_enabled():
        return {}
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _DOC_CACHE.get(key)
        if hit and now - hit[0] < _CACHE_TTL_S:
            return copy.deepcopy(hit[1])
    payload = _fetch_doc(key)
    with _CACHE_LOCK:
        _DOC_CACHE[key] = (now, payload)
    return copy.deepcopy(payload)


def kv_set(key: str, payload: dict[str, Any]) -> None:
    if not neon_enabled():
        return
    ensure_neon_schema()
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT metas_kv_set(%s, %s::jsonb)", (key, body))
        conn.commit()
    finally:
        conn.close()
    with _CACHE_LOCK:
        _DOC_CACHE[key] = (time.monotonic(), copy.deepcopy(payload))
        _VERSION_CACHE.pop(key, None)


def kv_version(key: str) -> int:
    if not neon_enabled():
        return 0
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _VERSION_CACHE.get(key)
        if hit and now - hit[0] < _CACHE_TTL_S:
            return hit[1]
    ensure_neon_schema()
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT metas_kv_version(%s)", (key,))
            row = cur.fetchone()
            ver = int(row[0] or 0) if row else 0
    finally:
        conn.close()
    with _CACHE_LOCK:
        _VERSION_CACHE[key] = (now, ver)
    return ver


@lru_cache(maxsize=1)
def storage_backend_label() -> str:
    return "Neon" if neon_enabled() else "arquivo local"


def migrate_json_file_to_neon(file_path: Path, neon_key: str) -> bool:
    """Uma vez: copia JSON local para Neon se Neon vazio e arquivo existe."""
    if not neon_enabled() or neon_key in _MIGRATED:
        return False
    _MIGRATED.add(neon_key)
    if not file_path.exists():
        return False
    if kv_version(neon_key) > 0:
        return False
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not data:
        return False
    if neon_key == "grid_snapshot":
        kv_set(neon_key, data if isinstance(data, dict) else {"months": {}})
    else:
        kv_set(neon_key, data if isinstance(data, dict) else {})
    return True
