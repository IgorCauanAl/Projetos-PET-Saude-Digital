from config import Cores
from utils import registrar_log, normalizar_texto
from sisab_base import BaseSisabXlsxStrategy


class ContextoSigtap(BaseSisabXlsxStrategy):

    NOME_LAYOUT = "SISAB - SIGTAP"

    MAPA_CODIGOS_SIGTAP = {
        "0301100039": "Afericao De Pressao Arterial",
        "0214010082": "Teste Rapido Para Sifilis Na Gestante Ou Pai/Parceiro",
        "0214010074": "Teste Rapido Para Sifilis",
        "0301100276": "Curativo Simples + Curativo Especial",
        "0301100284": "Curativo Simples + Curativo Especial",
        "0201020050": "Coleta De Sangue P/ Triagem Neonatal",
        "0301090033": "AVALIAÇÃO MULTIDIMENSIONAL DA PESSOA IDOSA",
    }

    def _extrair_dados_da_aba(self, ws):
        linha_header, mapa_colunas = self._localizar_header(ws, exige_indicador=True)

        if not linha_header:
            registrar_log("❌ Cabeçalho SIGTAP não encontrado.", Cores.VERMELHO)
            return []

        col_ine = self._localizar_coluna_ine(mapa_colunas)
        if not col_ine:
            registrar_log("❌ Coluna 'Equipe - INE' não encontrada no SIGTAP.", Cores.VERMELHO)
            return []

        indicadores_colunas = self._localizar_colunas_sigtap(mapa_colunas)
        registrar_log(f"✅ Cabeçalho SIGTAP encontrado na linha {linha_header}", Cores.VERDE)
        registrar_log(f"📌 Procedimentos SIGTAP encontrados: {list(indicadores_colunas.keys())}", Cores.AMARELO)

        if not indicadores_colunas:
            registrar_log(
                "⚠️ Nenhuma coluna SIGTAP foi reconhecida. Confira se o cabeçalho contém os códigos dos procedimentos.",
                Cores.AMARELO,
            )
            return []

        somas_por_ine_e_indicador = {}

        for row in range(linha_header + 1, ws.max_row + 1):
            ine = self._normalizar_ine(ws.cell(row=row, column=col_ine).value)
            if not ine:
                continue

            for indicador, col_indicador in indicadores_colunas.items():
                valor = self._converter_numero(ws.cell(row=row, column=col_indicador).value)
                if valor is None or valor <= 0:
                    continue

                chave = (ine, indicador)
                somas_por_ine_e_indicador[chave] = somas_por_ine_e_indicador.get(chave, 0) + valor

        dados_processados = []
        for (ine, indicador), total in somas_por_ine_e_indicador.items():
            dados_processados.append(self._montar_item(ine, indicador, total))
            print(f"DADO_EXTRAIDO|{ine}|{indicador}|{total}")

        return dados_processados

    def _localizar_colunas_sigtap(self, mapa_colunas):
        indicadores_colunas = {}

        for nome_coluna, numero_coluna in mapa_colunas.items():
            codigo = self._extrair_codigo_sigtap(nome_coluna)
            if codigo and codigo in self.MAPA_CODIGOS_SIGTAP:
                indicador = self.MAPA_CODIGOS_SIGTAP[codigo]
                indicadores_colunas[indicador] = numero_coluna
                continue

            indicador_por_texto = self._resolver_indicador_por_texto(nome_coluna)
            if indicador_por_texto:
                indicadores_colunas[indicador_por_texto] = numero_coluna

        return indicadores_colunas

    def _extrair_codigo_sigtap(self, texto):
        if texto is None:
            return None
        match = __import__("re").search(r"\(?\s*(\d{10})\s*\)?", str(texto))
        return match.group(1) if match else None

    def _resolver_indicador_por_texto(self, texto):
        texto_norm = normalizar_texto(str(texto or "")).lower()

        if "afericao" in texto_norm and "press" in texto_norm:
            return "Afericao De Pressao Arterial"

        if "sifilis" in texto_norm and "gestante" in texto_norm:
            return "Teste Rapido Para Sifilis Na Gestante Ou Pai/Parceiro"

        if "sifilis" in texto_norm and "teste rapido" in texto_norm:
            return "Teste Rapido Para Sifilis"

        if "curativo" in texto_norm:
            return "Curativo Simples + Curativo Especial"

        if "triagem neonatal" in texto_norm or "teste do pezinho" in texto_norm:
            return "Coleta De Sangue P/ Triagem Neonatal"

        if "multidimensional" in texto_norm or "idosa" in texto_norm:
            return "AVALIAÇÃO MULTIDIMENSIONAL DA PESSOA IDOSA"

        if "pe diabetico" in texto_norm:
            return "AVALIAÇÃO DO PÉ DIABÉTICO"

        return None
