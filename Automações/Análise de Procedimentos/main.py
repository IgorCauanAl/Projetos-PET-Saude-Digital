import os
import time
import warnings
import shutil
import threading
import queue
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from openpyxl import load_workbook

# Configurações e Utilitários do projeto
from config import PASTA_MONITORADA, PLANILHA_ANALISE, Cores
from utils import imprimir_banner_inicial, registrar_log

# Importando a função ÚNICA de mapeamento
from excel_manager import mapear_ine_para_abas

# Importações das estratégias de extração
from sisab_strategies import ContextoSisab
from pec_strategies import ContextoPec  

warnings.filterwarnings("ignore", category=UserWarning)

# Configurações de diretório
PASTA_AUTOMACAO = PASTA_MONITORADA
PASTA_PROCESSADOS = os.path.join(PASTA_AUTOMACAO, "Processados")

os.makedirs(PASTA_AUTOMACAO, exist_ok=True)
os.makedirs(PASTA_PROCESSADOS, exist_ok=True)

fila_arquivos = []
fila_interface = queue.Queue()

def planilha_esta_aberta(caminho_arquivo):
    """Testa se o arquivo está bloqueado (aberto no Excel) tentando um acesso rápido."""
    if not os.path.exists(caminho_arquivo):
        return False
    try:
        with open(caminho_arquivo, 'a'):
            pass
        return False
    except PermissionError:
        return True

def inicializar_mapa_postos():
    if not os.path.exists(PLANILHA_ANALISE):
        return {}
    try:
        wb = load_workbook(PLANILHA_ANALISE, data_only=True)
        mapa = mapear_ine_para_abas(wb)
        wb.close()
        return mapa
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível carregar o mapa inicial. ({e})")
        return {}

MAPA_NOMES_POSTOS = inicializar_mapa_postos()

class RedirecionadorSaida:
    def __init__(self, fila):
        self.fila = fila
        self.buffer = ""
    
    def write(self, texto):
        self.buffer += texto
        if '\n' in self.buffer:
            linhas = self.buffer.split('\n')
            for linha in linhas[:-1]:
                if linha.strip():
                    self.fila.put(linha.strip())
            self.buffer = linhas[-1]
            
    def flush(self): pass

def limpar_codigos_cor(texto):
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@~])')
    return ansi_escape.sub('', texto)

def eh_arquivo_valido(nome_arquivo):
    nome = nome_arquivo.lower()
    if nome.startswith("~") or nome.startswith(".") or "analise.xlsx" in nome: return False
    return nome.endswith(".xlsx") or nome.endswith(".pdf") or nome.endswith(".csv")

def processar_fila_em_lote():
    global fila_arquivos, MAPA_NOMES_POSTOS
    if not fila_arquivos: return
    
    if planilha_esta_aberta(PLANILHA_ANALISE):
        print("❌ PAUSA: A planilha 'analise.xlsx' está ABERTA! Feche-a para continuar.")
        return 
    
    lote = list(set(fila_arquivos.copy()))
    fila_arquivos.clear()
    
    print("UI_CMD|LIMPAR_TABELA")
    print(f"⚙️ Processando {len(lote)} arquivo(s)...")
    
    try:
        # CORREÇÃO: Adicionado data_only=True para extrair valores reais no lugar de fórmulas
        wb = load_workbook(PLANILHA_ANALISE, data_only=True)
        mapa_abas = mapear_ine_para_abas(wb)
        
        for caminho in lote:
            if not os.path.exists(caminho): continue 
            nome_arquivo_min = os.path.basename(caminho).lower()
            
            if nome_arquivo_min.endswith(".pdf"):
                contexto = ContextoPec(caminho, wb, mapa_abas)
                contexto.executar()
            elif "sisab" in nome_arquivo_min: # MANTIDO SEM ALTERAÇÃO (Tópico 1)
                contexto = ContextoSisab(caminho, wb, mapa_abas)
                contexto.executar()
            
        print(f"💾 Salvando resultados na planilha...")
        wb.save(PLANILHA_ANALISE)
        wb.close()
        
        # Atualiza o mapa global para a interface
        MAPA_NOMES_POSTOS = inicializar_mapa_postos()

        for caminho in lote:
            if os.path.exists(caminho):
                shutil.move(caminho, os.path.join(PASTA_PROCESSADOS, os.path.basename(caminho)))
        
        print("✅ Tudo pronto! Dados salvos e arquivos movidos.")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        fila_arquivos.extend(lote)

