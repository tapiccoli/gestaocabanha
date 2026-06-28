import re
import pandas as pd
import streamlit as st

from database import (
    init_db,
    inserir_fila,
    listar_fila,
    listar_animais,
    buscar_animal,
    buscar_principal_json,
    buscar_blocos_json,
    buscar_pedigree,
    atualizar_campos_cadastro,
    excluir_item_fila,
    limpar_fila_por_status,
)
from services.extraction_worker import processar_fila

st.set_page_config(page_title="ERP Cabanha", page_icon="🐴", layout="wide")
init_db()

st.markdown(
    """
<style>
.stButton button { font-weight: 700; border-radius: 8px; }
[data-testid="stMetricValue"] { font-size: 1.25rem; }
.card {
    border: 1px solid rgba(128,128,128,.35);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    background: rgba(128,128,128,.06);
}
.small-label { opacity: .75; font-size: .85rem; }
.big-value { font-size: 1.05rem; font-weight: 700; }
</style>
""",
    unsafe_allow_html=True,
)


def limpar_vazios(valor):
    if valor in [None, "", "xxxx", "xxx", "nan", "None"]:
        return ""
    return valor


def dict_para_dataframe(dados: dict):
    itens = []
    for k, v in dados.items():
        # Remove metadados técnicos e colunas Extra_ geradas por sobras do HTML.
        if k in ["URL"] or str(k).startswith("Extra_"):
            continue
        itens.append({"Campo": k, "Valor": limpar_vazios(v)})
    return pd.DataFrame(itens)


CAMPOS_PRINCIPAL_VISIVEIS = [
    "SBB_Pesquisado", "Status_Extracao", "Extraido_Em",
    "SBB", "Nome", "RP", "Status", "Situacao", "Confirmacao", "Sexo", "Nascimento",
    "SBB_alternativo", "Animal_com_restricao", "Pelagem", "Registro_de_meritos",
    "Res_Dominio", "Ult_transferencia", "Castra", "Data_da_morte", "NMGC",
    "Altura", "Torax", "Canela",
    "Pai_SBB", "Pai_RP", "Pai_Pelagem", "Pai_Nome",
    "Mae_SBB", "Mae_RP", "Mae_Pelagem", "Mae_Nome",
    "Criador_Codigo", "Criador_Nome", "Criador_Afixo", "Criador_Estabelecimento", "Criador_Cidade_estabelecimento",
    "Proprietario_Codigo", "Proprietario_Nome", "Proprietario_Estabelecimento", "Proprietario_Cidade_estabelecimento",
]


def principal_para_dataframe(dados: dict):
    ordenado = {campo: dados.get(campo, "") for campo in CAMPOS_PRINCIPAL_VISIVEIS}
    return dict_para_dataframe(ordenado)


def extrair_registros_numerados(dados: dict, prefixo: str, campos: list[str]):
    padrao = re.compile(rf"^{re.escape(prefixo)}_(\d{{3}})_(.+)$")
    registros = {}
    for chave, valor in dados.items():
        m = padrao.match(chave)
        if not m:
            continue
        idx = int(m.group(1))
        campo = m.group(2)
        registros.setdefault(idx, {})[campo] = limpar_vazios(valor)
    linhas = []
    for idx in sorted(registros):
        linha = {"Nº": idx}
        for campo in campos:
            linha[campo] = registros[idx].get(campo, "")
        if any(str(v).strip() for k, v in linha.items() if k != "Nº"):
            linhas.append(linha)
    return pd.DataFrame(linhas)


def mostrar_df(df, vazio="Sem registros extraídos."):
    if df is None or df.empty:
        st.info(vazio)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def opcoes_animais():
    animais = listar_animais()
    mapa = {}
    for a in animais:
        rotulo = f"{a.get('nome') or 'Sem nome'} | SBB {a.get('sbb')} | RP {a.get('rp') or ''}"
        mapa[rotulo] = a.get("sbb")
    return mapa


def card(label, value):
    st.markdown(
        f"<div class='card'><div class='small-label'>{label}</div><div class='big-value'>{limpar_vazios(value) or '-'}</div></div>",
        unsafe_allow_html=True,
    )


