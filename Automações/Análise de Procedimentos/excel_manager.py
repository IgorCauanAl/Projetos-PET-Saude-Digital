import os
import re 
from config import Cores
from utils import registrar_log, normalizar_texto

def mapear_ine_para_abas(wb):
    """
    Versão corrigida: Mapeia todos os números de 6 a 7 dígitos encontrados.
    Removido o 'break' para garantir que tanto CNES quanto INE apontem para a aba correta.
    """
    mapa = {}
    # Expressão regular para encontrar sequências de 6 ou 7 números isolados
    padrao_ine = re.compile(r'(?<!\d)(\d{6,7})(?!\d)')

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        
        # Busca no cabeçalho (Linha 1-60, Coluna 1-15)
        for row in range(1, 61):
            for col in range(1, 16):
                valor = ws.cell(row=row, column=col).value
                if valor is not None:
                    valor_str = str(valor).strip()
                    # Encontra todas as ocorrências na célula
                    matches = padrao_ine.findall(valor_str)
                    for ine in matches:
                        mapa[ine] = sheet_name
                
    return mapa

def atualizar_planilha_sisab_memoria(dados_por_ine, mes_atual, nome_arquivo, wb, mapa_abas):
    mes_busca = normalizar_texto(mes_atual)
    sistema_busca = "PEC" if isinstance(dados_por_ine, dict) else "SISAB"
    
    lista_processamento = []

    # 1. PREPARAÇÃO DOS DADOS SISAB (Excel/CSV)
    if isinstance(dados_por_ine, list):
        lista_processamento = dados_por_ine
    
    # 2. PREPARAÇÃO DOS DADOS PEC (PDF)
    else:
        nome_arquivo_puro = normalizar_texto(os.path.splitext(nome_arquivo)[0])
        ine_encontrado = None
        
        for ine, aba in mapa_abas.items():
            aba_limpa = normalizar_texto(aba)
            if aba_limpa in nome_arquivo_puro or nome_arquivo_puro in aba_limpa:
                ine_encontrado = ine
                break
        
        if ine_encontrado:
            for indicador, valor in dados_por_ine.items():
                lista_processamento.append({
                    'ine': ine_encontrado, 
                    'valor': valor, 
                    'indicadores': [indicador], 
                    'nome': nome_arquivo_puro
                })
        else:
            registrar_log(f"❌ Não vinculei o PDF: {nome_arquivo}", Cores.VERMELHO)
            for ind, val in dados_por_ine.items():
                # Envia '-' no valor da planilha para casos de falha
                print(f"UI_RESULTADO|FALHA_INE|None|{nome_arquivo}|{ind}|{val}|-|{mes_atual}")
            return

    # 3. LAÇO DE GRAVAÇÃO NA PLANILHA
    for item in lista_processamento:
        ine = str(item.get('ine', '')).replace(".0", "").strip()
        nome_posto_sisab = item.get('nome', '') 
        valor_novo = item.get('valor', 0)
        indicadores_alvo = item.get('indicadores', [])

        sheet_name = None

        if ine in mapa_abas:
            sheet_name = mapa_abas[ine]
        else:
            nome_sisab_limpo = normalizar_texto(nome_posto_sisab)
            palavras_posto = set([p for p in nome_sisab_limpo.split() if len(p) > 2])
            
            for nome_aba in wb.sheetnames:
                aba_limpa = normalizar_texto(nome_aba)
                
                if len(aba_limpa) >= 3 and len(nome_sisab_limpo) >= 3:
                    if aba_limpa in nome_sisab_limpo or nome_sisab_limpo in aba_limpa:
                        sheet_name = nome_aba
                        mapa_abas[ine] = sheet_name 
                        break
                
                palavras_aba = set([p for p in aba_limpa.split() if len(p) > 2])
                intersecao = palavras_posto.intersection(palavras_aba)
                
                if len(intersecao) >= 2: 
                    sheet_name = nome_aba
                    mapa_abas[ine] = sheet_name
                    break

        if not sheet_name:
            for ind_alvo in indicadores_alvo:
                print(f"UI_RESULTADO|FALHA_INE|{ine} ({nome_posto_sisab})|DESCONHECIDO|{ind_alvo}|{valor_novo}|-|{mes_atual}")
            continue
        
        ws = wb[sheet_name]

        col_mes_inicio = None
        col_final = None
        linha_mes_encontrada = 0
        
        for row_busca in range(1, 31): 
            for col in range(2, 50):
                celula = ws.cell(row=row_busca, column=col).value
                if celula:
                    celula_norm = normalizar_texto(celula)
                    if mes_busca in celula_norm:
                        col_mes_inicio = col
                        linha_mes_encontrada = row_busca
                        break
            if col_mes_inicio: break
        
        if not col_mes_inicio:
            for ind_alvo in indicadores_alvo:
                print(f"UI_RESULTADO|FALHA_MES|{ine}|{sheet_name}|{ind_alvo}|{valor_novo}|-|{mes_atual}")
            continue

        for col in range(col_mes_inicio, col_mes_inicio + 10):
            achou_sistema = False
            for offset in range(1, 6): 
                val_sis = ws.cell(row=linha_mes_encontrada + offset, column=col).value
                if val_sis:
                    val_norm = normalizar_texto(val_sis)
                    if (sistema_busca == "SISAB" and "SISAB" in val_norm) or \
                       (sistema_busca == "PEC" and ("ESUS" in val_norm or "PEC" in val_norm)):
                        col_final = col
                        achou_sistema = True
                        break
            if achou_sistema: break
        
        if not col_final:
            col_final = col_mes_inicio
            registrar_log(f"⚠️ Palavra '{sistema_busca}' não encontrada. Usando coluna padrão {col_final}.", Cores.AMARELO)

        mapa_linhas = {}
        for r in range(1, 300): 
            txt = ws.cell(row=r, column=1).value
            if txt: mapa_linhas[normalizar_texto(txt)] = r

        for indicador_alvo in indicadores_unicos_da_lista(indicadores_alvo):
            alvo_limpo = normalizar_texto(indicador_alvo)
            linha_destino = None

            if alvo_limpo in mapa_linhas:
                linha_destino = mapa_linhas[alvo_limpo]
            else:
                for chave_planilha, num_linha in mapa_linhas.items():
                    if chave_planilha in alvo_limpo or alvo_limpo in chave_planilha:
                        linha_destino = num_linha
                        break
                    
                    palavras_alvo = [p for p in alvo_limpo.split() if len(p) > 3]
                    if palavras_alvo and all(p in chave_planilha for p in palavras_alvo):
                        linha_destino = num_linha
                        break
            
            if linha_destino:
                # LÓGICA DE SOMAGEM:
                valor_atual_celula = ws.cell(row=linha_destino, column=col_final).value
                
                try:
                    v_atual = float(valor_atual_celula) if valor_atual_celula is not None else 0.0
                except (ValueError, TypeError):
                    v_atual = 0.0
                
                try:
                    v_novo = float(valor_novo)
                except (ValueError, TypeError):
                    v_novo = 0.0

                resultado_soma = v_atual + v_novo
                
                # Grava o resultado somado
                ws.cell(row=linha_destino, column=col_final, value=resultado_soma)
                # Envia Valor Doc (v_novo) e Valor Planilha (resultado_soma)
                print(f"UI_RESULTADO|SUCESSO|{ine}|{sheet_name}|{indicador_alvo}|{valor_novo}|{resultado_soma}|{mes_atual}")
            else:
                print(f"UI_RESULTADO|FALHA_LINHA|{ine}|{sheet_name}|{indicador_alvo}|{valor_novo}|-|{mes_atual}")

def indicadores_unicos_da_lista(lista):
    """Remove indicadores duplicados preservando a ordem da lista."""
    vistos = set()
    return [x for x in lista if not (x in vistos or vistos.add(x))]