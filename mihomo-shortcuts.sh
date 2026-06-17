#!/usr/bin/env bash
# Mihomo shortcut commands — all shortcuts in one file.
# Source this file in your shell to enable the commands:
#   source /path/to/mihomo-shortcuts.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLASHCTL="${CLASHCTL:-$SCRIPT_DIR/clashctl}"

pxon()      { "$CLASHCTL" start "$@"; }
pxoff()     { "$CLASHCTL" stop "$@"; }
pxrestart() { "$CLASHCTL" restart "$@"; }
pxlog()     { "$CLASHCTL" log "$@"; }
pxnodes()   { "$CLASHCTL" nodes "$@"; }
pxuse()     { "$CLASHCTL" use "$@"; }
pxtest()    { "$CLASHCTL" test "$@"; }
pxupdate()  { "$CLASHCTL" update "$@"; }
pxsub()     { "$CLASHCTL" sub "$@"; }
pxedit()    { "$CLASHCTL" edit "$@"; }
pxui()      { "$CLASHCTL" ui "$@"; }
pxproxy()   { "$CLASHCTL" proxy "$@"; }

pxstatus() {
  local CONFIG="$HOME/.config/mihomo/config.yaml"
  local LOG="/tmp/mihomo.log"
  local PID_FILE="/tmp/mihomo.pid"
  local API="http://127.0.0.1:9090"

  echo "=== mihomo status ==="

  if systemctl --user is-active mihomo.service &>/dev/null; then
    local PID=$(systemctl --user show mihomo.service -p MainPID --value)
    echo "Status:   running (systemd, PID: $PID)"
  elif [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Status:   running (nohup, PID: $(cat "$PID_FILE"))"
  elif pgrep -x mihomo &>/dev/null; then
    echo "Status:   running (PID: $(pgrep -x mihomo))"
  else
    echo "Status:   not running"
  fi

  if curl -s --max-time 2 "$API/proxies/PROXY" &>/dev/null; then
    local NOW=$(curl -s --max-time 2 "$API/proxies/PROXY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('now','N/A'))")
    echo "Current node: $NOW"
  else
    echo "Current node: API not ready"
  fi

  echo "Proxy port: 127.0.0.1:7890 (HTTP/SOCKS5)"
  echo "API port:   127.0.0.1:9090"

  echo -n "Connectivity: "
  if curl -x http://127.0.0.1:7890 -s --max-time 5 -I https://www.google.com &>/dev/null; then
    echo "OK ✓"
  else
    echo "Failed ✗"
  fi

  echo ""
  echo "--- last 5 log lines ---"
  if [ -f "$LOG" ]; then
    tail -n 5 "$LOG"
  elif systemctl --user is-active mihomo.service &>/dev/null; then
    journalctl --user -u mihomo.service -n 5 --no-pager 2>/dev/null
  else
    echo "no logs yet"
  fi
}
