import os
import re
import pandas as pd
from base import EstrategiaExtracao, extrair_texto_pdf, extrair_valor_da_secao_pdf
from config import Cores, MAPA_REGRAS_PDF, PASTA_LOGS
from utils import registrar_log
from excel_manager import atualizar_planilha_sisab_memoria

class PecAtividadeColetivaStrategy(EstrategiaExtracao):
    def __init__(self, texto): self.texto = texto
    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de Atividade Coletiva.")
        valor = extrair_valor_da_secao_pdf(self.texto, "Total de registros")
        if valor == 0:
            match = re.search(r"Total:\s*(\d+)", self.texto, re.IGNORECASE)
            if match: valor = int(match.group(1))
        return {"ATIVIDADE COLETIVA": valor} if valor > 0 else {}

class PecVisitaDomiciliarStrategy(EstrategiaExtracao):
    def __init__(self, texto): self.texto = texto
    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de Visita Domiciliar.")
        valor = extrair_valor_da_secao_pdf(self.texto, "Registros identificados")
        return {"VISITA DE ACS": valor} if valor > 0 else {}

class PecCadastroIndividualStrategy(EstrategiaExtracao):
    def __init__(self, texto): self.texto = texto
    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de Cadastro Individual.")
        valor = extrair_valor_da_secao_pdf(self.texto, "Cidadãos ativos")
        return {"ANÁLISE DA SITUAÇÃO CADASTRAL": valor} if valor > 0 else {}

class PecMarcadorConsumoStrategy(EstrategiaExtracao):
    def __init__(self, texto): self.texto = texto
    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de Marcadores de Consumo.")
        valor = extrair_valor_da_secao_pdf(self.texto, "Registros identificados")
        return {"MARCADOR DE CONSUMO ALIMENTAR (OLHAR NO E-SUS E NO IDS)": valor} if valor > 0 else {}

