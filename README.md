# ERP Cabanha — Cadastro Estrutural

Versão com cadastro de animais, fila de extração ABCCC e organização inicial do ciclo de vida do animal.

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Alterações desta versão

- Adicionado `status_ecossistema` ao animal.
- Animal vendido e entregue deixa de participar da operação, mas permanece para consulta histórica.
- Criadas tabelas:
  - `animal_historico_status`
  - `animal_parcerias`
  - `animal_vendas`
- Criado `repositories/animal_repository.py` para iniciar a separação profissional entre tela e banco.
- Cadastro manual ampliado com status no ecossistema.
- Nova aba **Venda / Parceria** dentro da ficha do animal.
- Nova aba **Histórico** para iniciar a linha do tempo do animal.
- Categoria de idade recalculada usando sexo, castrado e reprodução ativa.

## Regra importante

Animais não devem ser apagados quando vendidos. Eles devem ser marcados como `Vendido e entregue`, saindo dos manejos e custos futuros, mas mantendo histórico.

## v0.3 - Pessoas

Incluído módulo base de Pessoas, com cadastro único para clientes, fornecedores, veterinários, ferradores, treinadores/domadores, funcionários, parceiros, transportadores, leiloeiras, criadores, proprietários e outros papéis.

### Regras implementadas

- Uma pessoa pode ter vários papéis no sistema.
- Exclusão é lógica: a pessoa fica inativa para preservar histórico.
- O cadastro guarda contato, endereço, dados bancários/Pix e observações.
- O módulo já está preparado para ser reutilizado por financeiro, reprodução, sanidade, leilões e animais de terceiros.

### Arquivos principais

- `app.py`
- `database.py`
- `repositories/pessoa_repository.py`

## v0.4 - Financeiro Base

Incluído módulo financeiro inicial com:

- Lançamento de entradas e saídas.
- Pessoa relacionada ao lançamento.
- Centro de custo e atividade.
- Parcelamento automático.
- Rateio global, por animal, por vários animais, por categoria ou por manejo.
- Relatórios com filtros por tipo, centro de custo, atividade, período, status de parcela e busca textual.
- Indicadores de entradas, saídas, saldo previsto, saldo realizado, a pagar e a receber.
- Baixa de parcelas abertas.
- Exclusão lógica de lançamento financeiro.

Arquivos principais desta versão:

- `app.py`
- `database.py`
- `repositories/financeiro_repository.py`

## v0.4.1 - Correção de lançamentos financeiros

- Adicionada edição de lançamentos financeiros.
- Adicionada exclusão lógica com confirmação para lançamentos duplicados ou lançados com erro.
- Ao editar um lançamento, parcelas e rateios são recriados conforme os dados corrigidos.

## v0.45 - Ajuste de rateio financeiro

- Troca de "Global" para "Todos os Animais".
- Campo "Aplicar custo/receita para" fora do formulário, permitindo que a tela abra dinamicamente os campos corretos antes de salvar.
- Seleção de animal específico e vários animais corrigida.
- Validação para impedir salvar rateio sem animal, categoria ou manejo quando obrigatório.
- Edição de lançamento também passa a usar "Todos os Animais".

## v0.5.1 - Entrada de estoque com ou sem nota fiscal

- Na aba Estoque > Movimentações, o usuário escolhe se a entrada/saída possui nota fiscal.
- Com nota fiscal: importa XML de NF-e, lê fornecedor, número, série, data de emissão, valor total e itens.
- Cada item do XML pode ser vinculado a um produto existente, cadastrado como produto novo ou ignorado.
- Sem nota fiscal: mantém o lançamento manual como antes.
- A confirmação da NF gera movimentações de entrada para os itens confirmados.

## v0.5.2 - Estoque / XML NF-e e padronização de custos

- Importação de XML NF-e movida para a aba **Insumos e Cadastros**.
- Dados da NF podem ser conferidos e alterados antes de gravar.
- Centro de custo e atividade agora são selecionados por listas padronizadas.
- Categoria animal e manejo deixaram de ser campos livres nas telas de rateio/destino.
- Movimentações de estoque passaram a armazenar centro de custo e atividade.

## v0.6 — Sanidade e Farmácia

Incluído módulo de Sanidade e Farmácia com:

