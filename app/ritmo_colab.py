"""Sazonalidade semanal por colaborador (3 meses fechados) → peso e meta da semana/dia."""

from __future__ import annotations

import pandas as pd

from app.data import load_faturamento_diario_trimestre
from app.dates_util import business_days_between, semana_do_mes, semanas_mes
from app.equipe_grid_logic import _f, meta_final_row


MAX_SEM = 5


def _du_semanas(ano: int, mes: int) -> list[int]:
    return [max(business_days_between(a, b), 0) for a, b in semanas_mes(ano, mes)]


def pesos_uteis(ano: int, mes: int) -> list[float]:
    dus = _du_semanas(ano, mes)
    tot = sum(dus) or 1
    n = len(dus)
    return [(dus[i] / tot * 100.0) if i < n else 0.0 for i in range(MAX_SEM)]


def _hist_shares(ano: int, mes: int) -> dict[int, list[float]]:
    """Média das fatias de faturamento por semana-do-mês (0–4) nos 3 meses fechados."""
    df = load_faturamento_diario_trimestre(ano, mes)
    n_alvo = len(semanas_mes(ano, mes))
    if df.empty:
        return {}
    df = df.copy()
    df["dia"] = pd.to_datetime(df["dia"]).dt.date
    df["vendedor"] = df["vendedor"].astype(int)
    df["fat"] = pd.to_numeric(df["faturamento"], errors="coerce").fillna(0.0)
    df["ym"] = df["dia"].map(lambda d: (d.year, d.month))
    df["wi"] = df["dia"].map(semana_do_mes)

    acc: dict[int, list[list[float]]] = {}
    for (vid, _ym), g in df.groupby(["vendedor", "ym"]):
        tot = float(g["fat"].sum())
        if tot <= 0:
            continue
        slot = [0.0] * MAX_SEM
        for wi, sg in g.groupby("wi"):
            i = int(wi)
            if 0 <= i < MAX_SEM:
                slot[i] = float(sg["fat"].sum()) / tot
        acc.setdefault(int(vid), []).append(slot)

    out: dict[int, list[float]] = {}
    for vid, meses in acc.items():
        k = len(meses)
        avg = [sum(m[i] for m in meses) / k for i in range(MAX_SEM)]
        usable = avg[:n_alvo]
        s = sum(usable)
        if s > 0:
            usable = [x / s for x in usable]
        else:
            usable = pesos_uteis(ano, mes)[:n_alvo]
            su = sum(usable) or 1
            usable = [x / su for x in usable]
        while len(usable) < MAX_SEM:
            usable.append(0.0)
        out[vid] = [x * 100.0 for x in usable]
    return out


def _hist_fat_semana(ano: int, mes: int) -> dict[int, list[float]]:
    """Média de R$ naquela semana-do-mês (soma nos 3m ÷ meses em que a semana existiu)."""
    df = load_faturamento_diario_trimestre(ano, mes)
    if df.empty:
        return {}
    df = df.copy()
    df["dia"] = pd.to_datetime(df["dia"]).dt.date
    df["vendedor"] = df["vendedor"].astype(int)
    df["fat"] = pd.to_numeric(df["faturamento"], errors="coerce").fillna(0.0)
    df["ym"] = df["dia"].map(lambda d: (d.year, d.month))
    df["wi"] = df["dia"].map(semana_do_mes)

    soma: dict[int, list[float]] = {}
    cnt: dict[int, list[int]] = {}
    for (vid, _ym), g in df.groupby(["vendedor", "ym"]):
        vid = int(vid)
        soma.setdefault(vid, [0.0] * MAX_SEM)
        cnt.setdefault(vid, [0] * MAX_SEM)
        for wi, sg in g.groupby("wi"):
            i = int(wi)
            if 0 <= i < MAX_SEM:
                soma[vid][i] += float(sg["fat"].sum())
                cnt[vid][i] += 1
    out: dict[int, list[float]] = {}
    for vid, s in soma.items():
        out[vid] = [s[i] / cnt[vid][i] if cnt[vid][i] else 0.0 for i in range(MAX_SEM)]
    return out


