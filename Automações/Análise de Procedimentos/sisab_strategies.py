import os
import re
import pandas as pd
import unicodedata
from config import Cores, MAPA_CONDICOES_SISAB, MAPA_PROCEDIMENTOS_SISAB
from utils import registrar_log
from excel_manager import atualizar_planilha_sisab_memoria

# --- FUNÇÃO AUXILIAR NOVA (MELHORADA) ---
def extrair_apenas_ine_limpo(valor_bruto):
    """
    Remove letras, símbolos e zeros à esquerda, garantindo o INE puro.
    Ex: 'INE: 0000213861' -> '213861'
    """
    if pd.isna(valor_bruto): return ""
    valor_str = str(valor_bruto).strip()
    
    # Se terminar com .0 (padrão de float no pandas), removemos
    if valor_str.endswith('.0'): 
        valor_str = valor_str[:-2]
    
    # Regex busca o primeiro bloco numérico que encontrar na célula
    match = re.search(r'(\d+)', valor_str)
    
    if match:
        numero_encontrado = match.group(1)
        # O int() remove os zeros à esquerda magicamente. O str() devolve como texto.
        numero_limpo = str(int(numero_encontrado)) 
        return numero_limpo
        
    return valor_str
# ----------------------------------------

class EstrategiaExtracao:
    """Interface base para todas as estratégias de extração."""
    def extrair(self):
        raise NotImplementedError("O método extrair() deve ser implementado nas classes filhas.")

class SisabVisitaDomiciliarStrategy(EstrategiaExtracao):
    def __init__(self, df_dados, coluna_identificadora):
        self.df_dados = df_dados
        self.coluna_identificadora = coluna_identificadora
        
    def extrair(self):
        coluna_valor = None
        for col in self.df_dados.columns:
            if "visita" in str(col).lower():
                coluna_valor = col
                break
                
        if not coluna_valor: 
            registrar_log("❌ Coluna de Visitas não encontrada.", Cores.VERMELHO)
            return []
            
        col_nome = next((c for c in self.df_dados.columns if any(x in str(c).upper() for x in ["EQUIPE", "SIGLA", "NOME"])), None)
        dados_extraidos = []
        
        registros = self.df_dados.to_dict('records')
        
        for row in registros:
            if pd.isna(row.get(self.coluna_identificadora)): continue
            
            # MODIFICAÇÃO: Uso da função limpadora de INE com Regex
            cnes_ine = extrair_apenas_ine_limpo(row.get(self.coluna_identificadora))
            nome_posto = str(row.get(col_nome, "")).strip() if col_nome and pd.notna(row.get(col_nome)) else "Unidade não identificada"

            valor_bruto = row.get(coluna_valor)
            if pd.notna(valor_bruto):
                try:
                    valor = float(valor_bruto)
                    if 0 < valor < 10: valor = valor * 1000 
                    valor = int(valor) 
                except: 
                    valor = 0
                    
                if valor > 0:
                    dados_extraidos.append({
                        'ine': cnes_ine, 
                        'nome': nome_posto,
                        'valor': valor, 
                        'indicadores': ["VISITA DE ACS"] 
                    })
        return dados_extraidos


