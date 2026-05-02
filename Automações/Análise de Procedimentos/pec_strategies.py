import os
import re
import pandas as pd
from base import EstrategiaExtracao, extrair_texto_pdf, extrair_valor_da_secao_pdf
from config import Cores, MAPA_REGRAS_PDF
from utils import registrar_log
from excel_manager import atualizar_planilha_sisab_memoria

class PecAtividadeColetivaStrategy(EstrategiaExtracao):
    def __init__(self, texto): self.texto = texto
    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de Atividade Coletiva.")
        dados = {}
        
        # 19) PSE - Somatório das temáticas e procedimentos
        termos_pse = {
            "Ações de combate ao Aedes aegypti": r"Ações de combate ao Aedes aegypti[\s,]+(\d+)",
            "Alimentação saudável": r"Alimentação saudável[\s,]+(\d+)",
            "Outro procedimento coletivo": r"Outro procedimento coletivo[\s,]+(\d+)",
            "Outros": r"Outros[\s,]+(\d+)",
            "Não informado": r"Não informado[\s,]+(\d+)",
            "PREVENÇÃO AO COVID-19 NAS ESCOLAS": r"(?:0101010095|PREVEN(?:C|Ç)(?:A|Ã)O AO COVID-19 NAS ESCOLAS)[\s,]+(\d+)"
        }
        
        soma_pse = 0
        termos_encontrados = []
        for nome_termo, padrao in termos_pse.items():
            matches = re.findall(padrao, self.texto, re.IGNORECASE)
            valor_termo = sum(int(m) for m in matches)
            if valor_termo > 0:
                soma_pse += valor_termo
                termos_encontrados.append(f"{nome_termo} ({valor_termo})")
                
        if soma_pse > 0:
            dados["PSE"] = soma_pse
            registrar_log(f"   [+] SOMA PSE REALIZADA: {soma_pse} -> {', '.join(termos_encontrados)}", Cores.VERDE)

        # Resumo Geral da Atividade Coletiva
        val_geral = extrair_valor_da_secao_pdf(self.texto, "Total de registros")
        if val_geral == 0:
            match = re.search(r"Total:\s*(\d+)", self.texto, re.IGNORECASE)
            if match: val_geral = int(match.group(1))
        if val_geral > 0:
            dados["ATIVIDADE COLETIVA"] = val_geral

        return dados

class PecVisitaDomiciliarStrategy(EstrategiaExtracao):
    def __init__(self, texto): self.texto = texto
    
    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de visita domiciliar e territorial.")
        
        # O Regex OBRIGA que os valores estejam logo após o título "Resumo de produção"
        padrao = r"Resumo de produ[cç][aã]o[\s\S]{0,150}?Registros identificados[\W_]+(\d+)[\s\S]{0,150}?Registros n[aã]o identificados[\W_]+(\d+)"
        
        match = re.search(padrao, self.texto, re.IGNORECASE)
        
        if match:
            val_id = int(match.group(1))   
            val_nid = int(match.group(2))  
            total = val_id + val_nid       
            
            registrar_log(f"   [+] SOMA VISITAS ACS REALIZADA (Resumo de Produção): Identificados ({val_id}) + Não Identificados ({val_nid}) = {total}", Cores.VERDE)
            
            return {"VISITA DE ACS": total}
        
        registrar_log("   [-] ATENÇÃO: Bloco 'Resumo de produção' não encontrado corretamente no PDF.", Cores.AMARELO)
        return {}

class PecCadastroIndividualStrategy(EstrategiaExtracao):
    def __init__(self, texto): self.texto = texto
    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de cadastro individual.")
        # 21) ANÁLISE DA SITUAÇÃO CADASTRAL
        valor = extrair_valor_da_secao_pdf(self.texto, "Cidadãos ativos")
        return {"ANÁLISE DA SITUAÇÃO CADASTRAL": valor} if valor > 0 else {}

class PecMarcadorConsumoStrategy(EstrategiaExtracao):
    def __init__(self, texto): self.texto = texto
    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de marcadores de consumo alimentar.")
        # 22) MARCADOR DE CONSUMO ALIMENTAR: Somar Identificados e Não Identificados
        val_id = extrair_valor_da_secao_pdf(self.texto, "Registros identificados")
        val_nid = extrair_valor_da_secao_pdf(self.texto, "Registros não identificados")
        total = val_id + val_nid
        
        if total > 0:
            registrar_log(f"   [+] SOMA MARCADORES REALIZADA: Identificados ({val_id}) + Não Identificados ({val_nid})", Cores.VERDE)
            return {"MARCADOR DE CONSUMO ALIMENTAR (OLHAR NO E-SUS E NO IDS)": total}
        return {}

