# Environment Configuration Reference

## Required API Keys & Tokens

Three critical secret credentials are needed for full functionality:

```bash
# Translation API Access
export OPENROUTER_API_KEY="your-openrouter-key"

# PyPI Package Publishing 
export PYPI_API_TOKEN="your-pypi-token"

# Test Coverage Reporting
export CODECOV_API_TOKEN="your-codecov-token"
```
Those variables are usually already defined in the environment via .zshrc or .bashrc, so they usually does not need to be set explicitly. Set them only if they are not defined.

## Automatic Secret Configuration

The `release.sh` script handles GitHub secrets setup:

```bash
# Script automatically configures these as repository secrets:
gh secret set PYPI_API_KEY -b"$PYPI_API_TOKEN" -r"Emasoft/enchant_cli"
gh secret set OPENROUTER_API_KEY -b"$OPENROUTER_API_KEY" -r"Enchant/cli"
gh secret set CODECOV_API_TOKEN -b"$CODECOV_API_TOKEN" -r"Enchant/cli"
```

**No manual exporting needed** - these are already configured in:
1. Your local environment (via shell profile/CI variables)
2. GitHub repository secrets (via release script)

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

**Note:** The release script's secret configuration only needs to run once during initial setup. Subsequent releases will use the stored secrets.
