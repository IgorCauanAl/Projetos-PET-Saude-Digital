import os

# === CONFIGURAÇÕES DE CAMINHOS ===
PASTA_MONITORADA = r"C:\Users\win10\Desktop\multiteste"
PASTA_DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
PLANILHA_2026 = os.path.join(PASTA_MONITORADA, "Planilha Produção 2026 Teste.xlsx")
PASTA_PROCESSADOS = os.path.join(PASTA_MONITORADA, "processados")

# Garante a existência do diretório na inicialização das configurações
if not os.path.exists(PASTA_PROCESSADOS):
    os.makedirs(PASTA_PROCESSADOS)
