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