class PecAtendimentoProcedimentoStrategy(EstrategiaExtracao):
    def __init__(self, texto, categoria): 
        self.texto = texto
        self.categoria = categoria.title() # Ex: "Médico", "Enfermeiro"

    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de Atendimento/Procedimentos e Exames.")
        dados_extraidos = {}
        
        # Mapeamento expandido de Regex focando no layout do PEC
        mapeamento_regex = {
            # Atendimentos Básicos
            "ATENDIMENTO GERAL": r"Registros identificados[\s,]+(\d+)",
            "DIABETES": r"Diabetes[\s,]+(\d+)",
            "HIPERTENSÃO": r"Hipertensão arterial[\s,]+(\d+)",
            "PRÉ-NATAL": r"Pré-natal[\s,]+(\d+)",
            "PUERICULTURA": r"Puericultura[\s,]+(\d+)",
            "PUERPERAL (até 42 dias)": r"Puerpério \(até 42 dias\)[\s,]+(\d+)",
            "SAUDE SEXUAL E REPRODUTIVA": r"Saúde sexual e reprodutiva[\s,]+(\d+)",
            "RASTREAMENTO CANCER DE CMA": r"Câncer de mama[\s,]+(\d+)",
            "RASTREAMENTO CANCER DE CCU": r"(?:Câncer do colo do útero|0201020033).*?[\s,]+(\d+)",
            "ATEND. DOMICILIAR": r"Domicílio[\s,]+(\d+)",
            
            # Exames e Solicitações
            "SOLICITAÇÃO HEMOGLOBINA GLICADA": r"Hemoglobina glicada[\s,]+(\d+)",
            "SOROLOGIA HIV (PN": r"Sorologia para HIV[\s,]+(\d+)",
            "SOROLOGIA SIFILIS (PN": r"Sorologia de sífilis \(VDRL\)[\s,]+(\d+)",
            "TESTE DO PEZINHO": r"Teste do pezinho[\s,]+(\d+)",
            
            # Procedimentos (Novos Adicionados)
            "PREVENTIVO GINECOLÓGICO": r"Coleta de material(?:.*?)?citopatológico.*?[\s,]+(\d+)",
            "AFERIÇÃO DE PRESSÃO": r"Aferição de pressão.*?[\s,]+(\d+)",
            "CURATIVOS": r"Curativo.*?[\s,]+(\d+)",
            "TESTE RÁPIDO SIFILIS": r"Teste rápido para sífilis.*?[\s,]+(\d+)",
            "TESTE RÁPIDO HIV": r"Teste rápido para HIV.*?[\s,]+(\d+)"
        }

        for chave_base, padrao in mapeamento_regex.items():
            # Exceção da Saúde Mental mantida
            if "MENTAL" in chave_base.upper(): continue
            
            # findall é usado para achar todas as ocorrências e viabilizar as somas exigidas na planilha
            matches = re.findall(padrao, self.texto, re.IGNORECASE)
            if matches:
                valor_total = 0
                for match in matches:
                    # Captura do dado numérico, ignorando textos acidentais do PDF
                    num = match[0] if isinstance(match, tuple) else match
                    if str(num).strip().isdigit():
                        valor_total += int(str(num).strip())

                if valor_total > 0:
                    chave_final = None
                    chave_base_limpa = chave_base.lower().replace(" ", "").replace(".", "")
                    cat_limpa = self.categoria.lower()
                    
                    # Define quais itens na planilha não levam o nome do profissional (Médico/Enfermeiro)
                    itens_sem_categoria = [
                        "puerperal", "saudesexual", "rastreamento", "preventivo", 
                        "aferição", "testerápido", "curativos", "testedopezinho"
                    ]
                    precisa_categoria = not any(x in chave_base_limpa for x in itens_sem_categoria)

                    # Auto-Matcher para encontrar a chave invisível ou com quebra de linha do Excel
                    for chave_real in MAPA_REGRAS_PDF.keys():
                        chave_real_limpa = str(chave_real).lower().replace(" ", "").replace("\n", "").replace("\r", "")
                        
                        if chave_base_limpa in chave_real_limpa:
                            if precisa_categoria:
                                if cat_limpa in chave_real_limpa:
                                    chave_final = chave_real
                                    break
                            else:
                                chave_final = chave_real
                                break

                    # Sistema de segurança (Fallback) caso o mapa falhe
                    if not chave_final:
                        if "HEMOGLOBINA" in chave_base or "SOROLOGIA" in chave_base:
                            chave_final = f"{chave_base} - OLHAR SÓ NO E-SUS E NO IDS) - {self.categoria.upper()}"
                        elif precisa_categoria:
                            chave_final = f"{chave_base} ({self.categoria})"
                        else:
                            chave_final = chave_base
                            
                    dados_extraidos[chave_final] = dados_extraidos.get(chave_final, 0) + valor_total

        # Mantém a leitura secundária do MAPA original para não quebrar outras lógicas
        chaves_especiais = ["ATIVIDADE COLETIVA", "VISITA DE ACS", "ANÁLISE DA SITUAÇÃO CADASTRAL", "MARCADOR DE CONSUMO ALIMENTAR (OLHAR NO E-SUS E NO IDS)"]
        for chave_planilha, (secao, termo_busca_config, metodo) in MAPA_REGRAS_PDF.items():
            if chave_planilha in chaves_especiais or "MENTAL" in str(chave_planilha).upper(): continue
            if chave_planilha in dados_extraidos: continue

            valor_final = 0
            if isinstance(termo_busca_config, list):
                for termo in termo_busca_config:
                    valor_final += extrair_valor_da_secao_pdf(self.texto, termo, metodo)
            elif isinstance(termo_busca_config, str):
                valor_final = extrair_valor_da_secao_pdf(self.texto, termo_busca_config, metodo)
                
            if valor_final > 0: dados_extraidos[chave_planilha] = valor_final
                
        return dados_extraidos

