#!/usr/bin/env bash
# Restart the dev server, making sure no stale process survives.
# Two of them once ran at the same time and the old one kept serving stale
# Python, which cost an hour of confusion.
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
PY="E:/Program Files/Odoo19community/python/python.exe"
BIN="E:/Program Files/Odoo19community/server/odoo-bin"

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | Where-Object { \$_.CommandLine -like '*aam_dev.conf*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1 || true
sleep 3
LOG="dev/server_$(date +%H%M%S).log"
nohup "$PY" "$BIN" -c dev/aam_dev.conf -d aam19_dev --logfile "$LOG" >/dev/null 2>&1 &
sleep 10
echo "listening: $(netstat -ano 2>/dev/null | grep -cE ':8279\s+.*LISTENING')"
echo "processes: $(powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | Where-Object { \$_.CommandLine -like '*aam_dev.conf*' }).Count" 2>/dev/null | tr -d '\r')"
echo "log: $LOG  errors: $(grep -cE 'ERROR|CRITICAL' "$LOG" || echo 0)"