class PecAtendimentoProcedimentoStrategy(EstrategiaExtracao):
    def __init__(self, texto, categoria): 
        self.texto = texto
        self.categoria = categoria.upper()

    def _extrair_valor(self, padrao, tipo="simples"):
        # Tipo "simples": Pega a primeira ocorrência numérica à frente da palavra.
        # Tipo "avaliado": Pega a segunda ocorrência (para pular a coluna "Solicitado"). Se só tiver uma, pega ela.
        matches = re.findall(padrao + r"[\s,]+(\d+)(?:[\s,]+(\d+))?", self.texto, re.IGNORECASE)
        total = 0
        for m in matches:
            if tipo == "avaliado" and m[1]: 
                total += int(m[1])
            else: 
                total += int(m[0])
        return total

    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de Atendimento/Procedimentos e Exames.")
        dados_extraidos = {}
        
        # --- REGRAS SIMPLES E DIRETAS (Itens 1 ao 10 e 16 ao 18) ---
        regras_simples = {
            "ATENDIMENTO GERAL": r"Registros identificados", 
            "RASTREAMENTO CANCER DE CMA": r"Câncer de mama", 
            "RASTREAMENTO CANCER DE CCU": r"Câncer do colo do útero", 
            "PUERICULTURA": r"Puericultura", 
            "DIABETES": r"Diabetes", 
            "HIPERTENSÃO": r"Hipertensão arterial", 
            "PRÉ-NATAL": r"Pré-natal", 
            "PUERPERAL (até 42 dias)": r"Puerpério \(até 42 dias\)", 
            "SAUDE SEXUAL E REPRODUTIVA": r"Saúde sexual e reprodutiva", 
            "ATEND. DOMICILIAR": r"Domicílio", 
            # Exames de Solicitação (Pega a 1ª coluna - "Solicitado")
            "SOLICITAÇÃO HEMOGLOBINA GLICADA - OLHAR SÓ NO E-SUS E NO IDS": r"Hemoglobina glicada", 
            "SOROLOGIA HIV (PN - OLHAR SÓ NO E-SUS E NO IDS)": r"Sorologia para HIV", 
            "SOROLOGIA SIFILIS (PN - OLHAR SÓ NO E-SUS E NO IDS)": r"Sorologia de sífilis \(VDRL\)" 
        }

        for chave, padrao in regras_simples.items():
            val = self._extrair_valor(padrao, tipo="simples")
            if val > 0:
                # Acrescenta a categoria se a chave não tiver sufixo especial
                chave_final = f"{chave} ({self.categoria})" if "OLHAR SÓ" not in chave and chave != "ATENDIMENTO GERAL" else chave
                dados_extraidos[chave_final] = val

        # --- EXAMES AVALIADOS E PROCEDIMENTOS (Itens 11, 12, 14) ---
        regras_avaliados = {
            "PREVENTIVO GINECOLÓGICO": r"(?:Coleta de citopatológico de colo uterino|0201020033.*?CITOPATOL[OÓ]GICO)", 
            "AFERIÇÃO DE PRESSÃO": r"(?:AFERI(?:C|Ç)(?:A|Ã)O DE PRESS(?:A|Ã)O ARTERIAL|0301100039)", 
            "TESTE DO PEZINHO": r"(?:COLETA DE SANGUE PARA TRIAGEM NEONATAL|0201020050)" 
        }
        
        for chave, padrao in regras_avaliados.items():
            val = self._extrair_valor(padrao, tipo="avaliado")
            if val > 0:
                dados_extraidos[f"{chave} ({self.categoria})"] = val

        # --- SOMATÓRIOS ESPECIAIS (Itens 13 e 15) ---
        
        # 13) TESTE RÁPIDO SIFILIS
        val_sifilis_normal = self._extrair_valor(r"Teste rápido para sífilis(?!\s+na gestante)", tipo="avaliado")
        val_sifilis_gestante = self._extrair_valor(r"Teste rápido para sífilis na gestante ou pai/parceiro", tipo="avaliado")
        soma_sifilis = val_sifilis_normal + val_sifilis_gestante
        if soma_sifilis > 0:
            dados_extraidos[f"TESTE RÁPIDO SIFILIS ({self.categoria})"] = soma_sifilis
            registrar_log(f"   [+] SOMA TESTE SÍFILIS REALIZADA: Normal ({val_sifilis_normal}) + Gestante ({val_sifilis_gestante})", Cores.VERDE)

        # 15) CURATIVOS
        val_curativo_simples = self._extrair_valor(r"(?:CURATIVO SIMPLES|0301100284)", tipo="avaliado")
        val_curativo_especial = self._extrair_valor(r"(?:Curativo especial|0301100276)", tipo="avaliado")
        soma_curativos = val_curativo_simples + val_curativo_especial
        if soma_curativos > 0:
            dados_extraidos[f"CURATIVOS ({self.categoria})"] = soma_curativos
            registrar_log(f"   [+] SOMA CURATIVOS REALIZADA: Simples ({val_curativo_simples}) + Especial ({val_curativo_especial})", Cores.VERDE)

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

        mes_atual, categoria, unidade = self._extrair_metadados_comuns(texto_bruto)
        if not all([unidade, categoria]) or mes_atual == "MÊS NÃO IDENTIFICADO":
            registrar_log(f"❌ Falha ao extrair dados essenciais.", Cores.VERMELHO)
            return

        registrar_log(f"ℹ️ Unidade: {unidade} | Categoria: {categoria} | Mês: {mes_atual}", Cores.CIANO)
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
                print(f"DADO_EXTRAIDO|PEC|{unidade}|{str(chave).replace(chr(10), ' ').strip()}|{valor}|{mes_atual}", flush=True)            
            atualizar_planilha_sisab_memoria(dados_para_lancar, mes_atual, self.nome_arquivo, self.wb, self.mapa_abas)
        else:
            registrar_log(f"⚠️ Nenhum dado relevante a ser lançado.", Cores.AMARELO)

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

        mes_atual = "MÊS NÃO IDENTIFICADO"
        meses = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
        match_valido = re.search(r"Período: (\d{2}/\d{2}/\d{4})", texto) or re.search(r"Data: (\d{2}/\d{2}/\d{4})", texto) 
        if match_valido:
            try: 
                mes_atual = meses[pd.to_datetime(match_valido.group(1), dayfirst=True).month - 1]
            except: 
                pass
        
        unidade = os.path.splitext(self.nome_arquivo)[0].upper().strip()
        return mes_atual, categoria, unidade