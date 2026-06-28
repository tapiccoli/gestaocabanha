import os
import json
from pathlib import Path
from datetime import datetime, date

from sqlalchemy import create_engine, text

try:
    import streamlit as st
except Exception:
    st = None

DB_SQLITE_PATH = Path(__file__).parent / "cabanha_erp.sqlite3"


def _get_database_url():
    """
    Prioridade:
    1) variável de ambiente DATABASE_URL
    2) st.secrets["DATABASE_URL"] no Streamlit Cloud
    3) SQLite local como fallback para desenvolvimento
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    if st is not None:
        try:
            if "DATABASE_URL" in st.secrets:
                return st.secrets["DATABASE_URL"]
        except Exception:
            pass

    return f"sqlite:///{DB_SQLITE_PATH}"


DATABASE_URL = _get_database_url()

# Render/Heroku às vezes entregam postgres://, SQLAlchemy prefere postgresql+psycopg2://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


def db_backend():
    return engine.url.get_backend_name()


def _id_pk_sql():
    if db_backend().startswith("postgresql"):
        return "SERIAL PRIMARY KEY"
    return "INTEGER PRIMARY KEY AUTOINCREMENT"


def now_br():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def parse_data_br(valor):
    if not valor or valor in ["xxxx", "xxx", "None"]:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(str(valor).strip(), fmt).date()
        except ValueError:
            pass
    return None


def calcular_idade_categoria(nascimento, apto_reproducao=0, sexo=""):
    nasc = parse_data_br(nascimento)
    if not nasc:
        return "Não informado", ""
    hoje = date.today()
    meses = (hoje.year - nasc.year) * 12 + (hoje.month - nasc.month)
    if hoje.day < nasc.day:
        meses -= 1
    anos = meses // 12
    meses_restantes = meses % 12
    idade_txt = f"{anos} ano(s) e {meses_restantes} mês(es)"
    sexo = (sexo or "").upper()
    if meses <= 6:
        categoria = "Potro ao pé"
    elif 7 <= meses < 12:
        categoria = "Desmamado"
    elif 12 <= meses < 24:
        categoria = "Sobreano"
    elif 24 <= meses < 36:
        if int(apto_reproducao or 0):
            categoria = "Garanhão" if sexo.startswith("M") else "Égua de Cria"
        else:
            categoria = "Jovens"
    else:
        categoria = "Adultos"
    return idade_txt, categoria


def _fetch_all(sql, params=None):
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params or {}).mappings().all()
        return [dict(r) for r in rows]


def _fetch_one(sql, params=None):
    with engine.begin() as conn:
        row = conn.execute(text(sql), params or {}).mappings().first()
        return dict(row) if row else None


def _execute(sql, params=None):
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        return result.rowcount or 0


def init_db():
    pk = _id_pk_sql()
    with engine.begin() as conn:
        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS animais (
            id {pk},
            sbb TEXT UNIQUE NOT NULL,
            nome TEXT,
            rp TEXT,
            sexo TEXT,
            nascimento TEXT,
            pelagem TEXT,
            status TEXT,
            situacao TEXT,
            pai_sbb TEXT,
            pai_nome TEXT,
            mae_sbb TEXT,
            mae_nome TEXT,
            classificacao TEXT,
            manejo TEXT,
            apto_reproducao INTEGER DEFAULT 0,
            categoria_idade TEXT,
            origem TEXT,
            valor_aquisicao REAL DEFAULT 0,
            criado_em TEXT,
            atualizado_em TEXT
        )
        """))

        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS extracoes_fila (
            id {pk},
            sbb TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Em fila',
            etapa TEXT,
            erro TEXT,
            criado_em TEXT,
            iniciado_em TEXT,
            finalizado_em TEXT
        )
        """))

        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS abccc_principal (
            id {pk},
            animal_sbb TEXT NOT NULL,
            dados_json TEXT NOT NULL,
            url TEXT,
            extraido_em TEXT
        )
        """))

        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS abccc_blocos (
            id {pk},
            animal_sbb TEXT NOT NULL,
            tipo TEXT NOT NULL,
            dados_json TEXT NOT NULL,
            url TEXT,
            extraido_em TEXT
        )
        """))

        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS animal_pedigree (
            id {pk},
            animal_sbb TEXT NOT NULL,
            numero_item INTEGER,
            bloco TEXT,
            nome TEXT,
            sbb TEXT,
            pelagem TEXT,
            texto_completo TEXT,
            extraido_em TEXT
        )
        """))

        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS pedigree_html (
            id {pk},
            animal_sbb TEXT NOT NULL,
            geracao INTEGER NOT NULL,
            html TEXT NOT NULL,
            criado_em TEXT
        )
        """))

        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS financeiro_lancamentos (
            id {pk},
            origem_modulo TEXT,
            animal_sbb TEXT,
            motivo TEXT,
            fornecedor TEXT,
            valor REAL,
            data_lancamento TEXT,
            observacao TEXT,
            criado_em TEXT
        )
        """))


