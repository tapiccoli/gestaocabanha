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
    listar_historico_status,
    salvar_venda_animal,
    listar_vendas_animal,
    salvar_parceria_animal,
    listar_parcerias_animal,
)
from services.extraction_worker import processar_fila
from utils.campos_abccc import (
    CAMPOS_TECNICOS_EXCLUIR,
    CAMPOS_PRINCIPAL,
    CAMPOS_MERITOS,
    CAMPOS_HISTORICO,
    CAMPOS_PADREACOES,
    CAMPOS_DESCENDENTES,
    CAMPOS_PEDIGREE_VISIVEIS,
    traduzir_colunas_df,
    traduzir_dict_para_linhas,
)

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


def dict_para_dataframe(dados: dict, mapa_rotulos: dict | None = None):
    itens = []
    mapa_rotulos = mapa_rotulos or {}
    for k, v in dados.items():
        # Remove metadados técnicos do robô e colunas Extra_ geradas por sobras do HTML.
        if k in CAMPOS_TECNICOS_EXCLUIR or str(k).startswith("Extra_"):
            continue
        itens.append({"Campo": mapa_rotulos.get(k, k), "Valor": limpar_vazios(v)})
    return pd.DataFrame(itens)


def principal_para_dataframe(dados: dict):
    linhas = traduzir_dict_para_linhas(dados or {}, CAMPOS_PRINCIPAL)
    for linha in linhas:
        linha["Valor"] = limpar_vazios(linha["Valor"])
    return pd.DataFrame(linhas)

def extrair_registros_numerados(dados: dict, prefixo: str, campos: list[str], mapa_rotulos: dict | None = None):
    mapa_rotulos = mapa_rotulos or {}
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
            linha[mapa_rotulos.get(campo, campo)] = registros[idx].get(campo, "")
        if any(str(v).strip() for k, v in linha.items() if k != "Nº"):
            linhas.append(linha)
    return pd.DataFrame(linhas)


