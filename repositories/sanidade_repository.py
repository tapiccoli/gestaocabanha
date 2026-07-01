"""Repository de Sanidade e Farmácia."""

from database import (
    TIPOS_SANIDADE_PADRAO,
    VIAS_APLICACAO_PADRAO,
    PROTOCOLOS_SANIDADE_PADRAO,
    salvar_evento_sanidade,
    listar_eventos_sanidade,
    buscar_evento_sanidade,
    excluir_evento_sanidade,
    alertas_sanidade,
    atualizar_integracoes_sanidade,
)


class SanidadeRepository:
    TIPOS = TIPOS_SANIDADE_PADRAO
    VIAS = VIAS_APLICACAO_PADRAO
    PROTOCOLOS = PROTOCOLOS_SANIDADE_PADRAO

    @staticmethod
    def salvar_evento(dados, animais):
        return salvar_evento_sanidade(dados, animais)

    @staticmethod
    def listar_eventos(filtros=None):
        return listar_eventos_sanidade(filtros or {})

    @staticmethod
    def buscar_evento(evento_id):
        return buscar_evento_sanidade(evento_id)

    @staticmethod
    def excluir_evento(evento_id):
        return excluir_evento_sanidade(evento_id)

    @staticmethod
    def alertas(dias=30):
        return alertas_sanidade(dias=dias)

    @staticmethod
    def atualizar_integracoes(evento_id, lancamento_financeiro_id=None, movimentacao_estoque_id=None):
        return atualizar_integracoes_sanidade(evento_id, lancamento_financeiro_id, movimentacao_estoque_id)
