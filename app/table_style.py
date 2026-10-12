from __future__ import annotations

import pandas as pd

COL_ATINGIMENTO = "Atingimento"
COL_PROGRESSO = "Progresso"
COL_STATUS = "Status"
COL_COLABORADOR = "Colaborador"


def style_meta_table(
    df: pd.DataFrame,
    col_bateu: str = "_bateu",
    col_sub: str = "_sub",
):
    flags = df[col_bateu].tolist()
    subs = (
        df[col_sub].tolist()
        if col_sub in df.columns
        else [False] * len(df)
    )
    hidden = [c for c in df.columns if c.startswith("_")]
    display = df.drop(
        columns=[col_bateu, col_sub, "_vid", "_parent", *hidden],
        errors="ignore",
    )

    def row_style(row):
        bateu = flags[row.name]
        is_sub = subs[row.name]
        styles = []
        for col in display.columns:
            if col == COL_PROGRESSO:
                if is_sub:
                    bg = "#ecfdf5" if bateu else "#fff1f2"
                    fg = "#4ade80" if bateu else "#f87171"
                    styles.append(
                        f"background-color: {bg}; color: {fg}; font-weight: 600; "
                        f"font-family: 'DM Sans', monospace; font-size: 0.9em;"
                    )
                else:
                    bg = "#dcfce7" if bateu else "#fee2e2"
                    fg = "#15803d" if bateu else "#b91c1c"
                    styles.append(
                        f"background-color: {bg}; color: {fg}; font-weight: 600; "
                        f"font-family: 'DM Sans', monospace;"
                    )
            elif col == COL_ATINGIMENTO:
                fg = (
                    ("#16a34a" if bateu else "#dc2626")
                    if is_sub
                    else ("#15803d" if bateu else "#b91c1c")
                )
                styles.append(f"color: {fg}; font-weight: 700;")
            elif col == COL_STATUS:
                fg = (
                    ("#16a34a" if bateu else "#dc2626")
                    if is_sub
                    else ("#15803d" if bateu else "#b91c1c")
                )
                styles.append(f"color: {fg}; font-weight: 600;")
            elif col == COL_COLABORADOR and is_sub:
                styles.append(
                    "color: #7a6555; font-style: italic; padding-left: 0.75rem;"
                )
            elif col == COL_COLABORADOR and str(row.get(COL_COLABORADOR, "")).startswith(
                "TOTAL"
            ):
                styles.append("font-weight: 800; color: #3d2817;")
            else:
                styles.append("")
        return styles

    return display.style.apply(row_style, axis=1)
