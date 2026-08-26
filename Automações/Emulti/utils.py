import os
import time
import unicodedata
import re
from copy import copy

def padronizar_nome(nome):
    if nome is None:
        return ""
    nome_str = str(nome)
    nome_sem_acentos = ''.join(
        c for c in unicodedata.normalize('NFD', nome_str)
        if unicodedata.category(c) != 'Mn'
    )
    nome_maiusculo = nome_sem_acentos.upper()
    nome_maiusculo = re.sub(r"[^A-Z0-9\s]", " ", nome_maiusculo)
    return ' '.join(nome_maiusculo.split()).strip()

def _tokens_nome(nome):
    conectores = {"DE", "DA", "DAS", "DO", "DOS", "E"}
    return [t for t in padronizar_nome(nome).split() if t not in conectores]

def copiar_estilo(celula_origem, celula_destino):
    if celula_origem.has_style:
        celula_destino.font = copy(celula_origem.font)
        celula_destino.border = copy(celula_origem.border)
        celula_destino.fill = copy(celula_origem.fill)
        celula_destino.number_format = copy(celula_origem.number_format)
        celula_destino.protection = copy(celula_origem.protection)
        celula_destino.alignment = copy(celula_origem.alignment)

def esperar_download_concluir(caminho_arquivo, timeout=60):
    tempo_decorrido = 0
    tamanho_anterior = -1
    while tempo_decorrido < timeout:
        try:
            if not os.path.exists(caminho_arquivo):
                return False
            tamanho_atual = os.path.getsize(caminho_arquivo)
            if tamanho_atual > 0 and tamanho_atual == tamanho_anterior:
                with open(caminho_arquivo, 'rb'):
                    pass
                return True
            tamanho_anterior = tamanho_atual
        except (OSError, PermissionError):
            pass
        time.sleep(1)
        tempo_decorrido += 1
    return False

# Adicionado suporte para contar limpeza por minutos
def limpar_arquivos_antigos(pasta, horas=24, minutos=None, app=None):
    try:
        agora = time.time()
        # Se passar os minutos, converte pra segundos, se não, usa as horas em segundos
        limite_segundos = (minutos * 60) if minutos is not None else (horas * 3600)

        for arquivo in os.listdir(pasta):
            caminho_completo = os.path.join(pasta, arquivo)
            if os.path.isfile(caminho_completo):
                tempo_arquivo = os.path.getmtime(caminho_completo)
                if (agora - tempo_arquivo) > limite_segundos:
                    os.remove(caminho_completo)
    except Exception as e:
        if app:
            app.inserir_log(f"Erro ao limpar: {e}", "VERMELHO")