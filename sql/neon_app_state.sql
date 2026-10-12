-- MetasAvinor — estado da aplicação (premissas, snapshot da grade).
-- Rode no SQL Editor do Neon (projeto de app state, separado do MySQL EXTRACTOR).

CREATE TABLE IF NOT EXISTS metas_avinor_kv (
    key TEXT PRIMARY KEY,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION metas_kv_get(p_key TEXT)
RETURNS JSONB
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(
        (SELECT payload FROM metas_avinor_kv WHERE key = p_key),
        '{}'::jsonb
    );
$$;

CREATE OR REPLACE FUNCTION metas_kv_set(p_key TEXT, p_payload JSONB)
RETURNS TIMESTAMPTZ
LANGUAGE sql
AS $$
    INSERT INTO metas_avinor_kv (key, payload, updated_at)
    VALUES (p_key, p_payload, now())
    ON CONFLICT (key) DO UPDATE
        SET payload = EXCLUDED.payload,
            updated_at = now()
    RETURNING updated_at;
$$;

CREATE OR REPLACE FUNCTION metas_kv_version(p_key TEXT)
RETURNS BIGINT
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(
        (SELECT (EXTRACT(EPOCH FROM updated_at))::bigint FROM metas_avinor_kv WHERE key = p_key),
        0::bigint
    );
$$;
