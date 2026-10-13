"""Plano anual de metas: meta do ano, sazonalidade, meses salvos e ajustes manuais.

Tudo fica num documento compacto (Neon ``plano_metas`` ou ``plano_metas_local.json``):

    {"v": 1, "anos": {"2026": {
        "meta": 100800000.0, "saz": true,
        "meses": {"10": {"t": 1760300000,
                         "c": {"1003": [1000000.0, 1200000.0]},
                         "a": {"1003": [0.2, "d"]}}}}}}

``c`` = [meta automática, meta do mês] por colaborador no momento do salvamento.
``a`` = ajuste manual em relação à automática (fração) e escopo:
``"m"`` só este mês, ``"d"`` deste mês em diante.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_PATH = Path(__file__).resolve().parent.parent / "plano_metas_local.json"
_NEON_KEY = "plano_metas"

ESCOPO_MES = "m"
ESCOPO_DIANTE = "d"
ESCOPO_LABEL = {ESCOPO_DIANTE: "Deste mês em diante", ESCOPO_MES: "Só este mês"}

COMP_DESLIGADA = "Desligada"
COMP_INDIVIDUAL = "Individual"
COMP_GERAL = "Geral"
COMP_MODOS = (COMP_DESLIGADA, COMP_INDIVIDUAL, COMP_GERAL)

_local_cache: tuple[float, dict] | None = None


# ---------------------------------------------------------------- armazenamento


def _empty() -> dict:
    return {"v": 1, "anos": {}}


def _load_root() -> dict:
    global _local_cache
    from app.neon_store import kv_get, neon_enabled

    if neon_enabled():
        data = kv_get(_NEON_KEY)
    elif _PATH.exists():
        mtime = _PATH.stat().st_mtime
        if _local_cache and _local_cache[0] == mtime:
            return json.loads(json.dumps(_local_cache[1]))
        try:
            data = json.loads(_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        _local_cache = (mtime, data)
        data = json.loads(json.dumps(data))
    else:
        data = {}
    if not isinstance(data, dict) or "anos" not in data:
        return _empty()
    return data


def _save_root(data: dict) -> None:
    from app.neon_store import kv_set, neon_enabled

    if neon_enabled():
        kv_set(_NEON_KEY, data)
        return
    _PATH.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def plano_token() -> int:
    """Muda a cada salvamento — usado para recarregar a tabela."""
    from app.neon_store import kv_version, neon_enabled

    if neon_enabled():
        return kv_version(_NEON_KEY)
    return int(_PATH.stat().st_mtime) if _PATH.exists() else 0


def _bloco_ano(data: dict, ano: int) -> dict:
    return data["anos"].setdefault(str(ano), {})


# ---------------------------------------------------------------- calendário


def mes_corrente() -> tuple[int, int]:
    hoje = date.today()
    return hoje.year, hoje.month


def mes_editavel(ano: int, mes: int) -> bool:
    """Meses fechados ficam automáticos e travados; o mês atual e os futuros, editáveis."""
    return (ano, mes) >= mes_corrente()


def mes_fechado(ano: int, mes: int) -> bool:
    return (ano, mes) < mes_corrente()


def meses_restantes(ano: int) -> list[int]:
    a, m = mes_corrente()
    if ano < a:
        return []
    if ano > a:
        return list(range(1, 13))
    return list(range(m, 13))


def _mes_ref_pesos(ano: int, mes: int) -> tuple[int, int]:
    """Mês futuro ainda não tem os 3 meses anteriores fechados: usa o peso do mês atual."""
    return min((ano, mes), mes_corrente())


# ---------------------------------------------------------------- meta do ano


def _meta_anual_premissas(ano: int) -> float:
    from app.premissas import get_premissa_empresa

    return float(get_premissa_empresa(ano, 1).meta_empresa_anual_rs or 0)


def get_config_ano(ano: int) -> tuple[float, bool]:
    """(meta anual, sazonalidade ligada)."""
    blk = _load_root()["anos"].get(str(ano)) or {}
    meta = float(blk.get("meta") or 0)
    if meta <= 0:
        meta = _meta_anual_premissas(ano)
    return meta, bool(blk.get("saz", False))


def save_config_ano(ano: int, meta_anual: float, sazonal: bool) -> None:
    data = _load_root()
    blk = _bloco_ano(data, ano)
    blk["meta"] = round(float(meta_anual), 2)
    blk["saz"] = bool(sazonal)
    _save_root(data)


@dataclass(frozen=True)
class SugestaoAnual:
    ano: int
    fat_ano_menos_2: float
    fat_ano_menos_1: float
    crescimento: float
    realizado_fechado: float
    meses_fechados: int
    base_restante: float
    projecao_restante: float
    sugestao: float


def sugestao_meta_anual(ano: int) -> SugestaoAnual:
    """Realizado dos meses fechados + mesmos meses do ano anterior × (1 + crescimento)."""
    from app.data import load_fat_empresa_mensal

    fat = load_fat_empresa_mensal((ano - 2, ano - 1, ano))
    f2 = sum(v for (a, _), v in fat.items() if a == ano - 2)
    f1 = sum(v for (a, _), v in fat.items() if a == ano - 1)
    g = (f1 / f2 - 1.0) if f2 > 0 else 0.0
    restantes = set(meses_restantes(ano))
    fechados = [m for m in range(1, 13) if m not in restantes]
    real = sum(fat.get((ano, m), 0.0) for m in fechados)
    base = sum(fat.get((ano - 1, m), 0.0) for m in restantes)
    proj = base * (1.0 + g)
    return SugestaoAnual(
        ano=ano,
        fat_ano_menos_2=f2,
        fat_ano_menos_1=f1,
        crescimento=g,
        realizado_fechado=real,
        meses_fechados=len(fechados),
        base_restante=base,
        projecao_restante=proj,
        sugestao=real + proj,
    )


def pesos_sazonais(ano: int) -> dict[int, float]:
    """Fatia de cada mês no ano: média das fatias dos dois anos anteriores."""
    from app.data import load_fat_empresa_mensal

    fat = load_fat_empresa_mensal((ano - 2, ano - 1))
    fatias: list[dict[int, float]] = []
    for a in (ano - 2, ano - 1):
        tot = sum(fat.get((a, m), 0.0) for m in range(1, 13))
        meses_ok = sum(1 for m in range(1, 13) if fat.get((a, m), 0.0) > 0)
        if tot > 0 and meses_ok == 12:
            fatias.append({m: fat.get((a, m), 0.0) / tot for m in range(1, 13)})
    if not fatias:
        return {m: 1.0 / 12.0 for m in range(1, 13)}
    media = {m: sum(f[m] for f in fatias) / len(fatias) for m in range(1, 13)}
    soma = sum(media.values()) or 1.0
    return {m: v / soma for m, v in media.items()}


def pesos_meses(ano: int, sazonal: bool | None = None) -> dict[int, float]:
    if sazonal is None:
        sazonal = get_config_ano(ano)[1]
    return pesos_sazonais(ano) if sazonal else {m: 1.0 / 12.0 for m in range(1, 13)}


def meta_plano_mes(
    ano: int,
    mes: int,
    meta_anual: float | None = None,
    sazonal: bool | None = None,
) -> float:
    """Fatia do mês na meta anual (antes de ajustes manuais). Parâmetros = prévia sem salvar."""
    meta, saz = get_config_ano(ano)
    if meta_anual is not None:
        meta = float(meta_anual)
    if sazonal is not None:
        saz = bool(sazonal)
    if meta > 0:
        return meta * pesos_meses(ano, saz)[mes]
    from app.premissas import get_premissa_empresa

    return float(get_premissa_empresa(ano, mes).meta_empresa_rs or 0)


# ---------------------------------------------------------------- meses salvos


def meses_salvos(ano: int) -> dict[int, dict]:
    blk = _load_root()["anos"].get(str(ano)) or {}
    return {int(k): v for k, v in (blk.get("meses") or {}).items()}


def mes_salvo(ano: int, mes: int) -> dict | None:
    return meses_salvos(ano).get(mes)


def save_mes(
    ano: int,
    mes: int,
    colab: dict[int, tuple[float, float]],
    ajustes: dict[int, tuple[float, str]],
) -> None:
    data = _load_root()
    blk = _bloco_ano(data, ano)
    blk.setdefault("meses", {})[str(mes)] = {
        "t": int(time.time()),
        "c": {str(v): [round(a, 2), round(f, 2)] for v, (a, f) in colab.items()},
        "a": {str(v): [round(p, 6), e] for v, (p, e) in ajustes.items()},
    }
    _save_root(data)


# ---------------------------------------------------------------- colaboradores


def _meses_anteriores(ano: int, mes: int, n: int) -> list[tuple[int, int]]:
    out = []
    y, m = ano, mes
    for _ in range(n):
        m -= 1
        if m < 1:
            y, m = y - 1, 12
        out.append((y, m))
    return out


def pesos_colaboradores(ano: int, mes: int) -> dict[int, float]:
    """Peso de cada colaborador no faturamento dos 3 meses fechados de referência.

    Usa o faturamento por vendedor/mês do ano (uma consulta por ano, em cache), então
    calcular os 12 meses não multiplica consultas ao ERP.
    """
    from app.data import load_fat_vendedor_mes_ano

    ra, rm = _mes_ref_pesos(ano, mes)
    janela = _meses_anteriores(ra, rm, 3)
    por_ano = {y: load_fat_vendedor_mes_ano(y) for y in {y for y, _ in janela} | {ra}}
    fat_v: dict[int, float] = {}
    for y, m in janela:
        for (vid, mk), fat in por_ano[y].items():
            if mk == m:
                fat_v[vid] = fat_v.get(vid, 0.0) + fat
    for (vid, mk), fat in por_ano[ra].items():
        if mk == rm and fat > 0:
            fat_v.setdefault(vid, 0.0)
    total = sum(fat_v.values())
    if total <= 0:
        return {vid: 1.0 / len(fat_v) for vid in fat_v} if fat_v else {}
    return {vid: f / total for vid, f in fat_v.items()}


def ajustes_herdados(ano: int, mes: int) -> dict[int, tuple[float, int]]:
    """Ajustes "deste mês em diante" de meses salvos anteriores: vid → (fração, mês de origem).

    "Só este mês" não passa adiante. Um mês salvo em que o colaborador ficou sem ajuste
    encerra a herança dele.
    """
    salvos = meses_salvos(ano)
    out: dict[int, tuple[float, int]] = {}
    encerrados: set[int] = set()
    for k in sorted((k for k in salvos if k < mes), reverse=True):
        blk = salvos[k]
        ajustes = blk.get("a") or {}
        for vid_s in blk.get("c") or {}:
            vid = int(vid_s)
            if vid in out or vid in encerrados:
                continue
            aj = ajustes.get(vid_s)
            if aj is None:
                encerrados.add(vid)
            elif aj[1] == ESCOPO_DIANTE:
                out[vid] = (float(aj[0]), k)
    return out


@dataclass(frozen=True)
class MetaColab:
    vendedor: int
    peso: float
    auto: float
    final: float
    pct: float
    origem: str  # "auto" | "herdado" | "salvo"
    mes_origem: int | None = None


def metas_colaboradores_mes(ano: int, mes: int) -> dict[int, MetaColab]:
    salvo = mes_salvo(ano, mes)
    if salvo and salvo.get("c"):
        base = sum(v[0] for v in salvo["c"].values()) or 1.0
        out = {}
        for vid_s, (auto, final) in salvo["c"].items():
            pct = (final / auto - 1.0) if auto > 0 else 0.0
            out[int(vid_s)] = MetaColab(int(vid_s), auto / base, auto, final, pct, "salvo", mes)
        return out

    base = meta_plano_mes(ano, mes)
    pesos = pesos_colaboradores(ano, mes)
    herd = ajustes_herdados(ano, mes) if pesos else {}
    out = {}
    for vid, peso in pesos.items():
        auto = base * peso
        pct, origem_mes = herd.get(vid, (0.0, None))
        out[vid] = MetaColab(
            vid,
            peso,
            auto,
            auto * (1.0 + pct),
            pct,
            "herdado" if vid in herd else "auto",
            origem_mes,
        )
    return out


def meta_empresa_mes(
    ano: int,
    mes: int,
    meta_anual: float | None = None,
    sazonal: bool | None = None,
) -> float:
    """Meta do mês da empresa = soma das metas dos colaboradores (com ajustes manuais)."""
    salvo = mes_salvo(ano, mes)
    if salvo and salvo.get("c"):
        return float(sum(v[1] for v in salvo["c"].values()))
    base = meta_plano_mes(ano, mes, meta_anual, sazonal)
    if base <= 0:
        return 0.0
    herd = ajustes_herdados(ano, mes)
    if not herd:
        return base
    pesos = pesos_colaboradores(ano, mes)
    return base * (1.0 + sum(pesos.get(v, 0.0) * p for v, (p, _) in herd.items()))


def metas_empresa_ano(
    ano: int,
    meta_anual: float | None = None,
    sazonal: bool | None = None,
) -> dict[int, float]:
    return {m: meta_empresa_mes(ano, m, meta_anual, sazonal) for m in range(1, 13)}


# ---------------------------------------------------------------- compensação


@dataclass(frozen=True)
class Compensacao:
    modo: str
    saldo_total: float  # > 0: equipe ficou devendo; < 0: passou da meta
    fatia_mes: float  # parte do saldo que cai neste mês
    total_mes: float
    por_vendedor: dict[int, float]


def compensacao_mes(ano: int, mes: int, modo: str) -> Compensacao:
    """Saldo dos meses fechados do ano diluído nos meses restantes (pelo peso de cada mês).

    Individual: cada colaborador carrega o próprio saldo. Geral: o saldo da equipe é
    dividido pelo peso de cada um. É só visão — não altera o plano salvo.
    """
    vazio = Compensacao(modo, 0.0, 0.0, 0.0, {})
    restantes = meses_restantes(ano)
    if modo == COMP_DESLIGADA or mes not in restantes:
        return vazio
    fechados = [m for m in range(1, 13) if m not in restantes]
    if not fechados:
        return vazio

    from app.data import load_fat_vendedor_mes_ano

    real = load_fat_vendedor_mes_ano(ano)
    saldo: dict[int, float] = {}
    for k in fechados:
        for vid, mc in metas_colaboradores_mes(ano, k).items():
            saldo[vid] = saldo.get(vid, 0.0) + mc.final
        for (vid, mk), fat in real.items():
            if mk == k:
                saldo[vid] = saldo.get(vid, 0.0) - fat
    saldo_total = sum(saldo.values())

    w = pesos_meses(ano)
    soma_w = sum(w[m] for m in restantes) or 1.0
    fatia = w[mes] / soma_w

    if modo == COMP_INDIVIDUAL:
        por_vid = {vid: s * fatia for vid, s in saldo.items()}
    else:
        pesos = pesos_colaboradores(ano, mes)
        por_vid = {vid: saldo_total * fatia * p for vid, p in pesos.items()}
    return Compensacao(modo, saldo_total, fatia, saldo_total * fatia, por_vid)
