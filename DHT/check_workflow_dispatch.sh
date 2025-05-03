#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# Script to detect and verify workflow_dispatch trigger in GitHub workflows

echo "Checking GitHub workflows for workflow_dispatch trigger..."

# Check local workflow files
echo "Checking local workflow files..."
for file in .github/workflows/*.yml; do
  echo "Examining $file..."
  if grep -q "workflow_dispatch:" "$file"; then
    echo "✅ $file has workflow_dispatch trigger."
  else
    echo "❌ $file is missing workflow_dispatch trigger."
  fi
done

# Check GitHub API
echo "Checking workflows via GitHub API..."
REPO="Emasoft/enchant_cli"
gh api "repos/$REPO/actions/workflows" --jq '.workflows[] | {name: .name, path: .path, id: .id}'

# Try to get detailed info on workflows
echo "Getting more details on workflows..."
for id in $(gh api "repos/$REPO/actions/workflows" --jq '.workflows[].id'); do
  echo "Details for workflow ID $id:"
  gh api "repos/$REPO/actions/workflows/$id" --jq '{name: .name, path: .path, state: .state, html_url: .html_url}'
done

# Try manual triggering through API
echo "Attempting to manually trigger workflows through API..."
WORKFLOWS=$(gh api "repos/$REPO/actions/workflows" --jq '.workflows[].path' | sed 's/.*\///')
for workflow in $WORKFLOWS; do
  echo "Trying to trigger $workflow..."
  gh workflow run "$workflow" -f reason="Manual test from script" || echo "Failed to trigger $workflow"
done

exit 0
