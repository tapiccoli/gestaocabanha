"""Componentes de seleção contextual.

Objetivo:
- Padronizar campos do tipo: selecionar cadastro existente + consultar + cadastrar rápido.
- Evitar que o usuário precise sair da tela onde está trabalhando.

Observação técnica:
Em Streamlit, botões comuns não funcionam dentro de `st.form`. Por isso, este
componente deve ser usado fora de formulários ou em telas novas que não dependam
exclusivamente de `st.form`. Para formulários antigos, usamos os cadastros rápidos
em uma área imediatamente acima do formulário até refatorar cada tela.
"""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from repositories.pessoa_repository import PessoaRepository
from repositories.estoque_repository import EstoqueRepository


def entity_selector(
    label: str,
    options: dict[str, Any],
    key: str,
    *,
    help_text: str | None = None,
    view_renderer: Callable[[Any], None] | None = None,
    create_renderer: Callable[[str], Any] | None = None,
    disabled: bool = False,
):
    """Renderiza seleção contextual no padrão [select] [🔍] [➕].

    Retorna: (rotulo_selecionado, valor_selecionado)
    """
    labels = list(options.keys()) if options else [""]
    col_sel, col_view, col_add = st.columns([8, 1, 1])

    with col_sel:
        selected_label = st.selectbox(label, labels, key=f"{key}_select", help=help_text, disabled=disabled)

    selected_value = options.get(selected_label) if options else None

    with col_view:
        st.write("")
        if view_renderer and selected_value:
            with st.popover("🔍", use_container_width=True):
                view_renderer(selected_value)
        else:
            st.button("🔍", key=f"{key}_view_disabled", disabled=True, use_container_width=True)

    with col_add:
        st.write("")
        if create_renderer:
            with st.popover("➕", use_container_width=True):
                novo_id = create_renderer(f"{key}_create")
                if novo_id:
                    st.session_state[f"{key}_ultimo_criado"] = novo_id
                    st.rerun()
        else:
            st.button("➕", key=f"{key}_add_disabled", disabled=True, use_container_width=True)

    return selected_label, selected_value


def cadastro_rapido_pessoa(prefix: str, papel_padrao: str = ""):
    """Cadastro rápido de Pessoa para uso em popover/expander contextual."""
    st.markdown("#### Nova pessoa")
    nome = st.text_input("Nome / Razão social *", key=f"{prefix}_nome")
    c1, c2 = st.columns(2)
    with c1:
        whatsapp = st.text_input("WhatsApp", key=f"{prefix}_whatsapp")
        email = st.text_input("E-mail", key=f"{prefix}_email")
    with c2:
        documento = st.text_input("CPF/CNPJ/Documento", key=f"{prefix}_doc")
        tipo_pessoa = st.selectbox("Tipo", ["", "Pessoa Física", "Pessoa Jurídica"], key=f"{prefix}_tipo")

    papeis_padrao = [papel_padrao] if papel_padrao and papel_padrao in PessoaRepository.PAPEIS else []
    papeis = st.multiselect(
        "Papéis",
        PessoaRepository.PAPEIS,
        default=papeis_padrao,
        key=f"{prefix}_papeis",
    )
    observacoes = st.text_area("Observações", key=f"{prefix}_obs")

    if st.button("Salvar pessoa", key=f"{prefix}_salvar", type="primary", use_container_width=True):
        if not nome.strip():
            st.warning("Informe o nome da pessoa.")
            return None
        pessoa_id = PessoaRepository.salvar({
            "id": None,
            "nome_razao": nome.strip(),
            "nome_fantasia": "",
            "tipo_pessoa": tipo_pessoa,
            "tipo_documento": "CNPJ" if tipo_pessoa == "Pessoa Jurídica" else "CPF",
            "documento": documento,
            "email": email,
            "whatsapp": whatsapp,
            "telefone": "",
            "cidade": "",
            "uf": "",
            "pix": "",
            "banco": "",
            "agencia": "",
            "conta": "",
            "endereco": "",
            "observacoes": observacoes,
            "ativo": 1,
        }, papeis)
        st.success("Pessoa cadastrada com sucesso.")
        return pessoa_id
    return None


