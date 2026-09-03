import os
import re
import difflib
from config import Cores
from utils import registrar_log, normalizar_texto

TABELA_INE = {
    "ALTO DO MORRO":        "2309815",
    "BOA VISTA":            "2095572",
    "COCAO":                "2095521",
    "ESPERANCA":            "2077094",
    "ANDAIA II":            "2273977",
    "SANTA MADALENA":       "2275325",
    "ANDAIA I":             "1784285",
    "ANDAIA III":           "2502194",
    "ASA I":                "1780905",
    "ASA II":               "2502178",
    "G P SALLES I":         "2095548",
    "G P SALLES II":        "2333570",
    "AMPARO":               "2188503",
    "ALTO SOBRADINHO I":    "2073951",
    "ALTO SOBRADINHO II":   "2284995",
    "CENTROSAJ EAP":        "2073986",
    "CENTROSAJ ESF":        "2275341",
    "CALABAR I URBIS I":    "1784803",
    "CALABAR II URBIS I":   "2333546",
    "AURELINO REIS":        "2073978",
    "SAO FRANCISCO II":     "2273985",
    "SAO FRANCISCO I":      "2073935",
    "URBIS III A":          "1804421",
    "URBIS III B":          "2502186",
    "SAO PAULO I":          "1798820",
    "SAO PAULO II":         "1671421",
    "CIDADE NOVA II":       "2504413",
    "IRMA DULCE":           "2095564",
    "URBIS II B":           "2334011",
    "FERNANDO QUEIROZ I":   "2073943",
    "URBIS II A":           "1803352",
    "FERNANDO QUEIROZ II":  "2504391",
    "BELA VISTA":           "2095556",
    "MARITA AMANCIO":       "2243393",
    "VIRIATO LOBO ESF":     "1807803",
    "VIRIATO LOBO EAP":     "2309947",
    "ZILDA ARNS I":         "2309904",
    "ZILDA ARNS II":        "2504030",
}

INE_PARA_NOME = {v: k for k, v in TABELA_INE.items()}

MAPA_ABAS_PARA_CANONICO = {
    "ALTO DO MORRO": "ALTO DO MORRO",
    "BOA VISTA": "BOA VISTA",
    "COCÃO": "COCAO",
    "ESPERANÇA": "ESPERANCA",
    "SANTA MADALENA": "SANTA MADALENA",
    "ANDAIA I": "ANDAIA I",
    "ANDAIA II": "ANDAIA II",
    "ANDAIA III": "ANDAIA III",
    "ASA I": "ASA I",
    "ASA II": "ASA II",
    "G. P. SALLES I": "G P SALLES I",
    "G. P. SALLES II": "G P SALLES II",
    "AMPARO": "AMPARO",
    "ALTO SOBRADINHO I": "ALTO SOBRADINHO I",
    "ALTO SOBRADINHO II": "ALTO SOBRADINHO II",
    "CENTROSAJ EAP": "CENTROSAJ EAP",
    "CENTROSAJ ESF": "CENTROSAJ ESF",
    "CALABAR  URBIS I A": "CALABAR I URBIS I",
    "CALABAR  URBIS I B": "CALABAR II URBIS I",
    "AURELINO REIS": "AURELINO REIS",
    "SÃO FRANCISCO I": "SAO FRANCISCO I",
    "SÃO FRANCISCO II": "SAO FRANCISCO II",
    "URBIS III A": "URBIS III A",
    "URBIS III B": "URBIS III B",
    "CIDADE NOVA": "CIDADE NOVA II",
    "SÃO PAULO I": "SAO PAULO I",
    "SÃO PAULO II": "SAO PAULO II",
    "IRMÃ DULCE": "IRMA DULCE",
    "URBIS II A": "URBIS II A",
    "URBIS II B": "URBIS II B",
    "FERNANDO QUEIROZ I": "FERNANDO QUEIROZ I",
    "FERNANDO QUEIROZ II": "FERNANDO QUEIROZ II",
    "BELA VISTA": "BELA VISTA",
    "MARITA AMANCIO": "MARITA AMANCIO",
    "VIRIATO LOBO ESF": "VIRIATO LOBO ESF",
    "VIRIATO LOBO EAP": "VIRIATO LOBO EAP",
    "ZILDA ARNS I": "ZILDA ARNS I",
    "ZILDA ARNS II": "ZILDA ARNS II",
}

