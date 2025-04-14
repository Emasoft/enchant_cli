# Environment Configuration Reference

## Required API Keys & Tokens

Three critical secret credentials are needed for full functionality:

```bash
# Translation API Access
export OPENROUTER_API_KEY="your-openrouter-key"

# PyPI Package Publishing
# Note: For trusted publishing via GitHub Actions, this token is often not needed directly
# but might be used for local twine uploads if ever done manually.
# The workflow uses OIDC.
export PYPI_API_TOKEN="your-pypi-token" # Keep for potential manual use

# Test Coverage Reporting
export CODECOV_API_TOKEN="your-codecov-token"
```
Those variables are usually already defined in the environment via .zshrc or .bashrc, so they usually does not need to be set explicitly. Set them only if they are not defined.

## GitHub Secret Configuration

The `first_push.sh` script contains commands using the `gh` CLI to set up the necessary secrets in your GitHub repository during the initial setup. These secrets are then used by the GitHub Actions workflows (`tests.yml`, `publish.yml`).

Example commands from `first_push.sh`:
```bash
gh secret set PYPI_API_TOKEN -b"$PYPI_API_TOKEN" -r"Emasoft/enchant_cli" # For PyPI trusted publishing (OIDC preferred)
gh secret set OPENROUTER_API_KEY -b"$OPENROUTER_API_KEY" -r"Emasoft/enchant_cli" # For API access in tests/app
gh secret set CODECOV_API_TOKEN -b"$CODECOV_API_TOKEN" -r"Emasoft/enchant_cli" # For Codecov uploads
```

**No manual exporting needed for Actions** - these should be configured via:
 1. Your local environment (via shell profile/CI variables) for local development/testing.
 2. GitHub repository secrets (set up initially via `first_push.sh` or manually) for GitHub Actions.

## Verification Checklist

Confirm proper configuration in both environments:

### Local Development
```bash
echo $OPENROUTER_API_KEY  # Should show key
echo $PYPI_API_TOKEN      # Should show token
echo $CODECOV_API_TOKEN   # Should show token
```

### GitHub Actions
1. Repository Settings → Secrets & Variables → Actions
2. Verify all three secrets exist with correct names

**Note:** The secret configuration in `first_push.sh` only needs to run once during initial setup. Subsequent releases will use the stored secrets.
