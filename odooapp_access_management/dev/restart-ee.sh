#!/usr/bin/env bash
# Start (or restart) a long-running **Enterprise** dev server for browser testing.
#
# The sibling restart.sh does the same for Community. This is deliberately a
# separate script rather than a flag: different server tree, different python,
# its own conf, port, database and filestore.
#
# The kill filter matches `aam_dev_ee.conf` ONLY. The EE Windows service owns
# port 8169 and E:\Program Files\Odoo19\server\odoo.conf - never touch it.
#
# RUN THIS AFTER EVERY SCSS/JS/XML EDIT. A running v19 server keeps the compiled
# asset bundle and does not notice the files changed - and there is no `--dev`
# flag to make it: ALL_DEV_MODE in odoo/tools/config.py is
# ['access', 'qweb', 'reload', 'xml'], with no `assets`. The symptom is a page
# that renders the new markup with the old stylesheet, which looks like a
# specificity bug and is not one. Note also that the backend stylesheet the page
# actually links is `web.assets_web`, not `web.assets_backend` - compiling the
# latter by hand in a shell proves nothing about what the browser gets.
#
# `-u odooapp_access_management` on start: a plain start serves whatever view
# archs the database happens to hold, and `-u` against a *running* server
# updates the DB but not that process's Python, which crashes the web client in
# kanban_arch_parser. Doing the upgrade as part of the start avoids both.
set -e
cd "$(dirname "$0")/.."
export MSYS2_ARG_CONV_EXCL='*'

# This runner targets Odoo 19. Refuse to run from another serie's checkout:
# these scripts merge forward between the serie branches, so an 18.0 tree ends up
# holding the 19 runners and vice versa, and running the wrong one silently
# exercises the wrong server, port and database. The manifest is the authority.
_SERIE=$(grep -oE "'version':[[:space:]]*'[0-9]+" __manifest__.py | grep -oE '[0-9]+$')
if [ "$_SERIE" != "19" ]; then
    echo "$(basename "$0") targets Odoo 19, but __manifest__.py says ${_SERIE}.0."
    echo "Use the dev/*${_SERIE}*.sh runners in this checkout instead."
    exit 2
fi
PY="E:/Program Files/Odoo19/python/python.exe"
BIN="E:/Program Files/Odoo19/server/odoo-bin"

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | Where-Object { \$_.CommandLine -like '*aam_dev_ee.conf*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1 || true
sleep 3
LOG="dev/server_ee_$(date +%H%M%S).log"
nohup "$PY" "$BIN" -c dev/aam_dev_ee.conf -d aam19_ee \
  -u odooapp_access_management --logfile "$LOG" >/dev/null 2>&1 &
sleep 25
echo "listening: $(netstat -ano 2>/dev/null | grep -cE ':8379\s+.*LISTENING')"
echo "processes: $(powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | Where-Object { \$_.CommandLine -like '*aam_dev_ee.conf*' }).Count" 2>/dev/null | tr -d '\r')"
echo "log: $LOG  errors: $(grep -cE 'ERROR|CRITICAL' "$LOG" || echo 0)"