class SisabGenericoStrategy(EstrategiaExtracao):
    def __init__(self, df_dados, coluna_identificadora, colunas_valor, mapa_em_uso, categorias_ativas, coluna_profissional=None):
        self.df_dados = df_dados
        self.coluna_identificadora = coluna_identificadora
        self.colunas_valor = colunas_valor
        self.mapa_em_uso = mapa_em_uso
        self.categorias_ativas = categorias_ativas
        self.coluna_profissional = coluna_profissional

    def extrair(self):
        dados_agrupados = {} 
        col_nome = next((c for c in self.df_dados.columns if any(x in str(c).upper() for x in ["EQUIPE", "SIGLA", "NOME"])), None)

        mapa_correcao_ine = {
            "1780905": "213934", "1784285": "213969", "1784803": "214019", "1798820": "213942", 
            "1803352": "213985", "1804421": "213926", "1807803": "214078", "2073935": "213950", 
            "2073943": "214027", "2073951": "214108", "2073978": "214043", "2073986": "214094", 
            "2077094": "213861", "2095521": "213853", "2095548": "213993", "2095556": "214116", 
            "2095564": "213896", "2095572": "213918", "2188503": "214000", "2243393": "214086", 
            "2309815": "213888", "2309904": "2333554", "2504391": "214035", "2504413": "2502151",
        }

        registros = self.df_dados.to_dict('records')

        for row in registros:
            if pd.isna(row.get(self.coluna_identificadora)): continue
            
            # MODIFICAÇÃO: Uso da função limpadora de INE com Regex
            cnes_ine = extrair_apenas_ine_limpo(row.get(self.coluna_identificadora))
            nome_posto = str(row.get(col_nome, "")).strip() if col_nome and pd.notna(row.get(col_nome)) else "Unidade não identificada"

            cnes_ine_original = cnes_ine 

            if cnes_ine in mapa_correcao_ine:
                cnes_ine = mapa_correcao_ine[cnes_ine]
                registrar_log(f"🔄 UNIFICAÇÃO: Produção da ESB ({cnes_ine_original}) somada à ESF ({cnes_ine}).", Cores.AMARELO)

            valor_total = sum(float(row.get(col, 0)) if pd.notna(row.get(col)) and str(row.get(col)).replace('.','',1).isdigit() else 0 for col in self.colunas_valor if col in row)
            
            if valor_total > 0:
                indicadores_da_linha = []
                
                if self.coluna_profissional and pd.notna(row.get(self.coluna_profissional)):
                    prof_row = str(row.get(self.coluna_profissional, "")).lower()
                    if "médic" in prof_row or "medico" in prof_row:
                        if "Médico" in self.mapa_em_uso: indicadores_da_linha.append(self.mapa_em_uso["Médico"])
                    elif "enferm" in prof_row:
                        if "Enfermeiro" in self.mapa_em_uso: indicadores_da_linha.append(self.mapa_em_uso["Enfermeiro"])
                    elif "odont" in prof_row or "cirurgi" in prof_row or "dentista" in prof_row:
                        if "Odonto" in self.mapa_em_uso: indicadores_da_linha.append(self.mapa_em_uso["Odonto"])
                else:
                    for cat in self.categorias_ativas:
                        if cat in self.mapa_em_uso: indicadores_da_linha.append(self.mapa_em_uso[cat])
                
                if indicadores_da_linha:
                    indicadores_tupla = tuple(sorted(list(set(indicadores_da_linha))))
                    chave_agrupamento = (cnes_ine, nome_posto, indicadores_tupla)

                    if chave_agrupamento in dados_agrupados:
                        dados_agrupados[chave_agrupamento] += valor_total
                    else:
                        dados_agrupados[chave_agrupamento] = valor_total

        dados_extraidos = []
        for (ine, nome, indicadores), valor in dados_agrupados.items():
            dados_extraidos.append({
                'ine': ine, 
                'nome': nome,
                'valor': int(valor), 
                'indicadores': list(indicadores)
            })
            
        return dados_extraidos


class SisabSomaUltimasColunasStrategy(EstrategiaExtracao):
    def __init__(self, df_dados, coluna_identificadora, mapa_em_uso, nome_procedimento="Procedimento"):
        self.df_dados = df_dados
        self.coluna_identificadora = coluna_identificadora
        self.mapa_em_uso = mapa_em_uso
        self.nome_procedimento = nome_procedimento
        self.colunas_valor = self.df_dados.columns[-2:]

    def extrair(self):
        dados_agrupados = {} 
        col_nome = next((c for c in self.df_dados.columns if any(x in str(c).upper() for x in ["EQUIPE", "SIGLA", "NOME"])), None)

        registrar_log(f"📋 ATENÇÃO: Realizando somagem para {self.nome_procedimento}. Colunas lidas: {list(self.colunas_valor)}", Cores.VERDE)

        registros = self.df_dados.to_dict('records')

        for row in registros:
            if pd.isna(row.get(self.coluna_identificadora)): continue
            
            # MODIFICAÇÃO: Uso da função limpadora de INE com Regex
            cnes_ine = extrair_apenas_ine_limpo(row.get(self.coluna_identificadora))
            nome_posto = str(row.get(col_nome, "")).strip() if col_nome and pd.notna(row.get(col_nome)) else "Unidade não identificada"

            valor_total = sum(float(row.get(col, 0)) if pd.notna(row.get(col)) and str(row.get(col)).replace('.','',1).isdigit() else 0 for col in self.colunas_valor if col in row)
            
            if valor_total > 0:
                indicadores_da_linha = [val for key, val in self.mapa_em_uso.items()]
                
                if indicadores_da_linha:
                    indicadores_tupla = tuple(sorted(list(set(indicadores_da_linha))))
                    chave_agrupamento = (cnes_ine, nome_posto, indicadores_tupla)

                    if chave_agrupamento in dados_agrupados:
                        dados_agrupados[chave_agrupamento] += valor_total
                    else:
                        dados_agrupados[chave_agrupamento] = valor_total

        dados_extraidos = []
        for (ine, nome, indicadores), valor in dados_agrupados.items():
            dados_extraidos.append({
                'ine': ine, 
                'nome': nome,
                'valor': int(valor), 
                'indicadores': list(indicadores)
            })
            
        return dados_extraidos


