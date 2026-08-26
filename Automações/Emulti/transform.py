import re
from utils import padronizar_nome, _tokens_nome

MESES = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
]

MESES_NUMERO = {
    "01": "JANEIRO", "1": "JANEIRO", "02": "FEVEREIRO", "2": "FEVEREIRO",
    "03": "MARÇO", "3": "MARÇO", "04": "ABRIL", "4": "ABRIL",
    "05": "MAIO", "5": "MAIO", "06": "JUNHO", "6": "JUNHO",
    "07": "JULHO", "7": "JULHO", "08": "AGOSTO", "8": "AGOSTO",
    "09": "SETEMBRO", "9": "SETEMBRO", "10": "OUTUBRO",
    "11": "NOVEMBRO", "12": "DEZEMBRO",
}

def _mes_por_numero(mes_num):
    try: return MESES_NUMERO.get(str(int(str(mes_num).strip())))
    except Exception: return None

def _extrair_mes(texto_total):
    linhas = texto_total.splitlines()
    palavras_chave = ["PERIODO", "COMPETENCIA", "MES", "MÊS", "DATA INICIAL", "DATA DE INICIO", "DATA INICIO"]

    for linha in linhas:
        linha_pad = padronizar_nome(linha)
        if not any(padronizar_nome(chave) in linha_pad for chave in palavras_chave):
            continue
        for mes in MESES:
            if re.search(rf"\b{mes}\b", linha_pad): return mes
        m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", linha)
        if m:
            mes = _mes_por_numero(m.group(2))
            if mes: return mes
        m = re.search(r"(?<!\d)(\d{1,2})[/-](\d{2,4})(?!\d)", linha)
        if m:
            mes = _mes_por_numero(m.group(1))
            if mes: return mes

    for linha in linhas:
        linha_pad = padronizar_nome(linha)
        if "IMPRESSO" in linha_pad or "PAGINA" in linha_pad or linha_pad.startswith("PAG "): continue
        for mes in MESES:
            if re.search(rf"\b{mes}\b", linha_pad): return mes

    for linha in linhas:
        linha_pad = padronizar_nome(linha)
        if "IMPRESSO" in linha_pad or "PAGINA" in linha_pad or linha_pad.startswith("PAG "): continue
        m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", linha)
        if m:
            mes = _mes_por_numero(m.group(2))
            if mes: return mes
    return "MÊS NÃO IDENTIFICADO"

def _extrair_tipo_relatorio(texto_total):
    texto_pad = padronizar_nome(texto_total)
    if "ATIVIDADE COLETIVA" in texto_pad or "RELATORIO DE ATIVIDADE COLETIVA" in texto_pad: return "COLETIVO"
    if "ATENDIMENTO INDIVIDUAL" in texto_pad or "RELATORIO DE ATENDIMENTO INDIVIDUAL" in texto_pad: return "INDIVIDUAL"
    return "DESCONHECIDO"

def _limpar_nome_profissional(nome):
    nome = re.sub(r"\s+", " ", str(nome)).strip()
    nome = re.sub(r"\s+\d+[\d\.,]*\s*$", "", nome).strip()
    cortes = ["CBO", "CNS", "CPF", "INE", "CNES", "TOTAL", "QUANTIDADE", "PROCEDIMENTO", "OCUPAÇÃO", "OCUPACAO", "EQUIPE", "UNIDADE"]
    nome_pad = padronizar_nome(nome)
    for corte in cortes:
        m = re.search(rf"\b{re.escape(corte)}\b", nome_pad)
        if m and m.start() > 0:
            nome = nome[:m.start()].strip()
            break
    nome_pad = padronizar_nome(nome)
    nome_pad = re.sub(r"\b\d+\b", " ", nome_pad)
    return ' '.join(nome_pad.split()).strip()

def _eh_nome_resumo_ou_total(nome):
    nome_pad = padronizar_nome(nome)
    if not nome_pad: return True
    termos_resumo = ["TOTAL DA EQUIPE", "TOTAL EQUIPE", "TOTAL DE EQUIPE", "TOTAL GERAL", "TOTAL DO PROFISSIONAL", "TOTAL PROFISSIONAL", "SUBTOTAL", "RESUMO"]
    if any(termo in nome_pad for termo in termos_resumo): return True
    if nome_pad.startswith("TOTAL ") or nome_pad == "TOTAL": return True
    return False

def _nome_profissional_valido(nome, origem_tabela=True):
    nome_pad = padronizar_nome(nome)
    if _eh_nome_resumo_ou_total(nome_pad): return False
    if len(nome_pad) < 5 or re.search(r"\d", nome_pad): return False
    tokens = _tokens_nome(nome_pad)
    if not tokens: return False
    palavras_invalidas = {"ELA", "ROS", "PROFISSIONAL", "QUANTIDADE", "VALOR", "TOTAL", "EQUIPE", "MUNICIPIO", "UNIDADE", "RELATORIO", "PAGINA", "IMPRESSO"}
    if nome_pad in palavras_invalidas or any(t in palavras_invalidas for t in tokens): return False
    if origem_tabela and len(tokens) < 2: return False
    return True

