import sqlite3
from decimal import Decimal, ROUND_HALF_UP

def _d(x):
    return Decimal(str(x))

def get_base_cost(conn, product_id):
    cur = conn.cursor()
    cur.execute("""SELECT mu.quantidade, vm.preco_unitario FROM materials_usage mu JOIN vertical_materials vm ON mu.material_id=vm.id WHERE mu.product_id=?""", (product_id,))
    custo_materiais = sum((_d(r[0]) * _d(r[1]) for r in cur.fetchall()), _d(0))
    cur.execute("""SELECT pu.horas, vp.preco_unitario_hora FROM processes_usage pu JOIN vertical_processes vp ON pu.process_id=vp.id WHERE pu.product_id=?""", (product_id,))
    custo_processos = sum((_d(r[0]) * _d(r[1]) for r in cur.fetchall()), _d(0))
    cur.execute("""SELECT tu.quantidade, tp.preco_unitario FROM third_usage tu JOIN third_party_items tp ON tu.third_id=tp.id WHERE tu.product_id=?""", (product_id,))
    custo_terceiros = sum((_d(r[0]) * _d(r[1]) for r in cur.fetchall()), _d(0))
    
    # Recursive cost for sub-components (conjuntos)
    cur.execute("SELECT component_product_id, quantidade FROM product_components WHERE parent_product_id=?", (product_id,))
    components = cur.fetchall()
    custo_componentes_materiais = _d(0)
    custo_componentes_processos = _d(0)
    custo_componentes_terceiros = _d(0)
    
    for comp in components:
        comp_id = comp[0]
        comp_qty = _d(comp[1])
        # Recursive call
        comp_cost = get_base_cost(conn, comp_id)
        custo_componentes_materiais += comp_cost["materiais"] * comp_qty
        custo_componentes_processos += comp_cost["processos"] * comp_qty
        custo_componentes_terceiros += comp_cost["terceiros"] * comp_qty

    total_materiais = custo_materiais + custo_componentes_materiais
    total_processos = custo_processos + custo_componentes_processos
    total_terceiros = custo_terceiros + custo_componentes_terceiros

    cur.execute("SELECT SUM(valor) FROM admin_costs")
    v = cur.fetchone()[0]
    custo_admin = _d(v or 0)
    
    # admin cost is usually not recursive if it's a fixed value, but if it's percentage it's calculated later.
    # We will exclude fixed admin cost from recursion to avoid double counting if it's per product? 
    # Actually, for sub-assemblies, admin cost might be already included? 
    # Let's keep the logic simple: Roll up direct costs (Mat, Proc, Third). Admin/Markup is applied at top level or per level?
    # Usually overheads are applied at the finished good level. 
    # So we only roll up Mat, Proc, Third.

    custo_sem_impostos = total_materiais + total_processos + total_terceiros + custo_admin
    return {
        "materiais": total_materiais,
        "processos": total_processos,
        "terceiros": total_terceiros,
        "administrativos": custo_admin,
        "sem_impostos": custo_sem_impostos,
        "own_materiais": custo_materiais, # Keep track of own vs components if needed
        "own_processos": custo_processos,
        "own_terceiros": custo_terceiros
    }

def _tax_rate_for_product(conn, product_id, client_id):
    cur = conn.cursor()
    cur.execute("SELECT destino_uf, ncm, local_fabricacao_uf FROM products WHERE id=?", (product_id,))
    p = cur.fetchone()
    destino_uf = p["destino_uf"]
    ncm = p["ncm"]
    origem_uf = p["local_fabricacao_uf"]
    cur.execute("SELECT regime, pis, cofins, icms FROM clients WHERE id=?", (client_id,))
    c = cur.fetchone()
    regime = c["regime"]
    pis = _d(c["pis"])
    cofins = _d(c["cofins"])
    icms = _d(c["icms"])
    cur.execute("SELECT pis, cofins, icms FROM ncm_taxes WHERE ncm=?", (ncm,))
    r = cur.fetchone()
    if r:
        pis = _d(r["pis"])
        cofins = _d(r["cofins"])
        icms = _d(r["icms"])
    if origem_uf != destino_uf:
        icms = _d("0.12")
    total = pis + cofins + icms
    return {"pis": pis, "cofins": cofins, "icms": icms, "total": total, "regime": regime}

def suggest_sale_price(conn, product_id, client_id, margem_percentual, admin_pct=0.0, frete_pct=0.0, outros_pct=0.0):
    base_bruto = get_base_cost(conn, product_id)
    base_core = base_bruto["materiais"] + base_bruto["processos"] + base_bruto["terceiros"]
    perc_total = _d(admin_pct) + _d(frete_pct) + _d(outros_pct)
    custo_admin_calc = (base_core * (perc_total / _d(100))) if perc_total > _d(0) else base_bruto["administrativos"]
    custo_sem_impostos = base_core + custo_admin_calc
    base = {
        "materiais": base_bruto["materiais"],
        "processos": base_bruto["processos"],
        "terceiros": base_bruto["terceiros"],
        "administrativos": custo_admin_calc,
        "sem_impostos": custo_sem_impostos,
    }
    taxa = _tax_rate_for_product(conn, product_id, client_id)
    margem = _d(margem_percentual) / _d(100)
    preco = base["sem_impostos"] / (_d(1) - margem - taxa["total"])
    impostos_valor = preco * taxa["total"]
    margem_real = (preco - base["sem_impostos"] - impostos_valor) / preco * _d(100)
    return {
        "preco_venda": preco.quantize(_d("0.01"), rounding=ROUND_HALF_UP),
        "margem_real_percent": margem_real.quantize(_d("0.01"), rounding=ROUND_HALF_UP),
        "impostos_valor": impostos_valor.quantize(_d("0.01"), rounding=ROUND_HALF_UP),
        "base": {k: (v if isinstance(v, Decimal) else _d(v)).quantize(_d("0.01"), rounding=ROUND_HALF_UP) for k, v in base.items()},
        "taxas": {k: (v if isinstance(v, str) else v.quantize(_d("0.0001"))) for k, v in taxa.items() if k != "regime"},
        "regime": taxa["regime"],
    }

def import_planilha_processos(conn, rows):
    cur = conn.cursor()
    for r in rows:
        cur.execute(
            "INSERT INTO vertical_processes (grupo, subgrupo, nome, preco_unitario_hora, unidade, origem) VALUES (?,?,?,?,?,?)",
            (r.get("grupo") or "", r.get("subgrupo") or "", r["nome"], float(r["preco_unitario_hora"]), r.get("unidade") or "hora", "Planilha 1")
        )
    conn.commit()
