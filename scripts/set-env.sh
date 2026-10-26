#!/usr/bin/env bash
# Set one value in the SERVER's .env without showing it, then restart the bot.
# Usage (from the Mac):  ./scripts/set-env.sh BACKUP_PASSWORD
#
#   code:    Mac → git push → GitHub → server   (./scripts/deploy.sh)
#   secrets: Mac ──────── SSH ─────────► server (this script, never through git)
set -euo pipefail

name="${1:?usage: ./scripts/set-env.sh NAME}"
# The name goes into commands on the server, so allow only A-Z, 0-9 and _
if [[ ! "$name" =~ ^[A-Z][A-Z0-9_]*$ ]]; then
  echo "NAME must look like BACKUP_PASSWORD"
  exit 1
fi

read -rsp "Value for $name (hidden): " value
echo
if [[ -z "$value" || "$value" == *"'"* ]]; then
  echo "Empty, or contains ' (not allowed). Nothing changed."
  exit 1
fi

# The value travels through stdin, never as a command argument: arguments are
# visible to every user on a machine (ps), stdin is not.
printf '%s\n' "$value" | ssh prolog "
  set -e
  IFS= read -r value
  env_file=/home/prolog/app/.env
  sudo -u prolog sed -i '/^$name=/d' \$env_file   # replace, don't duplicate
  # Single quotes: the value is taken literally, even with # or spaces
  printf \"%s='%s'\n\" '$name' \"\$value\" | sudo -u prolog tee -a \$env_file >/dev/null
  sudo systemctl restart prolog
  sleep 3
  echo \"$name saved. Bot restarted: \$(systemctl is-active prolog)\"
"