MAPA_INDICADORES_SISAB = {
    "Diabetes": ["DIABETES (Enfermeiro)", "DIABETES (Médico)"],
    "Hipertensão arterial": ["HIPERTENSÃO (Enfermeiro)", "HIPERTENSÃO (Médico)"],
    "Pré-natal": ["PRÉ-NATAL (Enfermeiro)", "PRÉ-NATAL (Médico)", "PRÉ-NATAL (Odonto) - (OLHAR NO E-SUS)"],
    "Puericultura": ["PUERICULTURA (Enfermeiro)", "PUERICULTURA (Médico)"],
    "Puerpério (até 42 dias)": ["PUERPERAL (até 42 dias)"],
    "Saúde sexual e reprodutiva": ["SAUDE SEXUAL E REPRODUTIVA"],
    "Rast. câncer de mama": ["RASTREAMENTO CANCER DE CMA"],
    "Rast. câncer do colo do útero": ["RASTREAMENTO CANCER DE CCU"],
    "Atendimento domiciliar": ["ATEND. DOMICILIAR (Enfermeiro)", "ATEND. DOMICILIAR (Médico)", "ATEND. DOMICILIAR (Odonto)"]
}


MAPA_INDICADORES_SIGTAP = {
    "Afericao De Pressao Arterial": [
        "AFERIÇÃO DE PRESSÃO ARTERIAL",
        "AFERICAO DE PRESSAO ARTERIAL",
        "Afericao De Pressao Arterial",
    ],
    "Teste Rapido Para Sifilis Na Gestante Ou Pai/Parceiro": [
        "TESTE RÁPIDO PARA SÍFILIS NA GESTANTE OU PAI/PARCEIRO",
        "TESTE RAPIDO PARA SIFILIS NA GESTANTE OU PAI/PARCEIRO",
        "Teste Rapido Para Sifilis Na Gestante Ou Pai/Parceiro",
    ],
    "Teste Rapido Para Sifilis": [
        "TESTE RÁPIDO SIFILIS (SOMAR NORMAL E O PARA GESTANTE)",
        "TESTE RÁPIDO PARA SÍFILIS",
        "TESTE RAPIDO PARA SIFILIS",
        "Teste Rapido Para Sifilis",
    ],
    "Curativo Simples + Curativo Especial": [
        "CURATIVO SIMPLES + CURATIVO ESPECIAL",
        "CURATIVO SIMPLES E ESPECIAL",
        "CURATIVO SIMPLES/ESPECIAL",
        "CURATIVOS (SOMAR SIMPLES E ESPECIAL)",
        "CURATIVOS",
        "CURATIVO",
        "CURATIVO SIMPLES",
        "CURATIVO ESPECIAL",
    ],
    "Coleta De Sangue P/ Triagem Neonatal": [
        "COLETA DE SANGUE P/ TRIAGEM NEONATAL",
        "COLETA DE SANGUE PARA TRIAGEM NEONATAL",
        "Coleta De Sangue P/ Triagem Neonatal",
    ],
    "AVALIAÇÃO DO PÉ DIABÉTICO": [
        "AVALIAÇÃO DO PÉ DIABÉTICO ENFA",
        "AVALIAÇÃO DO PÉ DIABÉTICO MED",
        "AVALIAÇÃO DO PÉ DIABÉTICO",
        "AVALIACAO DO PE DIABETICO",
        "EXAME DO PÉ DIABÉTICO",
    ],
    "AVALIAÇÃO MULTIDIMENSIONAL DA PESSOA IDOSA": [
        "AVALIAÇÃO DA PESSOA IDOSA ENFA",
        "AVALIAÇÃO DA PESSOA IDOSA MED",
        "AVALIAÇÃO MULTIDIMENSIONAL DA PESSOA IDOSA",
        "AVALIACAO MULTIDIMENSIONAL DA PESSOA IDOSA",
        "AVALIAÇÃO MULTIDIMENSIONAL DA PESSOA",
    ],
}

