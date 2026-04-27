from .pec_strategies import ContextoPec
from .sisab_strategies import ContextoSisab

def processar_pdf(caminho_pdf, wb, mapa_abas):
    extrator = ContextoPec(caminho_pdf, wb, mapa_abas)
    extrator.executar()

def processar_xlsx_sisab(caminho_arquivo, wb, mapa_abas):
    extrator = ContextoSisab(caminho_arquivo, wb, mapa_abas)
    extrator.executar()