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
        # Ignora arquivos temporários e downloads incompletos
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
                    self.app.inserir_log("Arquivo movido para a pasta de produção.", "VERDE")
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
                self.app.inserir_log("ERRO: Tempo limite excedido. Arquivo ignorado.", "VERMELHO")
                self.arquivos_em_processamento.discard(caminho_arquivo)
                return

            try:
                # 1. Extraímos os dados do PDF
                tipo, mes, profissionais, duplicados = ler_relatorio_pdf(caminho_arquivo)
                
                # 2. Lemos a coluna exata da planilha
                profissionais_planilha = obter_profissionais_planilha(tipo, mes)
                
                evento = {
                    "acao": "PROCESSAR_PDF",
                    "caminho": caminho_arquivo, "tipo": tipo, "mes": mes,
                    "profissionais": profissionais, "duplicados": duplicados,
                    "profissionais_planilha": profissionais_planilha
                }
                self.app.fila_eventos.put(evento)
            except Exception as e:
                # Se cair aqui, a validação estrutural do PDF falhou (ou houve erro de leitura).
                self.app.inserir_log(f"Erro crítico: {e}", "VERMELHO")
                
                # --- CORREÇÃO: ELIMINAÇÃO DE CARGA INVÁLIDA (Payload Destruction) ---
                try:
                    if os.path.exists(caminho_arquivo):
                        os.remove(caminho_arquivo)
                        self.app.inserir_log("🗑️ Arquivo inválido apagado automaticamente da pasta.", "AMARELO")
                except Exception as ex:
                    self.app.inserir_log(f"Falha ao tentar apagar o arquivo inválido: {ex}", "VERMELHO")
                # --------------------------------------------------------------------
                
            finally:
                # Libera o arquivo do controle de processamento, independentemente de sucesso ou erro
                self.arquivos_em_processamento.discard(caminho_arquivo)

    def on_created(self, event):
        if not event.is_directory: self.processar_arquivo(event.src_path)
    def on_moved(self, event):
        if not event.is_directory: self.processar_arquivo(event.dest_path)