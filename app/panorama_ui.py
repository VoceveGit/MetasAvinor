from __future__ import annotations

import pandas as pd
import streamlit as st

from app.data import load_historico_meta_vendedor
from app.formatting import fmt_brl_cell, fmt_pct
from app.table_style import style_meta_table


def _bar_text(pct: float) -> str:
    p = min(max(float(pct), 0), 100)
    filled = int(round(p / 10))
    return "█" * filled + "░" * (10 - filled) + f" {p:.0f}%"


def _fmt_pct_rate(v: float | None) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{float(v):.0f}%"


def _fmt_tx_conv(v: float | None) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{float(v):.0f}%"


def _fmt_rec(v: float | None) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{float(v):.2f}"


def _build_panorama_table(pano: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for r in pano.itertuples(index=False):
        bateu = bool(r.bateu)
        rows.append(
            {
                "Colaborador": r.nome,
                "Carteira": int(r.carteira),
                "Oport. mês": int(r.oportunidades),
                "TX conv.": _fmt_tx_conv(getattr(r, "tx_conv_oport", None)),
                "Cob. média": _fmt_pct_rate(getattr(r, "cob_media_pct", None)),
                "Clientes mês": int(r.cobertura_qtd),
                "Dif. carteira": int(r.diff_carteira_cob),
                "Recorrência": _fmt_rec(getattr(r, "recorrencia", None)),
                "Meta sugerida": fmt_brl_cell(r.meta_sugerida),
                "Realizado": fmt_brl_cell(r.realizado),
                "Atingimento": fmt_pct(r.atingimento),
                "Progresso": _bar_text(r.atingimento),
                "Status": "Bateu" if bateu else "Não bateu",
                "_bateu": bateu,
                "_sub": False,
                "_vid": int(r.vendedor),
                "_meta": float(r.meta_sugerida),
                "_real": float(r.realizado),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    tot_meta = float(df["_meta"].sum())
    tot_real = float(df["_real"].sum())
    ating_tot = (tot_real / tot_meta * 100) if tot_meta > 0 else 0
    tot_row = {
        "Colaborador": "TOTAL EQUIPE",
        "Carteira": int(df["Carteira"].sum()),
        "Oport. mês": int(df["Oport. mês"].sum()),
        "TX conv.": "—",
        "Cob. média": "—",
        "Clientes mês": int(pano["clientes"].sum()),
        "Dif. carteira": int(df["Dif. carteira"].sum()),
        "Recorrência": "—",
        "Meta sugerida": fmt_brl_cell(tot_meta),
        "Realizado": fmt_brl_cell(tot_real),
        "Atingimento": fmt_pct(ating_tot),
        "Progresso": _bar_text(ating_tot),
        "Status": "—",
        "_bateu": tot_real >= tot_meta if tot_meta > 0 else False,
        "_sub": False,
        "_vid": -1,
        "_meta": tot_meta,
        "_real": tot_real,
    }
    return pd.concat([df, pd.DataFrame([tot_row])], ignore_index=True)


def _hist_to_table(hist: pd.DataFrame, carteira: int, vid: int) -> pd.DataFrame:
    rows: list[dict] = []
    for _, d in hist.iterrows():
        cob_pct = (float(d["clientes"]) / carteira * 100) if carteira > 0 else 0
        rec = float(d["notas"]) / float(d["clientes"]) if d["clientes"] else 0
        bateu = bool(d["bateu"])
        rows.append(
            {
                "Colaborador": f"  ↳ {d['periodo']}",
                "Carteira": "—",
                "Oport. mês": "—",
                "TX conv.": "—",
                "Cob. média": _fmt_pct_rate(cob_pct),
                "Clientes mês": int(d["clientes"]),
                "Dif. carteira": "—",
                "Recorrência": _fmt_rec(rec),
                "Meta sugerida": fmt_brl_cell(d["meta_sugerida"]),
                "Realizado": fmt_brl_cell(d["faturamento"]),
                "Atingimento": fmt_pct(d["atingimento"]),
                "Progresso": _bar_text(d["atingimento"]),
                "Status": "Bateu" if bateu else "Não bateu",
                "_bateu": bateu,
                "_sub": True,
                "_vid": vid,
            }
        )
    return pd.DataFrame(rows)


@st.fragment
def _panorama_historico_block(
    pano: pd.DataFrame,
    ano: int,
    mes: int,
    taxa: float,
) -> None:
    opcoes = ["— Nenhum —"] + [
        f"{int(r.vendedor)} — {r.nome}" for r in pano.itertuples()
    ]
    escolha = st.selectbox(
        "Histórico mensal do colaborador",
        opcoes,
        key=f"pan_hist_sel_{ano}_{mes}",
        help="Abre as últimas linhas de meta × realizado sem recarregar a página inteira.",
    )
    if escolha == "— Nenhum —":
        return
    vid = int(escolha.split(" — ")[0])
    row = pano.loc[pano["vendedor"] == vid].iloc[0]
    hist = load_historico_meta_vendedor(vid, ano, mes, taxa)
    hist_df = _hist_to_table(hist, int(row["carteira"]), vid)
    if hist_df.empty:
        st.info("Sem histórico para este colaborador.")
        return
    st.caption(f"Histórico de **{row['nome']}** (carteira {int(row['carteira'])} clientes).")
    styled = style_meta_table(hist_df)
    st.dataframe(styled, use_container_width=True, hide_index=True, height=280)


def render_panorama_equipe(
    pano: pd.DataFrame,
    ano: int,
    mes: int,
    taxa: float,
) -> None:
    table = _build_panorama_table(pano)
    if table.empty:
        return

    tot_meta = float(table.iloc[-1]["_meta"])
    tot_real = float(table.iloc[-1]["_real"])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Meta sugerida (equipe)", fmt_brl_cell(tot_meta))
    m2.metric("Realizado (equipe)", fmt_brl_cell(tot_real))
    m3.metric("Colaboradores no ranking", len(pano))
    m4.metric(
        "Atingimento médio (R$)",
        fmt_pct((tot_real / tot_meta * 100) if tot_meta > 0 else 0),
    )

    styled = style_meta_table(table)
    row_count = len(table)
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=min(560, 42 + row_count * 35),
    )
    st.caption(
        "Role a tabela: o cabeçalho permanece fixo. "
        "A linha **TOTAL EQUIPE** mostra a base dos percentuais de atingimento."
    )
    _panorama_historico_block(pano, ano, mes, taxa)
