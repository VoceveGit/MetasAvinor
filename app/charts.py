import pandas as pd
import plotly.graph_objects as go

PRIMARY = "#ea580c"
GHOST = "rgba(180, 140, 100, 0.35)"
GHOST_LINE = "rgba(160, 120, 90, 0.25)"
ACCENT = "#16a34a"
NEG = "#dc2626"
GRID = "rgba(120, 90, 60, 0.12)"


def _empty_month_frame() -> pd.DataFrame:
    return pd.DataFrame({"mes": list(range(1, 13))})


def prepare_year_series(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    base = _empty_month_frame()
    slice_df = df[df["ano"] == ano][["mes", "faturamento"]].copy()
    merged = base.merge(slice_df, on="mes", how="left")
    merged["faturamento"] = merged["faturamento"].fillna(0)
    labels = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    }
    merged["mes_label"] = merged["mes"].map(labels)
    return merged


def chart_year_compare(df: pd.DataFrame, ano_focus: int, ano_ghost: int | None, modo: str) -> go.Figure:
    focus = prepare_year_series(df, ano_focus)
    fig = go.Figure()

    if ano_ghost and ano_ghost != ano_focus and modo != "Só ano em foco":
        ghost = prepare_year_series(df, ano_ghost)
        if modo == "Fantasma atrás (overlay)":
            fig.add_trace(
                go.Bar(
                    x=ghost["mes_label"],
                    y=ghost["faturamento"],
                    name=str(ano_ghost),
                    marker=dict(color=GHOST),
                    width=0.55,
                )
            )
            fig.add_trace(
                go.Bar(
                    x=focus["mes_label"],
                    y=focus["faturamento"],
                    name=str(ano_focus),
                    marker=dict(color=PRIMARY),
                    width=0.38,
                )
            )
            fig.update_layout(barmode="overlay")
        else:
            fig.add_trace(go.Bar(x=ghost["mes_label"], y=ghost["faturamento"], name=str(ano_ghost), marker_color=GHOST_LINE))
            fig.add_trace(go.Bar(x=focus["mes_label"], y=focus["faturamento"], name=str(ano_focus), marker_color=PRIMARY))
            fig.update_layout(barmode="group", bargap=0.15)
    else:
        fig.add_trace(
            go.Bar(
                x=focus["mes_label"],
                y=focus["faturamento"],
                marker=dict(color=focus["faturamento"], colorscale=[[0, "#fde4c8"], [1, PRIMARY]]),
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=400,
        margin=dict(l=16, r=16, t=40, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
        font=dict(family="DM Sans, sans-serif", color="#5c4a3a"),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=GRID, tickprefix="R$ ", tickformat=",.0f"),
    )
    return fig


def chart_delta_meses(df: pd.DataFrame, ano_a: int, ano_b: int) -> go.Figure:
    a = prepare_year_series(df, ano_a).set_index("mes")["faturamento"]
    b = prepare_year_series(df, ano_b).set_index("mes")["faturamento"]
    delta = b - a
    labels = prepare_year_series(df, ano_a)["mes_label"]
    colors = [ACCENT if v >= 0 else NEG for v in delta]
    fig = go.Figure(go.Bar(x=labels, y=delta, marker_color=colors))
    fig.update_layout(
        template="plotly_white",
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor=GRID, tickprefix="R$ "),
        title=dict(
            text=f"Diferença por mês ({ano_b} menos {ano_a})",
            font=dict(size=13, color="#6b5b4d"),
        ),
        font=dict(family="DM Sans, sans-serif"),
    )
    fig.add_hline(y=0, line_color="rgba(100,80,60,0.35)")
    return fig


def chart_historico_meses(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["periodo"],
            y=df["faturamento"],
            name="Faturamento",
            marker_color=PRIMARY,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["periodo"],
            y=df["clientes"],
            name="Clientes",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color="#b45309", width=2),
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="R$", tickprefix="R$ "),
        yaxis2=dict(title="Clientes", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.12),
        font=dict(family="DM Sans, sans-serif"),
    )
    return fig


