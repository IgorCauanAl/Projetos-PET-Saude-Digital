import pdfplumber
import re
from abc import ABC, abstractmethod
from utils import registrar_log
from config import Cores

class EstrategiaExtracao(ABC):
    @abstractmethod
    def extrair(self):
        """Método obrigatório que retorna os dados extraídos."""
        pass

def extrair_texto_pdf(caminho_pdf):
    texto_total = []
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text(x_tolerance=2, y_tolerance=2)
                if texto_pagina: texto_total.append(texto_pagina)
        return "\n".join(texto_total)
    except Exception as e:
        registrar_log(f"❌ Erro ao tentar ler o PDF {caminho_pdf}: {e}", Cores.VERMELHO)
        return None

def extrair_valor_da_secao_pdf(texto_secao, termo_busca, metodo="simples"):
    if not texto_secao: return 0
    termo_flexivel = termo_busca.replace(" ", r"\s+")
    padrao = re.compile(f"{termo_flexivel}.*?(\\d+)", re.IGNORECASE | re.MULTILINE)
    match = padrao.search(texto_secao)
    return int(match.group(1)) if match else 0