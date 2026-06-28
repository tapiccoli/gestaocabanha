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
