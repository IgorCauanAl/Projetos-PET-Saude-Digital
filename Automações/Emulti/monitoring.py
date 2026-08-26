import os
import shutil
import threading
from datetime import datetime
from watchdog.events import FileSystemEventHandler

from config import PASTA_MONITORADA, PASTA_REJEITADOS, HORAS_LIMPEZA_PDFS, MINUTOS_LIMPEZA_REJEITADOS
from utils import esperar_download_concluir, limpar_arquivos_antigos
from extract import titulo_pdf_valido
from orchestrator import PipelineETL

TEMPO_ESPERA_LOTE_SEGUNDOS = 3

def mover_para_rejeitados(caminho_arquivo, motivo, app=None):
    try:
        os.makedirs(PASTA_REJEITADOS, exist_ok=True)
        nome_original = os.path.basename(caminho_arquivo)
        nome_sem_ext, ext = os.path.splitext(nome_original)
        nome_novo = f"{nome_sem_ext}_REJEITADO_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        destino = os.path.join(PASTA_REJEITADOS, nome_novo)
        if os.path.exists(caminho_arquivo):
            shutil.move(caminho_arquivo, destino)

            # Carimba a hora EXATA atual para corrigir o bug de pastas vazias imediatamente
            os.utime(destino, None)

        limpar_arquivos_antigos(PASTA_REJEITADOS, minutos=MINUTOS_LIMPEZA_REJEITADOS, app=None)

        if app:
            app.inserir_log(f"PDF rejeitado e removido da automação: {motivo}", "VERMELHO")
    except Exception as e:
        if app:
            app.inserir_log(f"Falha ao remover PDF rejeitado: {e}", "VERMELHO")


