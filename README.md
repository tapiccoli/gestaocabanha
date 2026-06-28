# ERP Cabanha - Cadastro por SBB

Versão inicial do cadastro de animais integrado à extração ABCCC.

## Recursos desta versão

- Cadastro de múltiplos SBBs com botão `+ Adicionar SBB`.
- Fila de extração.
- Selenium em modo oculto/headless.
- Banco SQLite local.
- Cadastro completo do animal com seleção por SBB/Nome.
- Abas de visualização:
  - Resumo do Cadastro
  - Principal ABCCC
  - Méritos
  - Padreações
  - Descendentes
  - Irmãos Paternos/Maternos
  - Pedigree
- Estrutura preparada para abrir HTML colorido de 6ª geração por animal.

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Observações

O Chrome/Chromedriver precisam estar instalados e acessíveis no ambiente.
Nesta versão, o processamento da fila é manual pelo botão `Processar fila agora`. Depois pode virar serviço contínuo.
