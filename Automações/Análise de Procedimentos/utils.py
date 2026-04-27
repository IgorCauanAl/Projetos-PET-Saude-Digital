import os
import re
import unicodedata
from datetime import datetime
from config import Cores

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def imprimir_banner_inicial():
    limpar_tela()
    print(f"{Cores.ROXO}{'='*70}")
    print(f"{Cores.NEGRITO}    🤖 AUTOMATIZAÇÃO DE PROCEDIMENTOS (LOTE & PDFPLUMBER)      {Cores.RESET}{Cores.ROXO}")
    print(f"{'='*70}{Cores.RESET}\n")
    print(f"{Cores.BRANCO}{Cores.NEGRITO}📋  INSTRUÇÕES AO USUÁRIO:{Cores.RESET}")
    print(f"{Cores.CIANO}----------------------------------------------------------------------{Cores.RESET}")
    print(f"  1. {Cores.AMARELO}NOMES DE ARQUIVOS:{Cores.RESET}")
    print(f"     - {Cores.NEGRITO}PEC (PDF):{Cores.RESET} O arquivo {Cores.VERMELHO}TEM QUE SER RENOMEADO{Cores.RESET} com o nome da unidade.")
    print(f"     - {Cores.NEGRITO}SISAB (Excel):{Cores.RESET} {Cores.VERDE}NÃO PRECISA{Cores.RESET} renomear o arquivo.")
    print(f"")
    print(f"  2. {Cores.AMARELO}PROCESSAMENTO EM LOTE:{Cores.RESET}")
    print(f"     - Pode soltar dezenas de arquivos de uma vez na pasta!")
    print(f"")
    print(f"  3. {Cores.AMARELO}LIMPEZA:{Cores.RESET} Assim que os dados forem inseridos na planilha,")
    print(f"     {Cores.FUNDO_VERMELHO} APAGUE OS ARQUIVOS DA PASTA {Cores.RESET} para evitar confusão.")
    print(f"{Cores.CIANO}----------------------------------------------------------------------{Cores.RESET}")
    print(f"\n{Cores.VERDE}📡  Monitorando pasta... Pode soltar os arquivos!{Cores.RESET}\n")

def registrar_log(mensagem, cor_terminal=None):
    if cor_terminal:
        print(f"{cor_terminal}[{datetime.now().strftime('%H:%M:%S')}] {mensagem}{Cores.RESET}")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {mensagem}")

def normalizar_texto(texto):
    """
    Remove acentos e caracteres especiais, mantendo letras, números e espaços.
    """
    if not texto: return ""
    texto = str(texto).upper()
    nfkd = unicodedata.normalize('NFD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # O \s na Regex (Expressão Regular) permite manter os espaços em branco
    texto_limpo = re.sub(r'[^A-Z0-9\s]', '', sem_acento).strip()
    # Remove espaços duplos acidentais
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
    return texto_limpo