def inserir_fila(sbb: str):
    sbb = sbb.strip().upper()
    if not sbb:
        return
    existe = _fetch_one(
        "SELECT id FROM extracoes_fila WHERE sbb=:sbb AND status IN ('Em fila', 'Processando')",
        {"sbb": sbb},
    )
    if not existe:
        _execute(
            """
            INSERT INTO extracoes_fila (sbb, status, etapa, criado_em)
            VALUES (:sbb, 'Em fila', 'Aguardando processamento', :criado_em)
            """,
            {"sbb": sbb, "criado_em": now_br()},
        )


def listar_fila(limit=100):
    return _fetch_all("SELECT * FROM extracoes_fila ORDER BY id DESC LIMIT :limit", {"limit": limit})


def excluir_item_fila(fila_id):
    row = _fetch_one("SELECT status FROM extracoes_fila WHERE id=:id", {"id": fila_id})
    if not row:
        return False, "Item não encontrado."
    if row["status"] == "Processando":
        return False, "Não é possível excluir um item em processamento."
    _execute("DELETE FROM extracoes_fila WHERE id=:id", {"id": fila_id})
    return True, "Item excluído da fila."


def limpar_fila_por_status(statuses):
    permitidos = {"Em fila", "Erro", "Finalizado"}
    statuses = [s for s in (statuses or []) if s in permitidos]
    if not statuses:
        return 0
    total = 0
    for status in statuses:
        total += _execute("DELETE FROM extracoes_fila WHERE status=:status", {"status": status})
    return total


def atualizar_fila(fila_id, status=None, etapa=None, erro=None, iniciado=False, finalizado=False):
    campos = []
    params = {"id": fila_id}
    if status is not None:
        campos.append("status=:status"); params["status"] = status
    if etapa is not None:
        campos.append("etapa=:etapa"); params["etapa"] = etapa
    if erro is not None:
        campos.append("erro=:erro"); params["erro"] = erro
    if iniciado:
        campos.append("iniciado_em=:iniciado_em"); params["iniciado_em"] = now_br()
    if finalizado:
        campos.append("finalizado_em=:finalizado_em"); params["finalizado_em"] = now_br()
    if campos:
        _execute(f"UPDATE extracoes_fila SET {', '.join(campos)} WHERE id=:id", params)


def buscar_pendentes():
    return _fetch_all("SELECT * FROM extracoes_fila WHERE status='Em fila' ORDER BY id ASC")


def salvar_principal(sbb, dados):
    url = dados.get("URL", "")
    apto = 0
    _, categoria = calcular_idade_categoria(dados.get("Nascimento"), apto, dados.get("Sexo"))

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM abccc_principal WHERE animal_sbb=:sbb"), {"sbb": sbb})
        conn.execute(text("""
            INSERT INTO abccc_principal (animal_sbb, dados_json, url, extraido_em)
            VALUES (:sbb, :dados_json, :url, :extraido_em)
        """), {
            "sbb": sbb,
            "dados_json": json.dumps(dados, ensure_ascii=False),
            "url": url,
            "extraido_em": now_br(),
        })

        conn.execute(text("""
            INSERT INTO animais (
                sbb, nome, rp, sexo, nascimento, pelagem, status, situacao,
                pai_sbb, pai_nome, mae_sbb, mae_nome, apto_reproducao,
                categoria_idade, criado_em, atualizado_em
            )
            VALUES (
                :sbb, :nome, :rp, :sexo, :nascimento, :pelagem, :status, :situacao,
                :pai_sbb, :pai_nome, :mae_sbb, :mae_nome, :apto_reproducao,
                :categoria_idade, :criado_em, :atualizado_em
            )
            ON CONFLICT(sbb) DO UPDATE SET
                nome=excluded.nome,
                rp=excluded.rp,
                sexo=excluded.sexo,
                nascimento=excluded.nascimento,
                pelagem=excluded.pelagem,
                status=excluded.status,
                situacao=excluded.situacao,
                pai_sbb=excluded.pai_sbb,
                pai_nome=excluded.pai_nome,
                mae_sbb=excluded.mae_sbb,
                mae_nome=excluded.mae_nome,
                categoria_idade=excluded.categoria_idade,
                atualizado_em=excluded.atualizado_em
        """), {
            "sbb": sbb,
            "nome": dados.get("Nome"),
            "rp": dados.get("RP"),
            "sexo": dados.get("Sexo"),
            "nascimento": dados.get("Nascimento"),
            "pelagem": dados.get("Pelagem"),
            "status": dados.get("Status"),
            "situacao": dados.get("Situacao"),
            "pai_sbb": dados.get("Pai_SBB"),
            "pai_nome": dados.get("Pai_Nome"),
            "mae_sbb": dados.get("Mae_SBB"),
            "mae_nome": dados.get("Mae_Nome"),
            "apto_reproducao": apto,
            "categoria_idade": categoria,
            "criado_em": now_br(),
            "atualizado_em": now_br(),
        })


