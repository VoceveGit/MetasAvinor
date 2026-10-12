"""Sugestões no estilo planilha: ~+5% e arredondar em passos práticos."""

from __future__ import annotations

import math


def sugerir_pct_meta(hist_pct: float) -> float:
    """Histórico + ~5%, arredondado para cima em degraus de 5 p.p. (ex.: 41 → 45)."""
    if hist_pct <= 0:
        return 0.0
    alvo = hist_pct * 1.05
    if 85.0 <= hist_pct < 92.0:
        alvo = max(alvo, 95.0)
    return min(100.0, math.ceil(alvo / 5.0) * 5.0)


def sugerir_tx_cobertura_projetada(hist_cob_pct: float, default_pct: float = 90.0) -> float:
    """TX conversão projetada (cobertura): padrão 90% ou histórico de cobertura + ~5%."""
    if hist_cob_pct <= 0:
        return default_pct
    sug = sugerir_pct_meta(hist_cob_pct)
    return max(default_pct, sug) if default_pct > 0 else sug


def sugerir_ticket_meta(ticket_hist: float) -> float:
    """Ticket histórico + ~5%, arredondado para inteiro “redondo”."""
    if ticket_hist <= 0:
        return 0.0
    base = ticket_hist * 1.05
    if base < 500:
        return math.ceil(base / 50.0) * 50.0
    if base < 5_000:
        return math.ceil(base / 100.0) * 100.0
    if base < 20_000:
        return math.ceil(base / 500.0) * 500.0
    return math.ceil(base / 1_000.0) * 1_000.0


def sugerir_recorrencia_meta(rec_media: float) -> float:
    if rec_media <= 0:
        return 0.0
    return round(rec_media * 1.05, 1)
