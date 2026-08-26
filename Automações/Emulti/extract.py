import pdfplumber
from utils import padronizar_nome

def _texto_pdf(caminho_pdf):
    texto_total = ""
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text() or ""
            texto_total += texto_pagina + "\n"
    return texto_total

def titulo_pdf_valido(caminho_pdf):
    try:
        texto_pad = padronizar_nome(_texto_pdf(caminho_pdf))
    except Exception:
        return False, "Não foi possível ler o PDF para validar o título."

    titulos_validos = [
        "RELATORIO DE ATENDIMENTO INDIVIDUAL SERIE HISTORICA",
        "RELATORIO DE ATIVIDADE COLETIVA SERIE HISTORICA",
        "RELATORIO DE ATIVIDADE INDIVIDUAL SERIE HISTORICA",
    ]

    if any(titulo in texto_pad for titulo in titulos_validos):
        return True, "PDF válido."

    return False, ("PDF rejeitado: o título precisa ser 'Relatório de Atividade Coletiva - Série Histórica' "
                   "ou 'Relatório de Atendimento Individual - Série Histórica'.")