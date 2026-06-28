"""Dicionário central de tradução dos campos extraídos da ABCCC.

Regra do projeto:
- Campo técnico: nome que vem do robô/extrator.
- Rótulo: nome amigável exibido ao usuário.
- Campos técnicos do robô não aparecem na ficha do animal.
"""

CAMPOS_TECNICOS_EXCLUIR = {
    "SBB_Pesquisado",
    "Status_Extracao",
    "Extraido_Em",
    "URL",
}

CAMPOS_PRINCIPAL = {
    "SBB": "SBB",
    "Nome": "Nome",
    "RP": "RP",
    "Status": "Status",
    "Situacao": "Situação",
    "Confirmacao": "Confirmação",
    "Sexo": "Sexo",
    "Nascimento": "Nascimento",
    "SBB_alternativo": "SBB Alternativo",
    "Animal_com_restricao": "Animal com Restrição?",
    "Pelagem": "Pelagem",
    "Registro_de_meritos": "Registro de Mérito",
    "Res_Dominio": "Reserva de Domínio",
    "Ult_transferencia": "Última Transferência",
    "Castra": "Castrado",
    "Data_da_morte": "Data da Morte",
    "NMGC": "NMGC",
    "Altura": "Altura",
    "Torax": "Tórax",
    "Canela": "Canela",
    "Pai_SBB": "SBB do Pai",
    "Pai_RP": "RP do Pai",
    "Pai_Pelagem": "Pelagem do Pai",
    "Pai_Nome": "Nome do Pai",
    "Mae_SBB": "SBB da Mãe",
    "Mae_RP": "RP da Mãe",
    "Mae_Pelagem": "Pelagem da Mãe",
    "Mae_Nome": "Nome da Mãe",
    "Criador_Codigo": "Código do Criador",
    "Criador_Nome": "Nome do Criador",
    "Criador_Afixo": "Afixo do Criador",
    "Criador_Estabelecimento": "Estabelecimento do Criador",
    "Criador_Cidade_estabelecimento": "Cidade do Estabelecimento do Criador",
    "Proprietario_Codigo": "Código do Proprietário",
    "Proprietario_Nome": "Nome do Proprietário",
    "Proprietario_Estabelecimento": "Estabelecimento do Proprietário",
    "Proprietario_Cidade_estabelecimento": "Cidade do Estabelecimento Proprietário",
}

CAMPOS_MERITOS = {
    "P_morfologicos": "Pontos Morfológicos",
    "P_funcionais": "Pontos Funcionais",
    "Total_pontos": "Total Pontos",
    "Numero_filhos_contrib": "Número de Filhos Contribuintes",
    "Numero_netos_contrib": "Número de Netos Contribuintes",
    "P_filho_contrib": "Pontos de Filhos Contribuintes",
    "P_neto_contrib": "Pontos de Netos Contribuintes",
    "P_descendentes": "Pontos de Descendentes",
    "P_proprios": "Pontos Próprios",
    "Numero_merito": "Número no Registro de Mérito",
}

CAMPOS_HISTORICO = {
    "Prova": "Prova",
    "Classificacao": "Classificação",
    "Premio": "Prêmio",
    "Ciclo": "Ciclo",
    "Pontos": "Pontos",
}

CAMPOS_PADREACOES = {
    "SBB": "SBB",
    "Nome": "Nome",
    "RP": "RP",
    "Inicio_periodo": "Início Período",
    "Fim_periodo": "Fim Período",
    "OBS": "OBS",
}

CAMPOS_DESCENDENTES = {
    "SBB": "SBB",
    "Nome": "Nome",
    "RP": "RP",
    "Sexo": "Sexo",
    "Data_nascimento": "Data de Nascimento",
    "Pelagem": "Pelagem",
    "Situacao": "Situação",
    "Pai_SBB": "SBB do Pai",
    "Pai_Nome": "Nome do Pai",
    "Mae_SBB": "SBB da Mãe",
    "Mae_Nome": "Nome da Mãe",
}

CAMPOS_PEDIGREE_VISIVEIS = {
    "bloco": "Geração",
    "texto_completo": "Dados",
}


