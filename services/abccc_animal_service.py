import os
import re
import time
from datetime import datetime
from urllib.parse import quote_plus

import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# ============================================================
# CONFIGURAÇÕES
# ============================================================
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CAMINHO_SBB = os.path.join(PASTA_SCRIPT, "sbb.txt")
CAMINHO_SAIDA = os.path.join(PASTA_SCRIPT, "extracao.xlsx")

URL_PESQUISA = "https://www.cavalocrioulo.org.br/pesquisa/pesquisas.php"
URL_MERITOS = "https://www.cavalocrioulo.org.br/pesquisa/meritos_imprmir.php?sbb={sbb}"
URL_PADREACOES = "https://www.cavalocrioulo.org.br/pesquisa/padreacao_imprmir.php?sbb={sbb}"
URL_DESCENDENTES = "https://www.cavalocrioulo.org.br/pesquisa/descendentes_imprmir.php?sbb={sbb}"
URL_IRMAOS_PATERNOS = "https://www.cavalocrioulo.org.br/pesquisa/irmaos_imprmir.php?sbb={sbb}"
URL_IRMAOS_MATERNOS = "https://www.cavalocrioulo.org.br/pesquisa/irmaos_imprmir.php?sbb={sbb}&tipo=m"

VAZIO_PADRAO = "xxxx"
TEMPO_ESPERA_CURTO = 2
TEMPO_ESPERA_PAGINA = 4
ABAS = ["Principal", "Meritos", "Padreacoes", "Descendentes", "Irmaos_Paternos", "Irmaos_Maternos"]

CAMPOS_PRINCIPAL_FIXOS = [
    "SBB", "Nome", "RP",
    "Status", "Situacao", "Confirmacao", "Sexo", "Nascimento",
    "SBB_alternativo", "Animal_com_restricao",
    "Pelagem", "Registro_de_meritos", "Res_Dominio", "Ult_transferencia",
    "Castra", "Data_da_morte", "NMGC",
    "Altura", "Torax", "Canela",
    "Pai_SBB", "Pai_RP", "Pai_Pelagem", "Pai_Nome",
    "Mae_SBB", "Mae_RP", "Mae_Pelagem", "Mae_Nome",
    "Criador_Codigo", "Criador_Nome", "Criador_Afixo", "Criador_Estabelecimento", "Criador_Cidade_estabelecimento",
    "Proprietario_Codigo", "Proprietario_Nome", "Proprietario_Estabelecimento", "Proprietario_Cidade_estabelecimento",
]

CAMPOS_CABECALHO = ["Animal_SBB", "Animal_Nome", "Animal_RP"]
CAMPOS_PADREACAO = ["SBB", "Nome", "RP", "Inicio_periodo", "Fim_periodo", "OBS"]
CAMPOS_DESCENDENTE = ["SBB", "Nome", "RP", "Sexo", "Data_nascimento", "Pelagem", "Situacao", "Pai_SBB", "Pai_Nome"]
CAMPOS_IRMAO_PATERNO = ["SBB", "Nome", "RP", "Sexo", "Data_nascimento", "Pelagem", "Situacao", "Mae_SBB", "Mae_Nome"]
CAMPOS_IRMAO_MATERNO = ["SBB", "Nome", "RP", "Sexo", "Data_nascimento", "Pelagem", "Situacao", "Pai_SBB", "Pai_Nome"]
CAMPOS_MERITOS_RESUMO = [
    "P_morfologicos", "P_funcionais", "Total_pontos",
    "Numero_filhos_contrib", "Numero_netos_contrib", "P_filho_contrib",
    "P_neto_contrib", "P_descendentes", "P_proprios", "Numero_merito",
]
CAMPOS_HISTORICO = ["Prova", "Classificacao", "Premio", "Ciclo", "Pontos"]

# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================
def limpar_texto(texto):
    if texto is None:
        return ""
    texto = str(texto).replace("\xa0", " ").replace("&nbsp;", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def valor_ou_xxxx(texto):
    texto = limpar_texto(texto)
    if not texto or texto.lower() in ["none", "nan", "nat"]:
        return VAZIO_PADRAO
    return texto


def slug_coluna(texto):
    texto = limpar_texto(texto).replace(":", "")
    mapa = {
        "º": "o", "ª": "a", "ç": "c", "Ç": "C", "ã": "a", "Ã": "A", "á": "a", "Á": "A",
        "à": "a", "À": "A", "â": "a", "Â": "A", "é": "e", "É": "E", "ê": "e", "Ê": "E",
        "í": "i", "Í": "I", "ó": "o", "Ó": "O", "ô": "o", "Ô": "O", "õ": "o", "Õ": "O",
        "ú": "u", "Ú": "U", "ñ": "n", "Ñ": "N",
    }
    for k, v in mapa.items():
        texto = texto.replace(k, v)
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto or "Campo"


def adicionar_metadados(sbb, url, status):
    return {
        "SBB_Pesquisado": sbb,
        "URL": url,
        "Status_Extracao": status,
        "Extraido_Em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }


def iniciar_driver(headless=True):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    else:
        options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def abrir_pagina_principal_por_sbb(driver, sbb):
    driver.get(URL_PESQUISA)
    time.sleep(TEMPO_ESPERA_CURTO)
    campo_sbb = driver.find_element(By.ID, "sbb")
    campo_sbb.clear()
    campo_sbb.send_keys(sbb)
    campo_sbb.send_keys(Keys.RETURN)
    time.sleep(TEMPO_ESPERA_PAGINA)
    return driver.page_source, driver.current_url, "OK"


def abrir_url_direta(driver, url):
    try:
        driver.get(url)
        time.sleep(TEMPO_ESPERA_PAGINA)
        return driver.page_source, driver.current_url, "OK"
    except Exception as e:
        return "", url, f"Erro: {e}"

# ============================================================
# EXTRAÇÃO GERAL POR PARES CABEÇALHO/VALOR
# ============================================================
def celula_tem_nomecampo(td):
    """Retorna True somente para células que são realmente rótulos/cabeçalhos da ABCCC.

    Versões anteriores aceitavam qualquer <td> com texto como cabeçalho.
    Isso fazia valores como "Confirmado", "Tostada Bragada" e datas virarem
    colunas Extra_... no cadastro do animal.
    """
    classes = td.get("class") or []
    if any("NomeCampo" in c for c in classes):
        return True
    if td.find(class_=lambda c: c and "NomeCampo" in c):
        return True
    return False


def extrair_pares_de_tabela(table):
    pares = []
    rows = table.find_all("tr")
    for i in range(len(rows) - 1):
        tds_cabecalho = rows[i].find_all("td")
        valores = rows[i + 1].find_all("td", class_=lambda c: c and "NomeResult" in c)

        # Títulos podem estar no próprio TD ou dentro de SPAN class=NomeCampo.
        cabecalhos = [td for td in tds_cabecalho if celula_tem_nomecampo(td)]

        if not cabecalhos or not valores:
            continue

        for pos, th in enumerate(cabecalhos):
            titulo = valor_ou_xxxx(th.get_text(" ", strip=True))
            if titulo == VAZIO_PADRAO:
                continue
            valor = VAZIO_PADRAO
            if pos < len(valores):
                valor = valor_ou_xxxx(valores[pos].get_text(" ", strip=True))
            pares.append((titulo, valor))
    return pares


def secao_atual_antes_da_tabela(table):
    anterior = table.find_previous(lambda tag: tag.name == "td" and tag.get("class") and any(c in ["titpreto", "titverde"] for c in tag.get("class")))
    return limpar_texto(anterior.get_text(" ", strip=True)) if anterior else ""


def mapear_campo_principal(secao, titulo):
    secao_s = slug_coluna(secao).lower()
    titulo_l = slug_coluna(titulo).lower()
    base = {
        "sbb": "SBB", "nome": "Nome", "rp": "RP", "status": "Status", "situacao": "Situacao",
        "confirmacao": "Confirmacao", "sexo": "Sexo", "nascimento": "Nascimento",
        "sbb_alternativo": "SBB_alternativo", "animal_com_restricao": "Animal_com_restricao",
        "registro_de_meritos": "Registro_de_meritos", "res_dominio": "Res_Dominio",
        "ult_transferencia": "Ult_transferencia", "castra": "Castra", "data_da_morte": "Data_da_morte",
        "n_m_g_c": "NMGC", "nmgc": "NMGC", "altura": "Altura", "torax": "Torax", "canela": "Canela",
    }
    if titulo_l == "pelagem" and "dados_do_pai" in secao_s:
        return "Pai_Pelagem"
    if titulo_l == "pelagem" and "dados_da_mae" in secao_s:
        return "Mae_Pelagem"
    if titulo_l == "pelagem":
        return "Pelagem"
    if titulo_l in base:
        return base[titulo_l]
    if "dados_do_pai" in secao_s:
        if titulo_l == "sbb_pai": return "Pai_SBB"
        if titulo_l == "rp_pai": return "Pai_RP"
        if titulo_l == "nome_pai": return "Pai_Nome"
    if "dados_da_mae" in secao_s:
        if titulo_l == "sbb_mae": return "Mae_SBB"
        if titulo_l == "rp_mae": return "Mae_RP"
        if titulo_l in ["mome_mae", "nome_mae"]: return "Mae_Nome"
    if "dados_do_criador" in secao_s:
        if titulo_l == "codigo_do_criador": return "Criador_Codigo"
        if titulo_l == "nome_do_criador": return "Criador_Nome"
        if titulo_l == "afixo": return "Criador_Afixo"
        if titulo_l == "estabelecimento": return "Criador_Estabelecimento"
        if titulo_l == "cidade_do_estabelecimento": return "Criador_Cidade_estabelecimento"
    if "dados_do_proprietario" in secao_s:
        if titulo_l == "codigo_do_proprietario": return "Proprietario_Codigo"
        if titulo_l == "nome_do_proprietario": return "Proprietario_Nome"
        if titulo_l in ["eestabelecimento", "estabelecimento"]: return "Proprietario_Estabelecimento"
        if titulo_l == "cidade_estabelecimento": return "Proprietario_Cidade_estabelecimento"
    return f"Extra_{slug_coluna(secao)}_{slug_coluna(titulo)}" if secao else f"Extra_{slug_coluna(titulo)}"


def extrair_principal(html, sbb, url, status):
    linha = adicionar_metadados(sbb, url, status)
    for campo in CAMPOS_PRINCIPAL_FIXOS:
        linha[campo] = VAZIO_PADRAO
    if not html:
        return linha

    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        secao = secao_atual_antes_da_tabela(table)
        for titulo, valor in extrair_pares_de_tabela(table):
            coluna = mapear_campo_principal(secao, titulo)
            # No cadastro principal só entram campos oficiais.
            # Campos não mapeados da página são descartados para não poluir a tela/tabela.
            if coluna in linha:
                linha[coluna] = valor_ou_xxxx(valor)
    return linha

# ============================================================
# CABEÇALHO DAS PÁGINAS DIRETAS
# ============================================================
def extrair_cabecalho_animal(soup):
    dados = {campo: VAZIO_PADRAO for campo in CAMPOS_CABECALHO}
    for table in soup.find_all("table")[:5]:
        pares = extrair_pares_de_tabela(table)
        if not pares:
            continue
        mapa = {slug_coluna(t).lower(): v for t, v in pares}
        if "sbb" in mapa and "nome" in mapa and "rp" in mapa:
            dados["Animal_SBB"] = valor_ou_xxxx(mapa.get("sbb"))
            dados["Animal_Nome"] = valor_ou_xxxx(mapa.get("nome"))
            dados["Animal_RP"] = valor_ou_xxxx(mapa.get("rp"))
            return dados
    return dados

# ============================================================
# PADREAÇÕES: 1 SBB PESQUISADO POR LINHA, PADREAÇÕES EM COLUNAS NUMERADAS
# ============================================================


def extrair_numero_proximo_do_rotulo(soup, padrao):
    """Procura um rótulo textual e retorna o <b> mais próximo na mesma linha."""
    for texto in soup.find_all(string=re.compile(padrao, re.I)):
        tr = texto.find_parent("tr")
        if not tr:
            continue
        b = tr.find("b")
        if b:
            return valor_ou_xxxx(b.get_text(" ", strip=True))
    return VAZIO_PADRAO

def extrair_padreacoes(html, sbb, url, status):
    linha = adicionar_metadados(sbb, url, status)
    if not html:
        return linha
    soup = BeautifulSoup(html, "html.parser")
    linha.update(extrair_cabecalho_animal(soup))

    linha["Total_Padreacao"] = extrair_numero_proximo_do_rotulo(soup, r"Total\s*Padrea|Padreacao|Padreações|Padrea")

    registros = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td", class_=lambda c: c and "NomeResult" in c)
        if len(cells) == 6:
            valores = [valor_ou_xxxx(c.get_text(" ", strip=True)) for c in cells]
            # evita capturar cabeçalho principal de 3 campos ou tabelas não relacionadas
            if valores[0] != VAZIO_PADRAO and re.match(r"^[A-Z*]?\d+|^[A-Z]\d+", valores[0]):
                registros.append(valores)

    if not registros:
        for campo in CAMPOS_PADREACAO:
            linha[f"Padreacao_001_{campo}"] = VAZIO_PADRAO
    else:
        for i, valores in enumerate(registros, start=1):
            for campo, valor in zip(CAMPOS_PADREACAO, valores):
                linha[f"Padreacao_{i:03d}_{campo}"] = valor_ou_xxxx(valor)
    return linha

# ============================================================
# MÉRITOS: RESUMO NOMEADO + HISTÓRICO EM COLUNAS NUMERADAS
# ============================================================
def normalizar_titulo_merito(titulo):
    t = slug_coluna(titulo).lower()
    mapa = {
        "p_morfologicos": "P_morfologicos",
        "p_funcionais": "P_funcionais",
        "total_pontos": "Total_pontos",
        "no_filhos_contrib": "Numero_filhos_contrib",
        "n_filhos_contrib": "Numero_filhos_contrib",
        "numero_filhos_contrib": "Numero_filhos_contrib",
        "no_netos_contrib": "Numero_netos_contrib",
        "n_netos_contrib": "Numero_netos_contrib",
        "numero_netos_contrib": "Numero_netos_contrib",
        "p_filho_contrib": "P_filho_contrib",
        "p_neto_contrib": "P_neto_contrib",
        "p_descendentes": "P_descendentes",
        "p_proprios": "P_proprios",
        "numero_merito": "Numero_merito",
        "numero_meritos": "Numero_merito",
    }
    return mapa.get(t, slug_coluna(titulo))


def extrair_meritos(html, sbb, url, status):
    linha = adicionar_metadados(sbb, url, status)
    for campo in CAMPOS_MERITOS_RESUMO:
        linha[campo] = VAZIO_PADRAO
    if not html:
        return linha
    soup = BeautifulSoup(html, "html.parser")
    linha.update(extrair_cabecalho_animal(soup))

    # Resumo de pontos: pares título/valor lado a lado dentro das linhas.
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) >= 2:
            # anda de 2 em 2: título, valor, título, valor...
            for idx in range(0, len(cells) - 1, 2):
                titulo = valor_ou_xxxx(cells[idx].get_text(" ", strip=True))
                valor = valor_ou_xxxx(cells[idx + 1].get_text(" ", strip=True))
                if titulo == VAZIO_PADRAO:
                    continue
                coluna = normalizar_titulo_merito(titulo)
                if coluna in CAMPOS_MERITOS_RESUMO:
                    linha[coluna] = valor

    # Histórico: linhas com 5 <td> e fonte pequena. Ignora a linha de títulos.
    historicos = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) == 5:
            valores = [valor_ou_xxxx(c.get_text(" ", strip=True)) for c in cells]
            joined = " ".join(valores).lower()
            if "prova" in joined and "classifica" in joined:
                continue
            # precisa ter pelo menos prova ou prêmio real
            if any(v != VAZIO_PADRAO for v in valores):
                # Evita capturar linhas do resumo de mérito, que também podem ter 5 células em alguns HTMLs
                if not any(re.search(r"\b\d{4}\b", v) for v in valores):
                    continue
                historicos.append(valores)

    if not historicos:
        for campo in CAMPOS_HISTORICO:
            linha[f"Historico_001_{campo}"] = VAZIO_PADRAO
    else:
        for i, valores in enumerate(historicos, start=1):
            for campo, valor in zip(CAMPOS_HISTORICO, valores):
                linha[f"Historico_{i:03d}_{campo}"] = valor_ou_xxxx(valor)
    return linha

