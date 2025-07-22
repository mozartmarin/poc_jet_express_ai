import pandas as pd
import os

# Caminho de origem dos arquivos .xlsx (ajustado com base na sua imagem)
origem = r"C:\Delta.AiTO\POC&MVP\Base de Dados para Integração Jet x SkyOne"

# Caminho de destino onde os arquivos .csv serão salvos (pasta do seu projeto)
destino = "data"

# Dicionário com mapeamento dos arquivos a converter
arquivos = {
    "3_Cadastro de Clientes_Client.xlsx": "clients.csv",
    "4_Cadastro de Cabeçalho de Pedidos_OrderHeader.xlsx": "orders.csv",
    "5_Cadastro de Itens dos Pedidos_OrderItem.xlsx": "items.csv",
    "6_Cadastro de Produtos_Product.xlsx": "products.csv"
}

# Garantir que a pasta destino existe
os.makedirs(destino, exist_ok=True)

# Loop para converter cada arquivo
for nome_excel, nome_csv in arquivos.items():
    caminho_entrada = os.path.join(origem, nome_excel)
    caminho_saida = os.path.join(destino, nome_csv)

    try:
        df = pd.read_excel(caminho_entrada)
        df.to_csv(caminho_saida, index=False, encoding='utf-8')
        print(f"✔️ Convertido: {nome_excel} -> {nome_csv}")
    except Exception as e:
        print(f"❌ Erro ao converter {nome_excel}: {e}")
