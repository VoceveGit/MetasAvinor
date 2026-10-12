"""Somente leitura no MySQL EXTRACTOR."""

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
    )


def read_sql(query: str, params: tuple | None = None) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(query, conn, params=params)
    finally:
        conn.close()
