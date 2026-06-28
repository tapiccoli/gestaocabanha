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


def calcular_idade_categoria(nascimento, apto_reproducao=0, sexo="", castrado=0):
    """Calcula idade em texto e categoria zootécnica automática.

    Regra definida no projeto:
    - Potro(a) ao pé: até 6 meses
    - Potro(a) Desmamado(a): 7 a 12 meses
    - Potro(a) Sobreano: 12 a 24 meses
    - Potranco(a): 24 a 36 meses, salvo se já estiver ativo reprodutivamente
    - Adultos: conforme sexo e flag de castrado
    - Égua Idosa: fêmea a partir de 16 anos
    """
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

    sexo = (sexo or "").upper().strip()
    castrado = int(bool(castrado))
    apto_reproducao = int(bool(apto_reproducao))

    sufixo = "a" if sexo.startswith("F") else "o"

    if meses <= 6:
        categoria = f"Potr{sufixo} ao pé"
    elif 7 <= meses < 12:
        categoria = "Potra Desmamada" if sexo.startswith("F") else "Potro Desmamado"
    elif 12 <= meses < 24:
        categoria = "Potra Sobreano" if sexo.startswith("F") else "Potro Sobreano"
    elif 24 <= meses < 36:
        if apto_reproducao:
            if sexo.startswith("F"):
                categoria = "Égua Adulta"
            elif castrado:
                categoria = "Macho Adulto Castrado"
            else:
                categoria = "Macho Adulto Inteiro"
        else:
            categoria = f"Potranc{sufixo}"
    else:
        if sexo.startswith("F"):
            categoria = "Égua Idosa" if anos >= 16 else "Égua Adulta"
        else:
            categoria = "Macho Adulto Castrado" if castrado else "Macho Adulto Inteiro"

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
        status_ecossistema TEXT DEFAULT 'Ativo na cabanha',
        tipo_vinculo TEXT,
        origem TEXT,
        classificacao TEXT,
        mansidao TEXT,
        manejo TEXT,
        castrado INTEGER DEFAULT 0,
        apto_reproducao INTEGER DEFAULT 0,
        categoria_idade TEXT,
        valor_aquisicao REAL DEFAULT 0,
        data_saida_ecossistema TEXT,
        observacoes TEXT,
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
    CREATE TABLE IF NOT EXISTS animal_historico_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_sbb TEXT NOT NULL,
        status_ecossistema TEXT NOT NULL,
        data_status TEXT,
        observacao TEXT,
        criado_em TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS animal_parcerias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_sbb TEXT NOT NULL,
        parceiro_nome TEXT,
        parceiro_contato TEXT,
        percentual_cabanha REAL DEFAULT 0,
        percentual_parceiro REAL DEFAULT 0,
        modelo_parceria TEXT,
        data_inicio TEXT,
        data_fim TEXT,
        ativo INTEGER DEFAULT 1,
        observacoes TEXT,
        criado_em TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS animal_vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_sbb TEXT NOT NULL,
        comprador_nome TEXT,
        comprador_cpf TEXT,
        comprador_whatsapp TEXT,
        comprador_email TEXT,
        data_venda TEXT,
        data_entrega TEXT,
        valor_venda REAL DEFAULT 0,
        condicao_pagamento TEXT,
        status_entrega TEXT,
        observacoes TEXT,
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


    def garantir_coluna(tabela, coluna, definicao):
        existentes = [r[1] for r in conn.execute(f"PRAGMA table_info({tabela})").fetchall()]
        if coluna not in existentes:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")

    # Migração leve para bancos SQLite já criados em versões anteriores.
    garantir_coluna("animais", "status_ecossistema", "TEXT DEFAULT 'Ativo na cabanha'")
    garantir_coluna("animais", "tipo_vinculo", "TEXT")
    garantir_coluna("animais", "origem", "TEXT")
    garantir_coluna("animais", "classificacao", "TEXT")
    garantir_coluna("animais", "mansidao", "TEXT")
    garantir_coluna("animais", "manejo", "TEXT")
    garantir_coluna("animais", "castrado", "INTEGER DEFAULT 0")
    garantir_coluna("animais", "apto_reproducao", "INTEGER DEFAULT 0")
    garantir_coluna("animais", "categoria_idade", "TEXT")
    garantir_coluna("animais", "valor_aquisicao", "REAL DEFAULT 0")
    garantir_coluna("animais", "data_saida_ecossistema", "TEXT")
    garantir_coluna("animais", "observacoes", "TEXT")

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




def excluir_item_fila(fila_id):
    conn = get_conn()
    row = conn.execute("SELECT status FROM extracoes_fila WHERE id=?", (fila_id,)).fetchone()
    if not row:
        conn.close()
        return False, "Item não encontrado."
    if row["status"] == "Processando":
        conn.close()
        return False, "Não é possível excluir um item em processamento."
    conn.execute("DELETE FROM extracoes_fila WHERE id=?", (fila_id,))
    conn.commit()
    conn.close()
    return True, "Item excluído da fila."


def limpar_fila_por_status(statuses):
    if not statuses:
        return 0
    permitidos = {"Em fila", "Erro", "Finalizado"}
    statuses = [s for s in statuses if s in permitidos]
    if not statuses:
        return 0
    placeholders = ",".join(["?"] * len(statuses))
    conn = get_conn()
    cur = conn.execute(f"DELETE FROM extracoes_fila WHERE status IN ({placeholders})", statuses)
    qtd = cur.rowcount or 0
    conn.commit()
    conn.close()
    return qtd


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
    idade_txt, categoria = calcular_idade_categoria(dados.get("Nascimento"), apto, dados.get("Sexo"), 0)
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


