from pricing.db import Database
from pricing.engine import suggest_sale_price, get_base_cost

db = Database()
db.seed_demo()
conn = db.connect()
base = get_base_cost(conn, 1)
res = suggest_sale_price(conn, 1, 1, 25)
print("BASE:", {k: float(v) for k, v in base.items()})
print("PRECO_VENDA:", float(res["preco_venda"]))
print("MARGEM_REAL_PERCENT:", float(res["margem_real_percent"]))
print("IMPOSTOS_VALOR:", float(res["impostos_valor"]))