def traduzir_colunas_df(df, mapa):
    """Renomeia colunas de um DataFrame usando o mapa informado."""
    if df is None or df.empty:
        return df
    return df.rename(columns={k: v for k, v in mapa.items() if k in df.columns})


def traduzir_dict_para_linhas(dados, mapa):
    """Converte um dict técnico em linhas Campo/Valor já com rótulos amigáveis."""
    linhas = []
    for campo_tecnico, rotulo in mapa.items():
        valor = dados.get(campo_tecnico, "") if dados else ""
        linhas.append({"Campo": rotulo, "Valor": valor})
    return linhas

# Mapa oficial informado pelo usuário para a coluna visual "Geração" da aba Pedigree.
# O número do item continua salvo no banco, mas não aparece no app.
PEDIGREE_GERACAO_POR_ITEM = {
    1: "(SBB)",
    2: "(NOME)",
    3: "(RP)",
    4: "(Quinta Geração)",
    5: "(Quarta Geração)",
    6: "(Quinta Geração)",
    7: "(Terceira Geração)",
    8: "(Quinta Geração)",
    9: "(Quarta Geração)",
    10: "(Quinta Geração)",
    11: "(Segunda Geração)",
    12: "(Quinta Geração)",
    13: "(Quarta Geração)",
    14: "(Quinta Geração)",
    15: "(Terceira Geração)",
    16: "(Quinta Geração)",
    17: "(Quarta Geração)",
    18: "(Quinta Geração)",
    19: "(Dados Animal)",
    21: "(Quinta Geração)",
    22: "(Quarta Geração)",
    23: "(Quinta Geração)",
    24: "(Terceira Geração)",
    25: "(Quinta Geração)",
    26: "(Quarta Geração)",
    27: "(Quinta Geração)",
    28: "(Segunda Geração)",
    29: "(Quinta Geração)",
    30: "(Quarta Geração)",
    31: "(Quinta Geração)",
    32: "(Terceira Geração)",
    33: "(Quinta Geração)",
    34: "(Quarta Geração)",
    35: "(Quinta Geração)",
    36: "(Sexta Geração)",
    37: "(Sexta Geração)",
    38: "(Sexta Geração)",
    39: "(Sexta Geração)",
    40: "(Sexta Geração)",
    41: "(Sexta Geração)",
    42: "(Sexta Geração)",
    43: "(Sexta Geração)",
    44: "(Sexta Geração)",
    45: "(Sexta Geração)",
    46: "(Sexta Geração)",
    47: "(Sexta Geração)",
    48: "(Sexta Geração)",
    49: "(Sexta Geração)",
    50: "(Sexta Geração)",
    51: "(Sexta Geração)",
    84: "(Sexta Geração)",
    85: "(Sexta Geração)",
    86: "(Sexta Geração)",
    87: "(Sexta Geração)",
    88: "(Sexta Geração)",
    89: "(Sexta Geração)",
    90: "(Sexta Geração)",
    91: "(Sexta Geração)",
    92: "(Sexta Geração)",
    93: "(Sexta Geração)",
    94: "(Sexta Geração)",
    95: "(Sexta Geração)",
    96: "(Sexta Geração)",
    97: "(Sexta Geração)",
    98: "(Sexta Geração)",
    99: "(Sexta Geração)",
}

PEDIGREE_ITENS_NAO_MOSTRAR = {20}


def montar_pedigree_visivel(registros):
    """Monta a versão limpa da aba Pedigree para exibição no Streamlit.

    O banco mantém numero_item, nome, sbb e pelagem, mas a tela mostra apenas:
    - Geração: conforme mapa oficial definido pelo usuário
    - Dados: conteúdo visível do animal/ancestral
    """
    linhas = []
    for registro in registros or []:
        try:
            numero_item = int(registro.get("numero_item"))
        except (TypeError, ValueError):
            continue

        if numero_item in PEDIGREE_ITENS_NAO_MOSTRAR:
            continue

        dados = registro.get("texto_completo") or registro.get("nome") or ""
        if not dados or str(dados).strip().lower() in {"xxx", "xxxx", "none", "nan"}:
            continue

        linhas.append({
            "Geração": PEDIGREE_GERACAO_POR_ITEM.get(numero_item, registro.get("bloco") or "Pedigree"),
            "Dados": dados,
        })
    return linhas