def mostrar_df(df, vazio="Sem registros extraídos."):
    if df is None or df.empty:
        st.info(vazio)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def opcoes_animais(incluir_inativos=True):
    animais = listar_animais(incluir_inativos=incluir_inativos)
    mapa = {}
    for a in animais:
        status = a.get("status_ecossistema") or "Ativo na cabanha"
        rotulo = f"{a.get('nome') or 'Sem nome'} | SBB {a.get('sbb')} | RP {a.get('rp') or ''} | {status}"
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
    incluir_inativos = st.checkbox("Incluir vendidos/entregues e inativos na consulta", value=True)
    mapa = opcoes_animais(incluir_inativos=incluir_inativos)
    if not mapa:
        st.info("Nenhum animal cadastrado ainda. Cadastre SBBs e processe a fila primeiro.")
        st.stop()

    escolha = st.selectbox("Animal", list(mapa.keys()))
    sbb = mapa[escolha]
    animal = buscar_animal(sbb)
    principal = buscar_principal_json(sbb)
    blocos = buscar_blocos_json(sbb)
    pedigree = buscar_pedigree(sbb)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: card("Nome", animal.get("nome"))
    with c2: card("SBB / RP", f"{animal.get('sbb')} / {animal.get('rp') or '-'}")
    with c3: card("Nascimento", animal.get("nascimento"))
    with c4: card("Idade", animal.get("idade_calculada"))
    with c5: card("Categoria", animal.get("categoria_calculada") or animal.get("categoria_idade"))
    with c6: card("Status", animal.get("status_ecossistema") or "Ativo na cabanha")

    tab_resumo, tab_principal, tab_meritos, tab_padreacoes, tab_desc, tab_irmaos, tab_pedigree, tab_venda_parceria, tab_historico = st.tabs([
        "Resumo do Cadastro",
        "Principal ABCCC",
        "Méritos",
        "Padreações",
        "Descendentes",
        "Irmãos",
        "Pedigree",
        "Venda / Parceria",
        "Histórico",
    ])

    with tab_resumo:
        st.markdown("### Dados manuais da cabanha")
        col_a, col_b, col_c = st.columns(3)

        def indice_opcao(opcoes, valor):
            return opcoes.index(valor) if valor in opcoes else 0

        with col_a:
            op_status_ecossistema = [
                "Ativo na cabanha",
                "Em parceria",
                "Animal de terceiro",
                "Vendido - aguardando entrega",
                "Vendido e entregue",
                "Morto",
                "Inativo histórico",
            ]
            status_ecossistema = st.selectbox(
                "Status no ecossistema", op_status_ecossistema,
                index=indice_opcao(op_status_ecossistema, animal.get("status_ecossistema") or "Ativo na cabanha"),
                help="Vendido e entregue sai de manejo, custos futuros, sanidade e reprodução, mas fica no histórico.",
            )
            op_tipo_vinculo = ["", "Próprio", "Terceiro", "Parceria"]
            tipo_vinculo = st.selectbox(
                "Tipo de vínculo", op_tipo_vinculo,
                index=indice_opcao(op_tipo_vinculo, animal.get("tipo_vinculo") or ""),
            )
            op_origem = ["", "Criação Própria", "Animal Adquirido", "Animal em Parceria", "Animal de Terceiro"]
            origem = st.selectbox(
                "Origem", op_origem,
                index=indice_opcao(op_origem, animal.get("origem") or ""),
            )
            op_classificacao = ["", "Matriz", "Arreio", "Garanhão", "Xucro"]
            classificacao = st.selectbox(
                "Classificação de uso", op_classificacao,
                index=indice_opcao(op_classificacao, animal.get("classificacao") or ""),
            )
        with col_b:
            op_mansidao = ["", "Xucro", "Manso de baixo", "Domado"]
            mansidao = st.selectbox(
                "Mansidão", op_mansidao,
                index=indice_opcao(op_mansidao, animal.get("mansidao") or ""),
            )
            op_manejo = ["", "A campo", "Pastagem", "Campo com suplementação", "Cabanha", "Doma", "Treinamento", "Central reprodutiva"]
            manejo = st.selectbox(
                "Manejo atual", op_manejo,
                index=indice_opcao(op_manejo, animal.get("manejo") or ""),
            )
            valor = st.number_input("Valor de aquisição", min_value=0.0, value=float(animal.get("valor_aquisicao") or 0), step=100.0)
        with col_c:
            castrado = st.checkbox("Castrado", value=bool(animal.get("castrado")))
            apto = st.checkbox("Ativo na reprodução", value=bool(animal.get("apto_reproducao")))
            st.text_input("Categoria calculada", value=animal.get("categoria_calculada") or "", disabled=True)

        observacoes = st.text_area(
            "Observações do cadastro",
            value=animal.get("observacoes") or "",
            placeholder="Comentários de compra, insights de cruzamento, informações de manejo, observações gerais...",
        )

        if st.button("Salvar dados do cadastro", type="primary"):
            atualizar_campos_cadastro(
                sbb=sbb,
                status_ecossistema=status_ecossistema,
                tipo_vinculo=tipo_vinculo,
                origem=origem,
                classificacao=classificacao,
                mansidao=mansidao,
                manejo=manejo,
                castrado=castrado,
                apto_reproducao=apto,
                valor_aquisicao=valor,
                observacoes=observacoes,
            )
            st.success("Cadastro atualizado.")
            st.rerun()

        st.markdown("### Filiação")
        cf1, cf2 = st.columns(2)
        with cf1:
            st.text_input("Pai", value=f"{animal.get('pai_sbb') or ''} - {animal.get('pai_nome') or ''}", disabled=True)
        with cf2:
            st.text_input("Mãe", value=f"{animal.get('mae_sbb') or ''} - {animal.get('mae_nome') or ''}", disabled=True)

        st.markdown("### Dados principais extraídos")
        resumo = {
            "SBB": animal.get("sbb"),
            "Nome": animal.get("nome"),
            "RP": animal.get("rp"),
            "Sexo": animal.get("sexo"),
            "Pelagem": animal.get("pelagem"),
            "Status": animal.get("status"),
            "Situação": animal.get("situacao"),
            "Status no Ecossistema": animal.get("status_ecossistema") or "Ativo na cabanha",
            "Tipo de Vínculo": animal.get("tipo_vinculo"),
            "Origem": animal.get("origem"),
            "Manejo": animal.get("manejo"),
            "Mansidão": animal.get("mansidao"),
            "SBB do Pai": animal.get("pai_sbb"),
            "Nome do Pai": animal.get("pai_nome"),
            "SBB da Mãe": animal.get("mae_sbb"),
            "Nome da Mãe": animal.get("mae_nome"),
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
        mostrar_df(dict_para_dataframe(resumo_meritos, CAMPOS_MERITOS), "Sem resumo de méritos.")
        st.markdown("### Histórico")
        hist = extrair_registros_numerados(mer, "Historico", ["Prova", "Classificacao", "Premio", "Ciclo", "Pontos"], CAMPOS_HISTORICO)
        mostrar_df(hist, "Sem histórico de méritos extraído.")

    with tab_padreacoes:
        st.markdown("### Padreações")
        pad = blocos.get("Padreacoes", {})
        st.metric("Total de padreações", limpar_vazios(pad.get("Total_Padreacao")) or "0")
        df_pad = extrair_registros_numerados(pad, "Padreacao", ["SBB", "Nome", "RP", "Inicio_periodo", "Fim_periodo", "OBS"], CAMPOS_PADREACOES)
        mostrar_df(df_pad)

    with tab_desc:
        st.markdown("### Descendentes")
        desc = blocos.get("Descendentes", {})
        st.metric("Número de filhos", limpar_vazios(desc.get("Numero_Filhos")) or "0")
        df_desc = extrair_registros_numerados(desc, "Descendente", ["SBB", "Nome", "RP", "Sexo", "Data_nascimento", "Pelagem", "Situacao", "Pai_SBB", "Pai_Nome", "Mae_SBB", "Mae_Nome"], CAMPOS_DESCENDENTES)
        mostrar_df(df_desc)

    with tab_irmaos:
        irp = blocos.get("Irmaos_Paternos", {})
        irm = blocos.get("Irmaos_Maternos", {})
        sub1, sub2 = st.tabs(["Irmãos Paternos", "Irmãos Maternos"])
        with sub1:
            st.metric("Número de irmãos paternos", limpar_vazios(irp.get("Numero_Irmaos_Paternos")) or "0")
            df_irp = extrair_registros_numerados(irp, "Irmao_Paterno", ["SBB", "Nome", "RP", "Sexo", "Data_nascimento", "Pelagem", "Situacao", "Mae_SBB", "Mae_Nome"], CAMPOS_DESCENDENTES)
            mostrar_df(df_irp)
        with sub2:
            st.metric("Número de irmãos maternos", limpar_vazios(irm.get("Numero_Irmaos_Maternos")) or "0")
            df_irm = extrair_registros_numerados(irm, "Irmao_Materno", ["SBB", "Nome", "RP", "Sexo", "Data_nascimento", "Pelagem", "Situacao", "Pai_SBB", "Pai_Nome"], CAMPOS_DESCENDENTES)
            mostrar_df(df_irm)

    with tab_pedigree:
        st.markdown("### Pedigree extraído")
        colp1, colp2 = st.columns([1, 2])
        with colp1:
            if st.button("Abrir 6ª geração colorida", use_container_width=True):
                st.warning("Botão reservado. Na próxima etapa conectamos o script do HTML colorido da 6ª geração.")
        with colp2:
            st.caption("A base já está preparada para armazenar o HTML colorido por animal e geração.")
        df_pedigree = pd.DataFrame(pedigree)
        if not df_pedigree.empty:
            colunas_visiveis = [c for c in ["bloco", "texto_completo"] if c in df_pedigree.columns]
            df_pedigree = traduzir_colunas_df(df_pedigree[colunas_visiveis], CAMPOS_PEDIGREE_VISIVEIS)
        mostrar_df(df_pedigree, "Nenhum pedigree extraído para este animal.")


    with tab_venda_parceria:
        st.markdown("### Venda do animal")
        st.caption("Ao informar data de entrega, o animal muda para 'Vendido e entregue' e sai das listas operacionais futuras, mantendo histórico para consulta.")
        with st.form("form_venda_animal"):
            cv1, cv2, cv3 = st.columns(3)
            with cv1:
                comprador_nome = st.text_input("Comprador")
                comprador_cpf = st.text_input("CPF/CNPJ")
                valor_venda = st.number_input("Valor da venda", min_value=0.0, step=100.0)
            with cv2:
                comprador_whatsapp = st.text_input("WhatsApp")
                comprador_email = st.text_input("E-mail")
                status_entrega = st.selectbox("Status da entrega", ["", "Aguardando entrega", "Entregue"])
            with cv3:
                data_venda = st.text_input("Data da venda", placeholder="DD/MM/AAAA")
                data_entrega = st.text_input("Data da entrega", placeholder="DD/MM/AAAA")
                condicao_pagamento = st.text_input("Condição de pagamento", placeholder="Ex: 1+49, plano safra, quitado...")
            obs_venda = st.text_area("Observações da venda")
            if st.form_submit_button("Registrar venda"):
                salvar_venda_animal(
                    sbb=sbb, comprador_nome=comprador_nome, comprador_cpf=comprador_cpf,
                    comprador_whatsapp=comprador_whatsapp, comprador_email=comprador_email,
                    data_venda=data_venda, data_entrega=data_entrega, valor_venda=valor_venda,
                    condicao_pagamento=condicao_pagamento, status_entrega=status_entrega, observacoes=obs_venda,
                )
                st.success("Venda registrada.")
                st.rerun()

        vendas = listar_vendas_animal(sbb)
        mostrar_df(pd.DataFrame(vendas), "Nenhuma venda registrada para este animal.")

        st.divider()
        st.markdown("### Parceria")
        with st.form("form_parceria_animal"):
            cp1, cp2, cp3 = st.columns(3)
            with cp1:
                parceiro_nome = st.text_input("Parceiro")
                parceiro_contato = st.text_input("Contato do parceiro")
                modelo_parceria = st.text_input("Modelo de parceria", placeholder="Ex: 50/50, um ano cada, divisão por produto...")
            with cp2:
                percentual_cabanha = st.number_input("% Cabanha", min_value=0.0, max_value=100.0, step=1.0)
                percentual_parceiro = st.number_input("% Parceiro", min_value=0.0, max_value=100.0, step=1.0)
                ativo_parceria = st.checkbox("Parceria ativa", value=True)
            with cp3:
                data_inicio = st.text_input("Data início", placeholder="DD/MM/AAAA")
                data_fim = st.text_input("Data fim", placeholder="DD/MM/AAAA")
            obs_parceria = st.text_area("Observações da parceria")
            if st.form_submit_button("Registrar parceria"):
                salvar_parceria_animal(
                    sbb=sbb, parceiro_nome=parceiro_nome, parceiro_contato=parceiro_contato,
                    percentual_cabanha=percentual_cabanha, percentual_parceiro=percentual_parceiro,
                    modelo_parceria=modelo_parceria, data_inicio=data_inicio, data_fim=data_fim,
                    ativo=ativo_parceria, observacoes=obs_parceria,
                )
                st.success("Parceria registrada.")
                st.rerun()

        parcerias = listar_parcerias_animal(sbb)
        mostrar_df(pd.DataFrame(parcerias), "Nenhuma parceria registrada para este animal.")

    with tab_historico:
        st.markdown("### Histórico de status no ecossistema")
        historico = listar_historico_status(sbb)
        mostrar_df(pd.DataFrame(historico), "Nenhuma alteração de status registrada.")
        st.info("Nesta aba ficará a linha do tempo do animal. Por enquanto começamos pelo histórico de status; depois sanidade, reprodução, morfologia e financeiro também alimentarão esta linha do tempo.")
