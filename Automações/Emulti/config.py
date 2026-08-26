import os
import re

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
PASTA_MONITORADA = DIRETORIO_ATUAL

NOME_BASE_PLANILHA = "Planilha Emulti"
EXTENSAO_PLANILHA = ".xlsx"
ANO_PADRAO_PLANILHA = "2026"

HORAS_LIMPEZA_PDFS = 24
MINUTOS_LIMPEZA_REJEITADOS = 20 # Nova regra de negócio para a lixeira
MAX_BACKUPS = 5

def localizar_planilha_emulti():
    candidatos = []
    try:
        for nome in os.listdir(PASTA_MONITORADA):
            nome_upper = nome.upper()
            if not nome_upper.endswith(EXTENSAO_PLANILHA.upper()):
                continue
            if nome.startswith("~$") or nome_upper.startswith("~"):
                continue

            if re.fullmatch(r"PLANILHA\s+EMULTI\s+\d{4}\.XLSX", nome_upper):
                caminho = os.path.join(PASTA_MONITORADA, nome)
                candidatos.append((os.path.getmtime(caminho), caminho))
                continue

            if nome_upper.startswith("PLANILHA EMULTI"):
                caminho = os.path.join(PASTA_MONITORADA, nome)
                candidatos.append((os.path.getmtime(caminho), caminho))
    except OSError:
        pass

    if candidatos:
        candidatos.sort(reverse=True)
        return candidatos[0][1]

    return os.path.join(PASTA_MONITORADA, f"{NOME_BASE_PLANILHA} {ANO_PADRAO_PLANILHA}{EXTENSAO_PLANILHA}")

PLANILHA_2026 = localizar_planilha_emulti()
PLANILHA_EMULTI = PLANILHA_2026

PASTA_PROCESSADOS = os.path.join(PASTA_MONITORADA, "Processados")
PASTA_COPIAS = os.path.join(PASTA_MONITORADA, "Copias")
PASTA_REJEITADOS = os.path.join(PASTA_MONITORADA, "Rejeitados")

for pasta in [PASTA_PROCESSADOS, PASTA_COPIAS, PASTA_REJEITADOS]:
    if not os.path.exists(pasta):
        os.makedirs(pasta)