class ContextoPec:
    def __init__(self, caminho_arquivo, wb, mapa_abas):
        self.caminho = caminho_arquivo
        self.nome_arquivo = os.path.basename(caminho_arquivo)
        self.wb = wb
        self.mapa_abas = mapa_abas

    def executar(self):
        print(f"\n{Cores.ROXO}📄 PROCESSANDO ARQUIVO PEC (PDF): {self.nome_arquivo}{Cores.RESET}")
        texto_bruto = extrair_texto_pdf(self.caminho)
        if not texto_bruto: return

        try:
            with open(os.path.join(PASTA_LOGS, f"DEBUG_{self.nome_arquivo}.txt"), "w", encoding="utf-8") as f:
                f.write(texto_bruto)
        except: pass

        mes_atual, categoria, unidade = self._extrair_metadados_comuns(texto_bruto)
        
        if not all([unidade, categoria]) or mes_atual == "MÊS NÃO IDENTIFICADO":
            registrar_log(f"❌ Falha ao extrair dados essenciais.", Cores.VERMELHO)
            return

        registrar_log(f"ℹ️ Unidade: {unidade} | Categoria: {categoria} | Mês: {mes_atual}", Cores.CIANO)

        # ALTERAÇÃO: Passando a categoria para a estratégia
        estrategia = self._selecionar_estrategia(texto_bruto, categoria)
        dados_brutos = estrategia.extrair()

        dados_para_lancar = {}
        categoria_pdf = categoria.lower()
        
        for chave, valor in dados_brutos.items():
            chave_limpa = str(chave).strip().lower()
            is_especifica = any(cat in chave_limpa for cat in ["médico", "enfermeiro", "odonto"])
            if is_especifica:
                if categoria_pdf != "não identificada" and categoria_pdf in chave_limpa:
                    dados_para_lancar[chave] = valor
                    registrar_log(f"   [✓] Lançando item ({categoria_pdf}): {str(chave).replace(chr(10), ' ')}", Cores.VERDE)
                else:
                    registrar_log(f"   [✗] Ignorando item específico: {str(chave).replace(chr(10), ' ')}", Cores.AMARELO)
            else:
                dados_para_lancar[chave] = valor
                registrar_log(f"   [✓] Lançando item (Geral): {str(chave).replace(chr(10), ' ')}", Cores.VERDE)

        if dados_para_lancar:
            for chave, valor in dados_para_lancar.items():
                indicador_limpo = str(chave).replace('\n', ' ').replace('\r', '').strip()
                valor_limpo = str(valor).replace('\n', '').replace('\r', '').strip()
                
                print(f"DADO_EXTRAIDO|PEC|{unidade}|{indicador_limpo}|{valor_limpo}|{mes_atual}", flush=True)            

            atualizar_planilha_sisab_memoria(dados_para_lancar, mes_atual, self.nome_arquivo, self.wb, self.mapa_abas)
        else:
            registrar_log(f"⚠️ Nenhum dado relevante a ser lançado.", Cores.AMARELO)

    # ALTERAÇÃO: O método _selecionar_estrategia agora envia a categoria
    def _selecionar_estrategia(self, texto, categoria=""):
        if re.search(r"Relatório de atividade coletiva", texto, re.IGNORECASE):
            return PecAtividadeColetivaStrategy(texto)
        elif re.search(r"Relatório de visita domiciliar e territorial", texto, re.IGNORECASE):
            return PecVisitaDomiciliarStrategy(texto)
        elif re.search(r"Relatório de cadastro individual", texto, re.IGNORECASE):
            return PecCadastroIndividualStrategy(texto)
        elif re.search(r"Relatório de marcadores de consumo alimentar", texto, re.IGNORECASE):
            return PecMarcadorConsumoStrategy(texto)
        else:
            return PecAtendimentoProcedimentoStrategy(texto, categoria)

    def _extrair_metadados_comuns(self, texto):
        categoria = "NÃO IDENTIFICADA"
        if "Categoria profissional: MÉDICO" in texto: categoria = "MÉDICO"
        elif "Categoria profissional: ENFERMEIRO" in texto: categoria = "ENFERMEIRO"
        elif "Categoria profissional: ODONTÓLOGO" in texto: categoria = "ODONTO"
        elif "Categoria profissional: AGENTE COMUNITÁRIO DE SAÚDE" in texto: categoria = "ACS" 

        meses = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
        mes_atual = "MÊS NÃO IDENTIFICADO"
        match_periodo = re.search(r"Período: (\d{2}/\d{2}/\d{4})", texto)
        match_data = re.search(r"Data: (\d{2}/\d{2}/\d{4})", texto) 

        match_valido = match_periodo or match_data
        if match_valido:
            try:
                mes_num = pd.to_datetime(match_valido.group(1), dayfirst=True).month
                mes_atual = meses[mes_num - 1]
            except: pass
        
        unidade = os.path.splitext(self.nome_arquivo)[0].upper().strip()
        
        return mes_atual, categoria, unidade