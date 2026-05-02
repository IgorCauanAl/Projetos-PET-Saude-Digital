import os

# === CONFIGURAÇÕES VISUAIS DO TERMINAL ===
class Cores:
    RESET = ''
    VERMELHO = ''
    VERDE = ''
    AMARELO = ''
    AZUL = ''
    ROXO = ''
    CIANO = ''
    BRANCO = ''
    NEGRITO = ''
    FUNDO_VERMELHO = ''

#configuracao universal do diretorio
HOME_USER = os.path.expanduser("~")

# Lista de possíveis nomes para a pasta
possiveis_nomes = ["Desktop", "Área de Trabalho", "Area de Trabalho"]
pasta_desktop = None

for nome in possiveis_nomes:
    caminho_teste = os.path.join(HOME_USER, nome)
    if os.path.exists(caminho_teste):
        pasta_desktop = caminho_teste
        break

# Caso o Windows use um padrão muito diferente
if not pasta_desktop:
    pasta_desktop = os.path.join(HOME_USER, "Desktop")

PASTA_MONITORADA = os.path.join(pasta_desktop, "analise")
PLANILHA_ANALISE = os.path.join(PASTA_MONITORADA, "analise.xlsx")


# Regras gerais
MAPA_REGRAS_PDF = {
    "ATENDIMENTO GERAL\n (Médico)": ("geral", "Registros identificados", "simples"),
    "ATENDIMENTO GERAL\n (Enfermeiro)": ("geral", "Registros identificados", "simples"),
    "PRÉ-NATAL (Médico)": ("geral", "Pré-natal", "simples"),
    "PRÉ-NATAL (Enfermeiro)": ("geral", "Pré-natal", "simples"),
    "PRÉ-NATAL (Odonto) - (OLHAR NO E-SUS E NO IDS)": ("geral", "Pré-natal", "simples"),
    "DIABETES (Médico)": ("geral", "Diabetes", "simples"),
    "DIABETES (Enfermeiro)": ("geral", "Diabetes", "simples"),
    "HIPERTENSÃO (Médico)": ("geral", "Hipertensão arterial", "simples"),
    "HIPERTENSÃO (Enfermeiro)": ("geral", "Hipertensão arterial", "simples"),
    "PUERPERAL": ("geral", "Puerpério", "simples"),
    "SAUDE SEXUAL E REPRODUTIVA": ("geral", "Saúde sexual e reprodutiva", "simples"),
    "PUERICULTURA\n (Médico)": ("geral", "Puericultura", "simples"),
    "PUERICULTURA\n(Enfermeiro)": ("geral", "Puericultura", "simples"),
    "PREVENTIVO GINECOLÓGICO": ("geral", "Coleta de citopatológico de colo uterino", "simples"),
    "RASTREAMENTO CANCER DE CCU": ("geral", "Câncer do colo do útero", "simples"),
    "RASTREAMENTO CANCER DE CMA": ("geral", "Câncer de mama", "simples"),
    "ATEND. DOMICILIAR (Enfermeiro)": ("geral", "Domicílio", "simples"),
    "ATEND. DOMICILIAR (Odonto)": ("geral", "Domicílio", "simples"),
    "ATEND. DOMICILIAR (Médico)": ("geral", "Domicílio", "simples"),
    "EXAME DO PÉ DIABÉTICO": ("geral", "Exame do pé diabético", "simples"),
    "TESTE DO PEZINHO": ("geral", "COLETA DE SANGUE PARA TRIAGEM NEONATAL", "exame"), 
    "SOLICITAÇÃO HEMOGLOBINA GLICADA (DIABÉTICOS - OLHAR SÓ NO E-SUS E NO IDS) - MÉDICO": ("geral", "Hemoglobina glicada", "exame"),
    "SOLICITAÇÃO HEMOGLOBINA GLICADA (DIABÉTICOS - OLHAR SÓ NO E-SUS E NO IDS) - ENFERMEIRO": ("geral", "Hemoglobina glicada", "exame"),
    "AFERIÇÃO DE PRESSÃO": ("geral", "AFERIÇÃO DE PRESSÃO", "simples"),
    "TESTE RÁPIDO SIFILIS (SOMAR NORMAL E O PARA GESTANTE)": ("geral", ["TESTE RÁPIDO PARA SÍFILIS", "TESTE RÁPIDO PARA SÍFILIS EM GESTANTE"], "exame"),
    "TESTE RÁPIDO HIV (SOMAR NORMAL E O PARA GESTANTE)": ("geral", ["TESTE RÁPIDO PARA HIV", "TESTE RÁPIDO PARA HIV EM GESTANTE"], "exame"),
    "CURATIVOS (SOMAR SIMPLES E ESPECIAL)": ("geral", ["Curativo especial", "CURATIVO SIMPLES"], "simples"),
    "SOROLOGIA HIV (PN - OLHAR SÓ NO E-SUS E NO IDS)": ("geral", "Sorologia para HIV", "simples"),
    "SOROLOGIA SIFILIS (PN - OLHAR SÓ NO E-SUS E NO IDS)": ("geral", "Sorologia de sífilis", "simples"),
    "PSE": ("geral", "Educação", "simples"),
    "ATIVIDADE COLETIVA": ("geral", "dummy_term", "simples"),
    "VISITA DE ACS": ("geral", "dummy_term", "simples"),
    "MARCADOR DE CONSUMO ALIMENTAR (OLHAR NO E-SUS E NO IDS)": ("geral", "dummy_term", "simples"),
    "ANÁLISE DA SITUAÇÃO CADASTRAL": ("geral", "dummy_term", "simples"),
}

