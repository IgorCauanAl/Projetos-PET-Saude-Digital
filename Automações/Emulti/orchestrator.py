import os
import shutil
from datetime import datetime
from dataclasses import dataclass

from config import PASTA_REJEITADOS
from extract import _texto_pdf, titulo_pdf_valido
from transform import transformar_dados_pdf
from load import obter_profissionais_planilha, atualizar_planilha

@dataclass
class RegistroETL:
    caminho: str
    arquivo: str
    tipo: str
    mes: str
    profissionais: dict
    duplicados: set
    profissionais_planilha: dict

class PipelineETL:
    def __init__(self, app=None):
        self.app = app

    def enviar_para_rejeitados(self, caminho, motivo):
        """Isola PDFs inconsistentes ou com erro estrutural direto nos Rejeitados."""
        try:
            os.makedirs(PASTA_REJEITADOS, exist_ok=True)
            nome_original = os.path.basename(caminho)
            nome_sem_ext, ext = os.path.splitext(nome_original)
            # Tag centralizada para Rejeitado
            nome_novo = f"{nome_sem_ext}_REJEITADO_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            destino = os.path.join(PASTA_REJEITADOS, nome_novo)

            if os.path.exists(caminho):
                shutil.move(caminho, destino)

            if self.app:
                self.app.inserir_log(f"PDF movido p/ REJEITADOS. Motivo: {motivo}", "AMARELO")
        except Exception as e:
            if self.app:
                self.app.inserir_log(f"Falha ao mover para rejeitados: {e}", "VERMELHO")

    def extrair_transformar(self, caminhos):
        """[E]xtract & [T]ransform."""
        registros = []
        for caminho in caminhos:
            try:
                # 1. EXTRACT
                valido, motivo = titulo_pdf_valido(caminho)
                if not valido:
                    raise ValueError(f"Título inválido: {motivo}")
                texto_total = _texto_pdf(caminho)

                # 2. TRANSFORM
                tipo, mes, profissionais, duplicados = transformar_dados_pdf(texto_total)

                # Validação de negócio no banco (Planilha)
                prof_planilha = obter_profissionais_planilha(
                    tipo=tipo,
                    mes_atual=mes,
                    nomes_profissionais=list(profissionais.keys())
                )

                registros.append(RegistroETL(
                    caminho=caminho,
                    arquivo=os.path.basename(caminho),
                    tipo=tipo,
                    mes=mes,
                    profissionais=profissionais,
                    duplicados=duplicados,
                    profissionais_planilha=prof_planilha
                ))
            except Exception as e:
                # Erro nos dados -> Manda direto pra Rejeitados (Ex-Quarentena)
                self.enviar_para_rejeitados(caminho, str(e))

        return registros

    def carregar_item(self, item):
        """[L]oad."""
        if isinstance(item, dict):
            tipo, mes, profs = item["tipo"], item["mes"], item["profissionais"]
        else:
            tipo, mes, profs = item.tipo, item.mes, item.profissionais

        return atualizar_planilha(tipo, mes, profs, self.app)