class MonitorRelatorios(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and eh_arquivo_valido(os.path.basename(event.src_path)):
            time.sleep(1) 
            if event.src_path not in fila_arquivos:
                fila_arquivos.append(event.src_path)

def iniciar_automacao_background():
    # Varredura inicial (Lê o que já está na pasta)
    if os.path.exists(PASTA_AUTOMACAO):
        for arquivo in os.listdir(PASTA_AUTOMACAO):
            caminho_completo = os.path.join(PASTA_AUTOMACAO, arquivo)
            if os.path.isfile(caminho_completo) and eh_arquivo_valido(arquivo):
                if caminho_completo not in fila_arquivos:
                    fila_arquivos.append(caminho_completo)

    event_handler = MonitorRelatorios()
    observer = Observer()
    observer.schedule(event_handler, path=PASTA_AUTOMACAO, recursive=False)
    observer.start()
    try:
        while True:
            processar_fila_em_lote()
            time.sleep(5)
    except Exception:
        observer.stop()
    observer.join()

class AplicativoAutomacao:
    def __init__(self, root):
        self.root = root
        self.root.title("Assistente de Análise - Profissional Rosileia")
        self.root.geometry("1100x750") 
        self.root.configure(bg="#F4F6F9")

        frame_topo = tk.Frame(self.root, bg="#FFFFFF", pady=15, padx=20, relief="groove", bd=1)
        frame_topo.pack(fill="x", padx=20, pady=15)
        tk.Label(frame_topo, text="👋 Olá, Rosileia!", bg="#FFFFFF", fg="#2C3E50", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(frame_topo, text="O sistema monitora a pasta e salva na planilha automaticamente.", bg="#FFFFFF", fg="#7F8C8D", font=("Segoe UI", 11)).pack(anchor="w")

        frame_status = tk.Frame(self.root, bg="#FFFFFF", pady=10, padx=20, relief="groove", bd=1)
        frame_status.pack(fill="x", padx=20, pady=(0, 15))
        self.var_ultima_acao = tk.StringVar(value="Monitorando a pasta...")
        tk.Label(frame_status, textvariable=self.var_ultima_acao, bg="#FFFFFF", fg="#34495E", font=("Segoe UI", 11)).pack(side="left")

        frame_tabela = tk.Frame(self.root, bg="#F4F6F9")
        frame_tabela.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        colunas = ("ine", "posto", "mes", "indicador", "valor", "status") 
        self.tabela = ttk.Treeview(frame_tabela, columns=colunas, show="headings")
        
        self.tabela.heading("ine", text="INE")
        self.tabela.heading("posto", text="Posto (Aba)")
        self.tabela.heading("mes", text="Mês")
        self.tabela.heading("indicador", text="Indicador / Procedimento")
        self.tabela.heading("valor", text="Valor")
        self.tabela.heading("status", text="Status na Planilha")

        self.tabela.column("ine", width=80, anchor="center")
        self.tabela.column("posto", width=180, anchor="w")
        self.tabela.column("mes", width=90, anchor="center")
        self.tabela.column("indicador", width=300, anchor="w")
        self.tabela.column("valor", width=70, anchor="center")
        self.tabela.column("status", width=180, anchor="center")

        self.tabela.tag_configure('sucesso', background='#E8F8F5', foreground='#117864') 
        self.tabela.tag_configure('erro', background='#FDEDEC', foreground='#C0392B')    

        scrollbar = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tabela.pack(side="left", fill="both", expand=True)

        sys.stdout = RedirecionadorSaida(fila_interface)
        self.atualizar_interface()
        threading.Thread(target=iniciar_automacao_background, daemon=True).start()

    def atualizar_interface(self):
        try:
            while True:
                texto = fila_interface.get_nowait()
                texto_limpo = limpar_codigos_cor(texto)
                
                if texto_limpo == "UI_CMD|LIMPAR_TABELA":
                    for item in self.tabela.get_children():
                        self.tabela.delete(item)
                        
                elif texto_limpo.startswith("UI_RESULTADO|"):
                    partes = texto_limpo.split("|")
                    if len(partes) >= 7:
                        status_cod = partes[1].strip()
                        ine_visual = partes[2].strip()
                        aba_nome = partes[3].strip()
                        indicador = partes[4].strip()
                        valor = partes[5].strip()
                        mes_visual = partes[6].strip()

                        status_map = {
                            "SUCESSO": ("✅ Salvo com sucesso", "sucesso"),
                            "FALHA_MES": ("❌ Mês não achado", "erro"),
                            "FALHA_SISTEMA": ("❌ Coluna SISAB/PEC ñ achada", "erro"),
                            "FALHA_LINHA": ("❌ Indicador não achado", "erro"),
                            "FALHA_INE": ("❌ Aba ñ encontrada", "erro")
                        }
                        texto_status, tag_cor = status_map.get(status_cod, ("❌ Erro desconhecido", "erro"))

                        posto_nome = MAPA_NOMES_POSTOS.get(ine_visual, aba_nome)
                        if ine_visual in ["None", "PDF_SEM_NOME"]: ine_visual = "-"

                        self.tabela.insert("", 0, values=(ine_visual, posto_nome, mes_visual, indicador, valor, texto_status), tags=(tag_cor,))
                
                elif not texto_limpo.startswith("DADO_EXTRAIDO|"):
                    self.var_ultima_acao.set(texto_limpo)
                        
        except queue.Empty:
            pass
        self.root.after(200, self.atualizar_interface)

if __name__ == "__main__":
    root = tk.Tk()
    app = AplicativoAutomacao(root)
    root.mainloop()