SUFIXO_PROFISSIONAL = {
    "MÉDICO": "(Médico)",
    "ENFERMEIRO": "(Enfermeiro)",
    "CIRURGIÃO DENTISTA": "(Odonto)",
    "ODONTÓLOGO": "(Odonto)"
}

MESES_ABREV = {
    "JAN": "JANEIRO", "FEV": "FEVEREIRO", "MAR": "MARÇO",
    "ABR": "ABRIL", "MAI": "MAIO", "JUN": "JUNHO",
    "JUL": "JULHO", "AGO": "AGOSTO", "SET": "SETEMBRO",
    "OUT": "OUTUBRO", "NOV": "NOVEMBRO", "DEZ": "DEZEMBRO"
}

def extrair_nome_mes(competencia: str) -> str:
    if not competencia:
        return competencia
    competencia = competencia.upper()
    if competencia in MESES_ABREV.values():
        return competencia
    match = re.search(r'(\w{3,4})', competencia)
    if match:
        abrev = match.group(1).upper()
        return MESES_ABREV.get(abrev, abrev)
    return competencia

def _tokenizar(texto: str) -> list[str]:
    return [t for t in normalizar_texto(texto).split() if len(t) > 1]

def _sufixo_numerico(nome_norm: str) -> str | None:
    sufixos = re.findall(r'\b(III|II|IV|VI|VII|VIII|IX|I|A|B)\b', nome_norm.upper())
    return sufixos[-1] if sufixos else None

def encontrar_aba_por_similaridade(nome_busca: str, lista_abas: list, limite: float = 0.6) -> str | None:
    if not nome_busca or not lista_abas:
        return None
    nome_norm = normalizar_texto(nome_busca)
    melhor_aba = None
    melhor_ratio = 0.0
    for aba in lista_abas:
        aba_norm = normalizar_texto(aba)
        ratio = difflib.SequenceMatcher(None, nome_norm, aba_norm).ratio()
        if ratio > melhor_ratio and ratio >= limite:
            melhor_ratio = ratio
            melhor_aba = aba
    return melhor_aba

def resolver_ine_por_nome(nome_entrada: str) -> str | None:
    nome_norm = normalizar_texto(nome_entrada)
    tokens_entrada = set(_tokenizar(nome_entrada))
    sufixo_entrada = _sufixo_numerico(nome_norm)

    if nome_norm in TABELA_INE:
        return TABELA_INE[nome_norm]

    melhor_ine = None
    melhor_score = -1
    stop_words = {'esf', 'eap', 'centro', 'saude', 'unidade', 'basica', 'equipe', 'familia', 'enasfap', 'posto', 'desconhecido'}

    for nome_canonical, ine in TABELA_INE.items():
        tokens_canonical = set(_tokenizar(nome_canonical))
        sufixo_canonical = _sufixo_numerico(nome_canonical)

        intersecao = tokens_entrada & tokens_canonical
        tokens_base = {
            t for t in intersecao
            if not re.match(r'^(i{1,3}|iv|vi{0,3}|ix|[ab])$', t.lower())
            and t.lower() not in stop_words
        }

        score = len(tokens_base)
        if score == 0:
            continue

        if sufixo_entrada and sufixo_canonical:
            if sufixo_entrada == sufixo_canonical:
                score += 2
            else:
                score -= 10

        if nome_canonical in nome_norm or nome_norm in nome_canonical:
            score += 1

        if score > melhor_score:
            melhor_score = score
            melhor_ine = ine

    return melhor_ine if melhor_score > 0 else None

