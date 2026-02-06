#!/usr/bin/env bash
set -euo pipefail

# Configuração
REPO="Marcelov1981/Precifica-o-Costi"
USER="CESARSCHECK"

echo "Adicionando $USER como admin em $REPO..."

if ! command -v gh >/dev/null 2>&1; then
  echo "Erro: gh CLI não encontrado. Instale via https://cli.github.com/"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Erro: Você não está logado no GitHub CLI."
  echo "Por favor, execute 'gh auth login' primeiro."
  exit 1
fi

# Tenta adicionar usando o comando de alto nível (mais seguro/amigável)
gh repo collaborator add "$USER" --permission admin -R "$REPO"

