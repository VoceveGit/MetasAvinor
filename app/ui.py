import html

import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: linear-gradient(165deg, #faf6ee 0%, #f5efe3 45%, #f0e9dc 100%);
}

.main .block-container {
    padding-top: 5.75rem;
    max-width: 1280px;
}

/* Esconde sidebar — controles no topo e na Visão geral */
section[data-testid="stSidebar"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    display: none !important;
}

.top-toolbar {
    background: #fffdf8;
    border: 1px solid #ebe3d5;
    border-radius: 12px;
    padding: 0.65rem 1rem 0.75rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 2px 12px rgba(92, 61, 46, 0.05);
}

/* Menu fixo no topo — só o bloco do menu (scroll continua em section.main) */
[data-testid="stVerticalBlockBorderWrapper"]:has(.avinor-nav-anchor),
.avinor-nav-fixed {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 1001 !important;
    background: #faf6ee !important;
    border: none !important;
    border-bottom: 2px solid #e8dfd0 !important;
    box-shadow: 0 4px 14px -6px rgba(92, 61, 46, 0.28) !important;
    padding: 0.45rem 1rem 0.6rem !important;
    margin: 0 !important;
    box-sizing: border-box !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.avinor-nav-anchor) > [data-testid="stVerticalBlock"] {
    max-width: 1280px;
    margin: 0 auto;
}
.avinor-brand-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #3d2817;
    margin: 0;
    line-height: 1.2;
}
.avinor-brand-title span {
    font-size: 0.78rem;
    font-weight: 600;
    color: #c45c26;
}
div[data-testid="stRadio"] > label {
    display: none !important;
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
    border-bottom: 2px solid #ea580c !important;
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


NAV_LABELS = (
    "Início",
    "Visão geral",
    "Produtos & linhas",
    "Colaboradores",
    "Ranking",
)


def render_fixed_nav(app_version: str, app_root: str | None = None) -> str:
    """Menu principal sempre visível no topo, com versão ao lado do título."""
    labels = list(NAV_LABELS)
    with st.container(border=True):
        st.markdown('<div class="avinor-nav-anchor"></div>', unsafe_allow_html=True)
        brand, menu = st.columns([1.15, 4.85], gap="small")
        with brand:
            root_tip = (
                f' title="Código: {html.escape(app_root)}"' if app_root else ""
            )
            st.markdown(
                f'<p class="avinor-brand-title">Metas Avinor<br>'
                f'<span{root_tip}>v{app_version}</span></p>',
                unsafe_allow_html=True,
            )
        with menu:
            prev = st.session_state.get("main_nav_page", labels[0])
            if prev in labels and "main_nav_radio" not in st.session_state:
                st.session_state["main_nav_radio"] = prev
            page = st.radio(
                "Menu principal",
                labels,
                horizontal=True,
                label_visibility="collapsed",
                key="main_nav_radio",
            )
    st.session_state["main_nav_page"] = page
    _pin_nav_bar_only()
    return page


def _pin_nav_bar_only() -> None:
    """Fixa só a barra do menu; não mexe no overflow da página."""
    import streamlit.components.v1 as components

    components.html(
        """
        <script>
        (function () {
            const doc = window.parent.document;
            function apply() {
                const anchor = doc.querySelector(".avinor-nav-anchor");
                if (!anchor) return;
                let wrap = anchor.closest('[data-testid="stVerticalBlockBorderWrapper"]');
                if (!wrap) {
                    let node = anchor.parentElement;
                    for (let i = 0; i < 10 && node; i++) {
                        if (
                            node.querySelector('[data-testid="stHorizontalBlock"]') &&
                            node.querySelector(".avinor-brand-title")
                        ) {
                            const h = node.offsetHeight;
                            if (h > 0 && h < 220) {
                                wrap = node;
                                break;
                            }
                        }
                        node = node.parentElement;
                    }
                }
                if (!wrap) return;
                wrap.classList.add("avinor-nav-fixed");
                wrap.style.setProperty("position", "fixed", "important");
                wrap.style.setProperty("top", "0", "important");
                wrap.style.setProperty("left", "0", "important");
                wrap.style.setProperty("right", "0", "important");
                wrap.style.setProperty("z-index", "1001", "important");
                wrap.style.setProperty("background", "#faf6ee", "important");
                const bc = doc.querySelector("section.main .block-container");
                if (bc) {
                    const h = wrap.getBoundingClientRect().height || 76;
                    bc.style.setProperty("padding-top", (h + 14) + "px", "important");
                }
            }
            apply();
            setTimeout(apply, 100);
            setTimeout(apply, 500);
            window.parent.addEventListener("resize", apply, { passive: true });
        })();
        </script>
        """,
        height=0,
    )


def render_top_toolbar() -> dict[str, bool]:
    st.markdown('<div class="top-toolbar">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.markdown(
            '<span style="color:#7a6555;">Filtros de leitura do ERP</span>',
            unsafe_allow_html=True,
        )
    with c2:
        apenas_pos = st.toggle("Só vendas positivas", value=True, key="top_apenas_pos")
    with c3:
        excluir_zero = st.toggle("Esconder sem vendedor", value=True, key="top_sem_vend")
    st.markdown("</div>", unsafe_allow_html=True)
    return {"apenas_positivos": apenas_pos, "excluir_sem_vendedor": excluir_zero}


def section_header(title: str, subtitle: str = ""):
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="section-head"><h2>{title}</h2>{sub}</div>',
        unsafe_allow_html=True,
    )
