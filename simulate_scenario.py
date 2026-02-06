import sqlite3
import pandas as pd
from pricing.db import Database
from pricing.engine import suggest_sale_price, get_base_cost

def run_simulation():
    print("=== Iniciando Simulação de Conjuntos e Vínculos ===")
    
    # Setup DB
    db = Database("test_sim.db")
    db.init_schema()
    db.seed_demo() # Ensure defaults (run before opening main connection to avoid lock)
    conn = db.connect()
    
    # 1. Create Component Product (Part A)
    print("\n1. Criando Componente A...")
    conn.execute("INSERT INTO products (codigo, nome, quantidade, destino_uf, ncm, local_fabricacao_uf) VALUES (?,?,?,?,?,?)",
                 ("COMP01", "Componente A", 10, "SP", "7208.38.90", "SP"))
    comp_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    
    # Add materials to Component A (Cost = 10 * 8.5 = 85.0)
    # Ensure material exists
    mat_id = conn.execute("SELECT id FROM vertical_materials LIMIT 1").fetchone()[0]
    db.add_material_usage(comp_id, mat_id, 10.0) 
    print(f"Componente A (ID {comp_id}) criado com custo material base.")

    # 2. Create Set Product (Conjunto B)
    print("\n2. Criando Conjunto B...")
    conn.execute("INSERT INTO products (codigo, nome, quantidade, destino_uf, ncm, local_fabricacao_uf) VALUES (?,?,?,?,?,?)",
                 ("CONJ01", "Conjunto B", 1, "SP", "7208.38.90", "SP"))
    set_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    
    # Add Component A to Set B (Qty 2) -> Cost should be 2 * Cost(A)
    print("Adicionando 2x Componente A ao Conjunto B...")
    db.add_component_usage(set_id, comp_id, 2.0)
    
    # Also add some direct process cost to Set B
    proc_id = conn.execute("SELECT id FROM vertical_processes LIMIT 1").fetchone()[0]
    db.add_process_usage(set_id, proc_id, 5.0) # 5 hours * 120 = 600.0
    print("Adicionando 5h de processo ao Conjunto B.")

    # 3. Calculate Cost of Set B
    print("\n3. Calculando Custo Base do Conjunto B...")
    base_cost = get_base_cost(conn, set_id)
    print(f"Custo Materiais (Recursivo): {base_cost['materiais']}") # Should be 2 * (10 * 8.5) = 170.0 (if mat cost is 8.5)
    print(f"Custo Processos: {base_cost['processos']}") # Should be 600.0
    print(f"Custo Total Sem Impostos: {base_cost['sem_impostos']}")
    
    # Verify values
    # Material cost from seed_demo is 8.5/kg. Component A uses 10kg = 85.0. Set B uses 2 * A = 170.0.
    # Process cost from seed_demo is 120.0/h. Set B uses 5h = 600.0.
    # Total direct = 170 + 600 = 770.0 (plus admin if any)
    
    # 4. Simulate Pricing for Client X
    print("\n4. Orçando para Cliente Demo...")
    client_id = conn.execute("SELECT id FROM clients LIMIT 1").fetchone()[0]
    price_res = suggest_sale_price(conn, set_id, client_id, margem_percentual=30.0)
    print(f"Preço Sugerido (30% margem): R$ {price_res['preco_venda']}")
    
    # 5. Link/Save Quote
    print("\n5. Salvando Orçamento...")
    db.link_product_client(set_id, client_id, 30.0, float(price_res['preco_venda']))
    
    # Verify Link
    link = conn.execute("SELECT * FROM product_clients WHERE product_id=? AND client_id=?", (set_id, client_id)).fetchone()
    print(f"Vínculo Salvo: Margem={link['margem']}%, Preço=R${link['preco_final']}")

    print("\n=== Simulação Concluída com Sucesso ===")
    
    conn.close()
    # Clean up
    import os
    if os.path.exists("test_sim.db"):
        os.remove("test_sim.db")

if __name__ == "__main__":
    run_simulation()
