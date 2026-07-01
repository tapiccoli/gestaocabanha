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
from services.nfe_xml_service import ler_xml_nfe
from repositories.pessoa_repository import PessoaRepository
from repositories.financeiro_repository import FinanceiroRepository
from repositories.estoque_repository import EstoqueRepository
from repositories.sanidade_repository import SanidadeRepository
from repositories.reproducao_repository import ReproducaoRepository
from repositories.evento_repository import EventoRepository
from components.entity_selector import cadastro_rapido_pessoa, cadastro_rapido_produto, selectbox_com_cadastro_rapido
from components.event_timeline import render_timeline
from utils.campos_abccc import (
    CAMPOS_TECNICOS_EXCLUIR,
    CAMPOS_PRINCIPAL,
    CAMPOS_MERITOS,
    CAMPOS_HISTORICO,
    CAMPOS_PADREACOES,
    CAMPOS_DESCENDENTES,
    CAMPOS_PEDIGREE_VISIVEIS,
    montar_pedigree_visivel,
    traduzir_colunas_df,
    traduzir_dict_para_linhas,
)

st.set_page_config(page_title="ERP Cabanha", page_icon="🐴", layout="wide")
init_db()
EventoRepository.init()
ReproducaoRepository.init()

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


def limpar_chaves_session(prefixos):
    """Remove valores antigos de widgets do session_state.

    No Streamlit, campos de formulário permanecem em memória mesmo após trocar de aba.
    Esta função força o próximo formulário a abrir limpo.
    """
    prefixos = tuple(prefixos)
    for chave in list(st.session_state.keys()):
        if str(chave).startswith(prefixos):
            del st.session_state[chave]


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


def render_modulo_pessoas():
    st.subheader("Cadastro de Pessoas")
    st.caption("Base única para clientes, fornecedores, veterinários, ferradores, treinadores, funcionários, parceiros, leiloeiras e transportadores.")

    if st.session_state.get("pessoa_salva_msg"):
        st.success(st.session_state.pop("pessoa_salva_msg"))

    if "pessoa_form_version" not in st.session_state:
        st.session_state.pessoa_form_version = 0

    if "pessoa_editando_id" not in st.session_state:
        st.session_state.pessoa_editando_id = None

    col_busca, col_papel, col_inativos = st.columns([2, 1.4, 1])
    with col_busca:
        busca = st.text_input("Buscar pessoa", placeholder="Nome, documento, e-mail ou WhatsApp")
    with col_papel:
        papel_filtro = st.selectbox("Filtrar por papel", [""] + PessoaRepository.PAPEIS)
    with col_inativos:
        incluir_inativos = st.checkbox("Incluir inativos", value=False)

    pessoas = PessoaRepository.listar(incluir_inativos=incluir_inativos, busca=busca, papel=papel_filtro)

    st.markdown("### Lista de pessoas")
    if pessoas:
        for pessoa in pessoas:
            ativo = bool(pessoa.get("ativo"))
            status = "Ativo" if ativo else "Inativo"
            c_nome, c_papeis, c_contato, c_acoes = st.columns([2.3, 2, 2, 1.5])
            with c_nome:
                st.write(f"**{pessoa.get('nome_razao')}**")
                detalhe = pessoa.get("nome_fantasia") or pessoa.get("documento") or ""
                if detalhe:
                    st.caption(detalhe)
            with c_papeis:
                st.write(pessoa.get("papeis") or "-")
                st.caption(status)
            with c_contato:
                st.write(pessoa.get("whatsapp") or pessoa.get("telefone") or "-")
                if pessoa.get("email"):
                    st.caption(pessoa.get("email"))
            with c_acoes:
                if st.button("Editar", key=f"editar_pessoa_{pessoa.get('id')}", use_container_width=True):
                    st.session_state.pessoa_editando_id = pessoa.get("id")
                    st.rerun()
                if ativo:
                    if st.button("Excluir", key=f"excluir_pessoa_{pessoa.get('id')}", use_container_width=True):
                        PessoaRepository.excluir(pessoa.get("id"))
                        st.success("Pessoa desativada. O histórico foi preservado.")
                        st.rerun()
                else:
                    if st.button("Reativar", key=f"reativar_pessoa_{pessoa.get('id')}", use_container_width=True):
                        PessoaRepository.reativar(pessoa.get("id"))
                        st.success("Pessoa reativada.")
                        st.rerun()
            st.divider()
    else:
        st.info("Nenhuma pessoa encontrada.")

    st.markdown("### Cadastrar / Editar pessoa")
    pessoa_atual = None
    if st.session_state.pessoa_editando_id:
        pessoa_atual = PessoaRepository.buscar(st.session_state.pessoa_editando_id)
        if pessoa_atual:
            st.info(f"Editando: {pessoa_atual.get('nome_razao')}")

    def valor_pessoa(campo, padrao=""):
        if not pessoa_atual:
            return padrao
        return pessoa_atual.get(campo) or padrao

    pessoa_form_version = st.session_state.get("pessoa_form_version", 0)
    with st.form(f"form_pessoa_{pessoa_form_version}"):
        c1, c2, c3 = st.columns(3)
        with c1:
            nome_razao = st.text_input("Nome / Razão Social *", value=valor_pessoa("nome_razao"))
            nome_fantasia = st.text_input("Nome Fantasia / Apelido", value=valor_pessoa("nome_fantasia"))
            tipo_pessoa = st.selectbox(
                "Tipo de pessoa",
                ["", "Pessoa Física", "Pessoa Jurídica"],
                index=(["", "Pessoa Física", "Pessoa Jurídica"].index(valor_pessoa("tipo_pessoa")) if valor_pessoa("tipo_pessoa") in ["", "Pessoa Física", "Pessoa Jurídica"] else 0),
            )
        with c2:
            tipo_documento = st.selectbox(
                "Tipo de documento",
                ["", "CPF", "CNPJ", "Outro"],
                index=(["", "CPF", "CNPJ", "Outro"].index(valor_pessoa("tipo_documento")) if valor_pessoa("tipo_documento") in ["", "CPF", "CNPJ", "Outro"] else 0),
            )
            documento = st.text_input("Documento", value=valor_pessoa("documento"))
            email = st.text_input("E-mail", value=valor_pessoa("email"))
        with c3:
            whatsapp = st.text_input("WhatsApp", value=valor_pessoa("whatsapp"))
            telefone = st.text_input("Telefone", value=valor_pessoa("telefone"))
            ativo = st.checkbox("Ativo", value=bool(valor_pessoa("ativo", 1)))

        st.markdown("#### Papéis no sistema")
        papeis_atuais = pessoa_atual.get("papeis_lista", []) if pessoa_atual else []
        papeis = st.multiselect(
            "Esta pessoa pode ser usada como",
            PessoaRepository.PAPEIS,
            default=[p for p in papeis_atuais if p in PessoaRepository.PAPEIS],
        )

        c4, c5, c6 = st.columns(3)
        with c4:
            cidade = st.text_input("Cidade", value=valor_pessoa("cidade"))
            uf = st.text_input("UF", value=valor_pessoa("uf"), max_chars=2)
        with c5:
            pix = st.text_input("Chave Pix", value=valor_pessoa("pix"))
            banco = st.text_input("Banco", value=valor_pessoa("banco"))
        with c6:
            agencia = st.text_input("Agência", value=valor_pessoa("agencia"))
            conta = st.text_input("Conta", value=valor_pessoa("conta"))

        endereco = st.text_area("Endereço", value=valor_pessoa("endereco"))
        observacoes = st.text_area("Observações", value=valor_pessoa("observacoes"))

        c_salvar, c_novo = st.columns([1, 1])
        with c_salvar:
            salvar = st.form_submit_button("Salvar pessoa", type="primary", use_container_width=True)
        with c_novo:
            novo = st.form_submit_button("Limpar / Novo cadastro", use_container_width=True)

        if salvar:
            if not nome_razao.strip():
                st.warning("Informe o Nome / Razão Social.")
            else:
                dados = {
                    "id": st.session_state.pessoa_editando_id,
                    "nome_razao": nome_razao.strip(),
                    "nome_fantasia": nome_fantasia.strip(),
                    "tipo_pessoa": tipo_pessoa,
                    "tipo_documento": tipo_documento,
                    "documento": documento.strip(),
                    "email": email.strip(),
                    "whatsapp": whatsapp.strip(),
                    "telefone": telefone.strip(),
                    "cidade": cidade.strip(),
                    "uf": uf.strip().upper(),
                    "endereco": endereco.strip(),
                    "pix": pix.strip(),
                    "banco": banco.strip(),
                    "agencia": agencia.strip(),
                    "conta": conta.strip(),
                    "observacoes": observacoes.strip(),
                    "ativo": ativo,
                }
                pessoa_id = PessoaRepository.salvar(dados, papeis)
                st.session_state.pessoa_editando_id = None
                st.session_state.pessoa_form_version = st.session_state.get("pessoa_form_version", 0) + 1
                st.session_state.pessoa_salva_msg = f"✅ Pessoa cadastrada/atualizada com sucesso."
                st.rerun()

        if novo:
            st.session_state.pessoa_editando_id = None
            st.session_state.pessoa_form_version = st.session_state.get("pessoa_form_version", 0) + 1
            st.session_state.pessoa_salva_msg = "Formulário limpo para novo cadastro."
            st.rerun()


st.title("ERP Cabanha")
st.caption("Cadastro inicial de animais com extração automática da ABCCC, banco interno e visualização completa por abas.")



def formatar_moeda(valor):
    try:
        return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _somar_meses_data_br(data_br, meses):
    """Soma meses a uma data DD/MM/AAAA sem depender de bibliotecas externas."""
    from datetime import datetime
    if not data_br:
        return ""
    try:
        dt = datetime.strptime(data_br, "%d/%m/%Y")
    except ValueError:
        return data_br
    mes = dt.month - 1 + meses
    ano = dt.year + mes // 12
    mes = mes % 12 + 1
    # limita dia ao fim do mês
    import calendar
    dia = min(dt.day, calendar.monthrange(ano, mes)[1])
    return f"{dia:02d}/{mes:02d}/{ano:04d}"


def _opcoes_pessoas_financeiro():
    pessoas = PessoaRepository.listar(incluir_inativos=False)
    opcoes = {"": (None, "")}
    for p in pessoas:
        rotulo = f"{p.get('nome_razao')} | {p.get('papeis') or 'Sem papel'}"
        opcoes[rotulo] = (p.get("id"), p.get("nome_razao"))
    return opcoes


def _opcoes_animais_financeiro():
    animais = listar_animais(incluir_inativos=False)
    opcoes = {"": ""}
    for a in animais:
        rotulo = f"{a.get('nome') or 'Sem nome'} | SBB {a.get('sbb')} | {a.get('categoria_idade') or ''} | {a.get('manejo') or ''}"
        opcoes[rotulo] = a.get("sbb")
    return opcoes


