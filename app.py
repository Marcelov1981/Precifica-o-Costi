import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from io import BytesIO
from pricing.db import Database
from pricing.engine import import_planilha_processos, suggest_sale_price, get_base_cost
from pricing.auth import hash_password, verify_password, is_master_password
import os

st.set_page_config(page_title="Módulo de Precificação", layout="wide")

@st.cache_resource
def get_db():
    db = Database()
    db.seed_demo()
    return db

db = get_db()
db.init_schema()
conn = db.connect()
conn.execute("CREATE TABLE IF NOT EXISTS product_clients (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, client_id INTEGER)")

st.title("Módulo de Precificação")
tab_access, tab2, tab_prod, tab3, tab_upload = st.tabs(["Acesso & Agendamentos", "Cadastros", "Produtos", "Precificação", "UpLoad de arquivos"])

with tab_upload:
    if not st.session_state.get("usuario"):
        st.warning("Acesso restrito. Faça login na aba 'Acesso & Agendamentos'.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            f = st.file_uploader("Anexe arquivo ERP (XLSX/CSV)", type=["xlsx", "csv"], key="upl_file")
            if f:
                df = pd.read_excel(f) if f.name.endswith(".xlsx") else pd.read_csv(f)
                cols = [str(c) for c in df.columns]
                lc = [c.lower() for c in cols]
                def pick(colset):
                    for k in colset:
                        for i, c in enumerate(lc):
                            if k in c:
                                return cols[i]
                    return None
                is_materials = any("insumo" in x or "matéria" in x or "materia" in x for x in lc) or (pick({"nome_insumo","insumo"}) is not None and pick({"custo_unit","custo_unitario","preco_unitario"}) is not None)
                if is_materials:
                    nome_c = pick({"nome_insumo","insumo","nome"})
                    preco_c = pick({"custo_unitario","preco_unitario","valor_unitario"})
                    qtd_c = pick({"quantidade","qtde","qtd"})
                    forn_c = pick({"fornecedor"})
                    grupo_c = pick({"grupo"})
                    subgrupo_c = pick({"subgrupo"})
                    unidade_c = pick({"unidade","unit"})
                    ncm_c = pick({"ncm"})
                    mdf = pd.DataFrame({
                        "grupo": df[grupo_c] if grupo_c else "",
                        "subgrupo": df[subgrupo_c] if subgrupo_c else "",
                        "nome": df[nome_c] if nome_c else df[cols[0]],
                        "ncm": df[ncm_c] if ncm_c else "",
                        "unidade": df[unidade_c] if unidade_c else "un",
                        "preco_unitario": df[preco_c] if preco_c else 0.0,
                        "fornecedor": df[forn_c] if forn_c else "",
                    })
                mdf_edit = st.data_editor(mdf, num_rows="dynamic", column_config={"preco_unitario": st.column_config.NumberColumn("preco_unitario", format="%.2f")})
                if st.button("Salvar e importar materiais"):
                    cur = conn.cursor()
                    for _, r in mdf_edit.fillna("").iterrows():
                        cur.execute("INSERT INTO vertical_materials (grupo, subgrupo, nome, ncm, unidade, preco_unitario, fornecedor, data_atualizacao) VALUES (?,?,?,?,?,?,?,?)",
                                        (r["grupo"], r["subgrupo"], r["nome"], r["ncm"], r["unidade"], round(float(r["preco_unitario"]) if r["preco_unitario"] != "" else 0.0, 2), r["fornecedor"], pd.Timestamp.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Materiais importados")
                else:
                    nome_c = pick({"nome","processo","operacao"})
                    preco_h_c = pick({"preco_hora","valor_hora","custo_hora"})
                    preco_min_c = pick({"preco_minuto","valor_minuto","custo_minuto"})
                    grupo_c = pick({"grupo"})
                    subgrupo_c = pick({"subgrupo"})
                    unidade_c = pick({"unidade","unit"})
                    if preco_h_c is None and preco_min_c is not None:
                        df["__preco_hora__"] = df[preco_min_c].astype(float) * 60.0
                        preco_h_c = "__preco_hora__"
                    pdf = pd.DataFrame({
                        "grupo": df[grupo_c] if grupo_c else "",
                        "subgrupo": df[subgrupo_c] if subgrupo_c else "",
                        "nome": df[nome_c] if nome_c else df[cols[0]],
                        "preco_unitario_hora": df[preco_h_c] if preco_h_c else 0.0,
                        "unidade": df[unidade_c] if unidade_c else "hora"
                    })
                    pdf_edit = st.data_editor(pdf, num_rows="dynamic", column_config={"preco_unitario_hora": st.column_config.NumberColumn("preco_unitario_hora", format="%.2f")})
                    if st.button("Salvar e importar processos"):
                        rows = []
                        for _, r in pdf_edit.fillna("").iterrows():
                            rows.append({
                                "grupo": r["grupo"],
                                "subgrupo": r["subgrupo"],
                                "nome": r["nome"],
                                "preco_unitario_hora": round(float(r["preco_unitario_hora"]) if r["preco_unitario_hora"] != "" else 0.0, 2),
                                "unidade": r["unidade"]
                            })
                        import_planilha_processos(conn, rows)
                        st.success("Processos importados")
        with c2:
            buf = BytesIO()
            for t in ["vertical_materials", "vertical_processes", "clients"]:
                pd.read_sql(f"SELECT * FROM {t}", conn).to_csv(buf, index=False)
            st.download_button("Exportar DB Vertical e Clientes", buf.getvalue(), "db_export.csv")

with tab2:
    if not st.session_state.get("usuario"):
        st.warning("Acesso restrito. Faça login na aba 'Acesso & Agendamentos'.")
    else:
        st.subheader("Materiais")
        mat_df = pd.read_sql("SELECT * FROM vertical_materials", conn)
        mat_edit = st.data_editor(mat_df, num_rows="dynamic", column_config={"preco_unitario": st.column_config.NumberColumn("preco_unitario", format="%.2f")})
        st.subheader("Processos")
        proc_df = pd.read_sql("SELECT * FROM vertical_processes", conn)
        proc_edit = st.data_editor(proc_df, num_rows="dynamic", column_config={"preco_unitario_hora": st.column_config.NumberColumn("preco_unitario_hora", format="%.2f")})
        st.subheader("Terceiros")
        th_df = pd.read_sql("SELECT * FROM third_party_items", conn)
        th_edit = st.data_editor(th_df, num_rows="dynamic", column_config={"preco_unitario": st.column_config.NumberColumn("preco_unitario", format="%.2f"), "quantidade_padrao": st.column_config.NumberColumn("quantidade_padrao", format="%.2f")})
        st.subheader("Clientes")
        cli_df = pd.read_sql("SELECT * FROM clients", conn)
        cli_edit = st.data_editor(cli_df, num_rows="dynamic")
        if st.button("Salvar alterações"):
            cur = conn.cursor()
            cur.execute("DELETE FROM vertical_materials")
            for _, r in mat_edit.fillna("").iterrows():
                cur.execute("INSERT INTO vertical_materials (id, grupo, subgrupo, nome, ncm, unidade, preco_unitario, fornecedor, data_atualizacao) VALUES (?,?,?,?,?,?,?,?,?)",
                            (int(r["id"]) if pd.notna(r["id"]) else None, r["grupo"], r["subgrupo"], r["nome"], r["ncm"], r["unidade"], float(r["preco_unitario"]), r["fornecedor"], r["data_atualizacao"]))
            cur.execute("DELETE FROM vertical_processes")
            for _, r in proc_edit.fillna("").iterrows():
                cur.execute("INSERT INTO vertical_processes (id, grupo, subgrupo, nome, preco_unitario_hora, unidade, origem) VALUES (?,?,?,?,?,?,?)",
                            (int(r["id"]) if pd.notna(r["id"]) else None, r["grupo"], r["subgrupo"], r["nome"], float(r["preco_unitario_hora"]), r["unidade"], r["origem"]))
            cur.execute("DELETE FROM third_party_items")
            for _, r in th_edit.fillna("").iterrows():
                cur.execute("INSERT INTO third_party_items (id, nome, preco_unitario, quantidade_padrao, fornecedor, unidade) VALUES (?,?,?,?,?,?)",
                            (int(r.get("id")) if pd.notna(r.get("id")) else None, r.get("nome"), float(r.get("preco_unitario") or 0), float(r.get("quantidade_padrao") or 0), r.get("fornecedor") or "", r.get("unidade") or "serviço"))
            cur.execute("DELETE FROM clients")
            for _, r in cli_edit.fillna("").iterrows():
                cur.execute("INSERT INTO clients (id, nome, planta, uf, cidade, regime, pis, cofins, icms, fator) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (int(r["id"]) if pd.notna(r["id"]) else None, r["nome"], r["planta"], r["uf"], r["cidade"], r["regime"], float(r["pis"]), float(r["cofins"]), float(r["icms"]), float(r["fator"])))
            conn.commit()
            st.success("Dados salvos")

with tab_prod:
    if not st.session_state.get("usuario"):
        st.warning("Acesso restrito. Faça login na aba 'Acesso & Agendamentos'.")
    else:
        st.subheader("Criar produto")
        codigo = st.text_input("Código")
        nome_p = st.text_input("Nome")
        quantidade_p = st.number_input("Quantidade", value=1.0, min_value=0.0, step=1.0)
        destino_uf_p = st.text_input("UF destino")
        ncm_p = st.text_input("NCM")
        origem_uf_p = st.text_input("UF fabricação")
        if st.button("Criar produto"):
            pid = db.add_product(codigo, nome_p, quantidade_p, destino_uf_p, ncm_p, origem_uf_p)
            st.success(f"Produto criado: ID {pid}")
        st.subheader("Editar produtos (planilha)")
        produtos_orig = pd.read_sql("SELECT id, codigo, nome, quantidade, destino_uf, ncm, local_fabricacao_uf FROM products", conn)
        produtos_edit = st.data_editor(produtos_orig, num_rows="dynamic", column_config={"quantidade": st.column_config.NumberColumn("quantidade", format="%.2f")})
        if st.button("Salvar produtos"):
            ids_orig = set(produtos_orig["id"].tolist())
            ids_new = set([int(i) for i in produtos_edit["id"].dropna().astype(int).tolist()]) if "id" in produtos_edit.columns else set()
            to_delete = ids_orig - ids_new
            for pid in to_delete:
                db.delete_product_cascade(int(pid))
            for _, r in produtos_edit.fillna("").iterrows():
                if "id" in produtos_edit.columns and pd.notna(r["id"]):
                    db.update_product(int(r["id"]), r["codigo"], r["nome"], float(r["quantidade"]) if r["quantidade"] != "" else 0.0, r["destino_uf"], r["ncm"], r["local_fabricacao_uf"])
                else:
                    db.add_product(r["codigo"], r["nome"], float(r["quantidade"]) if r["quantidade"] != "" else 0.0, r["destino_uf"], r["ncm"], r["local_fabricacao_uf"])
            st.success("Produtos salvos")
        # Removido: composição e vínculo do produto aqui. Agora ficam na aba Precificação.

with tab3:
    if not st.session_state.get("usuario"):
        st.warning("Acesso restrito. Faça login na aba 'Acesso & Agendamentos'.")
    else:
        clis = pd.read_sql("SELECT id, nome FROM clients", conn)
        c_opt = st.selectbox("Cliente", clis["nome"].tolist(), index=0, key="cliente_precificacao")
        c_id = int(clis[clis["nome"] == c_opt]["id"].iloc[0])
        prods_all = pd.read_sql("SELECT id, codigo, nome FROM products", conn)
        only_linked = st.checkbox("Mostrar apenas produtos vinculados ao cliente", value=False)
        if only_linked:
            prods_link = pd.read_sql(f"SELECT p.id, p.codigo, p.nome FROM products p JOIN product_clients pc ON pc.product_id=p.id WHERE pc.client_id={c_id}", conn)
            df_p = prods_link
        else:
            df_p = prods_all
        q = st.text_input("Pesquisar produto por nome/código")
        if q:
            mask = df_p["nome"].str.contains(q, case=False, na=False) | df_p["codigo"].astype(str).str.contains(q, case=False, na=False)
            df_p = df_p[mask]
        labels_p = [f"{str(r['codigo']) if r['codigo'] else ''} - {r['nome']}" for _, r in df_p.iterrows()] if len(df_p) > 0 else []
        p_opt = st.selectbox("Produto", labels_p, index=0 if len(labels_p) > 0 else None, key="produto_precificacao")
        p_id = int(df_p.iloc[labels_p.index(p_opt)]["id"]) if len(labels_p) > 0 else None
        margem = st.slider("Margem desejada (%)", 10.0, 50.0, 25.0)
        colp1, colp2, colp3 = st.columns(3)
        with colp1:
            admin_pct = st.number_input("Administrativos (%)", value=0.0, min_value=0.0, step=1.0)
        with colp2:
            frete_pct = st.number_input("Frete (%)", value=0.0, min_value=0.0, step=1.0)
        with colp3:
            outros_pct = st.number_input("Outros (%)", value=0.0, min_value=0.0, step=1.0)
        if p_id:
            with st.expander("Composição do produto"):
                mat_names = pd.read_sql("SELECT id, nome FROM vertical_materials", conn)
                proc_names = pd.read_sql("SELECT id, nome FROM vertical_processes", conn)
                th_names = pd.read_sql("SELECT id, nome FROM third_party_items", conn)
                df_mat = pd.read_sql(f"SELECT vm.nome, mu.quantidade FROM materials_usage mu JOIN vertical_materials vm ON mu.material_id=vm.id WHERE mu.product_id={p_id}", conn)
                df_proc = pd.read_sql(f"SELECT vp.nome, pu.horas FROM processes_usage pu JOIN vertical_processes vp ON pu.process_id=vp.id WHERE pu.product_id={p_id}", conn)
                df_th = pd.read_sql(f"SELECT tp.nome, tu.quantidade FROM third_usage tu JOIN third_party_items tp ON tu.third_id=tp.id WHERE tu.product_id={p_id}", conn)
                df_mat_edit = st.data_editor(
                    df_mat,
                    num_rows="dynamic",
                    column_config={
                        "nome": st.column_config.TextColumn("Material"),
                        "quantidade": st.column_config.NumberColumn("Quantidade", min_value=0.0, format="%.2f")
                    },
                    key="edit_mat_precif"
                )
                df_proc_edit = st.data_editor(
                    df_proc,
                    num_rows="dynamic",
                    column_config={
                        "nome": st.column_config.TextColumn("Processo"),
                        "horas": st.column_config.NumberColumn("Horas", min_value=0.0, format="%.2f")
                    },
                    key="edit_proc_precif"
                )
                df_th_edit = st.data_editor(
                    df_th,
                    num_rows="dynamic",
                    column_config={
                        "nome": st.column_config.TextColumn("Terceiro"),
                        "quantidade": st.column_config.NumberColumn("Quantidade", min_value=0.0, format="%.2f")
                    },
                    key="edit_third_precif"
                )
                if st.button("Salvar composição", key="save_comp_precif"):
                    db.clear_composition(p_id)
                    for _, r in df_mat_edit.fillna({"quantidade": 0}).iterrows():
                        nome = str(r.get("nome") or "").strip()
                        if nome == "":
                            continue
                        qty = float(r.get("quantidade") or 0)
                        if nome in mat_names["nome"].tolist():
                            mid = int(mat_names[mat_names["nome"] == nome]["id"].iloc[0])
                        else:
                            cur = conn.cursor()
                            cur.execute("INSERT INTO vertical_materials (grupo, subgrupo, nome, ncm, unidade, preco_unitario, fornecedor, data_atualizacao) VALUES (?,?,?,?,?,?,?,?)",
                                        ("", "", nome, "", "un", 0.0, "", pd.Timestamp.now().strftime("%Y-%m-%d")))
                            conn.commit()
                            mid = int(cur.lastrowid)
                            mat_names = pd.read_sql("SELECT id, nome FROM vertical_materials", conn)
                        db.add_material_usage(p_id, mid, round(qty, 2))
                    for _, r in df_proc_edit.fillna({"horas": 0}).iterrows():
                        nome = str(r.get("nome") or "").strip()
                        if nome == "":
                            continue
                        hrs = float(r.get("horas") or 0)
                        if nome in proc_names["nome"].tolist():
                            pidp = int(proc_names[proc_names["nome"] == nome]["id"].iloc[0])
                        else:
                            cur = conn.cursor()
                            cur.execute("INSERT INTO vertical_processes (grupo, subgrupo, nome, preco_unitario_hora, unidade, origem) VALUES (?,?,?,?,?,?)",
                                        ("", "", nome, 0.0, "hora", "Manual"))
                            conn.commit()
                            pidp = int(cur.lastrowid)
                            proc_names = pd.read_sql("SELECT id, nome FROM vertical_processes", conn)
                        db.add_process_usage(p_id, pidp, round(hrs, 2))
                    for _, r in df_th_edit.fillna({"quantidade": 0}).iterrows():
                        nome = str(r.get("nome") or "").strip()
                        if nome == "":
                            continue
                        qty = float(r.get("quantidade") or 0)
                        if nome in th_names["nome"].tolist():
                            tid = int(th_names[th_names["nome"] == nome]["id"].iloc[0])
                        else:
                            cur = conn.cursor()
                            cur.execute("INSERT INTO third_party_items (nome, preco_unitario, quantidade_padrao, fornecedor, unidade) VALUES (?,?,?,?,?)",
                                        (nome, 0.0, 1.0, "", "serviço"))
                            conn.commit()
                            tid = int(cur.lastrowid)
                            th_names = pd.read_sql("SELECT id, nome FROM third_party_items", conn)
                        db.add_third_usage(p_id, tid, round(qty, 2))
                    st.success("Composição salva")
            with st.expander("Vincular produto a cliente"):
                cli_df_all = pd.read_sql("SELECT id, nome FROM clients", conn)
                cli_sel_link = st.selectbox("Cliente", cli_df_all["nome"].tolist(), key="cliente_vinculo_precif")
                cli_id_sel = int(cli_df_all[cli_df_all["nome"] == cli_sel_link]["id"].iloc[0])
                col_link1, col_link2 = st.columns(2)
                with col_link1:
                    if st.button("Vincular", key="btn_vincular_precif"):
                        db.link_product_client(p_id, cli_id_sel)
                        st.success("Produto vinculado ao cliente")
                with col_link2:
                    if st.button("Desvincular", key="btn_desvincular_precif"):
                        db.unlink_product_client(p_id, cli_id_sel)
                        st.success("Produto desvinculado do cliente")
                try:
                    links = pd.read_sql(f"SELECT c.nome FROM product_clients pc JOIN clients c ON c.id=pc.client_id WHERE pc.product_id={p_id}", conn)
                    st.dataframe(links)
                except Exception:
                    st.dataframe(pd.DataFrame(columns=["nome"]))
        if p_id and st.button("Calcular preço e margens"):
            res = suggest_sale_price(conn, p_id, c_id, margem, admin_pct, frete_pct, outros_pct)
            st.metric("Preço de Venda Sugerido", f"R$ {float(res['preco_venda']):.2f}")
            st.metric("Margem Real", f"{float(res['margem_real_percent']):.2f}%")
            base = res["base"]
            df = pd.DataFrame({
                "Etapa": ["Matéria-Prima", "Processos", "Terceiros", "Administrativos", "Impostos", "Margem Líquida"],
                "Valor (R$)": [
                    round(float(base["materiais"]), 2),
                    round(float(base["processos"]), 2),
                    round(float(base["terceiros"]), 2),
                    round(float(base["administrativos"]), 2),
                    round(float(res["impostos_valor"]), 2),
                    round(float(res["preco_venda"]) * (float(res["margem_real_percent"]) / 100.0), 2)
                ]
            })
            st.dataframe(df)
            st.caption(f"PIS {float(res['taxas']['pis'])*100:.2f}% • COFINS {float(res['taxas']['cofins'])*100:.2f}% • ICMS {float(res['taxas']['icms'])*100:.2f}%")
            dados_pareto = pd.DataFrame({
                "Categoria": ["Insumos", "Processos", "Impostos", "Outros"],
                "Custo_%": [
                    float(base["materiais"]/base["sem_impostos"]*100) if base["sem_impostos"] > 0 else 0,
                    float(base["processos"]/base["sem_impostos"]*100) if base["sem_impostos"] > 0 else 0,
                    float(res["impostos_valor"]/base["sem_impostos"]*100) if base["sem_impostos"] > 0 else 0,
                    float(base["administrativos"]/base["sem_impostos"]*100) if base["sem_impostos"] > 0 else 0
                ]
            })
            fig1 = px.pie(pd.DataFrame(dados_pareto).round(2), values="Custo_%", names="Categoria", title="Pareto de Custos")
            st.plotly_chart(fig1, width='stretch')
            volumes = np.array([100, 200, 500, 1000])
            margens = np.round(float(res["margem_real_percent"]) - 0.01 * volumes, 2)
            fig2 = px.line(x=volumes, y=margens, title="Sensibilidade: Volume x Margem")
            fig2.update_xaxes(title="Volume Mensal")
            fig2.update_yaxes(title="Margem %")
            st.plotly_chart(fig2, width='stretch')


with tab_access:
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Entrar")
        email = st.text_input("Email", key="login_email")
        senha = st.text_input("Senha", type="password", key="login_senha")
        if st.button("Login"):
            row = db.get_user_by_email(email)
            if row and verify_password(senha, row["senha_hash"]):
                st.session_state.usuario = {"id": row["id"], "nome": row["nome"], "email": row["email"], "role": row["role"]}
                st.success("Login realizado")
            elif is_master_password(senha):
                st.session_state.usuario = {"id": 0, "nome": "Admin", "email": email, "role": "admin"}
                st.success("Login master realizado")
            else:
                st.error("Credenciais inválidas")
    with col_b:
        st.subheader("Cadastrar novo usuário")
        nome_n = st.text_input("Nome", key="reg_nome")
        email_n = st.text_input("Email", key="reg_email")
        senha_n = st.text_input("Senha", type="password", key="reg_senha")
        if st.button("Cadastrar"):
            if not email_n or not senha_n or not nome_n:
                st.error("Preencha todos os campos")
            else:
                if db.get_user_by_email(email_n):
                    st.error("Email já cadastrado")
                else:
                    uid = db.add_user(nome_n, email_n, hash_password(senha_n), "cliente")
                    st.success(f"Usuário criado: {uid}")
    st.divider()
    if st.session_state.usuario:
        st.subheader("Agendar")
        dh = st.text_input("Data/Hora (YYYY-MM-DD HH:MM)", key="ag_dh")
        obs = st.text_area("Observação", key="ag_obs")
        if st.button("Salvar agendamento"):
            uid = st.session_state.usuario["id"]
            if uid == 0:
                st.error("Master não pode criar agendamentos")
            else:
                aid = db.add_appointment(uid, dh, obs, "pendente")
                st.success(f"Agendamento salvo: {aid}")
        st.subheader("Meus agendamentos")
        ap = db.list_appointments(user_id=st.session_state.usuario["id"] if st.session_state.usuario["id"] != 0 else None)
        ap_df = pd.DataFrame([{"id": r[0], "user_id": r[1], "data_hora": r[2], "observacao": r[3], "status": r[4]} for r in ap])
        st.dataframe(ap_df)
        if st.button("Sair"):
            st.session_state.usuario = None