# ============================================================
# DESCENDENTES: 1 SBB PESQUISADO POR LINHA, FILHOS EM COLUNAS NUMERADAS
# ============================================================
def extrair_descendentes(html, sbb, url, status):
    linha = adicionar_metadados(sbb, url, status)
    if not html:
        return linha
    soup = BeautifulSoup(html, "html.parser")
    linha.update(extrair_cabecalho_animal(soup))

    linha["Numero_Filhos"] = extrair_numero_proximo_do_rotulo(soup, r"Numero\s*Filhos|Número\s*Filhos|N.mero\s*Filhos|Filhos")

    conteudo = soup.find(id="conteudo_lista") or soup
    tabelas = conteudo.find_all("table")
    filhos = []
    i = 0
    while i < len(tabelas):
        pares1 = extrair_pares_de_tabela(tabelas[i])
        mapa1 = {slug_coluna(t).lower(): valor_ou_xxxx(v) for t, v in pares1}
        if "sbb" in mapa1 and "nome" in mapa1 and "rp" in mapa1:
            filho = {campo: VAZIO_PADRAO for campo in CAMPOS_DESCENDENTE}
            filho["SBB"] = mapa1.get("sbb", VAZIO_PADRAO)
            filho["Nome"] = mapa1.get("nome", VAZIO_PADRAO)
            filho["RP"] = mapa1.get("rp", VAZIO_PADRAO)

            if i + 1 < len(tabelas):
                mapa2 = {slug_coluna(t).lower(): valor_ou_xxxx(v) for t, v in extrair_pares_de_tabela(tabelas[i + 1])}
                filho["Sexo"] = mapa2.get("sexo", VAZIO_PADRAO)
                filho["Data_nascimento"] = mapa2.get("data_nascimento", VAZIO_PADRAO)
                filho["Pelagem"] = mapa2.get("pelagem", VAZIO_PADRAO)
                filho["Situacao"] = mapa2.get("situacao", VAZIO_PADRAO)

            if i + 2 < len(tabelas):
                mapa3 = {slug_coluna(t).lower(): valor_ou_xxxx(v) for t, v in extrair_pares_de_tabela(tabelas[i + 2])}
                filho["Pai_SBB"] = mapa3.get("sbb_pai", mapa3.get("sbb_pai", VAZIO_PADRAO))
                # slug de "SBB - pai" vira SBB_pai
                filho["Pai_SBB"] = mapa3.get("sbb_pai", filho["Pai_SBB"])
                filho["Pai_Nome"] = mapa3.get("pai", VAZIO_PADRAO)
            filhos.append(filho)
            i += 3
        else:
            i += 1

    if not filhos:
        for campo in CAMPOS_DESCENDENTE:
            linha[f"Descendente_001_{campo}"] = VAZIO_PADRAO
    else:
        for idx, filho in enumerate(filhos, start=1):
            for campo in CAMPOS_DESCENDENTE:
                linha[f"Descendente_{idx:03d}_{campo}"] = valor_ou_xxxx(filho.get(campo, VAZIO_PADRAO))
    return linha


