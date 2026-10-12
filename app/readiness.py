from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.constants import label_mes
from app.dates_util import month_bounds
from app.db import read_sql
from app.data import load_faturamento_por_familia
from app.premissas import count_premissas_vendedor_mes, get_premissa_empresa
from app.rotas_oportunidades import build_oportunidades_por_vendedor, rotas_file_info


@dataclass(frozen=True)
class ReadinessCheck:
    id: str
    status: str  # ok | warn | fail | na
    titulo: str
    passo_planilha: str
    fonte_avinor: str
    para_que_serve: str
    situacao: str
    se_faltar: str


def _meses_fechados_antes(ano: int, mes: int, qtd: int = 3) -> list[tuple[int, int]]:
    y, m = ano, mes
    out: list[tuple[int, int]] = []
    for _ in range(qtd):
        m -= 1
        if m < 1:
            m = 12
            y -= 1
        out.append((y, m))
    return out


def avaliar_preparacao_mes(ano: int, mes: int) -> list[ReadinessCheck]:
    checks: list[ReadinessCheck] = []
    ref = label_mes(ano, mes)

    # 1 — BASE_VENDAS / faturamento 3m
    meses_hist = _meses_fechados_antes(ano, mes, 3)
    meses_com_venda: list[str] = []
    fat_total_3m = 0.0
    for y, m in meses_hist:
        ini, fim = month_bounds(y, m)
        row = read_sql(
            """
            SELECT COALESCE(SUM(valor_total_faturado), 0) AS fat
            FROM faturamento_avinor
            WHERE data >= %s AND data < %s AND valor_total_faturado > 0
            """,
            (ini.isoformat(), fim.isoformat()),
        ).iloc[0]
        fat = float(row["fat"])
        if fat > 0:
            meses_com_venda.append(label_mes(y, m))
            fat_total_3m += fat
    if len(meses_com_venda) >= 3:
        st_txt = "ok"
        sit = (
            f"Encontramos faturamento nos 3 meses anteriores a {ref}: "
            + ", ".join(meses_com_venda)
            + f". Total ~R$ {fat_total_3m:,.0f}."
        )
        falta = ""
    elif meses_com_venda:
        st_txt = "warn"
        sit = f"Só achamos vendas em: {', '.join(meses_com_venda)}."
        falta = (
            "Ticket, recorrência e cobertura média ficam fracos ou zerados para quem "
            "não teve histórico completo — a meta sugerida pode sair errada."
        )
    else:
        st_txt = "fail"
        sit = "Não há faturamento nos 3 meses anteriores ao mês de referência."
        falta = (
            "Sem isso o painel não calcula bem ticket/recorrência/cobertura histórica "
            "(passo 1 e 7 da planilha COMECE AQUI)."
        )
    checks.append(
        ReadinessCheck(
            id="hist_3m",
            status=st_txt,
            titulo="Histórico de vendas (3 meses)",
            passo_planilha="COMECE AQUI · passo 1 — BASE_VENDAS",
            fonte_avinor="MySQL · tabela `faturamento_avinor` (automático)",
            para_que_serve="Alimenta ticket médio, recorrência e cobertura média de cada vendedor.",
            situacao=sit,
            se_faltar=falta,
        )
    )

    # 2 — Carteira
    cart = int(
        read_sql(
            """
            SELECT COUNT(*) AS c FROM base_clientes_avinor
            WHERE `Situação` = 'Ativo' AND `Vendedor` > 0
            """
        ).iloc[0]["c"]
    )
    checks.append(
        ReadinessCheck(
            id="carteira",
            status="ok" if cart > 0 else "fail",
            titulo="Carteira de clientes ativos",
            passo_planilha="COMECE AQUI · passo 8 — carteira no PAINEL",
            fonte_avinor="MySQL · `base_clientes_avinor` (automático)",
            para_que_serve="Define quantos clientes entram na meta de cobertura.",
            situacao=f"{cart:,} clientes ativos com vendedor.".replace(",", "."),
            se_faltar="Meta de cobertura e diferença carteira×cobertura não fazem sentido.",
        )
    )

    # 3 — Mês de referência com vendas
    ini, fim = month_bounds(ano, mes)
    row_mes = read_sql(
        """
        SELECT
            COALESCE(SUM(valor_total_faturado), 0) AS fat,
            COUNT(DISTINCT vendedor) AS vends
        FROM faturamento_avinor
        WHERE data >= %s AND data < %s AND valor_total_faturado > 0 AND vendedor > 0
        """,
        (ini.isoformat(), fim.isoformat()),
    ).iloc[0]
    fat_mes = float(row_mes["fat"])
    vends_mes = int(row_mes["vends"])
    checks.append(
        ReadinessCheck(
            id="realizado_mes",
            status="ok" if fat_mes > 0 else "warn",
            titulo=f"Faturamento realizado em {ref}",
            passo_planilha="PAINEL · coluna realizado / acompanhamento do mês",
            fonte_avinor="MySQL · `faturamento_avinor` no período do mês",
            para_que_serve="Compara meta × realizado e ranking do período.",
            situacao=(
                f"R$ {fat_mes:,.0f} com {vends_mes} vendedores com venda."
                if fat_mes > 0
                else f"Ainda sem vendas lançadas em {ref}."
            ).replace(",", "."),
            se_faltar="Panorama e ranking do mês ficam vazios ou incompletos.",
        )
    )

    # 4 — ROTAS / oportunidades
    info = rotas_file_info()
    sem_rota = 0
    mapeados = 0
    if info["presente"]:
        try:
            oport_df = build_oportunidades_por_vendedor()
            sem_rota = int(oport_df["clientes_sem_rota"].sum())
            mapeados = int(oport_df["clientes_mapeados"].sum())
        except Exception:
            sem_rota = -1
        atualizado = info["atualizado_em"]
        dt = (
            atualizado.strftime("%d/%m/%Y %H:%M")
            if isinstance(atualizado, datetime)
            else "—"
        )
        if sem_rota < 0:
            st_r = "fail"
            sit = f"Arquivo em {info['caminho']}, mas não foi possível ler as abas."
        elif sem_rota == 0:
            st_r = "ok"
            sit = (
                f"Planilha carregada (atualizada em {dt}). "
                f"{mapeados} clientes mapeados por cidade/bairro."
            )
        elif sem_rota <= max(5, mapeados * 0.05):
            st_r = "warn"
            sit = (
                f"Planilha de {dt}. {mapeados} mapeados, {sem_rota} sem rota "
                "(usam estimativa 1,04 contato/semana)."
            )
        else:
            st_r = "warn"
            sit = (
                f"Planilha de {dt}. {sem_rota} clientes sem rota — "
                f"oportunidades podem ficar imprecisas."
            )
        falta_r = (
            "Oportunidades e positivação meta ficam estimadas; conversão e meta em R$ perdem precisão."
            if sem_rota > 0
            else ""
        )
    else:
        st_r = "fail"
        sit = "Nenhum arquivo ROTAS AVINOR.xlsx na pasta data/ ou raiz do projeto."
        falta_r = (
            "Equivalente ao passo 8 (oportunidades) — sem rotas usamos estimativa genérica "
            "ou valor manual por vendedor na seção 2 (aba Início)."
        )
    checks.append(
        ReadinessCheck(
            id="rotas",
            status=st_r,
            titulo="Rotas comerciais (oportunidades/mês)",
            passo_planilha="COMECE AQUI · passo 8 — oportunidades (dias CRM)",
            fonte_avinor="Arquivo **ROTAS AVINOR.xlsx** (upload mensal) × carteira",
            para_que_serve="Conta quantos contatos CRM cada cliente tem no mês (× 4 semanas).",
            situacao=sit,
            se_faltar=falta_r,
        )
    )

    # 5 — Premissas empresa
    emp = get_premissa_empresa(ano, mes)
    if emp.meta_empresa_rs > 0:
        st_emp = "ok"
        sit_emp = f"Meta empresa R$ {emp.meta_empresa_rs:,.0f} salva para {ref}.".replace(
            ",", "."
        )
        falta_emp = ""
    else:
        st_emp = "warn"
        sit_emp = f"Meta empresa ainda não salva para {ref}."
        falta_emp = "Linha FALTA/SOBRA e teto do mês não fecham."
    checks.append(
        ReadinessCheck(
            id="premissas_empresa",
            status=st_emp,
            titulo="Meta da empresa (premissa do mês)",
            passo_planilha="COMECE AQUI · passo 9 — meta total no PAINEL",
            fonte_avinor="Salvar na seção **1 · Configurar o mês** (aba Início)",
            para_que_serve="Comparar soma das metas dos vendedores com a meta da empresa.",
            situacao=sit_emp,
            se_faltar=falta_emp,
        )
    )

    # 6 — Premissas vendedores
    ini_p, fim_p = month_bounds(ano, mes)
    ranking_p = read_sql(
        """
        SELECT COUNT(DISTINCT vendedor) AS v
        FROM faturamento_avinor
        WHERE data >= %s AND data < %s AND valor_total_faturado > 0 AND vendedor > 0
        """,
        (ini_p.isoformat(), fim_p.isoformat()),
    ).iloc[0]
    vends_mes = int(ranking_p["v"]) or 0
    n_prem = count_premissas_vendedor_mes(ano, mes)
    if vends_mes > 0 and n_prem >= vends_mes:
        st_v = "ok"
        sit_v = f"Todos os {vends_mes} vendedores com venda em {ref} têm premissa salva."
        falta_v = ""
    elif n_prem > 0:
        st_v = "warn"
        sit_v = f"{n_prem} de {vends_mes} vendedores com premissa salva."
        falta_v = "Quem falta usa só cálculo automático até você salvar (botão no checklist)."
    else:
        st_v = "warn"
        sit_v = "Nenhuma premissa por vendedor salva ainda."
        falta_v = "Metas oficiais por pessoa não ficam gravadas; use lote (seção 1) ou salve na seção 2."
    checks.append(
        ReadinessCheck(
            id="premissas_vendedores",
            status=st_v,
            titulo="Premissas por vendedor (conversão, ticket, cobertura)",
            passo_planilha="COMECE AQUI · passo 10 — PAINEL por colaborador",
            fonte_avinor="Lote na seção 1 ou ajuste na **seção 2** (aba Início)",
            para_que_serve="Trava as alavancas do motor de meta de cada colaborador.",
            situacao=sit_v,
            se_faltar=falta_v,
        )
    )

    # 7 — Dados por família/produto
    fam_df = load_faturamento_por_familia(ini_p, fim_p, None)
    if not fam_df.empty and float(fam_df["faturamento"].sum()) > 0:
        n_fam = len(fam_df)
        st_prod = "ok"
        sit_prod = (
            f"{n_fam} famílias com venda em {ref} — veja aba **Produtos & linhas**."
        )
        falta_prod = ""
    else:
        st_prod = "warn"
        sit_prod = f"Sem itens de produto no faturamento de {ref}."
        falta_prod = "Análise por linha de produto fica vazia."
    checks.append(
        ReadinessCheck(
            id="produtos_familia",
            status=st_prod,
            titulo="Vendas por família / produto (ERP)",
            passo_planilha="Analítico (equivalente ao mix nas abas BOI/SUINO na Frigosol)",
            fonte_avinor="`faturamento_avinor` · campos `familia`, `produto`, `descricao`",
            para_que_serve="Ver mix e ranking de itens; não substitui meta por vendedor.",
            situacao=sit_prod,
            se_faltar=falta_prod,
        )
    )

    # 8 — Distribuição semanal (não implementado)
    checks.append(
        ReadinessCheck(
            id="distribuicao",
            status="na",
            titulo="Distribuição de força por semana",
            passo_planilha="COMECE AQUI · passo 6 — aba DISTRIBUIÇÃO",
            fonte_avinor="Ainda **não** no painel Avinor",
            para_que_serve="Na planilha Frigosol: espalha meta ao longo das semanas do mês.",
            situacao="Não coletamos isso hoje — use a planilha se precisar desse recorte.",
            se_faltar="Não afeta meta total do mês; só o acompanhamento semana a semana.",
        )
    )

    # 9 — PAINÉIS separados Frigosol (não se aplica)
    checks.append(
        ReadinessCheck(
            id="linhas_frigosol",
            status="na",
            titulo="PAINÉIS Frigosol separados (BOI / SUINO / CONFRIGO)",
            passo_planilha="COMECE AQUI · várias abas e empresas na mesma planilha",
            fonte_avinor="Avinor unificada — use **Produtos & linhas** para mix por família",
            para_que_serve="Na Frigosol cada unidade tinha planilha própria; aqui é uma operação.",
            situacao="Não é pendência: é diferença de modelo de negócio.",
            se_faltar="",
        )
    )

    return checks
