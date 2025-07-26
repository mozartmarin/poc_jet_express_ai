# app.py
import os
import io
from datetime import datetime

import pandas as pd
# app.py
import streamlit as st
st.set_page_config(page_title="POC Expressa - E-commerce (IA opcional)", layout="wide")

# CSS - look & feel moderno
st.markdown("""
    <style>
    html, body, [class*="css"]  {
        font-family: 'Segoe UI', sans-serif;
        background-color: #0e1117;
        color: #FFFFFF;
    }

    h1, h2, h3 {
        color: #00CED1 !important;
    }

    .stApp {
        background-color: #0e1117;
    }

    .stMarkdown, .stDataFrame, .stExpander, .stMetric, .stSelectbox, .stTextInput {
        background-color: #1a1c22 !important;
        border-radius: 10px !important;
        color: #FFFFFF !important;
    }

    .stButton > button {
        background-color: #00CED1;
        color: black;
        font-weight: bold;
        border-radius: 6px;
    }

    .stSlider > div > div {
        background-color: #1a1c22;
    }

    ::-webkit-scrollbar {
        width: 6px;
    }

    ::-webkit-scrollbar-thumb {
        background-color: #00CED1;
        border-radius: 6px;
    }

    .stChatInputContainer, .stChatMessage {
        background-color: #1a1c22 !important;
        color: #ffffff !important;
        border-radius: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# agora sim:
st.title("POC Expressa de E-commerce — Modo IA Opcional")



# IA é opcional
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# ------------------------------------------------------------------
# Configuração
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# Sidebar – configurações
# ------------------------------------------------------------------
st.sidebar.header("⚙️ Configurações")
USE_IA = st.sidebar.toggle("Usar IA para explicar respostas", value=False)

OPENROUTER_API_KEY = (
    st.secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
    if USE_IA
    else ""
)
MODEL_NAME = st.sidebar.text_input(
    "Modelo (OpenRouter)", value="mistralai/mistral-7b-instruct", disabled=not USE_IA
)
MAX_NUMBERS_TO_SEND = st.sidebar.slider(
    "Quantos números no resumo enviado à IA", 20, 200, 60, disabled=not USE_IA
)

with st.sidebar.expander("❓ O que significam esses parâmetros?"):
    st.markdown(
        """
    **Usar IA para explicar respostas:** ativa uma explicação baseada em linguagem natural para os dados já calculados.

    **Modelo:** é o modelo que será consultado via OpenRouter (ex: mistral-7b).

    **Quantos números no resumo enviado à IA:** limita quantos valores numéricos serão enviados para a IA basear a explicação. Valores maiores aumentam contexto, mas também o custo e tempo.
    """
    )

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
@st.cache_data
def carregar_dados():
    try:
        clientes = pd.read_csv("data/clients.csv", encoding="utf-8")
        pedidos = pd.read_csv("data/orders.csv", encoding="utf-8")
        itens = pd.read_csv("data/items.csv", encoding="utf-8")
        produtos = pd.read_csv("data/products.csv", encoding="utf-8")
        return clientes, pedidos, itens, produtos, None
    except Exception as e:
        return None, None, None, None, str(e)


def build_client():
    if not USE_IA:
        return None, None
    if not OPENROUTER_API_KEY:
        return None, "API key não encontrada. Configure OPENROUTER_API_KEY em Secrets."
    if OpenAI is None:
        return None, "Pacote openai não instalado."
    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
        return client, None
    except Exception as e:
        return None, f"Erro criando cliente OpenRouter: {e}"


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


# ---------------- Cálculos determinísticos ----------------
def answer_ticket_medio(pedidos: pd.DataFrame):
    df = pedidos.copy()
    df = df[df["SituacaoPedido"].astype(str).str.lower().eq("faturado")]
    tm = df["TotalPedido"].apply(safe_float).mean()
    n = df.shape[0]
    soma = df["TotalPedido"].apply(safe_float).sum()
    return {
        "titulo": "Ticket médio (pedidos faturados)",
        "valor": tm,
        "detalhe": {
            "soma_total": soma,
            "num_pedidos_faturados": n,
        },
    }


def answer_desconto_medio(pedidos: pd.DataFrame):
    df = pedidos.copy()
    df = df[df["SituacaoPedido"].astype(str).str.lower().eq("faturado")]

    descontos = df["ValorDesconto"].apply(safe_float)
    media = descontos.mean()
    total = descontos.sum()

    return {
        "titulo": "Desconto médio (pedidos faturados)",
        "valor": media,
        "detalhe": {
            "soma_descontos": total,
            "num_pedidos_faturados": df.shape[0]
        },
    }



def top_produtos(itens: pd.DataFrame, produtos: pd.DataFrame, n=5):
    top = (
        itens.groupby("CodigoProdutoVendido")["QuantidadeVendidaItem"]
        .sum()
        .reset_index()
        .sort_values(by="QuantidadeVendidaItem", ascending=False)
        .head(n)
    )
    top = top.merge(
        produtos.drop_duplicates(subset="CodigoProduto"),
        left_on="CodigoProdutoVendido",
        right_on="CodigoProduto",
        how="left",
    )
    return top[["Produto", "QuantidadeVendidaItem"]]


def formas_pagamento(pedidos: pd.DataFrame):
    fp = pedidos["FormaPagamento"].value_counts().reset_index()
    fp.columns = ["Forma de Pagamento", "Total"]
    return fp


def status_pedidos(pedidos: pd.DataFrame):
    status = pedidos["SituacaoPedido"].value_counts().reset_index()
    status.columns = ["Situação", "Total"]
    return status


def tipo_cliente(pedidos: pd.DataFrame, clientes: pd.DataFrame):
    pedidos_clientes = pedidos.merge(
        clientes, left_on="CodigoClientePedido", right_on="CodigoCliente", how="left"
    )
    tipos = pedidos_clientes["TipoCliente"].value_counts().reset_index()
    tipos.columns = ["Tipo de Cliente", "Total de Pedidos"]
    return tipos


# ---------------- IA prompts/helpers ----------------
def default_system_prompt():
    return (
        "Você é um analista de dados sênior. Explique o raciocínio com clareza, "
        "cite as fórmulas usadas e a interpretação do resultado. Use apenas os números que eu te passar. "
        "Se algo não fizer sentido, diga explicitamente."
    )


def summarize_numbers_for_llm(d: dict, limit=60) -> str:
    flat = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple, set)):
            for v in x:
                walk(v)
        else:
            try:
                v = float(x)
                flat.append(v)
            except Exception:
                pass

    walk(d)
    return ", ".join(f"{v:.4f}" for v in flat[:limit])


def dataset_min_snapshot(clientes, pedidos, itens, produtos) -> dict:
    """Resumo curto com números úteis para fallback em perguntas não mapeadas."""
    out = {}
    try:
        if pedidos is not None and not pedidos.empty:
            ped_faturados = pedidos[pedidos["SituacaoPedido"].astype(str).str.lower().eq("faturado")]
            out.update(
                dict(
                    total_pedidos=int(pedidos.shape[0]),
                    total_pedidos_faturados=int(ped_faturados.shape[0]),
                    ticket_medio=pd.to_numeric(ped_faturados["TotalPedido"], errors="coerce").mean(),
                    desconto_medio=pd.to_numeric(ped_faturados["ValorDesconto"], errors="coerce").mean(),
                )
            )
    except Exception:
        pass
    try:
        if itens is not None and not itens.empty:
            top = (
                itens.groupby("CodigoProdutoVendido")["QuantidadeVendidaItem"].sum().sort_values(ascending=False).head(5)
            )
            out["top_qtd_itens"] = list(top.values)
    except Exception:
        pass
    return out


def ask_model_explain(client, model, question: str, result: dict, max_numbers=60, temperature=0.1):
    if not client:
        return None, "Cliente IA não disponível."
    try:
        numbers = summarize_numbers_for_llm(result, limit=max_numbers)
        content = (
            f"Pergunta do usuário: {question}\n"
            f"Números já calculados pelo backend (use apenas estes): {numbers}\n"
            f"Resultado estruturado (não envie de volta, apenas use para explicar): {result}"
        )
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": default_system_prompt()},
                {"role": "user", "content": content},
            ],
            temperature=temperature,
        )
        return completion.choices[0].message.content, None
    except Exception as e:
        return None, f"Erro ao chamar o modelo: {e}"



def ask_model_fallback(client, model, question: str, clientes, pedidos, itens, produtos, max_numbers=60):
    """Quando a pergunta não é mapeada, tenta responder SOMENTE com um snapshot pequeno do dataset."""
    if not client:
        return None, "Cliente IA não disponível."
    payload = dataset_min_snapshot(clientes, pedidos, itens, produtos)
    if not payload:
        return None, "Snapshot vazio – não há números para enviar."
    return ask_model_explain(client, model, question, payload, max_numbers=max_numbers)


# ---------------- Router ----------------
def route_question(pergunta: str, clientes, pedidos, itens, produtos):
    q = pergunta.lower()
    if "ticket" in q and ("médio" in q or "medio" in q):
        return "ticket_medio", answer_ticket_medio(pedidos)
    if "desconto" in q and "médio" in q:
        return "desconto_medio", answer_desconto_medio(pedidos)
    if "produtos mais vendidos" in q or "top produtos" in q:
        return "top_produtos", top_produtos(itens, produtos, n=5)
    if "forma de pagamento" in q or "formas de pagamento" in q:
        return "formas_pgto", formas_pagamento(pedidos)
    if "frete grátis" in q or "frete gratis" in q:
        total = pedidos[pedidos["FreteGratis"].astype(str).str.lower().isin(["sim", "s", "true", "1"])].shape[0]
        return "frete_gratis", {"total_frete_gratis": int(total)}
    if "status" in q:
        return "status_pedidos", status_pedidos(pedidos)
    if (
        "tipo de cliente" in q
        or "cliente físico" in q
        or "cliente juridico" in q
        or "jurídico" in q
    ):
        return "tipo_cliente", tipo_cliente(pedidos, clientes)
    return "nao_mapeado", {}


# ------------------------------------------------------------------
# Carregamento
# ------------------------------------------------------------------
clientes, pedidos, itens, produtos, erro = carregar_dados()
if erro:
    st.error(f"❌ Erro ao carregar CSVs: {erro}")
    st.stop()
else:
    st.success("✅ Dados carregados com sucesso!")

col1, col2, col3, col4 = st.columns(4)
try:
    total_pedidos = pedidos.shape[0]
    ticket_medio_df = pedidos[pedidos["SituacaoPedido"].astype(str).str.lower().eq("faturado")]["TotalPedido"].apply(safe_float).mean()
    frete_gratis_qtd = pedidos[pedidos["FreteGratis"].astype(str).str.lower().isin(["sim", "s", "true", "1"])].shape[0]
    pct_frete_gratis = (frete_gratis_qtd / total_pedidos) * 100 if total_pedidos > 0 else 0
    desconto_medio = pedidos[pedidos["SituacaoPedido"].astype(str).str.lower().eq("faturado")]["ValorDesconto"].apply(safe_float).mean()


    col1.metric("📦 Total de Pedidos", f"{total_pedidos:,}")
    col2.metric("💰 Ticket Médio", f"R$ {ticket_medio_df:,.2f}")
    col3.metric("🚚 Frete Grátis (%)", f"{pct_frete_gratis:.1f}%")
    col4.metric("🔻 Desconto Médio", f"R$ {desconto_medio:,.2f}")
except Exception as e:
    st.warning(f"⚠️ Não foi possível calcular os KPIs: {e}")

with st.expander("🔍 Ver amostras de dados carregados"):
    st.write("Clientes", clientes.head())
    st.write("Pedidos", pedidos.head())
    st.write("Itens", itens.head())
    st.write("Produtos", produtos.head())

# ------------------------------------------------------------------
# Chat
# ------------------------------------------------------------------
st.header("💬 Faça perguntas aos dados (IA opcional)")

client, client_err = build_client()
if client_err:
    st.sidebar.error(client_err)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

pergunta = st.chat_input("Pergunte algo como: 'Qual é o ticket médio por tipo de cliente?'")

if pergunta:
    st.session_state.messages.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    intent, result = route_question(pergunta, clientes, pedidos, itens, produtos)

    with st.chat_message("assistant"):
        is_result_empty = (
            result is None
            or (isinstance(result, dict) and not result)
            or (isinstance(result, pd.DataFrame) and result.empty)
        )

        if is_result_empty:
            if USE_IA:
                st.warning("⚠️ Pergunta não está mapeada para cálculo. Pesquisando com IA…")
                with st.spinner("Consultando modelo…"):
                    explicacao, err = ask_model_fallback(
                        client, MODEL_NAME, pergunta, clientes, pedidos, itens, produtos, max_numbers=MAX_NUMBERS_TO_SEND
                    )
                if err:
                    st.error(err)
                else:
                    st.markdown(explicacao)
            else:
                st.warning(
                    "⚠️ Pergunta não está mapeada para cálculo determinístico. "
                    "Ative a IA na barra lateral ou diga qual métrica específica quer que eu implemente."
                )
        else:
            # 1) Mostra a resposta determinística
            if isinstance(result, pd.DataFrame):
                st.dataframe(result)
            else:
                st.write(result)

            # 2) Explica com IA (opcional)
            if USE_IA:
                with st.spinner("Explicando com IA…"):
                    explicacao, err = ask_model_explain(
                        client, MODEL_NAME, pergunta, result, max_numbers=MAX_NUMBERS_TO_SEND
                    )
                if err:
                    st.error(err)
                else:
                    st.markdown(explicacao)

        # salva no histórico
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "(ver acima – resposta renderizada com dataframe/valores + IA opcional)",
            }
        )

# ------------------------------------------------------------------
# Exportar dados
# ------------------------------------------------------------------
with st.expander("📁 Exportar dados para Excel"):
    if clientes is None:
        st.warning("Carregue os dados primeiro.")
    else:
        exportar = st.selectbox(
            "Escolha o conjunto de dados:", ["Clientes", "Pedidos", "Itens", "Produtos"]
        )
        if st.button("📄 Exportar"):
            dfs = {
                "Clientes": clientes,
                "Pedidos": pedidos,
                "Itens": itens,
                "Produtos": produtos,
            }
            df_export = dfs[exportar]
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df_export.to_excel(writer, sheet_name=exportar, index=False)
            buffer.seek(0)
            st.download_button(
                label=f"⬇️ Baixar {exportar}.xlsx",
                data=buffer,
                file_name=f"{exportar}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
