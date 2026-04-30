import os
import time
import pdfplumber
import pandas as pd
from copy import copy
from openpyxl import load_workbook
from openpyxl.formula.translate import Translator
import unicodedata
from config import PLANILHA_2026

def padronizar_nome(nome):
    if not nome: return ""
    nome_str = str(nome)
    nome_sem_acentos = ''.join(c for c in unicodedata.normalize('NFD', nome_str) if unicodedata.category(c) != 'Mn')
    nome_maiusculo = nome_sem_acentos.upper()
    return ' '.join(nome_maiusculo.split()).strip()

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
            if not os.path.exists(caminho_arquivo): return False
            tamanho_atual = os.path.getsize(caminho_arquivo)
            if tamanho_atual > 0 and tamanho_atual == tamanho_anterior:
                with open(caminho_arquivo, 'rb'): pass
                return True
            tamanho_anterior = tamanho_atual
        except (OSError, PermissionError):
            pass 
        time.sleep(1) 
        tempo_decorrido += 1
    return False 

def limpar_arquivos_antigos(pasta, horas=24, app=None):
    try:
        agora = time.time()
        for arquivo in os.listdir(pasta):
            caminho_completo = os.path.join(pasta, arquivo)
            if os.path.isfile(caminho_completo):
                tempo_arquivo = os.path.getmtime(caminho_completo)
                if (agora - tempo_arquivo) > (horas * 3600):
                    os.remove(caminho_completo)
                    if app: app.inserir_log(f"Arquivo expirado removido: {arquivo}", "AMARELO")
    except Exception as e:
        if app: app.inserir_log(f"Erro ao limpar: {e}", "VERMELHO")

def obter_profissionais_planilha():
    existentes = set()
    if not os.path.exists(PLANILHA_2026): return existentes
    try:
        wb = load_workbook(PLANILHA_2026, read_only=True, data_only=True)
        ws = wb.active
        for row in ws.iter_rows(min_row=13, max_col=1):
            cell_value = row[0].value
            if not cell_value: continue
            nome_padronizado = padronizar_nome(str(cell_value))
            if "TOTAL" in nome_padronizado: break 
            if nome_padronizado: existentes.add(nome_padronizado)
        wb.close()
    except Exception: pass
    return existentes

def ler_relatorio_pdf(caminho_pdf):
    texto_total = ""
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto_total += pagina.extract_text() + "\n"
    
    linhas = texto_total.splitlines()
    periodo_linha = next((l for l in linhas if "Período:" in l), "")
    mes_atual = "MÊS NÃO IDENTIFICADO"
    if periodo_linha:
        try:
            data_inicio = periodo_linha.split("Período:")[1].split("a")[0].strip()
            mes_num = pd.to_datetime(data_inicio, dayfirst=True, errors='coerce').month
            meses = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
            if mes_num: mes_atual = meses[mes_num - 1]
        except Exception: pass

    tipo = "COLETIVO" if "Relatório de atividade coletiva" in texto_total else ("INDIVIDUAL" if "Relatório de atendimento individual" in texto_total else "DESCONHECIDO")

    profissionais, nomes_duplicados = {}, set()
    processando = False 
    termos_ignorar = ["IMPRESSO EM", "PAG.", "PAGINA", "RELATORIO"]
    
    for linha in linhas:
        linha_pad = padronizar_nome(linha)
        if "TOTAL GERAL" in linha_pad: break 
        if "PROFISSIONAL" in linha_pad:
            processando = True
            continue 
        if "TOTAL" in linha_pad or any(t in linha_pad for t in termos_ignorar): continue

        if processando and any(c.isdigit() for c in linha.strip().split()[-1:]):
            partes = linha.strip().rsplit(" ", 1)
            if len(partes) == 2:
                nome, valor_texto = partes
                try:
                    if nome.strip().endswith(valor_texto): nome = nome.strip()[:-len(valor_texto)].strip()
                    valor_numerico = int(valor_texto)
                    nome_pad = padronizar_nome(nome)
                    if nome_pad: 
                        if nome_pad in profissionais:
                            profissionais[nome_pad] += valor_numerico
                            nomes_duplicados.add(nome_pad)
                        else:
                            profissionais[nome_pad] = valor_numerico
                except ValueError: continue
    return tipo, mes_atual, profissionais, nomes_duplicados

