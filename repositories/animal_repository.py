"""Camada de acesso aos dados do animal.

A tela Streamlit deve conversar com este arquivo em vez de espalhar SQL pelo app.
Neste primeiro momento ele encapsula funções já existentes em database.py.
No futuro, se migrarmos para PostgreSQL/SQLAlchemy, a tela muda pouco ou nada.
"""

from database import (
    listar_animais,
    buscar_animal,
    buscar_principal_json,
    buscar_blocos_json,
    buscar_pedigree,
    atualizar_campos_cadastro,
    listar_historico_status,
    salvar_venda_animal,
    listar_vendas_animal,
    salvar_parceria_animal,
    listar_parcerias_animal,
)


class AnimalRepository:
    @staticmethod
    def listar(incluir_inativos=True):
        return listar_animais(incluir_inativos=incluir_inativos)

    @staticmethod
    def buscar(sbb):
        return buscar_animal(sbb)

    @staticmethod
    def buscar_principal(sbb):
        return buscar_principal_json(sbb)

    @staticmethod
    def buscar_blocos(sbb):
        return buscar_blocos_json(sbb)

    @staticmethod
    def buscar_pedigree(sbb):
        return buscar_pedigree(sbb)

    @staticmethod
    def atualizar_cadastro(**kwargs):
        return atualizar_campos_cadastro(**kwargs)

    @staticmethod
    def historico_status(sbb):
        return listar_historico_status(sbb)

    @staticmethod
    def salvar_venda(**kwargs):
        return salvar_venda_animal(**kwargs)

    @staticmethod
    def vendas(sbb):
        return listar_vendas_animal(sbb)

    @staticmethod
    def salvar_parceria(**kwargs):
        return salvar_parceria_animal(**kwargs)

    @staticmethod
    def parcerias(sbb):
        return listar_parcerias_animal(sbb)