def salvar_bloco(sbb, tipo, dados):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM abccc_blocos WHERE animal_sbb=:sbb AND tipo=:tipo"), {"sbb": sbb, "tipo": tipo})
        conn.execute(text("""
            INSERT INTO abccc_blocos (animal_sbb, tipo, dados_json, url, extraido_em)
            VALUES (:sbb, :tipo, :dados_json, :url, :extraido_em)
        """), {
            "sbb": sbb,
            "tipo": tipo,
            "dados_json": json.dumps(dados, ensure_ascii=False),
            "url": dados.get("URL", ""),
            "extraido_em": now_br(),
        })


def salvar_pedigree(sbb, itens):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM animal_pedigree WHERE animal_sbb=:sbb"), {"sbb": sbb})
        for item in itens:
            conn.execute(text("""
                INSERT INTO animal_pedigree (
                    animal_sbb, numero_item, bloco, nome, sbb, pelagem, texto_completo, extraido_em
                ) VALUES (
                    :animal_sbb, :numero_item, :bloco, :nome, :sbb_item, :pelagem, :texto_completo, :extraido_em
                )
            """), {
                "animal_sbb": sbb,
                "numero_item": item.get("numero_item"),
                "bloco": item.get("bloco"),
                "nome": item.get("nome"),
                "sbb_item": item.get("sbb"),
                "pelagem": item.get("pelagem"),
                "texto_completo": item.get("texto_completo"),
                "extraido_em": now_br(),
            })


def listar_animais():
    return _fetch_all("SELECT * FROM animais ORDER BY nome, sbb")


def buscar_animal(sbb):
    animal = _fetch_one("SELECT * FROM animais WHERE sbb=:sbb", {"sbb": sbb})
    if not animal:
        return None
    idade, categoria = calcular_idade_categoria(animal.get("nascimento"), animal.get("apto_reproducao"), animal.get("sexo"))
    animal["idade_calculada"] = idade
    animal["categoria_calculada"] = categoria
    return animal


def buscar_principal_json(sbb):
    row = _fetch_one(
        "SELECT * FROM abccc_principal WHERE animal_sbb=:sbb ORDER BY id DESC LIMIT 1",
        {"sbb": sbb},
    )
    return json.loads(row["dados_json"]) if row else {}


def buscar_blocos_json(sbb):
    rows = _fetch_all("SELECT tipo, dados_json FROM abccc_blocos WHERE animal_sbb=:sbb", {"sbb": sbb})
    return {r["tipo"]: json.loads(r["dados_json"]) for r in rows}


def buscar_pedigree(sbb):
    return _fetch_all(
        """
        SELECT numero_item, bloco, nome, sbb, pelagem, texto_completo
        FROM animal_pedigree
        WHERE animal_sbb=:sbb
        ORDER BY numero_item
        """,
        {"sbb": sbb},
    )


def atualizar_campos_cadastro(sbb, classificacao, manejo, apto_reproducao, origem, valor_aquisicao):
    animal = buscar_animal(sbb) or {}
    _, categoria = calcular_idade_categoria(animal.get("nascimento"), apto_reproducao, animal.get("sexo"))
    _execute("""
        UPDATE animais
        SET classificacao=:classificacao,
            manejo=:manejo,
            apto_reproducao=:apto_reproducao,
            origem=:origem,
            valor_aquisicao=:valor_aquisicao,
            categoria_idade=:categoria_idade,
            atualizado_em=:atualizado_em
        WHERE sbb=:sbb
    """, {
        "classificacao": classificacao,
        "manejo": manejo,
        "apto_reproducao": int(bool(apto_reproducao)),
        "origem": origem,
        "valor_aquisicao": float(valor_aquisicao or 0),
        "categoria_idade": categoria,
        "atualizado_em": now_br(),
        "sbb": sbb,
    })
