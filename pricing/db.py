import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, path=None):
        self.path = path or os.path.join(os.getcwd(), "precificacao.db")
        self._ensure_db()
        self.init_schema()

    def _ensure_db(self):
        if not os.path.exists(self.path):
            conn = sqlite3.connect(self.path)
            conn.close()

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS vertical_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo TEXT,
            subgrupo TEXT,
            nome TEXT,
            ncm TEXT,
            unidade TEXT,
            preco_unitario REAL,
            fornecedor TEXT,
            data_atualizacao TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS vertical_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo TEXT,
            subgrupo TEXT,
            nome TEXT,
            preco_unitario_hora REAL,
            unidade TEXT,
            origem TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS third_party_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            preco_unitario REAL,
            quantidade_padrao REAL,
            fornecedor TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            valor REAL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            planta TEXT,
            uf TEXT,
            cidade TEXT,
            regime TEXT,
            pis REAL,
            cofins REAL,
            icms REAL,
            fator REAL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS ncm_taxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ncm TEXT,
            pis REAL,
            cofins REAL,
            icms REAL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT,
            nome TEXT,
            quantidade REAL,
            destino_uf TEXT,
            ncm TEXT,
            local_fabricacao_uf TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS product_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            client_id INTEGER
        )
        """)
        cur.execute("PRAGMA table_info(products)")
        cols = [r[1] for r in cur.fetchall()]
        if "codigo" not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN codigo TEXT")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS materials_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            material_id INTEGER,
            quantidade REAL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS processes_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            process_id INTEGER,
            horas REAL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS third_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            third_id INTEGER,
            quantidade REAL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT UNIQUE,
            senha_hash TEXT,
            role TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            data_hora TEXT,
            observacao TEXT,
            status TEXT
        )
        """)
        conn.commit()
        conn.close()

    def seed_demo(self):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM vertical_materials")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO vertical_materials (grupo, subgrupo, nome, ncm, unidade, preco_unitario, fornecedor, data_atualizacao) VALUES (?,?,?,?,?,?,?,?)",
                ("Aço", "Chapas", "Chapa A36 3mm", "7208.38.90", "kg", 8.5, "Fornecedor X", datetime.now().strftime("%Y-%m-%d"))
            )
        cur.execute("SELECT COUNT(*) FROM vertical_processes")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO vertical_processes (grupo, subgrupo, nome, preco_unitario_hora, unidade, origem) VALUES (?,?,?,?,?,?)",
                ("Usinagem", "CNC", "Fresamento CNC", 120.0, "hora", "Planilha 1")
            )
        cur.execute("SELECT COUNT(*) FROM third_party_items")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO third_party_items (nome, preco_unitario, quantidade_padrao, fornecedor) VALUES (?,?,?,?)",
                ("Tratamento térmico", 300.0, 1, "Terceiro Y")
            )
        cur.execute("SELECT COUNT(*) FROM admin_costs")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO admin_costs (nome, valor) VALUES (?,?)",
                ("Frete", 500.0)
            )
        cur.execute("SELECT COUNT(*) FROM clients")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO clients (nome, planta, uf, cidade, regime, pis, cofins, icms, fator) VALUES (?,?,?,?,?,?,?,?,?)",
                ("Cliente Demo", "Planta 1", "SP", "São Paulo", "real", 0.0165, 0.076, 0.12, 1.0)
            )
        cur.execute("SELECT COUNT(*) FROM ncm_taxes")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO ncm_taxes (ncm, pis, cofins, icms) VALUES (?,?,?,?)",
                ("7208.38.90", 0.0165, 0.076, 0.12)
            )
        cur.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO products (codigo, nome, quantidade, destino_uf, ncm, local_fabricacao_uf) VALUES (?,?,?,?,?,?)",
                ("PRD-0001", "Conjunto Mecânico", 1, "SP", "8421.99.90", "SP")
            )
            product_id = cur.lastrowid
            cur.execute("SELECT id FROM vertical_materials LIMIT 1")
            material_id = cur.fetchone()[0]
            cur.execute("INSERT INTO materials_usage (product_id, material_id, quantidade) VALUES (?,?,?)", (product_id, material_id, 150))
            cur.execute("SELECT id FROM vertical_processes LIMIT 1")
            process_id = cur.fetchone()[0]
            cur.execute("INSERT INTO processes_usage (product_id, process_id, horas) VALUES (?,?,?)", (product_id, process_id, 12))
            cur.execute("SELECT id FROM third_party_items LIMIT 1")
            third_id = cur.fetchone()[0]
            cur.execute("INSERT INTO third_usage (product_id, third_id, quantidade) VALUES (?,?,?)", (product_id, third_id, 1))
        conn.commit()
        conn.close()

    def add_product(self, codigo, nome, quantidade, destino_uf, ncm, local_fabricacao_uf):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (codigo, nome, quantidade, destino_uf, ncm, local_fabricacao_uf) VALUES (?,?,?,?,?,?)",
            (codigo, nome, quantidade, destino_uf, ncm, local_fabricacao_uf)
        )
        conn.commit()
        pid = cur.lastrowid
        conn.close()
        return pid

    def update_product(self, product_id, codigo, nome, quantidade, destino_uf, ncm, local_fabricacao_uf):
        conn = self.connect()
        conn.execute(
            "UPDATE products SET codigo=?, nome=?, quantidade=?, destino_uf=?, ncm=?, local_fabricacao_uf=? WHERE id=?",
            (codigo, nome, quantidade, destino_uf, ncm, local_fabricacao_uf, product_id)
        )
        conn.commit()
        conn.close()

    def delete_product_cascade(self, product_id):
        conn = self.connect()
        conn.execute("DELETE FROM materials_usage WHERE product_id=?", (product_id,))
        conn.execute("DELETE FROM processes_usage WHERE product_id=?", (product_id,))
        conn.execute("DELETE FROM third_usage WHERE product_id=?", (product_id,))
        conn.execute("DELETE FROM product_clients WHERE product_id=?", (product_id,))
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        conn.close()

    def add_material_usage(self, product_id, material_id, quantidade):
        conn = self.connect()
        conn.execute("INSERT INTO materials_usage (product_id, material_id, quantidade) VALUES (?,?,?)", (product_id, material_id, quantidade))
        conn.commit()
        conn.close()

    def add_process_usage(self, product_id, process_id, horas):
        conn = self.connect()
        conn.execute("INSERT INTO processes_usage (product_id, process_id, horas) VALUES (?,?,?)", (product_id, process_id, horas))
        conn.commit()
        conn.close()

    def add_third_usage(self, product_id, third_id, quantidade):
        conn = self.connect()
        conn.execute("INSERT INTO third_usage (product_id, third_id, quantidade) VALUES (?,?,?)", (product_id, third_id, quantidade))
        conn.commit()
        conn.close()

    def clear_composition(self, product_id):
        conn = self.connect()
        conn.execute("DELETE FROM materials_usage WHERE product_id=?", (product_id,))
        conn.execute("DELETE FROM processes_usage WHERE product_id=?", (product_id,))
        conn.execute("DELETE FROM third_usage WHERE product_id=?", (product_id,))
        conn.commit()
        conn.close()

    def link_product_client(self, product_id, client_id):
        conn = self.connect()
        conn.execute("INSERT INTO product_clients (product_id, client_id) VALUES (?,?)", (product_id, client_id))
        conn.commit()
        conn.close()

    def unlink_product_client(self, product_id, client_id):
        conn = self.connect()
        conn.execute("DELETE FROM product_clients WHERE product_id=? AND client_id=?", (product_id, client_id))
        conn.commit()
        conn.close()

    def get_products_by_client(self, client_id):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("""SELECT p.id, p.codigo, p.nome FROM products p 
                       JOIN product_clients pc ON pc.product_id=p.id 
                       WHERE pc.client_id=?""", (client_id,))
        rows = cur.fetchall()
        conn.close()
        return rows

    def add_user(self, nome, email, senha_hash, role="cliente"):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (nome, email, senha_hash, role) VALUES (?,?,?,?)", (nome, email, senha_hash, role))
        conn.commit()
        uid = cur.lastrowid
        conn.close()
        return uid

    def get_user_by_email(self, email):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT id, nome, email, senha_hash, role FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        conn.close()
        return row

    def add_appointment(self, user_id, data_hora, observacao, status="pendente"):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("INSERT INTO appointments (user_id, data_hora, observacao, status) VALUES (?,?,?,?)", (user_id, data_hora, observacao, status))
        conn.commit()
        aid = cur.lastrowid
        conn.close()
        return aid

    def list_appointments(self, user_id=None):
        conn = self.connect()
        if user_id:
            df = conn.execute("SELECT id, user_id, data_hora, observacao, status FROM appointments WHERE user_id=?", (user_id,)).fetchall()
        else:
            df = conn.execute("SELECT id, user_id, data_hora, observacao, status FROM appointments").fetchall()
        conn.close()
        return df
