"""Repository de Eventos Gerais.

O objetivo é formar a linha do tempo do animal e permitir que qualquer módulo
registre 'o que aconteceu' sem duplicar lógica.
"""

from database import (
    init_eventos_db,
    registrar_evento_geral,
    listar_eventos_gerais,
    excluir_evento_geral,
)


class EventoRepository:
    @staticmethod
    def init():
        return init_eventos_db()

    @staticmethod
    def registrar(dados):
        return registrar_evento_geral(dados)

    @staticmethod
    def listar(filtros=None):
        return listar_eventos_gerais(filtros or {})

    @staticmethod
    def excluir(evento_id):
        return excluir_evento_geral(evento_id)