MAPA_CONDICOES_SISAB = {
    "Pré-natal": {"Médico": "PRÉ-NATAL (Médico)", "Enfermeiro": "PRÉ-NATAL (Enfermeiro)"},
    "Diabetes": {"Médico": "DIABETES (Médico)", "Enfermeiro": "DIABETES (Enfermeiro)"},
    "Hipertensão": {"Médico": "HIPERTENSÃO (Médico)", "Enfermeiro": "HIPERTENSÃO (Enfermeiro)"},
    "Puerpério": {"Médico": "PUERPERAL", "Enfermeiro": "PUERPERAL"},
    "Saúde sexual e reprodutiva": {"Médico": "SAUDE SEXUAL E REPRODUTIVA", "Enfermeiro": "SAUDE SEXUAL E REPRODUTIVA"},
    "Puericultura": {"Médico": "PUERICULTURA\n (Médico)", "Enfermeiro": "PUERICULTURA\n(Enfermeiro)"},
    "Rast. câncer do colo do útero.": {"Médico": "RASTREAMENTO CANCER DE CCU", "Enfermeiro": "RASTREAMENTO CANCER DE CCU"},
    "Rast. câncer de mama": {"Médico": "RASTREAMENTO CANCER DE CMA", "Enfermeiro": "RASTREAMENTO CANCER DE CMA"}
}

MAPA_PROCEDIMENTOS_SISAB = {
    "Preventivo Ginecológico": {"Médico": "PREVENTIVO GINECOLÓGICO", "Enfermeiro": "PREVENTIVO GINECOLÓGICO"},
    "Aferição de Pressão": {"Médico": "AFERIÇÃO DE PRESSÃO", "Enfermeiro": "AFERIÇÃO DE PRESSÃO"},
    "Teste do Pezinho": {"Médico": "TESTE DO PEZINHO", "Enfermeiro": "TESTE DO PEZINHO"},
    "Solicitação Hemoglobina Glicada": {"Médico": "SOLICITAÇÃO HEMOGLOBINA GLICADA (DIABÉTICOS - OLHAR SÓ NO E-SUS E NO IDS) - MÉDICO", "Enfermeiro": "SOLICITAÇÃO HEMOGLOBINA GLICADA (DIABÉTICOS - OLHAR SÓ NO E-SUS E NO IDS) - ENFERMEIRO"},
    "Sorologia Hiv": {"Médico": "SOROLOGIA HIV (PN - OLHAR SÓ NO E-SUS E NO IDS)", "Enfermeiro": "SOROLOGIA HIV (PN - OLHAR SÓ NO E-SUS E NO IDS)"},
    "Sorologia Sifilis": {"Médico": "SOROLOGIA SIFILIS (PN - OLHAR SÓ NO E-SUS E NO IDS)", "Enfermeiro": "SOROLOGIA SIFILIS (PN - OLHAR SÓ NO E-SUS E NO IDS)"},
    "Atividade Coletiva": {"Médico": "ATIVIDADE COLETIVA", "Enfermeiro": "ATIVIDADE COLETIVA"},
    "Curativo": {"Médico": "CURATIVOS (SOMAR SIMPLES E ESPECIAL)", "Enfermeiro": "CURATIVOS (SOMAR SIMPLES E ESPECIAL)"},
    "Sifilis": {"Médico": "TESTE RÁPIDO SIFILIS (SOMAR NORMAL E O PARA GESTANTE)", "Enfermeiro": "TESTE RÁPIDO SIFILIS (SOMAR NORMAL E O PARA GESTANTE)"},
    "Hiv": {"Médico": "TESTE RÁPIDO HIV (SOMAR NORMAL E O PARA GESTANTE)", "Enfermeiro": "TESTE RÁPIDO HIV (SOMAR NORMAL E O PARA GESTANTE)"}
}