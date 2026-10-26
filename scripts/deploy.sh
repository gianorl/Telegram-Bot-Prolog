#!/usr/bin/env bash
# Deploy the latest pushed code to the VPS. Run from the Mac: ./scripts/deploy.sh
#
#   Mac: git push  ──►  GitHub  ──►  server: git pull → pip install → restart
#
# Migrations run by themselves when the bot starts (db.migrate).
set -euo pipefail

APP=/home/prolog/app

ssh prolog "
  set -e
  sudo -u prolog git -C $APP pull --ff-only
  sudo -u prolog $APP/venv/bin/pip install -q --disable-pip-version-check -r $APP/requirements.txt
  sudo systemctl restart prolog
  sleep 5
  echo \"deployed: \$(sudo -u prolog git -C $APP log --oneline -1)\"
  echo \"status:   \$(systemctl is-active prolog)\"
"
