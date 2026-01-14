#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-Marcelov1981/Modulo-Precificacao}"
USER="${USER:-CESARSCHECK}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI não encontrado. Instale via https://cli.github.com/ e autentique com 'gh auth login'."
  exit 1
fi

gh api -X PUT "repos/${REPO}/collaborators/${USER}" -f permission=admin
echo "Solicitada adição de ${USER} como admin em ${REPO}."
