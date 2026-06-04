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

from config import PASTA_PROCESSADOS, PASTA_REJEITADOS, PASTA_MONITORADA, PASTA_DOWNLOADS, PLANILHA_2026, HORAS_LIMPEZA_PDFS
from extracao import atualizar_planilha, limpar_arquivos_antigos, planilha_esta_aberta
from monitoramento import RoteadorDownloads, MonitorRelatorios


class AplicacaoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Produção 2026 - Profissional Cátia")
        self.root.geometry("1200x840")
        self.root.configure(bg="#F4F6F9")
        self.fila_eventos = queue.Queue()

        frame_topo = tk.Frame(self.root, bg="#FFFFFF", pady=15, padx=20, relief="groove", bd=1)
        frame_topo.pack(fill="x", padx=20, pady=15)

        tk.Label(frame_topo, text="👋 Olá, Cátia!", bg="#FFFFFF", fg="#2C3E50",
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(frame_topo, text="Sua assistente está monitorando os relatórios 'emulti' para você.",
                 bg="#FFFFFF", fg="#7F8C8D", font=("Segoe UI", 11)).pack(anchor="w")

        self.caixa_instrucoes = tk.Text(frame_topo, bg="#FFFFFF", font=("Segoe UI", 10),
                                        bd=0, highlightthickness=0, height=12, wrap="word")
        self.caixa_instrucoes.pack(fill="x", pady=5)

        self.caixa_instrucoes.tag_configure("padrao", foreground="#7F8C8D")
        self.caixa_instrucoes.tag_configure("alerta", foreground="#E74C3C", font=("Segoe UI", 10, "bold"))
        self.caixa_instrucoes.tag_configure("ok", foreground="#27AE60", font=("Segoe UI", 10, "bold"))
        self.caixa_instrucoes.tag_configure("atencao", foreground="#E67E22", font=("Segoe UI", 10, "bold"))

        self.caixa_instrucoes.insert("end", "1) MANTENHA ABERTO: ", "padrao")
        self.caixa_instrucoes.insert("end", "Pode minimizar esta janela, mas não feche.\n", "ok")

        self.caixa_instrucoes.insert("end", "2) PDF: ", "padrao")
        self.caixa_instrucoes.insert("end", "O nome do arquivo precisa começar com \"emulti\". Pode colocar o PDF na pasta Downloads ou diretamente na pasta da automação.\n", "atencao")

        self.caixa_instrucoes.insert("end", "3) PROCESSAMENTO EM LOTE: ", "padrao")
        self.caixa_instrucoes.insert("end", "Pode colocar vários PDFs emulti de uma vez; o sistema processa pela quantidade colocada.\n", "ok")

        self.caixa_instrucoes.insert("end", "4) PLANILHA: ", "padrao")
        self.caixa_instrucoes.insert("end", "O nome da planilha precisa ser \"Planilha Emulti\" + o ano correspondente. Exemplo: Planilha Emulti 2026.xlsx.\n", "atencao")

        self.caixa_instrucoes.insert("end", "5) PLANILHA FECHADA: ", "padrao")
        self.caixa_instrucoes.insert("end", "NUNCA deixe a planilha aberta", "alerta")
        self.caixa_instrucoes.insert("end", " ao confirmar atualização.\n", "padrao")

        self.caixa_instrucoes.insert("end", "6) RECUPERAÇÃO: ", "padrao")
        self.caixa_instrucoes.insert("end", "Se acontecer algum problema, pegue a penúltima cópia na pasta Copias e renomeie para \"Planilha Emulti\" + o ano correspondente.\n", "atencao")

        self.caixa_instrucoes.insert("end", "7) LIMPEZA: ", "padrao")
        self.caixa_instrucoes.insert("end", "As pastas Processados e Rejeitados apagam automaticamente arquivos com mais de 24 horas.\n", "ok")
        self.caixa_instrucoes.configure(state="disabled")

        frame_status = tk.Frame(self.root, bg="#FFFFFF", pady=10, padx=20, relief="groove", bd=1)
        frame_status.pack(fill="x", padx=20, pady=(0, 15))
        self.var_ultima_acao = tk.StringVar(value="🚀 Sistema iniciado. Aguardando relatórios...")
        tk.Label(frame_status, textvariable=self.var_ultima_acao, bg="#FFFFFF",
                 fg="#34495E", font=("Segoe UI", 11)).pack(side="left")

        self.botao_abrir_planilha = tk.Button(
            frame_status,
            text="📂 Abrir planilha",
            command=self.abrir_planilha,
            bg="#27AE60",
            fg="#FFFFFF",
            activebackground="#1E8449",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 10, "bold")
        )
        self.botao_abrir_planilha.pack(side="right")

        frame_tabela = tk.Frame(self.root, bg="#F4F6F9")
        frame_tabela.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        colunas = ("arquivo", "nome", "mes", "categoria", "qtd_doc", "qtd_plan", "status")
        self.tabela = ttk.Treeview(frame_tabela, columns=colunas, show="headings")

        self.tabela.heading("arquivo", text="Arquivo")
        self.tabela.heading("nome", text="Nome")
        self.tabela.heading("mes", text="Mês")
        self.tabela.heading("categoria", text="Tipo")
        self.tabela.heading("qtd_doc", text="Qtd.Documento")
        self.tabela.heading("qtd_plan", text="Qtd.Planilha")
        self.tabela.heading("status", text="Status na Planilha")

        self.tabela.column("arquivo", width=180, anchor="w")
        self.tabela.column("nome", width=300, anchor="w")
        self.tabela.column("mes", width=100, anchor="center")
        self.tabela.column("categoria", width=120, anchor="center")
        self.tabela.column("qtd_doc", width=110, anchor="center")
        self.tabela.column("qtd_plan", width=110, anchor="center")
        self.tabela.column("status", width=210, anchor="center")

        self.tabela.tag_configure('novo', background='#EBF5FB', foreground='#2E86C1')
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
            if sys.platform.startswith("win"):
                os.startfile(PLANILHA_2026)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", PLANILHA_2026])
            else:
                subprocess.Popen(["xdg-open", PLANILHA_2026])
            self.var_ultima_acao.set("📂 Planilha aberta. Feche antes de lançar outro PDF.")
        except Exception as e:
            messagebox.showerror("Erro ao abrir planilha", f"Não foi possível abrir a planilha:\n{e}")

    def inserir_log(self, mensagem, cor_ignorada=None):
        self.var_ultima_acao.set(mensagem)

    def verificar_fila(self):
        try:
            while not self.fila_eventos.empty():
                evento = self.fila_eventos.get_nowait()
                if evento["acao"] == "PROCESSAR_PDF":
                    self.solicitar_confirmacao_e_atualizar(evento)
                elif evento["acao"] == "PROCESSAR_LOTE":
                    self.solicitar_confirmacao_e_atualizar_lote(evento)
        except queue.Empty:
            pass
        finally:
            self.root.after(200, self.verificar_fila)

    def solicitar_confirmacao_e_atualizar(self, evento):
        # Compatibilidade com eventos antigos de PDF único.
        evento_lote = {
            "acao": "PROCESSAR_LOTE",
            "itens": [{
                "caminho": evento["caminho"],
                "arquivo": os.path.basename(evento["caminho"]),
                "tipo": evento["tipo"],
                "mes": evento["mes"],
                "profissionais": evento["profissionais"],
                "duplicados": evento["duplicados"],
                "profissionais_planilha": evento["profissionais_planilha"],
            }],
            "total_pdfs": 1,
            "rejeitados": [],
        }
        self.solicitar_confirmacao_e_atualizar_lote(evento_lote)

    def solicitar_confirmacao_e_atualizar_lote(self, evento):
        itens = evento.get("itens", [])
        total_pdfs = evento.get("total_pdfs", len(itens))
        rejeitados = evento.get("rejeitados", [])

        for item in self.tabela.get_children():
            self.tabela.delete(item)

        bloqueados_por_pdf = {}
        total_linhas = 0

        for item in itens:
            arquivo = item.get("arquivo") or os.path.basename(item["caminho"])
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

                self.tabela.insert(
                    "", "end",
                    values=(arquivo, nome, mes, tipo, valor, qtd_planilha_visual, status_visual),
                    tags=(tag_cor,)
                )
                total_linhas += 1

            if bloqueados_pdf:
                bloqueados_por_pdf[arquivo] = bloqueados_pdf

        if total_pdfs > 1:
            mensagem_lote = (
                f"Foram detectados {total_pdfs} PDF(s).\n\n"
                f"O processo será feito conforme a quantidade colocada de PDF.\n"
                f"PDF(s) válido(s) para conferência: {len(itens)}"
            )
            if rejeitados:
                mensagem_lote += f"\nPDF(s) rejeitado(s): {len(rejeitados)}"
            messagebox.showinfo("Processamento em lote", mensagem_lote)
            self.var_ultima_acao.set(f"📦 Lote com {total_pdfs} PDF(s) detectado. Confira a tabela antes de atualizar.")
        else:
            self.var_ultima_acao.set("📊 PDF detectado. Confira a tabela antes de atualizar.")

        meses_invalidos = [item.get("arquivo", os.path.basename(item["caminho"])) for item in itens if item["mes"] == "MÊS NÃO IDENTIFICADO"]
        if meses_invalidos:
            messagebox.showerror(
                "Mês não identificado",
                "O sistema não conseguiu identificar o mês de um ou mais PDFs.\n\n"
                + "\n".join(meses_invalidos)
                + "\n\nEsses PDFs serão retirados da automação. Lance novamente após corrigir."
            )
            for item in itens:
                motivo = "MES_NAO_IDENTIFICADO" if item["mes"] == "MÊS NÃO IDENTIFICADO" else "NAO_PROCESSADO_POR_LOTE_INVALIDO"
                self._limpar_e_arquivar_pdf(item["caminho"], motivo=motivo)
            return

        aberta, _ = planilha_esta_aberta()
        if aberta:
            messagebox.showerror(
                "Planilha aberta",
                "Feche a planilha antes de lançar os dados.\n\n"
                "Este lote será retirado da automação. Depois de fechar a planilha, coloque novamente os PDFs na pasta."
            )
            self.var_ultima_acao.set("⛔ Planilha aberta. Feche a planilha e lance novamente os PDFs.")
            for item in itens:
                self._limpar_e_arquivar_pdf(item["caminho"], motivo="PLANILHA_ABERTA")
            return

        total_profissionais = sum(len(item["profissionais"]) for item in itens)
        total_bloqueados = sum(len(v) for v in bloqueados_por_pdf.values())
        total_autorizados = total_profissionais - total_bloqueados

        if total_autorizados <= 0:
            detalhes = []
            for arquivo, nomes in bloqueados_por_pdf.items():
                detalhes.append(f"{arquivo}: " + ", ".join(nomes))
            messagebox.showerror(
                "Nenhum profissional autorizado",
                "Nenhum profissional dos PDFs foi encontrado na planilha da gestora.\n\n"
                + "\n".join(detalhes[:20])
                + "\n\nNenhum dado será gravado no Excel."
            )
            self.var_ultima_acao.set("⛔ Nenhum profissional do lote existe na planilha da gestora.")
            for item in itens:
                self._limpar_e_arquivar_pdf(item["caminho"], motivo="SEM_PROFISSIONAL_AUTORIZADO")
            return

        if total_bloqueados > 0:
            detalhes = []
            for arquivo, nomes in bloqueados_por_pdf.items():
                detalhes.append(f"{arquivo}: " + ", ".join(nomes))
            msg_ignorar = (
                "O lote possui profissional(is) fora da planilha da gestora.\n\n"
                "Eles serão IGNORADOS, mas os profissionais encontrados na planilha serão lançados normalmente.\n\n"
                f"Autorizados: {total_autorizados}\nIgnorados: {total_bloqueados}\n\n"
                "Ignorados:\n" + "\n".join(detalhes[:20])
                + "\n\nDeseja continuar lançando somente os profissionais autorizados?"
            )
            if not messagebox.askokcancel("Ignorar profissionais fora da planilha?", msg_ignorar):
                self.var_ultima_acao.set("⚠️ Operação cancelada. Nenhum dado foi gravado.")
                for item in itens:
                    self._limpar_e_arquivar_pdf(item["caminho"], motivo="CANCELADO")
                return

        msg = (
            f"Deseja atualizar a planilha agora?\n\n"
            f"PDF(s) no lote: {len(itens)}\n"
            f"Linhas exibidas na conferência: {total_linhas}\n"
            f"Profissionais autorizados para lançamento: {total_autorizados}\n\n"
            "Lembre-se: A PLANILHA DEVE ESTAR FECHADA!"
        )
        if not messagebox.askokcancel("Confirmação de leitura em lote", msg):
            self.var_ultima_acao.set("⚠️ Operação cancelada. PDFs movidos para Processados.")
            for item in itens:
                self._limpar_e_arquivar_pdf(item["caminho"], motivo="CANCELADO")
            return

        # Segunda checagem imediatamente antes de gravar.
        aberta, _ = planilha_esta_aberta()
        if aberta:
            messagebox.showerror(
                "Planilha aberta",
                "A planilha foi aberta antes do lançamento.\n\n"
                "Nenhum dado foi gravado. Coloque novamente os PDFs na pasta depois de fechar a planilha."
            )
            self.var_ultima_acao.set("⛔ Planilha aberta. Feche a planilha e lance novamente os PDFs.")
            for item in itens:
                self._limpar_e_arquivar_pdf(item["caminho"], motivo="PLANILHA_ABERTA")
            return

        self.var_ultima_acao.set(f"⏳ Processando lote com {len(itens)} PDF(s)... aguarde.")
        sucessos = 0
        falhas = []
        for item in itens:
            ok = atualizar_planilha(item["tipo"], item["mes"], item["profissionais"], self)
            if ok:
                sucessos += 1
                self._limpar_e_arquivar_pdf(item["caminho"], motivo="PROCESSADO")
            else:
                falhas.append(item.get("arquivo") or os.path.basename(item["caminho"]))
                self._limpar_e_arquivar_pdf(item["caminho"], motivo="NAO_PROCESSADO")

        if sucessos:
            self.var_ultima_acao.set(f"✅ Lote concluído: {sucessos}/{len(itens)} PDF(s) processado(s). A planilha pode ser aberta.")
            if falhas:
                messagebox.showwarning(
                    "Lote concluído com avisos",
                    f"{sucessos} PDF(s) foram processados.\n"
                    f"{len(falhas)} PDF(s) não foram lançados e devem ser reenviados se necessário:\n\n"
                    + "\n".join(falhas[:20])
                )
        else:
            self.var_ultima_acao.set("⚠️ Nenhum PDF do lote foi lançado. Verifique os avisos e lance novamente, se necessário.")

    def _limpar_e_arquivar_pdf(self, caminho_arquivo, motivo="PROCESSADO"):
        try:
            if not os.path.exists(caminho_arquivo):
                return
            nome_original = os.path.basename(caminho_arquivo)
            nome_sem_ext, ext = os.path.splitext(nome_original)
            sufixo = motivo if motivo else "PROCESSADO"
            nome_novo = f"{nome_sem_ext}_{sufixo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            shutil.move(caminho_arquivo, os.path.join(PASTA_PROCESSADOS, nome_novo))
            limpar_arquivos_antigos(PASTA_PROCESSADOS, horas=HORAS_LIMPEZA_PDFS, app=None)
            limpar_arquivos_antigos(PASTA_REJEITADOS, horas=HORAS_LIMPEZA_PDFS, app=None)
        except Exception as e:
            self.var_ultima_acao.set(f"Erro ao mover arquivo: {e}")

    def iniciar_monitoramento(self):
        limpar_arquivos_antigos(PASTA_PROCESSADOS, horas=HORAS_LIMPEZA_PDFS, app=None)
        limpar_arquivos_antigos(PASTA_REJEITADOS, horas=HORAS_LIMPEZA_PDFS, app=None)
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
