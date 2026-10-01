#!/usr/bin/env bash
# Run the suite against Odoo 19 **Community** - the companion to test-ee.sh.
#
# Stops the dev server first. The tours need to bind `http_port` from the conf,
# so leaving a dev server on 8279 makes every browser test fail with a spawn
# error that looks like "chrome.exe not found" and says nothing about the port.
#
# No `--logfile`, for the same reason as the EE script: with one, the per-test
# `FAIL:` line and the tour's own report never appear.
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

LOG="dev/test_ce_$(date +%H%M%S).log"

# --- preflight: fail loudly rather than skip silently ----------------------
# A missing websocket-client or chrome raises a bare unittest.SkipTest, and a
# skipped tour still tallies "0 failed".
"$PY" -c "import websocket" 2>/dev/null || { echo "PREFLIGHT FAIL: websocket-client missing in $PY - every HttpCase will skip"; exit 1; }
[ -x "/c/Program Files/Google/Chrome/Application/chrome.exe" ] || { echo "PREFLIGHT FAIL: chrome.exe not at the expected path - every tour will skip"; exit 1; }

# Reap orphaned test chromes and their profile dirs, matched on the
# --user-data-dir Odoo gives them and never on the process name - the
# developer's own Chrome must survive.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | Where-Object { \$_.CommandLine -like '*_chrome_odoo*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1 || true
rm -rf "$TEMP"/tmp*_chrome_odoo 2>/dev/null || true

# `tee`: keep the filtered console this script has always printed, and also keep
# a durable log so the tally below can be trusted and a failure re-read later.
# An array rather than backslash continuations: keeps the invocation
# greppable and immune to a stray trailing space after a "\".
ARGS=(-c dev/aam_dev.conf -d aam19_dev -u odooapp_access_management --test-enable)
ARGS+=(--test-tags "${1:-/odooapp_access_management}" --stop-after-init)

PATTERN="FAIL:|ERROR:|FAILED: \[|has not been found|failed, .* error|tour succeeded|skipped Test"
"$PY" "$BIN" "${ARGS[@]}" 2>&1 \
  | tee "$LOG" \
  | grep -E "$PATTERN" \
  | sed 's/.*TestAam/TestAam/;s/.*tests\.//;s/.*result: //' \
  | cut -c1-160

echo "--- tally ---"
# Count only real tour completions: a bare `grep -c 'tour succeeded'` also matches
# the `success_signal="tour succeeded"` line in every traceback.
echo "tours succeeded: $(grep -acE '\.browser: tour succeeded' "$LOG" || true)"
# No traceback count here, unlike the Odoo 18 scripts: those grep a --logfile,
# while these tee the console, which also carries Odoo's own debug stack traces
# ("setting X to Y"). The number would read in the hundreds on a perfectly green
# run and teach you to ignore the tally.

CHROME_SKIPS=$(grep -acE 'skipped .*(chrome\.exe|not found)' "$LOG" || true)
echo "skips (expected, app not installed): $(grep -acE 'skipped .*(Enterprise|not installed)' "$LOG" || true)"
echo "skips (CHROME - NOT a pass):         $CHROME_SKIPS"
if [ "$CHROME_SKIPS" -gt 0 ]; then
  echo
  echo "!!! $CHROME_SKIPS tour(s) were SKIPPED because chrome could not be spawned."
  echo "!!! The suite still reports '0 failed'. This is NOT a green run."
  echo "!!! common.py turns ANY OSError out of _spawn_chrome into"
  echo "!!! SkipTest(\"<path> not found\"). The usual one on Windows is a"
  echo "!!! PermissionError reading DevToolsActivePort while Chrome still has it"
  echo "!!! locked; tests/common.py ChromeSpawnTolerance retries that, so a skip now"
  echo "!!! means something else: orphaned chromes, stale profile dirs, or a"
  echo "!!! devtools port collision."
  echo "!!! Re-run the affected classes individually until each prints 'tour succeeded':"
  grep -aE 'skipped .*(chrome\.exe|not found)' "$LOG" | sed 's/.*skipped /    /;s/ :.*//'
  echo "log: $LOG"
  exit 1
fi
echo "log: $LOG"
