import sqlite3

def get_connection():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row   # permite acessar colunas por nome
    return conn
