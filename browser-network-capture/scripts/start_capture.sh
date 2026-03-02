#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <abs_log_file_path> [user_data_dir]"
  exit 1
fi

LOG_FILE="$1"
USER_DATA_DIR="${2:-$HOME/.local/playwright/profile}"
SCRIPT_PRIMARY="$HOME/.config/km-cli/playwright/capture-network.mjs"
SCRIPT_FALLBACK="/Users/huanghao/workspace/mt-cli/tools/km-cli/scripts/capture-network.mjs"

if [[ -f "$SCRIPT_PRIMARY" ]]; then
  SCRIPT="$SCRIPT_PRIMARY"
elif [[ -f "$SCRIPT_FALLBACK" ]]; then
  SCRIPT="$SCRIPT_FALLBACK"
else
  echo "capture script not found"
  exit 2
fi

mkdir -p "$(dirname "$LOG_FILE")"

echo "[capture] script=$SCRIPT"
echo "[capture] user_data_dir=$USER_DATA_DIR"
echo "[capture] log_file=$LOG_FILE"

USER_DATA_DIR="$USER_DATA_DIR" LOG_FILE="$LOG_FILE" node "$SCRIPT"
