"""Repository do módulo de Reprodução.

Centraliza temporadas, planejamentos, ciclos/inseminações e diagnósticos.
"""

from database import (
    init_reproducao_db,
    TEMPORADA_STATUS_PADRAO,
    TIPOS_COBERTURA_PADRAO,
    STATUS_REPRODUTIVO_PADRAO,
    TIPOS_DIAGNOSTICO_PADRAO,
    salvar_temporada_reprodutiva,
    listar_temporadas_reprodutivas,
    buscar_temporada_reprodutiva,
    excluir_temporada_reprodutiva,
    salvar_planejamento_reprodutivo,
    listar_planejamentos_reprodutivos,
    buscar_planejamento_reprodutivo,
    excluir_planejamento_reprodutivo,
    salvar_evento_reprodutivo,
    listar_eventos_reprodutivos,
    excluir_evento_reprodutivo,
    matrizes_ativas_reproducao,
    garanhoes_ativos_reproducao,
)


class ReproducaoRepository:
    STATUS_TEMPORADA = TEMPORADA_STATUS_PADRAO
    TIPOS_COBERTURA = TIPOS_COBERTURA_PADRAO
    STATUS_REPRODUTIVO = STATUS_REPRODUTIVO_PADRAO
    TIPOS_DIAGNOSTICO = TIPOS_DIAGNOSTICO_PADRAO

    @staticmethod
    def init():
        return init_reproducao_db()

    @staticmethod
    def salvar_temporada(dados):
        return salvar_temporada_reprodutiva(dados)

    @staticmethod
    def listar_temporadas(incluir_inativas=True):
        return listar_temporadas_reprodutivas(incluir_inativas=incluir_inativas)

    @staticmethod
    def buscar_temporada(temporada_id):
        return buscar_temporada_reprodutiva(temporada_id)

    @staticmethod
    def excluir_temporada(temporada_id):
        return excluir_temporada_reprodutiva(temporada_id)

    @staticmethod
    def salvar_planejamento(dados):
        return salvar_planejamento_reprodutivo(dados)

    @staticmethod
    def listar_planejamentos(filtros=None):
        return listar_planejamentos_reprodutivos(filtros or {})

    @staticmethod
    def buscar_planejamento(planejamento_id):
        return buscar_planejamento_reprodutivo(planejamento_id)

    @staticmethod
    def excluir_planejamento(planejamento_id):
        return excluir_planejamento_reprodutivo(planejamento_id)

    @staticmethod
    def salvar_evento(dados):
        return salvar_evento_reprodutivo(dados)

    @staticmethod
    def listar_eventos(filtros=None):
        return listar_eventos_reprodutivos(filtros or {})

    @staticmethod
    def excluir_evento(evento_id):
        return excluir_evento_reprodutivo(evento_id)

    @staticmethod
    def matrizes_ativas():
        return matrizes_ativas_reproducao()

    @staticmethod
    def garanhoes_ativos():
        return garanhoes_ativos_reproducao()
