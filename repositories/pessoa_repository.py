"""Repository de Pessoas.

Centraliza o acesso ao banco para clientes, fornecedores, veterinários,
ferradores, treinadores, funcionários, parceiros, leiloeiras e demais contatos.
"""

from database import (
    PAPEIS_PADRAO,
    salvar_pessoa,
    listar_pessoas,
    buscar_pessoa,
    excluir_pessoa,
    reativar_pessoa,
)


class PessoaRepository:
    PAPEIS = PAPEIS_PADRAO

    @staticmethod
    def salvar(dados, papeis):
        return salvar_pessoa(dados, papeis)

    @staticmethod
    def listar(incluir_inativos=False, busca="", papel=""):
        return listar_pessoas(incluir_inativos=incluir_inativos, busca=busca, papel=papel)

    @staticmethod
    def buscar(pessoa_id):
        return buscar_pessoa(pessoa_id)

    @staticmethod
    def excluir(pessoa_id):
        return excluir_pessoa(pessoa_id)

    @staticmethod
    def reativar(pessoa_id):
        return reativar_pessoa(pessoa_id)
