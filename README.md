# Módulo de Precificação

Aplicativo Streamlit para precificação fabril focado em matéria-prima, processos, terceiros, custos administrativos e impostos (PIS/COFINS/ICMS) por NCM e UF.

## Rodar
1. python3 -m venv .venv
2. .venv/bin/pip install streamlit pandas numpy plotly openpyxl
3. .venv/bin/streamlit run app.py

## Railway
- Configure o repositório no Railway e selecione Deploy via Dockerfile
- Defina variável de ambiente MASTER_PASSWORD com sua senha master
- Railway define PORT automaticamente; o app usa PORT e expõe 0.0.0.0
- Opcional: adicione PostgreSQL para persistência avançada; neste módulo usa SQLite para demonstração

## Estrutura
- pricing/db.py: esquema SQLite, seed, utilitários de produto e vínculos
- pricing/engine.py: motor de custo, impostos e preço sugerido
- app.py: interface com upload de ERP, edição de DB Vertical, Produtos e Precificação
 - pricing/auth.py: hashing e verificação de senha; master via ambiente
 - Acesso & Agendamentos: cadastro/login e criação de agendamentos vinculados ao usuário

## Publicar no GitHub
1. git branch -M main
2. git remote add origin https://github.com/SEU_USUARIO/modulo-precificacao.git
3. git push -u origin main
4. Adicione o colaborador cesarscheck nas configurações do repositório (Settings → Collaborators)

## Administradores e colaboradores
- Para adicionar CESARSCHECK como admin pela UI:
  - Acesse Settings → Collaborators → Add people → informe CESARSCHECK → permissão Admin
- Via GitHub CLI (requer gh instalado e login):
  - REPO="Marcelov1981/Modulo-Precificacao" USER="CESARSCHECK" bash scripts/add_collaborator.sh
  - ou: gh api -X PUT "repos/Marcelov1981/Modulo-Precificacao/collaborators/CESARSCHECK" -f permission=admin
