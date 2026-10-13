from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

CANAIS_VENDEDOR = [
    "Não informado",
    "Televendas",
    "Externo",
    "Venda direta",
]

_PREMISSAS_PATH = Path(__file__).resolve().parent.parent / "premissas_local.json"
_NEON_KEY = "premissas"


@dataclass
class PremissaVendedor:
    canal: str = "Não informado"
    oportunidades_mes: float = 0.0
    conversao_meta_pct: float = 0.0
    meta_faturamento_rs: float = 0.0
    meta_cobertura_qtd: float = 0.0
    meta_recorrencia: float = 0.0
    meta_positivacao: float = 0.0
    tx_conv_projetada_pct: float = 0.0
    ticket_meta: float = 0.0
    cobertura_meta_pct: float = 0.0
    taxa_cobertura: float = 0.9
    usar_meta_oficial_rs: bool = False


@dataclass
class PremissaEmpresa:
    meta_empresa_anual_rs: float = 0.0
    meta_empresa_rs: float = 0.0
    limite_televendas_rs: float = 0.0
    limite_externo_rs: float = 0.0
    limite_grandes_redes_rs: float = 0.0


def _storage_key(vendedor_id: int, ano: int, mes: int) -> str:
    return f"{vendedor_id}:{ano}:{mes:02d}"


def _empresa_key(ano: int, mes: int) -> str:
    return f"empresa:{ano}:{mes:02d}"


def premissas_file_token() -> int:
    """Mudança no storage → recarregar grade."""
    from app.neon_store import kv_version, migrate_json_file_to_neon, neon_enabled

    if neon_enabled():
        migrate_json_file_to_neon(_PREMISSAS_PATH, _NEON_KEY)
        return kv_version(_NEON_KEY)
    if not _PREMISSAS_PATH.exists():
        return 0
    return int(_PREMISSAS_PATH.stat().st_mtime)


_local_cache: tuple[float, dict] | None = None


def _load_all() -> dict:
    global _local_cache
    from app.neon_store import kv_get, migrate_json_file_to_neon, neon_enabled

    if neon_enabled():
        migrate_json_file_to_neon(_PREMISSAS_PATH, _NEON_KEY)
        return kv_get(_NEON_KEY)
    if not _PREMISSAS_PATH.exists():
        return {}
    mtime = _PREMISSAS_PATH.stat().st_mtime
    if _local_cache is None or _local_cache[0] != mtime:
        try:
            _local_cache = (mtime, json.loads(_PREMISSAS_PATH.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return {}
    return json.loads(json.dumps(_local_cache[1]))


def _save_all(data: dict) -> None:
    from app.neon_store import kv_set, neon_enabled

    if neon_enabled():
        kv_set(_NEON_KEY, data)
        return
    _PREMISSAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PREMISSAS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_premissa(vendedor_id: int, ano: int, mes: int) -> PremissaVendedor:
    raw = _load_all().get(_storage_key(vendedor_id, ano, mes))
    if not raw:
        return PremissaVendedor()
    allowed = {f.name for f in PremissaVendedor.__dataclass_fields__.values()}
    return PremissaVendedor(**{k: v for k, v in raw.items() if k in allowed})


def save_premissa(vendedor_id: int, ano: int, mes: int, premissa: PremissaVendedor) -> None:
    data = _load_all()
    data[_storage_key(vendedor_id, ano, mes)] = asdict(premissa)
    _save_all(data)


def save_premissas_lote(ano: int, mes: int, premissas: dict[int, PremissaVendedor]) -> None:
    """Grava várias premissas com uma leitura e uma escrita."""
    data = _load_all()
    for vid, prem in premissas.items():
        data[_storage_key(int(vid), ano, mes)] = asdict(prem)
    _save_all(data)


def _meta_anual_do_ano(data: dict, ano: int) -> float:
    """A meta anual vale para o ano todo, em qualquer mês em que tenha sido salva."""
    for m in range(12, 0, -1):
        raw = data.get(_empresa_key(ano, m)) or {}
        v = float(raw.get("meta_empresa_anual_rs") or 0)
        if v > 0:
            return v
    return 0.0


def get_premissa_empresa(ano: int, mes: int) -> PremissaEmpresa:
    data = _load_all()
    raw = data.get(_empresa_key(ano, mes))
    allowed = {f.name for f in PremissaEmpresa.__dataclass_fields__.values()}
    emp = (
        PremissaEmpresa(**{k: v for k, v in raw.items() if k in allowed})
        if raw
        else PremissaEmpresa()
    )
    if emp.meta_empresa_anual_rs <= 0:
        emp.meta_empresa_anual_rs = _meta_anual_do_ano(data, ano)
    return emp


def save_premissa_empresa(ano: int, mes: int, premissa: PremissaEmpresa) -> None:
    data = _load_all()
    data[_empresa_key(ano, mes)] = asdict(premissa)
    _save_all(data)


def vendedor_tem_premissa(vendedor_id: int, ano: int, mes: int) -> bool:
    return _storage_key(vendedor_id, ano, mes) in _load_all()


def count_premissas_vendedor_mes(ano: int, mes: int) -> int:
    suffix = f":{ano}:{mes:02d}"
    data = _load_all()
    return sum(
        1
        for key in data
        if key.endswith(suffix) and not key.startswith("empresa:")
    )