# ============================================================
# IRMÃOS PATERNOS: 1 SBB PESQUISADO POR LINHA, IRMÃOS EM COLUNAS NUMERADAS
# Estrutura igual à aba Descendentes, mas o terceiro bloco traz SBB - mãe / mãe.
# ============================================================
def extrair_irmaos_paternos(html, sbb, url, status):
    linha = adicionar_metadados(sbb, url, status)
    if not html:
        return linha
    soup = BeautifulSoup(html, "html.parser")
    linha.update(extrair_cabecalho_animal(soup))

    linha["Numero_Irmaos_Paternos"] = extrair_numero_proximo_do_rotulo(soup, r"Numero\s*Irm|Número\s*Irm|N.mero\s*Irm|Irmãos")

    conteudo = soup.find(id="conteudo_lista") or soup
    tabelas = conteudo.find_all("table")
    irmaos = []
    i = 0
    while i < len(tabelas):
        pares1 = extrair_pares_de_tabela(tabelas[i])
        mapa1 = {slug_coluna(t).lower(): valor_ou_xxxx(v) for t, v in pares1}
        if "sbb" in mapa1 and "nome" in mapa1 and "rp" in mapa1:
            irmao = {campo: VAZIO_PADRAO for campo in CAMPOS_IRMAO_PATERNO}
            irmao["SBB"] = mapa1.get("sbb", VAZIO_PADRAO)
            irmao["Nome"] = mapa1.get("nome", VAZIO_PADRAO)
            irmao["RP"] = mapa1.get("rp", VAZIO_PADRAO)

            if i + 1 < len(tabelas):
                mapa2 = {slug_coluna(t).lower(): valor_ou_xxxx(v) for t, v in extrair_pares_de_tabela(tabelas[i + 1])}
                irmao["Sexo"] = mapa2.get("sexo", VAZIO_PADRAO)
                irmao["Data_nascimento"] = mapa2.get("data_nascimento", VAZIO_PADRAO)
                irmao["Pelagem"] = mapa2.get("pelagem", VAZIO_PADRAO)
                irmao["Situacao"] = mapa2.get("situacao", VAZIO_PADRAO)

            if i + 2 < len(tabelas):
                mapa3 = {slug_coluna(t).lower(): valor_ou_xxxx(v) for t, v in extrair_pares_de_tabela(tabelas[i + 2])}
                # No HTML vem como "SBB - mãe" e "mãe".
                irmao["Mae_SBB"] = mapa3.get("sbb_mae", VAZIO_PADRAO)
                irmao["Mae_Nome"] = mapa3.get("mae", VAZIO_PADRAO)

            irmaos.append(irmao)
            i += 3
        else:
            i += 1

    if not irmaos:
        for campo in CAMPOS_IRMAO_PATERNO:
            linha[f"Irmao_Paterno_001_{campo}"] = VAZIO_PADRAO
    else:
        for idx, irmao in enumerate(irmaos, start=1):
            for campo in CAMPOS_IRMAO_PATERNO:
                linha[f"Irmao_Paterno_{idx:03d}_{campo}"] = valor_ou_xxxx(irmao.get(campo, VAZIO_PADRAO))
    return linha



