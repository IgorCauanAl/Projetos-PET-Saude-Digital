import os
import shutil
import queue
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from watchdog.observers import Observer

from config import PASTA_PROCESSADOS, PASTA_MONITORADA, PASTA_DOWNLOADS
from extracao import atualizar_planilha, limpar_arquivos_antigos
from monitoramento import RoteadorDownloads, MonitorRelatorios

class AplicacaoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Produção 2026 - Profissional Cátia")
        self.root.geometry("850x650")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.fila_eventos = queue.Queue()

        self.txt_log = ctk.CTkTextbox(
            self.root, font=("Consolas", 18), state="disabled", wrap="word",
            fg_color="#1e1e1e", text_color="#f8f8f2"
        )
        self.txt_log.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        cores = {"VERMELHO": "#ff5555", "VERDE": "#50fa7b", "AMARELO": "#f1fa8c", 
                 "AZUL": "#8be9fd", "ROXO": "#bd93f9", "CIANO": "#8be9fd", 
                 "BRANCO": "#ffffff", "PADRAO": "#f8f8f2"}
        for nome, hex_cor in cores.items():
            self.txt_log.tag_config(nome, foreground=hex_cor, justify="center")

        self.verificar_fila()
        self.exibir_instrucoes()
        self.iniciar_monitoramento()

    def inserir_log(self, mensagem, cor="PADRAO"):
        self.root.after(0, self._inserir_texto, mensagem, cor)

    def _inserir_texto(self, mensagem, cor):
        self.txt_log.configure(state="normal")
        self.txt_log.insert(tk.END, mensagem + "\n", cor)
        self.txt_log.see(tk.END) 
        self.txt_log.configure(state="disabled")

    def exibir_instrucoes(self):
        self.inserir_log("-" * 70, "ROXO")
        self.inserir_log("SISTEMA DE PRODUÇÃO 2026 - MONITORAMENTO ATIVO", "BRANCO")
        self.inserir_log("-" * 70 + "\n", "ROXO")
        self.inserir_log("INSTRUÇÕES AO USUÁRIO:", "AMARELO")
        self.inserir_log("1. MANTENHA ABERTO: Pode minimizar esta janela.", "VERDE")
        self.inserir_log("2. O arquivo precisa começar com 'emulti'.", "VERDE")
        self.inserir_log("3. PLANILHA FECHADA: Não deixe a planilha aberta.", "VERMELHO")
        self.inserir_log("4. LIMPEZA: PDFs são apagados após 24h.\n", "VERDE")
        self.inserir_log("Monitorando Downloads e Pasta Local...", "VERDE")

    def verificar_fila(self):
        try:
            while not self.fila_eventos.empty():
                evento = self.fila_eventos.get_nowait()
                if evento["acao"] == "PROCESSAR_PDF":
                    self.solicitar_confirmacao_e_atualizar(evento)
        except queue.Empty: pass
        finally: self.root.after(200, self.verificar_fila)

    def solicitar_confirmacao_e_atualizar(self, evento):
        # Desempacota variáveis
        tipo, mes = evento["tipo"], evento["mes"]
        prof, dupl = evento["profissionais"], evento["duplicados"]
        prof_planilha, caminho = evento["profissionais_planilha"], evento["caminho"]

        self.inserir_log("\n" + "="*70, "AMARELO")
        self.inserir_log(f" RELATÓRIO DETECTADO: {tipo} | MÊS: {mes} ", "CIANO")
        self.inserir_log("="*70, "AMARELO")
        self.inserir_log(f"{'NOME':<40} | {'VALOR':^10} | {'STATUS':^12}", "BRANCO")
        self.inserir_log("-" * 70, "BRANCO")
        
        novos = False
        for nome, valor in prof.items():
            nome_exib = nome[:37] + "..." if len(nome) > 40 else nome
            status, cor = "OK", "PADRAO"
            if prof_planilha and nome not in prof_planilha:
                status, cor, novos = "NOVO", "ROXO", True
            elif nome in dupl:
                status, cor = "SOMADO", "AZUL"
            self.inserir_log(f"{nome_exib:<40} | {valor:^10} | {status:^12}", cor)
            
        self.inserir_log("="*70 + "\n", "AMARELO")

        msg = f"Relatório {tipo} de {mes} lido com sucesso.\n\nPLANILHA FECHADA ANTES DO OK!"
        if dupl: msg += "\n\nHá nomes duplicados."
        if novos: msg += "\n\nNovos profissionais serão inseridos."

        if messagebox.askokcancel("Ação Necessária", msg, parent=self.root): 
            self.inserir_log("Atualizando...", "AMARELO")
            if atualizar_planilha(tipo, mes, prof, self):
                self._limpar_e_arquivar_pdf(caminho)
        else:
            self.inserir_log("Cancelado. PDF mantido.", "VERMELHO")

    def _limpar_e_arquivar_pdf(self, caminho_arquivo):
        try:
            nome_original = os.path.basename(caminho_arquivo)
            nome_sem_ext, ext = os.path.splitext(nome_original)
            nome_novo = f"{nome_sem_ext}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            shutil.move(caminho_arquivo, os.path.join(PASTA_PROCESSADOS, nome_novo))
            self.inserir_log("Processado movido para 'processados'.", "CIANO")
            limpar_arquivos_antigos(PASTA_PROCESSADOS, horas=24, app=self)
            self.inserir_log("Aguardando...\n", "VERDE")
        except Exception as e:
            self.inserir_log(f"Erro ao mover: {e}", "VERMELHO")

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
