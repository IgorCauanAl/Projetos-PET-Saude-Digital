import os

# Descobre a pasta exata onde ESTE script Python está localizado
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))

# Mantém a pasta de Downloads apontada para a pasta padrão do usuário do Windows
PASTA_DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")

# === CONFIGURAÇÕES DE CAMINHOS ===
# A pasta monitorada agora é a própria pasta onde o script está rodando
PASTA_MONITORADA = DIRETORIO_ATUAL

# O nome da planilha fica na mesma pasta do script
PLANILHA_2026 = os.path.join(PASTA_MONITORADA, "Planilha Produção 2026.xlsx")

# Pastas auxiliares serão criadas DENTRO da pasta do script
PASTA_PROCESSADOS = os.path.join(PASTA_MONITORADA, "Processados")
PASTA_COPIAS = os.path.join(PASTA_MONITORADA, "Copias")

# Garante a existência dos diretórios auxiliares na inicialização
# (Não precisamos checar a PASTA_MONITORADA porque o script já está dentro dela)
for pasta in [PASTA_PROCESSADOS, PASTA_COPIAS]:
    if not os.path.exists(pasta):
        os.makedirs(pasta)