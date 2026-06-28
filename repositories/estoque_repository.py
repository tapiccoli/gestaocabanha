"""Repository de Estoque.

Centraliza cadastro de produtos/insumos e movimentações de entrada, consumo e ajuste.
"""

from database import (
    CATEGORIAS_ESTOQUE_PADRAO,
    UNIDADES_ESTOQUE_PADRAO,
    TIPOS_MOV_ESTOQUE,
    salvar_produto_estoque,
    listar_produtos_estoque,
    buscar_produto_estoque,
    excluir_produto_estoque,
    salvar_movimentacao_estoque,
    listar_movimentacoes_estoque,
    excluir_movimentacao_estoque,
    saldo_estoque_produtos,
)


class EstoqueRepository:
    CATEGORIAS = CATEGORIAS_ESTOQUE_PADRAO
    UNIDADES = UNIDADES_ESTOQUE_PADRAO
    TIPOS_MOVIMENTO = TIPOS_MOV_ESTOQUE

    @staticmethod
    def salvar_produto(dados):
        return salvar_produto_estoque(dados)

    @staticmethod
    def listar_produtos(incluir_inativos=False, busca="", categoria=""):
        return listar_produtos_estoque(incluir_inativos=incluir_inativos, busca=busca, categoria=categoria)

    @staticmethod
    def buscar_produto(produto_id):
        return buscar_produto_estoque(produto_id)

    @staticmethod
    def excluir_produto(produto_id):
        return excluir_produto_estoque(produto_id)

    @staticmethod
    def salvar_movimentacao(dados):
        return salvar_movimentacao_estoque(dados)

    @staticmethod
    def listar_movimentacoes(filtros=None):
        return listar_movimentacoes_estoque(filtros or {})

    @staticmethod
    def excluir_movimentacao(mov_id):
        return excluir_movimentacao_estoque(mov_id)

    @staticmethod
    def saldos():
        return saldo_estoque_produtos()