# ============================================================
# IRMÃOS MATERNOS: 1 SBB PESQUISADO POR LINHA, IRMÃOS EM COLUNAS NUMERADAS
# URL com complemento &tipo=m.
# Estrutura igual à aba Descendentes: terceiro bloco traz SBB - pai / pai.
# ============================================================
def extrair_irmaos_maternos(html, sbb, url, status):
    linha = adicionar_metadados(sbb, url, status)
    if not html:
        return linha
    soup = BeautifulSoup(html, "html.parser")
    linha.update(extrair_cabecalho_animal(soup))

    linha["Numero_Irmaos_Maternos"] = extrair_numero_proximo_do_rotulo(soup, r"Numero\s*Irm|Número\s*Irm|N.mero\s*Irm|Irmãos")

    conteudo = soup.find(id="conteudo_lista") or soup
    tabelas = conteudo.find_all("table")
    irmaos = []
    i = 0
    while i < len(tabelas):
        pares1 = extrair_pares_de_tabela(tabelas[i])
        mapa1 = {slug_coluna(t).lower(): valor_ou_xxxx(v) for t, v in pares1}
        if "sbb" in mapa1 and "nome" in mapa1 and "rp" in mapa1:
            irmao = {campo: VAZIO_PADRAO for campo in CAMPOS_IRMAO_MATERNO}
            irmao["SBB"] = mapa1.get("sbb", VAZIO_PADRAO)
            irmao["Nome"] = mapa1.get("nome", VAZIO_PADRAO)
            irmao["RP"] = mapa1.get("rp", VAZIO_PADRAO)

            if i + 1 < len(tabelas):
                mapa2 = {slug_coluna(t).lower(): valor_ou_xxxx(v) for t, v in extrair_pares_de_tabela(tabelas[i + 1])}
                irmao["Sexo"] = mapa2.get("sexo", VAZIO_PADRAO)
                irmao["Data_nascimento"] = mapa2.get("data_nascimento", VAZIO_PADRAO)
                irmao["Pelagem"] = mapa2.get("pelagem", VAZIO_PADRAO)
                irmao["Situacao"] = mapa2.get("situacao", VAZIO_PADRAO)

            if i + 2 < len(tabelas):
                mapa3 = {slug_coluna(t).lower(): valor_ou_xxxx(v) for t, v in extrair_pares_de_tabela(tabelas[i + 2])}
                # No HTML dos irmãos maternos vem como "SBB - pai" e "pai".
                irmao["Pai_SBB"] = mapa3.get("sbb_pai", VAZIO_PADRAO)
                irmao["Pai_Nome"] = mapa3.get("pai", VAZIO_PADRAO)

            irmaos.append(irmao)
            i += 3
        else:
            i += 1

    if not irmaos:
        for campo in CAMPOS_IRMAO_MATERNO:
            linha[f"Irmao_Materno_001_{campo}"] = VAZIO_PADRAO
    else:
        for idx, irmao in enumerate(irmaos, start=1):
            for campo in CAMPOS_IRMAO_MATERNO:
                linha[f"Irmao_Materno_{idx:03d}_{campo}"] = valor_ou_xxxx(irmao.get(campo, VAZIO_PADRAO))
    return linha

