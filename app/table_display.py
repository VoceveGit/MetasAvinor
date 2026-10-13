from __future__ import annotations

from typing import Any, Literal

import pandas as pd
import streamlit as st

from app.brl_input import parse_br_number
from app.formatting import fmt_brl_table, fmt_int_table, fmt_pct_table

ColKind = Literal[
    "text",
    "money",
    "money_edit",
    "pct",
    "pct_edit",
    "int",
    "int_edit",
    "float",
    "code",
]


def format_dataframe_columns(df: pd.DataFrame, spec: dict[str, ColKind]) -> pd.DataFrame:
    """Aplica formatação PT-BR nas colunas indicadas (valores numéricos de entrada)."""
    out = df.copy()
    for col, kind in spec.items():
        if col not in out.columns:
            continue
        if kind == "money":
            out[col] = out[col].apply(fmt_brl_table)
        elif kind == "money_edit":
            out[col] = out[col].apply(
                lambda v: fmt_brl_table(v)
                if v is not None and not (isinstance(v, float) and pd.isna(v)) and float(v) > 0
                else ""
            )
        elif kind == "pct":
            out[col] = out[col].apply(fmt_pct_table)
        elif kind == "pct_edit":
            out[col] = out[col].apply(
                lambda v: fmt_pct_table(v)
                if v is not None and not (isinstance(v, float) and pd.isna(v)) and float(v) > 0
                else ""
            )
        elif kind == "int":
            out[col] = out[col].apply(fmt_int_table)
        elif kind == "int_edit":
            out[col] = out[col].apply(
                lambda v: fmt_int_table(v)
                if v is not None and not (isinstance(v, float) and pd.isna(v)) and float(v) > 0
                else ""
            )
        elif kind == "float":
            out[col] = out[col].apply(lambda v: f"{float(v):.2f}" if v is not None and not pd.isna(v) else "—")
        elif kind == "code":
            def _fmt_code(v: Any) -> str:
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return ""
                s = str(v).strip()
                if not s or s in ("—", "-", "None", "nan"):
                    return s if s == "—" else ""
                try:
                    return str(int(float(s)))
                except (TypeError, ValueError):
                    return s

            out[col] = out[col].apply(_fmt_code)
    return out


def parse_pct_cell(value: Any) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, min(100.0, float(value)))
    s = str(value).strip().replace("%", "").replace(",", ".")
    if not s or s in ("—", "None", "nan"):
        return 0.0
    try:
        return max(0.0, min(100.0, float(s)))
    except ValueError:
        return 0.0


def parse_int_cell(value: Any) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0, int(round(float(value))))
    s = str(value).strip()
    if not s or s in ("—", "None", "nan"):
        return 0
    digits = "".join(c for c in s if c.isdigit())
    return int(digits) if digits else 0