def listar_animais(incluir_inativos=True):
    conn = get_conn()
    if incluir_inativos:
        rows = conn.execute("SELECT * FROM animais ORDER BY nome, sbb").fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM animais
            WHERE COALESCE(status_ecossistema, 'Ativo na cabanha') NOT IN ('Vendido e entregue', 'Morto', 'Inativo histórico')
            ORDER BY nome, sbb
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_animal(sbb):
    conn = get_conn()
    row = conn.execute("SELECT * FROM animais WHERE sbb=?", (sbb,)).fetchone()
    conn.close()
    if not row:
        return None
    animal = dict(row)
    idade, categoria = calcular_idade_categoria(animal.get("nascimento"), animal.get("apto_reproducao"), animal.get("sexo"), animal.get("castrado"))
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


def atualizar_campos_cadastro(
    sbb,
    status_ecossistema,
    tipo_vinculo,
    origem,
    classificacao,
    mansidao,
    manejo,
    castrado,
    apto_reproducao,
    valor_aquisicao,
    observacoes,
):
    animal = buscar_animal(sbb) or {}
    _, categoria = calcular_idade_categoria(
        animal.get("nascimento"), apto_reproducao, animal.get("sexo"), castrado
    )

    status_anterior = animal.get("status_ecossistema") or "Ativo na cabanha"
    data_saida = animal.get("data_saida_ecossistema")
    if status_ecossistema in ["Vendido e entregue", "Morto", "Inativo histórico"] and not data_saida:
        data_saida = now_br()
    elif status_ecossistema not in ["Vendido e entregue", "Morto", "Inativo histórico"]:
        data_saida = None

    conn = get_conn()
    conn.execute("""
        UPDATE animais
        SET status_ecossistema=?, tipo_vinculo=?, origem=?, classificacao=?, mansidao=?, manejo=?, castrado=?,
            apto_reproducao=?, valor_aquisicao=?, observacoes=?, categoria_idade=?, data_saida_ecossistema=?, atualizado_em=?
        WHERE sbb=?
    """, (
        status_ecossistema, tipo_vinculo, origem, classificacao, mansidao, manejo, int(bool(castrado)),
        int(bool(apto_reproducao)), float(valor_aquisicao or 0), observacoes, categoria, data_saida, now_br(), sbb
    ))

    if status_ecossistema != status_anterior:
        conn.execute("""
            INSERT INTO animal_historico_status (animal_sbb, status_ecossistema, data_status, observacao, criado_em)
            VALUES (?, ?, ?, ?, ?)
        """, (sbb, status_ecossistema, now_br(), f"Alterado de {status_anterior} para {status_ecossistema}", now_br()))

    conn.commit(); conn.close()


def listar_historico_status(sbb):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM animal_historico_status
        WHERE animal_sbb=?
        ORDER BY id DESC
    """, (sbb,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def salvar_venda_animal(sbb, comprador_nome, comprador_cpf, comprador_whatsapp, comprador_email, data_venda, data_entrega, valor_venda, condicao_pagamento, status_entrega, observacoes):
    conn = get_conn()
    conn.execute("""
        INSERT INTO animal_vendas (animal_sbb, comprador_nome, comprador_cpf, comprador_whatsapp, comprador_email, data_venda, data_entrega, valor_venda, condicao_pagamento, status_entrega, observacoes, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sbb, comprador_nome, comprador_cpf, comprador_whatsapp, comprador_email, data_venda, data_entrega, float(valor_venda or 0), condicao_pagamento, status_entrega, observacoes, now_br()))

    if data_entrega:
        conn.execute("""
            UPDATE animais
            SET status_ecossistema='Vendido e entregue', data_saida_ecossistema=?, atualizado_em=?
            WHERE sbb=?
        """, (data_entrega, now_br(), sbb))
        conn.execute("""
            INSERT INTO animal_historico_status (animal_sbb, status_ecossistema, data_status, observacao, criado_em)
            VALUES (?, 'Vendido e entregue', ?, 'Venda cadastrada com entrega informada.', ?)
        """, (sbb, data_entrega, now_br()))
    else:
        conn.execute("""
            UPDATE animais
            SET status_ecossistema='Vendido - aguardando entrega', atualizado_em=?
            WHERE sbb=?
        """, (now_br(), sbb))

    conn.commit(); conn.close()


def listar_vendas_animal(sbb):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM animal_vendas WHERE animal_sbb=? ORDER BY id DESC", (sbb,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def salvar_parceria_animal(sbb, parceiro_nome, parceiro_contato, percentual_cabanha, percentual_parceiro, modelo_parceria, data_inicio, data_fim, ativo, observacoes):
    conn = get_conn()
    conn.execute("""
        INSERT INTO animal_parcerias (animal_sbb, parceiro_nome, parceiro_contato, percentual_cabanha, percentual_parceiro, modelo_parceria, data_inicio, data_fim, ativo, observacoes, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sbb, parceiro_nome, parceiro_contato, float(percentual_cabanha or 0), float(percentual_parceiro or 0), modelo_parceria, data_inicio, data_fim, int(bool(ativo)), observacoes, now_br()))
    if ativo:
        conn.execute("UPDATE animais SET status_ecossistema='Em parceria', tipo_vinculo='Parceria', atualizado_em=? WHERE sbb=?", (now_br(), sbb))
    conn.commit(); conn.close()


def listar_parcerias_animal(sbb):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM animal_parcerias WHERE animal_sbb=? ORDER BY id DESC", (sbb,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