# ============================================================
# SALVAMENTO
# ============================================================
def normalizar_df(linhas, colunas_fixadas=None):
    df = pd.DataFrame(linhas).fillna(VAZIO_PADRAO)
    for col in df.columns:
        df[col] = df[col].apply(valor_ou_xxxx)
    inicio = [c for c in ["SBB_Pesquisado", "URL", "Status_Extracao", "Extraido_Em"] if c in df.columns]
    fixas = [c for c in (colunas_fixadas or []) if c in df.columns and c not in inicio]
    outras = [c for c in df.columns if c not in inicio and c not in fixas]
    return df[inicio + fixas + outras]


def salvar_excel_abas(dados_por_aba, caminho_base):
    nome_base, extensao = os.path.splitext(caminho_base)
    contador = 1
    while True:
        caminho_final = caminho_base if contador == 1 else f"{nome_base}{contador}{extensao}"
        try:
            with pd.ExcelWriter(caminho_final, engine="openpyxl") as writer:
                normalizar_df(dados_por_aba["Principal"], CAMPOS_PRINCIPAL_FIXOS).to_excel(writer, sheet_name="Principal", index=False)
                normalizar_df(dados_por_aba["Meritos"], CAMPOS_CABECALHO + CAMPOS_MERITOS_RESUMO).to_excel(writer, sheet_name="Meritos", index=False)
                normalizar_df(dados_por_aba["Padreacoes"], CAMPOS_CABECALHO + ["Total_Padreacao"]).to_excel(writer, sheet_name="Padreacoes", index=False)
                normalizar_df(dados_por_aba["Descendentes"], CAMPOS_CABECALHO + ["Numero_Filhos"]).to_excel(writer, sheet_name="Descendentes", index=False)
                normalizar_df(dados_por_aba["Irmaos_Paternos"], CAMPOS_CABECALHO + ["Numero_Irmaos_Paternos"]).to_excel(writer, sheet_name="Irmaos_Paternos", index=False)
                normalizar_df(dados_por_aba["Irmaos_Maternos"], CAMPOS_CABECALHO + ["Numero_Irmaos_Maternos"]).to_excel(writer, sheet_name="Irmaos_Maternos", index=False)
            print(f"Planilha salva em: {caminho_final}")
            return caminho_final
        except PermissionError:
            contador += 1

