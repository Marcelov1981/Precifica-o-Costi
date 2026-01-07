# Módulo de Precificação

Aplicativo Streamlit para precificação fabril focado em matéria-prima, processos, terceiros, custos administrativos e impostos (PIS/COFINS/ICMS) por NCM e UF.

## Rodar
1. python3 -m venv .venv
2. .venv/bin/pip install streamlit pandas numpy plotly openpyxl
3. .venv/bin/streamlit run app.py

## Estrutura
- pricing/db.py: esquema SQLite, seed, utilitários de produto e vínculos
- pricing/engine.py: motor de custo, impostos e preço sugerido
- app.py: interface com upload de ERP, edição de DB Vertical, Produtos e Precificação

## Publicar no GitHub
1. git branch -M main
2. git remote add origin https://github.com/SEU_USUARIO/modulo-precificacao.git
3. git push -u origin main
4. Adicione o colaborador cesarscheck nas configurações do repositório (Settings → Collaborators)
