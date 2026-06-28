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
