import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime

# Configuração da interface
st.set_page_config(page_title="POC Expressa - E-commerce", layout="wide")
st.title("📦 POC Expressa de E-commerce")

# Carrega os dados CSV da pasta 'data'
@st.cache_data
def carregar_dados():
    try:
        clientes = pd.read_csv("data/clients.csv", encoding="utf-8")
        pedidos = pd.read_csv("data/orders.csv", encoding="utf-8")
        itens = pd.read_csv("data/items.csv", encoding="utf-8")
        produtos = pd.read_csv("data/products.csv", encoding="utf-8")
        return clientes, pedidos, itens, produtos
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return None, None, None, None

# Carregamento inicial
clientes, pedidos, itens, produtos = carregar_dados()

if clientes is not None:
    st.success("✅ Dados carregados com sucesso!")

    # KPIs executivos
    col1, col2, col3, col4 = st.columns(4)
    try:
        total_pedidos = pedidos.shape[0]
        ticket_medio = pedidos[pedidos["SituacaoPedido"] == "Faturado"]["TotalPedido"].mean()
        frete_gratis_qtd = pedidos[pedidos["FreteGratis"].astype(str).str.lower().isin(["sim", "s", "true", "1"])].shape[0]
        pct_frete_gratis = (frete_gratis_qtd / total_pedidos) * 100
        desconto_medio = pedidos["ValorDesconto"].mean()

        col1.metric("📦 Total de Pedidos", f"{total_pedidos:,}")
        col2.metric("💰 Ticket Médio", f"R$ {ticket_medio:,.2f}")
        col3.metric("🚚 Frete Grátis (%)", f"{pct_frete_gratis:.1f}%")
        col4.metric("🔻 Desconto Médio", f"R$ {desconto_medio:,.2f}")
    except Exception as e:
        st.warning(f"⚠️ Não foi possível calcular os KPIs: {e}")

    # Visualização de dados
    with st.expander("🔍 Visualizar amostra dos dados"):
        st.write("Clientes", clientes.head())
        st.write("Pedidos", pedidos.head())
        st.write("Itens", itens.head())
        st.write("Produtos", produtos.head())

    # Exportar dados para Excel
    with st.expander("📁 Exportar dados para Excel"):
        exportar = st.selectbox("Escolha o conjunto de dados:", ["Clientes", "Pedidos", "Itens", "Produtos"])
        btn_exportar = st.button("📤 Exportar")

        if btn_exportar:
            dfs = {
                "Clientes": clientes,
                "Pedidos": pedidos,
                "Itens": itens,
                "Produtos": produtos
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
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Campo de pergunta
    pergunta = st.text_input("Digite uma pergunta sobre os dados:")

    if pergunta:
        st.markdown(f"🔎 **Pergunta:** {pergunta}")

        # 1. Ticket médio
        if "ticket médio" in pergunta.lower():
            try:
                pedidos_faturados = pedidos[pedidos["SituacaoPedido"] == "Faturado"]
                ticket_medio = pedidos_faturados["TotalPedido"].mean()
                st.success(f"📊 O ticket médio dos pedidos faturados é de R$ {ticket_medio:.2f}")
            except Exception as e:
                st.error(f"Erro ao calcular o ticket médio: {e}")

        # 2. Produtos mais vendidos
        elif "produtos mais vendidos" in pergunta.lower():
            try:
                top_produtos = (
                    itens.groupby("CodigoProdutoVendido")["QuantidadeVendidaItem"]
                    .sum()
                    .reset_index()
                    .sort_values(by="QuantidadeVendidaItem", ascending=False)
                    .head(5)
                )
                resultado = top_produtos.merge(
                    produtos.drop_duplicates(subset="CodigoProduto"),
                    left_on="CodigoProdutoVendido",
                    right_on="CodigoProduto",
                    how="left"
                )[["Produto", "QuantidadeVendidaItem"]]

                st.write("📦 Top 5 produtos mais vendidos por quantidade:", resultado)

                fig = px.bar(
                    resultado,
                    x="QuantidadeVendidaItem",
                    y="Produto",
                    orientation="h",
                    color="QuantidadeVendidaItem",
                    color_continuous_scale="blues",
                    labels={"QuantidadeVendidaItem": "Qtd Vendida"},
                    title="Top 5 Produtos Mais Vendidos"
                )
                fig.update_layout(height=400, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Erro ao buscar produtos mais vendidos: {e}")

        # 3. Formas de pagamento
        elif "forma de pagamento" in pergunta.lower() or "formas de pagamento" in pergunta.lower():
            try:
                forma_pgto = pedidos["FormaPagamento"].value_counts().reset_index()
                forma_pgto.columns = ["Forma de Pagamento", "Total"]
                st.write("💳 Formas de pagamento mais utilizadas:", forma_pgto)

                fig = px.pie(
                    forma_pgto,
                    names="Forma de Pagamento",
                    values="Total",
                    title="Distribuição das Formas de Pagamento",
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Erro ao calcular formas de pagamento: {e}")

        # 4. Frete grátis
        elif "frete grátis" in pergunta.lower() or "frete gratis" in pergunta.lower():
            try:
                total_frete_gratis = pedidos[pedidos["FreteGratis"].astype(str).str.lower().isin(["sim", "s", "true", "1"])].shape[0]
                st.success(f"📦 Total de pedidos com frete grátis: {total_frete_gratis}")
            except Exception as e:
                st.error(f"Erro ao calcular pedidos com frete grátis: {e}")

        # 5. Distribuição de status
        elif "status dos pedidos" in pergunta.lower() or "distribuição de status" in pergunta.lower():
            try:
                status = pedidos["SituacaoPedido"].value_counts().reset_index()
                status.columns = ["Situação", "Total"]
                st.write("📊 Distribuição de pedidos por situação:", status)

                fig = px.pie(
                    status,
                    names="Situação",
                    values="Total",
                    title="Status dos Pedidos",
                    color_discrete_sequence=px.colors.sequential.Agsunset
                )
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Erro ao calcular status dos pedidos: {e}")

        # 6. Desconto médio
        elif "valor médio de desconto" in pergunta.lower() or "desconto médio" in pergunta.lower():
            try:
                desconto_medio = pedidos["ValorDesconto"].mean()
                st.success(f"💰 Valor médio de desconto aplicado: R$ {desconto_medio:.2f}")
            except Exception as e:
                st.error(f"Erro ao calcular o valor médio de desconto: {e}")

        # 7. Tipo de cliente
        elif "tipo de cliente" in pergunta.lower() or "cliente físico" in pergunta.lower() or "cliente jurídico" in pergunta.lower():
            try:
                pedidos_clientes = pedidos.merge(clientes, left_on="CodigoClientePedido", right_on="CodigoCliente", how="left")
                tipos = pedidos_clientes["TipoCliente"].value_counts().reset_index()
                tipos.columns = ["Tipo de Cliente", "Total de Pedidos"]
                st.write("🧾 Pedidos por tipo de cliente:", tipos)

                fig = px.bar(
                    tipos,
                    x="Tipo de Cliente",
                    y="Total de Pedidos",
                    color="Tipo de Cliente",
                    title="Pedidos por Tipo de Cliente",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Erro ao calcular pedidos por tipo de cliente: {e}")

        else:
            st.warning("⚠️ Essa pergunta ainda não está mapeada.")
else:
    st.error("❌ Os dados não foram carregados. Verifique os arquivos na pasta /data.")