st.title("ERP Cabanha")
st.caption("Cadastro inicial de animais com extração automática da ABCCC, banco interno e visualização completa por abas.")

aba_cad, aba_fila, aba_animais = st.tabs(["Cadastrar por SBB", "Fila de Extração", "Cadastro Completo"])

with aba_cad:
    st.subheader("Informar SBBs para cadastro")
    st.write("Use o botão **+ Adicionar SBB** para montar a lista antes de iniciar a extração.")

    if "sbb_inputs" not in st.session_state:
        st.session_state.sbb_inputs = [""]

    for i, valor in enumerate(st.session_state.sbb_inputs):
        c_sbb, c_remove = st.columns([5, 1])
        with c_sbb:
            st.session_state.sbb_inputs[i] = st.text_input(
                f"SBB {i + 1}", value=valor, key=f"sbb_{i}", placeholder="Ex: B446540"
            ).upper().strip()
        with c_remove:
            st.write("")
            if len(st.session_state.sbb_inputs) > 1 and st.button("Excluir", key=f"rem_{i}", use_container_width=True):
                st.session_state.sbb_inputs.pop(i)
                st.rerun()

    col1, col2, col3 = st.columns([1.3, 1.2, 2])
    with col1:
        if st.button("+ Adicionar SBB", use_container_width=True):
            st.session_state.sbb_inputs.append("")
            st.rerun()
    with col2:
        if st.button("Limpar lista", use_container_width=True):
            st.session_state.sbb_inputs = [""]
            st.rerun()
    with col3:
        if st.button("Cadastrar e colocar na fila", type="primary", use_container_width=True):
            lista = []
            for s in st.session_state.sbb_inputs:
                s = s.strip().upper()
                if s and s not in lista:
                    lista.append(s)
            if not lista:
                st.warning("Informe ao menos um SBB.")
            else:
                for sbb in lista:
                    inserir_fila(sbb)
                st.success(f"{len(lista)} SBB(s) enviado(s) para a fila de extração.")

    st.divider()
    st.info("Nesta etapa o sistema grava os dados em banco. A planilha deixa de ser o destino final e passa a servir apenas como referência de estrutura.")

with aba_fila:
    st.subheader("Fila de Extração")
    c1, c2 = st.columns([1.2, 3])
    with c1:
        if st.button("Processar fila agora", type="primary", use_container_width=True):
            with st.spinner("Extraindo dados em modo oculto/headless e gravando no banco..."):
                qtd = processar_fila(headless=True)
            st.success(f"Processamento finalizado. Registros processados: {qtd}")
            st.rerun()
    with c2:
        st.caption("Depois podemos transformar isso em serviço automático contínuo, mas para testes o botão manual é mais seguro.")

    fila = listar_fila()

    if not fila:
        st.info("Nenhum SBB na fila.")
    else:
        st.markdown("### Itens da fila")
        st.caption("Você pode excluir itens em fila, com erro ou já finalizados. Itens em processamento ficam protegidos.")

        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1:
            if st.button("Limpar itens em fila", use_container_width=True):
                qtd = limpar_fila_por_status(["Em fila"])
                st.success(f"{qtd} item(ns) removido(s).")
                st.rerun()
        with col_l2:
            if st.button("Limpar erros", use_container_width=True):
                qtd = limpar_fila_por_status(["Erro"])
                st.success(f"{qtd} item(ns) removido(s).")
                st.rerun()
        with col_l3:
            if st.button("Limpar finalizados", use_container_width=True):
                qtd = limpar_fila_por_status(["Finalizado"])
                st.success(f"{qtd} item(ns) removido(s).")
                st.rerun()

        st.divider()

        for item in fila:
            status = item.get("status") or ""
            bloqueado = status == "Processando"
            c_id, c_sbb, c_status, c_etapa, c_data, c_del = st.columns([0.6, 1.2, 1.2, 2.3, 1.5, 1])
            with c_id:
                st.write(item.get("id"))
            with c_sbb:
                st.write(f"**{item.get('sbb')}**")
            with c_status:
                st.write(status)
            with c_etapa:
                st.write(item.get("etapa") or "-")
                if item.get("erro"):
                    st.caption(item.get("erro"))
            with c_data:
                st.write(item.get("criado_em") or "-")
            with c_del:
                if st.button("Excluir", key=f"del_fila_{item.get('id')}", disabled=bloqueado, use_container_width=True):
                    ok, msg = excluir_item_fila(item.get("id"))
                    if ok:
                        st.success(msg)
                    else:
                        st.warning(msg)
                    st.rerun()

        with st.expander("Ver tabela técnica da fila"):
            mostrar_df(pd.DataFrame(fila), "Nenhum SBB na fila.")

