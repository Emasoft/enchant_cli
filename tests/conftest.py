from rich.console import Console
from rich.table import Table
import pytest

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "api_key: mark test as requiring OPENROUTER_API_KEY environment variable"
    )

def pytest_sessionfinish(session, exitstatus):
    # Simplified version without rich traceback handling
    console = Console()
    
    # Get test statistics from terminal reporter
    reporter = session.config.pluginmanager.getplugin('terminalreporter')
    passed = len(reporter.stats.get('passed', []))
    failed = len(reporter.stats.get('failed', []))
    skipped = len(reporter.stats.get('skipped', []))
    
    # Print simple summary without rich traceback formatting
    console.print("\n📊 [bold]Test Summary[/]")
    console.print(f"Total Tests: [cyan]{passed + failed + skipped}[/]")
    console.print(f"✅ Passed: [green]{passed}[/]")
    console.print(f"❌ Failed: [red]{failed}[/]")
    console.print(f"⏩ Skipped: [yellow]{skipped}[/]")
