#!/usr/bin/env bash
# Start (or restart) a long-running Odoo 18 **Community** dev server for clicking
# through in a browser: http://localhost:8779/odoo, admin/admin.
#
# The kill filter matches `aam18_dev.conf` ONLY. It must never touch
# E:\Program Files\Odoo18community\server\odoo.conf (8569/8572), the stopped NSSM
# service `odoo-server-18.0` (8069), or either Odoo 19 dev server - and it cannot,
# because "aam18_dev.conf" does not contain the substring "aam_dev.conf".
#
# RUN THIS AFTER EVERY SCSS/JS/XML EDIT. A running server keeps the compiled asset
# bundle and never notices the files changed. There is no `--dev=assets` on 18 any
# more than on 19: v18 `odoo/tools/config.py:305,576` accepts only
# all|reload|qweb|xml, and the two `'assets' in ...` reads in v18 test
# `session.debug` (the ?debug=assets URL parameter), not `dev_mode`. The symptom is
# new markup with the old stylesheet, which looks like a specificity bug and is not
# one. Note the page links `web.assets_web`, not `web.assets_backend`.
#
# `-u odooapp_access_management` on start: a plain start serves whatever archs the
# database happens to hold, and `-u` against a *running* server updates the DB but
# not that process's Python, which then crashes the web client in
# kanban_arch_parser with "Cannot read properties of undefined (reading 'type')".
set -e
cd "$(dirname "$0")/.."
export MSYS2_ARG_CONV_EXCL='*'

# This runner targets Odoo 18. Refuse to run from another serie's checkout:
# these scripts merge forward between the serie branches, so an 18.0 tree ends up
# holding the 19 runners and vice versa, and running the wrong one silently
# exercises the wrong server, port and database. The manifest is the authority.
_SERIE=$(grep -oE "'version':[[:space:]]*'[0-9]+" __manifest__.py | grep -oE '[0-9]+$')
if [ "$_SERIE" != "18" ]; then
    echo "$(basename "$0") targets Odoo 18, but __manifest__.py says ${_SERIE}.0."
    echo "Use the dev/*${_SERIE}*.sh runners in this checkout instead."
    exit 2
fi
PY="E:/Program Files/Odoo18community/python/python.exe"
BIN="E:/Program Files/Odoo18community/server/odoo-bin"
PORT=8779

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | Where-Object { \$_.CommandLine -like '*aam18_dev.conf*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1 || true
sleep 3

LOG="dev/server18_$(date +%H%M%S).log"
nohup "$PY" "$BIN" -c dev/aam18_dev.conf -d aam18_dev \
  -u odooapp_access_management --logfile "$LOG" >/dev/null 2>&1 &

# Poll rather than sleep a fixed 10-25s: an under-sleep reports "not listening" on
# a server that was merely slow, and an over-sleep wastes every iteration.
for _ in $(seq 1 60); do
  if netstat -ano 2>/dev/null | grep -qE ":$PORT\s+.*LISTENING"; then break; fi
  sleep 1
done

echo "listening: $(netstat -ano 2>/dev/null | grep -cE ":$PORT\s+.*LISTENING")"
echo "processes: $(powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | Where-Object { \$_.CommandLine -like '*aam18_dev.conf*' }).Count" 2>/dev/null | tr -d '\r')"
echo "log: $LOG  errors: $(grep -cE 'ERROR|CRITICAL' "$LOG" || echo 0)"
echo "url: http://localhost:$PORT/odoo"