class ContextoSisab:
    def __init__(self, caminho_arquivo, wb, mapa_abas):
        self.caminho = caminho_arquivo
        self.nome_arquivo = os.path.basename(caminho_arquivo)
        self.wb = wb
        self.mapa_abas = mapa_abas

    def executar(self):
        print(f"\n{Cores.AZUL}📊 PROCESSANDO ARQUIVO SISAB: {self.nome_arquivo}{Cores.RESET}")
        try:
            if self.caminho.lower().endswith('.csv'):
                try:
                    with open(self.caminho, 'r', encoding='utf-8', errors='ignore') as f:
                        primeira_linha = f.readline()
                    separador = ';' if ';' in primeira_linha else ','
                except:
                    separador = ';'

                try:
                    df_completo = pd.read_csv(self.caminho, sep=separador, encoding='utf-8', header=None)
                except UnicodeDecodeError:
                    df_completo = pd.read_csv(self.caminho, sep=separador, encoding='latin1', header=None)
            else:
                df_completo = pd.read_excel(self.caminho, header=None)

            df_meta = df_completo.head(30)
            texto_meta = " ".join(df_meta.astype(str).stack().tolist())

            mes_atual = self._extrair_mes(texto_meta)
            if mes_atual == "MÊS NÃO IDENTIFICADO":
                registrar_log(f"❌ Mês não identificado.", Cores.VERMELHO)
                return

            estrategia, df_dados = self._selecionar_estrategia(df_completo, df_meta, texto_meta)
            if not estrategia: return
            
            dados = estrategia.extrair()

            if dados:
                for d in dados:
                    ine_limpo = str(d['ine']).replace('\n', '').replace('\r', '').strip()
                    nome_limpo = str(d.get('nome', 'Unidade não identificada')).replace('\n', '').replace('\r', '').strip()
                    valor_limpo = str(d['valor']).replace('\n', '').replace('\r', '').strip()
                    indicadores_limpos = [str(i).replace('\n', ' ').replace('\r', '').strip() for i in d['indicadores']]
                    indicadores_texto = " + ".join(indicadores_limpos)
                    
                    print(f"DADO_EXTRAIDO|{ine_limpo}|{nome_limpo}|{indicadores_texto}|{valor_limpo}|{mes_atual}", flush=True)                
                
                atualizar_planilha_sisab_memoria(dados, mes_atual, self.nome_arquivo, self.wb, self.mapa_abas)
            else:
                registrar_log("⚠️ Nenhum dado válido encontrado para extração no documento.", Cores.AMARELO)
        except Exception as e:
            registrar_log(f"❌ Erro crítico em SISAB '{self.nome_arquivo}': {e}", Cores.VERMELHO)

    def _extrair_mes(self, texto_meta):
        mes_map = {"JAN": "JANEIRO", "FEV": "FEVEREIRO", "MAR": "MARÇO", "ABR": "ABRIL", "MAI": "MAIO", "JUN": "JUNHO", "JUL": "JULHO", "AGO": "AGOSTO", "SET": "SETEMBRO", "OUT": "OUTUBRO", "NOV": "NOVEMBRO", "DEZ": "DEZEMBRO"}
        match_mes = re.search(r"Competência:\s*([A-Z]{3})/(\d{4})", texto_meta, re.IGNORECASE)
        if not match_mes:
            match_mes = re.search(r"Sigla da equipe.*?([A-Z]{3}/\d{4})", texto_meta, re.IGNORECASE | re.DOTALL)
            if not match_mes: match_mes = re.search(r"([A-Z]{3}/\d{4})", texto_meta, re.IGNORECASE)
        if match_mes:
            data_str = match_mes.group(1)
            mes_abrev = data_str.split('/')[0].upper() if '/' in data_str else data_str.upper()
            mes = mes_map.get(mes_abrev, "MÊS NÃO IDENTIFICADO")
            registrar_log(f"📅 Mês identificado: {mes}", Cores.CIANO)
            return mes
        return "MÊS NÃO IDENTIFICADO"

    def _selecionar_estrategia(self, df_completo, df_meta, texto_meta):
        texto_lower = str(texto_meta).lower()
        nome_lower = str(self.nome_arquivo).lower()
        
        is_visita = False
        if "visita domiciliar" in nome_lower or "visitadomiciliar" in nome_lower:
            is_visita = True
        elif "visita domiciliar" in texto_lower and ("agente comunitário" in texto_lower or "acs" in texto_lower):
            is_visita = True

        if is_visita:
            linha_cabecalho = self._encontrar_linha_flexivel(df_meta, ["CNES", "Visita"])
            df_dados = self._isolar_df(df_completo, linha_cabecalho)
            col_id = self._encontrar_col_identificadora(df_dados)
            if not col_id: return None, None
            return SisabVisitaDomiciliarStrategy(df_dados, col_id), df_dados

        if "sifilis" in texto_lower or "sífilis" in texto_lower or "0214010074" in texto_lower or "sifilis" in nome_lower:
             mapa_sifilis = {"Geral": "TESTE RÁPIDO SÍFILIS"} 
             linha_cabecalho = self._encontrar_linha_flexivel(df_meta, ["CNES", "Equipe"])
             df_dados = self._isolar_df(df_completo, linha_cabecalho)
             col_id = self._encontrar_col_identificadora(df_dados)
             if not col_id: return None, None
             return SisabSomaUltimasColunasStrategy(df_dados, col_id, mapa_sifilis, "Sífilis (Normal + Gestante)"), df_dados

        if "hiv" in texto_lower or "0214010058" in texto_lower or "hiv" in nome_lower:
             mapa_hiv = {"Geral": "TESTE RÁPIDO HIV"} 
             linha_cabecalho = self._encontrar_linha_flexivel(df_meta, ["CNES", "Equipe"])
             df_dados = self._isolar_df(df_completo, linha_cabecalho)
             col_id = self._encontrar_col_identificadora(df_dados)
             if not col_id: return None, None
             return SisabSomaUltimasColunasStrategy(df_dados, col_id, mapa_hiv, "HIV (Normal + Gestante)"), df_dados

        if "curativo" in texto_lower or "0301100284" in texto_lower or "curativo" in nome_lower:
             mapa_curativo = {"Geral": "CURATIVOS"} 
             linha_cabecalho = self._encontrar_linha_flexivel(df_meta, ["CNES", "Equipe"])
             df_dados = self._isolar_df(df_completo, linha_cabecalho)
             col_id = self._encontrar_col_identificadora(df_dados)
             if not col_id: return None, None
             return SisabSomaUltimasColunasStrategy(df_dados, col_id, mapa_curativo, "Curativos (Simples + Especial)"), df_dados

        mapa_em_uso, tipo_arquivo = self._identificar_tipo_generico(texto_meta)
        if not mapa_em_uso: 
            return None, None
            
        tem_medico = bool(re.search(r"Categoria Profissional:.*Médico", texto_meta, re.IGNORECASE))
        tem_enfermeiro = bool(re.search(r"Categoria Profissional:.*Enfermeiro", texto_meta, re.IGNORECASE))
        tem_odonto = bool(re.search(r"Categoria Profissional:.*(Odont[óo]logo|Cirurgi[ãa]o[\s\-]?dentista|Dentista)", texto_meta, re.IGNORECASE))
        
        if not tem_medico and not tem_enfermeiro and not tem_odonto:
            if "medico" in nome_lower or "médico" in nome_lower: tem_medico = True
            if "enferm" in nome_lower: tem_enfermeiro = True
            if "odonto" in nome_lower or "dentista" in nome_lower or "cirurgi" in nome_lower: tem_odonto = True

        categorias_ativas = []
        if tem_medico: categorias_ativas.append("Médico")
        if tem_enfermeiro: categorias_ativas.append("Enfermeiro")
        if tem_odonto: categorias_ativas.append("Odonto")
        if not categorias_ativas: categorias_ativas = ["Médico", "Enfermeiro", "Odonto"] 

        linha_cabecalho = self._encontrar_linha_generica(df_meta, tipo_arquivo)
        df_dados = self._isolar_df(df_completo, linha_cabecalho)
        col_id = self._encontrar_col_identificadora(df_dados)
        if not col_id: return None, None

        coluna_profissional = None
        for col in df_dados.columns:
            col_str = str(col).strip().lower()
            if "categoria" in col_str and "profissional" in col_str:
                coluna_profissional = col
                break

        if len(categorias_ativas) > 1 and tipo_arquivo not in ['atividade_coletiva', 'cadastro']:
            destinos_unicos = set(mapa_em_uso.get(c) for c in categorias_ativas if mapa_em_uso.get(c))
            if len(destinos_unicos) > 1:
                if not coluna_profissional: return None, None

        colunas_valor = self._encontrar_colunas_valor(df_dados, tipo_arquivo)

        estrategia = SisabGenericoStrategy(
            df_dados, col_id, colunas_valor, mapa_em_uso, categorias_ativas, coluna_profissional
        )
        return estrategia, df_dados

    def _identificar_tipo_generico(self, texto_meta):
        def limpar_texto(txt):
            txt_str = str(txt).lower()
            return ''.join(c for c in unicodedata.normalize('NFD', txt_str) if unicodedata.category(c) != 'Mn')

        texto_limpo = limpar_texto(texto_meta)
        nome_arq_limpo = limpar_texto(self.nome_arquivo)

        if "colo uterino" in texto_limpo or "col. de cito" in texto_limpo:
             return {"Médico": "Preventivo Ginecologico", "Enfermeiro": "Preventivo Ginecologico"}, 'procedimento_sigtap'

        if "04 - domicilio" in texto_limpo or "local de atendimento: 04" in texto_limpo:
             return {"Médico": "ATEND. DOMICILIAR (Médico)", "Enfermeiro": "ATEND. DOMICILIAR (Enfermeiro)", "Odonto": "ATEND. DOMICILIAR (Odonto)"}, 'atendimento_domiciliar'

        if "tipologia do municipio" in texto_limpo:
             return {"Médico": "ANÁLISE DA SITUAÇÃO CADASTRAL", "Enfermeiro": "ANÁLISE DA SITUAÇÃO CADASTRAL", "Odonto": "ANÁLISE DA SITUAÇÃO CADASTRAL"}, 'cadastro'
        
        if "qt atividade coletiva" in texto_limpo or "numero de participantes" in texto_limpo or "atividade coletiva" in nome_arq_limpo:
             fallback_mapa = {"Médico": "ATIVIDADE COLETIVA", "Enfermeiro": "ATIVIDADE COLETIVA", "Odonto": "ATIVIDADE COLETIVA"}
             mapa = MAPA_PROCEDIMENTOS_SISAB.get("Atividade Coletiva", fallback_mapa)
             return mapa, 'atividade_coletiva'
        
        if "afericao de pressao arterial" in texto_limpo or "0301100039" in texto_meta:
             return MAPA_PROCEDIMENTOS_SISAB.get("Afericao De Pressao", {"Médico": "AFERIÇÃO DE PRESSÃO", "Enfermeiro": "AFERIÇÃO DE PRESSÃO"}), 'procedimento_sigtap'

        if "0201020050" in texto_meta or "coleta de sangue" in texto_limpo:
             return MAPA_PROCEDIMENTOS_SISAB.get("Teste do pezinho", {"Médico": "TESTE DO PEZINHO", "Enfermeiro": "TESTE DO PEZINHO"}), 'procedimento_sigtap'

        match_condicao = re.search(r"Probl/\s*Condição Avaliada:\s*([A-Za-zÀ-ÖØ-öø-ÿ\s\.\-]+)", texto_meta, re.IGNORECASE)

        if match_condicao:
            condicao_interna = limpar_texto(match_condicao.group(1).strip())
            for chave, mapa_cat in MAPA_CONDICOES_SISAB.items():
                if limpar_texto(chave) in condicao_interna:
                    return mapa_cat, f'condicao_{chave}'

        for chave, mapa_cat in MAPA_CONDICOES_SISAB.items():
            if limpar_texto(chave) in nome_arq_limpo:
                return mapa_cat, 'condicao'
        
        for chave, mapa_cat in MAPA_PROCEDIMENTOS_SISAB.items():
            if limpar_texto(chave) in nome_arq_limpo:
                return mapa_cat, 'procedimento'
                
        return None, None

    def _encontrar_linha_flexivel(self, df_meta, termos):
        termos_lower = [t.lower() for t in termos]
        for i, row in df_meta.iterrows():
            row_str = " ".join([str(x).lower() for x in row.values])
            if all(t in row_str for t in termos_lower): return i
        return 9

    def _encontrar_linha_generica(self, df_meta, tipo_arquivo):
        termos_cab = ["Municipio", "Equipe - INE", "CNES", "Tipo Equipe", "Sigla da equipe", "INE", "Uf", "Ibge"]
        termos_cad = ["Q1", "Q2", "Q3", "Total", "Quantidade", "Cadastros", "Validado", "/20"]
        for i, row in df_meta.iterrows():
            row_str = " ".join([str(x).strip() for x in row.values if pd.notna(x)])
            
            if tipo_arquivo == 'cadastro' and any(t in row_str for t in termos_cab) and (any(tv in row_str for tv in termos_cad) or "/" in row_str):
                return i
            elif sum(1 for t in termos_cab if t in row_str) >= 3:
                return i
        return 10

    def _isolar_df(self, df_completo, linha_cabecalho):
        df = df_completo.iloc[linha_cabecalho:].copy()
        if not df.empty:
            df.columns = [str(c).strip() for c in df.iloc[0].values]
            df = df.iloc[1:].reset_index(drop=True)
        return df

    def _encontrar_col_identificadora(self, df):
        # MODIFICAÇÃO: A busca do cabeçalho agora tolera mais variações de texto na coluna
        for c in df.columns:
            nome_col = str(c).strip().upper()
            if nome_col in ["EQUIPE - INE", "INE"]: return c
            # Se a coluna contiver a palavra INE (ex: "CÓDIGO INE"), ele também captura
            if "INE" in nome_col: return c
        for c in df.columns:
            if "CNES" in str(c).strip().upper(): return c
        return None

    def _encontrar_colunas_valor(self, df, tipo_arquivo):
        def limpar_texto(txt):
            txt_str = str(txt).lower().strip()
            return ''.join(c for c in unicodedata.normalize('NFD', txt_str) if unicodedata.category(c) != 'Mn')

        col_encontradas = []
        
        if tipo_arquivo == 'atendimento_domiciliar':
            for c in df.columns:
                c_limpo = limpar_texto(c)
                if c_limpo in ["atendimento individual", "atendimento odontologico"]: col_encontradas.append(c)
                    
        elif tipo_arquivo == 'cadastro':
            ignorar = ["CNES", "INE", "Sigla", "Equipe", "Municipio", "Uf", "Ibge", "Tipo"]
            for col in df.columns:
                if not any(ign in col for ign in ignorar) and (any(k in col for k in ["Total", "Q1", "Q2", "Q3", "202", "Quant", "Cadast", "Valid"]) or "/" in col):
                    col_encontradas.append(col)
                    
        elif tipo_arquivo.startswith('condicao_'):
            chave = tipo_arquivo.split('_')[1]
            chave_limpa = limpar_texto(chave)
            for c in df.columns:
                c_limpo = limpar_texto(c)
                if chave_limpa in c_limpo or c_limpo in ["atendimento individual", "atendimento odontologico", "procedimento"]:
                    col_encontradas.append(c)
                    
        elif tipo_arquivo == 'condicao':
            for c in df.columns:
                c_limpo = limpar_texto(c)
                if c_limpo in ["atendimento individual", "atendimento odontologico", "procedimento"]:
                    col_encontradas.append(c)
                    
        elif tipo_arquivo == 'atividade_coletiva':
            for c in df.columns:
                c_limpo = limpar_texto(c)
                if ("quantidade" in c_limpo and "atividade" in c_limpo) or "no de atividades" in c_limpo or "qt atividade coletiva" in c_limpo:
                    col_encontradas.append(c)
                    
        elif tipo_arquivo == 'procedimento_sigtap' or tipo_arquivo == 'procedimento':
            for c in df.columns:
                c_str = str(c)
                c_limpo = limpar_texto(c_str)
                if re.search(r"\(\d{10}\)", c_str) or "afericao" in c_limpo or "coleta" in c_limpo or "quantidade" in c_limpo or "colo uterino" in c_limpo or "col. de cito" in c_limpo:
                    col_encontradas.append(c)

        if not col_encontradas and not df.empty:
            ultima_coluna = df.columns[-1]
            if "CNES" not in str(ultima_coluna).upper(): col_encontradas.append(ultima_coluna)
            else: col_encontradas = [c for c in ["Procedimento", "Total"] if c in df.columns]

        return col_encontradas