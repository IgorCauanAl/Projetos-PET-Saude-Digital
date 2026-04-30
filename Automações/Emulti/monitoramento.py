import os
import shutil
from watchdog.events import FileSystemEventHandler
from config import PASTA_MONITORADA
from extracao import esperar_download_concluir, ler_relatorio_pdf, obter_profissionais_planilha

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
                caminho_destino = os.path.join(PASTA_MONITORADA, os.path.basename(caminho_arquivo))
                try:
                    shutil.move(caminho_arquivo, caminho_destino)
                    self.app.inserir_log("ROTEADOR: Arquivo movido para a pasta de produção.", "VERDE")
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
        self.arquivos_em_processamento = set()

    def processar_arquivo(self, caminho_arquivo):
        nome_arquivo = os.path.basename(caminho_arquivo).lower()
        if nome_arquivo.startswith("~") or nome_arquivo.startswith("."): return
            
        if caminho_arquivo.lower().endswith(".pdf"):
            if caminho_arquivo in self.arquivos_em_processamento: return
            self.arquivos_em_processamento.add(caminho_arquivo)
            self.app.inserir_log("PROCESSADOR: PDF detectado na pasta local. Lendo...", "AMARELO")
            
            if not esperar_download_concluir(caminho_arquivo):
                self.app.inserir_log("ERRO: Tempo limite excedido.", "VERMELHO")
                self.arquivos_em_processamento.discard(caminho_arquivo)
                return

            try:
                tipo, mes, profissionais, duplicados = ler_relatorio_pdf(caminho_arquivo)
                profissionais_planilha = obter_profissionais_planilha()
                
                evento = {
                    "acao": "PROCESSAR_PDF",
                    "caminho": caminho_arquivo, "tipo": tipo, "mes": mes,
                    "profissionais": profissionais, "duplicados": duplicados,
                    "profissionais_planilha": profissionais_planilha
                }
                self.app.fila_eventos.put(evento)
            except Exception as e:
                self.app.inserir_log(f"Erro crítico: {e}", "VERMELHO")
            finally:
                self.arquivos_em_processamento.discard(caminho_arquivo)

    def on_created(self, event):
        if not event.is_directory: self.processar_arquivo(event.src_path)
    def on_moved(self, event):
        if not event.is_directory: self.processar_arquivo(event.dest_path)
