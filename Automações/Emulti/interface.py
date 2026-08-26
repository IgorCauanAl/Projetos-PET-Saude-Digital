import os
import shutil
import queue
import subprocess
import sys
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from watchdog.observers import Observer

from config import PASTA_PROCESSADOS, PASTA_REJEITADOS, PASTA_MONITORADA, PASTA_DOWNLOADS, PLANILHA_2026, HORAS_LIMPEZA_PDFS, MINUTOS_LIMPEZA_REJEITADOS
from utils import limpar_arquivos_antigos
from load import planilha_esta_aberta, criar_backup_rotativo
from monitoring import RoteadorDownloads, MonitorRelatorios
from orchestrator import PipelineETL

class AplicacaoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Automação da Produção Emulti ")
        self.root.geometry("1200x840")
        self.root.configure(bg="#F4F6F9")
        self.fila_eventos = queue.Queue()
        self.pipeline = PipelineETL(self)

        frame_topo = tk.Frame(self.root, bg="#FFFFFF", pady=15, padx=20, relief="groove", bd=1)
        frame_topo.pack(fill="x", padx=20, pady=15)

        tk.Label(frame_topo, text="👋 Olá Gestora!", bg="#FFFFFF", fg="#2C3E50", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(frame_topo, text="Sua assistente está monitorando os relatórios 'emulti' para você.", bg="#FFFFFF", fg="#7F8C8D", font=("Segoe UI", 11)).pack(anchor="w")

        self.caixa_instrucoes = tk.Text(frame_topo, bg="#FFFFFF", font=("Segoe UI", 10), bd=0, highlightthickness=0, height=12, wrap="word")
        self.caixa_instrucoes.pack(fill="x", pady=5)

        self.caixa_instrucoes.tag_configure("padrao", foreground="#7F8C8D")
        self.caixa_instrucoes.tag_configure("alerta", foreground="#E74C3C", font=("Segoe UI", 10, "bold"))
        self.caixa_instrucoes.tag_configure("ok", foreground="#27AE60", font=("Segoe UI", 10, "bold"))
        self.caixa_instrucoes.tag_configure("atencao", foreground="#E67E22", font=("Segoe UI", 10, "bold"))

        self.caixa_instrucoes.insert("end", "1) MANTENHA ABERTO: Pode minimizar esta janela, mas não feche.\n", "ok")
        self.caixa_instrucoes.insert("end", "2) PDF: O nome do arquivo precisa começar com \"emulti\".\n", "atencao")
        self.caixa_instrucoes.insert("end", "3) PROCESSAMENTO EM LOTE: Pode colocar vários PDFs emulti de uma vez.\n", "ok")
        self.caixa_instrucoes.insert("end", "4) PLANILHA: O nome da planilha precisa ser \"Planilha Emulti 2026.xlsx\".\n", "atencao")
        self.caixa_instrucoes.insert("end", "5) PLANILHA FECHADA: NUNCA deixe a planilha aberta ao confirmar atualização.\n", "alerta")
        self.caixa_instrucoes.insert("end", "6) RECUPERAÇÃO: Pegue a penúltima cópia na pasta Copias em caso de erro.\n", "atencao")
        # Instrução alterada para refletir os 20 minutos
        self.caixa_instrucoes.insert("end", "7) LIMPEZA: Processados apagam em 24h. Rejeitados apagam em 20 min.\n", "ok")
        self.caixa_instrucoes.configure(state="disabled")

        frame_status = tk.Frame(self.root, bg="#FFFFFF", pady=10, padx=20, relief="groove", bd=1)
        frame_status.pack(fill="x", padx=20, pady=(0, 15))
        self.var_ultima_acao = tk.StringVar(value="🚀 Sistema iniciado. Aguardando relatórios...")
        tk.Label(frame_status, textvariable=self.var_ultima_acao, bg="#FFFFFF", fg="#34495E", font=("Segoe UI", 11)).pack(side="left")

        self.botao_abrir_planilha = tk.Button(frame_status, text="📂 Abrir planilha", command=self.abrir_planilha, bg="#27AE60", fg="#FFFFFF", relief="flat", padx=12, pady=6, font=("Segoe UI", 10, "bold"))
        self.botao_abrir_planilha.pack(side="right")

        frame_tabela = tk.Frame(self.root, bg="#F4F6F9")
        frame_tabela.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        colunas = ("arquivo", "nome", "mes", "categoria", "qtd_doc", "qtd_plan", "status")
        self.tabela = ttk.Treeview(frame_tabela, columns=colunas, show="headings")

        for col, nome in zip(colunas, ["Arquivo", "Nome", "Mês", "Tipo", "Qtd.Documento", "Qtd.Planilha", "Status na Planilha"]):
            self.tabela.heading(col, text=nome)

        self.tabela.column("arquivo", width=180, anchor="w")
        self.tabela.column("nome", width=300, anchor="w")
        self.tabela.column("mes", width=100, anchor="center")
        self.tabela.column("categoria", width=120, anchor="center")
        self.tabela.column("qtd_doc", width=110, anchor="center")
        self.tabela.column("qtd_plan", width=110, anchor="center")
        self.tabela.column("status", width=210, anchor="center")

        self.tabela.tag_configure('sucesso', background='#E8F8F5', foreground='#117864')
        self.tabela.tag_configure('duplicado', background='#FEF9E7', foreground='#9A7D0A')
        self.tabela.tag_configure('bloqueado', background='#FDEDEC', foreground='#B03A2E')

        scrollbar_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_y.pack(side="right", fill="y")
        self.tabela.pack(side="left", fill="both", expand=True)

        self.verificar_fila()
        self.iniciar_monitoramento()

    def abrir_planilha(self):
        if not os.path.exists(PLANILHA_2026):
            messagebox.showerror("Planilha não encontrada", f"Não encontrei a planilha em:\n{PLANILHA_2026}")
            return
        try:
            if sys.platform.startswith("win"): os.startfile(PLANILHA_2026)
            elif sys.platform == "darwin": subprocess.Popen(["open", PLANILHA_2026])
            else: subprocess.Popen(["xdg-open", PLANILHA_2026])
            self.var_ultima_acao.set("📂 Planilha aberta. Feche antes de lançar outro PDF.")
        except Exception as e:
            messagebox.showerror("Erro ao abrir planilha", f"Não foi possível abrir a planilha:\n{e}")

    def inserir_log(self, mensagem, cor_ignorada=None):
        self.var_ultima_acao.set(mensagem)

    def verificar_fila(self):
        try:
            while not self.fila_eventos.empty():
                evento = self.fila_eventos.get_nowait()
                if evento["acao"] == "PROCESSAR_LOTE":
                    self.solicitar_confirmacao_e_atualizar_lote(evento)
        except queue.Empty: pass
        finally: self.root.after(200, self.verificar_fila)

    def solicitar_confirmacao_e_atualizar_lote(self, evento):
        itens = evento.get("itens", [])
        total_pdfs = evento.get("total_pdfs", len(itens))
        rejeitados = evento.get("rejeitados", [])

        for item in self.tabela.get_children(): self.tabela.delete(item)

        bloqueados_por_pdf = {}
        total_linhas = 0
        itens_validos = []

        for item in itens:
            arquivo = item.get("arquivo") or os.path.basename(item["caminho"])

            if item["mes"] == "MÊS NÃO IDENTIFICADO":
                self._limpar_e_arquivar_pdf(item["caminho"], motivo="MES_NAO_IDENTIFICADO")
                rejeitados.append(arquivo)
                continue

            tipo = item["tipo"]
            mes = item["mes"]
            prof = item["profissionais"]
            dupl = item["duplicados"]
            prof_planilha = item["profissionais_planilha"]

            bloqueados_pdf = []
            for nome, valor in prof.items():
                status_visual = "OK - ATUALIZAR"
                tag_cor = 'sucesso'
                qtd_planilha_visual = 0

                if not prof_planilha or nome not in prof_planilha:
                    status_visual = "IGNORADO - FORA DA PLANILHA"
                    tag_cor = 'bloqueado'
                    bloqueados_pdf.append(nome)
                else:
                    qtd_planilha_visual = prof_planilha.get(nome, 0)
                    if nome in dupl:
                        status_visual = "SOMAR VALORES"
                        tag_cor = 'duplicado'

                self.tabela.insert("", "end", values=(arquivo, nome, mes, tipo, valor, qtd_planilha_visual, status_visual), tags=(tag_cor,))
                total_linhas += 1

            if bloqueados_pdf:
                bloqueados_por_pdf[arquivo] = bloqueados_pdf

            if len(bloqueados_pdf) == len(prof):
                self._limpar_e_arquivar_pdf(item["caminho"], motivo="SEM_PROFISSIONAL_AUTORIZADO")
                rejeitados.append(arquivo)
            else:
                itens_validos.append(item)

        # MENSAGEM AOS ARQUIVOS REJEITADOS E PRAZO DE 20 MINUTOS
        if rejeitados:
            msg_rejeitados = "⚠️ Os seguintes arquivos apresentaram problemas e foram REJEITADOS:\n\n- "
            msg_rejeitados += "\n- ".join(rejeitados)
            msg_rejeitados += "\n\nEles foram movidos para a pasta 'Rejeitados' e serão apagados automaticamente em 20 minutos."
            messagebox.showwarning("Aviso - Arquivos Rejeitados", msg_rejeitados)

        if not itens_validos:
            if itens:
                self.var_ultima_acao.set("⛔ Nenhum PDF do lote possuía profissionais válidos na planilha.")
            return

        if total_pdfs > 1:
            mensagem_lote = f"Foram detectados {total_pdfs} PDF(s).\nPDF(s) válido(s) para conferência: {len(itens_validos)}"
            self.var_ultima_acao.set(f"📦 Lote detectado. Confira a tabela antes de atualizar.")
            messagebox.showinfo("Processamento em lote", mensagem_lote)
        else:
            self.var_ultima_acao.set("📊 PDF detectado. Confira a tabela antes de atualizar.")

        aberta, _ = planilha_esta_aberta()
        if aberta:
            messagebox.showerror("Planilha aberta", "Feche a planilha antes de lançar os dados.")
            self.var_ultima_acao.set("⛔ Planilha aberta. Feche a planilha e lance novamente os PDFs.")
            for item in itens_validos: self._limpar_e_arquivar_pdf(item["caminho"], motivo="PLANILHA_ABERTA")
            return

        total_profissionais = sum(len(item["profissionais"]) for item in itens_validos)
        total_bloqueados = sum(len(bloqueados_por_pdf.get(item.get("arquivo") or os.path.basename(item["caminho"]), [])) for item in itens_validos)
        total_autorizados = total_profissionais - total_bloqueados

        msg = f"Deseja atualizar a planilha agora?\n\nAutorizados: {total_autorizados}\nLembre-se: A PLANILHA DEVE ESTAR FECHADA!"
        if not messagebox.askokcancel("Confirmação", msg):
            self.var_ultima_acao.set("⚠️ Operação cancelada. PDFs movidos para Rejeitados.")
            for item in itens_validos: self._limpar_e_arquivar_pdf(item["caminho"], motivo="CANCELADO")
            return

        aberta, _ = planilha_esta_aberta()
        if aberta:
            messagebox.showerror("Planilha aberta", "A planilha foi aberta antes do lançamento.")
            for item in itens_validos: self._limpar_e_arquivar_pdf(item["caminho"], motivo="PLANILHA_ABERTA")
            return

        # =========================================================
        # BACKUP EXECUTADO UMA ÚNICA VEZ PARA O LOTE INTEIRO AQUI
        # =========================================================
        try:
            criar_backup_rotativo(self)
        except Exception as e:
            messagebox.showerror("Erro Crítico de Backup", f"Falha ao criar backup: {e}\n\nA atualização do lote inteira foi cancelada por segurança.")
            self.var_ultima_acao.set("⛔ Falha no backup. Operação cancelada.")
            for item in itens_validos: self._limpar_e_arquivar_pdf(item["caminho"], motivo="FALHA_BACKUP")
            return

        self.var_ultima_acao.set(f"⏳ Processando lote com {len(itens_validos)} PDF(s)... aguarde.")
        sucessos = 0
        falhas = []

        # Inicia a atualização iterando sobre o lote com a segurança do backup já gerado
        for item in itens_validos:
            ok = self.pipeline.carregar_item(item)
            if ok:
                sucessos += 1
                self._limpar_e_arquivar_pdf(item["caminho"], motivo="PROCESSADO")
            else:
                falhas.append(item.get("arquivo") or os.path.basename(item["caminho"]))
                self._limpar_e_arquivar_pdf(item["caminho"], motivo="NAO_PROCESSADO")

        if sucessos:
            # MENSAGEM FINAL EXATA SOLICITADA
            msg_final = "Processo concluido, abra a planilha para ver os dados atualizados"
            self.var_ultima_acao.set(f"✅ {msg_final} ({sucessos}/{len(itens_validos)} PDFs)")
            messagebox.showinfo("Sucesso", msg_final)

            if falhas:
                messagebox.showwarning("Avisos", f"{len(falhas)} PDF(s) não foram lançados:\n" + "\n".join(falhas[:20]))
        else:
            self.var_ultima_acao.set("⚠️ Nenhum PDF do lote foi lançado.")

    def _limpar_e_arquivar_pdf(self, caminho_arquivo, motivo="PROCESSADO"):
        try:
            if not os.path.exists(caminho_arquivo): return
            nome_original = os.path.basename(caminho_arquivo)
            nome_sem_ext, ext = os.path.splitext(nome_original)
            sufixo = motivo if motivo else "PROCESSADO"
            nome_novo = f"{nome_sem_ext}_{sufixo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

            pasta_destino = PASTA_PROCESSADOS if motivo == "PROCESSADO" else PASTA_REJEITADOS
            caminho_destino = os.path.join(pasta_destino, nome_novo)

            shutil.move(caminho_arquivo, caminho_destino)

            # Carimba a hora EXATA atual no arquivo movido para corrigir o bug da data antiga do servidor web
            os.utime(caminho_destino, None)

            limpar_arquivos_antigos(PASTA_PROCESSADOS, horas=HORAS_LIMPEZA_PDFS, app=None)
            limpar_arquivos_antigos(PASTA_REJEITADOS, minutos=MINUTOS_LIMPEZA_REJEITADOS, app=None)
        except Exception as e:
            self.var_ultima_acao.set(f"Erro ao mover arquivo: {e}")

    def iniciar_monitoramento(self):
        limpar_arquivos_antigos(PASTA_PROCESSADOS, horas=HORAS_LIMPEZA_PDFS, app=None)
        limpar_arquivos_antigos(PASTA_REJEITADOS, minutos=MINUTOS_LIMPEZA_REJEITADOS, app=None)
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