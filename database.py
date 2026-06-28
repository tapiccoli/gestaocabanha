import sqlite3
import json
from pathlib import Path
from datetime import datetime, date

DB_PATH = Path(__file__).parent / "cabanha_erp.sqlite3"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


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


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS animais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS extracoes_fila (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sbb TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Em fila',
        etapa TEXT,
        erro TEXT,
        criado_em TEXT,
        iniciado_em TEXT,
        finalizado_em TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS abccc_principal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_sbb TEXT NOT NULL,
        dados_json TEXT NOT NULL,
        url TEXT,
        extraido_em TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS abccc_blocos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_sbb TEXT NOT NULL,
        tipo TEXT NOT NULL,
        dados_json TEXT NOT NULL,
        url TEXT,
        extraido_em TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS animal_pedigree (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_sbb TEXT NOT NULL,
        numero_item INTEGER,
        bloco TEXT,
        nome TEXT,
        sbb TEXT,
        pelagem TEXT,
        texto_completo TEXT,
        extraido_em TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pedigree_html (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_sbb TEXT NOT NULL,
        geracao INTEGER NOT NULL,
        html TEXT NOT NULL,
        criado_em TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS financeiro_lancamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origem_modulo TEXT,
        animal_sbb TEXT,
        motivo TEXT,
        fornecedor TEXT,
        valor REAL,
        data_lancamento TEXT,
        observacao TEXT,
        criado_em TEXT
    )
    """)

    conn.commit()
    conn.close()


def inserir_fila(sbb: str):
    sbb = sbb.strip().upper()
    if not sbb:
        return
    conn = get_conn()
    existe_aberta = conn.execute(
        "SELECT id FROM extracoes_fila WHERE sbb=? AND status IN ('Em fila', 'Processando')",
        (sbb,),
    ).fetchone()
    if not existe_aberta:
        conn.execute(
            "INSERT INTO extracoes_fila (sbb, status, etapa, criado_em) VALUES (?, 'Em fila', 'Aguardando processamento', ?)",
            (sbb, now_br()),
        )
    conn.commit()
    conn.close()


def listar_fila(limit=100):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM extracoes_fila ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def atualizar_fila(fila_id, status=None, etapa=None, erro=None, iniciado=False, finalizado=False):
    campos, vals = [], []
    if status is not None:
        campos.append("status=?"); vals.append(status)
    if etapa is not None:
        campos.append("etapa=?"); vals.append(etapa)
    if erro is not None:
        campos.append("erro=?"); vals.append(erro)
    if iniciado:
        campos.append("iniciado_em=?"); vals.append(now_br())
    if finalizado:
        campos.append("finalizado_em=?"); vals.append(now_br())
    if not campos:
        return
    vals.append(fila_id)
    conn = get_conn()
    conn.execute(f"UPDATE extracoes_fila SET {', '.join(campos)} WHERE id=?", vals)
    conn.commit(); conn.close()


def buscar_pendentes():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM extracoes_fila WHERE status='Em fila' ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def salvar_principal(sbb, dados):
    conn = get_conn()
    url = dados.get("URL", "")
    apto = 0
    idade_txt, categoria = calcular_idade_categoria(dados.get("Nascimento"), apto, dados.get("Sexo"))
    conn.execute("DELETE FROM abccc_principal WHERE animal_sbb=?", (sbb,))
    conn.execute(
        "INSERT INTO abccc_principal (animal_sbb, dados_json, url, extraido_em) VALUES (?, ?, ?, ?)",
        (sbb, json.dumps(dados, ensure_ascii=False), url, now_br()),
    )
    conn.execute("""
        INSERT INTO animais (sbb, nome, rp, sexo, nascimento, pelagem, status, situacao, pai_sbb, pai_nome, mae_sbb, mae_nome, apto_reproducao, categoria_idade, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(sbb) DO UPDATE SET
            nome=excluded.nome, rp=excluded.rp, sexo=excluded.sexo, nascimento=excluded.nascimento,
            pelagem=excluded.pelagem, status=excluded.status, situacao=excluded.situacao,
            pai_sbb=excluded.pai_sbb, pai_nome=excluded.pai_nome, mae_sbb=excluded.mae_sbb, mae_nome=excluded.mae_nome,
            categoria_idade=excluded.categoria_idade, atualizado_em=excluded.atualizado_em
    """, (
        sbb, dados.get("Nome"), dados.get("RP"), dados.get("Sexo"), dados.get("Nascimento"), dados.get("Pelagem"),
        dados.get("Status"), dados.get("Situacao"), dados.get("Pai_SBB"), dados.get("Pai_Nome"), dados.get("Mae_SBB"), dados.get("Mae_Nome"),
        apto, categoria, now_br(), now_br()
    ))
    conn.commit(); conn.close()


def salvar_bloco(sbb, tipo, dados):
    conn = get_conn()
    conn.execute("DELETE FROM abccc_blocos WHERE animal_sbb=? AND tipo=?", (sbb, tipo))
    conn.execute(
        "INSERT INTO abccc_blocos (animal_sbb, tipo, dados_json, url, extraido_em) VALUES (?, ?, ?, ?, ?)",
        (sbb, tipo, json.dumps(dados, ensure_ascii=False), dados.get("URL", ""), now_br()),
    )
    conn.commit(); conn.close()


def salvar_pedigree(sbb, itens):
    conn = get_conn()
    conn.execute("DELETE FROM animal_pedigree WHERE animal_sbb=?", (sbb,))
    for item in itens:
        conn.execute("""
            INSERT INTO animal_pedigree (animal_sbb, numero_item, bloco, nome, sbb, pelagem, texto_completo, extraido_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (sbb, item.get("numero_item"), item.get("bloco"), item.get("nome"), item.get("sbb"), item.get("pelagem"), item.get("texto_completo"), now_br()))
    conn.commit(); conn.close()


def listar_animais():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM animais ORDER BY nome, sbb").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_animal(sbb):
    conn = get_conn()
    row = conn.execute("SELECT * FROM animais WHERE sbb=?", (sbb,)).fetchone()
    conn.close()
    if not row:
        return None
    animal = dict(row)
    idade, categoria = calcular_idade_categoria(animal.get("nascimento"), animal.get("apto_reproducao"), animal.get("sexo"))
    animal["idade_calculada"] = idade
    animal["categoria_calculada"] = categoria
    return animal


def buscar_principal_json(sbb):
    conn = get_conn()
    row = conn.execute("SELECT * FROM abccc_principal WHERE animal_sbb=? ORDER BY id DESC LIMIT 1", (sbb,)).fetchone()
    conn.close()
    if not row:
        return {}
    return json.loads(row["dados_json"])


def buscar_blocos_json(sbb):
    conn = get_conn()
    rows = conn.execute("SELECT tipo, dados_json FROM abccc_blocos WHERE animal_sbb=?", (sbb,)).fetchall()
    conn.close()
    return {r["tipo"]: json.loads(r["dados_json"]) for r in rows}


def buscar_pedigree(sbb):
    conn = get_conn()
    rows = conn.execute("SELECT numero_item, bloco, nome, sbb, pelagem, texto_completo FROM animal_pedigree WHERE animal_sbb=? ORDER BY numero_item", (sbb,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def atualizar_campos_cadastro(sbb, classificacao, manejo, apto_reproducao, origem, valor_aquisicao):
    animal = buscar_animal(sbb) or {}
    _, categoria = calcular_idade_categoria(animal.get("nascimento"), apto_reproducao, animal.get("sexo"))
    conn = get_conn()
    conn.execute("""
        UPDATE animais
        SET classificacao=?, manejo=?, apto_reproducao=?, origem=?, valor_aquisicao=?, categoria_idade=?, atualizado_em=?
        WHERE sbb=?
    """, (classificacao, manejo, int(bool(apto_reproducao)), origem, float(valor_aquisicao or 0), categoria, now_br(), sbb))
    conn.commit(); conn.close()