# ============================================================
# EXECUÇÃO
# ============================================================
def main():
    if not os.path.exists(CAMINHO_SBB):
        raise FileNotFoundError(f"Arquivo sbb.txt não encontrado na pasta do script: {PASTA_SCRIPT}")
    with open(CAMINHO_SBB, "r", encoding="utf-8") as file:
        lista_sbb = [linha.strip() for linha in file.readlines() if linha.strip()]
    if not lista_sbb:
        raise ValueError("O arquivo sbb.txt está vazio.")

    dados_por_aba = {aba: [] for aba in ABAS}
    driver = iniciar_driver()
    try:
        for contador, sbb in enumerate(lista_sbb, start=1):
            print("=" * 80)
            print(f"Processando {contador}/{len(lista_sbb)} | SBB: {sbb}")

            try:
                html, url, status = abrir_pagina_principal_por_sbb(driver, sbb)
            except Exception as e:
                html, url, status = "", URL_PESQUISA, f"Erro: {e}"
            dados_por_aba["Principal"].append(extrair_principal(html, sbb, url, status))

            url_meritos = URL_MERITOS.format(sbb=quote_plus(sbb))
            html, url, status = abrir_url_direta(driver, url_meritos)
            dados_por_aba["Meritos"].append(extrair_meritos(html, sbb, url, status))

            url_padreacoes = URL_PADREACOES.format(sbb=quote_plus(sbb))
            html, url, status = abrir_url_direta(driver, url_padreacoes)
            dados_por_aba["Padreacoes"].append(extrair_padreacoes(html, sbb, url, status))

            url_descendentes = URL_DESCENDENTES.format(sbb=quote_plus(sbb))
            html, url, status = abrir_url_direta(driver, url_descendentes)
            dados_por_aba["Descendentes"].append(extrair_descendentes(html, sbb, url, status))

            url_irmaos_paternos = URL_IRMAOS_PATERNOS.format(sbb=quote_plus(sbb))
            html, url, status = abrir_url_direta(driver, url_irmaos_paternos)
            dados_por_aba["Irmaos_Paternos"].append(extrair_irmaos_paternos(html, sbb, url, status))

            url_irmaos_maternos = URL_IRMAOS_MATERNOS.format(sbb=quote_plus(sbb))
            html, url, status = abrir_url_direta(driver, url_irmaos_maternos)
            dados_por_aba["Irmaos_Maternos"].append(extrair_irmaos_maternos(html, sbb, url, status))

            print(f"OK: {sbb}")
    finally:
        driver.quit()

    caminho_final = salvar_excel_abas(dados_por_aba, CAMINHO_SAIDA)
    print("=" * 80)
    print("Extração finalizada.")
    print(f"Arquivo gerado: {caminho_final}")



