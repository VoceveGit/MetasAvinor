from __future__ import annotations

import re

import streamlit as st

from app.formatting import fmt_brl_cell


def format_br_number(value: float | int, decimals: int = 0) -> str:
    v = float(value)
    if decimals <= 0:
        s = f"{int(round(v)):,}"
    else:
        s = f"{v:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def parse_br_number(text: str, decimals: int = 0) -> float:
    if text is None:
        return 0.0
    s = str(text).strip()
    if not s:
        return 0.0
    s = re.sub(r"[R$r\s]", "", s, flags=re.IGNORECASE)
    if not s:
        return 0.0

    if decimals <= 0:
        digits = re.sub(r"\D", "", s)
        return float(digits) if digits else 0.0

    if "," in s:
        s = s.replace(".", "").replace(",", ".")
        return float(s) if s else 0.0

    if s.count(".") > 1:
        s = s.replace(".", "")
        return float(s) if s else 0.0

    if s.count(".") == 1:
        left, right = s.split(".", 1)
        if len(right) == 3 and left.isdigit() and right.isdigit():
            return float(left + right)
        return float(s)

    return float(s)


def _apply_format(key: str, decimals: int) -> None:
    raw_s = str(st.session_state.get(key, "") or "")
    if decimals <= 0:
        digits = re.sub(r"\D", "", raw_s)
        st.session_state[key] = format_br_number(int(digits), 0) if digits else ""
        return
    try:
        val = parse_br_number(raw_s, decimals)
    except ValueError:
        return
    if val or "," in raw_s or "." in raw_s:
        st.session_state[key] = format_br_number(val, decimals)


_MASK_JS = """
<script>
(function () {
  const sel = '.st-key-__KEY__ input';
  const fmt = (d) => d.replace(/^0+(?=\\d)/, '').replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.');
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  function bind(tries) {
    const el = document.querySelector(sel);
    if (!el) { if (tries > 0) setTimeout(() => bind(tries - 1), 200); return; }
    if (el.dataset.brlMask) return;
    el.dataset.brlMask = '1';
    el.setAttribute('inputmode', 'numeric');
    el.addEventListener('input', () => {
      const pos = el.selectionStart || 0;
      const digitsLeft = el.value.slice(0, pos).replace(/\\D/g, '').length;
      const out = fmt(el.value.replace(/\\D/g, ''));
      if (out === el.value) return;
      setter.call(el, out);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      let p = 0, seen = 0;
      while (p < out.length && seen < digitsLeft) { if (/\\d/.test(out[p])) seen++; p++; }
      el.setSelectionRange(p, p);
    });
  }
  bind(25);
})();
</script>
"""


def _mask_live(container_key: str) -> None:
    """Formata 200.000.000 enquanto digita (o valor salvo continua vindo do Python)."""
    st.html(_MASK_JS.replace("__KEY__", container_key), unsafe_allow_javascript=True)


def brl_text_input(
    label: str,
    value: float,
    key: str,
    decimals: int = 0,
    help_text: str | None = None,
) -> float:
    """
    Formata ao sair do campo (Tab/Enter/clique fora). Inteiros: só dígitos → 20.000.000.
    """
    init_key = f"{key}__init"
    if init_key not in st.session_state:
        st.session_state[key] = format_br_number(value, decimals) if value else ""
        st.session_state[init_key] = value

    if st.session_state.get(init_key) != value:
        st.session_state[key] = format_br_number(value, decimals) if value else ""
        st.session_state[init_key] = value

    help_txt = help_text or (
        "Digite os números; ao sair do campo formata (ex.: 20.000.000)."
        if decimals <= 0
        else "Use vírgula para centavos (ex.: 1.924,46). Ao sair do campo, formata."
    )

    def _on_blur() -> None:
        _apply_format(key, decimals)

    with st.container(key=f"brlmask_{key}"):
        st.text_input(label, key=key, help=help_txt, on_change=_on_blur)
    if decimals <= 0:
        _mask_live(f"brlmask_{key}")

    raw = st.session_state.get(key, "")
    try:
        parsed = parse_br_number(str(raw), decimals)
    except ValueError:
        parsed = float(st.session_state.get(init_key) or 0)

    if parsed > 0:
        st.caption(f"Valor: **{fmt_brl_cell(parsed)}**")
    return parsed


def count_text_input(
    label: str,
    value: int | float,
    key: str,
    help_text: str | None = None,
) -> int:
    """Contagem (oportunidades, clientes) — formata milhar, sem R$."""
    init_key = f"{key}__init"
    if init_key not in st.session_state:
        st.session_state[key] = format_br_number(value, 0) if value else ""
        st.session_state[init_key] = int(value)

    if st.session_state.get(init_key) != int(value):
        st.session_state[key] = format_br_number(value, 0) if value else ""
        st.session_state[init_key] = int(value)

    help_txt = help_text or "Quantidade inteira. Deixe 0 para usar o valor automático (rotas/estimativa)."

    def _on_blur() -> None:
        _apply_format(key, 0)

    st.text_input(label, key=key, help=help_txt, on_change=_on_blur)

    raw = st.session_state.get(key, "")
    try:
        parsed = int(parse_br_number(str(raw), 0))
    except ValueError:
        parsed = int(st.session_state.get(init_key) or 0)

    if parsed > 0:
        st.caption(f"Quantidade: **{format_br_number(parsed, 0)}**")
    return max(0, parsed)


def int_br_text_input(
    label: str,
    value: int | float,
    key: str,
    help_text: str | None = None,
) -> int:
    return count_text_input(label, value, key, help_text=help_text)
