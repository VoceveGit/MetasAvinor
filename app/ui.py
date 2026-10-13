import html

import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');

:root {
    --avinor-bg: #f5f7f6;
    --avinor-fg: #2f3d38;
    --avinor-muted: #6b7a73;
    --avinor-border: #e2e8e5;
    --avinor-card: #ffffff;
    --avinor-primary: #3d6b5c;
    --avinor-sidebar: #2a3632;
    --avinor-sidebar-fg: #f3f6f4;
    --avinor-sidebar-muted: #9aaba3;
    --avinor-sidebar-active: #3d524c;
    --avinor-lime: #d4f574;
    --avinor-nav-bg: #12261d;
    --avinor-nav-active: #22382d;
    --avinor-nav-muted: #b4c2ba;
}

html, body, [class*="css"] {
    font-family: 'Manrope', sans-serif;
    font-size: 14px;
}

.stApp {
    background: var(--avinor-bg);
    color: var(--avinor-fg);
}

.main .block-container {
    max-width: 1480px;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* Esconde sidebar — controles no topo e na Visão geral */
section[data-testid="stSidebar"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    display: none !important;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.avinor-toolbar-anchor) {
    background: var(--avinor-card) !important;
    border: 1px solid var(--avinor-border) !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 5px rgba(32, 48, 40, 0.04) !important;
    padding: 0.65rem 1rem !important;
    margin-bottom: 1rem !important;
}

.st-key-avinor_nav_filtros button {
    background: transparent !important;
    color: #d9e4de !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    border-radius: 10px !important;
}
.st-key-avinor_nav_filtros button:hover { background: rgba(255, 255, 255, 0.08) !important; }
div[data-baseweb="popover"] { z-index: 1000000 !important; }

/* —— Menu superior fixo (container com key="avinor_nav") —— */
[data-testid="stMainBlockContainer"],
.main .block-container {
    padding-top: 6.25rem !important;
}
.st-key-avinor_nav {
    position: fixed !important;
    top: 0;
    left: 0;
    right: 0;
    z-index: 999990;
    height: 76px;
    padding: 0 32px !important;
    box-sizing: border-box;
    background: var(--avinor-nav-bg) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
    flex-wrap: nowrap !important;
    overflow-x: auto;
    gap: 6px !important;
}
.st-key-avinor_nav [data-testid="stElementContainer"] {
    width: auto !important;
}
.avinor-brand-lockup {
    display: flex;
    align-items: center;
    gap: 12px;
    white-space: nowrap;
    margin-right: 22px;
}
.avinor-brand-mark {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: var(--avinor-lime);
    color: var(--avinor-nav-bg);
    display: grid;
    place-items: center;
    flex-shrink: 0;
}
.st-key-avinor_nav .avinor-brand-title {
    font-size: 26px !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    color: #ffffff !important;
    margin: 0 !important;
    line-height: 1 !important;
}
.avinor-brand-title .brand-dot {
    color: var(--avinor-lime);
}
.st-key-avinor_nav button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    min-height: 44px !important;
    color: var(--avinor-nav-muted) !important;
    white-space: nowrap !important;
    transition: background 0.15s ease, color 0.15s ease;
}
.st-key-avinor_nav button p {
    font-size: 15px !important;
    font-weight: 500 !important;
    color: inherit !important;
}
.st-key-avinor_nav button [data-testid="stIconMaterial"] {
    font-size: 20px !important;
    color: inherit !important;
}
.st-key-avinor_nav button:hover {
    background: rgba(255, 255, 255, 0.06) !important;
    color: #ffffff !important;
}
.st-key-avinor_nav button[data-testid="stBaseButton-primary"] {
    background: var(--avinor-nav-active) !important;
    color: #ffffff !important;
}
.st-key-avinor_nav button[data-testid="stBaseButton-primary"] [data-testid="stIconMaterial"] {
    color: var(--avinor-lime) !important;
}
.st-key-avinor_nav button:focus,
.st-key-avinor_nav button:focus-visible {
    outline: none !important;
    box-shadow: none !important;
}
.avinor-nav-actions {
    display: flex;
    align-items: center;
    gap: 18px;
    color: var(--avinor-nav-muted);
    white-space: nowrap;
}
.avinor-nav-actions .icon-btn {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    color: var(--avinor-nav-muted);
}
.avinor-nav-actions .icon-btn:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #ffffff;
}
.avinor-nav-actions .divider {
    width: 1px;
    height: 28px;
    background: rgba(255, 255, 255, 0.12);
}
.avinor-nav-actions .avatar {
    width: 38px;
    height: 38px;
    border-radius: 999px;
    background: #e3efe6;
    color: var(--avinor-nav-bg);
    display: grid;
    place-items: center;
    font-size: 13px;
    font-weight: 800;
}
@media (max-width: 1180px) {
    .st-key-avinor_nav {
        padding: 0 16px !important;
    }
    .avinor-brand-lockup {
        margin-right: 6px;
    }
    .st-key-avinor_nav button {
        padding: 8px 10px !important;
    }
    .st-key-avinor_nav button p {
        font-size: 14px !important;
    }
    .avinor-nav-actions {
        gap: 8px;
    }
    .avinor-nav-actions .divider {
        display: none;
    }
}
@media (max-width: 960px) {
    .st-key-avinor_nav button p {
        display: none !important;
    }
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.vg-filter-anchor) {
    background: #fff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 14px !important;
    box-shadow: 0 1px 3px rgba(15, 51, 40, 0.06) !important;
    padding: 0.75rem 1rem 0.85rem !important;
    margin-bottom: 1rem !important;
}
/* Sidebar — laranja pastel */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #fde8d4 0%, #f9dcc4 50%, #f5d0b5 100%) !important;
    border-right: 1px solid #e8c4a8;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] .stMarkdown {
    color: #5c3d2e !important;
}
section[data-testid="stSidebar"] .stCaption {
    color: #7a5544 !important;
}

