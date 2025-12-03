import sqlite3
from werkzeug.security import generate_password_hash

DB = "database.db"

sql = """
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS pesagens;
DROP TABLE IF EXISTS solicitacoes_recompensas;
DROP TABLE IF EXISTS recompensas;
DROP TABLE IF EXISTS resgates;
DROP TABLE IF EXISTS campanhas;
DROP TABLE IF EXISTS pontos_coleta;
DROP TABLE IF EXISTS descarte;

CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL,
    tipo TEXT DEFAULT 'user',
    eco_balance INTEGER DEFAULT 0
);

CREATE TABLE pesagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    peso REAL NOT NULL,
    eco_moedas INTEGER NOT NULL,
    status TEXT DEFAULT 'pendente',
    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE solicitacoes_recompensas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    recompensa_id INTEGER,
    status TEXT DEFAULT 'pendente',
    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recompensas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    custo INTEGER NOT NULL,
    codigo TEXT NOT NULL,
    criado_em TEXT DEFAULT (datetime('now'))
);

CREATE TABLE resgates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    recompensa_id INTEGER,
    codigo_usado TEXT,
    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE campanhas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descricao TEXT,
    autor_id INTEGER,
    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pontos_coleta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    endereco TEXT,
    cidade TEXT,
    contato TEXT,
    pin TEXT
);

CREATE TABLE descarte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    ponto_id INTEGER,
    material TEXT,
    peso REAL,
    eco_moedas INTEGER DEFAULT 0,
    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Executa criação das tabelas
    cur.executescript(sql)
    conn.commit()

    # Insere admin padrão com senha hasheada
    admin_email = "admin@admin.com"
    admin_nome = "Administrador"
    admin_password = "123"  # senha que será gerada (troque se quiser)
    admin_hash = generate_password_hash(admin_password)

    # Verifica se já existe admin com esse email
    cur.execute("SELECT id FROM usuarios WHERE email = ?", (admin_email,))
    if cur.fetchone() is None:
        cur.execute("""
            INSERT INTO usuarios (nome, email, senha, tipo, eco_balance)
            VALUES (?, ?, ?, 'admin', 0)
        """, (admin_nome, admin_email, admin_hash))
        conn.commit()
        print(f"Admin criado: {admin_email} / senha: {admin_password}")
    else:
        print("Admin já existe — não foi criado um novo.")

    cur.close()
    conn.close()
    print("database.db criado/atualizado com sucesso.")

if __name__ == "__main__":
    main()
