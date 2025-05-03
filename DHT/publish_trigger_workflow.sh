#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

repo_fullname="$1"
branch="$2"
wf_type="$3"
max_retries="${4:-3}"

# Detect appropriate workflow file
workflow_file="$("${SCRIPT_DIR}/publish_trigger_detect.sh" "$repo_fullname" "$wf_type")" || exit 1

helpers=(trigger_cli trigger_api trigger_id trigger_curl trigger_any trigger_temp)
for h in "${helpers[@]}"; do
  if "${SCRIPT_DIR}/publish_${h}.sh" "$repo_fullname" "$branch" "$workflow_file" "$max_retries"; then
    exit 0
  fi
done

# Manual instructions last
"${SCRIPT_DIR}/publish_trigger_manual.sh" "$repo_fullname" "$workflow_file"
exit 1