with aba_animais:
    st.subheader("Selecionar animal cadastrado")
    mapa = opcoes_animais()
    if not mapa:
        st.info("Nenhum animal cadastrado ainda. Cadastre SBBs e processe a fila primeiro.")
        st.stop()

    escolha = st.selectbox("Animal", list(mapa.keys()))
    sbb = mapa[escolha]
    animal = buscar_animal(sbb)
    principal = buscar_principal_json(sbb)
    blocos = buscar_blocos_json(sbb)
    pedigree = buscar_pedigree(sbb)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: card("Nome", animal.get("nome"))
    with c2: card("SBB / RP", f"{animal.get('sbb')} / {animal.get('rp') or '-'}")
    with c3: card("Nascimento", animal.get("nascimento"))
    with c4: card("Idade", animal.get("idade_calculada"))
    with c5: card("Categoria", animal.get("categoria_calculada") or animal.get("categoria_idade"))

    tab_resumo, tab_principal, tab_meritos, tab_padreacoes, tab_desc, tab_irmaos, tab_pedigree = st.tabs([
        "Resumo do Cadastro",
        "Principal ABCCC",
        "Méritos",
        "Padreações",
        "Descendentes",
        "Irmãos",
        "Pedigree",
    ])

    with tab_resumo:
        st.markdown("### Dados do sistema")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            classificacao = st.selectbox(
                "Classificação",
                ["", "Matriz", "Arreio", "Garanhão", "Xucro"],
                index=["", "Matriz", "Arreio", "Garanhão", "Xucro"].index(animal.get("classificacao") or "") if (animal.get("classificacao") or "") in ["", "Matriz", "Arreio", "Garanhão", "Xucro"] else 0,
            )
            manejo = st.selectbox(
                "Manejo",
                ["", "A campo", "Pastagem", "Campo com suplementação", "Cabanha"],
                index=["", "A campo", "Pastagem", "Campo com suplementação", "Cabanha"].index(animal.get("manejo") or "") if (animal.get("manejo") or "") in ["", "A campo", "Pastagem", "Campo com suplementação", "Cabanha"] else 0,
            )
        with col_b:
            apto = st.checkbox("Apto à reprodução", value=bool(animal.get("apto_reproducao")))
            origem = st.selectbox(
                "Origem",
                ["", "Adquirido", "Nascido na Propriedade"],
                index=["", "Adquirido", "Nascido na Propriedade"].index(animal.get("origem") or "") if (animal.get("origem") or "") in ["", "Adquirido", "Nascido na Propriedade"] else 0,
            )
        with col_c:
            valor = st.number_input("Valor de aquisição", min_value=0.0, value=float(animal.get("valor_aquisicao") or 0), step=100.0)
            st.text_input("Pai", value=f"{animal.get('pai_sbb') or ''} - {animal.get('pai_nome') or ''}", disabled=True)
            st.text_input("Mãe", value=f"{animal.get('mae_sbb') or ''} - {animal.get('mae_nome') or ''}", disabled=True)

        if st.button("Salvar dados do cadastro", type="primary"):
            atualizar_campos_cadastro(sbb, classificacao, manejo, apto, origem, valor)
            st.success("Cadastro atualizado.")
            st.rerun()

        st.markdown("### Dados principais extraídos")
        resumo = {
            "SBB": animal.get("sbb"),
            "Nome": animal.get("nome"),
            "RP": animal.get("rp"),
            "Sexo": animal.get("sexo"),
            "Pelagem": animal.get("pelagem"),
            "Status": animal.get("status"),
            "Situação": animal.get("situacao"),
            "Pai_SBB": animal.get("pai_sbb"),
            "Pai_Nome": animal.get("pai_nome"),
            "Mae_SBB": animal.get("mae_sbb"),
            "Mae_Nome": animal.get("mae_nome"),
        }
        mostrar_df(dict_para_dataframe(resumo))

    with tab_principal:
        st.markdown("### Aba Principal")
        st.caption("Somente campos oficiais do cadastro. Colunas técnicas Extra_ foram removidas da visualização e não entram na tabela principal de animais.")
        mostrar_df(principal_para_dataframe(principal))

    with tab_meritos:
        st.markdown("### Resumo de méritos")
        mer = blocos.get("Meritos", {})
        campos_resumo = [
            "P_morfologicos", "P_funcionais", "Total_pontos", "Numero_filhos_contrib", "Numero_netos_contrib",
            "P_filho_contrib", "P_neto_contrib", "P_descendentes", "P_proprios", "Numero_merito",
        ]
        resumo_meritos = {c: mer.get(c, "") for c in campos_resumo if c in mer}
        mostrar_df(dict_para_dataframe(resumo_meritos), "Sem resumo de méritos.")
        st.markdown("### Histórico")
        hist = extrair_registros_numerados(mer, "Historico", ["Prova", "Classificacao", "Premio", "Ciclo", "Pontos"])
        mostrar_df(hist, "Sem histórico de méritos extraído.")

    with tab_padreacoes:
        st.markdown("### Padreações")
        pad = blocos.get("Padreacoes", {})
        st.metric("Total de padreações", limpar_vazios(pad.get("Total_Padreacao")) or "0")
        df_pad = extrair_registros_numerados(pad, "Padreacao", ["SBB", "Nome", "RP", "Inicio_periodo", "Fim_periodo", "OBS"])
        mostrar_df(df_pad)

    with tab_desc:
        st.markdown("### Descendentes")
        desc = blocos.get("Descendentes", {})
        st.metric("Número de filhos", limpar_vazios(desc.get("Numero_Filhos")) or "0")
        df_desc = extrair_registros_numerados(desc, "Descendente", ["SBB", "Nome", "RP", "Sexo", "Data_nascimento", "Pelagem", "Situacao", "Pai_SBB", "Pai_Nome"])
        mostrar_df(df_desc)

    with tab_irmaos:
        irp = blocos.get("Irmaos_Paternos", {})
        irm = blocos.get("Irmaos_Maternos", {})
        sub1, sub2 = st.tabs(["Irmãos Paternos", "Irmãos Maternos"])
        with sub1:
            st.metric("Número de irmãos paternos", limpar_vazios(irp.get("Numero_Irmaos_Paternos")) or "0")
            df_irp = extrair_registros_numerados(irp, "Irmao_Paterno", ["SBB", "Nome", "RP", "Sexo", "Data_nascimento", "Pelagem", "Situacao", "Mae_SBB", "Mae_Nome"])
            mostrar_df(df_irp)
        with sub2:
            st.metric("Número de irmãos maternos", limpar_vazios(irm.get("Numero_Irmaos_Maternos")) or "0")
            df_irm = extrair_registros_numerados(irm, "Irmao_Materno", ["SBB", "Nome", "RP", "Sexo", "Data_nascimento", "Pelagem", "Situacao", "Pai_SBB", "Pai_Nome"])
            mostrar_df(df_irm)

    with tab_pedigree:
        st.markdown("### Pedigree extraído")
        colp1, colp2 = st.columns([1, 2])
        with colp1:
            if st.button("Abrir 6ª geração colorida", use_container_width=True):
                st.warning("Botão reservado. Na próxima etapa conectamos o script do HTML colorido da 6ª geração.")
        with colp2:
            st.caption("A base já está preparada para armazenar o HTML colorido por animal e geração.")
        mostrar_df(pd.DataFrame(pedigree), "Nenhum pedigree extraído para este animal.")
