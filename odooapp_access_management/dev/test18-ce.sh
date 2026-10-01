#!/usr/bin/env bash
# Run the suite against Odoo 18 **Community**. Companion: dev/test18-ee.sh.
#
# Three things make a tour run lie, and all three are handled here:
#
#  1. A stale dev server on the conf's http_port. HttpCase binds that port, so a
#     leftover server makes every browser test die with a spawn error that
#     mentions chrome and says nothing about the port. Killed first.
#  2. Orphaned chrome processes and stale %TEMP%/tmp*_chrome_odoo profile dirs.
#     A missing chrome and a missing websocket-client both raise a bare
#     unittest.SkipTest, so a silently skipped tour still tallies "0 failed".
#     Preflighted below; orphans are reaped by their --user-data-dir, never by
#     process name - the developer's own Chrome must survive.
#  3. The first tour after a JS change pays for the asset bundle rebuild and can
#     time out on step 1 while every later tour passes.
#
# `--logfile`, NOT `tee`. This is the opposite of the Odoo 19 scripts, and it is
# not a style choice: on this Windows build Odoo 18 writes nothing at all to
# stdout or stderr (measured - a failing install produced 0 bytes on both while
# 4883 bytes appeared in a log file). Worse, with no `logfile` set it falls back
# to the shared E:\Program Files\Odoo18community\server\odoo.log, which other
# instances also write to. So a `tee`-the-console pipeline sees an empty stream
# AND the output interleaves with unrelated runs. Always name our own file.
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
CONF=dev/aam18_dev.conf
DB=aam18_dev
PORT=8779

# --- preflight: fail loudly rather than skip silently ----------------------
"$PY" -c "import websocket" 2>/dev/null || { echo "PREFLIGHT FAIL: websocket-client missing in $PY - every HttpCase will skip"; exit 1; }
[ -x "/c/Program Files/Google/Chrome/Application/chrome.exe" ] || { echo "PREFLIGHT FAIL: chrome.exe not at the expected path - every tour will skip"; exit 1; }

# --- 1. no stale dev server on the conf's port -----------------------------
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | Where-Object { \$_.CommandLine -like '*aam18_dev.conf*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1 || true
sleep 3
if netstat -ano 2>/dev/null | grep -qE ":$PORT\s+.*LISTENING"; then
  echo "PREFLIGHT FAIL: something is still listening on $PORT"; exit 1
fi

# --- 2. reap orphaned test chromes and their profile dirs ------------------
# Matched on --user-data-dir=...tmp*_chrome_odoo, never on the process name.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | Where-Object { \$_.CommandLine -like '*_chrome_odoo*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1 || true
rm -rf "$TEMP"/tmp*_chrome_odoo 2>/dev/null || true

LOG="dev/test18_ce_$(date +%H%M%S).log"

# An array rather than backslash continuations: keeps the invocation greppable
# and immune to a stray trailing space after a "\".
ARGS=(-c "$CONF" -d "$DB" -u odooapp_access_management --test-enable)
ARGS+=(--test-tags "${1:-/odooapp_access_management}")
ARGS+=(--stop-after-init --logfile "$LOG")

"$PY" "$BIN" "${ARGS[@]}" >/dev/null 2>&1 || true

PATTERN="FAIL:|ERROR:|FAILED: \[|has not been found|failed, .* error|tour succeeded|skipped Test"
grep -aE "$PATTERN" "$LOG" | sed 's/.*TestAam/TestAam/;s/.*tests\.//;s/.*result: //' | cut -c1-160

echo "--- tally ---"
# Count only real tour completions. A bare `grep -c 'tour succeeded'` also matches
# the `success_signal="tour succeeded"` line inside every traceback, which inflates
# the number by roughly 3x and makes a failing run look busy and healthy.
echo "tours succeeded: $(grep -acE '\.browser: tour succeeded' "$LOG" || true)"
echo "tracebacks:      $(grep -ac 'Traceback (most recent call last)' "$LOG" || true)"

# A skipped test still tallies "0 failed", so skips have to be read, not counted.
# Two kinds, and only one of them is legitimate here.
ENT_SKIPS=$(grep -acE 'skipped .*(Enterprise|not installed)' "$LOG" || true)
CHROME_SKIPS=$(grep -acE 'skipped .*(chrome\.exe|not found)' "$LOG" || true)
echo "skips (expected, app not installed): $ENT_SKIPS"
echo "skips (CHROME - NOT a pass):         $CHROME_SKIPS"
if [ "$CHROME_SKIPS" -gt 0 ]; then
  echo
  echo "!!! $CHROME_SKIPS tour(s) were SKIPPED because chrome could not be spawned."
  echo "!!! The suite still reports '0 failed'. This is NOT a green run."
  echo "!!! The message is misleading: _chrome_start (tests/common.py) turns ANY"
  echo "!!! OSError out of _spawn_chrome into SkipTest(\"<path> not found\"). The usual"
  echo "!!! one on Windows is a PermissionError reading DevToolsActivePort while"
  echo "!!! Chrome still has it locked; tests/common.py ChromeSpawnTolerance retries"
  echo "!!! that, so a skip now means something else: orphaned chromes, stale"
  echo "!!! %TEMP%/tmp*_chrome_odoo profiles, or a devtools port collision."
  echo "!!! Re-run the affected classes individually until each prints 'tour succeeded':"
  grep -aE 'skipped .*(chrome\.exe|not found)' "$LOG" | sed 's/.*skipped /    /;s/ :.*//'
  echo "log: $LOG"
  exit 1
fi
echo "log: $LOG"