def chart_familia_pizza(df: pd.DataFrame, titulo: str = "Faturamento por família") -> go.Figure:
    if df.empty:
        return go.Figure()
    top = df.head(12).copy()
    outros = float(df["faturamento"].iloc[12:].sum()) if len(df) > 12 else 0
    if outros > 0:
        top = pd.concat(
            [top, pd.DataFrame([{"familia": "Outros", "faturamento": outros}])],
            ignore_index=True,
        )
    fig = go.Figure(
        go.Pie(
            labels=top["familia"],
            values=top["faturamento"],
            hole=0.45,
            textinfo="percent+label",
            textposition="outside",
            marker=dict(line=dict(color="#fff", width=1)),
        )
    )
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=14, color="#5c4a3a")),
        height=420,
        margin=dict(l=16, r=16, t=48, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif"),
        showlegend=False,
    )
    return fig


def chart_top_familias_barras(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    d = df.head(15).iloc[::-1]
    fig = go.Figure(
        go.Bar(
            x=d["faturamento"],
            y=d["familia"],
            orientation="h",
            text=d["pct"].map(lambda x: f"{x:.1f}%"),
            textposition="outside",
            marker_color=PRIMARY,
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=max(320, len(d) * 28),
        margin=dict(l=8, r=56, t=16, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickprefix="R$ ", gridcolor=GRID),
        font=dict(family="DM Sans, sans-serif"),
    )
    return fig


def chart_ranking_realizado_meta(df: pd.DataFrame) -> go.Figure:
    """Barras agrupadas: realizado vs meta (modo mês)."""
    if df.empty or "meta" not in df.columns:
        return go.Figure()
    d = df.head(12).iloc[::-1]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=d["nome"],
            x=d["faturamento"],
            name="Realizado",
            orientation="h",
            marker_color=PRIMARY,
        )
    )
    fig.add_trace(
        go.Bar(
            y=d["nome"],
            x=d["meta"],
            name="Meta",
            orientation="h",
            marker_color="rgba(22, 163, 74, 0.65)",
        )
    )
    fig.update_layout(
        template="plotly_white",
        barmode="group",
        height=max(300, len(d) * 40),
        margin=dict(l=8, r=48, t=16, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickprefix="R$ ", gridcolor=GRID),
        yaxis=dict(autorange="reversed"),
        legend=dict(orientation="h", y=1.06),
        font=dict(family="DM Sans, sans-serif"),
    )
    return fig


def chart_mapa_cidades_recorrencia(df: pd.DataFrame) -> go.Figure:
    """Mapa (OSM) com bolhas por cidade — cor = recorrência, tamanho = faturamento."""
    if df.empty or "lat" not in df.columns:
        return go.Figure()
    d = df.dropna(subset=["lat", "lon"]).copy()
    if d.empty:
        return go.Figure()
    d = d.sort_values("faturamento", ascending=False).head(60)
    max_fat = float(d["faturamento"].max()) or 1.0
    d["marker_size"] = (d["faturamento"] / max_fat * 36 + 8).clip(8, 44)
    center_lat = float(d["lat"].mean())
    center_lon = float(d["lon"].mean())
    fig = go.Figure(
        go.Scattermap(
            lat=d["lat"],
            lon=d["lon"],
            mode="markers",
            marker=dict(
                size=d["marker_size"],
                color=d["recorrencia"],
                colorscale=[[0, "#dbeafe"], [0.45, "#3b82f6"], [1, "#1e3a8a"]],
                cmin=float(d["recorrencia"].min()),
                cmax=float(d["recorrencia"].max()),
                colorbar=dict(title="Recorrência"),
                opacity=0.85,
            ),
            text=d.apply(
                lambda r: (
                    f"{r['cidade']} ({r['uf']})<br>"
                    f"Recorrência: {r['recorrencia']:.2f}<br>"
                    f"Clientes: {int(r['clientes'])} · Notas: {int(r['notas'])}"
                ),
                axis=1,
            ),
            hoverinfo="text",
        )
    )
    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=5.5,
        ),
        margin=dict(l=0, r=0, t=8, b=0),
        height=480,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color="#5c4a3a"),
    )
    return fig


def chart_top_vendedores(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    fig = go.Figure(
        go.Bar(
            x=df["faturamento"],
            y=df["nome"],
            orientation="h",
            text=df["pct_faturamento"].map(lambda x: f"{x:.1f}%"),
            textposition="outside",
            marker=dict(color=df["faturamento"], colorscale=[[0, "#fde4c8"], [1, PRIMARY]]),
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=max(280, len(df) * 34),
        margin=dict(l=8, r=48, t=16, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickprefix="R$ ", gridcolor=GRID),
        yaxis=dict(autorange="reversed"),
        font=dict(family="DM Sans, sans-serif"),
    )
    return fig
