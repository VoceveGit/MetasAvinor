"""Somente leitura no MySQL EXTRACTOR."""

import threading
import time

import pandas as pd
import mysql.connector
from mysql.connector import Error

from app.config import get_db_config


def get_connection():
    cfg = get_db_config()
    if not cfg.user or not cfg.password:
        if cfg.user and not cfg.password:
            msg = (
                "TEST_DB_PASSWORD está vazio no .env. "
                "Preencha a senha do MySQL (não commite o .env)."
            )
        else:
            msg = "Credenciais ausentes. Defina TEST_DB_USER e TEST_DB_PASSWORD no .env"
        raise Error(msg)
    return mysql.connector.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        connection_timeout=30,
        autocommit=True,
    )


_POOL_MAX = 4
_POOL_IDLE_S = 60.0
_POOL: list[tuple[float, object]] = []
_POOL_LOCK = threading.Lock()


def _acquire():
    agora = time.monotonic()
    while True:
        with _POOL_LOCK:
            item = _POOL.pop() if _POOL else None
        if item is None:
            return get_connection()
        ts, conn = item
        if agora - ts <= _POOL_IDLE_S:
            try:
                if conn.is_connected():
                    return conn
            except Error:
                pass
        _close(conn)


def _release(conn) -> None:
    with _POOL_LOCK:
        if len(_POOL) < _POOL_MAX:
            _POOL.append((time.monotonic(), conn))
            return
    _close(conn)


def _close(conn) -> None:
    try:
        conn.close()
    except Exception:
        pass


def read_sql(query: str, params: tuple | None = None) -> pd.DataFrame:
    conn = _acquire()
    try:
        df = pd.read_sql(query, conn, params=params)
    except (Error, pd.errors.DatabaseError):
        _close(conn)
        conn = get_connection()
        try:
            df = pd.read_sql(query, conn, params=params)
        except Exception:
            _close(conn)
            raise
    except Exception:
        _close(conn)
        raise
    _release(conn)
    return df