- Registro de vacinas, vermífugos, medicações, exames, procedimentos e atendimentos veterinários.
- Aplicação para animal específico, vários animais, categoria, manejo ou todos os animais.
- Produto do estoque, princípio ativo, nome comercial, lote, via de aplicação e próxima dose.
- Responsável/veterinário usando o cadastro de Pessoas.
- Baixa automática opcional do estoque.
- Lançamento financeiro automático opcional com rateio por animal.
- Histórico sanitário com filtros.
- Exclusão lógica de eventos lançados por engano.
- Alertas de próximas doses/reforços.

## v0.6.1 - Estoque fracionado por unidade de consumo

Ajustes realizados:
- Produtos agora têm unidade de compra e unidade de consumo/controle.
- Produto pode informar quantas unidades de consumo existem em cada unidade comprada.
  - Exemplo: 1 frasco = 50 mL.
  - Exemplo: 1 saco = 40 kg.
- Na importação XML da NF-e, o sistema converte automaticamente a quantidade comprada para quantidade real de estoque.
- O custo unitário passa a ser calculado pela unidade de consumo.
- Movimentações sem nota passam a informar quantidade na unidade de consumo/controle.

## v0.6.2 - XML NF-e item a item

A importação de XML da NF-e foi ajustada para tratar cada item da nota individualmente:

- cada produto da NF pode ser vinculado ou cadastrado separadamente;
- cada item possui seu próprio centro de custo;
- cada item possui sua própria atividade;
- cada item possui seu próprio destino/rateio: animal específico, categoria, manejo ou todos os animais;
- a nota continua sendo o documento pai, mas o custo/estoque é classificado por item.

## v0.6.3 — Infraestrutura de Componentes e Eventos

Esta versão inicia a infraestrutura reutilizável do ERP.

### Novos componentes

- `components/entity_selector.py`
  - Base para seleção contextual no padrão: selecionar, consultar e cadastrar rápido.
  - Inclui cadastro rápido de Pessoas e Produtos/Insumos.

- `components/event_timeline.py`
  - Componente inicial para exibir a linha do tempo do animal.

- `components/tabela_padrao.py`
  - Primeira versão de tabela padronizada para uso futuro.

### Nova entidade técnica

- `eventos_gerais`
  - Tabela base para linha do tempo.
  - Qualquer módulo poderá registrar eventos nela.

### Integração inicial

- Eventos de Sanidade agora também alimentam a Linha do Tempo do Animal.
- A tela de Sanidade ganhou área de cadastro rápido contextual para nova pessoa/responsável e novo produto/insumo.

Observação: os formulários antigos ainda usam `st.form`. Como o Streamlit não permite botões comuns dentro de `st.form`, a implantação completa do botão `+` ao lado de cada campo será feita gradualmente conforme as telas forem refatoradas para o novo padrão de componentes.

## v0.6.4 - Cadastro contextual via primeira opção da lista

Ajustes de usabilidade:
- O padrão de cadastro rápido foi alterado para ficar dentro da própria lista do campo.
- A primeira opção agora é `➕ Cadastrar novo...`.
- Ao selecionar essa opção, o cadastro rápido aparece imediatamente no local do campo.
- Aplicado inicialmente no módulo de Sanidade para:
  - Produto do estoque
  - Veterinário / responsável
- O formulário de Sanidade foi ajustado para funcionar fora de `st.form`, permitindo a reação imediata da tela ao selecionar `➕ Cadastrar novo...`.

Esse padrão será replicado gradualmente para os demais formulários do ERP.

## v0.7 — Reprodução

Incluído módulo inicial de Reprodução com:

- Temporadas reprodutivas.
- Planejamento de matrizes x garanhões.
- Tipo de cobertura: monta natural, sêmen fresco, sêmen congelado e transferência de embrião.
- Execução do ciclo: inseminação/cobertura, diagnóstico, parto, falha/repetição e outros eventos.
- Status reprodutivo da matriz no planejamento.
- Diagnóstico positivo altera o status do planejamento para Prenha.
- Eventos reprodutivos alimentam a linha do tempo do animal.
- Relatórios iniciais de planejamentos, eventos, matrizes e garanhões ativos.

## v0.7.1 - Correção de navegação
- O menu principal foi movido para a barra lateral.
- Todos os módulos anteriores continuam disponíveis: Cadastrar por SBB, Fila, Cadastro Completo, Pessoas, Financeiro, Estoque, Sanidade e Reprodução.
- A mudança evita que módulos fiquem ocultos quando há muitos tabs na parte superior da tela.
