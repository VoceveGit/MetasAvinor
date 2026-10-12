from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.db import read_sql

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ROTAS_CANDIDATES = (
    _PROJECT_ROOT / "data" / "ROTAS AVINOR.xlsx",
    _PROJECT_ROOT / "ROTAS AVINOR.xlsx",
)

VDC_CIDADE_NORM = "VITORIA DA CONQUISTA"
SEMANAS_NO_MES = 4
FALLBACK_CONTATOS_SEMANA = 1.04


def _normalize_key(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text)
    return text


def contatos_por_semana(enviar_cards: object) -> float:
    """Dias de contato CRM por semana a partir da coluna Enviar cards."""
    raw = _normalize_key(enviar_cards)
    if not raw:
        return 0.0
    if "QUINZENAL" in raw:
        return 0.5
    dias = ("SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO")
    found = sum(1 for d in dias if d in raw)
    if found > 0:
        return float(found)
    return 1.0


def find_rotas_path() -> Path | None:
    for path in _ROTAS_CANDIDATES:
        if path.is_file():
            return path
    return None


def _resolve_rotas_path() -> Path:
    path = find_rotas_path()
    if path is None:
        raise FileNotFoundError(
            "Planilha ROTAS AVINOR.xlsx não encontrada (raiz do projeto ou pasta data/)."
        )
    return path


def rotas_file_info() -> dict:
    path = find_rotas_path()
    if path is None:
        return {"presente": False, "caminho": "", "atualizado_em": None}
    mtime = path.stat().st_mtime
    from datetime import datetime

    return {
        "presente": True,
        "caminho": str(path),
        "atualizado_em": datetime.fromtimestamp(mtime),
    }


def clear_rotas_cache() -> None:
    _load_rotas_tables.cache_clear()
    build_oportunidades_por_vendedor.cache_clear()


def save_rotas_workbook(content: bytes) -> Path:
    dest = _PROJECT_ROOT / "data" / "ROTAS AVINOR.xlsx"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    clear_rotas_cache()
    return dest


@lru_cache(maxsize=1)
def _load_rotas_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    path = _resolve_rotas_path()
    rotas = pd.read_excel(path, sheet_name="Rotas")
    rotas = rotas.iloc[:, :4].copy()
    rotas.columns = ["cidade", "rota", "saida_carga", "enviar_cards"]
    vdc = pd.read_excel(path, sheet_name=1)
    vdc = vdc.iloc[:, :3].copy()
    vdc.columns = ["cidade", "bairro", "rota"]
    return rotas, vdc


def _build_lookup_rotas(rotas: pd.DataFrame) -> dict[str, float]:
    """Cidade (normalizada) → contatos/semana; duplicatas: maior valor."""
    by_city: dict[str, float] = {}
    for row in rotas.itertuples(index=False):
        cidade = _normalize_key(row.cidade)
        rota = _normalize_key(row.rota)
        if not cidade:
            continue
        if cidade == VDC_CIDADE_NORM and rota.startswith("VDC "):
            continue
        cps = contatos_por_semana(row.enviar_cards)
        by_city[cidade] = max(by_city.get(cidade, 0.0), cps)
    return by_city


def _build_lookup_vdc(rotas: pd.DataFrame, vdc: pd.DataFrame) -> dict[str, float]:
    """Bairro normalizado → contatos/semana (via rota VDC na aba Rotas)."""
    rota_cards: dict[str, float] = {}
    for row in rotas.itertuples(index=False):
        rota = _normalize_key(row.rota)
        if rota.startswith("VDC "):
            rota_cards[rota] = contatos_por_semana(row.enviar_cards)

    by_bairro: dict[str, float] = {}
    for row in vdc.itertuples(index=False):
        if _normalize_key(row.cidade) != VDC_CIDADE_NORM:
            continue
        bairro = _normalize_key(row.bairro)
        rota = _normalize_key(row.rota)
        if not bairro or not rota:
            continue
        cps = rota_cards.get(rota)
        if cps is None:
            continue
        by_bairro[bairro] = cps
    return by_bairro


def contatos_semana_cliente(
    cidade: object,
    bairro: object,
    lookup_cidade: dict[str, float],
    lookup_vdc_bairro: dict[str, float],
) -> float | None:
    cidade_n = _normalize_key(cidade)
    if not cidade_n:
        return None
    if cidade_n == VDC_CIDADE_NORM:
        bairro_n = _normalize_key(bairro)
        if bairro_n and bairro_n in lookup_vdc_bairro:
            return lookup_vdc_bairro[bairro_n]
        return lookup_cidade.get(cidade_n)
    return lookup_cidade.get(cidade_n)


def oportunidades_mes_de_contatos_semana(contatos_semana: float) -> int:
    return int(round(contatos_semana * SEMANAS_NO_MES))


@lru_cache(maxsize=1)
def build_oportunidades_por_vendedor() -> pd.DataFrame:
    """
    Soma oportunidades/mês (contatos/semana × 4) por vendedor, cruzando carteira ativa com ROTAS AVINOR.
    Clientes sem rota usam fallback ~1,04 contato/semana (mesma lógica da estimativa Frigosol).
    """
    rotas, vdc = _load_rotas_tables()
    lookup_cidade = _build_lookup_rotas(rotas)
    lookup_vdc = _build_lookup_vdc(rotas, vdc)

    clientes = read_sql(
        """
        SELECT
            `Cliente` AS cliente,
            `Cidade` AS cidade,
            `Bairro` AS bairro,
            `Vendedor` AS vendedor
        FROM base_clientes_avinor
        WHERE `Situação` = 'Ativo' AND `Vendedor` > 0
        """
    )
    if clientes.empty:
        return pd.DataFrame(
            columns=[
                "vendedor",
                "oportunidades_mes",
                "clientes_mapeados",
                "clientes_sem_rota",
                "carteira",
            ]
        )

    rows: list[dict] = []
    for vend, grp in clientes.groupby("vendedor"):
        oport = 0
        mapeados = 0
        sem_rota = 0
        for r in grp.itertuples(index=False):
            cps = contatos_semana_cliente(
                r.cidade, r.bairro, lookup_cidade, lookup_vdc
            )
            if cps is None:
                sem_rota += 1
                cps = FALLBACK_CONTATOS_SEMANA
            else:
                mapeados += 1
            oport += oportunidades_mes_de_contatos_semana(cps)
        rows.append(
            {
                "vendedor": int(vend),
                "oportunidades_mes": int(oport),
                "clientes_mapeados": mapeados,
                "clientes_sem_rota": sem_rota,
                "carteira": len(grp),
            }
        )
    return pd.DataFrame(rows)


def oportunidades_rotas_vendedor(vendedor_id: int) -> int | None:
    df = build_oportunidades_por_vendedor()
    row = df.loc[df["vendedor"] == vendedor_id]
    if row.empty:
        return None
    return int(row.iloc[0]["oportunidades_mes"])