def extrair_todos_dados_animal(driver, sbb):
    """Extrai todas as abas equivalentes à planilha, mas retorna dicionários para gravação em banco."""
    try:
        html, url, status = abrir_pagina_principal_por_sbb(driver, sbb)
    except Exception as e:
        html, url, status = "", URL_PESQUISA, f"Erro: {e}"
    principal = extrair_principal(html, sbb, url, status)

    blocos = {}
    url_meritos = URL_MERITOS.format(sbb=quote_plus(sbb))
    html, url, status = abrir_url_direta(driver, url_meritos)
    blocos["Meritos"] = extrair_meritos(html, sbb, url, status)

    url_padreacoes = URL_PADREACOES.format(sbb=quote_plus(sbb))
    html, url, status = abrir_url_direta(driver, url_padreacoes)
    blocos["Padreacoes"] = extrair_padreacoes(html, sbb, url, status)

    url_descendentes = URL_DESCENDENTES.format(sbb=quote_plus(sbb))
    html, url, status = abrir_url_direta(driver, url_descendentes)
    blocos["Descendentes"] = extrair_descendentes(html, sbb, url, status)

    url_irmaos_paternos = URL_IRMAOS_PATERNOS.format(sbb=quote_plus(sbb))
    html, url, status = abrir_url_direta(driver, url_irmaos_paternos)
    blocos["Irmaos_Paternos"] = extrair_irmaos_paternos(html, sbb, url, status)

    url_irmaos_maternos = URL_IRMAOS_MATERNOS.format(sbb=quote_plus(sbb))
    html, url, status = abrir_url_direta(driver, url_irmaos_maternos)
    blocos["Irmaos_Maternos"] = extrair_irmaos_maternos(html, sbb, url, status)

    return principal, blocos

if __name__ == "__main__":
    main()
