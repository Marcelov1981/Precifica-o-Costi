from pricing.db import Database
from pricing.auth import hash_password

db = Database()
conn = db.connect()
email = "admin@costi.com"
senha = "admin"
senha_hash = hash_password(senha)

# Check if user exists
cur = conn.cursor()
cur.execute("SELECT id FROM users WHERE email=?", (email,))
if not cur.fetchone():
    db.add_user("Admin", email, senha_hash, "admin")
    print(f"Usuário criado: {email} / {senha}")
else:
    print(f"Usuário já existe: {email}")

conn.close()