def mapear_ine_para_abas(wb):
    mapa = {}
    padrao_ine = re.compile(r'(?<!\d)(\d{6,7})(?!\d)')

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in range(1, 61):
            for col in range(1, 16):
                valor = ws.cell(row=row, column=col).value
                if valor is not None:
                    valor_str = str(valor).strip()
                    for ine in padrao_ine.findall(valor_str):
                        mapa[ine] = sheet_name

        if sheet_name in MAPA_ABAS_PARA_CANONICO:
            nome_canonico = MAPA_ABAS_PARA_CANONICO[sheet_name]
            ine_via_nome = TABELA_INE.get(nome_canonico)
            if ine_via_nome and ine_via_nome not in mapa:
                mapa[ine_via_nome] = sheet_name
        else:
            ine_via_nome = resolver_ine_por_nome(sheet_name)
            if ine_via_nome and ine_via_nome not in mapa:
                mapa[ine_via_nome] = sheet_name

    return mapa

def obter_sufixo_categoria(categoria: str) -> str | None:
    if not categoria:
        return None
    cat_upper = categoria.upper()
    for chave, sufixo in SUFIXO_PROFISSIONAL.items():
        if chave in cat_upper:
            return sufixo
    return None

def atualizar_planilha_sisab_memoria(
    dados_por_ine,
    mes_atual,
    nome_arquivo,
    wb,
    mapa_abas,
    profissional_categoria=None,
    sistema_origem=None
):
    mes_busca = extrair_nome_mes(mes_atual)

    if sistema_origem:
        sistema_busca = normalizar_texto(str(sistema_origem))
    else:
        extensao = os.path.splitext(str(nome_arquivo))[1].lower()
        nome_base = normalizar_texto(os.path.basename(str(nome_arquivo)))

        if extensao == ".pdf" or "PEC" in nome_base or "ESUS" in nome_base or "E-SUS" in nome_base:
            sistema_busca = "E-SUS"
        else:
            sistema_busca = "SISAB"

    lista_processamento = []
    if isinstance(dados_por_ine, list):
        lista_processamento = dados_por_ine
    else:
        nome_arquivo_puro = normalizar_texto(os.path.splitext(nome_arquivo)[0])
        ine_encontrado = None

        for ine, aba in mapa_abas.items():
            aba_limpa = normalizar_texto(aba)
            if aba_limpa == nome_arquivo_puro:
                ine_encontrado = ine
                break

        if not ine_encontrado:
            ine_encontrado = resolver_ine_por_nome(nome_arquivo_puro)
            if ine_encontrado:
                registrar_log(
                    f"🔎 INE resolvido pela tabela fixa: {nome_arquivo} → {ine_encontrado} "
                    f"({INE_PARA_NOME.get(ine_encontrado, '?')})",
                    Cores.AMARELO,
                )
        if ine_encontrado:
            for indicador, valor in dados_por_ine.items():
                lista_processamento.append({
                    'ine': ine_encontrado,
                    'valor': valor,
                    'indicadores': [indicador],
                    'nome': nome_arquivo_puro,
                })
        else:
            registrar_log(f"❌ Não vinculei o PDF: {nome_arquivo}", Cores.VERMELHO)
            for ind, val in dados_por_ine.items():
                print(f"UI_RESULTADO|FALHA_INE_NAO_MAPEADO|None|{nome_arquivo}|{ind}|{val}|-|{mes_atual}")
            return

    sufixo = obter_sufixo_categoria(profissional_categoria)

    for item in lista_processamento:
        ine = str(item.get('ine', '')).replace(".0", "").strip()
        nome_posto_sisab = item.get('nome', '')
        valor_novo = item.get('valor', 0)
        indicadores_alvo = item.get('indicadores', [])

        sheet_name = mapa_abas.get(ine)
        usar_ine_exato = bool(item.get("ine_exato", False))

        if not sheet_name and not usar_ine_exato:
            ine_resolvido = resolver_ine_por_nome(nome_posto_sisab)
            if ine_resolvido:
                sheet_name = mapa_abas.get(ine_resolvido)
                if sheet_name:
                    mapa_abas[ine] = sheet_name

        if not sheet_name:
            registrar_log(
                f"🚨 INE {ine} ({nome_posto_sisab}) não mapeado em nenhuma aba. "
                "O INE não pertence à área ou a aba correspondente não existe.",
                Cores.VERMELHO,
            )
            for ind_alvo in indicadores_alvo:
                print(f"UI_RESULTADO|FALHA_ABA_NAO_ENCONTRADA|{ine}|{nome_posto_sisab}|{ind_alvo}|{valor_novo}|-|{mes_atual}")
            continue

        ws = wb[sheet_name]

        col_mes_inicio = None
        linha_mes_encontrada = 0
        mes_busca_norm = normalizar_texto(mes_busca)
        for row_busca in range(1, 60):
            for col in range(2, 50):
                celula = ws.cell(row=row_busca, column=col).value
                if celula:
                    if mes_busca_norm == normalizar_texto(str(celula)):
                        col_mes_inicio = col
                        linha_mes_encontrada = row_busca
                        break
            if col_mes_inicio:
                break

        if not col_mes_inicio:
            for ind_alvo in indicadores_alvo:
                print(f"UI_RESULTADO|FALHA_MES|{ine}|{sheet_name}|{ind_alvo}|{valor_novo}|-|{mes_atual}")
            continue

        col_final = None
        achou_sistema = False
        for offset_linha in range(1, 5):
            linha_alvo = linha_mes_encontrada + offset_linha
            for offset_col in range(0, 3):
                col_alvo = col_mes_inicio + offset_col
                val_sis = ws.cell(row=linha_alvo, column=col_alvo).value
                if val_sis:
                    val_norm = normalizar_texto(str(val_sis))
                    if sistema_busca == "SISAB" and "SISAB" in val_norm:
                        col_final = col_alvo
                        achou_sistema = True
                        break
                    elif sistema_busca in ["E-SUS", "ESUS", "PEC"] and any(
                        t in val_norm for t in ["E-SUS", "E SUS", "ESUS", "PEC"]
                    ):
                        col_final = col_alvo
                        achou_sistema = True
                        break
            if achou_sistema:
                break

        if not col_final:
            registrar_log(
                f"⚠️ Coluna do sistema '{sistema_busca}' não encontrada para o mês {mes_busca}.",
                Cores.AMARELO,
            )
            for ind_alvo in indicadores_alvo:
                print(f"UI_RESULTADO|FALHA_SISTEMA|{ine}|{sheet_name}|{ind_alvo}|{valor_novo}|-|{mes_atual}")
            continue

        mapa_linhas = {}
        for r in range(1, ws.max_row + 1):
            txt = ws.cell(row=r, column=1).value
            if txt:
                mapa_linhas[normalizar_texto(str(txt))] = r

        for indicador_alvo in indicadores_unicos_da_lista(indicadores_alvo):
            linhas_destino = []

            # Bloco que resolve o SIGTAP categorizado (Pé Diabético e Idoso ENFA/MED)
            if indicador_alvo in MAPA_INDICADORES_SIGTAP:
                possiveis_rotulos = MAPA_INDICADORES_SIGTAP[indicador_alvo]

                cat_upper = str(profissional_categoria).upper() if profissional_categoria else ""
                if "MÉDIC" in cat_upper or "MEDIC" in cat_upper:
                    filtro_cat = "MED"
                elif "ENFERMEIR" in cat_upper:
                    filtro_cat = "ENFA"
                else:
                    filtro_cat = None

                for rotulo in possiveis_rotulos:
                    # Filtro inteligente para rotear direto para a linha da enfermeira ou médico
                    if " ENFA" in rotulo and filtro_cat != "ENFA": continue
                    if " MED" in rotulo and filtro_cat != "MED": continue

                    rotulo_norm = normalizar_texto(rotulo)
                    if rotulo_norm in mapa_linhas:
                        linhas_destino.append(mapa_linhas[rotulo_norm])
                        break

                if not linhas_destino:
                    aliases_norm = [normalizar_texto(r) for r in possiveis_rotulos]
                    for chave_planilha, num_linha in mapa_linhas.items():
                        if any(alias == chave_planilha for alias in aliases_norm):
                            linhas_destino.append(num_linha)
                            break
                        if indicador_alvo == "Curativo Simples + Curativo Especial":
                            if "CURATIVO" in chave_planilha:
                                linhas_destino.append(num_linha)
                                break
                        else:
                            if any(alias in chave_planilha or chave_planilha in alias for alias in aliases_norm):
                                linhas_destino.append(num_linha)
                                break

            elif indicador_alvo in MAPA_INDICADORES_SISAB:
                possiveis_rotulos = MAPA_INDICADORES_SISAB[indicador_alvo]
                if sufixo:
                    linhas_destino = []
                    for rotulo in possiveis_rotulos:
                        if sufixo in rotulo and normalizar_texto(rotulo) in mapa_linhas:
                            linhas_destino.append(mapa_linhas[normalizar_texto(rotulo)])
                    if not linhas_destino:
                        print(f"⚠️ Nenhuma linha com sufixo '{sufixo}' encontrada para '{indicador_alvo}' (INE {ine}).")
                        continue
                else:
                    print(f"⚠️ Categoria profissional não informada. Indicador '{indicador_alvo}' não será preenchido para INE {ine}.")
                    print(f"UI_RESULTADO|FALHA_CATEGORIA|{ine}|{sheet_name}|{indicador_alvo}|{valor_novo}|-|{mes_atual}")
                    continue
            else:
                alvo_limpo = normalizar_texto(indicador_alvo)
                if alvo_limpo in mapa_linhas:
                    linhas_destino = [mapa_linhas[alvo_limpo]]
                else:
                    for chave_planilha, num_linha in mapa_linhas.items():
                        if chave_planilha in alvo_limpo or alvo_limpo in chave_planilha:
                            linhas_destino.append(num_linha)
                            break
                        palavras_alvo = [p for p in alvo_limpo.split() if len(p) > 3]
                        if palavras_alvo and all(p in chave_planilha for p in palavras_alvo):
                            linhas_destino.append(num_linha)
                            break

                if not linhas_destino and sufixo:
                    for chave_planilha, num_linha in mapa_linhas.items():
                        if sufixo in chave_planilha and (alvo_limpo in chave_planilha or
                            any(palavra in chave_planilha for palavra in alvo_limpo.split())):
                            linhas_destino.append(num_linha)

            if linhas_destino:
                for linha_destino in linhas_destino:
                    valor_atual_celula = ws.cell(row=linha_destino, column=col_final).value
                    try:
                        v_atual = float(valor_atual_celula) if valor_atual_celula is not None else 0.0
                    except (ValueError, TypeError):
                        v_atual = 0.0
                    try:
                        v_novo = float(valor_novo)
                    except (ValueError, TypeError):
                        v_novo = 0.0
                    resultado_soma = v_atual + v_novo
                    ws.cell(row=linha_destino, column=col_final, value=resultado_soma)
                    print(f"UI_RESULTADO|SUCESSO|{ine}|{sheet_name}|{indicador_alvo}|{valor_novo}|{resultado_soma}|{mes_atual}")
            else:
                print(f"UI_RESULTADO|FALHA_LINHA|{ine}|{sheet_name}|{indicador_alvo}|{valor_novo}|-|{mes_atual}")

def indicadores_unicos_da_lista(lista):
    vistos = set()
    return [x for x in lista if not (x in vistos or vistos.add(x))]
