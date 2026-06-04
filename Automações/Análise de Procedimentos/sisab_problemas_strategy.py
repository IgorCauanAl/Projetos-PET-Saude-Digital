from config import Cores
from utils import registrar_log, normalizar_texto
from excel_manager import MAPA_INDICADORES_SISAB
from sisab_base import BaseSisabXlsxStrategy


class ContextoSisabProblemasCondicoes(BaseSisabXlsxStrategy):
    """Lê o layout SISAB de Problemas/Condições Avaliadas."""

    NOME_LAYOUT = "SISAB - Problemas/Condições"

    def _extrair_dados_da_aba(self, ws):
        linha_header, mapa_colunas = self._localizar_header(ws, exige_indicador=True)

        if not linha_header:
            registrar_log("❌ Cabeçalho do SISAB não encontrado.", Cores.VERMELHO)
            return []

        col_ine = self._localizar_coluna_ine(mapa_colunas)
        if not col_ine:
            registrar_log("❌ Coluna 'Equipe - INE' não encontrada no SISAB.", Cores.VERMELHO)
            return []

        indicadores_colunas = self._localizar_colunas_indicadores(mapa_colunas)
        registrar_log(f"✅ Cabeçalho SISAB encontrado na linha {linha_header}", Cores.VERDE)
        registrar_log(f"📌 Indicadores SISAB encontrados: {list(indicadores_colunas.keys())}", Cores.AMARELO)

        if not indicadores_colunas:
            registrar_log(
                "⚠️ Nenhuma coluna de Problemas/Condições foi reconhecida nesse arquivo.",
                Cores.AMARELO,
            )
            return []

        dados_processados = []

        for row in range(linha_header + 1, ws.max_row + 1):
            ine = self._normalizar_ine(ws.cell(row=row, column=col_ine).value)
            if not ine:
                continue

            for indicador, col_indicador in indicadores_colunas.items():
                valor = self._converter_numero(ws.cell(row=row, column=col_indicador).value)
                if valor is None or valor <= 0:
                    continue

                dados_processados.append(self._montar_item(ine, indicador, valor))

                print(f"DADO_EXTRAIDO|{ine}|{indicador}|{valor}")

        return dados_processados

    def _localizar_colunas_indicadores(self, mapa_colunas):
        indicadores_colunas = {}

        for indicador in MAPA_INDICADORES_SISAB.keys():
            indicador_norm = normalizar_texto(indicador).lower()

            for nome_coluna, numero_coluna in mapa_colunas.items():
                coluna_norm = normalizar_texto(nome_coluna).lower()

                if indicador_norm in coluna_norm or coluna_norm in indicador_norm:
                    indicadores_colunas[indicador] = numero_coluna
                    break

        return indicadores_colunas
