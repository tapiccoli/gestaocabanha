"""Repository do Financeiro.

Mantém a tela desacoplada das funções de banco.
"""

from database import (
    CENTROS_CUSTO_PADRAO,
    ATIVIDADES_PADRAO,
    FORMAS_PAGAMENTO_PADRAO,
    STATUS_PARCELA_PADRAO,
    salvar_lancamento_financeiro,
    atualizar_lancamento_financeiro,
    listar_lancamentos_financeiros,
    buscar_lancamento_financeiro,
    excluir_lancamento_financeiro,
    pagar_parcela_financeira,
    listar_parcelas_financeiras,
    listar_rateios_financeiros,
    indicadores_financeiros,
)


class FinanceiroRepository:
    CENTROS_CUSTO = CENTROS_CUSTO_PADRAO
    ATIVIDADES = ATIVIDADES_PADRAO
    FORMAS_PAGAMENTO = FORMAS_PAGAMENTO_PADRAO
    STATUS_PARCELA = STATUS_PARCELA_PADRAO

    @staticmethod
    def salvar_lancamento(dados, parcelas, rateios):
        return salvar_lancamento_financeiro(dados, parcelas, rateios)

    @staticmethod
    def atualizar_lancamento(lancamento_id, dados, parcelas, rateios):
        return atualizar_lancamento_financeiro(lancamento_id, dados, parcelas, rateios)

    @staticmethod
    def listar_lancamentos(filtros=None):
        return listar_lancamentos_financeiros(filtros or {})

    @staticmethod
    def buscar_lancamento(lancamento_id):
        return buscar_lancamento_financeiro(lancamento_id)

    @staticmethod
    def excluir_lancamento(lancamento_id):
        return excluir_lancamento_financeiro(lancamento_id)

    @staticmethod
    def pagar_parcela(parcela_id, data_pagamento, valor_pago=None):
        return pagar_parcela_financeira(parcela_id, data_pagamento, valor_pago)

    @staticmethod
    def listar_parcelas(lancamento_id=None, filtros=None):
        return listar_parcelas_financeiras(lancamento_id=lancamento_id, filtros=filtros or {})

    @staticmethod
    def listar_rateios(lancamento_id):
        return listar_rateios_financeiros(lancamento_id)

    @staticmethod
    def indicadores(filtros=None):
        return indicadores_financeiros(filtros or {})