def aplicar_ritmo_sugerido(rows: list[dict], ano: int, mes: int) -> list[dict]:
    n = len(semanas_mes(ano, mes))
    du_w = _du_semanas(ano, mes)
    du_pad = pesos_uteis(ano, mes)
    shares = _hist_shares(ano, mes)
    fat_w = _hist_fat_semana(ano, mes)
    out = []
    for row in rows:
        r = dict(row)
        vid = int(r["vendedor"])
        sug = shares.get(vid) or list(du_pad)
        hist = fat_w.get(vid) or [0.0] * MAX_SEM
        origem = "histórico 3m" if vid in shares else "dias úteis do mês"
        for i in range(MAX_SEM):
            hab = sug[i] if i < n else 0.0
            r[f"peso_sem_hab_{i+1}"] = round(hab, 1) if i < n else None
            r[f"peso_sem_sug_{i+1}"] = round(hab * 1.05, 1) if i < n and hab > 0 else None
            r[f"fat_sem_hist_{i+1}"] = round(hist[i], 0) if i < n else None
            r[f"du_sem_{i+1}"] = du_w[i] if i < n else 0
            if r.get(f"peso_sem_man_{i+1}") is None:
                r[f"peso_sem_man_{i+1}"] = 0.0
        r["n_semanas"] = n
        r["ritmo_origem"] = origem
        r["ritmo_info"] = (
            f"Peso habitual: {origem}. "
            "Dourado = evolução atingível (habitual × 1,05). "
            "Manual vazio = vale o dourado. Meta da semana = meta do mês × peso aplicado."
        )
        out.append(r)
    return out


def peso_sem_efetivo(row: dict, i: int) -> float:
    man = _f(row, f"peso_sem_man_{i}")
    return man if man > 0 else _f(row, f"peso_sem_sug_{i}")


def tem_peso_manual(row: dict, n: int) -> bool:
    return any(_f(row, f"peso_sem_man_{i}") > 0 for i in range(1, n + 1))


def pesos_aplicados(row: dict, n: int, compensar: bool) -> list[float]:
    """Pesos % usados no R$ da semana. Compensador ligado: mês fecha em 100%."""
    man = [_f(row, f"peso_sem_man_{i}") for i in range(1, n + 1)]
    sug = [_f(row, f"peso_sem_sug_{i}") for i in range(1, n + 1)]
    hab = [_f(row, f"peso_sem_hab_{i}") for i in range(1, n + 1)]
    locked = [m > 0 for m in man]
    efs = [man[i] if locked[i] else sug[i] for i in range(n)]
    if not compensar:
        if not any(locked):
            return list(hab)
        return efs
    if not any(locked):
        tot = sum(efs) or 1.0
        return [e / tot * 100.0 for e in efs]
    lock_sum = sum(efs[i] for i in range(n) if locked[i])
    rest = 100.0 - lock_sum
    free_idx = [i for i in range(n) if not locked[i]]
    free_sum = sum(efs[i] for i in free_idx)
    out = [0.0] * n
    for i in range(n):
        if locked[i]:
            out[i] = efs[i]
        elif free_sum > 0 and rest > 0:
            out[i] = efs[i] / free_sum * rest
        else:
            out[i] = 0.0
    return out


def sincronizar_meta_pelo_ritmo(rows: list[dict], n: int, compensar: bool) -> list[dict]:
    """Compensador desligado + peso manual: a soma das semanas vira a meta do mês."""
    if compensar:
        return rows
    out = []
    for r in rows:
        x = dict(r)
        if not tem_peso_manual(x, n):
            out.append(x)
            continue
        efs = pesos_aplicados(x, n, compensar=False)
        meta = meta_final_row(x)
        nova = round(sum(meta * e / 100.0 for e in efs), 0)
        if nova > 0 and abs(nova - meta) >= 1:
            x["meta_manual"] = nova
        out.append(x)
    return out