class RoteadorDownloads(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
        self.arquivos_em_processamento = set()

    def processar_arquivo(self, caminho_arquivo):
        nome_arquivo = os.path.basename(caminho_arquivo).lower()
        if nome_arquivo.startswith("~") or nome_arquivo.startswith(".") or nome_arquivo.endswith(".crdownload") or nome_arquivo.endswith(".tmp"):
            return

        if nome_arquivo.startswith("emulti") and nome_arquivo.endswith(".pdf"):
            if caminho_arquivo in self.arquivos_em_processamento: return
            self.arquivos_em_processamento.add(caminho_arquivo)

            self.app.inserir_log(f"ROTEADOR: Arquivo '{nome_arquivo}' detectado em Downloads!", "AZUL")
            if esperar_download_concluir(caminho_arquivo):
                valido, motivo = titulo_pdf_valido(caminho_arquivo)
                if not valido:
                    mover_para_rejeitados(caminho_arquivo, motivo, self.app)
                    self.arquivos_em_processamento.discard(caminho_arquivo)
                    return

                caminho_destino = os.path.join(PASTA_MONITORADA, os.path.basename(caminho_arquivo))
                try:
                    shutil.move(caminho_arquivo, caminho_destino)
                    self.app.inserir_log("PDF válido movido para a pasta de produção.", "VERDE")
                except Exception as e:
                    self.app.inserir_log(f"Erro crítico ao mover: {e}", "VERMELHO")
            self.arquivos_em_processamento.discard(caminho_arquivo)

    def on_created(self, event):
        if not event.is_directory: self.processar_arquivo(event.src_path)

    def on_moved(self, event):
        if not event.is_directory: self.processar_arquivo(event.dest_path)


class MonitorRelatorios(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
        self.pipeline = PipelineETL(app)
        self.arquivos_em_processamento = set()
        self.arquivos_pendentes = {}
        self.lock_lote = threading.Lock()
        self.timer_lote = None

    def _arquivo_deve_ser_ignorado(self, caminho_arquivo):
        nome_arquivo = os.path.basename(caminho_arquivo).lower()
        return (nome_arquivo.startswith("~") or nome_arquivo.startswith(".") or nome_arquivo.endswith(".crdownload") or nome_arquivo.endswith(".tmp"))

    def _agendar_processamento_lote(self):
        with self.lock_lote:
            if self.timer_lote and self.timer_lote.is_alive():
                self.timer_lote.cancel()
            self.timer_lote = threading.Timer(TEMPO_ESPERA_LOTE_SEGUNDOS, self.processar_lote_pendente)
            self.timer_lote.daemon = True
            self.timer_lote.start()

    def processar_arquivo(self, caminho_arquivo):
        if self._arquivo_deve_ser_ignorado(caminho_arquivo) or not caminho_arquivo.lower().endswith(".pdf"):
            return

        if caminho_arquivo in self.arquivos_em_processamento: return
        self.arquivos_em_processamento.add(caminho_arquivo)

        try:
            self.app.inserir_log("PROCESSADOR: PDF detectado. Aguardando possíveis PDFs do mesmo lote...", "AMARELO")

            if not esperar_download_concluir(caminho_arquivo):
                self.app.inserir_log("ERRO: Tempo limite excedido. PDF removido da automação.", "VERMELHO")
                mover_para_rejeitados(caminho_arquivo, "download incompleto ou travado", self.app)
                return

            valido, motivo = titulo_pdf_valido(caminho_arquivo)
            if not valido:
                mover_para_rejeitados(caminho_arquivo, motivo, self.app)
                return

            with self.lock_lote:
                self.arquivos_pendentes[caminho_arquivo] = datetime.now()
                quantidade = len(self.arquivos_pendentes)

            if quantidade > 1:
                self.app.inserir_log(f"📦 {quantidade} PDFs detectados.", "AZUL")

            self._agendar_processamento_lote()

        finally:
            self.arquivos_em_processamento.discard(caminho_arquivo)

    def processar_lote_pendente(self):
        with self.lock_lote:
            caminhos = list(self.arquivos_pendentes.keys())
            self.arquivos_pendentes.clear()

        if not caminhos: return

        total_detectado = len(caminhos)
        itens = []
        rejeitados = []

        if total_detectado > 1:
            self.app.inserir_log(f"📦 Processando lote com {total_detectado} PDF(s).", "AZUL")
        else:
            self.app.inserir_log("PROCESSADOR: lendo PDF detectado...", "AMARELO")

        for caminho_arquivo in caminhos:
            try:
                if not os.path.exists(caminho_arquivo): continue

                valido, motivo = titulo_pdf_valido(caminho_arquivo)
                if not valido:
                    mover_para_rejeitados(caminho_arquivo, motivo, self.app)
                    rejeitados.append(os.path.basename(caminho_arquivo))
                    continue

                registros = self.pipeline.extrair_transformar([caminho_arquivo])
                if not registros:
                    rejeitados.append(os.path.basename(caminho_arquivo))
                    continue

                registro = registros[0]
                itens.append({
                    "caminho": registro.caminho,
                    "arquivo": registro.arquivo,
                    "tipo": registro.tipo,
                    "mes": registro.mes,
                    "profissionais": registro.profissionais,
                    "duplicados": registro.duplicados,
                    "profissionais_planilha": registro.profissionais_planilha,
                })
            except Exception as e:
                mover_para_rejeitados(caminho_arquivo, str(e), self.app)
                rejeitados.append(os.path.basename(caminho_arquivo))

        if not itens:
            self.app.inserir_log("Nenhum PDF válido ficou disponível para lançamento.", "VERMELHO")
            return

        evento = {
            "acao": "PROCESSAR_LOTE",
            "itens": itens,
            "total_pdfs": total_detectado,
            "rejeitados": rejeitados,
        }
        self.app.fila_eventos.put(evento)

    def on_created(self, event):
        if not event.is_directory: self.processar_arquivo(event.src_path)

    def on_moved(self, event):
        if not event.is_directory: self.processar_arquivo(event.dest_path)