def format_edit_cell(value: Any, kind: ColKind) -> str:
    """Formata célula editável após digitar (ex.: 1200 → R$ 1.200)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    if not s or s in ("—", "None", "nan"):
        return ""
    if kind == "money_edit":
        n = parse_money_cell(value)
        return fmt_brl_table(n) if n > 0 else s
    if kind == "pct_edit":
        n = parse_pct_cell(value)
        return fmt_pct_table(n) if n > 0 else s
    if kind == "int_edit":
        n = parse_int_cell(value)
        return fmt_int_table(n) if n > 0 else s
    return s


def normalize_editable_columns(
    df: pd.DataFrame,
    spec: dict[str, ColKind],
    editable_cols: list[str],
) -> pd.DataFrame:
    out = df.copy()
    for col in editable_cols:
        if col not in out.columns:
            continue
        kind = spec.get(col, "text")
        if kind not in ("money_edit", "pct_edit", "int_edit"):
            continue
        for i in range(len(out)):
            loc = out.columns.get_loc(col)
            out.iat[i, loc] = format_edit_cell(out.iat[i, loc], kind)
    return out


def fill_column_down(df: pd.DataFrame, column: str, start_row_index: int) -> pd.DataFrame:
    """Repete o valor da linha `start_row_index` nas linhas abaixo (estilo arrastar no Excel)."""
    if column not in df.columns or start_row_index < 0 or start_row_index >= len(df):
        return df
    out = df.copy()
    val = out.iloc[start_row_index][column]
    loc = out.columns.get_loc(column)
    for r in range(start_row_index + 1, len(out)):
        out.iat[r, loc] = val
    return out


def _session_state_to_dataframe(state: Any) -> pd.DataFrame | None:
    if state is None:
        return None
    if isinstance(state, pd.DataFrame):
        return state.copy()
    if isinstance(state, dict):
        if "data" in state:
            return pd.DataFrame(state["data"])
        try:
            return pd.DataFrame(state)
        except (ValueError, TypeError):
            return None
    return None


def parse_money_cell(value: Any) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, float(value))
    s = str(value).strip()
    if not s or s in ("—", "None", "nan"):
        return 0.0
    return max(0.0, parse_br_number(s, 0))


_TOTAL_CSS = "background-color:#dfece4;color:#12261d;font-weight:700"


def show_data_table(
    df: pd.DataFrame,
    spec: dict[str, ColKind] | None = None,
    helps: dict[str, str] | None = None,
    total: list[str] | None = None,
    styles: dict[str, Any] | None = None,
    progress: list[str] | None = None,
    **kwargs: Any,
) -> None:
    """st.dataframe com padrão Avinor (R$ 1.234.567, sem abreviar mi/mil).

    `helps`: explicação por coluna — o título ganha um ⓘ e o texto aparece ao passar o mouse.
    `total`: colunas somadas numa linha TOTAL no fim (1ª coluna recebe o rótulo).
    `styles`: {coluna: f(valor numérico) -> css} para pintar números.
    `progress`: colunas de % mostradas como barra (0–100).
    """
    raw = df.reset_index(drop=True)
    progress = [c for c in (progress or []) if c in raw.columns]
    if total and not raw.empty:
        row: dict[str, Any] = {c: None for c in raw.columns}
        for c in total:
            if c in raw.columns:
                row[c] = pd.to_numeric(raw[c], errors="coerce").sum()
        row[raw.columns[0]] = "TOTAL"
        raw[raw.columns[0]] = raw[raw.columns[0]].astype(str)
        raw = pd.concat([raw, pd.DataFrame([row])], ignore_index=True)
    fmt_spec = {k: v for k, v in (spec or {}).items() if k not in progress}
    display = format_dataframe_columns(raw, fmt_spec) if fmt_spec else raw.copy()
    if total and not raw.empty:
        for c in display.columns:
            if c not in total and c != display.columns[0] and c not in progress:
                display.iat[len(display) - 1, display.columns.get_loc(c)] = ""

    cfg: dict[str, Any] = {}
    for col in display.columns:
        txt = (helps or {}).get(col)
        label = f"{col} ⓘ" if txt else col
        if col in progress:
            cfg[col] = st.column_config.ProgressColumn(
                label, help=txt, format="%.1f%%", min_value=0.0,
                max_value=float(max(1.0, pd.to_numeric(raw[col], errors="coerce").max() or 1.0)),
            )
        elif txt:
            cfg[col] = st.column_config.Column(label=label, help=txt)
    if cfg:
        kwargs.setdefault("column_config", cfg)

    out: Any = display
    if styles or (total and not raw.empty):
        n_total = len(raw) - 1 if total and not raw.empty else None

        def _css(_: pd.DataFrame) -> pd.DataFrame:
            m = pd.DataFrame("", index=display.index, columns=display.columns)
            for col, fn in (styles or {}).items():
                if col not in raw.columns:
                    continue
                for i, v in enumerate(raw[col]):
                    if i == n_total or v is None or (isinstance(v, float) and pd.isna(v)):
                        continue
                    m.iat[i, m.columns.get_loc(col)] = fn(float(v)) or ""
            if n_total is not None:
                m.iloc[n_total] = _TOTAL_CSS
            return m

        out = display.style.apply(_css, axis=None)
    st.dataframe(
        out,
        hide_index=True,
        use_container_width=True,
        **kwargs,
    )


def css_sinal(v: float, neutro: float = 0.0) -> str:
    """Vermelho abaixo de `neutro`, verde acima."""
    if v < neutro:
        return "color:#b42318;font-weight:700"
    if v > neutro:
        return "color:#1f7a4d;font-weight:700"
    return ""


def money_editor_column_config(
    df: pd.DataFrame,
    spec: dict[str, ColKind],
    editable_money_col: str | None = None,
) -> dict[str, st.column_config.Column]:
    """data_editor: dinheiro como texto formatado; uma coluna editável opcional."""
    formatted = format_dataframe_columns(df, spec)
    cfg: dict[str, st.column_config.Column] = {}
    for col in formatted.columns:
        kind = spec.get(col, "text")
        if col == editable_money_col:
            cfg[col] = st.column_config.TextColumn(
                help="Ex.: 1.200.000 — vazio = meta automática.",
            )
        elif kind in ("money", "money_edit", "pct", "int"):
            cfg[col] = st.column_config.TextColumn(disabled=True)
        elif kind in ("text", "code"):
            cfg[col] = st.column_config.TextColumn(disabled=True)
        else:
            cfg[col] = st.column_config.NumberColumn(disabled=True)
    return cfg, formatted


def render_grid_data_editor(
    df: pd.DataFrame,
    spec: dict[str, ColKind],
    editable_cols: list[str],
    editor_key: str,
    height: int | None = None,
) -> pd.DataFrame:
    """Várias colunas editáveis; formata R$/ % ao sair da célula (rerun do editor)."""
    base = format_dataframe_columns(df, spec)
    persisted = _session_state_to_dataframe(st.session_state.get(editor_key))
    if persisted is not None and len(persisted) == len(base):
        working = persisted
        for col in base.columns:
            if col not in working.columns:
                working[col] = base[col]
    else:
        working = base

    working = normalize_editable_columns(working, spec, editable_cols)

    _help = {
        "money_edit": "Digite o valor; ao mudar de célula formata em R$ (ex.: 1200000 → R$ 1.200.000).",
        "pct_edit": "Digite só o número; formata em % (ex.: 90 → 90,0%).",
        "int_edit": "Número inteiro (oportunidades).",
    }
    cfg: dict[str, st.column_config.Column] = {}
    for col in working.columns:
        if col in editable_cols:
            kind = spec.get(col, "text")
            cfg[col] = st.column_config.TextColumn(help=_help.get(kind, "Célula editável — gestor"))
        else:
            kind = spec.get(col, "text")
            if kind in ("money", "money_edit", "pct", "pct_edit", "int", "int_edit", "float", "code"):
                cfg[col] = st.column_config.TextColumn(disabled=True)
            elif kind == "text":
                cfg[col] = st.column_config.TextColumn(disabled=True)
            else:
                cfg[col] = st.column_config.NumberColumn(disabled=True)

    edited = st.data_editor(
        working,
        column_config=cfg,
        hide_index=True,
        use_container_width=True,
        height=height,
        key=editor_key,
    )
    return normalize_editable_columns(edited, spec, editable_cols)


def render_money_data_editor(
    df: pd.DataFrame,
    spec: dict[str, ColKind],
    editable_money_col: str,
    editor_key: str,
    height: int | None = None,
) -> pd.DataFrame:
    """Editor com colunas monetárias já formatadas; retorna o dataframe editado (texto)."""
    cfg, formatted = money_editor_column_config(df, spec, editable_money_col)
    return st.data_editor(
        formatted,
        column_config=cfg,
        hide_index=True,
        use_container_width=True,
        height=height,
        key=editor_key,
    )