/* Selects legíveis na sidebar */
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] input {
    background-color: #fffaf3 !important;
    color: #3d2817 !important;
    border: 1px solid #e0b896 !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] span,
section[data-testid="stSidebar"] [data-baseweb="select"] div[role="listbox"] {
    color: #3d2817 !important;
}

section[data-testid="stSidebar"] .stRadio label {
    color: #5c3d2e !important;
}

.hero-title {
    font-size: 1.9rem;
    font-weight: 700;
    color: #3d2817;
    letter-spacing: -0.03em;
    margin: 0 0 0.2rem 0;
}
.hero-sub {
    color: #7a6555;
    font-size: 0.95rem;
    margin-bottom: 1rem;
}

.metric-card {
    background: #fffdf8;
    border: 1px solid #ebe3d5;
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow: 0 2px 16px rgba(92, 61, 46, 0.06);
    height: 100%;
}
.metric-card.accent {
    border-color: #e8a55c;
    background: linear-gradient(135deg, #fff9f0 0%, #fff3e0 100%);
}
.metric-card .label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #9a8474;
    margin-bottom: 0.35rem;
}
.metric-card .value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #3d2817;
    line-height: 1.2;
}
.metric-card .value.highlight {
    color: #c45c26;
}
.metric-card .compare {
    font-size: 0.82rem;
    margin-top: 0.45rem;
    color: #57534e;
    font-weight: 500;
}
.metric-card .compare strong {
    color: #3d2817;
    font-weight: 700;
}
.metric-card .delta {
    font-size: 0.78rem;
    margin-top: 0.25rem;
    font-weight: 600;
}
.delta-up { color: #15803d; }
.delta-down { color: #b91c1c; }
.delta-neutral { color: #78716c; }

.panel-card {
    background: #fffdf8;
    border-radius: 16px;
    padding: 1.1rem 1.25rem;
    border: 1px solid #ebe3d5;
    box-shadow: 0 4px 20px rgba(92, 61, 46, 0.05);
    margin-bottom: 0.85rem;
}
.panel-card h3 {
    font-size: 1.05rem;
    font-weight: 700;
    color: #3d2817;
    margin: 0 0 0.35rem 0;
}
.panel-card .hint {
    font-size: 0.85rem;
    color: #7a6555;
    line-height: 1.45;
}

.panel-card.param {
    border-color: #e8a55c;
    background: linear-gradient(135deg, #fffaf3 0%, #fff3e6 100%);
}
.panel-card.readonly {
    border-color: #d6d3d1;
    background: #fafaf9;
}

.section-head {
    margin: 0.75rem 0 0.5rem 0;
}
.section-head h2 {
    font-size: 1.25rem;
    font-weight: 700;
    color: #3d2817;
    margin: 0;
}
.section-head p {
    font-size: 0.88rem;
    color: #7a6555;
    margin: 0.15rem 0 0 0;
}

.badge-hit {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    background: #dcfce7;
    color: #166534;
}
.badge-miss {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    background: #fee2e2;
    color: #991b1b;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    background-color: #fff3e0 !important;
    color: #9a3412 !important;
    border-bottom: 2px solid #2f6b55 !important;
}
div[data-testid="stTabs"] button {
    color: #7a6555 !important;
    font-weight: 600;
}
</style>
"""


def inject_styles():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def metric_card(
    label: str,
    value: str,
    delta: str = "",
    delta_kind: str = "neutral",
    accent: bool = False,
    highlight_value: bool = False,
    compare_label: str = "",
    compare_value: str = "",
):
    cls = {"up": "delta-up", "down": "delta-down", "neutral": "delta-neutral"}.get(
        delta_kind, "delta-neutral"
    )
    compare_html = ""
    if compare_label and compare_value:
        compare_html = (
            f'<div class="compare">{compare_label}: <strong>{compare_value}</strong></div>'
        )
    delta_html = f'<div class="delta {cls}">{delta}</div>' if delta else ""
    card_cls = "metric-card accent" if accent else "metric-card"
    val_cls = "value highlight" if highlight_value else "value"
    st.markdown(
        f"""
        <div class="{card_cls}">
            <div class="label">{label}</div>
            <div class="{val_cls}">{value}</div>
            {compare_html}
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def panel_box(title: str, hint: str, variant: str = "default"):
    extra = ""
    if variant == "param":
        extra = " param"
    elif variant == "readonly":
        extra = " readonly"
    st.markdown(
        f"""
        <div class="panel-card{extra}">
            <h3>{title}</h3>
            <div class="hint">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


NAV_ITEMS = (
    ("Início", ":material/home:"),
    ("Visão geral", ":material/grid_view:"),
    ("Produtos & linhas", ":material/inventory_2:"),
    ("Colaboradores", ":material/group:"),
    ("Progresso", ":material/trophy:"),
)
NAV_LABELS = tuple(label for label, _ in NAV_ITEMS)

_BRAND_ICON_SVG = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/>'
    '<circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/></svg>'
)
_HELP_ICON_SVG = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/>'
    '<path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.3"/><circle cx="12" cy="17" r=".6" '
    'fill="currentColor"/></svg>'
)
_BELL_ICON_SVG = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>'
)


def _set_nav_page(label: str) -> None:
    st.session_state["main_nav_page"] = label


def render_fixed_nav(app_version: str, app_root: str | None = None) -> str:
    """Barra superior fixa: marca, abas com ícone e ações à direita."""
    page = st.session_state.get("main_nav_page", NAV_LABELS[0])
    if page not in NAV_LABELS:
        page = NAV_LABELS[0]
        st.session_state["main_nav_page"] = page

    tip = f"Metas Avinor · v{app_version}"
    if app_root:
        tip += f" · {app_root}"

    with st.container(
        key="avinor_nav",
        horizontal=True,
        vertical_alignment="center",
        wrap=False,
    ):
        st.markdown(
            f"""
            <div class="avinor-brand-lockup" title="{html.escape(tip)}">
              <div class="avinor-brand-mark">{_BRAND_ICON_SVG}</div>
              <p class="avinor-brand-title">meta<span class="brand-dot">.</span></p>
            </div>
            """,
            unsafe_allow_html=True,
            width="content",
        )
        for i, (label, icon) in enumerate(NAV_ITEMS):
            st.button(
                label,
                key=f"avinor_nav_btn_{i}",
                icon=icon,
                type="primary" if label == page else "tertiary",
                on_click=_set_nav_page,
                args=(label,),
            )
        st.space("stretch")
        with st.popover("Filtros", icon=":material/filter_alt:", key="avinor_nav_filtros"):
            st.caption("Filtros de leitura do ERP (valem para todas as telas).")
            st.toggle("Só vendas positivas", value=True, key="top_apenas_pos")
            st.toggle("Esconder sem vendedor", value=True, key="top_sem_vend")
        st.markdown(
            f"""
            <div class="avinor-nav-actions">
              <span class="icon-btn" title="Ajuda">{_HELP_ICON_SVG}</span>
              <span class="icon-btn" title="Notificações">{_BELL_ICON_SVG}</span>
              <span class="divider"></span>
              <span class="avatar">CS</span>
            </div>
            """,
            unsafe_allow_html=True,
            width="content",
        )
    return page


def render_top_toolbar() -> dict[str, bool]:
    """Filtros do ERP: os toggles ficam no popover do menu (render_fixed_nav)."""
    return {
        "apenas_positivos": bool(st.session_state.get("top_apenas_pos", True)),
        "excluir_sem_vendedor": bool(st.session_state.get("top_sem_vend", True)),
    }


def section_header(title: str, subtitle: str = ""):
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="section-head"><h2>{title}</h2>{sub}</div>',
        unsafe_allow_html=True,
    )
