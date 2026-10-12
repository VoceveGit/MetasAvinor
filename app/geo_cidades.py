from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "cidade_latlon.json"

# Coordenadas fixas (interior BA — base Avinor) para não depender de rede no primeiro paint
_FALLBACK: dict[str, tuple[float, float]] = {
    "VITORIA DA CONQUISTA|BA": (-14.8661, -40.8394),
    "VDC|BA": (-14.8661, -40.8394),
    "BOTUPORA|BA": (-13.3378, -42.5247),
    "BARREIRAS|BA": (-12.1529, -44.9900),
    "BRUMADO|BA": (-14.2036, -41.6653),
    "ITAPETINGA|BA": (-15.2547, -40.2481),
    "ITAMBÉ|BA": (-15.0411, -40.6244),
    "PLANALTO|BA": (-14.6508, -40.4786),
    "POÇÕES|BA": (-14.5167, -40.3667),
    "POCOES|BA": (-14.5167, -40.3667),
    "JEQUIÉ|BA": (-13.8588, -40.0851),
    "JEQUIE|BA": (-13.8588, -40.0851),
    "SALVADOR|BA": (-12.9777, -38.5016),
    "ILHÉUS|BA": (-14.7886, -39.0494),
    "ILHEUS|BA": (-14.7886, -39.0494),
}


def _normalize_cidade(cidade: str) -> str:
    s = re.sub(r"\s+", " ", str(cidade or "").strip().upper())
    return s


def _cache_key(cidade: str, uf: str) -> str:
    return f"{_normalize_cidade(cidade)}|{str(uf or '').strip().upper()}"


def _load_cache() -> dict[str, list[float]]:
    if not _CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(data: dict[str, list[float]]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def lookup_latlon(cidade: str, uf: str) -> tuple[float, float] | None:
    key = _cache_key(cidade, uf)
    if key in _FALLBACK:
        return _FALLBACK[key]
    cache = _load_cache()
    if key in cache and len(cache[key]) == 2:
        return float(cache[key][0]), float(cache[key][1])
    return None


def geocode_cidade(cidade: str, uf: str, timeout: float = 8.0) -> tuple[float, float] | None:
    """Nominatim (OSM) com cache local — só para cidades ainda sem coordenada."""
    key = _cache_key(cidade, uf)
    hit = lookup_latlon(cidade, uf)
    if hit:
        return hit
    q = f"{cidade}, {uf}, Brasil"
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1}
    )
    req = urllib.request.Request(url, headers={"User-Agent": "MetasAvinor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    if not data:
        return None
    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    cache = _load_cache()
    cache[key] = [lat, lon]
    _save_cache(cache)
    return lat, lon


def enrich_coords(df, cidade_col: str = "cidade", uf_col: str = "uf", max_geocode: int = 15):
    """Adiciona lat/lon; geocodifica no máximo max_geocode cidades novas por chamada."""
    import pandas as pd

    lats: list[float | None] = []
    lons: list[float | None] = []
    geocoded = 0
    for _, row in df.iterrows():
        latlon = lookup_latlon(row[cidade_col], row[uf_col])
        if latlon is None and geocoded < max_geocode:
            latlon = geocode_cidade(row[cidade_col], row[uf_col])
            if latlon:
                geocoded += 1
        if latlon:
            lats.append(latlon[0])
            lons.append(latlon[1])
        else:
            lats.append(None)
            lons.append(None)
    out = df.copy()
    out["lat"] = lats
    out["lon"] = lons
    return out