def render_modulo_financeiro():
    st.subheader("Financeiro Base")
    st.caption("Lançamentos, parcelas, rateios e relatórios filtráveis. Este é o motor financeiro que será reaproveitado pelos módulos de reprodução, sanidade, estoque e leilões.")

    tab_lancar, tab_relatorios, tab_parcelas = st.tabs(["Novo lançamento", "Relatórios", "Parcelas / Baixa"])

    with tab_lancar:
        st.markdown("### Novo lançamento financeiro")

        if st.session_state.get("fin_lancamento_salvo_msg"):
            st.success(st.session_state.pop("fin_lancamento_salvo_msg"))

        pessoas_op = _opcoes_pessoas_financeiro()
        animais_op = _opcoes_animais_financeiro()

        # Usamos uma chave variável para o formulário.
        # Quando um lançamento é salvo, incrementamos essa versão e damos st.rerun().
        # Assim o Streamlit recria o formulário limpo, evitando lançamentos duplicados por dúvida do usuário.
        fin_form_version = st.session_state.get("fin_form_version", 0)

        criterio_rateio_pre = st.selectbox(
            "Aplicar custo/receita para",
            ["Todos os Animais", "Animal específico", "Vários animais", "Categoria", "Manejo"],
            key=f"fin_criterio_rateio_{fin_form_version}",
        )

        with st.form(f"form_financeiro_lancamento_{fin_form_version}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
                descricao = st.text_input("Descrição / Motivo *", placeholder="Ex: Compra de alfafa, sêmen, vacina, venda de animal...")
                valor_total = st.number_input("Valor total", min_value=0.0, step=100.0)
            with c2:
                data_evento = st.text_input("Data do Evento", placeholder="DD/MM/AAAA")
                data_competencia = data_evento
                data_emissao = data_evento
                forma_pagamento = st.selectbox("Forma de pagamento", FinanceiroRepository.FORMAS_PAGAMENTO)
            with c3:
                pessoa_rotulo = st.selectbox("Pessoa relacionada", list(pessoas_op.keys()))
                pessoa_id, pessoa_nome = pessoas_op[pessoa_rotulo]
                centro_custo = st.selectbox("Centro de custo", [""] + FinanceiroRepository.CENTROS_CUSTO)
                atividade = st.selectbox("Atividade", [""] + FinanceiroRepository.ATIVIDADES)

            observacoes = st.text_area("Observações")

            st.markdown("#### Parcelamento")
            cp1, cp2, cp3 = st.columns(3)
            with cp1:
                num_parcelas = st.number_input("Número de parcelas", min_value=1, max_value=120, value=1, step=1)
            with cp2:
                primeiro_vencimento = st.text_input("Primeiro vencimento", placeholder="DD/MM/AAAA")
            with cp3:
                intervalo_meses = st.number_input("Intervalo em meses", min_value=1, max_value=12, value=1, step=1)

            st.markdown("#### Aplicar custo/receita para")
            st.caption("Escolha o destino do lançamento. A tela mostra somente os campos necessários para o tipo selecionado.")
            criterio_rateio = criterio_rateio_pre
            st.write(f"**Destino escolhido:** {criterio_rateio}")

            rateios = []
            erro_rateio = ""
            qtd_destinos = 0

            if criterio_rateio == "Animal específico":
                animal_rotulo = st.selectbox("Selecionar animal", list(animais_op.keys()))
                animal_sbb = animais_op.get(animal_rotulo, "")
                if animal_sbb:
                    qtd_destinos = 1
                    rateios = [{"criterio_rateio": criterio_rateio, "animal_sbb": animal_sbb, "percentual": 100, "valor_rateado": valor_total}]
                else:
                    erro_rateio = "Selecione um animal para o rateio."

            elif criterio_rateio == "Vários animais":
                opcoes_animais_validas = [k for k in animais_op.keys() if k]
                animais_selecionados = st.multiselect("Selecionar animais que participam do rateio", opcoes_animais_validas)
                qtd = len(animais_selecionados)
                qtd_destinos = qtd
                if qtd:
                    for rotulo in animais_selecionados:
                        rateios.append({
                            "criterio_rateio": criterio_rateio,
                            "animal_sbb": animais_op[rotulo],
                            "percentual": 100 / qtd,
                            "valor_rateado": valor_total / qtd if qtd else 0,
                        })
                else:
                    erro_rateio = "Selecione pelo menos um animal para o rateio."

            elif criterio_rateio == "Categoria":
                categoria_animal = st.selectbox("Categoria animal", _opcoes_categorias_animais())
                qtd_destinos = 1
                rateios = [{"criterio_rateio": criterio_rateio, "categoria_animal": categoria_animal, "percentual": 100, "valor_rateado": valor_total}]
                if not categoria_animal:
                    erro_rateio = "Selecione a categoria do rateio."

            elif criterio_rateio == "Manejo":
                manejo = st.selectbox("Manejo", _opcoes_manejos_animais())
                qtd_destinos = 1
                rateios = [{"criterio_rateio": criterio_rateio, "manejo": manejo, "percentual": 100, "valor_rateado": valor_total}]
                if not manejo:
                    erro_rateio = "Selecione o manejo do rateio."

            else:
                qtd_destinos = len([v for v in animais_op.values() if v])
                rateios = [{"criterio_rateio": "Todos os Animais", "percentual": 100, "valor_rateado": valor_total}]

            if qtd_destinos:
                st.info(f"Destino selecionado: {criterio_rateio}. Quantidade de destino(s): {qtd_destinos}.")

            salvar = st.form_submit_button("Salvar lançamento", type="primary", use_container_width=True)
            if salvar:
                if not descricao.strip() or valor_total <= 0:
                    st.warning("Informe descrição e valor total maior que zero.")
                elif erro_rateio:
                    st.warning(erro_rateio)
                else:
                    valor_parcela = valor_total / int(num_parcelas)
                    parcelas = []
                    base_venc = primeiro_vencimento or data_evento
                    for i in range(int(num_parcelas)):
                        parcelas.append({
                            "numero_parcela": i + 1,
                            "data_vencimento": _somar_meses_data_br(base_venc, i * int(intervalo_meses)),
                            "valor_previsto": valor_parcela,
                            "status": "Aberta",
                        })
                    dados = {
                        "tipo": tipo,
                        "descricao": descricao.strip(),
                        "data_competencia": data_evento.strip(),
                        "data_emissao": data_evento.strip(),
                        "valor_total": valor_total,
                        "pessoa_id": pessoa_id,
                        "pessoa_nome": pessoa_nome,
                        "centro_custo": centro_custo,
                        "atividade": atividade,
                        "origem_modulo": "Manual",
                        "forma_pagamento": forma_pagamento,
                        "observacoes": observacoes.strip(),
                    }
                    lancamento_id = FinanceiroRepository.salvar_lancamento(dados, parcelas, rateios)
                    st.session_state["fin_lancamento_salvo_msg"] = (
                        f"✅ Lançamento financeiro #{lancamento_id} cadastrado com sucesso. "
                        f"Foram geradas {len(parcelas)} parcela(s) e {len(rateios)} rateio(s). "
                        "O formulário foi limpo para um novo cadastro."
                    )
                    st.session_state["fin_form_version"] = st.session_state.get("fin_form_version", 0) + 1
                    st.rerun()

    with tab_relatorios:
        st.markdown("### Relatórios financeiros")
        st.caption("Nesta primeira versão já filtramos por variáveis principais. Nas próximas versões vamos acrescentar relatórios por animal, categoria, manejo, produto, safra/ciclo e DRE.")

        cf1, cf2, cf3, cf4 = st.columns(4)
        with cf1:
            f_tipo = st.selectbox("Tipo", [""] + ["Entrada", "Saída"], key="fin_f_tipo")
            f_data_inicio = st.text_input("Data inicial", placeholder="DD/MM/AAAA", key="fin_f_ini")
        with cf2:
            f_centro = st.selectbox("Centro de custo", [""] + FinanceiroRepository.CENTROS_CUSTO, key="fin_f_centro")
            f_data_fim = st.text_input("Data final", placeholder="DD/MM/AAAA", key="fin_f_fim")
        with cf3:
            f_atividade = st.selectbox("Atividade", [""] + FinanceiroRepository.ATIVIDADES, key="fin_f_atividade")
            f_status_parcela = st.selectbox("Status parcela", [""] + FinanceiroRepository.STATUS_PARCELA, key="fin_f_status")
        with cf4:
            f_busca = st.text_input("Buscar", placeholder="Descrição, pessoa ou observação", key="fin_f_busca")

        filtros = {
            "tipo": f_tipo,
            "centro_custo": f_centro,
            "atividade": f_atividade,
            "status_parcela": f_status_parcela,
            "data_inicio": f_data_inicio.strip(),
            "data_fim": f_data_fim.strip(),
            "busca": f_busca.strip(),
        }
        filtros = {k: v for k, v in filtros.items() if v}

        ind = FinanceiroRepository.indicadores(filtros)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Entradas previstas", formatar_moeda(ind["entradas_previstas"]))
        m2.metric("Saídas previstas", formatar_moeda(ind["saidas_previstas"]))
        m3.metric("Saldo previsto", formatar_moeda(ind["saldo_previsto"]))
        m4.metric("Saldo realizado", formatar_moeda(ind["saldo_realizado"]))
        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Recebido", formatar_moeda(ind["recebido"]))
        m6.metric("Pago", formatar_moeda(ind["pago"]))
        m7.metric("A receber", formatar_moeda(ind["aberto_receber"]))
        m8.metric("A pagar", formatar_moeda(ind["aberto_pagar"]))

        st.markdown("#### Lançamentos")
        lancamentos = FinanceiroRepository.listar_lancamentos(filtros)
        mostrar_df(pd.DataFrame(lancamentos), "Nenhum lançamento encontrado.")

        st.markdown("#### Parcelas")
        parcelas = FinanceiroRepository.listar_parcelas(filtros=filtros)
        mostrar_df(pd.DataFrame(parcelas), "Nenhuma parcela encontrada.")

        if lancamentos:
            ids = [str(l["id"]) for l in lancamentos]
            id_sel = st.selectbox("Ver rateios do lançamento", [""] + ids)
            if id_sel:
                lancamento_id_sel = int(id_sel)
                rateios = FinanceiroRepository.listar_rateios(lancamento_id_sel)
                mostrar_df(pd.DataFrame(rateios), "Sem rateios.")

                lanc_atual = FinanceiroRepository.buscar_lancamento(lancamento_id_sel)
                parcelas_atual = FinanceiroRepository.listar_parcelas(lancamento_id=lancamento_id_sel)

                with st.expander("Editar lançamento selecionado", expanded=False):
                    st.warning("Use a edição apenas para corrigir erro de digitação, valor, parcelamento ou rateio. Se o lançamento já teve baixa real, confira antes de alterar.")
                    pessoas_op_edit = _opcoes_pessoas_financeiro()
                    animais_op_edit = _opcoes_animais_financeiro()
                    labels_pessoas = list(pessoas_op_edit.keys())
                    pessoa_index = 0
                    for idx, label in enumerate(labels_pessoas):
                        pid, _pnome = pessoas_op_edit[label]
                        if lanc_atual and pid == lanc_atual.get("pessoa_id"):
                            pessoa_index = idx
                            break

                    criterio_atual_pre = rateios[0].get("Critério") if rateios else "Todos os Animais"
                    if criterio_atual_pre == "Global":
                        criterio_atual_pre = "Todos os Animais"
                    criterios_pre = ["Todos os Animais", "Animal específico", "Vários animais", "Categoria", "Manejo"]
                    e_criterio_rateio_pre = st.selectbox(
                        "Aplicar custo/receita para",
                        criterios_pre,
                        index=criterios_pre.index(criterio_atual_pre) if criterio_atual_pre in criterios_pre else 0,
                        key=f"e_crit_pre_{lancamento_id_sel}",
                    )

                    with st.form(f"form_editar_lancamento_{lancamento_id_sel}"):
                        ec1, ec2, ec3 = st.columns(3)
                        with ec1:
                            e_tipo = st.selectbox("Tipo", ["Saída", "Entrada"], index=0 if (lanc_atual or {}).get("tipo") != "Entrada" else 1, key=f"e_tipo_{lancamento_id_sel}")
                            e_descricao = st.text_input("Descrição / Motivo *", value=(lanc_atual or {}).get("descricao") or "", key=f"e_desc_{lancamento_id_sel}")
                            e_valor_total = st.number_input("Valor total", min_value=0.0, step=100.0, value=float((lanc_atual or {}).get("valor_total") or 0), key=f"e_valor_{lancamento_id_sel}")
                        with ec2:
                            data_evento_atual = (lanc_atual or {}).get("data_competencia") or (lanc_atual or {}).get("data_emissao") or ""
                            e_data_evento = st.text_input("Data do Evento", value=data_evento_atual, placeholder="DD/MM/AAAA", key=f"e_evento_{lancamento_id_sel}")
                            e_data_competencia = e_data_evento
                            e_data_emissao = e_data_evento
                            forma_atual = (lanc_atual or {}).get("forma_pagamento") or ""
                            formas = FinanceiroRepository.FORMAS_PAGAMENTO
                            e_forma_pagamento = st.selectbox("Forma de pagamento", formas, index=formas.index(forma_atual) if forma_atual in formas else 0, key=f"e_forma_{lancamento_id_sel}")
                        with ec3:
                            e_pessoa_rotulo = st.selectbox("Pessoa relacionada", labels_pessoas, index=pessoa_index, key=f"e_pessoa_{lancamento_id_sel}")
                            e_pessoa_id, e_pessoa_nome = pessoas_op_edit[e_pessoa_rotulo]
                            centro_atual = (lanc_atual or {}).get("centro_custo") or ""
                            centros = [""] + FinanceiroRepository.CENTROS_CUSTO
                            e_centro_custo = st.selectbox("Centro de custo", centros, index=centros.index(centro_atual) if centro_atual in centros else 0, key=f"e_centro_{lancamento_id_sel}")
                            atividade_atual = (lanc_atual or {}).get("atividade") or ""
                            atividades = [""] + FinanceiroRepository.ATIVIDADES
                            e_atividade = st.selectbox("Atividade", atividades, index=atividades.index(atividade_atual) if atividade_atual in atividades else 0, key=f"e_ativ_{lancamento_id_sel}")

                        e_observacoes = st.text_area("Observações", value=(lanc_atual or {}).get("observacoes") or "", key=f"e_obs_{lancamento_id_sel}")

                        st.markdown("#### Parcelamento corrigido")
                        ep1, ep2, ep3 = st.columns(3)
                        with ep1:
                            e_num_parcelas = st.number_input("Número de parcelas", min_value=1, max_value=120, value=max(1, len(parcelas_atual) or 1), step=1, key=f"e_nparc_{lancamento_id_sel}")
                        with ep2:
                            venc_padrao = parcelas_atual[0].get("Vencimento") if parcelas_atual else ((lanc_atual or {}).get("data_competencia") or "")
                            e_primeiro_vencimento = st.text_input("Primeiro vencimento", value=venc_padrao or "", placeholder="DD/MM/AAAA", key=f"e_venc_{lancamento_id_sel}")
                        with ep3:
                            e_intervalo_meses = st.number_input("Intervalo em meses", min_value=1, max_value=12, value=1, step=1, key=f"e_intervalo_{lancamento_id_sel}")

                        st.markdown("#### Rateio corrigido")
                        e_criterio_rateio = e_criterio_rateio_pre
                        st.write(f"**Destino escolhido:** {e_criterio_rateio}")
                        e_rateios = []
                        if e_criterio_rateio == "Animal específico":
                            animal_atual = rateios[0].get("Animal") if rateios else ""
                            labels_animais = list(animais_op_edit.keys())
                            animal_index = 0
                            for idx, label in enumerate(labels_animais):
                                if animais_op_edit[label] == animal_atual:
                                    animal_index = idx
                                    break
                            e_animal_rotulo = st.selectbox("Animal", labels_animais, index=animal_index, key=f"e_animal_{lancamento_id_sel}")
                            e_rateios = [{"criterio_rateio": e_criterio_rateio, "animal_sbb": animais_op_edit[e_animal_rotulo], "percentual": 100, "valor_rateado": e_valor_total}]
                        elif e_criterio_rateio == "Vários animais":
                            animais_atuais = [r.get("Animal") for r in rateios if r.get("Animal")]
                            opcoes_animais_validas = [k for k in animais_op_edit.keys() if k]
                            default_multi = [k for k in opcoes_animais_validas if animais_op_edit[k] in animais_atuais]
                            e_animais_selecionados = st.multiselect("Animais que participam do rateio", opcoes_animais_validas, default=default_multi, key=f"e_multi_{lancamento_id_sel}")
                            qtd = len(e_animais_selecionados)
                            if qtd:
                                for rotulo in e_animais_selecionados:
                                    e_rateios.append({"criterio_rateio": e_criterio_rateio, "animal_sbb": animais_op_edit[rotulo], "percentual": 100 / qtd, "valor_rateado": e_valor_total / qtd})
                        elif e_criterio_rateio == "Categoria":
                            categoria_atual = rateios[0].get("Categoria") if rateios else ""
                            categorias = _opcoes_categorias_animais()
                            e_categoria_animal = st.selectbox("Categoria animal", categorias, index=categorias.index(categoria_atual) if categoria_atual in categorias else 0, key=f"e_categoria_{lancamento_id_sel}")
                            e_rateios = [{"criterio_rateio": e_criterio_rateio, "categoria_animal": e_categoria_animal, "percentual": 100, "valor_rateado": e_valor_total}]
                        elif e_criterio_rateio == "Manejo":
                            manejo_atual = rateios[0].get("Manejo") if rateios else ""
                            manejos = _opcoes_manejos_animais()
                            e_manejo = st.selectbox("Manejo", manejos, index=manejos.index(manejo_atual) if manejo_atual in manejos else 0, key=f"e_manejo_{lancamento_id_sel}")
                            e_rateios = [{"criterio_rateio": e_criterio_rateio, "manejo": e_manejo, "percentual": 100, "valor_rateado": e_valor_total}]
                        else:
                            e_rateios = [{"criterio_rateio": "Todos os Animais", "percentual": 100, "valor_rateado": e_valor_total}]

                        col_salvar, col_cancelar = st.columns(2)
                        with col_salvar:
                            editar = st.form_submit_button("Salvar alterações", type="primary", use_container_width=True)
                        with col_cancelar:
                            st.form_submit_button("Cancelar", use_container_width=True)

                        if editar:
                            if not e_descricao.strip() or e_valor_total <= 0:
                                st.warning("Informe descrição e valor total maior que zero.")
                            else:
                                valor_parcela = e_valor_total / int(e_num_parcelas)
                                e_parcelas = []
                                base_venc = e_primeiro_vencimento or e_data_evento
                                for i in range(int(e_num_parcelas)):
                                    e_parcelas.append({
                                        "numero_parcela": i + 1,
                                        "data_vencimento": _somar_meses_data_br(base_venc, i * int(e_intervalo_meses)),
                                        "valor_previsto": valor_parcela,
                                        "status": "Aberta",
                                    })
                                e_dados = {
                                    "tipo": e_tipo,
                                    "descricao": e_descricao.strip(),
                                    "data_competencia": e_data_evento.strip(),
                                    "data_emissao": e_data_evento.strip(),
                                    "valor_total": e_valor_total,
                                    "pessoa_id": e_pessoa_id,
                                    "pessoa_nome": e_pessoa_nome,
                                    "centro_custo": e_centro_custo,
                                    "atividade": e_atividade,
                                    "origem_modulo": (lanc_atual or {}).get("origem_modulo") or "Manual",
                                    "forma_pagamento": e_forma_pagamento,
                                    "observacoes": e_observacoes.strip(),
                                }
                                FinanceiroRepository.atualizar_lancamento(lancamento_id_sel, e_dados, e_parcelas, e_rateios)
                                st.success(f"Lançamento #{lancamento_id_sel} atualizado com sucesso.")
                                st.rerun()

                st.divider()
                st.markdown("#### Excluir duplicidade ou lançamento errado")
                st.caption("A exclusão é lógica: o lançamento sai dos relatórios operacionais, mas o registro fica preservado no banco para rastreabilidade.")
                confirmar_exclusao = st.checkbox(f"Confirmo que desejo excluir o lançamento #{lancamento_id_sel}", key=f"conf_excluir_lanc_{lancamento_id_sel}")
                if st.button("Excluir lançamento selecionado", type="secondary", disabled=not confirmar_exclusao):
                    FinanceiroRepository.excluir_lancamento(lancamento_id_sel)
                    st.success("Lançamento excluído logicamente. Ele não aparecerá mais nos relatórios operacionais.")
                    st.rerun()

    with tab_parcelas:
        st.markdown("### Parcelas em aberto / baixa")
        parcelas = FinanceiroRepository.listar_parcelas(filtros={"status_parcela": "Aberta"})
        if not parcelas:
            st.info("Nenhuma parcela em aberto.")
        else:
            for p in parcelas:
                c1, c2, c3, c4, c5 = st.columns([1.1, 2.8, 1.2, 1.2, 1.2])
                with c1:
                    st.write(f"#{p.get('id')}")
                    st.caption(f"Lanç. {p.get('Lançamento')}")
                with c2:
                    st.write(f"**{p.get('Descrição')}**")
                    st.caption(f"{p.get('Pessoa') or '-'} | {p.get('Centro de Custo') or '-'} | {p.get('Atividade') or '-'}")
                with c3:
                    st.write(p.get("Vencimento") or "-")
                    st.caption(p.get("Tipo") or "")
                with c4:
                    st.write(formatar_moeda(p.get("Valor Previsto")))
                with c5:
                    data_pgto = st.text_input("Data baixa", value="", placeholder="DD/MM/AAAA", key=f"data_pgto_{p.get('id')}")
                    if st.button("Baixar", key=f"baixar_parcela_{p.get('id')}", use_container_width=True):
                        FinanceiroRepository.pagar_parcela(p.get("id"), data_pgto or p.get("Vencimento"), p.get("Valor Previsto"))
                        st.success("Parcela baixada.")
                        st.rerun()
                st.divider()





def _opcoes_produtos_estoque():
    produtos = EstoqueRepository.listar_produtos(incluir_inativos=False)
    opcoes = {"": None}
    for p in produtos:
        rotulo = f"{p.get('Produto')} | {p.get('Categoria') or ''} | {p.get('Unidade') or ''}"
        opcoes[rotulo] = p.get("id")
    return opcoes


def _opcoes_categorias_animais():
    return [
        "",
        "Potro ao pé",
        "Potra ao pé",
        "Potro Desmamado",
        "Potra Desmamada",
        "Potro Sobreano",
        "Potra Sobreano",
        "Potranco",
        "Potranca",
        "Macho Adulto Inteiro",
        "Macho Adulto Castrado",
        "Égua Adulta",
        "Égua Idosa",
    ]


def _opcoes_manejos_animais():
    return [
        "",
        "A campo",
        "Pastagem",
        "Campo com suplementação",
        "Cabanha",
        "Doma",
        "Treinamento",
        "Central reprodutiva",
    ]


def _formatar_moeda(valor):
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _calcular_estoque_fracionado(qtd_compra, valor_total, fator_conversao):
    """Converte unidade de compra da nota para unidade real de consumo/controle.

    Exemplo: NF veio 1 frasco de R$ 100. Produto controla 50 mL por frasco.
    Resultado: entra 50 mL no estoque, custo unitário R$ 2,00/mL.
    """
    qtd_compra = float(qtd_compra or 0)
    valor_total = float(valor_total or 0)
    fator = float(fator_conversao or 1)
    if fator <= 0:
        fator = 1
    qtd_consumo = qtd_compra * fator
    valor_unitario_consumo = valor_total / qtd_consumo if qtd_consumo else 0
    return qtd_consumo, valor_unitario_consumo


def _render_destino_estoque(prefixo, destino_tipo, animais_op):
    """Renderiza destino da movimentação sem campos livres para categoria/manejo."""
    animal_sbb = categoria_animal = manejo = ""
    if destino_tipo == "Animal específico":
        animal_rotulo = st.selectbox("Animal", list(animais_op.keys()), key=f"{prefixo}_animal")
        animal_sbb = animais_op.get(animal_rotulo, "")
    elif destino_tipo == "Categoria":
        categoria_animal = st.selectbox("Categoria animal", _opcoes_categorias_animais(), key=f"{prefixo}_categoria")
    elif destino_tipo == "Manejo":
        manejo = st.selectbox("Manejo", _opcoes_manejos_animais(), key=f"{prefixo}_manejo")
    return animal_sbb, categoria_animal, manejo


def _validar_destino_estoque(destino_tipo, animal_sbb, categoria_animal, manejo):
    if destino_tipo == "Animal específico" and not animal_sbb:
        return "Selecione o animal do destino."
    if destino_tipo == "Categoria" and not categoria_animal:
        return "Selecione a categoria animal."
    if destino_tipo == "Manejo" and not manejo:
        return "Selecione o manejo."
    return ""


def render_modulo_estoque():
    st.subheader("Estoque")
    st.caption("Cadastro de insumos, medicamentos, rações, suplementos, sêmen/palhetas e controle de entradas/consumos. Esta base será reaproveitada por sanidade, reprodução, leilões e manejo.")

    tab_produtos, tab_mov, tab_saldos = st.tabs(["Insumos e Cadastros", "Movimentações sem nota", "Saldos e alertas"])

    produtos_op = _opcoes_produtos_estoque()
    pessoas_op = _opcoes_pessoas_financeiro()
    animais_op = _opcoes_animais_financeiro()

    with tab_produtos:
        st.markdown("### Cadastro de produto/insumo")
        if st.session_state.get("estoque_produto_msg"):
            st.success(st.session_state.pop("estoque_produto_msg"))

        versao = st.session_state.get("estoque_produto_form_version", 0)
        produtos_lista = EstoqueRepository.listar_produtos(incluir_inativos=True)
        ids = [""] + [str(p.get("id")) for p in produtos_lista]
        id_editar = st.selectbox("Editar produto existente", ids, key=f"estoque_produto_editar_{versao}")
        atual = EstoqueRepository.buscar_produto(int(id_editar)) if id_editar else {}

        with st.form(f"form_estoque_produto_{versao}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                nome = st.text_input("Nome do produto *", value=atual.get("nome", ""), placeholder="Ex: Ração Potros, Ivomec, Vacina Raiva")
                categoria = st.selectbox(
                    "Categoria",
                    [""] + EstoqueRepository.CATEGORIAS,
                    index=([""] + EstoqueRepository.CATEGORIAS).index(atual.get("categoria", "")) if atual.get("categoria", "") in ([""] + EstoqueRepository.CATEGORIAS) else 0,
                )
                unidade_compra_atual = atual.get("unidade_compra") or ""
                unidade_consumo_atual = atual.get("unidade_consumo") or atual.get("unidade") or ""
                unidade_compra = st.selectbox(
                    "Unidade de compra",
                    [""] + EstoqueRepository.UNIDADES,
                    index=([""] + EstoqueRepository.UNIDADES).index(unidade_compra_atual) if unidade_compra_atual in ([""] + EstoqueRepository.UNIDADES) else 0,
                    help="Como o produto normalmente vem na nota. Ex: frasco, saco, fardo, un."
                )
                unidade_consumo = st.selectbox(
                    "Unidade de controle/consumo",
                    [""] + EstoqueRepository.UNIDADES,
                    index=([""] + EstoqueRepository.UNIDADES).index(unidade_consumo_atual) if unidade_consumo_atual in ([""] + EstoqueRepository.UNIDADES) else 0,
                    help="Como será baixado no uso. Ex: mL, g, kg, dose."
                )
            with c2:
                apresentacao = st.text_input("Apresentação", value=atual.get("apresentacao", ""), placeholder="Ex: Saco 40kg, frasco 50mL")
                laboratorio = st.text_input("Laboratório/Fabricante", value=atual.get("laboratorio_fabricante", ""))
                vencimento = st.text_input("Data de vencimento", value=atual.get("data_vencimento", ""), placeholder="DD/MM/AAAA")
            with c3:
                qtd_consumo_por_unidade_compra = st.number_input(
                    "Qtd. de consumo por unidade de compra",
                    min_value=0.0,
                    step=1.0,
                    value=float(atual.get("qtd_consumo_por_unidade_compra") or 1),
                    help="Ex: 1 frasco com 50 mL = informe 50. 1 saco com 40 kg = informe 40."
                )
                estoque_minimo = st.number_input("Estoque mínimo", min_value=0.0, step=1.0, value=float(atual.get("estoque_minimo") or 0))
                valor_unitario = st.number_input("Valor unitário padrão da unidade de consumo", min_value=0.0, step=1.0, value=float(atual.get("valor_unitario") or 0))
                ativo = st.checkbox("Ativo", value=bool(atual.get("ativo", 1)))

            observacoes = st.text_area("Observações", value=atual.get("observacoes", ""))
            col_a, col_b = st.columns(2)
            salvar = col_a.form_submit_button("Salvar produto", type="primary", use_container_width=True)
            limpar = col_b.form_submit_button("Limpar / Novo produto", use_container_width=True)

            if salvar:
                if not nome.strip():
                    st.warning("Informe o nome do produto.")
                else:
                    produto_id = EstoqueRepository.salvar_produto({
                        "id": int(id_editar) if id_editar else None,
                        "nome": nome,
                        "categoria": categoria,
                        "apresentacao": apresentacao,
                        "laboratorio_fabricante": laboratorio,
                        "unidade": unidade_consumo,
                        "unidade_compra": unidade_compra,
                        "unidade_consumo": unidade_consumo,
                        "qtd_consumo_por_unidade_compra": qtd_consumo_por_unidade_compra,
                        "estoque_minimo": estoque_minimo,
                        "valor_unitario": valor_unitario,
                        "data_vencimento": vencimento,
                        "observacoes": observacoes,
                        "ativo": 1 if ativo else 0,
                    })
                    st.session_state["estoque_produto_msg"] = f"✅ Produto #{produto_id} salvo com sucesso. O formulário foi limpo."
                    st.session_state["estoque_produto_form_version"] = versao + 1
                    st.rerun()
            if limpar:
                st.session_state["estoque_produto_form_version"] = versao + 1
                st.session_state["estoque_produto_msg"] = "Formulário limpo para novo produto."
                st.rerun()

        st.markdown("### Importar NF-e XML")
        st.caption("Use esta opção quando a entrada de estoque tiver nota fiscal. O sistema lê os itens, permite revisar a NF, vincular produtos existentes ou cadastrar produtos novos.")
        if st.session_state.get("estoque_mov_msg"):
            st.success(st.session_state.pop("estoque_mov_msg"))

        versao_xml = st.session_state.get("estoque_xml_form_version", 0)
        xml = st.file_uploader("Importar XML da NF-e", type=["xml"], key=f"xml_nfe_estoque_{versao_xml}")
        if xml is not None:
            try:
                st.session_state["estoque_xml_dados"] = ler_xml_nfe(xml.read())
            except Exception as e:
                st.error(f"Não consegui ler o XML: {e}")

        dados_nfe = st.session_state.get("estoque_xml_dados")
        if dados_nfe:
            st.markdown("#### Conferência e edição dos dados da nota")
            n1, n2, n3, n4 = st.columns(4)
            nf_numero = n1.text_input("Número da NF", value=dados_nfe.get("numero", ""), key=f"xml_numero_{versao_xml}")
            nf_serie = n2.text_input("Série", value=dados_nfe.get("serie", ""), key=f"xml_serie_{versao_xml}")
            nf_emissao = n3.text_input("Data de emissão", value=dados_nfe.get("data_emissao", ""), placeholder="DD/MM/AAAA", key=f"xml_emissao_{versao_xml}")
            nf_valor = n4.number_input("Valor total da NF", min_value=0.0, step=1.0, value=float(dados_nfe.get("valor_total") or 0), key=f"xml_valor_{versao_xml}")

            f1, f2 = st.columns(2)
            fornecedor_nome_xml = f1.text_input("Fornecedor da NF", value=dados_nfe.get("fornecedor_nome", ""), key=f"xml_forn_nome_{versao_xml}")
            fornecedor_cnpj_xml = f2.text_input("CNPJ/CPF fornecedor", value=dados_nfe.get("fornecedor_cnpj", ""), key=f"xml_forn_cnpj_{versao_xml}")

            pessoa_rotulo_xml = st.selectbox(
                "Vincular fornecedor a uma pessoa cadastrada (opcional)",
                list(pessoas_op.keys()),
                key=f"estoque_xml_pessoa_{versao_xml}",
            )
            pessoa_id_xml, pessoa_nome_xml = pessoas_op[pessoa_rotulo_xml]
            if not pessoa_nome_xml:
                pessoa_nome_xml = fornecedor_nome_xml

            st.info(
                "A NF pode ter itens de naturezas diferentes. Por isso, a classificação, o centro de custo, "
                "a atividade e o destino do rateio são definidos individualmente em cada produto da nota."
            )

            st.markdown("#### Itens encontrados no XML")
            itens_confirmar = []
            for idx, item in enumerate(dados_nfe.get("itens", []), start=1):
                with st.expander(f"Item {idx}: {item.get('descricao', '')} — {item.get('quantidade', 0)} {item.get('unidade', '')}", expanded=True):
                    a, b, c, d = st.columns(4)
                    a.write(f"**Código:** {item.get('codigo', '')}")
                    b.write(f"**NCM:** {item.get('ncm', '')}")
                    c.write(f"**CFOP:** {item.get('cfop', '')}")
                    d.write(f"**Valor:** {_formatar_moeda(item.get('valor_total'))}")

                    acao = st.radio(
                        "O que fazer com este item?",
                        ["Vincular a produto existente", "Cadastrar como produto novo", "Ignorar este item"],
                        horizontal=True,
                        key=f"xml_item_acao_{versao_xml}_{idx}",
                    )

                    produto_id = None
                    novo_produto = {}
                    if acao == "Vincular a produto existente":
                        produto_rotulo = st.selectbox("Produto do estoque", list(produtos_op.keys()), key=f"xml_item_prod_{versao_xml}_{idx}")
                        produto_id = produtos_op.get(produto_rotulo)
                        produto_existente = EstoqueRepository.buscar_produto(produto_id) if produto_id else None
                        if produto_existente:
                            fator_existente = float(produto_existente.get("qtd_consumo_por_unidade_compra") or 1)
                            unidade_consumo_existente = produto_existente.get("unidade_consumo") or produto_existente.get("unidade") or ""
                            qtd_estoque_preview, valor_unit_preview = _calcular_estoque_fracionado(item.get("quantidade"), item.get("valor_total"), fator_existente)
                            st.info(
                                f"Produto classificado como **{produto_existente.get('categoria') or 'Sem categoria'}**. "
                                f"Entrada no estoque: {qtd_estoque_preview:g} {unidade_consumo_existente} | "
                                f"Custo unitário: {_formatar_moeda(valor_unit_preview)} por {unidade_consumo_existente}"
                            )
                    elif acao == "Cadastrar como produto novo":
                        n1, n2, n3 = st.columns(3)
                        nome_novo = n1.text_input("Nome do novo produto", value=item.get("descricao", ""), key=f"xml_novo_nome_{versao_xml}_{idx}")
                        cat_novo = n2.selectbox("Categoria", [""] + EstoqueRepository.CATEGORIAS, key=f"xml_novo_cat_{versao_xml}_{idx}")
                        unidade_xml = item.get("unidade") or ""
                        unidade_padrao = unidade_xml if unidade_xml in EstoqueRepository.UNIDADES else ""
                        unidade_idx = ([""] + EstoqueRepository.UNIDADES).index(unidade_padrao) if unidade_padrao in ([""] + EstoqueRepository.UNIDADES) else 0
                        unidade_compra_novo = n3.selectbox("Unidade de compra/NF", [""] + EstoqueRepository.UNIDADES, index=unidade_idx, key=f"xml_novo_un_compra_{versao_xml}_{idx}")
                        q1, q2 = st.columns(2)
                        unidade_consumo_novo = q1.selectbox("Unidade de controle/consumo", [""] + EstoqueRepository.UNIDADES, key=f"xml_novo_un_consumo_{versao_xml}_{idx}", help="Ex: frasco comprado, mas estoque em mL.")
                        qtd_consumo_por_compra_novo = q2.number_input("Qtd. consumo por unidade comprada", min_value=0.0, step=1.0, value=1.0, key=f"xml_novo_fator_{versao_xml}_{idx}", help="Ex: 1 frasco com 50 mL = 50; 1 saco com 40 kg = 40.")
                        qtd_preview, valor_unit_preview = _calcular_estoque_fracionado(item.get("quantidade"), item.get("valor_total"), qtd_consumo_por_compra_novo)
                        st.info(f"Entrada no estoque: {qtd_preview:g} {unidade_consumo_novo or unidade_compra_novo or unidade_xml} | Custo unitário: {_formatar_moeda(valor_unit_preview)}")
                        novo_produto = {
                            "nome": nome_novo,
                            "categoria": cat_novo,
                            "apresentacao": f"{qtd_consumo_por_compra_novo:g} {unidade_consumo_novo} por {unidade_compra_novo or unidade_xml}",
                            "laboratorio_fabricante": "",
                            "unidade": unidade_consumo_novo or unidade_compra_novo or unidade_xml,
                            "unidade_compra": unidade_compra_novo or unidade_xml,
                            "unidade_consumo": unidade_consumo_novo or unidade_compra_novo or unidade_xml,
                            "qtd_consumo_por_unidade_compra": qtd_consumo_por_compra_novo,
                            "estoque_minimo": 0,
                            "valor_unitario": valor_unit_preview,
                            "data_vencimento": "",
                            "observacoes": f"Cadastrado a partir da NF {nf_numero}",
                            "ativo": 1,
                        }

                    item_centro_col, item_atividade_col = st.columns(2)
                    item_centro_custo = item_centro_col.selectbox(
                        "Centro de custo deste item",
                        [""] + FinanceiroRepository.CENTROS_CUSTO,
                        key=f"xml_item_centro_{versao_xml}_{idx}",
                        help="Ex: Sanidade, Manejo, Reprodução, Alimentação. Cada produto da mesma NF pode ter um centro de custo diferente.",
                    )
                    item_atividade = item_atividade_col.selectbox(
                        "Atividade deste item",
                        [""] + FinanceiroRepository.ATIVIDADES,
                        key=f"xml_item_atividade_{versao_xml}_{idx}",
                    )

                    item_destino_tipo = st.selectbox(
                        "Aplicar este item para",
                        ["", "Animal específico", "Categoria", "Manejo", "Todos os Animais"],
                        key=f"xml_item_destino_tipo_{versao_xml}_{idx}",
                        help="Define quem receberá o custo/consumo deste produto. Essa escolha é individual por item da NF.",
                    )
                    item_animal_sbb, item_categoria_animal, item_manejo = _render_destino_estoque(
                        f"xml_item_destino_{versao_xml}_{idx}",
                        item_destino_tipo,
                        animais_op,
                    )

                    itens_confirmar.append({
                        "item_xml": item,
                        "acao": acao,
                        "produto_id": produto_id,
                        "novo_produto": novo_produto,
                        "centro_custo": item_centro_custo,
                        "atividade": item_atividade,
                        "destino_tipo": item_destino_tipo,
                        "animal_sbb": item_animal_sbb,
                        "categoria_animal": item_categoria_animal,
                        "manejo": item_manejo,
                    })

            obs_xml = st.text_area("Observações", key=f"xml_obs_{versao_xml}")
            col_xml1, col_xml2 = st.columns(2)
            confirmar_xml = col_xml1.button("Confirmar entrada da NF no estoque", type="primary", use_container_width=True, key=f"confirmar_xml_{versao_xml}")
            limpar_xml = col_xml2.button("Limpar XML", use_container_width=True, key=f"limpar_xml_{versao_xml}")

            if limpar_xml:
                st.session_state.pop("estoque_xml_dados", None)
                st.session_state["estoque_xml_form_version"] = versao_xml + 1
                st.rerun()

            if confirmar_xml:
                processados = 0
                erros = []

                # Primeiro valida todos os itens da NF. Assim evitamos gravar metade da nota
                # se algum produto estiver sem classificação, destino ou vínculo.
                for idx, item_cfg in enumerate(itens_confirmar, start=1):
                    if item_cfg["acao"] == "Ignorar este item":
                        continue

                    erro_destino = _validar_destino_estoque(
                        item_cfg.get("destino_tipo"),
                        item_cfg.get("animal_sbb"),
                        item_cfg.get("categoria_animal"),
                        item_cfg.get("manejo"),
                    )
                    if not item_cfg.get("centro_custo"):
                        erros.append(f"Item {idx}: selecione o centro de custo.")
                    if not item_cfg.get("atividade"):
                        erros.append(f"Item {idx}: selecione a atividade.")
                    if not item_cfg.get("destino_tipo"):
                        erros.append(f"Item {idx}: selecione para quem este item será aplicado.")
                    if erro_destino:
                        erros.append(f"Item {idx}: {erro_destino}")

                    if item_cfg["acao"] == "Cadastrar como produto novo":
                        novo = item_cfg.get("novo_produto") or {}
                        if not str(novo.get("nome", "")).strip():
                            erros.append(f"Item {idx}: informe o nome do produto novo.")
                        if not str(novo.get("categoria", "")).strip():
                            erros.append(f"Item {idx}: selecione a categoria do produto novo.")
                    elif item_cfg["acao"] == "Vincular a produto existente" and not item_cfg.get("produto_id"):
                        erros.append(f"Item {idx}: selecione o produto existente.")

                if erros:
                    st.error("\n".join(erros))
                else:
                    for idx, item_cfg in enumerate(itens_confirmar, start=1):
                        if item_cfg["acao"] == "Ignorar este item":
                            continue

                        produto_id_final = item_cfg.get("produto_id")
                        if item_cfg["acao"] == "Cadastrar como produto novo":
                            produto_id_final = EstoqueRepository.salvar_produto(item_cfg.get("novo_produto") or {})

                        item = item_cfg["item_xml"]
                        produto_conv = EstoqueRepository.buscar_produto(produto_id_final) or {}
                        fator_conv = float(produto_conv.get("qtd_consumo_por_unidade_compra") or 1)
                        quantidade_estoque, valor_unitario_estoque = _calcular_estoque_fracionado(
                            item.get("quantidade"),
                            item.get("valor_total"),
                            fator_conv,
                        )
                        unidade_consumo_obs = produto_conv.get("unidade_consumo") or produto_conv.get("unidade") or ""

                        EstoqueRepository.salvar_movimentacao({
                            "produto_id": produto_id_final,
                            "tipo_movimento": "Entrada",
                            "data_movimento": nf_emissao,
                            "quantidade": quantidade_estoque,
                            "valor_unitario": valor_unitario_estoque,
                            "valor_total": float(item.get("valor_total") or 0),
                            "pessoa_id": pessoa_id_xml,
                            "pessoa_nome": pessoa_nome_xml,
                            "destino_tipo": item_cfg.get("destino_tipo"),
                            "animal_sbb": item_cfg.get("animal_sbb"),
                            "categoria_animal": item_cfg.get("categoria_animal"),
                            "manejo": item_cfg.get("manejo"),
                            "centro_custo": item_cfg.get("centro_custo"),
                            "atividade": item_cfg.get("atividade"),
                            "observacoes": (
                                f"NF {nf_numero} série {nf_serie}. "
                                f"Fornecedor: {fornecedor_nome_xml} {fornecedor_cnpj_xml}. "
                                f"Valor NF: {_formatar_moeda(nf_valor)}. "
                                f"Chave: {dados_nfe.get('chave', '')}. "
                                f"Item NF: {item.get('descricao', '')}. "
                                f"Compra na NF: {item.get('quantidade', 0)} {item.get('unidade', '')}; "
                                f"entrada convertida: {quantidade_estoque:g} {unidade_consumo_obs}. "
                                f"{obs_xml}"
                            ),
                        })
                        processados += 1

                    st.session_state.pop("estoque_xml_dados", None)
                    st.session_state["estoque_mov_msg"] = f"✅ NF {nf_numero} importada com sucesso. {processados} item(ns) entraram no estoque com classificação e destino individuais."
                    st.session_state["estoque_xml_form_version"] = versao_xml + 1
                    st.rerun()

        st.markdown("### Produtos cadastrados")
        f1, f2, f3 = st.columns(3)
        busca = f1.text_input("Buscar produto", key="estoque_busca_produto")
        cat = f2.selectbox("Categoria", [""] + EstoqueRepository.CATEGORIAS, key="estoque_cat_produto")
        incluir = f3.checkbox("Mostrar inativos", key="estoque_prod_inativos")
        df_prod = pd.DataFrame(EstoqueRepository.listar_produtos(incluir_inativos=incluir, busca=busca, categoria=cat))
        st.dataframe(df_prod, use_container_width=True, hide_index=True)
        if not df_prod.empty:
            excluir_id = st.selectbox("Excluir produto", [""] + [str(x) for x in df_prod["id"].tolist()], key="estoque_excluir_produto")
            if excluir_id and st.button("Confirmar exclusão do produto", type="secondary"):
                EstoqueRepository.excluir_produto(int(excluir_id))
                st.success("Produto inativado com sucesso.")
                st.rerun()

    with tab_mov:
        st.markdown("### Nova movimentação sem nota fiscal")
        if st.session_state.get("estoque_mov_msg"):
            st.success(st.session_state.pop("estoque_mov_msg"))
        st.info("Use esta tela quando não houver nota fiscal. Se houver XML de NF-e, faça a importação em Insumos e Cadastros.")
        versao_mov = st.session_state.get("estoque_mov_form_version", 0)
        with st.form(f"form_estoque_mov_{versao_mov}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                produto_rotulo = st.selectbox("Produto *", list(produtos_op.keys()))
                produto_id = produtos_op.get(produto_rotulo)
                tipo_mov = st.selectbox("Tipo de movimentação", EstoqueRepository.TIPOS_MOVIMENTO)
                data_mov = st.text_input("Data do movimento", placeholder="DD/MM/AAAA")
            with c2:
                quantidade = st.number_input("Quantidade na unidade de consumo/controle", min_value=0.0, step=1.0)
                valor_unitario = st.number_input("Valor unitário da unidade de consumo", min_value=0.0, step=1.0)
                valor_total = quantidade * valor_unitario
                st.write(f"**Valor total estimado:** {_formatar_moeda(valor_total)}")
            with c3:
                pessoa_rotulo = st.selectbox("Pessoa relacionada", list(pessoas_op.keys()))
                pessoa_id, pessoa_nome = pessoas_op[pessoa_rotulo]
                centro_custo = st.selectbox("Centro de custo", [""] + FinanceiroRepository.CENTROS_CUSTO)
                atividade = st.selectbox("Atividade", [""] + FinanceiroRepository.ATIVIDADES)

            d1, d2 = st.columns(2)
            with d1:
                destino_tipo = st.selectbox("Destino / Aplicação", ["", "Animal específico", "Categoria", "Manejo", "Todos os Animais"])
            with d2:
                animal_sbb = categoria_animal = manejo = ""
                animal_sbb, categoria_animal, manejo = _render_destino_estoque("manual", destino_tipo, animais_op)

            observacoes = st.text_area("Observações da movimentação")
            salvar_mov = st.form_submit_button("Salvar movimentação", type="primary", use_container_width=True)
            if salvar_mov:
                erro_destino = _validar_destino_estoque(destino_tipo, animal_sbb, categoria_animal, manejo)
                if not produto_id:
                    st.warning("Selecione um produto.")
                elif quantidade <= 0:
                    st.warning("Informe quantidade maior que zero.")
                elif erro_destino:
                    st.warning(erro_destino)
                else:
                    mov_id = EstoqueRepository.salvar_movimentacao({
                        "produto_id": produto_id,
                        "tipo_movimento": tipo_mov,
                        "data_movimento": data_mov,
                        "quantidade": quantidade,
                        "valor_unitario": valor_unitario,
                        "valor_total": valor_total,
                        "pessoa_id": pessoa_id,
                        "pessoa_nome": pessoa_nome,
                        "destino_tipo": destino_tipo,
                        "animal_sbb": animal_sbb,
                        "categoria_animal": categoria_animal,
                        "manejo": manejo,
                        "centro_custo": centro_custo,
                        "atividade": atividade,
                        "observacoes": observacoes,
                    })
                    st.session_state["estoque_mov_msg"] = f"✅ Movimentação #{mov_id} registrada com sucesso. O formulário foi limpo."
                    st.session_state["estoque_mov_form_version"] = versao_mov + 1
                    st.rerun()

        st.markdown("### Movimentações registradas")
        mf1, mf2, mf3 = st.columns(3)
        m_tipo = mf1.selectbox("Movimento", [""] + EstoqueRepository.TIPOS_MOVIMENTO, key="estoque_f_mov")
        m_cat = mf2.selectbox("Categoria produto", [""] + EstoqueRepository.CATEGORIAS, key="estoque_f_cat_mov")
        m_busca = mf3.text_input("Buscar", key="estoque_f_busca_mov")
        movs = EstoqueRepository.listar_movimentacoes({"tipo_movimento": m_tipo, "categoria": m_cat, "busca": m_busca})
        df_mov = pd.DataFrame(movs)
        st.dataframe(df_mov, use_container_width=True, hide_index=True)
        if not df_mov.empty:
            mov_excluir = st.selectbox("Excluir movimentação", [""] + [str(x) for x in df_mov["id"].tolist()], key="estoque_excluir_mov")
            if mov_excluir and st.button("Confirmar exclusão da movimentação", type="secondary"):
                EstoqueRepository.excluir_movimentacao(int(mov_excluir))
                st.success("Movimentação excluída logicamente.")
                st.rerun()

    with tab_saldos:
        st.markdown("### Saldos")
        saldos = EstoqueRepository.saldos()
        df_saldos = pd.DataFrame(saldos)
        if not df_saldos.empty:
            baixo = df_saldos[df_saldos["Saldo"] <= df_saldos["Estoque Mínimo"]]
            if not baixo.empty:
                st.warning(f"{len(baixo)} produto(s) estão no estoque mínimo ou abaixo.")
            st.dataframe(df_saldos, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum saldo encontrado.")



def _animais_ativos_lista():
    return listar_animais(incluir_inativos=False)


def _animais_por_destino_sanidade(destino_tipo, animal_sbb="", animais_sbb=None, categoria_animal="", manejo=""):
    animais = _animais_ativos_lista()
    animais_sbb = animais_sbb or []
    selecionados = []
    for a in animais:
        sbb = a.get("sbb")
        if destino_tipo == "Animal específico" and sbb == animal_sbb:
            selecionados.append(a)
        elif destino_tipo == "Vários animais" and sbb in animais_sbb:
            selecionados.append(a)
        elif destino_tipo == "Categoria" and (a.get("categoria_idade") or "") == categoria_animal:
            selecionados.append(a)
        elif destino_tipo == "Manejo" and (a.get("manejo") or "") == manejo:
            selecionados.append(a)
        elif destino_tipo == "Todos os Animais":
            selecionados.append(a)
    return selecionados


def render_modulo_sanidade():
    st.subheader("Sanidade e Farmácia")
    st.caption("Registro de vacinas, vermífugos, medicações e atendimentos veterinários, com baixa opcional do estoque, custo por animal/grupo e alerta de próxima dose.")

    tab_novo, tab_eventos, tab_alertas = st.tabs(["Novo evento sanitário", "Histórico e relatórios", "Alertas de próximas doses"])
    animais_op = _opcoes_animais_financeiro()
    pessoas_op = _opcoes_pessoas_financeiro()
    produtos_op = _opcoes_produtos_estoque()

    with tab_novo:
        if st.session_state.get("sanidade_msg"):
            st.success(st.session_state.pop("sanidade_msg"))

        versao = st.session_state.get("sanidade_form_version", 0)
        prefix = f"san_{versao}"

        st.markdown("### Dados do evento")
        c1, c2, c3 = st.columns(3)
        with c1:
            tipo_evento = st.selectbox("Tipo de evento *", SanidadeRepository.TIPOS, key=f"{prefix}_tipo_evento")
            data_evento = st.text_input("Data do evento *", placeholder="DD/MM/AAAA", key=f"{prefix}_data_evento")
            protocolo = st.selectbox("Protocolo", SanidadeRepository.PROTOCOLOS, key=f"{prefix}_protocolo")
        with c2:
            produto_valor, produto_rotulo = selectbox_com_cadastro_rapido(
                "Produto do estoque",
                produtos_op,
                key=f"{prefix}_produto",
                tipo="produto",
                categoria_padrao="Medicamento",
                help_text="A primeira opção permite cadastrar um novo produto sem sair deste evento.",
            )
            produto_id = produto_valor
            produto_nome = produto_rotulo.split(" | ")[0] if produto_rotulo and not produto_rotulo.startswith("➕") else ""
            principio_ativo = st.text_input("Princípio ativo", key=f"{prefix}_principio")
            nome_comercial = st.text_input("Nome comercial", value=produto_nome, key=f"{prefix}_nome_comercial")
        with c3:
            lote = st.text_input("Lote", key=f"{prefix}_lote")
            via_aplicacao = st.selectbox("Via de aplicação", SanidadeRepository.VIAS, key=f"{prefix}_via")
            proxima_dose = st.text_input("Próxima dose / reforço", placeholder="DD/MM/AAAA", key=f"{prefix}_prox")

        st.markdown("### Animais atendidos")
        d1, d2 = st.columns([1, 2])
        with d1:
            destino_tipo = st.selectbox("Aplicar para", ["", "Animal específico", "Vários animais", "Categoria", "Manejo", "Todos os Animais"], key=f"{prefix}_destino")
        with d2:
            animal_sbb = ""; animais_sbb = []; categoria_animal = ""; manejo = ""
            if destino_tipo == "Animal específico":
                animal_rotulo = st.selectbox("Animal", list(animais_op.keys()), key=f"{prefix}_animal")
                animal_sbb = animais_op.get(animal_rotulo, "")
            elif destino_tipo == "Vários animais":
                labels = [k for k in animais_op.keys() if k]
                escolhidos = st.multiselect("Animais", labels, key=f"{prefix}_animais_multi")
                animais_sbb = [animais_op[x] for x in escolhidos]
            elif destino_tipo == "Categoria":
                categoria_animal = st.selectbox("Categoria animal", _opcoes_categorias_animais(), key=f"{prefix}_categoria")
            elif destino_tipo == "Manejo":
                manejo = st.selectbox("Manejo", _opcoes_manejos_animais(), key=f"{prefix}_manejo")
            elif destino_tipo == "Todos os Animais":
                st.info("O evento será aplicado a todos os animais ativos na cabanha.")

        animais_sel = _animais_por_destino_sanidade(destino_tipo, animal_sbb, animais_sbb, categoria_animal, manejo)
        if destino_tipo:
            st.caption(f"Animais selecionados para o evento: {len(animais_sel)}")

        st.markdown("### Quantidade, custo e responsável")
        q1, q2, q3 = st.columns(3)
        with q1:
            quantidade_por_animal = st.number_input("Quantidade por animal", min_value=0.0, step=1.0, key=f"{prefix}_qtd")
            unidade = st.selectbox("Unidade", [""] + EstoqueRepository.UNIDADES, key=f"{prefix}_un")
            valor_unitario = st.number_input("Valor unitário do produto", min_value=0.0, step=1.0, key=f"{prefix}_vl_unit")
        with q2:
            pessoa_valor, pessoa_rotulo = selectbox_com_cadastro_rapido(
                "Veterinário / responsável",
                pessoas_op,
                key=f"{prefix}_pessoa",
                tipo="pessoa",
                papel_padrao="Veterinário",
                help_text="A primeira opção permite cadastrar uma nova pessoa sem sair deste evento.",
            )
            veterinario_pessoa_id, veterinario_nome = pessoa_valor if pessoa_valor else (None, "")
            local_atendimento = st.text_input("Local", key=f"{prefix}_local")
            motivo = st.text_input("Motivo", key=f"{prefix}_motivo")
        with q3:
            honorarios = st.number_input("Honorários", min_value=0.0, step=1.0, key=f"{prefix}_hon")
            outros_custos = st.number_input("Outros custos", min_value=0.0, step=1.0, key=f"{prefix}_outros")
            centro_custo = st.selectbox("Centro de custo", [""] + FinanceiroRepository.CENTROS_CUSTO, key=f"{prefix}_cc")
            atividade = st.selectbox("Atividade", [""] + FinanceiroRepository.ATIVIDADES, key=f"{prefix}_ativ")

        quantidade_total = quantidade_por_animal * len(animais_sel)
        valor_produtos = quantidade_total * valor_unitario
        custo_total = valor_produtos + honorarios + outros_custos
        st.info(f"Quantidade total: {quantidade_total:g} {unidade or ''} | Custo total estimado: {_formatar_moeda(custo_total)} | Custo médio por animal: {_formatar_moeda(custo_total / len(animais_sel) if animais_sel else 0)}")

        gerar_baixa_estoque = st.checkbox("Gerar saída automática do estoque", value=bool(produto_id and quantidade_total > 0), key=f"{prefix}_baixa")
        gerar_financeiro = st.checkbox("Gerar lançamento financeiro automaticamente", value=bool(custo_total > 0), key=f"{prefix}_fin")
        observacoes = st.text_area("Observações", key=f"{prefix}_obs")

        col_salvar, col_limpar = st.columns(2)
        salvar = col_salvar.button("Salvar evento sanitário", type="primary", use_container_width=True, key=f"{prefix}_salvar")
        limpar = col_limpar.button("Limpar / Novo evento", use_container_width=True, key=f"{prefix}_limpar")
        if limpar:
            st.session_state["sanidade_form_version"] = versao + 1
            st.session_state["sanidade_msg"] = "Formulário limpo para novo evento."
            st.rerun()

        if salvar:
            if not data_evento.strip():
                st.warning("Informe a data do evento.")
            elif not destino_tipo:
                st.warning("Informe para quais animais este evento será aplicado.")
            elif not animais_sel:
                st.warning("Nenhum animal foi selecionado para este evento.")
            elif gerar_baixa_estoque and not produto_id:
                st.warning("Para gerar baixa de estoque, selecione um produto do estoque.")
            else:
                animais_payload = []
                custo_rateado = custo_total / len(animais_sel) if animais_sel else 0
                for a in animais_sel:
                    animais_payload.append({
                        "animal_sbb": a.get("sbb"),
                        "animal_nome": a.get("nome") or "",
                        "quantidade": quantidade_por_animal,
                        "custo_rateado": custo_rateado,
                    })
                evento_id = SanidadeRepository.salvar_evento({
                    "tipo_evento": tipo_evento,
                    "data_evento": data_evento,
                    "protocolo": protocolo,
                    "principio_ativo": principio_ativo,
                    "nome_comercial": nome_comercial,
                    "lote": lote,
                    "via_aplicacao": via_aplicacao,
                    "produto_id": produto_id,
                    "produto_nome": produto_nome or nome_comercial,
                    "quantidade_total": quantidade_total,
                    "unidade": unidade,
                    "valor_produtos": valor_produtos,
                    "veterinario_pessoa_id": veterinario_pessoa_id,
                    "veterinario_nome": veterinario_nome,
                    "local_atendimento": local_atendimento,
                    "motivo": motivo,
                    "honorarios": honorarios,
                    "outros_custos": outros_custos,
                    "custo_total": custo_total,
                    "proxima_dose": proxima_dose,
                    "centro_custo": centro_custo,
                    "atividade": atividade,
                    "gerar_financeiro": gerar_financeiro,
                    "observacoes": observacoes,
                }, animais_payload)

                mov_id = None
                if gerar_baixa_estoque and produto_id and quantidade_total > 0:
                    mov_id = EstoqueRepository.salvar_movimentacao({
                        "produto_id": produto_id,
                        "tipo_movimento": "Saída / Consumo",
                        "data_movimento": data_evento,
                        "quantidade": quantidade_total,
                        "valor_unitario": valor_unitario,
                        "valor_total": valor_produtos,
                        "pessoa_id": veterinario_pessoa_id,
                        "pessoa_nome": veterinario_nome,
                        "destino_tipo": destino_tipo,
                        "animal_sbb": animal_sbb,
                        "categoria_animal": categoria_animal,
                        "manejo": manejo,
                        "centro_custo": centro_custo,
                        "atividade": atividade,
                        "observacoes": f"Baixa automática gerada pelo evento sanitário #{evento_id}. {tipo_evento}. {observacoes}",
                    })

                lanc_id = None
                if gerar_financeiro and custo_total > 0:
                    parcelas = [{"numero": 1, "vencimento": data_evento, "valor": custo_total, "status": "Aberta", "observacoes": f"Evento sanitário #{evento_id}"}]
                    rateios = []
                    for a in animais_payload:
                        rateios.append({
                            "criterio_rateio": "Animal específico",
                            "animal_sbb": a["animal_sbb"],
                            "categoria_animal": "",
                            "manejo": "",
                            "percentual": 100 / len(animais_payload),
                            "valor_rateado": a["custo_rateado"],
                            "observacoes": f"Rateio automático do evento sanitário #{evento_id}",
                        })
                    lanc_id = FinanceiroRepository.salvar_lancamento({
                        "tipo": "Saída",
                        "data_evento": data_evento,
                        "data_emissao": data_evento,
                        "competencia": data_evento[3:] if len(data_evento) == 10 else data_evento,
                        "descricao": f"{tipo_evento} - {nome_comercial or principio_ativo or 'Evento sanitário'}",
                        "pessoa_id": veterinario_pessoa_id,
                        "pessoa_nome": veterinario_nome,
                        "valor_total": custo_total,
                        "forma_pagamento": "",
                        "centro_custo": centro_custo or "Veterinário",
                        "atividade": atividade or "Sanidade",
                        "origem_modulo": "Sanidade",
                        "observacoes": f"Gerado automaticamente pelo evento sanitário #{evento_id}. {observacoes}",
                    }, parcelas, rateios)
                SanidadeRepository.atualizar_integracoes(evento_id, lancamento_financeiro_id=lanc_id, movimentacao_estoque_id=mov_id)
                for a in animais_payload:
                    EventoRepository.registrar({
                        "data_evento": data_evento,
                        "tipo_evento": tipo_evento,
                        "modulo_origem": "Sanidade",
                        "entidade_tipo": "Animal",
                        "entidade_id": a.get("animal_sbb"),
                        "animal_sbb": a.get("animal_sbb"),
                        "pessoa_id": veterinario_pessoa_id,
                        "produto_id": produto_id,
                        "lancamento_financeiro_id": lanc_id,
                        "movimentacao_estoque_id": mov_id,
                        "sanidade_evento_id": evento_id,
                        "descricao": f"{tipo_evento} - {nome_comercial or principio_ativo or produto_nome or 'Evento sanitário'}",
                        "observacoes": observacoes,
                    })
                st.session_state["sanidade_msg"] = f"✅ Evento sanitário #{evento_id} salvo com sucesso. Animais: {len(animais_sel)}. Estoque: {'sim' if mov_id else 'não'}. Financeiro: {'sim' if lanc_id else 'não'}."
                st.session_state["sanidade_form_version"] = versao + 1
                st.rerun()

    with tab_eventos:
        st.markdown("### Histórico sanitário")
        f1, f2, f3, f4 = st.columns(4)
        f_tipo = f1.selectbox("Tipo", [""] + SanidadeRepository.TIPOS, key="san_f_tipo")
        f_protocolo = f2.selectbox("Protocolo", [""] + [p for p in SanidadeRepository.PROTOCOLOS if p], key="san_f_prot")
        f_animal_rotulo = f3.selectbox("Animal", list(animais_op.keys()), key="san_f_animal")
        f_busca = f4.text_input("Buscar", key="san_f_busca")
        eventos = SanidadeRepository.listar_eventos({"tipo_evento": f_tipo, "protocolo": f_protocolo, "animal_sbb": animais_op.get(f_animal_rotulo, ""), "busca": f_busca})
        df_eventos = pd.DataFrame(eventos)
        st.dataframe(df_eventos, use_container_width=True, hide_index=True)
        if not df_eventos.empty:
            exc = st.selectbox("Excluir evento lançado por engano", [""] + [str(x) for x in df_eventos["id"].tolist()], key="san_exc")
            if exc and st.button("Confirmar exclusão do evento sanitário", type="secondary"):
                SanidadeRepository.excluir_evento(int(exc))
                st.success("Evento sanitário excluído logicamente.")
                st.rerun()

    with tab_alertas:
        st.markdown("### Próximas doses / reforços")
        alertas = SanidadeRepository.alertas()
        df_alertas = pd.DataFrame(alertas)
        if df_alertas.empty:
            st.info("Nenhum alerta de próxima dose cadastrado.")
        else:
            st.dataframe(df_alertas, use_container_width=True, hide_index=True)



# ============================================================
# REPRODUÇÃO
# ============================================================
def _opcoes_temporadas_reproducao():
    temporadas = ReproducaoRepository.listar_temporadas(incluir_inativas=False)
    op = {"": None}
    for t in temporadas:
        op[f"{t.get('nome')} | {t.get('status','')}"] = t
    return op


def _opcoes_matrizes_reproducao():
    animais = ReproducaoRepository.matrizes_ativas()
    op = {"": None}
    for a in animais:
        op[f"{a.get('nome') or ''} | {a.get('sbb') or ''}"] = a
    return op


def _opcoes_garanhoes_reproducao():
    animais = ReproducaoRepository.garanhoes_ativos()
    op = {"": None}
    for a in animais:
        op[f"{a.get('nome') or ''} | {a.get('sbb') or ''}"] = a
    return op


def render_modulo_reproducao():
    st.subheader("Reprodução")
    st.caption("Temporada reprodutiva, planejamento de acasalamentos, inseminações/coberturas e diagnóstico de gestação.")

    tab_temp, tab_plan, tab_eventos, tab_rel = st.tabs(["Temporadas", "Planejamento", "Execução do ciclo", "Relatórios"])

    pessoas_op = _opcoes_pessoas_financeiro()
    produtos_op = _opcoes_produtos_estoque()

    with tab_temp:
        if st.session_state.get("repro_temp_msg"):
            st.success(st.session_state.pop("repro_temp_msg"))
        st.markdown("### Nova temporada")
        v = st.session_state.get("repro_temp_form_version", 0)
        with st.form(f"form_temporada_repro_{v}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                nome = st.text_input("Nome da temporada *", placeholder="Ex: 2026/2027")
                status = st.selectbox("Status", ReproducaoRepository.STATUS_TEMPORADA)
            with c2:
                data_inicio = st.text_input("Data início", placeholder="DD/MM/AAAA")
                data_fim = st.text_input("Data fim", placeholder="DD/MM/AAAA")
            with c3:
                observacoes = st.text_area("Observações")
            salvar = st.form_submit_button("Salvar temporada", type="primary")
            if salvar:
                if not nome.strip():
                    st.warning("Informe o nome da temporada.")
                else:
                    temp_id = ReproducaoRepository.salvar_temporada({"nome": nome, "data_inicio": data_inicio, "data_fim": data_fim, "status": status, "observacoes": observacoes})
                    st.session_state.repro_temp_form_version = v + 1
                    st.session_state.repro_temp_msg = f"✅ Temporada cadastrada com sucesso. ID {temp_id}."
                    st.rerun()

        st.markdown("### Temporadas cadastradas")
        temporadas = pd.DataFrame(ReproducaoRepository.listar_temporadas())
        mostrar_df(temporadas, "Nenhuma temporada cadastrada.")
        if not temporadas.empty:
            ids = temporadas["id"].tolist()
            col1, col2 = st.columns([2, 1])
            tid = col1.selectbox("Selecionar temporada para arquivar/excluir", ids, format_func=lambda x: f"#{x} - {temporadas.loc[temporadas['id']==x, 'nome'].iloc[0]}")
            if col2.button("Arquivar temporada", use_container_width=True):
                ReproducaoRepository.excluir_temporada(tid)
                st.success("Temporada arquivada.")
                st.rerun()

    with tab_plan:
        if st.session_state.get("repro_plan_msg"):
            st.success(st.session_state.pop("repro_plan_msg"))
        st.markdown("### Novo planejamento")
        v = st.session_state.get("repro_plan_form_version", 0)
        temp_op = _opcoes_temporadas_reproducao()
        matrizes_op = _opcoes_matrizes_reproducao()
        garanhoes_op = _opcoes_garanhoes_reproducao()
        with st.form(f"form_planejamento_repro_{v}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                temp_label = st.selectbox("Temporada *", list(temp_op.keys()))
                temporada = temp_op.get(temp_label)
                matriz_label = st.selectbox("Matriz *", list(matrizes_op.keys()))
                matriz = matrizes_op.get(matriz_label)
                status_rep = st.selectbox("Status reprodutivo", ReproducaoRepository.STATUS_REPRODUTIVO)
            with c2:
                gar_label = st.selectbox("Garanhão pretendido", list(garanhoes_op.keys()))
                garanhao = garanhoes_op.get(gar_label)
                tipo_cobertura = st.selectbox("Tipo de cobertura", [""] + ReproducaoRepository.TIPOS_COBERTURA)
                custo_previsto = st.number_input("Custo previsto", min_value=0.0, step=100.0)
            with c3:
                vet_label = st.selectbox("Veterinário", list(pessoas_op.keys()), key=f"repro_plan_vet_{v}")
                vet_val = pessoas_op.get(vet_label)
                central_label = st.selectbox("Central", list(pessoas_op.keys()), key=f"repro_plan_central_{v}")
                central_val = pessoas_op.get(central_label)
                transp_label = st.selectbox("Transportador", list(pessoas_op.keys()), key=f"repro_plan_transp_{v}")
                transp_val = pessoas_op.get(transp_label)
            observacoes = st.text_area("Observações do cruzamento")
            salvar = st.form_submit_button("Salvar planejamento", type="primary")
            if salvar:
                if not temporada:
                    st.warning("Selecione a temporada.")
                elif not matriz:
                    st.warning("Selecione a matriz.")
                else:
                    plan_id = ReproducaoRepository.salvar_planejamento({
                        "temporada_id": temporada.get("id"), "temporada_nome": temporada.get("nome"),
                        "matriz_sbb": matriz.get("sbb"), "matriz_nome": matriz.get("nome"),
                        "garanhao_sbb": (garanhao or {}).get("sbb"), "garanhao_nome": (garanhao or {}).get("nome"),
                        "tipo_cobertura": tipo_cobertura,
                        "central_pessoa_id": central_val[0] if central_val else None, "central_nome": central_val[1] if central_val else "",
                        "veterinario_pessoa_id": vet_val[0] if vet_val else None, "veterinario_nome": vet_val[1] if vet_val else "",
                        "transportador_pessoa_id": transp_val[0] if transp_val else None, "transportador_nome": transp_val[1] if transp_val else "",
                        "status_reprodutivo": status_rep, "custo_previsto": custo_previsto, "observacoes": observacoes,
                    })
                    st.session_state.repro_plan_form_version = v + 1
                    st.session_state.repro_plan_msg = f"✅ Planejamento cadastrado com sucesso. ID {plan_id}."
                    st.rerun()

        st.markdown("### Planejamentos")
        f1, f2, f3 = st.columns(3)
        temp_f_op = _opcoes_temporadas_reproducao()
        tf_label = f1.selectbox("Filtrar temporada", list(temp_f_op.keys()), key="repro_f_temp")
        sf = f2.selectbox("Filtrar status", [""] + ReproducaoRepository.STATUS_REPRODUTIVO, key="repro_f_status")
        busca = f3.text_input("Buscar", key="repro_f_busca")
        filtros = {"busca": busca, "status_reprodutivo": sf}
        if temp_f_op.get(tf_label):
            filtros["temporada_id"] = temp_f_op[tf_label]["id"]
        plans = pd.DataFrame(ReproducaoRepository.listar_planejamentos(filtros))
        mostrar_df(plans, "Nenhum planejamento encontrado.")
        if not plans.empty:
            ids = plans["id"].tolist()
            pid = st.selectbox("Selecionar planejamento para excluir", ids, format_func=lambda x: f"#{x} - {plans.loc[plans['id']==x, 'Matriz'].iloc[0]}")
            if st.button("Excluir planejamento selecionado"):
                ReproducaoRepository.excluir_planejamento(pid)
                st.success("Planejamento excluído/inativado.")
                st.rerun()

    with tab_eventos:
        if st.session_state.get("repro_evento_msg"):
            st.success(st.session_state.pop("repro_evento_msg"))
        st.markdown("### Registrar execução do ciclo")
        v = st.session_state.get("repro_evento_form_version", 0)
        plans_raw = ReproducaoRepository.listar_planejamentos({})
        plan_op = {"": None}
        for p in plans_raw:
            plan_op[f"#{p.get('id')} | {p.get('Matriz')} x {p.get('Garanhão') or '---'} | {p.get('Temporada')}"] = p.get("id")
        with st.form(f"form_evento_repro_{v}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                plan_label = st.selectbox("Planejamento *", list(plan_op.keys()))
                planejamento_id = plan_op.get(plan_label)
                plan = ReproducaoRepository.buscar_planejamento(planejamento_id) if planejamento_id else None
                tipo_evento = st.selectbox("Tipo de evento", ["Inseminação/Cobertura", "Diagnóstico de gestação", "Parto", "Falha/Repetição", "Outro"])
                data_evento = st.text_input("Data do evento *", placeholder="DD/MM/AAAA")
            with c2:
                tipo_cobertura = st.selectbox("Tipo de cobertura", [""] + ReproducaoRepository.TIPOS_COBERTURA, index=0)
                diagnostico = st.selectbox("Diagnóstico", [""] + ReproducaoRepository.TIPOS_DIAGNOSTICO)
                status_resultante = st.selectbox("Status resultante", [""] + ReproducaoRepository.STATUS_REPRODUTIVO)
            with c3:
                vet_label = st.selectbox("Veterinário", list(pessoas_op.keys()), key=f"repro_event_vet_{v}")
                vet_val = pessoas_op.get(vet_label)
                produto_label = st.selectbox("Produto/medicação/sêmen do estoque", list(produtos_op.keys()), key=f"repro_event_prod_{v}")
                produto_val = produtos_op.get(produto_label)
                quantidade_produto = st.number_input("Quantidade produto", min_value=0.0, step=1.0)
                unidade_produto = st.selectbox("Unidade", [""] + EstoqueRepository.UNIDADES)
            c4, c5, c6 = st.columns(3)
            with c4:
                custo_total = st.number_input("Custo total do evento", min_value=0.0, step=100.0)
            with c5:
                centro_custo = st.selectbox("Centro de custo", [""] + FinanceiroRepository.CENTROS_CUSTO)
            with c6:
                atividade = st.selectbox("Atividade", [""] + FinanceiroRepository.ATIVIDADES)
            observacoes = st.text_area("Observações")
            salvar = st.form_submit_button("Salvar evento reprodutivo", type="primary")
            if salvar:
                if not plan:
                    st.warning("Selecione um planejamento.")
                elif not data_evento.strip():
                    st.warning("Informe a data do evento.")
                else:
                    if not tipo_cobertura:
                        tipo_cobertura = plan.get("tipo_cobertura") or ""
                    if tipo_evento == "Diagnóstico de gestação" and diagnostico == "Positivo" and not status_resultante:
                        status_resultante = "Prenha"
                    elif tipo_evento == "Diagnóstico de gestação" and diagnostico == "Negativo" and not status_resultante:
                        status_resultante = "Falhada"
                    evento_id = ReproducaoRepository.salvar_evento({
                        "planejamento_id": plan.get("id"), "temporada_id": plan.get("temporada_id"), "temporada_nome": plan.get("temporada_nome"),
                        "matriz_sbb": plan.get("matriz_sbb"), "matriz_nome": plan.get("matriz_nome"),
                        "garanhao_sbb": plan.get("garanhao_sbb"), "garanhao_nome": plan.get("garanhao_nome"),
                        "tipo_evento": tipo_evento, "data_evento": data_evento, "tipo_cobertura": tipo_cobertura,
                        "diagnostico": diagnostico, "status_resultante": status_resultante,
                        "veterinario_pessoa_id": vet_val[0] if vet_val else plan.get("veterinario_pessoa_id"), "veterinario_nome": vet_val[1] if vet_val else plan.get("veterinario_nome"),
                        "produto_id": produto_val, "produto_nome": produto_label.split(" | ")[0] if produto_label else "",
                        "quantidade_produto": quantidade_produto, "unidade_produto": unidade_produto,
                        "custo_total": custo_total, "centro_custo": centro_custo, "atividade": atividade, "observacoes": observacoes,
                    })
                    # Alimenta linha do tempo da matriz.
                    EventoRepository.registrar({
                        "data_evento": data_evento,
                        "tipo_evento": tipo_evento,
                        "modulo_origem": "Reprodução",
                        "entidade_tipo": "reproducao_evento",
                        "entidade_id": evento_id,
                        "animal_sbb": plan.get("matriz_sbb"),
                        "pessoa_id": vet_val[0] if vet_val else plan.get("veterinario_pessoa_id"),
                        "produto_id": produto_val,
                        "descricao": f"{tipo_evento}: {plan.get('matriz_nome')} x {plan.get('garanhao_nome') or '---'}",
                        "observacoes": observacoes,
                    })
                    st.session_state.repro_evento_form_version = v + 1
                    st.session_state.repro_evento_msg = f"✅ Evento reprodutivo cadastrado com sucesso. ID {evento_id}."
                    st.rerun()

        st.markdown("### Eventos reprodutivos")
        eventos = pd.DataFrame(ReproducaoRepository.listar_eventos({}))
        mostrar_df(eventos, "Nenhum evento reprodutivo registrado.")

    with tab_rel:
        st.markdown("### Indicadores iniciais")
        plans = ReproducaoRepository.listar_planejamentos({})
        eventos = ReproducaoRepository.listar_eventos({})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Planejamentos", len(plans))
        c2.metric("Eventos", len(eventos))
        c3.metric("Matrizes ativas", len(ReproducaoRepository.matrizes_ativas()))
        c4.metric("Garanhões ativos", len(ReproducaoRepository.garanhoes_ativos()))
        if plans:
            dfp = pd.DataFrame(plans)
            if "Status" in dfp.columns:
                st.markdown("### Status dos planejamentos")
                st.dataframe(dfp.groupby("Status").size().reset_index(name="Quantidade"), use_container_width=True, hide_index=True)


st.sidebar.markdown("## Navegação")
modulo = st.sidebar.radio(
    "Selecione o módulo",
    [
        "Cadastrar por SBB",
        "Fila de Extração",
        "Cadastro Completo",
        "Pessoas",
        "Financeiro",
        "Estoque",
        "Sanidade",
        "Reprodução",
    ],
    key="menu_principal_modulo",
)

if modulo == "Cadastrar por SBB":
    st.subheader("Informar SBBs para cadastro")
    st.write("Use o botão **+ Adicionar SBB** para montar a lista antes de iniciar a extração.")

    if st.session_state.get("sbb_cadastro_msg"):
        st.success(st.session_state.pop("sbb_cadastro_msg"))

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
            limpar_chaves_session(["sbb_"])
            st.session_state.sbb_cadastro_msg = "Lista limpa para novo cadastro."
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
                st.session_state.sbb_inputs = [""]
                limpar_chaves_session(["sbb_"])
                st.session_state.sbb_cadastro_msg = f"✅ {len(lista)} SBB(s) enviado(s) para a fila de extração. O formulário foi limpo."
                st.rerun()

    st.divider()
    st.info("Nesta etapa o sistema grava os dados em banco. A planilha deixa de ser o destino final e passa a servir apenas como referência de estrutura.")

if modulo == "Fila de Extração":
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

if modulo == "Cadastro Completo":
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

    tab_resumo, tab_principal, tab_meritos, tab_padreacoes, tab_desc, tab_irmaos, tab_pedigree, tab_venda_parceria, tab_historico, tab_linha_tempo = st.tabs([
        "Resumo do Cadastro",
        "Principal ABCCC",
        "Méritos",
        "Padreações",
        "Descendentes",
        "Irmãos",
        "Pedigree",
        "Venda / Parceria",
        "Histórico",
        "Linha do Tempo",
    ])

    with tab_resumo:
        if st.session_state.get("animal_cadastro_msg"):
            st.success(st.session_state.pop("animal_cadastro_msg"))
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
            st.session_state.animal_cadastro_msg = "✅ Cadastro do animal atualizado com sucesso."
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
        pedigree_visivel = montar_pedigree_visivel(pedigree)
        df_pedigree = pd.DataFrame(pedigree_visivel)
        mostrar_df(df_pedigree, "Nenhum pedigree extraído para este animal.")


    with tab_venda_parceria:
        if st.session_state.get("venda_parceria_msg"):
            st.success(st.session_state.pop("venda_parceria_msg"))
        st.markdown("### Venda do animal")
        st.caption("Ao informar data de entrega, o animal muda para 'Vendido e entregue' e sai das listas operacionais futuras, mantendo histórico para consulta.")
        venda_form_version = st.session_state.get("venda_form_version", 0)
        with st.form(f"form_venda_animal_{sbb}_{venda_form_version}"):
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
                st.session_state.venda_form_version = st.session_state.get("venda_form_version", 0) + 1
                st.session_state.venda_parceria_msg = "✅ Venda registrada com sucesso. O formulário foi limpo."
                st.rerun()

        vendas = listar_vendas_animal(sbb)
        mostrar_df(pd.DataFrame(vendas), "Nenhuma venda registrada para este animal.")

        st.divider()
        st.markdown("### Parceria")
        parceria_form_version = st.session_state.get("parceria_form_version", 0)
        with st.form(f"form_parceria_animal_{sbb}_{parceria_form_version}"):
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
                st.session_state.parceria_form_version = st.session_state.get("parceria_form_version", 0) + 1
                st.session_state.venda_parceria_msg = "✅ Parceria registrada com sucesso. O formulário foi limpo."
                st.rerun()

        parcerias = listar_parcerias_animal(sbb)
        mostrar_df(pd.DataFrame(parcerias), "Nenhuma parceria registrada para este animal.")

    with tab_historico:
        st.markdown("### Histórico de status no ecossistema")
        historico = listar_historico_status(sbb)
        mostrar_df(pd.DataFrame(historico), "Nenhuma alteração de status registrada.")
        st.info("Nesta aba ficará a linha do tempo do animal. Por enquanto começamos pelo histórico de status; depois sanidade, reprodução, morfologia e financeiro também alimentarão esta linha do tempo.")



    with tab_linha_tempo:
        st.markdown("### Linha do Tempo do Animal")
        eventos = EventoRepository.listar({"animal_sbb": sbb})
        render_timeline(eventos)

if modulo == "Pessoas":
    render_modulo_pessoas()


if modulo == "Financeiro":
    render_modulo_financeiro()

if modulo == "Estoque":
    render_modulo_estoque()

if modulo == "Sanidade":
    render_modulo_sanidade()

if modulo == "Reprodução":
    render_modulo_reproducao()
