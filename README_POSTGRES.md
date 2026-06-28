# Configuração PostgreSQL

O sistema agora usa SQLAlchemy e aceita PostgreSQL via `DATABASE_URL`.

## Local

Crie uma variável de ambiente:

```bash
set DATABASE_URL=postgresql+psycopg2://usuario:senha@localhost:5432/cabanha_erp
streamlit run app.py
```

Sem `DATABASE_URL`, o sistema usa SQLite local como fallback.

## Streamlit Cloud

Em **Settings > Secrets**, cadastre:

```toml
DATABASE_URL = "postgresql+psycopg2://usuario:senha@host:5432/nome_do_banco"
```

Depois faça redeploy.
