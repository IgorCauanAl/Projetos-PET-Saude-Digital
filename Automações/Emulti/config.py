import os
import re

# Descobre a pasta exata onde ESTE script Python está localizado
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))

# Mantém a pasta de Downloads apontada para a pasta padrão do usuário do Windows
PASTA_DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")

# === CONFIGURAÇÕES DE CAMINHOS ===
# A pasta monitorada agora é a própria pasta onde o script está rodando
PASTA_MONITORADA = DIRETORIO_ATUAL

# Nome obrigatório da planilha: "Planilha Emulti" + ano desejado pela gestora.
# Exemplos aceitos:
# - Planilha Emulti 2025.xlsx
# - Planilha Emulti 2026.xlsx
# - Planilha Emulti 2027.xlsx
NOME_BASE_PLANILHA = "Planilha Emulti"
EXTENSAO_PLANILHA = ".xlsx"
ANO_PADRAO_PLANILHA = "2026"

# Limpezas automáticas
HORAS_LIMPEZA_PDFS = 24
MAX_BACKUPS = 5


def localizar_planilha_emulti():
    """
    Localiza a planilha da gestora na pasta do sistema.

    Regra de nome:
    - O arquivo precisa começar com "Planilha Emulti".
    - O ano fica logo depois do nome, conforme o ano que a gestora estiver usando.
    - Exemplo: Planilha Emulti 2026.xlsx

    Se houver mais de uma planilha com esse padrão, usa a mais recente.
    """
    candidatos = []

    try:
        for nome in os.listdir(PASTA_MONITORADA):
            nome_upper = nome.upper()

            if not nome_upper.endswith(EXTENSAO_PLANILHA.upper()):
                continue
            if nome.startswith("~$") or nome_upper.startswith("~"):
                continue

            # Aceita: Planilha Emulti 2025.xlsx, Planilha Emulti 2026.xlsx, etc.
            if re.fullmatch(r"PLANILHA\s+EMULTI\s+\d{4}\.XLSX", nome_upper):
                caminho = os.path.join(PASTA_MONITORADA, nome)
                candidatos.append((os.path.getmtime(caminho), caminho))
                continue

            # Fallback seguro: também aceita se começar com Planilha Emulti e terminar em .xlsx.
            # Isso ajuda se a gestora salvar como "Planilha Emulti 2026 - Cópia.xlsx".
            if nome_upper.startswith("PLANILHA EMULTI"):
                caminho = os.path.join(PASTA_MONITORADA, nome)
                candidatos.append((os.path.getmtime(caminho), caminho))

    except OSError:
        pass

    if candidatos:
        candidatos.sort(reverse=True)
        return candidatos[0][1]

    # Caminho padrão para mensagem de erro previsível.
    return os.path.join(PASTA_MONITORADA, f"{NOME_BASE_PLANILHA} {ANO_PADRAO_PLANILHA}{EXTENSAO_PLANILHA}")


# Mantém o nome antigo da constante para não quebrar os outros arquivos do sistema.
PLANILHA_2026 = localizar_planilha_emulti()
PLANILHA_EMULTI = PLANILHA_2026

# Pastas auxiliares serão criadas DENTRO da pasta do script
PASTA_PROCESSADOS = os.path.join(PASTA_MONITORADA, "Processados")
PASTA_COPIAS = os.path.join(PASTA_MONITORADA, "Copias")
PASTA_REJEITADOS = os.path.join(PASTA_MONITORADA, "Rejeitados")

# Garante a existência dos diretórios auxiliares na inicialização
for pasta in [PASTA_PROCESSADOS, PASTA_COPIAS, PASTA_REJEITADOS]:
    if not os.path.exists(pasta):
        os.makedirs(pasta)
