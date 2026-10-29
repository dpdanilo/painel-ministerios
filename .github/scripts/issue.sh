#!/usr/bin/env bash
# Abre (ou atualiza) uma issue com o título dado, sem duplicar.
# Uso: issue.sh "<título>" <arquivo-com-o-corpo> <rótulo>
set -euo pipefail
titulo="$1"; corpo="$2"; rotulo="$3"
gh label create "$rotulo" --color d21212 --force >/dev/null 2>&1 || true
num=$(gh issue list --state open --label "$rotulo" --search "\"$titulo\" in:title" --json number,title \
      --jq "map(select(.title == \"$titulo\")) | .[0].number // empty")
if [ -n "$num" ]; then
  gh issue edit "$num" --body-file "$corpo" >/dev/null
  echo "issue #$num atualizada"
else
  gh issue create --title "$titulo" --body-file "$corpo" --label "$rotulo"
fi
