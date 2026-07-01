"""Tabela padrão do ERP.

Primeira versão simples: centraliza o st.dataframe e prepara exportação/filtros futuros.
"""

import pandas as pd
import streamlit as st


def tabela_padrao(dados, mensagem_vazio="Nenhum registro encontrado.", *, key=None):
    df = pd.DataFrame(dados)
    if df.empty:
        st.info(mensagem_vazio)
        return df
    st.dataframe(df, use_container_width=True, hide_index=True, key=key)
    return df