def cadastro_rapido_produto(prefix: str, categoria_padrao: str = ""):
    """Cadastro rápido de Produto/Insumo para uso em popover/expander contextual."""
    st.markdown("#### Novo produto / insumo")
    nome = st.text_input("Nome do produto *", key=f"{prefix}_nome")
    c1, c2 = st.columns(2)
    with c1:
        idx_cat = ([""] + EstoqueRepository.CATEGORIAS).index(categoria_padrao) if categoria_padrao in EstoqueRepository.CATEGORIAS else 0
        categoria = st.selectbox("Categoria *", [""] + EstoqueRepository.CATEGORIAS, index=idx_cat, key=f"{prefix}_cat")
        laboratorio = st.text_input("Laboratório/Fabricante", key=f"{prefix}_lab")
    with c2:
        unidade_compra = st.selectbox("Unidade de compra", [""] + EstoqueRepository.UNIDADES, key=f"{prefix}_un_compra")
        unidade_consumo = st.selectbox("Unidade de consumo/controle", [""] + EstoqueRepository.UNIDADES, key=f"{prefix}_un_consumo")

    fator = st.number_input(
        "Qtd. consumo por unidade comprada",
        min_value=0.0,
        step=1.0,
        value=1.0,
        key=f"{prefix}_fator",
        help="Ex.: 1 frasco com 50 mL = 50; 1 saco com 40 kg = 40.",
    )
    estoque_minimo = st.number_input("Estoque mínimo", min_value=0.0, step=1.0, key=f"{prefix}_min")
    observacoes = st.text_area("Observações", key=f"{prefix}_obs")

    if st.button("Salvar produto", key=f"{prefix}_salvar", type="primary", use_container_width=True):
        if not nome.strip():
            st.warning("Informe o nome do produto.")
            return None
        if not categoria:
            st.warning("Selecione a categoria do produto.")
            return None
        produto_id = EstoqueRepository.salvar_produto({
            "id": None,
            "nome": nome.strip(),
            "categoria": categoria,
            "apresentacao": f"{fator:g} {unidade_consumo} por {unidade_compra}" if unidade_compra or unidade_consumo else "",
            "laboratorio_fabricante": laboratorio,
            "unidade": unidade_consumo or unidade_compra,
            "unidade_compra": unidade_compra,
            "unidade_consumo": unidade_consumo or unidade_compra,
            "qtd_consumo_por_unidade_compra": fator or 1,
            "estoque_minimo": estoque_minimo,
            "valor_unitario": 0,
            "data_vencimento": "",
            "observacoes": observacoes,
            "ativo": 1,
        })
        st.success("Produto cadastrado com sucesso.")
        return produto_id
    return None

# ============================================================
# PADRÃO NOVO: CADASTRO CONTEXTUAL COMO 1ª OPÇÃO DO SELECTBOX
# ============================================================
OPCAO_CADASTRAR_NOVO = "➕ Cadastrar novo..."


def selectbox_com_cadastro_rapido(
    label: str,
    options: dict[str, Any],
    key: str,
    *,
    tipo: str,
    papel_padrao: str = "",
    categoria_padrao: str = "",
    help_text: str | None = None,
):
    """Selectbox com a primeira opção '➕ Cadastrar novo...'.

    Este padrão funciona melhor no Streamlit do que botão interno em formulários.
    Uso esperado fora de st.form, para que a tela reaja imediatamente quando o usuário
    escolhe cadastrar um novo registro.

    Retorna o mesmo valor do dicionário `options` para a opção selecionada.
    """
    opcoes_reais = list(options.keys()) if options else [""]
    opcoes = [OPCAO_CADASTRAR_NOVO] + opcoes_reais

    selecionado = st.selectbox(label, opcoes, key=key, help=help_text)

    if selecionado == OPCAO_CADASTRAR_NOVO:
        st.info(f"Cadastre o novo registro abaixo. Depois de salvar, a lista será atualizada automaticamente.")
        if tipo == "pessoa":
            novo_id = cadastro_rapido_pessoa(f"{key}_quick", papel_padrao=papel_padrao)
        elif tipo == "produto":
            novo_id = cadastro_rapido_produto(f"{key}_quick", categoria_padrao=categoria_padrao)
        else:
            st.warning("Tipo de cadastro rápido ainda não suportado.")
            novo_id = None

        if novo_id:
            st.session_state[f"{key}_novo_id"] = novo_id
            st.success("Cadastro rápido realizado. O campo será atualizado.")
            st.rerun()
        return None, selecionado

    return options.get(selecionado), selecionado
