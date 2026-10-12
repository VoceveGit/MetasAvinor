"""Mapa didático: colunas da planilha Mari ↔ painel Avinor."""

import streamlit as st

from app.ui import panel_box


def render_mapa_planilha_mari() -> None:
    with st.expander("Mapa rápido: planilha PAINEL ↔ este painel", expanded=False):
        st.markdown(
            """
| Planilha (PAINEL) | No painel | Tipo |
|-------------------|-----------|------|
| Carteira | Carteira | Automático (base clientes) |
| Oportunidades | Oportunidades | Automático (ROTAS × carteira) |
| TX Conv. Oport. | TX conv. oport. | Positivação média ÷ Oportunidades |
| **Conversão** | **Conversão** | **Manual** (fallback se faltar cob×rec) |
| Oport. Calculada | Oport. calc. | **Cobertura × Recorrência** (itens por cliente na carteira) |
| Cobertura média | Cobertura média | Média 3m clientes com venda |
| **TX Conversão Projetada** | **TX conv. projetada** | **Manual** (ex. 90%) |
| Cobertura | Cobertura | Carteira × TX projetada |
| Diferença Carteira × Cobertura | Dif. cart. × cob. | Carteira − Cobertura |
| TX Conversão (média) | TX conv. (média) | Cobertura média ÷ Carteira |
| Faturamento (média) | Fat. média | Média 3m faturamento |
| Positivação (média) | Positivação média | Média 3m itens vendidos (carteira ativa) |
| Ticket Histórico | Ticket histórico | Fat. média ÷ Positivação média |
| **Ticket Médio** | **Ticket médio** | **Manual** |
| Recorrência média | Recorrência média | Positivação média ÷ Cobertura média |
| **Recorrência** | **Recorrência** | **Manual** |
| Meta | Meta calc. | Ticket médio × Recorrência × Cobertura |
| Meta em R$ (travada) | Meta manual (R$) | **Opcional** — alvo que você quer impor |
| — | Realizado (mês) | Faturamento do mês até agora (ERP) |
            """
        )
