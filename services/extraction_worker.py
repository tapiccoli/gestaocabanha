from database import buscar_pendentes, atualizar_fila, salvar_principal, salvar_bloco, salvar_pedigree
from services.abccc_animal_service import iniciar_driver, extrair_todos_dados_animal
from services.abccc_pedigree_service import extrair_pedigree_completo


def processar_fila(headless=True, limite=None):
    pendentes = buscar_pendentes()
    if limite:
        pendentes = pendentes[:limite]
    if not pendentes:
        return 0

    driver = iniciar_driver(headless=headless)
    processados = 0
    try:
        for item in pendentes:
            fila_id = item["id"]
            sbb = item["sbb"].strip().upper()
            try:
                atualizar_fila(fila_id, status="Processando", etapa="Extraindo dados ABCCC", iniciado=True)
                principal, blocos = extrair_todos_dados_animal(driver, sbb)
                salvar_principal(sbb, principal)
                for tipo, dados in blocos.items():
                    salvar_bloco(sbb, tipo, dados)

                atualizar_fila(fila_id, etapa="Extraindo pedigree 5ª geração")
                pedigree = extrair_pedigree_completo(driver, sbb)
                salvar_pedigree(sbb, pedigree)

                atualizar_fila(fila_id, status="Finalizado", etapa="Concluído", finalizado=True)
                processados += 1
            except Exception as e:
                atualizar_fila(fila_id, status="Erro", etapa="Falha na extração", erro=str(e), finalizado=True)
    finally:
        driver.quit()
    return processados
