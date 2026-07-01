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


    cur.execute("""
    CREATE TABLE IF NOT EXISTS pessoas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_razao TEXT NOT NULL,
        nome_fantasia TEXT,
        tipo_pessoa TEXT,
        tipo_documento TEXT,
        documento TEXT,
        email TEXT,
        whatsapp TEXT,
        telefone TEXT,
        cidade TEXT,
        uf TEXT,
        endereco TEXT,
        pix TEXT,
        banco TEXT,
        agencia TEXT,
        conta TEXT,
        observacoes TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TEXT,
        atualizado_em TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pessoa_papeis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pessoa_id INTEGER NOT NULL,
        papel TEXT NOT NULL,
        ativo INTEGER DEFAULT 1,
        criado_em TEXT,
        UNIQUE(pessoa_id, papel),
        FOREIGN KEY(pessoa_id) REFERENCES pessoas(id)
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

    # Migração leve da tabela de pessoas.
    garantir_coluna("pessoas", "nome_fantasia", "TEXT")
    garantir_coluna("pessoas", "tipo_pessoa", "TEXT")
    garantir_coluna("pessoas", "tipo_documento", "TEXT")
    garantir_coluna("pessoas", "documento", "TEXT")
    garantir_coluna("pessoas", "email", "TEXT")
    garantir_coluna("pessoas", "whatsapp", "TEXT")
    garantir_coluna("pessoas", "telefone", "TEXT")
    garantir_coluna("pessoas", "cidade", "TEXT")
    garantir_coluna("pessoas", "uf", "TEXT")
    garantir_coluna("pessoas", "endereco", "TEXT")
    garantir_coluna("pessoas", "pix", "TEXT")
    garantir_coluna("pessoas", "banco", "TEXT")
    garantir_coluna("pessoas", "agencia", "TEXT")
    garantir_coluna("pessoas", "conta", "TEXT")
    garantir_coluna("pessoas", "observacoes", "TEXT")
    garantir_coluna("pessoas", "ativo", "INTEGER DEFAULT 1")
    garantir_coluna("pessoas", "criado_em", "TEXT")
    garantir_coluna("pessoas", "atualizado_em", "TEXT")

    conn.commit()
    conn.close()

    try:
        init_financeiro_db()
    except NameError:
        pass
    try:
        init_estoque_db()
    except NameError:
        pass
    try:
        init_sanidade_db()
    except NameError:
        pass


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


# ============================================================
# PESSOAS
# ============================================================
PAPEIS_PADRAO = [
    "Cliente",
    "Fornecedor",
    "Veterinário",
    "Ferrador",
    "Treinador/Domador",
    "Funcionário",
    "Parceiro",
    "Transportador",
    "Leiloeira",
    "Criador",
    "Proprietário",
    "Outro",
]


def normalizar_papeis(papeis):
    if not papeis:
        return []
    vistos = []
    for papel in papeis:
        papel = str(papel or "").strip()
        if papel and papel not in vistos:
            vistos.append(papel)
    return vistos


def salvar_pessoa(dados, papeis):
    conn = get_conn()
    pessoa_id = dados.get("id")
    agora = now_br()
    valores = (
        dados.get("nome_razao"), dados.get("nome_fantasia"), dados.get("tipo_pessoa"),
        dados.get("tipo_documento"), dados.get("documento"), dados.get("email"),
        dados.get("whatsapp"), dados.get("telefone"), dados.get("cidade"), dados.get("uf"),
        dados.get("endereco"), dados.get("pix"), dados.get("banco"), dados.get("agencia"),
        dados.get("conta"), dados.get("observacoes"), int(bool(dados.get("ativo", 1))), agora,
    )
    if pessoa_id:
        conn.execute("""
            UPDATE pessoas
            SET nome_razao=?, nome_fantasia=?, tipo_pessoa=?, tipo_documento=?, documento=?, email=?, whatsapp=?, telefone=?,
                cidade=?, uf=?, endereco=?, pix=?, banco=?, agencia=?, conta=?, observacoes=?, ativo=?, atualizado_em=?
            WHERE id=?
        """, valores + (pessoa_id,))
    else:
        cur = conn.execute("""
            INSERT INTO pessoas (
                nome_razao, nome_fantasia, tipo_pessoa, tipo_documento, documento, email, whatsapp, telefone,
                cidade, uf, endereco, pix, banco, agencia, conta, observacoes, ativo, criado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, valores)
        pessoa_id = cur.lastrowid

    conn.execute("UPDATE pessoa_papeis SET ativo=0 WHERE pessoa_id=?", (pessoa_id,))
    for papel in normalizar_papeis(papeis):
        conn.execute("""
            INSERT INTO pessoa_papeis (pessoa_id, papel, ativo, criado_em)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(pessoa_id, papel) DO UPDATE SET ativo=1
        """, (pessoa_id, papel, agora))
    conn.commit(); conn.close()
    return pessoa_id


def listar_pessoas(incluir_inativos=False, busca="", papel=""):
    conn = get_conn()
    where = []
    params = []
    if not incluir_inativos:
        where.append("p.ativo=1")
    if busca:
        termo = f"%{busca.strip()}%"
        where.append("(p.nome_razao LIKE ? OR p.nome_fantasia LIKE ? OR p.documento LIKE ? OR p.email LIKE ? OR p.whatsapp LIKE ?)")
        params += [termo, termo, termo, termo, termo]
    if papel:
        where.append("EXISTS (SELECT 1 FROM pessoa_papeis pp WHERE pp.pessoa_id=p.id AND pp.ativo=1 AND pp.papel=?)")
        params.append(papel)
    sql_where = " WHERE " + " AND ".join(where) if where else ""
    rows = conn.execute(f"""
        SELECT p.*,
               COALESCE((SELECT GROUP_CONCAT(pp.papel, ', ') FROM pessoa_papeis pp WHERE pp.pessoa_id=p.id AND pp.ativo=1), '') AS papeis
        FROM pessoas p
        {sql_where}
        ORDER BY p.ativo DESC, p.nome_razao COLLATE NOCASE
    """, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_pessoa(pessoa_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM pessoas WHERE id=?", (pessoa_id,)).fetchone()
    if not row:
        conn.close(); return None
    papeis = conn.execute("SELECT papel FROM pessoa_papeis WHERE pessoa_id=? AND ativo=1 ORDER BY papel", (pessoa_id,)).fetchall()
    conn.close()
    dados = dict(row)
    dados["papeis_lista"] = [p["papel"] for p in papeis]
    return dados


def excluir_pessoa(pessoa_id):
    """Exclusão lógica: preserva histórico e só desativa a pessoa."""
    conn = get_conn()
    conn.execute("UPDATE pessoas SET ativo=0, atualizado_em=? WHERE id=?", (now_br(), pessoa_id))
    conn.commit(); conn.close()


def reativar_pessoa(pessoa_id):
    conn = get_conn()
    conn.execute("UPDATE pessoas SET ativo=1, atualizado_em=? WHERE id=?", (now_br(), pessoa_id))
    conn.commit(); conn.close()

# ============================================================
# FINANCEIRO BASE v0.4
# ============================================================
CENTROS_CUSTO_PADRAO = [
    "Alimentação", "Suplementação", "Sanidade", "Reprodução", "Doma", "Treinamento",
    "Ferrageamento", "Frete / Transporte", "Leilões", "Mão de obra", "Manutenção",
    "Pastagens / Potreiros", "Custos Operacionais", "Venda de Animais", "Outros",
]

ATIVIDADES_PADRAO = [
    "Geral", "Reprodução", "Sanidade", "Doma", "Treinamento", "Competição", "Leilão",
    "Venda", "Manejo diário", "Pastagem / Potreiro", "Estoque", "Administrativo",
]

FORMAS_PAGAMENTO_PADRAO = ["", "Dinheiro", "Pix", "Boleto", "Cartão", "Transferência", "Cheque", "Permuta", "Outro"]
STATUS_PARCELA_PADRAO = ["Aberta", "Paga", "Recebida", "Vencida", "Cancelada"]


def init_financeiro_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS financeiro_lancamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        descricao TEXT,
        data_competencia TEXT,
        data_emissao TEXT,
        valor_total REAL DEFAULT 0,
        pessoa_id INTEGER,
        pessoa_nome TEXT,
        centro_custo TEXT,
        atividade TEXT,
        origem_modulo TEXT,
        forma_pagamento TEXT,
        status_lancamento TEXT DEFAULT 'Ativo',
        observacoes TEXT,
        animal_sbb TEXT,
        motivo TEXT,
        fornecedor TEXT,
        valor REAL,
        data_lancamento TEXT,
        observacao TEXT,
        criado_em TEXT,
        atualizado_em TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS financeiro_parcelas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lancamento_id INTEGER NOT NULL,
        numero_parcela INTEGER,
        data_vencimento TEXT,
        data_pagamento TEXT,
        valor_previsto REAL DEFAULT 0,
        valor_pago REAL DEFAULT 0,
        status TEXT DEFAULT 'Aberta',
        observacoes TEXT,
        criado_em TEXT,
        atualizado_em TEXT,
        FOREIGN KEY(lancamento_id) REFERENCES financeiro_lancamentos(id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS financeiro_rateios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lancamento_id INTEGER NOT NULL,
        criterio_rateio TEXT,
        animal_sbb TEXT,
        categoria_animal TEXT,
        manejo TEXT,
        percentual REAL DEFAULT 0,
        valor_rateado REAL DEFAULT 0,
        observacoes TEXT,
        criado_em TEXT,
        FOREIGN KEY(lancamento_id) REFERENCES financeiro_lancamentos(id)
    )
    """)

    def garantir_coluna(tabela, coluna, definicao):
        existentes = [r[1] for r in conn.execute(f"PRAGMA table_info({tabela})").fetchall()]
        if coluna not in existentes:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")

    for coluna, definicao in {
        "tipo": "TEXT",
        "descricao": "TEXT",
        "data_competencia": "TEXT",
        "data_emissao": "TEXT",
        "valor_total": "REAL DEFAULT 0",
        "pessoa_id": "INTEGER",
        "pessoa_nome": "TEXT",
        "centro_custo": "TEXT",
        "atividade": "TEXT",
        "origem_modulo": "TEXT",
        "forma_pagamento": "TEXT",
        "status_lancamento": "TEXT DEFAULT 'Ativo'",
        "observacoes": "TEXT",
        "atualizado_em": "TEXT",
    }.items():
        garantir_coluna("financeiro_lancamentos", coluna, definicao)

    conn.commit(); conn.close()


def salvar_lancamento_financeiro(dados, parcelas, rateios):
    init_financeiro_db()
    conn = get_conn(); cur = conn.cursor()
    valor_total = float(dados.get("valor_total") or 0)
    descricao = (dados.get("descricao") or dados.get("motivo") or "").strip()
    pessoa_nome = dados.get("pessoa_nome") or ""
    cur.execute("""
        INSERT INTO financeiro_lancamentos (
            tipo, descricao, data_competencia, data_emissao, valor_total,
            pessoa_id, pessoa_nome, centro_custo, atividade, origem_modulo,
            forma_pagamento, status_lancamento, observacoes,
            motivo, fornecedor, valor, data_lancamento, observacao, criado_em, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Ativo', ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados.get("tipo"), descricao, dados.get("data_competencia"), dados.get("data_emissao"), valor_total,
        dados.get("pessoa_id"), pessoa_nome, dados.get("centro_custo"), dados.get("atividade"), dados.get("origem_modulo") or "Manual",
        dados.get("forma_pagamento"), dados.get("observacoes"), descricao, pessoa_nome, valor_total,
        dados.get("data_competencia"), dados.get("observacoes"), now_br(), now_br(),
    ))
    lancamento_id = cur.lastrowid
    if not parcelas:
        parcelas = [{"numero_parcela": 1, "data_vencimento": dados.get("data_competencia") or dados.get("data_emissao"), "valor_previsto": valor_total, "status": "Aberta", "observacoes": ""}]
    for parcela in parcelas:
        cur.execute("""
            INSERT INTO financeiro_parcelas (lancamento_id, numero_parcela, data_vencimento, valor_previsto, status, observacoes, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (lancamento_id, parcela.get("numero_parcela"), parcela.get("data_vencimento"), float(parcela.get("valor_previsto") or 0), parcela.get("status") or "Aberta", parcela.get("observacoes") or "", now_br(), now_br()))
    if not rateios:
        rateios = [{"criterio_rateio": "Global", "animal_sbb": "", "categoria_animal": "", "manejo": "", "percentual": 100, "valor_rateado": valor_total, "observacoes": ""}]
    for rateio in rateios:
        cur.execute("""
            INSERT INTO financeiro_rateios (lancamento_id, criterio_rateio, animal_sbb, categoria_animal, manejo, percentual, valor_rateado, observacoes, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (lancamento_id, rateio.get("criterio_rateio") or "Global", rateio.get("animal_sbb") or "", rateio.get("categoria_animal") or "", rateio.get("manejo") or "", float(rateio.get("percentual") or 0), float(rateio.get("valor_rateado") or 0), rateio.get("observacoes") or "", now_br()))
    conn.commit(); conn.close(); return lancamento_id



def atualizar_lancamento_financeiro(lancamento_id, dados, parcelas, rateios):
    """Atualiza um lançamento financeiro e recria parcelas/rateios.

    Uso previsto: correção de lançamentos cadastrados com erro.
    Para manter o financeiro consistente, as parcelas e rateios anteriores são substituídos
    pela nova composição informada na tela de edição.
    """
    init_financeiro_db()
    conn = get_conn(); cur = conn.cursor()
    valor_total = float(dados.get("valor_total") or 0)
    descricao = (dados.get("descricao") or dados.get("motivo") or "").strip()
    pessoa_nome = dados.get("pessoa_nome") or ""

    cur.execute("""
        UPDATE financeiro_lancamentos
        SET tipo=?, descricao=?, data_competencia=?, data_emissao=?, valor_total=?,
            pessoa_id=?, pessoa_nome=?, centro_custo=?, atividade=?, origem_modulo=?,
            forma_pagamento=?, observacoes=?, motivo=?, fornecedor=?, valor=?,
            data_lancamento=?, observacao=?, atualizado_em=?
        WHERE id=?
    """, (
        dados.get("tipo"), descricao, dados.get("data_competencia"), dados.get("data_emissao"), valor_total,
        dados.get("pessoa_id"), pessoa_nome, dados.get("centro_custo"), dados.get("atividade"), dados.get("origem_modulo") or "Manual",
        dados.get("forma_pagamento"), dados.get("observacoes"), descricao, pessoa_nome, valor_total,
        dados.get("data_competencia"), dados.get("observacoes"), now_br(), lancamento_id,
    ))

    cur.execute("DELETE FROM financeiro_parcelas WHERE lancamento_id=?", (lancamento_id,))
    cur.execute("DELETE FROM financeiro_rateios WHERE lancamento_id=?", (lancamento_id,))

    if not parcelas:
        parcelas = [{"numero_parcela": 1, "data_vencimento": dados.get("data_competencia") or dados.get("data_emissao"), "valor_previsto": valor_total, "status": "Aberta", "observacoes": ""}]
    for parcela in parcelas:
        cur.execute("""
            INSERT INTO financeiro_parcelas (lancamento_id, numero_parcela, data_vencimento, valor_previsto, status, observacoes, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (lancamento_id, parcela.get("numero_parcela"), parcela.get("data_vencimento"), float(parcela.get("valor_previsto") or 0), parcela.get("status") or "Aberta", parcela.get("observacoes") or "", now_br(), now_br()))

    if not rateios:
        rateios = [{"criterio_rateio": "Global", "animal_sbb": "", "categoria_animal": "", "manejo": "", "percentual": 100, "valor_rateado": valor_total, "observacoes": ""}]
    for rateio in rateios:
        cur.execute("""
            INSERT INTO financeiro_rateios (lancamento_id, criterio_rateio, animal_sbb, categoria_animal, manejo, percentual, valor_rateado, observacoes, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (lancamento_id, rateio.get("criterio_rateio") or "Global", rateio.get("animal_sbb") or "", rateio.get("categoria_animal") or "", rateio.get("manejo") or "", float(rateio.get("percentual") or 0), float(rateio.get("valor_rateado") or 0), rateio.get("observacoes") or "", now_br()))

    conn.commit(); conn.close(); return True

def listar_lancamentos_financeiros(filtros=None):
    init_financeiro_db(); filtros = filtros or {}
    where = ["COALESCE(l.status_lancamento, 'Ativo') <> 'Excluído'"]; params = []
    for campo in ["tipo", "centro_custo", "atividade", "origem_modulo", "pessoa_id"]:
        if filtros.get(campo):
            where.append(f"l.{campo}=?"); params.append(filtros[campo])
    if filtros.get("busca"):
        where.append("(LOWER(l.descricao) LIKE ? OR LOWER(COALESCE(l.pessoa_nome,'')) LIKE ? OR LOWER(COALESCE(l.observacoes,'')) LIKE ?)")
        termo = f"%{str(filtros['busca']).lower()}%"; params.extend([termo, termo, termo])
    if filtros.get("data_inicio"):
        where.append("l.data_competencia >= ?"); params.append(filtros["data_inicio"])
    if filtros.get("data_fim"):
        where.append("l.data_competencia <= ?"); params.append(filtros["data_fim"])
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT l.id, l.tipo AS Tipo, l.data_competencia AS Data, l.descricao AS Descrição,
               l.valor_total AS Valor, COALESCE(p.nome_razao, l.pessoa_nome, '') AS Pessoa,
               l.centro_custo AS 'Centro de Custo', l.atividade AS Atividade, l.origem_modulo AS Origem,
               l.forma_pagamento AS 'Forma de Pagamento', l.status_lancamento AS Status
        FROM financeiro_lancamentos l
        LEFT JOIN pessoas p ON p.id = l.pessoa_id
        WHERE {' AND '.join(where)}
        ORDER BY l.id DESC
    """, params).fetchall()
    conn.close(); return [dict(r) for r in rows]


def buscar_lancamento_financeiro(lancamento_id):
    init_financeiro_db(); conn = get_conn()
    row = conn.execute("SELECT * FROM financeiro_lancamentos WHERE id=?", (lancamento_id,)).fetchone()
    conn.close(); return dict(row) if row else None


def listar_parcelas_financeiras(lancamento_id=None, filtros=None):
    init_financeiro_db(); filtros = filtros or {}
    where = ["COALESCE(l.status_lancamento, 'Ativo') <> 'Excluído'"]; params = []
    if lancamento_id:
        where.append("p.lancamento_id=?"); params.append(lancamento_id)
    for campo_l, chave in [("tipo", "tipo"), ("centro_custo", "centro_custo"), ("atividade", "atividade")]:
        if filtros.get(chave):
            where.append(f"l.{campo_l}=?"); params.append(filtros[chave])
    if filtros.get("status_parcela"):
        where.append("p.status=?"); params.append(filtros["status_parcela"])
    if filtros.get("data_inicio"):
        where.append("p.data_vencimento >= ?"); params.append(filtros["data_inicio"])
    if filtros.get("data_fim"):
        where.append("p.data_vencimento <= ?"); params.append(filtros["data_fim"])
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT p.id, p.lancamento_id AS Lançamento, l.tipo AS Tipo, l.descricao AS Descrição,
               COALESCE(pe.nome_razao, l.pessoa_nome, '') AS Pessoa, p.numero_parcela AS Parcela,
               p.data_vencimento AS Vencimento, p.data_pagamento AS Pagamento,
               p.valor_previsto AS 'Valor Previsto', p.valor_pago AS 'Valor Pago', p.status AS Status,
               l.centro_custo AS 'Centro de Custo', l.atividade AS Atividade
        FROM financeiro_parcelas p
        JOIN financeiro_lancamentos l ON l.id = p.lancamento_id
        LEFT JOIN pessoas pe ON pe.id = l.pessoa_id
        WHERE {' AND '.join(where)}
        ORDER BY p.data_vencimento, p.id
    """, params).fetchall()
    conn.close(); return [dict(r) for r in rows]


def listar_rateios_financeiros(lancamento_id):
    init_financeiro_db(); conn = get_conn()
    rows = conn.execute("""
        SELECT r.id, r.criterio_rateio AS Critério, r.animal_sbb AS Animal, a.nome AS 'Nome Animal',
               r.categoria_animal AS Categoria, r.manejo AS Manejo, r.percentual AS Percentual,
               r.valor_rateado AS 'Valor Rateado', r.observacoes AS Observações
        FROM financeiro_rateios r
        LEFT JOIN animais a ON a.sbb = r.animal_sbb
        WHERE r.lancamento_id=? ORDER BY r.id
    """, (lancamento_id,)).fetchall()
    conn.close(); return [dict(r) for r in rows]


def pagar_parcela_financeira(parcela_id, data_pagamento, valor_pago=None):
    init_financeiro_db(); conn = get_conn()
    row = conn.execute("SELECT valor_previsto FROM financeiro_parcelas WHERE id=?", (parcela_id,)).fetchone()
    if not row:
        conn.close(); return False
    lanc = conn.execute("SELECT l.tipo FROM financeiro_parcelas p JOIN financeiro_lancamentos l ON l.id=p.lancamento_id WHERE p.id=?", (parcela_id,)).fetchone()
    status = "Paga" if lanc and lanc["tipo"] == "Saída" else "Recebida"
    valor = float(valor_pago if valor_pago is not None else row["valor_previsto"] or 0)
    conn.execute("UPDATE financeiro_parcelas SET data_pagamento=?, valor_pago=?, status=?, atualizado_em=? WHERE id=?", (data_pagamento, valor, status, now_br(), parcela_id))
    conn.commit(); conn.close(); return True


def excluir_lancamento_financeiro(lancamento_id):
    init_financeiro_db(); conn = get_conn()
    conn.execute("UPDATE financeiro_lancamentos SET status_lancamento='Excluído', atualizado_em=? WHERE id=?", (now_br(), lancamento_id))
    conn.commit(); conn.close(); return True


def indicadores_financeiros(filtros=None):
    parcelas = listar_parcelas_financeiras(filtros=filtros or {})
    saidas = entradas = pago = recebido = aberto_pagar = aberto_receber = 0.0
    for p in parcelas:
        prev = float(p.get("Valor Previsto") or 0); real = float(p.get("Valor Pago") or 0)
        if p.get("Tipo") == "Entrada":
            entradas += prev
            if p.get("Status") == "Recebida": recebido += real or prev
            elif p.get("Status") != "Cancelada": aberto_receber += prev
        elif p.get("Tipo") == "Saída":
            saidas += prev
            if p.get("Status") == "Paga": pago += real or prev
            elif p.get("Status") != "Cancelada": aberto_pagar += prev
    return {
        "entradas_previstas": entradas, "saidas_previstas": saidas, "saldo_previsto": entradas - saidas,
        "recebido": recebido, "pago": pago, "saldo_realizado": recebido - pago,
        "aberto_receber": aberto_receber, "aberto_pagar": aberto_pagar,
    }

# ============================================================
# ESTOQUE v0.5
# ============================================================
CATEGORIAS_ESTOQUE_PADRAO = [
    "Ração",
    "Suplemento",
    "Medicamento",
    "Vacina",
    "Vermífugo",
    "Material de manejo",
    "Material veterinário",
    "Sêmen / Palheta",
    "Feno / Volumoso",
    "Outro",
]

UNIDADES_ESTOQUE_PADRAO = ["kg", "g", "L", "mL", "un", "dose", "saco", "fardo", "palheta", "frasco", "ampola", "bisnaga"]

TIPOS_MOV_ESTOQUE = ["Entrada", "Saída / Consumo", "Ajuste"]


def init_estoque_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS estoque_produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        categoria TEXT,
        apresentacao TEXT,
        laboratorio_fabricante TEXT,
        unidade TEXT,
        unidade_compra TEXT,
        unidade_consumo TEXT,
        qtd_consumo_por_unidade_compra REAL DEFAULT 1,
        estoque_minimo REAL DEFAULT 0,
        valor_unitario REAL DEFAULT 0,
        data_vencimento TEXT,
        observacoes TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TEXT,
        atualizado_em TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        tipo_movimento TEXT NOT NULL,
        data_movimento TEXT,
        quantidade REAL DEFAULT 0,
        valor_unitario REAL DEFAULT 0,
        valor_total REAL DEFAULT 0,
        pessoa_id INTEGER,
        pessoa_nome TEXT,
        destino_tipo TEXT,
        animal_sbb TEXT,
        categoria_animal TEXT,
        manejo TEXT,
        centro_custo TEXT,
        atividade TEXT,
        observacoes TEXT,
        status_movimento TEXT DEFAULT 'Ativo',
        criado_em TEXT,
        atualizado_em TEXT,
        FOREIGN KEY(produto_id) REFERENCES estoque_produtos(id)
    )
    """)

    # Migração leve para bancos já criados em versões anteriores.
    colunas_prod = [r[1] for r in cur.execute("PRAGMA table_info(estoque_produtos)").fetchall()]
    if "unidade_compra" not in colunas_prod:
        cur.execute("ALTER TABLE estoque_produtos ADD COLUMN unidade_compra TEXT")
    if "unidade_consumo" not in colunas_prod:
        cur.execute("ALTER TABLE estoque_produtos ADD COLUMN unidade_consumo TEXT")
    if "qtd_consumo_por_unidade_compra" not in colunas_prod:
        cur.execute("ALTER TABLE estoque_produtos ADD COLUMN qtd_consumo_por_unidade_compra REAL DEFAULT 1")

    colunas = [r[1] for r in cur.execute("PRAGMA table_info(estoque_movimentacoes)").fetchall()]
    if "centro_custo" not in colunas:
        cur.execute("ALTER TABLE estoque_movimentacoes ADD COLUMN centro_custo TEXT")
    if "atividade" not in colunas:
        cur.execute("ALTER TABLE estoque_movimentacoes ADD COLUMN atividade TEXT")

    conn.commit()
    conn.close()


def salvar_produto_estoque(dados):
    init_estoque_db()
    conn = get_conn()
    cur = conn.cursor()
    agora = now_br()
    produto_id = dados.get("id")
    valores = (
        (dados.get("nome") or "").strip(),
        dados.get("categoria") or "",
        dados.get("apresentacao") or "",
        dados.get("laboratorio_fabricante") or "",
        dados.get("unidade") or dados.get("unidade_consumo") or "",
        dados.get("unidade_compra") or "",
        dados.get("unidade_consumo") or dados.get("unidade") or "",
        float(dados.get("qtd_consumo_por_unidade_compra") or 1),
        float(dados.get("estoque_minimo") or 0),
        float(dados.get("valor_unitario") or 0),
        dados.get("data_vencimento") or "",
        dados.get("observacoes") or "",
        int(dados.get("ativo", 1)),
    )
    if produto_id:
        cur.execute("""
            UPDATE estoque_produtos
            SET nome=?, categoria=?, apresentacao=?, laboratorio_fabricante=?, unidade=?, unidade_compra=?, unidade_consumo=?,
                qtd_consumo_por_unidade_compra=?, estoque_minimo=?, valor_unitario=?, data_vencimento=?, observacoes=?, ativo=?, atualizado_em=?
            WHERE id=?
        """, valores + (agora, produto_id))
    else:
        cur.execute("""
            INSERT INTO estoque_produtos (
                nome, categoria, apresentacao, laboratorio_fabricante, unidade, unidade_compra, unidade_consumo,
                qtd_consumo_por_unidade_compra, estoque_minimo, valor_unitario, data_vencimento, observacoes, ativo, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, valores + (agora, agora))
        produto_id = cur.lastrowid
    conn.commit(); conn.close()
    return produto_id


def listar_produtos_estoque(incluir_inativos=False, busca="", categoria=""):
    init_estoque_db()
    where = [] if incluir_inativos else ["ativo=1"]
    params = []
    if busca:
        where.append("(LOWER(nome) LIKE ? OR LOWER(COALESCE(apresentacao,'')) LIKE ? OR LOWER(COALESCE(laboratorio_fabricante,'')) LIKE ?)")
        termo = f"%{str(busca).lower()}%"; params.extend([termo, termo, termo])
    if categoria:
        where.append("categoria=?"); params.append(categoria)
    sql_where = "WHERE " + " AND ".join(where) if where else ""
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT id, nome AS Produto, categoria AS Categoria, apresentacao AS Apresentação,
               laboratorio_fabricante AS 'Laboratório/Fabricante',
               COALESCE(unidade_consumo, unidade, '') AS 'Unidade de Consumo',
               COALESCE(unidade_compra, '') AS 'Unidade de Compra',
               COALESCE(qtd_consumo_por_unidade_compra, 1) AS 'Qtd Consumo por Compra',
               estoque_minimo AS 'Estoque Mínimo', valor_unitario AS 'Valor Unitário Consumo',
               data_vencimento AS Vencimento, ativo AS Ativo
        FROM estoque_produtos
        {sql_where}
        ORDER BY nome
    """, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_produto_estoque(produto_id):
    init_estoque_db(); conn = get_conn()
    row = conn.execute("SELECT * FROM estoque_produtos WHERE id=?", (produto_id,)).fetchone()
    conn.close(); return dict(row) if row else None


def excluir_produto_estoque(produto_id):
    init_estoque_db(); conn = get_conn()
    conn.execute("UPDATE estoque_produtos SET ativo=0, atualizado_em=? WHERE id=?", (now_br(), produto_id))
    conn.commit(); conn.close(); return True


def salvar_movimentacao_estoque(dados):
    init_estoque_db()
    conn = get_conn(); cur = conn.cursor(); agora = now_br()
    mov_id = dados.get("id")
    quantidade = float(dados.get("quantidade") or 0)
    valor_unitario = float(dados.get("valor_unitario") or 0)
    valor_total = float(dados.get("valor_total") if dados.get("valor_total") is not None else quantidade * valor_unitario)
    valores = (
        int(dados.get("produto_id")), dados.get("tipo_movimento") or "Entrada", dados.get("data_movimento") or "",
        quantidade, valor_unitario, valor_total, dados.get("pessoa_id"), dados.get("pessoa_nome") or "",
        dados.get("destino_tipo") or "", dados.get("animal_sbb") or "", dados.get("categoria_animal") or "",
        dados.get("manejo") or "", dados.get("centro_custo") or "", dados.get("atividade") or "",
        dados.get("observacoes") or "",
    )
    if mov_id:
        cur.execute("""
            UPDATE estoque_movimentacoes
            SET produto_id=?, tipo_movimento=?, data_movimento=?, quantidade=?, valor_unitario=?, valor_total=?,
                pessoa_id=?, pessoa_nome=?, destino_tipo=?, animal_sbb=?, categoria_animal=?, manejo=?,
                centro_custo=?, atividade=?, observacoes=?, atualizado_em=?
            WHERE id=?
        """, valores + (agora, mov_id))
    else:
        cur.execute("""
            INSERT INTO estoque_movimentacoes (
                produto_id, tipo_movimento, data_movimento, quantidade, valor_unitario, valor_total,
                pessoa_id, pessoa_nome, destino_tipo, animal_sbb, categoria_animal, manejo, centro_custo, atividade, observacoes,
                status_movimento, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Ativo', ?, ?)
        """, valores + (agora, agora))
        mov_id = cur.lastrowid
    conn.commit(); conn.close(); return mov_id


def listar_movimentacoes_estoque(filtros=None):
    init_estoque_db(); filtros = filtros or {}
    where = ["COALESCE(m.status_movimento,'Ativo') <> 'Excluído'"]; params = []
    if filtros.get("produto_id"):
        where.append("m.produto_id=?"); params.append(filtros["produto_id"])
    if filtros.get("tipo_movimento"):
        where.append("m.tipo_movimento=?"); params.append(filtros["tipo_movimento"])
    if filtros.get("categoria"):
        where.append("p.categoria=?"); params.append(filtros["categoria"])
    if filtros.get("busca"):
        where.append("(LOWER(p.nome) LIKE ? OR LOWER(COALESCE(m.observacoes,'')) LIKE ? OR LOWER(COALESCE(m.pessoa_nome,'')) LIKE ?)")
        termo = f"%{str(filtros['busca']).lower()}%"; params.extend([termo, termo, termo])
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT m.id, m.data_movimento AS Data, m.tipo_movimento AS Movimento, p.nome AS Produto,
               p.categoria AS Categoria, m.quantidade AS Quantidade, COALESCE(p.unidade_consumo, p.unidade, '') AS Unidade,
               m.valor_unitario AS 'Valor Unitário', m.valor_total AS 'Valor Total',
               COALESCE(pe.nome_razao, m.pessoa_nome, '') AS Pessoa, m.destino_tipo AS Destino,
               m.animal_sbb AS Animal, m.categoria_animal AS 'Categoria Animal', m.manejo AS Manejo,
               m.centro_custo AS 'Centro de Custo', m.atividade AS Atividade,
               m.observacoes AS Observações
        FROM estoque_movimentacoes m
        JOIN estoque_produtos p ON p.id = m.produto_id
        LEFT JOIN pessoas pe ON pe.id = m.pessoa_id
        WHERE {' AND '.join(where)}
        ORDER BY m.id DESC
    """, params).fetchall()
    conn.close(); return [dict(r) for r in rows]


def excluir_movimentacao_estoque(mov_id):
    init_estoque_db(); conn = get_conn()
    conn.execute("UPDATE estoque_movimentacoes SET status_movimento='Excluído', atualizado_em=? WHERE id=?", (now_br(), mov_id))
    conn.commit(); conn.close(); return True


def saldo_estoque_produtos():
    init_estoque_db(); conn = get_conn()
    rows = conn.execute("""
        SELECT p.id, p.nome AS Produto, p.categoria AS Categoria, COALESCE(p.unidade_consumo, p.unidade, '') AS Unidade,
               p.estoque_minimo AS 'Estoque Mínimo', p.data_vencimento AS Vencimento,
               COALESCE(SUM(CASE
                    WHEN m.status_movimento='Excluído' THEN 0
                    WHEN m.tipo_movimento='Entrada' THEN m.quantidade
                    WHEN m.tipo_movimento='Saída / Consumo' THEN -m.quantidade
                    WHEN m.tipo_movimento='Ajuste' THEN m.quantidade
                    ELSE 0 END), 0) AS Saldo,
               COALESCE(SUM(CASE
                    WHEN m.status_movimento='Excluído' THEN 0
                    WHEN m.tipo_movimento='Entrada' THEN m.valor_total
                    WHEN m.tipo_movimento='Saída / Consumo' THEN -m.valor_total
                    WHEN m.tipo_movimento='Ajuste' THEN m.valor_total
                    ELSE 0 END), 0) AS 'Valor em Estoque'
        FROM estoque_produtos p
        LEFT JOIN estoque_movimentacoes m ON m.produto_id = p.id
        WHERE p.ativo=1
        GROUP BY p.id
        ORDER BY p.nome
    """).fetchall()
    conn.close(); return [dict(r) for r in rows]


# ============================================================
# SANIDADE E FARMÁCIA
# ============================================================
TIPOS_SANIDADE_PADRAO = [
    "Vacina",
    "Vermífugo",
    "Medicação",
    "Atendimento veterinário",
    "Exame",
    "Procedimento",
    "Outro",
]

VIAS_APLICACAO_PADRAO = ["", "Oral", "Intramuscular", "Subcutânea", "Intravenosa", "Tópica", "Intranasal", "Outra"]

PROTOCOLOS_SANIDADE_PADRAO = ["", "Geral", "Éguas de cria", "Potros", "Garanhões", "Animais em treinamento", "Animais de terceiros"]


def init_sanidade_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sanidade_eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_evento TEXT NOT NULL,
        data_evento TEXT,
        protocolo TEXT,
        principio_ativo TEXT,
        nome_comercial TEXT,
        lote TEXT,
        via_aplicacao TEXT,
        produto_id INTEGER,
        produto_nome TEXT,
        quantidade_total REAL DEFAULT 0,
        unidade TEXT,
        valor_produtos REAL DEFAULT 0,
        veterinario_pessoa_id INTEGER,
        veterinario_nome TEXT,
        local_atendimento TEXT,
        motivo TEXT,
        honorarios REAL DEFAULT 0,
        outros_custos REAL DEFAULT 0,
        custo_total REAL DEFAULT 0,
        proxima_dose TEXT,
        centro_custo TEXT,
        atividade TEXT,
        gerar_financeiro INTEGER DEFAULT 0,
        lancamento_financeiro_id INTEGER,
        movimentacao_estoque_id INTEGER,
        observacoes TEXT,
        status_evento TEXT DEFAULT 'Ativo',
        criado_em TEXT,
        atualizado_em TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sanidade_evento_animais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evento_id INTEGER NOT NULL,
        animal_sbb TEXT NOT NULL,
        animal_nome TEXT,
        quantidade REAL DEFAULT 0,
        custo_rateado REAL DEFAULT 0,
        observacoes TEXT,
        FOREIGN KEY(evento_id) REFERENCES sanidade_eventos(id)
    )
    """)
    conn.commit(); conn.close()


def salvar_evento_sanidade(dados, animais):
    init_sanidade_db()
    conn = get_conn(); cur = conn.cursor(); agora = now_br()
    evento_id = dados.get("id")
    animais = animais or []
    qtd_animais = max(len(animais), 1)
    custo_total = float(dados.get("custo_total") or 0)
    valores = (
        dados.get("tipo_evento") or "", dados.get("data_evento") or "", dados.get("protocolo") or "",
        dados.get("principio_ativo") or "", dados.get("nome_comercial") or "", dados.get("lote") or "",
        dados.get("via_aplicacao") or "", dados.get("produto_id"), dados.get("produto_nome") or "",
        float(dados.get("quantidade_total") or 0), dados.get("unidade") or "", float(dados.get("valor_produtos") or 0),
        dados.get("veterinario_pessoa_id"), dados.get("veterinario_nome") or "", dados.get("local_atendimento") or "",
        dados.get("motivo") or "", float(dados.get("honorarios") or 0), float(dados.get("outros_custos") or 0),
        custo_total, dados.get("proxima_dose") or "", dados.get("centro_custo") or "", dados.get("atividade") or "",
        int(bool(dados.get("gerar_financeiro", 0))), dados.get("lancamento_financeiro_id"), dados.get("movimentacao_estoque_id"),
        dados.get("observacoes") or "",
    )
    if evento_id:
        cur.execute("""
            UPDATE sanidade_eventos
            SET tipo_evento=?, data_evento=?, protocolo=?, principio_ativo=?, nome_comercial=?, lote=?, via_aplicacao=?,
                produto_id=?, produto_nome=?, quantidade_total=?, unidade=?, valor_produtos=?, veterinario_pessoa_id=?, veterinario_nome=?,
                local_atendimento=?, motivo=?, honorarios=?, outros_custos=?, custo_total=?, proxima_dose=?, centro_custo=?, atividade=?,
                gerar_financeiro=?, lancamento_financeiro_id=?, movimentacao_estoque_id=?, observacoes=?, atualizado_em=?
            WHERE id=?
        """, valores + (agora, evento_id))
        cur.execute("DELETE FROM sanidade_evento_animais WHERE evento_id=?", (evento_id,))
    else:
        cur.execute("""
            INSERT INTO sanidade_eventos (
                tipo_evento, data_evento, protocolo, principio_ativo, nome_comercial, lote, via_aplicacao,
                produto_id, produto_nome, quantidade_total, unidade, valor_produtos, veterinario_pessoa_id, veterinario_nome,
                local_atendimento, motivo, honorarios, outros_custos, custo_total, proxima_dose, centro_custo, atividade,
                gerar_financeiro, lancamento_financeiro_id, movimentacao_estoque_id, observacoes, status_evento, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Ativo', ?, ?)
        """, valores + (agora, agora))
        evento_id = cur.lastrowid
    for a in animais:
        cur.execute("""
            INSERT INTO sanidade_evento_animais (evento_id, animal_sbb, animal_nome, quantidade, custo_rateado, observacoes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            evento_id, a.get("animal_sbb") or "", a.get("animal_nome") or "",
            float(a.get("quantidade") or 0), float(a.get("custo_rateado") if a.get("custo_rateado") is not None else (custo_total / qtd_animais)),
            a.get("observacoes") or "",
        ))
    conn.commit(); conn.close(); return evento_id


def atualizar_integracoes_sanidade(evento_id, lancamento_financeiro_id=None, movimentacao_estoque_id=None):
    init_sanidade_db(); conn = get_conn()
    conn.execute("""
        UPDATE sanidade_eventos
        SET lancamento_financeiro_id=COALESCE(?, lancamento_financeiro_id),
            movimentacao_estoque_id=COALESCE(?, movimentacao_estoque_id),
            atualizado_em=?
        WHERE id=?
    """, (lancamento_financeiro_id, movimentacao_estoque_id, now_br(), evento_id))
    conn.commit(); conn.close(); return True


def listar_eventos_sanidade(filtros=None):
    init_sanidade_db(); filtros = filtros or {}
    where = ["COALESCE(e.status_evento,'Ativo') <> 'Excluído'"]; params = []
    if filtros.get("tipo_evento"):
        where.append("e.tipo_evento=?"); params.append(filtros["tipo_evento"])
    if filtros.get("animal_sbb"):
        where.append("a.animal_sbb=?"); params.append(filtros["animal_sbb"])
    if filtros.get("protocolo"):
        where.append("e.protocolo=?"); params.append(filtros["protocolo"])
    if filtros.get("busca"):
        termo = f"%{str(filtros['busca']).lower()}%"
        where.append("(LOWER(COALESCE(e.nome_comercial,'')) LIKE ? OR LOWER(COALESCE(e.principio_ativo,'')) LIKE ? OR LOWER(COALESCE(e.motivo,'')) LIKE ? OR LOWER(COALESCE(a.animal_nome,'')) LIKE ? OR LOWER(COALESCE(a.animal_sbb,'')) LIKE ?)")
        params.extend([termo, termo, termo, termo, termo])
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT e.id, e.data_evento AS Data, e.tipo_evento AS Tipo, e.protocolo AS Protocolo,
               e.nome_comercial AS Produto, e.principio_ativo AS 'Princípio Ativo', e.lote AS Lote,
               e.via_aplicacao AS Via, e.veterinario_nome AS Veterinário,
               GROUP_CONCAT(a.animal_nome || ' (' || a.animal_sbb || ')', ', ') AS Animais,
               e.custo_total AS 'Custo Total', e.proxima_dose AS 'Próxima Dose',
               e.centro_custo AS 'Centro de Custo', e.atividade AS Atividade, e.observacoes AS Observações
        FROM sanidade_eventos e
        LEFT JOIN sanidade_evento_animais a ON a.evento_id = e.id
        WHERE {' AND '.join(where)}
        GROUP BY e.id
        ORDER BY e.id DESC
    """, params).fetchall()
    conn.close(); return [dict(r) for r in rows]


def buscar_evento_sanidade(evento_id):
    init_sanidade_db(); conn = get_conn()
    evento = conn.execute("SELECT * FROM sanidade_eventos WHERE id=?", (evento_id,)).fetchone()
    animais = conn.execute("SELECT * FROM sanidade_evento_animais WHERE evento_id=?", (evento_id,)).fetchall()
    conn.close()
    return {"evento": dict(evento) if evento else None, "animais": [dict(a) for a in animais]}


def excluir_evento_sanidade(evento_id):
    init_sanidade_db(); conn = get_conn()
    conn.execute("UPDATE sanidade_eventos SET status_evento='Excluído', atualizado_em=? WHERE id=?", (now_br(), evento_id))
    conn.commit(); conn.close(); return True


def alertas_sanidade(dias=30):
    init_sanidade_db(); conn = get_conn()
    rows = conn.execute("""
        SELECT e.id, e.proxima_dose AS 'Próxima Dose', e.tipo_evento AS Tipo, e.nome_comercial AS Produto,
               GROUP_CONCAT(a.animal_nome || ' (' || a.animal_sbb || ')', ', ') AS Animais
        FROM sanidade_eventos e
        LEFT JOIN sanidade_evento_animais a ON a.evento_id=e.id
        WHERE COALESCE(e.status_evento,'Ativo') <> 'Excluído'
          AND COALESCE(e.proxima_dose,'') <> ''
        GROUP BY e.id
        ORDER BY e.proxima_dose
    """).fetchall()
    conn.close(); return [dict(r) for r in rows]
