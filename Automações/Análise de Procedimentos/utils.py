import os
import re
import unicodedata
import shutil
import glob
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
    if not texto: return ""
    texto = str(texto).upper()
    nfkd = unicodedata.normalize('NFD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    texto_limpo = re.sub(r'[^A-Z0-9\s]', '', sem_acento).strip()
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
    return texto_limpo

def realizar_backup_planilha(caminho_planilha):
    """
    Realiza o backup da planilha adicionando a data e hora.
    Mantém apenas os 10 backups mais recentes para poupar espaço.
    """
    if not os.path.exists(caminho_planilha):
        registrar_log("⚠️ Arquivo original não encontrado para backup.", Cores.AMARELO)
        return False
        
    pasta_backup = os.path.join(os.path.dirname(caminho_planilha), "Cópia")
    os.makedirs(pasta_backup, exist_ok=True)
    
    # CORREÇÃO 1: A variável timestamp é criada antes de ser usada!
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_arquivo_original = os.path.basename(caminho_planilha)

    nome_base, extensao = os.path.splitext(nome_arquivo_original)
    nome_backup = f"Copia_{timestamp}{extensao}"
    caminho_backup = os.path.join(pasta_backup, nome_backup)
    
    try:
        shutil.copy2(caminho_planilha, caminho_backup)
        registrar_log(f"💾 Backup de segurança criado: {nome_backup}", Cores.VERDE)
        
        # CORREÇÃO 2: Padrão de busca corrigido para encontrar os ficheiros 'Copia_...'
        padrao_busca = os.path.join(pasta_backup, f"Copia_*{extensao}")
        arquivos_backup = sorted(glob.glob(padrao_busca), key=os.path.getmtime)
        
        while len(arquivos_backup) > 10:
            arquivo_antigo = arquivos_backup.pop(0)
            os.remove(arquivo_antigo)
            registrar_log(f"♻️ Expurgo de backup antigo: {os.path.basename(arquivo_antigo)}", Cores.AMARELO)
            
        return True
    except Exception as e:
        registrar_log(f"❌ Falha crítica ao criar backup: {e}", Cores.VERMELHO)
        return False