def limpar_pesos_semana(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        x = dict(r)
        for i in range(1, MAX_SEM + 1):
            x[f"peso_sem_man_{i}"] = 0.0
        out.append(x)
    return out


def rows_to_semana_df(rows: list[dict], ano: int, mes: int, compensar: bool = True) -> pd.DataFrame:
    n = len(semanas_mes(ano, mes))
    data = []
    for r in rows:
        vid = int(r["vendedor"])
        meta = meta_final_row(r)
        rec = {
            "vid": vid,
            "colab": f"{vid:03d} · {str(r['nome'])[:44]}",
            "meta_mes": round(meta, 0) or None,
            "origem": r.get("ritmo_origem") or "",
            "info": r.get("ritmo_info") or "",
        }
        for i in range(1, MAX_SEM + 1):
            if i > n:
                rec[f"h{i}"] = None
                rec[f"p{i}"] = None
                rec[f"s{i}"] = None
                rec[f"m{i}"] = None
                rec[f"v{i}"] = None
                continue
            rec[f"h{i}"] = round(_f(r, f"fat_sem_hist_{i}"), 0) or None
            rec[f"p{i}"] = round(_f(r, f"peso_sem_hab_{i}"), 1) or None
            rec[f"s{i}"] = round(_f(r, f"peso_sem_sug_{i}"), 1) or None
            rec[f"m{i}"] = round(_f(r, f"peso_sem_man_{i}"), 1) or None
        apl = pesos_aplicados(r, n, compensar)
        for i in range(1, n + 1):
            ef = apl[i - 1]
            rec[f"v{i}"] = round(meta * ef / 100.0, 0) if meta > 0 and ef > 0 else None
        rec["soma"] = round(sum(apl), 1)
        data.append(rec)
    return pd.DataFrame(data)


def rows_to_dia_df(rows: list[dict], ano: int, mes: int, compensar: bool = True) -> pd.DataFrame:
    semanas = semanas_mes(ano, mes)
    n = len(semanas)
    data = []
    for r in rows:
        vid = int(r["vendedor"])
        meta = meta_final_row(r)
        rec = {
            "vid": vid,
            "colab": f"{vid:03d} · {str(r['nome'])[:44]}",
            "meta_mes": round(meta, 0) or None,
        }
        apl = pesos_aplicados(r, n, compensar)
        for i, (a, b) in enumerate(semanas, start=1):
            du = max(business_days_between(a, b), 0)
            ef = apl[i - 1]
            msem = meta * ef / 100.0 if meta > 0 and ef > 0 else 0.0
            rec[f"du{i}"] = du or None
            rec[f"ms{i}"] = round(msem, 0) or None
            rec[f"dia{i}"] = round(msem / du, 0) if du > 0 and msem > 0 else None
        for i in range(n + 1, MAX_SEM + 1):
            rec[f"du{i}"] = None
            rec[f"ms{i}"] = None
            rec[f"dia{i}"] = None
        data.append(rec)
    return pd.DataFrame(data)


def patch_pesos_from_aggrid(rows: list[dict], agdf: pd.DataFrame | None) -> list[dict]:
    if agdf is None or agdf.empty or "vid" not in agdf.columns:
        return rows
    edited = agdf[agdf["colab"].astype(str).str.upper() != "TOTAL"]
    by_vid = {}
    for _, r in edited.iterrows():
        if pd.isna(r.get("vid")):
            continue
        by_vid[int(r["vid"])] = r
    out = []
    for prev in rows:
        x = dict(prev)
        row = by_vid.get(int(prev["vendedor"]))
        if row is not None:
            for i in range(1, MAX_SEM + 1):
                x[f"peso_sem_man_{i}"] = _f(row, f"m{i}")
        out.append(x)
    return out


def total_ritmo_row(df: pd.DataFrame) -> dict:
    """Linha TOTAL: soma R$ (meta do mês, médias, metas da semana/dia)."""
    rec: dict = {"vid": None, "colab": "TOTAL", "origem": "", "info": ""}
    money = {"meta_mes"}
    money.update({f"h{i}" for i in range(1, MAX_SEM + 1)})
    money.update({f"v{i}" for i in range(1, MAX_SEM + 1)})
    money.update({f"ms{i}" for i in range(1, MAX_SEM + 1)})
    money.update({f"dia{i}" for i in range(1, MAX_SEM + 1)})
    ints = {f"du{i}" for i in range(1, MAX_SEM + 1)}
    skip = {"vid", "colab", "origem", "info", "soma"}
    skip.update({f"p{i}" for i in range(1, MAX_SEM + 1)})
    skip.update({f"s{i}" for i in range(1, MAX_SEM + 1)})
    skip.update({f"m{i}" for i in range(1, MAX_SEM + 1)})
    if df is None or df.empty:
        return rec
    body = df[df["colab"].astype(str).str.upper() != "TOTAL"]
    for col in body.columns:
        if col in skip:
            continue
        if col in money or col in ints:
            s = pd.to_numeric(body[col], errors="coerce").sum()
            rec[col] = round(float(s), 0) if s and not pd.isna(s) else None
        else:
            rec[col] = None
    rec["colab"] = "TOTAL"
    rec["soma"] = None
    return rec


def semana_labels(ano: int, mes: int) -> list[str]:
    from datetime import date as _date

    labs = []
    for i, (a, b) in enumerate(semanas_mes(ano, mes), start=1):
        fim = _date.fromordinal(b.toordinal() - 1)
        labs.append(f"S{i} {a:%d}–{fim:%d}")
    return labs
