import os
import re
import pandas as pd

from base import EstrategiaExtracao, extrair_texto_pdf, extrair_valor_da_secao_pdf
from config import Cores
from utils import registrar_log
from excel_manager import atualizar_planilha_sisab_memoria

class PecAtividadeColetivaStrategy(EstrategiaExtracao):
    def __init__(self, texto):
        self.texto = texto

    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de Atividade Coletiva.")
        dados = {}

        termos_pse = {
            "Ações de combate ao Aedes aegypti": r"Ações de combate ao Aedes aegypti[\s,]+(\d+)",
            "Alimentação saudável": r"Alimentação saudável[\s,]+(\d+)",
            "Outro procedimento coletivo": r"Outro procedimento coletivo[\s,]+(\d+)",
            "Outros": r"Outros[\s,]+(\d+)",
            "Não informado": r"Não informado[\s,]+(\d+)",
            "PREVENÇÃO AO COVID-19 NAS ESCOLAS": r"(?:0101010095|PREVEN(?:C|Ç)(?:A|Ã)O AO COVID-19 NAS ESCOLAS)[\s,]+(\d+)"
        }

        soma_pse = 0
        for nome_termo, padrao in termos_pse.items():
            matches = re.findall(padrao, self.texto, re.IGNORECASE)
            valor_termo = sum(int(m) for m in matches)
            if valor_termo > 0:
                soma_pse += valor_termo
                print(f"UI_DETALHE|PSE - Procedimentos Coletivos|{nome_termo}|{valor_termo}", flush=True)

        if soma_pse > 0:
            dados["PSE"] = soma_pse

        val_geral = extrair_valor_da_secao_pdf(self.texto, "Total de registros")
        if val_geral == 0:
            match = re.search(r"Total:\s*(\d+)", self.texto, re.IGNORECASE)
            if match: val_geral = int(match.group(1))

        if val_geral > 0:
            dados["ATIVIDADE COLETIVA"] = val_geral
            print(f"UI_DETALHE|ATIVIDADE COLETIVA|Total de Registros|{val_geral}", flush=True)

        return dados

class PecVisitaDomiciliarStrategy(EstrategiaExtracao):
    def __init__(self, texto):
        self.texto = texto

    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de visita domiciliar e territorial.")
        padrao = r"Resumo de produ[cç][aã]o[\s\S]{0,150}?Registros identificados[\W_]+(\d+)[\s\S]{0,150}?Registros n[aã]o identificados[\W_]+(\d+)"
        match = re.search(padrao, self.texto, re.IGNORECASE)

        if match:
            val_id = int(match.group(1))
            val_nid = int(match.group(2))
            total = val_id + val_nid
            print(f"UI_DETALHE|VISITA DE ACS|Registros Identificados|{val_id}", flush=True)
            print(f"UI_DETALHE|VISITA DE ACS|Registros Não Identificados|{val_nid}", flush=True)
            return {"VISITA DE ACS": total}

        return {}

class PecCadastroIndividualStrategy(EstrategiaExtracao):
    def __init__(self, texto):
        self.texto = texto

    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de cadastro individual.")
        valor = extrair_valor_da_secao_pdf(self.texto, "Cidadãos ativos")
        if valor > 0:
            print(f"UI_DETALHE|SITUAÇÃO CADASTRAL|Cidadãos ativos|{valor}", flush=True)
        return {"ANÁLISE DA SITUAÇÃO CADASTRAL": valor} if valor > 0 else {}

class PecMarcadorConsumoStrategy(EstrategiaExtracao):
    def __init__(self, texto):
        self.texto = texto

    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de marcadores de consumo alimentar.")
        val_id = extrair_valor_da_secao_pdf(self.texto, "Registros identificados")
        val_nid = extrair_valor_da_secao_pdf(self.texto, "Registros não identificados")
        total = val_id + val_nid

        if total > 0:
            print(f"UI_DETALHE|MARCADOR DE CONSUMO|Registros Identificados|{val_id}", flush=True)
            print(f"UI_DETALHE|MARCADOR DE CONSUMO|Registros Não Identificados|{val_nid}", flush=True)
            return {"MARCADOR DE CONSUMO ALIMENTAR (OLHAR NO E-SUS)": total}
        return {}

