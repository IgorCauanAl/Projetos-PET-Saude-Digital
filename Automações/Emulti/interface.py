import os
import shutil
import queue
import threading
import time
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk, messagebox
from watchdog.observers import Observer

# Importações dos seus módulos de lógica
from config import PASTA_PROCESSADOS, PASTA_MONITORADA, PASTA_DOWNLOADS, PLANILHA_2026
from extracao import atualizar_planilha, limpar_arquivos_antigos
from monitoramento import RoteadorDownloads, MonitorRelatorios

class AplicacaoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Produção 2026 - Profissional Cátia")
        self.root.geometry("1100x750")
        self.root.configure(bg="#F4F6F9")
        self.fila_eventos = queue.Queue()

        # --- CABEÇALHO (BANNER) ---
        frame_topo = tk.Frame(self.root, bg="#FFFFFF", pady=15, padx=20, relief="groove", bd=1)
        frame_topo.pack(fill="x", padx=20, pady=15)
        
        tk.Label(frame_topo, text="👋 Olá, Cátia!", bg="#FFFFFF", fg="#2C3E50", 
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(frame_topo, text="Sua assistente está monitorando os relatórios 'emulti' para você.", 
                 bg="#FFFFFF", fg="#7F8C8D", font=("Segoe UI", 11)).pack(anchor="w")

        # --- CAIXA DE INSTRUÇÕES COLORIDAS ---
        self.caixa_instrucoes = tk.Text(frame_topo, bg="#FFFFFF", font=("Segoe UI", 10), 
                                        bd=0, highlightthickness=0, height=8, wrap="word")
        self.caixa_instrucoes.pack(fill="x", pady=5)

        self.caixa_instrucoes.tag_configure("padrao", foreground="#7F8C8D")
        self.caixa_instrucoes.tag_configure("alerta", foreground="#E74C3C", font=("Segoe UI", 10, "bold"))
        self.caixa_instrucoes.tag_configure("ok", foreground="#27AE60", font=("Segoe UI", 10, "bold"))
        self.caixa_instrucoes.tag_configure("atencao", foreground="#E67E22", font=("Segoe UI", 10, "bold"))

        self.caixa_instrucoes.insert("end", "1) MANTENHA ABERTO: ", "padrao")
        self.caixa_instrucoes.insert("end", "Pode minimizar esta janela, mas não feche.\n", "ok")
        self.caixa_instrucoes.insert("end", "2) NOME DO ARQUIVO: ", "padrao")
        self.caixa_instrucoes.insert("end", "O PDF precisa começar com 'emulti' para ser lido.\n", "atencao")
        self.caixa_instrucoes.insert("end", "3) PLANILHA FECHADA: ", "padrao")
        self.caixa_instrucoes.insert("end", "NUNCA deixe a planilha aberta", "alerta")
        self.caixa_instrucoes.insert("end", " ao clicar em confirmar atualização.\n", "padrao")
        self.caixa_instrucoes.insert("end", "4) SEGURANÇA: ", "padrao")
        self.caixa_instrucoes.insert("end", "Sempre é feito um backup na pasta 'Copias' após cada sucesso.\n", "ok")
        self.caixa_instrucoes.configure(state="disabled")

        # --- STATUS DA ÚLTIMA AÇÃO ---
        frame_status = tk.Frame(self.root, bg="#FFFFFF", pady=10, padx=20, relief="groove", bd=1)
        frame_status.pack(fill="x", padx=20, pady=(0, 15))
        self.var_ultima_acao = tk.StringVar(value="🚀 Sistema iniciado. Aguardando relatórios...")
        tk.Label(frame_status, textvariable=self.var_ultima_acao, bg="#FFFFFF", 
                 fg="#34495E", font=("Segoe UI", 11)).pack(side="left")

        # --- TABELA DE DADOS ---
        frame_tabela = tk.Frame(self.root, bg="#F4F6F9")
        frame_tabela.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        colunas = ("nome", "categoria", "qtd_doc", "qtd_plan", "status")
        self.tabela = ttk.Treeview(frame_tabela, columns=colunas, show="headings")
        
        self.tabela.heading("nome", text="Nome")
        self.tabela.heading("categoria", text="Tipo do Relatório")
        self.tabela.heading("qtd_doc", text="Qtd.Documento")
        self.tabela.heading("qtd_plan", text="Qtd.Planilha")
        self.tabela.heading("status", text="Status na Planilha")

        self.tabela.column("nome", width=300, anchor="w")
        self.tabela.column("categoria", width=200, anchor="center")
        self.tabela.column("qtd_doc", width=120, anchor="center")
        self.tabela.column("qtd_plan", width=120, anchor="center")
        self.tabela.column("status", width=200, anchor="center")

        # Cores para as linhas da tabela
        self.tabela.tag_configure('novo', background='#EBF5FB', foreground='#2E86C1')
        self.tabela.tag_configure('sucesso', background='#E8F8F5', foreground='#117864')
        self.tabela.tag_configure('duplicado', background='#FEF9E7', foreground='#9A7D0A')

        # Barras de rolagem
        scrollbar_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_y.pack(side="right", fill="y")
        self.tabela.pack(side="left", fill="both", expand=True)

        # Iniciar threads e monitoramento
        self.verificar_fila()
        self.iniciar_monitoramento()

    def inserir_log(self, mensagem, cor_ignorada=None):
        self.var_ultima_acao.set(mensagem)

    def verificar_fila(self):
        try:
            while not self.fila_eventos.empty():
                evento = self.fila_eventos.get_nowait()
                if evento["acao"] == "PROCESSAR_PDF":
                    self.solicitar_confirmacao_e_atualizar(evento)
        except queue.Empty: pass
        finally: self.root.after(200, self.verificar_fila)

    def solicitar_confirmacao_e_atualizar(self, evento):
        tipo, mes = evento["tipo"], evento["mes"]
        prof, dupl = evento["profissionais"], evento["duplicados"]
        prof_planilha, caminho = evento["profissionais_planilha"], evento["caminho"]

        for item in self.tabela.get_children():
            self.tabela.delete(item)

        for nome, valor in prof.items():
            status_visual = "OK - ATUALIZAR"
            tag_cor = 'sucesso'
            # AQUI: Inicializa com 0 numérico para garantir o padrão visual de quantidade
            qtd_planilha_visual = 0 
            
            # Se já existir na planilha, captura o valor numérico exato que está lá
            if prof_planilha and nome in prof_planilha:
                qtd_planilha_visual = prof_planilha[nome]
            
            # Condicionais de estado e cor (sem mascarar o número)
            if prof_planilha and nome not in prof_planilha:
                status_visual = "NOVO PROFISSIONAL"
                tag_cor = 'novo'
            elif nome in dupl:
                status_visual = "SOMAR VALORES"
                tag_cor = 'duplicado'

            self.tabela.insert("", "end", values=(nome, tipo, valor, qtd_planilha_visual, status_visual), tags=(tag_cor,))

        self.var_ultima_acao.set(f"📊 Relatório {tipo} de {mes} detectado. Aguardando sua confirmação...")

        msg = f"Detectado: {tipo} | Mês: {mes}\n\nDeseja atualizar a planilha agora?\nLembre-se: A PLANILHA DEVE ESTAR FECHADA!"
        
        if messagebox.askokcancel("Confirmação de Leitura", msg):
            self.var_ultima_acao.set("⏳ Atualizando planilha... aguarde.")
            
            if atualizar_planilha(tipo, mes, prof, self):
                self.var_ultima_acao.set("✅ Planilha atualizada. Arquivo movido para Processados.")
        else:
            self.var_ultima_acao.set("⚠️ Operação cancelada. O PDF lido foi movido para Processados.")

        self._limpar_e_arquivar_pdf(caminho)

    def _limpar_e_arquivar_pdf(self, caminho_arquivo):
        try:
            nome_original = os.path.basename(caminho_arquivo)
            nome_sem_ext, ext = os.path.splitext(nome_original)
            nome_novo = f"{nome_sem_ext}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            shutil.move(caminho_arquivo, os.path.join(PASTA_PROCESSADOS, nome_novo))
            
            limpar_arquivos_antigos(PASTA_PROCESSADOS, horas=24, app=self)
        except Exception as e:
            self.var_ultima_acao.set(f"Erro ao mover arquivo: {e}")

    def iniciar_monitoramento(self):
        limpar_arquivos_antigos(PASTA_PROCESSADOS, horas=24, app=self)
        self.observer = Observer()
        self.observer.schedule(MonitorRelatorios(self), PASTA_MONITORADA, recursive=False)
        self.observer.schedule(RoteadorDownloads(self), PASTA_DOWNLOADS, recursive=False)
        self.observer.start()

    def fechar_aplicacao(self):
        self.observer.stop()
        self.observer.join()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
    style.configure("Treeview", font=("Segoe UI", 10), rowheight=25)
    
    app = AplicacaoGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.fechar_aplicacao)
    root.mainloop()