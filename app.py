from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)

# --------------------------------------------------------
# Chave secreta usada para sessões e flash messages
# (troque por uma chave segura antes do deploy)
# --------------------------------------------------------
app.secret_key = "troque_essa_chave_para_algo_seguro"  


# --------------------------------------------------------
# --------------------- Banco de Dados -------------------
# --------------------------------------------------------

DB_FILE = "database.db"

# Conexão com SQLite (abre em modo row_factory p/ permitir dict-like)
def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Consulta única
def query_one(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    conn.close()
    return row

# Consulta múltipla
def query_all(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows

# Executa INSERT/UPDATE/DELETE
def execute(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id



# --------------------------------------------------------
# ------------------- Rotas Públicas ---------------------
# --------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Registro de novo usuário
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")

        if not nome or not email or not senha:
            flash("Preencha todos os campos.", "error")
            return redirect("/register")

        hashed = generate_password_hash(senha)

        try:
            execute(
                "INSERT INTO usuarios (nome, email, senha, tipo, eco_balance) VALUES (?, ?, ?, ?, ?)",
                (nome, email, hashed, "user", 0)
            )
            flash("Conta criada com sucesso! Faça login.", "success")
            return redirect("/login")
        except Exception as e:
            flash("Erro ao criar conta: " + str(e), "error")
            return redirect("/register")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Login de usuário
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        if not email or not senha:
            flash("Preencha email e senha.", "error")
            return redirect("/login")

        user = query_one("SELECT * FROM usuarios WHERE email = ?", (email,))

        if user and check_password_hash(user["senha"], senha):
            # Guarda ID, nome e tipo na sessão
            session["user"] = {"id": user["id"], "nome": user["nome"], "tipo": user["tipo"]}
            return redirect("/dashboard")

        flash("Usuário ou senha inválidos.", "error")
        return redirect("/login")

    return render_template("login.html")


@app.route("/logout")
def logout():
    # Encerrar sessão
    session.clear()
    return redirect("/")



# --------------------------------------------------------
# ---------------- Dashboard do Usuário ------------------
# --------------------------------------------------------

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    # Admin vai direto para painel admin
    if session["user"]["tipo"] == "admin":
        return redirect("/admin")

    # Busca dados do usuário
    user = query_one("SELECT id, nome, eco_balance FROM usuarios WHERE id = ?", (session["user"]["id"],))

    # Últimos descartes e pesagens
    descartes = query_all("SELECT * FROM descarte WHERE usuario_id = ? ORDER BY data DESC LIMIT 10", (user["id"],))
    pesagens_pendentes = query_all("SELECT * FROM pesagens WHERE user_id = ? ORDER BY data DESC LIMIT 10", (user["id"],))

    return render_template("dashboard.html", user=user, descartes=descartes, pesagens=pesagens_pendentes)



# --------------------------------------------------------
# ------------ Registrar Pesagem (Pendentes) -------------
# --------------------------------------------------------

@app.route('/registrar_pesagem', methods=['POST'])
def registrar_pesagem():
    if 'user' not in session:
        return redirect('/login')

    peso_raw = request.form.get('peso')
    pin = request.form.get('pin')

    # Validar peso
    try:
        peso = float(peso_raw)
        if peso <= 0:
            raise ValueError
    except:
        flash("Peso inválido.", "error")
        return redirect('/dashboard')

    # Verificar PIN do ponto de coleta
    ponto = query_one("SELECT * FROM pontos_coleta WHERE pin = ?", (pin,))
    if not ponto:
        flash("PIN incorreto. Apenas pontos válidos.", "error")
        return redirect('/dashboard')

    # Conversão para EcoMoedas
    fator = 10
    eco = int(peso * fator)

    try:
        execute("""
            INSERT INTO pesagens (user_id, peso, eco_moedas, status)
            VALUES (?, ?, ?, 'pendente')
        """, (session['user']['id'], peso, eco))

        flash(f"Pesagem registrada no ponto {ponto['nome']}. Aguarde validação.", "success")

    except Exception as e:
        flash("Erro ao registrar pesagem: " + str(e), "error")

    return redirect('/dashboard')



# --------------------------------------------------------
# -------- Registrar Descarte Direto (histórico) --------
# --------------------------------------------------------

@app.route("/registrar_descarte", methods=["GET", "POST"])
def registrar_descarte():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        material = request.form.get("material", "N/A")

        try:
            peso = float(request.form.get("peso", 0))
        except ValueError:
            flash("Peso inválido.", "error")
            return redirect("/registrar_descarte")

        if peso <= 0:
            flash("Informe peso maior que 0.", "error")
            return redirect("/registrar_descarte")

        fator = 10
        eco = int(peso * fator)

        try:
            # Insere no histórico
            execute(
                "INSERT INTO descarte (usuario_id, material, peso, eco_moedas) VALUES (?, ?, ?, ?)",
                (session["user"]["id"], material, peso, eco)
            )
            # Atualiza saldo
            execute("UPDATE usuarios SET eco_balance = eco_balance + ? WHERE id = ?", (eco, session["user"]["id"]))

            flash(f"Descarte registrado! +{eco} EcoMoedas.", "success")
            return redirect("/dashboard")

        except Exception as e:
            flash("Erro ao registrar descarte: " + str(e), "error")
            return redirect("/registrar_descarte")

    return render_template("registrar_descarte.html")



# --------------------------------------------------------
# ------------------ Campanhas (posts) -------------------
# --------------------------------------------------------

@app.route("/campanhas", methods=["GET", "POST"])
def campanhas():
    # Criar campanha
    if request.method == "POST":
        if "user" not in session:
            flash("Faça login.", "error")
            return redirect("/login")

        titulo = request.form.get("titulo")
        descricao = request.form.get("descricao")

        try:
            execute("INSERT INTO campanhas (titulo, descricao, autor_id) VALUES (?, ?, ?)",
                    (titulo, descricao, session["user"]["id"]))

            flash("Campanha criada.", "success")
            return redirect("/campanhas")

        except Exception as e:
            flash("Erro ao criar campanha: " + str(e), "error")
            return redirect("/campanhas")

    # Lista campanhas
    posts = query_all("""
        SELECT c.*, u.nome as autor
        FROM campanhas c
        LEFT JOIN usuarios u ON c.autor_id = u.id
        ORDER BY c.data DESC
    """)

    return render_template("campanhas.html", posts=posts)



# --------------------------------------------------------
# ----------- Recompensas / Resgates / Solicitações ------
# --------------------------------------------------------

@app.route("/recompensas")
def recompensas():
    items = query_all("SELECT * FROM recompensas ORDER BY id DESC")
    return render_template("recompensas.html", items=items)



@app.route("/resgatar_direct/<int:reward_id>", methods=["POST"])
def resgatar_direct(reward_id):
    # Resgatar de forma instantânea
    if "user" not in session:
        return redirect("/login")

    user = query_one("SELECT id, eco_balance FROM usuarios WHERE id = ?", (session["user"]["id"],))
    reward = query_one("SELECT * FROM recompensas WHERE id = ?", (reward_id,))

    if not reward:
        flash("Recompensa inválida.", "error")
        return redirect("/recompensas")

    if user["eco_balance"] < reward["custo"]:
        flash("Saldo insuficiente.", "error")
        return redirect("/recompensas")

    try:
        # Debita saldo
        execute("UPDATE usuarios SET eco_balance = eco_balance - ? WHERE id = ?", (reward["custo"], user["id"]))

        # Registra resgate
        execute("INSERT INTO resgates (usuario_id, recompensa_id, codigo_usado) VALUES (?, ?, ?)",
                (user["id"], reward_id, reward["codigo"]))

        flash(f"Recompensa resgatada! Código: {reward['codigo']}", "success")

    except Exception as e:
        flash("Erro ao resgatar: " + str(e), "error")

    return redirect("/dashboard")



@app.route("/solicitar_recompensa/<int:reward_id>", methods=["POST"])
def solicitar_recompensa(reward_id):
    # Envia solicitação para admin aprovar
    if "user" not in session:
        return redirect("/login")

    try:
        execute("INSERT INTO solicitacoes_recompensas (user_id, recompensa_id, status) VALUES (?, ?, ?)",
                (session["user"]["id"], reward_id, "pendente"))

        flash("Solicitação enviada! Aguarde aprovação.", "success")

    except Exception as e:
        flash("Erro ao solicitar recompensa: " + str(e), "error")

    return redirect("/recompensas")



# --------------------------------------------------------
# ---------------------- ADMIN ---------------------------
# --------------------------------------------------------

@app.route("/admin")
def admin():
    # Painel administrativo
    if "user" not in session or session["user"]["tipo"] != "admin":
        return redirect("/login")

    usuarios = query_all("SELECT id, nome, email, eco_balance, tipo FROM usuarios ORDER BY id")
    pontos = query_all("SELECT * FROM pontos_coleta ORDER BY id")
    recompensas = query_all("SELECT * FROM recompensas ORDER BY id")
    solicitacoes = query_all("SELECT * FROM solicitacoes_recompensas WHERE status = 'pendente' ORDER BY data DESC")
    pesagens = query_all("""
        SELECT p.id, p.user_id, u.nome as nome, p.peso, p.eco_moedas, p.status, p.data
        FROM pesagens p JOIN usuarios u ON p.user_id = u.id
        WHERE p.status = 'pendente'
        ORDER BY p.data DESC
    """)

    return render_template("admin.html",
                           usuarios=usuarios,
                           pontos=pontos,
                           recompensas=recompensas,
                           solicitacoes=solicitacoes,
                           pesagens=pesagens)


# ---------- Aprovar recompensa ----------
@app.route("/admin/aprovar_recompensa/<int:sol_id>", methods=["POST", "GET"])
def admin_aprovar_recompensa(sol_id):
    if "user" not in session or session["user"]["tipo"] != "admin":
        flash("Acesso negado.", "error")
        return redirect("/")

    s = query_one("SELECT * FROM solicitacoes_recompensas WHERE id = ?", (sol_id,))
    if not s:
        flash("Solicitação não encontrada.", "error")
        return redirect("/admin")

    r = query_one("SELECT * FROM recompensas WHERE id = ?", (s["recompensa_id"],))
    if not r:
        flash("Recompensa não encontrada.", "error")
        return redirect("/admin")

    u = query_one("SELECT eco_balance FROM usuarios WHERE id = ?", (s["user_id"],))
    if not u:
        flash("Usuário não encontrado.", "error")
        return redirect("/admin")

    if u["eco_balance"] < r["custo"]:
        flash("Saldo insuficiente.", "error")
        return redirect("/admin")

    try:
        # Debitar moedas
        execute("UPDATE usuarios SET eco_balance = eco_balance - ? WHERE id = ?", (r["custo"], s["user_id"]))
        # Marcar aprovada
        execute("UPDATE solicitacoes_recompensas SET status = 'aprovada' WHERE id = ?", (sol_id,))
        # Registrar resgate
        execute("INSERT INTO resgates (usuario_id, recompensa_id, codigo_usado) VALUES (?, ?, ?)",
                (s["user_id"], s["recompensa_id"], r["codigo"]))

        flash("Recompensa aprovada.", "success")

    except Exception as e:
        flash("Erro ao aprovar recompensa: " + str(e), "error")

    return redirect("/admin")



# ---------- Recusar recompensa ----------
@app.route("/admin/recusar_recompensa/<int:sol_id>", methods=["POST", "GET"])
def admin_recusar_recompensa(sol_id):
    if "user" not in session or session["user"]["tipo"] != "admin":
        flash("Acesso negado.", "error")
        return redirect("/")

    try:
        execute("UPDATE solicitacoes_recompensas SET status = 'recusada' WHERE id = ?", (sol_id,))
        flash("Solicitação recusada.", "success")
    except Exception as e:
        flash("Erro ao recusar: " + str(e), "error")

    return redirect("/admin")



# ---------- Validar Pesagem ----------
@app.route("/admin/validar_pesagem/<int:pes_id>", methods=["POST", "GET"])
def admin_validar_pesagem(pes_id):
    if "user" not in session or session["user"]["tipo"] != "admin":
        flash("Acesso negado.", "error")
        return redirect("/")

    p = query_one("SELECT * FROM pesagens WHERE id = ?", (pes_id,))
    if not p:
        flash("Pesagem não encontrada.", "error")
        return redirect("/admin")

    if p["status"] != "pendente":
        flash("Pesagem não está pendente.", "info")
        return redirect("/admin")

    try:
        # Atualizar saldo do usuário
        execute("UPDATE usuarios SET eco_balance = eco_balance + ? WHERE id = ?", (p["eco_moedas"], p["user_id"]))

        # Marcar como validada
        execute("UPDATE pesagens SET status = 'validada' WHERE id = ?", (pes_id,))

        # Inserir no histórico
        execute("INSERT INTO descarte (usuario_id, material, peso, eco_moedas) VALUES (?, ?, ?, ?)",
                (p["user_id"], "N/A", p["peso"], p["eco_moedas"]))

        flash("Pesagem validada.", "success")

    except Exception as e:
        flash("Erro ao validar pesagem: " + str(e), "error")

    return redirect("/admin")



# ---------- Recusar Pesagem ----------
@app.route("/admin/recusar_pesagem/<int:pes_id>", methods=["POST", "GET"])
def admin_recusar_pesagem(pes_id):
    if "user" not in session or session["user"]["tipo"] != "admin":
        flash("Acesso negado.", "error")
        return redirect("/")

    try:
        execute("UPDATE pesagens SET status = 'recusada' WHERE id = ?", (pes_id,))
        flash("Pesagem recusada.", "success")
    except Exception as e:
        flash("Erro ao recusar pesagem: " + str(e), "error")

    return redirect("/admin")



# ---------- Admin: adicionar ponto ----------
@app.route("/admin/pontos/add", methods=["POST"])
def admin_pontos_add():
    if "user" not in session or session["user"]["tipo"] != "admin":
        return redirect("/login")

    nome = request.form["nome"]
    endereco = request.form["endereco"]
    cidade = request.form["cidade"]
    contato = request.form.get("contato", "")
    pin = request.form["pin"]

    execute("""
        INSERT INTO pontos_coleta (nome, endereco, cidade, contato, pin)
        VALUES (?, ?, ?, ?, ?)
    """, (nome, endereco, cidade, contato, pin))

    flash("Ponto adicionado!", "success")
    return redirect("/admin")



# ---------- Admin: adicionar recompensa ----------
@app.route("/admin/recompensa/add", methods=["POST"])
def admin_add_recompensa():
    if "user" not in session or session["user"]["tipo"] != "admin":
        flash("Acesso negado.", "error")
        return redirect("/login")

    titulo = request.form.get("titulo")
    descricao = request.form.get("descricao")
    custo = int(request.form.get("custo") or 0)
    codigo = request.form.get("codigo") or f"C-{titulo[:4].upper()}"

    try:
        execute("INSERT INTO recompensas (titulo, descricao, custo, codigo) VALUES (?, ?, ?, ?)",
                (titulo, descricao, custo, codigo))
        flash("Recompensa criada.", "success")

    except Exception as e:
        flash("Erro ao criar recompensa: " + str(e), "error")

    return redirect("/admin#recompensas")



# ---------- Admin: Relatório de Reciclagem ----------
@app.route("/admin/reciclagem")
def admin_reciclagem():
    if "user" not in session or session["user"]["tipo"] != "admin":
        return redirect("/login")

    total_row = query_one("SELECT SUM(eco_moedas) AS total FROM descarte")
    total_moedas = total_row["total"] if total_row and total_row["total"] is not None else 0

    por_material = query_all("""
        SELECT material, SUM(peso) AS total_peso, SUM(eco_moedas) AS total_moedas
        FROM descarte
        GROUP BY material
    """)

    return render_template("admin_reciclagem.html", total_moedas=total_moedas, por_material=por_material)



# ---------- Admin: Relatórios Gerais ----------
@app.route("/admin/relatorios")
def admin_relatorios():
    if "user" not in session or session["user"]["tipo"] != "admin":
        return redirect("/login")

    usuarios = query_all("SELECT id, nome, eco_balance FROM usuarios ORDER BY eco_balance DESC")
    descartes = query_all("SELECT * FROM descarte ORDER BY data DESC")

    return render_template("admin_relatorios.html", usuarios=usuarios, descartes=descartes)



# --------------------------------------------------------
# ---------------------- Rodar App -----------------------
# --------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