def atualizar_planilha(tipo, mes_atual, profissionais, app):
    try:
        wb = load_workbook(PLANILHA_2026)
        ws = wb.active
        col_mes_inicio = next((cell.column for cell in ws[11] if cell.value and padronizar_nome(str(cell.value)) == mes_atual), None)
        
        if not col_mes_inicio:
            app.inserir_log(f"ERRO: Mês '{mes_atual}' não encontrado.", "VERMELHO")
            wb.close()
            return False
        
        coluna_alvo = None
        if tipo == "INDIVIDUAL" and padronizar_nome(str(ws.cell(row=12, column=col_mes_inicio).value)) == "INDIVIDUAL":
            coluna_alvo = col_mes_inicio
        elif tipo == "COLETIVO" and padronizar_nome(str(ws.cell(row=12, column=col_mes_inicio + 1).value)) == "COLETIVO":
            coluna_alvo = col_mes_inicio + 1
        
        if not coluna_alvo:
            app.inserir_log(f"ERRO: Coluna '{tipo}' não encontrada.", "VERMELHO")
            wb.close()
            return False

        atualizados = 0
        novos_inseridos = [] 
        linha_insercao = next((row[0].row for row in ws.iter_rows(min_row=13, max_col=1) if "TOTAL" in padronizar_nome(str(row[0].value))), ws.max_row + 1)

        for row in ws.iter_rows(min_row=13, max_row=linha_insercao-1, max_col=1): 
            cell_nome = row[0]
            if not cell_nome.value: continue
            nome_planilha = padronizar_nome(str(cell_nome.value))
            if nome_planilha in profissionais:
                celula_alvo = ws.cell(row=cell_nome.row, column=coluna_alvo)
                valor_atual = celula_alvo.value if isinstance(celula_alvo.value, (int, float)) else 0
                celula_alvo.value = valor_atual + profissionais[nome_planilha]
                atualizados += 1
                del profissionais[nome_planilha] 

        if profissionais:
            app.inserir_log("Inserindo novos profissionais na linha de baixo...", "CIANO")
            for nome_novo, valor_novo in profissionais.items():
                ws.insert_rows(linha_insercao)
                ws.cell(row=linha_insercao, column=1, value=nome_novo)
                ws.cell(row=linha_insercao, column=coluna_alvo, value=valor_novo)
                
                linha_ref = linha_insercao - 1
                for col in range(1, ws.max_column + 1):
                    cell_ref = ws.cell(row=linha_ref, column=col)
                    cell_nova = ws.cell(row=linha_insercao, column=col)
                    copiar_estilo(cell_ref, cell_nova)
                    if cell_ref.data_type == 'f' and not cell_nova.value:
                        try: cell_nova.value = Translator(cell_ref.value, origin=cell_ref.coordinate).translate_formula(cell_nova.coordinate)
                        except: pass 
                novos_inseridos.append(f"{nome_novo} -> {valor_novo}")
                linha_insercao += 1 
                atualizados += 1

        wb.save(PLANILHA_2026)
        wb.close()
        app.inserir_log("SUCESSO! ATUALIZAÇÃO CONCLUÍDA.", "VERDE")
        app.inserir_log(f"Total processado: {atualizados} registros.", "BRANCO")
        if novos_inseridos:
            app.inserir_log("PROFISSIONAIS ADICIONADOS:", "CIANO")
            for item in novos_inseridos: app.inserir_log(f"   {item}", "VERDE")
        return True 
    except PermissionError:
        app.inserir_log("ERRO: Planilha aberta. Feche e tente novamente.", "VERMELHO")
        return False
    except Exception as e:
        app.inserir_log(f"Erro GERAL: {e}", "VERMELHO")
        return False