def _parse_valor(valor_texto):
    valor_limpo = re.sub(r"[^0-9]", "", str(valor_texto))
    return int(valor_limpo) if valor_limpo else None

def _extrair_total_geral(linhas):
    for linha in linhas:
        linha_pad = padronizar_nome(linha)
        if "TOTAL GERAL" in linha_pad or linha_pad.startswith("TOTAL"):
            m = re.search(r"(\d[\d\.\,]*)\s*$", linha.strip())
            if m: return _parse_valor(m.group(1))
    return None

def _extrair_profissional_unico(linhas):
    padroes = [r"PROFISSIONAL\s*:?\s*(.+)", r"NOME DO PROFISSIONAL\s*:?\s*(.+)"]
    for linha in linhas:
        linha_sem = linha.strip()
        linha_pad = padronizar_nome(linha_sem)
        if not linha_pad or linha_pad == "PROFISSIONAL": continue
        for padrao in padroes:
            m = re.search(padrao, linha_sem, flags=re.IGNORECASE)
            if m:
                candidato = m.group(1).strip()
                cand_pad = padronizar_nome(candidato)
                if cand_pad in {"TOTAL", "QUANTIDADE", "PRODUCAO", "VALOR"} or _eh_nome_resumo_ou_total(cand_pad): continue
                nome = _limpar_nome_profissional(candidato)
                if _nome_profissional_valido(nome, origem_tabela=False): return nome
    return None

def _extrair_profissionais_tabela(linhas):
    profissionais = {}
    nomes_duplicados = set()
    processando = False
    termos_ignorar = ["IMPRESSO EM", "PAG", "PAGINA", "RELATORIO", "MUNICIPIO", "UNIDADE DE SAUDE", "NIVEL DE DETALHE", "PERIODO", "CNES", "PROFISSIONAL TOTAL", "PROFISSIONAL QUANTIDADE"]

    for linha in linhas:
        linha_original = linha.strip()
        linha_pad = padronizar_nome(linha_original)
        if not linha_pad: continue
        if "TOTAL GERAL" in linha_pad: break
        if _eh_nome_resumo_ou_total(linha_pad): continue
        if any(t in linha_pad for t in termos_ignorar):
            if "PROFISSIONAL" in linha_pad and ("TOTAL" in linha_pad or "QUANTIDADE" in linha_pad): processando = True
            continue
        if linha_pad == "PROFISSIONAL" or linha_pad.startswith("PROFISSIONAL "):
            processando = True
            continue

        m = re.match(r"^(.+?)\s+(\d[\d\.\,]*)$", linha_original)
        if not (processando and m): continue

        nome = _limpar_nome_profissional(m.group(1))
        valor = _parse_valor(m.group(2))
        if not nome or valor is None or not _nome_profissional_valido(nome, origem_tabela=True): continue

        if nome in profissionais:
            profissionais[nome] += valor
            nomes_duplicados.add(nome)
        else: profissionais[nome] = valor

    return profissionais, nomes_duplicados

def transformar_dados_pdf(texto_total):
    texto_pad = padronizar_nome(texto_total)

    marcadores_minimos = ["MINISTERIO DA SAUDE", "SANTO ANTONIO DE JESUS"]
    for marcador in marcadores_minimos:
        if marcador not in texto_pad:
            raise ValueError(f"Estrutura inválida. Marcador ausente: '{marcador}'")

    if "NIVEL DE DETALHE" in texto_pad and "PROFISSIONAL" not in texto_pad:
        raise ValueError("Estrutura inválida. O relatório não está detalhado por profissional.")

    linhas = texto_total.splitlines()
    mes_atual = _extrair_mes(texto_total)
    tipo = _extrair_tipo_relatorio(texto_total)

    if tipo == "DESCONHECIDO":
        raise ValueError("Estrutura inválida. O PDF não é de Atividade Coletiva nem Individual.")
    if mes_atual == "MÊS NÃO IDENTIFICADO":
        raise ValueError("Não foi possível identificar o mês/competência do PDF.")

    profissionais, nomes_duplicados = _extrair_profissionais_tabela(linhas)

    profissionais = {n: v for n, v in profissionais.items() if not _eh_nome_resumo_ou_total(n)}
    nomes_duplicados = {n for n in nomes_duplicados if not _eh_nome_resumo_ou_total(n)}

    if not profissionais:
        nome_unico = _extrair_profissional_unico(linhas)
        total = _extrair_total_geral(linhas)
        if nome_unico and total is not None:
            profissionais[nome_unico] = total

    if not profissionais:
        raise ValueError("Não foi possível identificar profissional e valor no PDF.")

    return tipo, mes_atual, profissionais, nomes_duplicados