class PecAtendimentoProcedimentoStrategy(EstrategiaExtracao):
    def __init__(self, texto, categoria):
        self.texto = texto
        self.categoria = categoria.upper()

    def _extrair_valor(self, padroes, tipo="simples", procedimento_nome=""):
        texto_limpo = re.sub(r'["\',]', ' ', self.texto)
        texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
        total = 0

        if isinstance(padroes, str):
            padroes = [padroes]

        spans_contabilizados = []

        def _sobrepoe(inicio, fim):
            return any(not (fim <= s0 or inicio >= s1) for s0, s1 in spans_contabilizados)

        for padrao in padroes:
            regex_completa = padrao + r"(?:(?!Total\s*:)[^\d]){0,80}?(\d{1,5})\b(?:\s+(\d{1,5})\b)?"
            matches = list(re.finditer(regex_completa, texto_limpo, re.IGNORECASE))

            for m in matches:
                if _sobrepoe(m.start(), m.end()):
                    continue

                val1 = int(m.group(1)) if m.group(1) else 0
                val2 = int(m.group(2)) if m.group(2) else 0

                valor_final = 0
                if tipo == "simples": valor_final = val1
                elif tipo == "avaliado": valor_final = val2 if val2 > 0 else val1
                elif tipo == "soma_exames": valor_final = (val1 + val2)

                if valor_final > 0:
                    total += valor_final
                    spans_contabilizados.append((m.start(), m.end()))

                    if "Registros" in padrao and "identificados" in padrao:
                        item_limpo = "Registros Identificados"
                    else:
                        match_codigo = re.search(r'([A-Z]\d{2}|48|49|\d{10})', padrao)

                        if match_codigo:
                            codigo_encontrado = match_codigo.group(1)
                            descricoes_ciap2 = {
                                "48": "48 - Esclarecimento / discussão / aconselhamento preventivo",
                                "49": "49 - Outros procedimentos preventivos",
                            }
                            item_limpo = descricoes_ciap2.get(codigo_encontrado, codigo_encontrado)
                        else:
                            if "mama" in padrao.lower(): item_limpo = "Câncer de Mama"
                            elif "colo" in padrao.lower(): item_limpo = "Câncer do Colo do Útero"
                            elif "Diabetes" in padrao: item_limpo = "Diabetes"
                            elif "Hipertens" in padrao: item_limpo = "Hipertensão Arterial"
                            elif "Domic" in padrao: item_limpo = "Atendimento Domiciliar"
                            elif "PUERICULTURA" in padrao: item_limpo = "Puericultura"
                            elif "PARTO" in padrao: item_limpo = "Parto"
                            elif "s[ií]filis" in padrao: item_limpo = "Sorologia Sífilis"
                            elif "HIV" in padrao: item_limpo = "Sorologia HIV"
                            elif "Hemoglobina" in padrao: item_limpo = "Hemoglobina Glicada"
                            else: item_limpo = procedimento_nome.title()

                    print(f"UI_DETALHE|{procedimento_nome}|{item_limpo}|{valor_final}", flush=True)
        return total

    def extrair(self):
        registrar_log("ℹ️ Detectado: Relatório de Atendimento/Procedimentos e Exames.")
        dados_extraidos = {}

        # NOVO: Identifica se é relatório de procedimentos para evitar duplicidade de "Registros Identificados"
        eh_relatorio_procedimentos = bool(re.search(r"Relatório\s+de\s+procedimentos", self.texto, re.IGNORECASE))

        regras_mapeamento = {
            "ATENDIMENTO GERAL": {"termos": [r"Resumo\s*de\s*produ[çc][ãa]o[\s\S]{0,200}?Registros\s*identificados[^\d]{0,80}?"], "tipo": "simples"},
            "RASTREAMENTO CANCER DE CMA": {"termos": [r"\b0204030188\b[^\d]{0,80}?"], "tipo": "simples"},
            "RASTREAMENTO CANCER DE CCU": {"termos": [r"C[âa]ncer do colo do [úu]tero[^\d]{0,80}?"], "tipo": "simples"},
            "DIABETES": {"termos": [r"\bT89\b[^\d]{0,80}?", r"\bT90\b[^\d]{0,80}?"], "tipo": "simples"},
            "HIPERTENSÃO": {"termos": [r"\bK86\b[^\d]{0,80}?", r"\bK87\b[^\d]{0,80}?"], "tipo": "simples"},
            "ATEND. DOMICILIAR": {"termos": [r"Domic[íi]lio[^\d]{0,80}?"], "tipo": "simples"},
            "AVALIAÇÃO DO PÉ DIABÉTICO": {"termos": [r"Exame\s+do\s+p[eé]\s+diab[eé]tico[^\d]{0,80}?"], "tipo": "simples"},
            "AVALIAÇÃO DA PESSOA IDOSA": {"termos": [r"\b0301010293\b[^\d]{0,80}?", r"\b0301090033\b[^\d]{0,80}?", r"AVALIA[CÇ][AÃ]O\s+MULTIDIMENSIONAL\s+DA\s+PESSOA\s+IDOSA[^\d]{0,80}?"], "tipo": "simples"},
            "PREVENTIVO GINECOLÓGICO": {"termos": [r"Coleta\s+de\s+citopatol[oó]gico\s+de\s+colo\s+uterino[^\d]{0,80}?", r"Coleta\s+de\s+material\s+do\s+colo\s+de\s+[úu]tero\s+para\s+exame\s+citopatol[oó]gico[^\d]{0,80}?"], "tipo": "simples"},
            "AFERIÇÃO DE PRESSÃO ARTERIAL": {"termos": [r"(?:AFERI(?:C|Ç)(?:A|Ã)O\s+DE\s+PRESS(?:A|Ã)O\s+ARTERIAL|0301100039)[^\d]{0,80}?"], "tipo": "simples"},
            "TESTE RÁPIDO SIFILIS": {
                "termos": [
                    r"\b0214010252\b[^\d]{0,80}?",
                    r"\b0214010074\b[^\d]{0,80}?",
                    r"Trepon[êe]mico\s*\(s[ií]filis\)[^\d]{0,80}?",
                ], "tipo": "avaliado"
            },
            "TESTE RÁPIDO HIV": {
                "termos": [
                    r"\b0214010279\b[^\d]{0,80}?",
                    r"\b0214010058\b[^\d]{0,80}?",
                    r"Teste\s+r[aá]pido[\s\S]{0,60}?Para\s+HIV[^\d]{0,80}?",
                    r"anticorpos\s+anti-?HIV\s+para\s+popula[çc][ãa]o\s+geral[^\d]{0,80}?",
                ], "tipo": "avaliado"
            },
            "TESTE DO PEZINHO": {"termos": [r"(?:TESTE\s+DO\s+PEZINHO|COLETA\s+DE\s+SANGUE\s+PARA\s+TRIAGEM\s+NEONATAL|0201020050)[^\d]{0,80}?"], "tipo": "simples"},
            "CURATIVOS": {"termos": [r"(?:CURATIVO SIMPLES|0301100284)[^\d]{0,80}?", r"(?:Curativo especial|0301100276)[^\d]{0,80}?"], "tipo": "simples"},
            "PUERICULTURA": {
                "termos": [
                    r"\b0301010269\b[^\d]{0,80}?",
                    r"\b0301010277\b[^\d]{0,80}?",
                    r"\bABP0*4\b[^\d]{0,80}?",
                ], "tipo": "simples"
            },
            "SAUDE SEXUAL E REPRODUTIVA": {"termos": [r"\bB25\b[^\d]{0,80}?", r"\bW02\b[^\d]{0,80}?", r"\bW1[0-5]\b[^\d]{0,80}?", r"\bW79\b[^\d]{0,80}?", r"\bW82\b[^\d]{0,80}?", r"\bX0[1-9]\b[^\d]{0,80}?", r"\bX1[0-3]\b[^\d]{0,80}?", r"\bX2[34]\b[^\d]{0,80}?", r"\bX82\b[^\d]{0,80}?", r"\bX89\b[^\d]{0,80}?", r"\bY14\b[^\d]{0,80}?", r"\bABP003\b[^\d]{0,80}?", r"\bABP022\b[^\d]{0,80}?", r"\bABP023\b[^\d]{0,80}?"], "tipo": "simples"},
            "PRÉ-NATAL": {"termos": [r"\bW78\b[^\d]{0,80}?", r"\bW79\b[^\d]{0,80}?", r"\bW81\b[^\d]{0,80}?", r"\bW84\b[^\d]{0,80}?", r"\bW85\b[^\d]{0,80}?", r"\b0301010110\b[^\d]{0,80}?"], "tipo": "simples"},
            "PUERPERAL (até 42 dias)": {"termos": [r"(?<!\d)48(?!\d)\s*[-–]?\s*Esclarecimento[^\d]{0,80}?", r"(?<!\d)49(?!\d)\s*[-–]?\s*Outros[^\d]{0,80}?", r"\bP29\b[^\d]{0,80}?", r"\bW18\b[^\d]{0,80}?", r"\bW19\b[^\d]{0,80}?", r"\bW70\b[^\d]{0,80}?", r"\bW9[0-6]\b[^\d]{0,80}?", r"\b0301010129\b[^\d]{0,80}?"], "tipo": "simples"},
            "SOROLOGIA SIFILIS (PN - OLHAR SÓ NO E-SUS)": {"termos": [r"Sorologia\s*de\s*s[ií]filis(?:\s*\(VDRL\))?[^\d]{0,80}?", r"\b0202031179\b[^\d]{0,80}?", r"\b0202031390\b[^\d]{0,80}?"], "tipo": "soma_exames"},
            "SOROLOGIA HIV (PN - OLHAR SÓ NO E-SUS)": {"termos": [r"Sorologia\s*para\s*HIV[^\d]{0,80}?", r"\b0202031500\b[^\d]{0,80}?", r"\b0202031519\b[^\d]{0,80}?"], "tipo": "soma_exames"},
            "SOLICITAÇÃO HEMOGLOBINA GLICADA - OLHAR SÓ NO E-SUS": {"termos": [r"Hemoglobina\s*glicada[^\d]{0,80}?", r"\b0202010503\b[^\d]{0,80}?"], "tipo": "soma_exames"}
        }

        total_registros_match = re.search(
            r"Registros\s*identificados[^\d]{0,20}?(\d{1,5})\b", self.texto, re.IGNORECASE
        )
        total_registros = int(total_registros_match.group(1)) if total_registros_match else None

        for chave_base, regra in regras_mapeamento.items():

            # NOVO: Se for um relatório de procedimentos, pula a extração do Atendimento Geral
            if chave_base == "ATENDIMENTO GERAL" and eh_relatorio_procedimentos:
                continue

            valor_extraido = self._extrair_valor(regra["termos"], tipo=regra["tipo"], procedimento_nome=chave_base)

            if total_registros and valor_extraido > total_registros:
                registrar_log(
                    f"⚠️ SUSPEITO: '{chave_base}' extraiu {valor_extraido}, "
                    f"maior que o total de Registros Identificados ({total_registros}). "
                    f"Possível falso positivo — revisar manualmente.",
                    Cores.AMARELO,
                )

            if valor_extraido > 0:
                cat_cap = self.categoria.capitalize()

                cat_planilha = ""
                if cat_cap in ["Enfermeiro", "Enfermeira"]:
                    cat_planilha = "ENFA"
                elif cat_cap in ["Médico", "Medico"]:
                    cat_planilha = "MED"
                elif cat_cap in ["Odonto", "Dentista", "Cirurgião dentista"]:
                    cat_planilha = "ODONTO"

                ancoras_map = {
                    "ATENDIMENTO GERAL": f"ATENDIMENTO GERAL ({cat_cap})",
                    "PUERICULTURA": f"PUERICULTURA ({cat_cap})",
                    "DIABETES": f"DIABETES ({cat_cap})",
                    "HIPERTENSÃO": f"HIPERTENSÃO ({cat_cap})",
                    "PRÉ-NATAL": f"PRÉ-NATAL ({cat_cap})",
                    "ATEND. DOMICILIAR": f"ATEND. DOMICILIAR ({cat_cap})",
                    "PUERPERAL (até 42 dias)": "PUERPERAL (até 42 dias)",
                    "AVALIAÇÃO DO PÉ DIABÉTICO": f"AVALIAÇÃO DO PÉ DIABÉTICO {cat_planilha}".strip(),
                    "AVALIAÇÃO DA PESSOA IDOSA": f"AVALIAÇÃO DA PESSOA IDOSA {cat_planilha}".strip(),
                    "PREVENTIVO GINECOLÓGICO": "PREVENTIVO GINECOLÓGICO",
                    "AFERIÇÃO DE PRESSÃO ARTERIAL": "AFERIÇÃO DE PRESSÃO ARTERIAL",
                    "CURATIVOS": "CURATIVOS (SOMAR SIMPLES E ESPECIAL)",
                    "TESTE RÁPIDO SIFILIS": "Teste Rapido Para Sifilis",
                    "TESTE RÁPIDO HIV": "Teste Rapido Para HIV",
                    "SOROLOGIA SIFILIS (PN - OLHAR SÓ NO E-SUS)": "SOROLOGIA SIFILIS (PN - OLHAR SÓ NO E-SUS)",
                    "SOROLOGIA HIV (PN - OLHAR SÓ NO E-SUS)": "SOROLOGIA HIV (PN - OLHAR SÓ NO E-SUS)",
                    "SOLICITAÇÃO HEMOGLOBINA GLICADA - OLHAR SÓ NO E-SUS": f"SOLICITAÇÃO HEMOGLOBINA GLICADA (DIABÉTICOS - OLHAR SÓ NO E-SUS) - {cat_cap}",
                    "TESTE DO PEZINHO": "TESTE DO PEZINHO",
                    "SAUDE SEXUAL E REPRODUTIVA": "SAUDE SEXUAL E REPRODUTIVA",
                    "RASTREAMENTO CANCER DE CMA": "MAMOGRAFIA",
                    "RASTREAMENTO CANCER DE CCU": "PREVENTIVO GINECOLÓGICO"
                }

                chave_final = ancoras_map.get(chave_base, f"{chave_base} ({cat_cap})")
                dados_extraidos[chave_final] = valor_extraido

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

        mes_atual, categoria, identificador = self._extrair_metadados_comuns(texto_bruto)
        if not all([identificador, categoria]) or mes_atual == "MÊS NÃO IDENTIFICADO":
            registrar_log(f"❌ Falha ao extrair dados essenciais do PDF.", Cores.VERMELHO)
            return

        identificador = self._normalizar_identificador_ine(identificador)
        identificador_eh_ine = bool(re.fullmatch(r"\d{6,7}", str(identificador or "")))

        if identificador_eh_ine and identificador in self.mapa_abas:
            nome_aba_real = self.mapa_abas[identificador]
        elif identificador_eh_ine:
            nome_aba_real = f"INE {identificador}"
            registrar_log(
                f"⚠️ INE {identificador} encontrado no PDF, mas não existe uma aba mapeada para ele.",
                Cores.AMARELO,
            )
        else:
            nome_aba_real = identificador

        nome_arquivo_virtual = f"{nome_aba_real}.pdf"

        estrategia = self._selecionar_estrategia(texto_bruto, categoria)
        dados_brutos = estrategia.extrair()
        dados_para_lancar = {}

        categoria_pdf = categoria.lower()
        aliases_categoria = [categoria_pdf]
        if "cirurg" in categoria_pdf and "dent" in categoria_pdf:
            aliases_categoria.extend(["odonto", "odontólogo", "odontologo", "dentista"])
        elif "médico" in categoria_pdf or "medico" in categoria_pdf:
            aliases_categoria.extend(["médico", "medico"])
        elif "enfermeiro" in categoria_pdf:
            aliases_categoria.append("enfermeiro")

        for chave, valor in dados_brutos.items():
            chave_limpa = str(chave).strip().lower()
            is_especifica = any(cat in chave_limpa for cat in ["médico", "medico", "enfermeiro", "odonto", "dentista"])
            if is_especifica:
                if categoria_pdf != "não identificada" and any(alias in chave_limpa for alias in aliases_categoria):
                    dados_para_lancar[chave] = valor
            else:
                dados_para_lancar[chave] = valor

        if dados_para_lancar:
            for chave, valor in dados_para_lancar.items():
                print(f"DADO_EXTRAIDO|PEC|{nome_aba_real}|{str(chave).replace(chr(10), ' ').strip()}|{valor}|{mes_atual}", flush=True)

            if identificador_eh_ine:
                dados_com_ine_exato = []
                for chave, valor in dados_para_lancar.items():
                    dados_com_ine_exato.append({
                        "ine": identificador,
                        "valor": valor,
                        "indicadores": [chave],
                        "nome": nome_aba_real,
                        "ine_exato": True,
                    })

                atualizar_planilha_sisab_memoria(
                    dados_com_ine_exato,
                    mes_atual,
                    self.nome_arquivo,
                    self.wb,
                    self.mapa_abas,
                    profissional_categoria=categoria,
                    sistema_origem="E-SUS",
                )
            else:
                atualizar_planilha_sisab_memoria(
                    dados_para_lancar,
                    mes_atual,
                    nome_arquivo_virtual,
                    self.wb,
                    self.mapa_abas,
                    profissional_categoria=categoria,
                    sistema_origem="E-SUS",
                )

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

    def _normalizar_identificador_ine(self, identificador):
        if identificador is None:
            return None

        texto = str(identificador).strip()
        somente_digitos = re.sub(r"\D", "", texto)

        if somente_digitos and len(somente_digitos) >= 6:
            return somente_digitos[-7:].lstrip("0")

        return texto.upper().strip()

    def _normalizar_categoria_profissional(self, texto_categoria):
        if not texto_categoria:
            return "NÃO IDENTIFICADA"

        texto_norm = str(texto_categoria).upper().strip()
        texto_norm = texto_norm.replace("MEDICO", "MÉDICO")
        texto_norm = texto_norm.replace("CIRURGIAO", "CIRURGIÃO")

        if re.search(r"M[EÉ]DICO", texto_norm, re.IGNORECASE):
            return "MÉDICO"

        if re.search(r"ENFERMEIR[OA]", texto_norm, re.IGNORECASE):
            return "ENFERMEIRO"

        if re.search(r"CIRURGI[AÃ]O[- ]?DENTISTA|ODONT[OÓ]LOG[OA]|ODONTO", texto_norm, re.IGNORECASE):
            return "CIRURGIÃO DENTISTA"

        if re.search(r"AGENTE\s+COMUNIT[AÁ]RIO\s+DE\s+SA[UÚ]DE|\bACS\b", texto_norm, re.IGNORECASE):
            return "ACS"

        return "NÃO IDENTIFICADA"

    def _extrair_metadados_comuns(self, texto):
        categoria = "NÃO IDENTIFICADA"

        match_categoria = re.search(
            r"Categoria\s+profissional\s*:\s*([^|\n\r]+)",
            texto,
            re.IGNORECASE,
        )
        if match_categoria:
            categoria = self._normalizar_categoria_profissional(match_categoria.group(1))

        if categoria == "NÃO IDENTIFICADA":
            padroes_categoria = [
                r"M[EÉ]DICO\s+DA\s+ESTRAT[EÉ]GIA\s+DE\s+SA[UÚ]DE\s+DA\s+FAM[IÍ]LIA",
                r"ENFERMEIR[OA]\s+DA\s+ESTRAT[EÉ]GIA\s+DE\s+SA[UÚ]DE\s+DA\s+FAM[IÍ]LIA",
                r"CIRURGI[AÃ]O[- ]?DENTISTA\s+DA\s+ESTRAT[EÉ]GIA\s+DE\s+SA[UÚ]DE\s+DA\s+FAM[IÍ]LIA",
                r"ODONT[OÓ]LOG[OA]\s+DA\s+ESTRAT[EÉ]GIA\s+DE\s+SA[UÚ]DE\s+DA\s+FAM[IÍ]LIA",
                r"AGENTE\s+COMUNIT[AÁ]RIO\s+DE\s+SA[UÚ]DE",
            ]

            for padrao in padroes_categoria:
                match = re.search(padrao, texto, re.IGNORECASE)
                if match:
                    categoria = self._normalizar_categoria_profissional(match.group(0))
                    break

        mes_atual = "MÊS NÃO IDENTIFICADO"
        meses = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
        match_valido = re.search(r"Período: (\d{2}/\d{2}/\d{4})", texto) or re.search(r"Data: (\d{2}/\d{2}/\d{4})", texto)
        if match_valido:
            try: mes_atual = meses[pd.to_datetime(match_valido.group(1), dayfirst=True).month - 1]
            except: pass

        ine_pdf = None
        match_ine = re.search(r"Equipe:\s*0*(\d{6,7})", texto, re.IGNORECASE)
        if match_ine: ine_pdf = match_ine.group(1)

        unidade_fallback = os.path.splitext(self.nome_arquivo)[0].upper().strip()
        identificador_aba = ine_pdf if ine_pdf else unidade_fallback

        return mes_atual, categoria, identificador_aba
